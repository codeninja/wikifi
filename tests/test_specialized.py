"""Type-aware (specialized) extractor tests."""

from __future__ import annotations

from wikifi.repograph import FileKind
from wikifi.specialized.dispatch import select
from wikifi.specialized.graphql import extract as gql_extract
from wikifi.specialized.openapi import extract as openapi_extract
from wikifi.specialized.protobuf import extract as proto_extract
from wikifi.specialized.sql import extract as sql_extract


def test_select_routes_known_kinds_to_extractors():
    assert select(FileKind.SQL) is sql_extract
    assert select(FileKind.PROTOBUF) is proto_extract
    assert select(FileKind.GRAPHQL) is gql_extract
    assert select(FileKind.OPENAPI) is openapi_extract
    # SQL-shaped migrations route to the SQL migration variant.
    sql_mig = select(FileKind.MIGRATION, rel_path="db/migrations/0042_orders.sql")
    assert sql_mig is not None
    assert sql_mig.__name__ == "extract_migration"
    # Python / JS / Ruby migrations stay on the LLM path — the SQL
    # parser would silently produce empty findings on real code.
    assert select(FileKind.MIGRATION, rel_path="alembic/versions/0001_init.py") is None
    assert select(FileKind.MIGRATION, rel_path="db/migrate/20260501_add_users.rb") is None
    assert select(FileKind.MIGRATION, rel_path="db/migrations/001-add-users.js") is None
    # Without a rel_path the dispatcher can't tell SQL from non-SQL —
    # err on the safe side and return ``None``.
    assert select(FileKind.MIGRATION) is None
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


def test_graphql_extract_handles_extend_type_query(tmp_path):
    """`extend type Query` blocks contribute to the capabilities section.

    Modular GraphQL schemas split root types across files; if the
    extractor only matched bare `type Query { ... }` declarations,
    capabilities would silently disappear for any schema composed from
    multiple files.
    """
    sdl = """
    type Order {
      id: ID!
    }

    extend type Query {
      orderById(id: ID!): Order
    }

    extend type Mutation {
      cancelOrder(id: ID!): Boolean!
    }
    """
    result = gql_extract("schema.graphql", sdl)
    capabilities = [f for f in result.findings if f.section_id == "capabilities"]
    assert any("orderById" in f.finding for f in capabilities)
    assert any("cancelOrder" in f.finding for f in capabilities)


def test_graphql_block_after_handles_indented_closing_brace():
    """`_block_after` must stop on indented `}` lines, not just column-0 ones.

    Many SDL formatters indent the closing brace; the previous
    column-0-only check would let the scan run into subsequent type
    declarations, polluting the root field list with unrelated fields.
    """
    sdl = """
    type Query {
      orderById(id: ID!): Order
      listOrders: [Order!]!
    }

    type SecretOps {
      shouldNotAppear: String!
    }
    """
    result = gql_extract("schema.graphql", sdl)
    capabilities = next(f for f in result.findings if f.section_id == "capabilities")
    assert "orderById" in capabilities.finding
    assert "listOrders" in capabilities.finding
    assert "shouldNotAppear" not in capabilities.finding


def test_proto_scopes_rpcs_to_owning_service():
    """Multiple `service` blocks: each owns only its own RPCs.

    The previous scope ("every RPC at or after my line") attributed
    every later service's RPCs to the first service, inflating the
    integration inventory whenever a proto file declared more than one.
    """
    text = """
    service AccountsService {
      rpc CreateAccount (CreateAccountRequest) returns (Account);
    }

    service BillingService {
      rpc ChargeAccount (ChargeRequest) returns (Receipt);
      rpc Refund (RefundRequest) returns (Receipt);
    }
    """
    result = proto_extract("svc.proto", text)
    integrations = {f.finding.split("\n", 1)[0]: f.finding for f in result.findings if f.section_id == "integrations"}
    accounts_finding = next(v for k, v in integrations.items() if "AccountsService" in k)
    billing_finding = next(v for k, v in integrations.items() if "BillingService" in k)

    assert "CreateAccount" in accounts_finding
    assert "ChargeAccount" not in accounts_finding
    assert "Refund" not in accounts_finding

    assert "ChargeAccount" in billing_finding
    assert "Refund" in billing_finding
    assert "CreateAccount" not in billing_finding


def test_sql_migration_with_only_alter_counts_altered_tables():
    """An ALTER-only migration reports its altered targets, not 0 tables.

    Prior to the fix the summary counted only CREATE TABLE matches, so
    a migration that only ALTERs existing tables was reported as
    "Migration touches 0 table(s)" even though it had real targets.
    """
    from wikifi.specialized.sql import extract_migration

    text = """
    ALTER TABLE orders ADD COLUMN refund_status TEXT;
    ALTER TABLE customers ADD COLUMN tier TEXT;
    """
    result = extract_migration("backend/migrations/0042_alter.sql", text)
    assert "0 table" not in result.summary
    assert "2 table" in result.summary
