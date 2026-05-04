# User Personas

Three primary personas are named explicitly in the upstream content, and a fourth is strongly implied by the operational surface the system exposes. Each is described below with goals, needs, pain points, and the system capabilities that serve them.

---

## Persona 1 — The Systems Architect

**Who they are.** A senior technical authority responsible for understanding what a large or legacy codebase actually does, independent of how it was implemented. They are typically engaged early in a migration or re-implementation programme to produce an auditable record of system behaviour.

### Goals
- Produce a technology-agnostic, citable account of the system's domain intent, entities, and contracts.
- Identify areas where the codebase contradicts itself — schema definitions that diverge from application usage, contracts defined one way and consumed another.
- Verify that the resulting documentation is grounded in source evidence, not paraphrased from memory or tribal knowledge.

### Needs
- **Full traceability** — every claim in the generated wiki must be traceable to a specific file and line range so the architect can verify any assertion against the original codebase.
- **Explicit contradiction surfacing** — disagreements between source files must be visible, not silently merged; these are high-priority signals marking undocumented behaviour and accumulated drift.
- **Technology-agnostic output** — the wiki must be expressed in domain terms so the architect can reason about system behaviour without knowledge of the implementation language or runtime.

### Pain points
- Manually reading a large repository (potentially tens of thousands of files) to extract domain intent is prohibitively slow and error-prone.
- Implicit knowledge encoded in the shape of data models, API contracts, and schema migrations is the hardest kind to recover and the most important for migration.
- Without structured citations, any documentation produced cannot be trusted or audited.

### Use cases served
- Initiating a full pipeline run to generate the primary wiki sections (business domains, system intent, capabilities, external dependencies, integrations, cross-cutting concerns, core entities, hard specifications).
- Reviewing generated sections with citation markers to trace any assertion back to its source file and line range.
- Inspecting surfaced contradictions to identify where the codebase has drifted from its intended contracts.
- Consulting the interactive chat mode to ask precise questions about system behaviour, knowing answers are grounded in wiki content rather than invented.

---

## Persona 2 — The Migration Lead

**Who they are.** A programme or delivery lead who must decide whether a re-implementation project is ready to proceed. They are not necessarily reading the generated wiki in detail; they need to answer two specific gate questions before committing resources.

### Goals
- Determine whether the entire codebase was covered by the analysis — no significant portion silently excluded.
- Determine whether the resulting wiki is complete and reliable enough to act on as a specification for re-implementation.

### Needs
- **Coverage statistics** — total files analysed, files with at least one finding, per-section finding and contributing-file counts.
- **Quality scores** — an overall floating-point quality score and per-section integer scores (0–10) with summaries of unsupported claims and gaps.
- **Gap reporting** — explicit identification of sections that are empty or under-evidenced, so the lead can decide whether to accept the gap or request additional analysis.

### Pain points
- Without a structured report, it is impossible to know whether the pipeline covered the whole codebase or silently skipped significant portions.
- Qualitative assurances about documentation completeness are not fundable; numeric coverage and quality metrics are.
- A wiki that looks complete but contains speculative or unsupported claims is worse than a wiki that declares its gaps explicitly.

### Use cases served
- Running the report command to obtain the `WikiReport` and `WikiQualityReport`, including overall and per-section quality scores and coverage statistics.
- Reviewing the critic-generated lists of unsupported claims and suggested edits to assess the risk of acting on the current documentation state.
- Using the coverage percentage (files-with-findings divided by total files) from the quality-review subsystem to determine whether the analysis was sufficiently comprehensive.

---

## Persona 3 — The Re-implementation Engineer

**Who they are.** A developer working on the re-implementation project who needs authoritative, precise answers about the behaviour of the existing system — without reading every source file themselves.

### Goals
- Get fast, accurate answers to specific questions about system behaviour, entity contracts, and integration touchpoints.
- Understand what the existing system's API surface, data schemas, and event streams look like, expressed in domain terms they can target in the new implementation.
- Identify any known contradictions or gaps in the documentation before writing code that depends on an assumption.

