# Vision

## Why wikify exists
Legacy systems are hard to migrate because the **intent** of the code is locked inside its implementation choices. A team lifting a legacy project into a modern microservice-oriented architecture needs more than a repo — they need a description of *what the system does and why*, decoupled from *how it currently does it*.

wikify produces that description. It walks a target codebase, uses an AI agent to hydrate domain knowledge per logical unit, and writes a **technology-agnostic** Notion wiki the target team can use to re-implement the system on a fresh stack from the wiki alone.

Once wikified as modular segregrated domain knowledge the wiki becomes the source of the new system's intent.

## Problem space
- Legacy projects encode tech-stack assumptions in their structure, naming, and integrations. A re-platforming team that follows the existing structure ends up recreating the legacy system in a new language. wikify frees the new team from that pull by capturing intent independently of the original implementation.
- A walking agent captures every section systematically — including the cross-cutting concerns hand-written specs typically gloss over.
- Walking the source mechanically scales across modules, repos, and packages; an agent walking with intent surfaces *why* the code does what it does, beyond just *what* it does.

wikify exists to make the intent of a legacy system **explicit, complete, and portable**.

## What every generated wiki captures
- **User personas** — AI Generated user personas with intent, needs, painpoints, usage patterns, and use cases.
- **User stories** - Feature mapped to a Gerkin style user storyies, with acceptance criteria.
- **DDD domains and subdomains** — the core business domains, subdomains, and their relationships as expressed in the codebase, without reference to current module boundaries or tech stack
- **Intent and problem space** — the "why" behind the system, in the system's own words, independent of the current implementation
- **What the application does and solves** — a domain-level description of the system's functionality, features, and value proposition, without reference to the current tech stack or architecture
- **External-system dependencies** — third-party APIs, services, infrastructure
- **Internal + external integrations** — touchpoints in both directions
- **Cross-cutting concerns** — observability, monitoring, data integrity, authentication & authorization, data storage
- **Core entities and their structures** - data structures, relationships, and patterns that define the system's domain model, independent of the current implementation. A definition of what the core entities needs are and how they relate to other entities. 
- **Hard specifications** — Critical requirements which must be carried forward.

These are not hard requirements, and the agent is free to identify and capture additional relevant information beyond this list. The goal is a comprehensive, technology-agnostic representation of the system's intent and problem space that empowers a new team to re-implement the system into one or more smaller services in a modern stack from the wiki alone.

## Interacting with the wiki
The wiki will have a CLI and MCP interface into 

## Scope boundary
wikify focuses on production functionality. 
The legacy project's existing test infrastructure stays out of scope, unless there is something truely remarkable about that test infrastructure that must be retained.
Wikify is not concerned with repo configuration, build pipelines or development tooling — only the production code and its intent.
Wikify is not a code translation tool. It is a system wide feature discovery and documentation tool.

## Success criteria
A migration team handed only the wiki wikify produces — working from the wiki alone — can deliver a microservice re-implementation that preserves the original system's personas, problem space, integrations, cross-cutting concerns, entities, and data patterns.

## Open design questions
Intent-level decisions still to resolve. Surface each at planning time so the choice is explicit.

- **"Notion in Docker"** — official Notion SaaS API with a containerized client, or a self-hosted Notion-like alternative (Outline / AppFlowy / Wiki.js) running locally?
- **Project-boundary discovery** — heuristic detection (`pyproject.toml`, `package.json`, `Cargo.toml`, etc.) or explicit user configuration?
- **Token / target-page configuration** — interactive `wikify init` prompts, or `.env`-driven?
- **Polyglot scope** — Python-only at v1, or multi-language from the first release?
- **Notion-unavailable fallback** — markdown to disk, or hard-fail?
