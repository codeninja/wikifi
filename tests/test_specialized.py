"""Type-aware (specialized) extractor tests."""

from __future__ import annotations

from wikifi.repograph import FileKind
from wikifi.specialized import select
from wikifi.specialized.graphql import extract as gql_extract
from wikifi.specialized.openapi import extract as openapi_extract
from wikifi.specialized.protobuf import extract as proto_extract
from wikifi.specialized.sql import extract as sql_extract


def test_select_routes_known_kinds_to_extractors():
    assert select(FileKind.SQL) is sql_extract
    assert select(FileKind.PROTOBUF) is proto_extract
    assert select(FileKind.GRAPHQL) is gql_extract
    assert select(FileKind.OPENAPI) is openapi_extract
    # Migrations route to a SQL variant.
    assert select(FileKind.MIGRATION).__name__ == "extract_migration"
    assert select(FileKind.APPLICATION_CODE) is None
    assert select(FileKind.OTHER) is None


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------


def test_sql_extracts_table_and_foreign_key():
    text = """
    CREATE TABLE customer (
        id INTEGER PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL
    );

    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER REFERENCES customer(id),
        total INTEGER NOT NULL
    );
    """
    result = sql_extract("schema.sql", text)
    sections = {f.section_id for f in result.findings}
    assert "entities" in sections
    assert "integrations" in sections
    findings_by_section = {s: [f for f in result.findings if f.section_id == s] for s in sections}
    # Both tables surface as entities.
    entity_findings = findings_by_section["entities"]
    assert any("customer" in f.finding for f in entity_findings)
    assert any("orders" in f.finding for f in entity_findings)
    # FK becomes an integration.
    fk_findings = findings_by_section["integrations"]
    assert any("customer" in f.finding for f in fk_findings)


def test_sql_migration_marks_summary():
    text = "ALTER TABLE orders ADD COLUMN refund_status TEXT;"
    from wikifi.specialized.sql import extract_migration

    result = extract_migration("backend/migrations/0042_refunds.sql", text)
    assert "Migration" in result.summary or "migration" in result.summary.lower()
    assert any("orders" in f.finding for f in result.findings)


def test_sql_index_becomes_cross_cutting():
    text = "CREATE INDEX idx_orders_customer ON orders (customer_id);"
    result = sql_extract("schema.sql", text)
    assert any(f.section_id == "cross_cutting" and "idx_orders_customer" in f.finding for f in result.findings)


# ---------------------------------------------------------------------------
# OpenAPI
# ---------------------------------------------------------------------------


def test_openapi_extracts_endpoints_and_schemas_from_json():
    spec = """
    {
      "openapi": "3.0.0",
      "info": {"title": "Orders API", "version": "1.0"},
      "paths": {
        "/orders": {
          "post": {"summary": "Create order"},
          "get": {"summary": "List orders"}
        }
      },
      "components": {
        "schemas": {"Order": {"type": "object"}, "LineItem": {"type": "object"}},
        "securitySchemes": {"bearerAuth": {"type": "http"}}
      }
    }
    """
    result = openapi_extract("openapi.json", spec)
    sections = {f.section_id for f in result.findings}
    assert "intent" in sections
    assert "capabilities" in sections
    assert "entities" in sections
    assert "integrations" in sections
    assert "cross_cutting" in sections
    cap_text = next(f.finding for f in result.findings if f.section_id == "capabilities")
    assert "POST /orders" in cap_text
    assert "GET /orders" in cap_text


def test_openapi_handles_unparseable_input():
    result = openapi_extract("openapi.yaml", "")
    assert any(f.section_id == "capabilities" for f in result.findings)
    assert "Unparseable" in result.summary or "manual review" in result.findings[0].finding.lower()


def test_openapi_yaml_fallback_parser():
    """The shallow YAML parser should work even without PyYAML installed."""
    spec = """openapi: 3.0.0
info:
  title: Test API
  version: "1.0"
paths:
  /test:
    get:
      summary: Test endpoint
"""
    result = openapi_extract("openapi.yaml", spec)
    # Should at least extract intent (title is present).
    assert any("Test API" in f.finding for f in result.findings)


# ---------------------------------------------------------------------------
# Protobuf
# ---------------------------------------------------------------------------


def test_proto_extracts_messages_and_services():
    text = """
    syntax = "proto3";
    package billing.v1;

    message Invoice {
      int64 id = 1;
      string customer_id = 2;
    }

    service BillingService {
      rpc CreateInvoice (Invoice) returns (Invoice);
      rpc StreamInvoices (Invoice) returns (stream Invoice);
    }
    """
    result = proto_extract("billing.proto", text)
    sections = {f.section_id for f in result.findings}
    assert "entities" in sections
    assert "integrations" in sections
    assert "capabilities" in sections
    integrations = next(f for f in result.findings if f.section_id == "integrations")
    assert "BillingService" in integrations.finding
    assert "CreateInvoice" in integrations.finding


# ---------------------------------------------------------------------------
# GraphQL
# ---------------------------------------------------------------------------


def test_graphql_extracts_types_and_roots():
    sdl = """
    type Order {
      id: ID!
      total: Int!
    }

    input OrderInput {
      total: Int!
    }

    type Query {
      order(id: ID!): Order
    }

    type Mutation {
      createOrder(input: OrderInput!): Order!
    }
    """
    result = gql_extract("schema.graphql", sdl)
    sections = {f.section_id for f in result.findings}
    assert "entities" in sections
    assert "capabilities" in sections
    cap = next(f for f in result.findings if f.section_id == "capabilities")
    assert "Query" in cap.finding or "Mutation" in cap.finding
