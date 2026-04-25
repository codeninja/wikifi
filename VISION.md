# Vision

## Why wikifi exists
Legacy systems are hard to migrate because the **intent** of the code is locked inside its implementation choices. A team lifting a legacy project into a modern microservice-oriented architecture needs more than a repo — they need a description of *what the system does and why*, decoupled from *how it currently does it*.

wikifi produces that description. It walks a target codebase, uses an AI agent to extract domain knowledge from the source, and writes a **technology-agnostic** wiki the target team can use to re-implement the system on a fresh stack from the wiki alone.

Once captured as modular, segregated domain knowledge, the wiki becomes the source of the new system's intent.

## Problem space
- Legacy projects encode tech-stack assumptions in their structure, naming, and integrations. A re-platforming team that follows the existing structure ends up recreating the legacy system in a new language. wikifi frees the new team from that pull by capturing intent independently of the original implementation.
- A walking agent captures every section systematically — including the cross-cutting concerns hand-written specs typically gloss over.
- Walking the source mechanically scales across modules, repos, and packages; an agent walking with intent surfaces *why* the code does what it does, beyond just *what* it does.

wikifi exists to make the intent of a legacy system **explicit, complete, and portable**.

## What every generated wiki conveys
The wiki must convey at least the following about the target system. Whether each item lives in its own file, rolls up under a parent, nests, or splits further is **at the implementor's discretion** — wikifi specifies *what* must be present, not the on-disk shape.

### Primary capture — extracted from direct evidence in the source
- **DDD domains and subdomains** — the core business domains, subdomains, and their relationships as expressed in the codebase, without reference to current module boundaries or tech stack.
- **Intent and problem space** — the "why" behind the system, in the system's own words, independent of the current implementation.
- **What the application does and solves** — a domain-level description of the system's functionality, features, and value proposition, without reference to the current tech stack or architecture.
- **External-system dependencies** — third-party APIs, services, infrastructure.
- **Internal + external integrations** — touchpoints in both directions.
- **Cross-cutting concerns** — observability, monitoring, data integrity, authentication & authorization, data storage.
- **Core entities and their structures** — data structures, relationships, and patterns that define the system's domain model, independent of the current implementation. A definition of what the core entities need are and how they relate to other entities.
- **Hard specifications** — critical requirements which must be carried forward.

### Derivative capture — synthesized from the aggregate after primary capture is complete
Some knowledge cannot be extracted from any single file — it emerges from the aggregate of what the system does. The implementation must produce these items in a step that runs *after* primary capture, taking the synthesized primary content as its input. They must never be inferred from a single source file.

- **User personas** — derived from the aggregate of capabilities, intent, entities, and integrations. AI-generated, with intent, needs, painpoints, usage patterns, and use cases.
- **User stories** — features expressed as Gherkin-style user stories with acceptance criteria, keyed to the personas above.
- **Diagrams** — visual representations of the system's domains, entities, and integrations, rendered from the aggregate; technology-agnostic.

These are not hard requirements, and the agent is free to identify and capture additional relevant information beyond this list. The goal is a comprehensive, technology-agnostic representation of the system's intent and problem space that empowers a new team to re-implement the system into one or more smaller services in a modern stack from the wiki alone.

## Storage
Stores wiki content in the target project's `.wikifi/` directory. Layout, taxonomy, and file structure within that directory are **at the implementor's discretion** — the contract is the *content* the wiki conveys, not its on-disk shape.

## Interacting with the wiki
The wiki will have a CLI interface. An MCP interface is in scope for a follow-up.

## Scope boundary
- wikifi focuses on production functionality.
- The legacy project's existing test infrastructure stays out of scope, unless there is something truly remarkable about it that must be retained.
- wikifi is not concerned with repo configuration, build pipelines, or development tooling — only the production code and its intent.
- **wikifi is a feature-extraction tool, not a transposition tool.** It surfaces what the legacy system does. It does not transform the source into the shape of any target architecture, target language, or target framework. The migration team owns that transposition; wikifi owns the description that informs it.

## Operational requirements
- **Local LLM by default.** The agent must run against a local LLM out of the box, with no cloud dependency required to wikify a codebase. Hosted backends are valid additional options, not the default.
- **Provider abstraction.** The implementation must reach the LLM through an abstraction layer so the backend can be swapped (local Ollama, hosted Anthropic, hosted OpenAI, custom) without changes outside the provider boundary.
- **Reasoning quality preferred over walk speed.** When the chosen model exposes a thinking / reasoning level, the agent runs at the highest available setting. wikifi prioritizes wiki quality over how long a walk takes.
- **Resilience to unstructured or near-empty input.** The walker must recognize and skip files that carry no extractable intent (stub `__init__` files, empty fixtures, generated lockfiles, and similar) before they reach the agent. A single empty or unstructured file must never stall the walk.

## Success criteria
A migration team handed only the wiki wikifi produces — working from the wiki alone — can deliver a microservice re-implementation that preserves the original system's personas, problem space, integrations, cross-cutting concerns, entities, and data patterns.
