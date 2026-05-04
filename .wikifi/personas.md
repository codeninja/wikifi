# User Personas

Four personas emerge from the aggregate of what the system does, the problems it is designed to solve, and the interaction surfaces it exposes. No persona is inferred from a single capability; each is grounded in the convergence of multiple upstream sections.

---

## Persona 1 — The Migration Planner

> *Leads or participates in the planned migration of a legacy system to a new architecture, organizational boundary, or technology set.*

The upstream Intent section names migration teams as the primary design audience. Every major architectural decision — evidence traceability, explicit conflict surfacing, technology-agnostic output, and a pre-migration coverage report — is framed in terms of what a migration team needs.

### Goals
- Establish a shared, authoritative understanding of what an existing system does *before* any changes are made.
- Identify hidden dependencies, integration touchpoints, and entity relationships that could break during migration.
- Determine whether the generated documentation is reliable enough to act on.

### Needs
| Need | System capability that serves it |
|---|---|
| Every claim traceable to a precise source location | SourceRef model with path and line-range citations on every Claim |
| Explicit surfacing of file-level contradictions | Contradiction entity; conflict-detection pipeline stage |
| Tech-agnostic output that survives a technology change | Domain-terms-only output enforced throughout the pipeline |
| Coverage assurance before migration begins | Read-only reporting capability (WikiReport, WikiQualityReport, CoverageStats) |
| Integration inventory of the target system | Specialized extractors surface HTTP endpoints, RPC services, event subscriptions, and foreign-key constraints |

### Pain Points
- Legacy codebases contain implicit, undocumented knowledge that lives only in engineers' heads.
- Naive documentation tools silently merge conflicting assertions, causing migration teams to inherit wrong assumptions.
- Documentation written in implementation terms becomes meaningless after the technology changes.

### Use Cases Served
- Running the full four-stage pipeline walk against the target repository.
- Reviewing surfaced contradictions and tracing each back to its originating source files.
- Using the pre-migration coverage report to verify that the walk reached all intent-bearing areas of the repository.
- Reading the integrations section to catalog external dependencies that must be preserved, replaced, or renegotiated.

---

## Persona 2 — The Onboarding Engineer

> *A software engineer who is new to a codebase and needs to build a working mental model quickly without reading tens of thousands of files.*

The Intent section explicitly identifies onboarding teams as a target audience. The conversational chat interface, cross-file import-graph enrichment, and the section structure covering entities, capabilities, and integrations all directly address the onboarding problem.

### Goals
- Build a coherent picture of domain entities, system capabilities, and integration points without a guided tour.
- Locate the code that actually matters — not scaffolding, build artifacts, or vendored dependencies.
- Ask targeted questions about unfamiliar parts of the system and get grounded, citable answers.

### Needs
| Need | System capability that serves it |
|---|---|
| Domain-level descriptions of each file's role | Per-file FileFindings with one-sentence role summary |
| Cross-file relationship context | Import-graph neighborhood injected into extraction prompts |
| Navigable, structured wiki | Eight primary sections plus derivative persona, user-story, and diagram sections |
| Interactive question-and-answer over the wiki | ChatSession grounded in populated wiki content; constrained to cite sections and admit gaps |

### Pain Points
- Raw source code communicates intent only to engineers already steeped in its conventions.
- Large repositories contain mostly scaffolding and build artifacts, making it hard to identify intent-bearing logic.
- There is no interactive way to ask targeted questions about the codebase without interrupting senior colleagues.

### Use Cases Served
- Reading generated wiki sections to understand the system's entities, capabilities, and external dependencies.
- Using the conversational interface (`chat` subcommand) to ask domain questions and receive answers that cite specific wiki sections.
- Following numbered citations in section narratives back to the originating source files to dive deeper.

---

## Persona 3 — The Non-Technical Stakeholder

> *A product owner, business analyst, or executive who needs to reason about a system's capabilities and risks without reading or interpreting code.*

The Intent section explicitly names stakeholders as an audience who must be able to reason about capability and risk. The technology-agnostic output constraint and the business-domains primary section exist precisely to serve this persona.

### Goals
- Understand what the system does at a domain level, in terms that do not require engineering background.
- Assess system capability and integration risk for planning, prioritization, or compliance purposes.

### Needs
| Need | System capability that serves it |
|---|---|
| Output free of implementation terminology | Tech-agnosticism enforced as a hard constraint across all pipeline stages |
| Business-level capability summary | Business domains and system intent as dedicated primary sections |
| Readable summary of external dependencies | Integrations section populated from specialized extractors |
| Ability to ask questions in plain language | Grounded conversational interface constrained to cite sections rather than invent answers |

### Pain Points
- Technical documentation is written for engineers and is impenetrable without prior context.
- There is no single, reliable source of truth about what a system does expressed in business terms.
- Asking engineers directly is time-consuming and produces inconsistent answers.

### Use Cases Served
- Reading the generated wiki sections covering business domains, system intent, and capabilities.
- Using the conversational interface to query specific capabilities or integration touchpoints in plain language.
- Sharing wiki output as a neutral artifact that communicates system scope across engineering and non-engineering audiences.

---

## Persona 4 — The Platform or Documentation Engineer

> *An engineer responsible for operating and maintaining the documentation pipeline across one or more projects, managing inference costs, and ensuring quality on repeated runs.*

The Capabilities section identifies low marginal effort on subsequent runs as a core value proposition. The caching model, quality-review loop, configurable provider selection, resumability, and per-project TOML configuration all point to an operator persona distinct from those who consume the output.

### Goals
- Keep documentation current with minimal re-processing cost on every repository change.
- Ensure that generated sections meet a defined quality bar before they are distributed or acted upon.
- Control inference costs across multiple projects with different size and sensitivity profiles.

### Needs
| Need | System capability that serves it |
|---|---|
| Incremental re-processing on repeated walks | Content-addressed cache (CachedFindings, CachedSection); only changed files trigger new inference calls |
| Recovery after interruption | Resumability as a direct by-product of the cache mechanism |
| Quality assurance with automatic revision | Critic/reviser loop; Critique and ReviewOutcome entities; configurable quality threshold |
| Cost control across provider types | Configurable provider selection (local-first default, hosted as explicit opt-in); prompt-caching for hosted providers |
| Per-project tuning | TOML configuration file per project; graceful fallback to environment-derived defaults on parse failure |
| Audit trail for a run | WalkReport carrying IntrospectionResult, ExtractionStats, AggregationStats, DerivationStats, and ReviewOutcomes |

### Pain Points
- Full re-generation on every repository change is prohibitively expensive for large codebases.
- Undetected hallucinations or unsupported claims in generated documentation create risk for downstream consumers.
- Different projects require different cost-quality trade-offs that a single global configuration cannot express.
- Mid-run failures on large repositories waste significant compute if the run cannot be resumed.

### Use Cases Served
- Configuring provider, model identity, caching behavior, feature flags, and quality threshold per project.
- Running repeated walks that leverage the cache and skip files whose content has not changed.
- Reviewing WikiQualityReport and per-section SectionReport outputs to verify coverage and quality before release.
- Tuning the quality threshold that triggers automatic section revision, balancing thoroughness against cost.
- Monitoring ExtractionStats and AggregationStats to understand pipeline efficiency across runs.

---

## Coverage Gap

The upstream sections are silent on whether any persona interacts with the system through an interface other than the command-line (`init`, `walk`, `chat`, `report` subcommands) or a direct filesystem read of the generated wiki. No web-based, API-based, or programmatic consumer persona is evidenced; any such persona would need to be inferred from sources not available in these upstreams.