### Needs
- **Interactive query access** — a conversational interface that answers questions grounded in the wiki content, acknowledging gaps rather than inventing answers.
- **Structured entity and contract documentation** — clear descriptions of core entities, foreign-key couplings, HTTP endpoints, remote-procedure-call operations (with request/response types and streaming directions), and real-time subscription surfaces.
- **Traceable, non-speculative claims** — any assertion the engineer relies on must be verifiable against the source codebase.

### Pain points
- Reading tens of thousands of source files to find the answer to a single domain question is impractical.
- Documentation that silently fills gaps with plausible-sounding but unsupported assertions causes implementation errors that are expensive to fix.
- Contract information spread across schema files, API specifications, and application logic is inconsistent in legacy systems; engineers need to know where disagreements exist before designing the replacement.

### Use cases served
- Using the chat REPL (the `chat` command) to ask targeted questions about entity relationships, API contracts, integration touchpoints, and business rules, receiving answers grounded in loaded wiki sections.
- Reading the entities section to understand the domain object model and the integrations section to understand inbound and outbound contract surfaces.
- Reviewing surfaced contradictions to understand where the existing system's behaviour is ambiguous before encoding assumptions into the re-implementation.

---

## Persona 4 — The Pipeline Operator

**Who they are.** A technically proficient practitioner — often an architect, a senior engineer, or a platform engineer — responsible for configuring, running, and maintaining the analysis pipeline against the target repository. This persona is implied by the breadth of operational controls the system exposes: provider selection, model configuration, caching behaviour, incremental update strategies, and the multi-command CLI surface.

### Goals
- Initialise and run the pipeline reliably against large repositories without incurring prohibitive cost or latency.
- Keep the generated wiki up to date incrementally as the source repository evolves, without triggering full re-analysis of unchanged files.
- Configure the pipeline appropriately for the environment: provider selection (hosted or on-premises), model identity, file-size thresholds, chunk sizes, and feature flags.

### Needs
- **Incremental caching** — content-addressed caching that skips unchanged files on re-runs, reducing hours-long full walks to minutes-long incremental updates; surgical editing that patches only the affected portions of cached prose.
- **Provider flexibility** — the ability to select among multiple AI backends (hosted options or a fully on-premises local model service) without changing pipeline behaviour.
- **Operational visibility** — structured run statistics (files seen, cache hits, sections written, sections surgically edited, sections served from cache) to understand what the pipeline did and at what cost.

### Pain points
- AI-backed analysis of large repositories is inherently expensive; without caching and incremental strategies the cost is prohibitive at scale.
- Switching AI backends for cost, latency, or data-residency reasons should not require changes to the pipeline logic.
- Without operational metrics it is impossible to diagnose why a run was slow, expensive, or incomplete.

### Use cases served
- Running the `init` command to create the browsable wiki stub before any analysis runs, making the structure available regardless of pipeline state.
- Running the `walk` command to execute the four-stage pipeline (introspection → extraction → aggregation → derivation), with caching and incremental update behaviour governed by settings.
- Configuring provider identity, model, inference endpoint, request timeout, chunk sizes, and feature flags (caching, graph construction, specialised extractors, review loop, surgical edits) via the layered settings model.
- Monitoring `WalkReport` and `AggregationStats` / `DerivationStats` outputs to understand run coverage, cache efficiency, and section-level outcomes.

---

## Persona–Capability Matrix

| Capability | Architect | Migration Lead | Engineer | Operator |
|---|:---:|:---:|:---:|:---:|
| Four-stage wiki generation pipeline | ✓ | | | ✓ |
| Per-claim citation markers and source traceability | ✓ | | ✓ | |
| Explicit contradiction surfacing | ✓ | ✓ | ✓ | |
| Interactive chat (grounded Q&A) | ✓ | | ✓ | |
| Coverage and quality reporting | | ✓ | | ✓ |
| Incremental caching and surgical updates | | | | ✓ |
| Specialised contract and schema extraction | ✓ | | ✓ | |
| Provider and model selection | | | | ✓ |
| Derivative content (personas, user stories, diagrams) | ✓ | ✓ | | |

---

> **Gap note.** The upstream sections do not describe any persona who consumes the generated wiki without also being involved in the migration programme (for example, a product owner or external auditor). If such a consumer exists, their needs are not evidenced in the current documentation and cannot be inferred from the available upstream content.
