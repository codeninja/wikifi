# User Personas

Two broad audiences are evident from the system's stated purpose and the capabilities built to serve them: **migration teams** who need portable domain knowledge extracted from a legacy codebase, and **knowledge consumers** who need to interrogate that knowledge without reading the source. A third role — the **wiki operator** — emerges from the pipeline management and quality-assurance capabilities. A fourth is implied by the interactive chat interface and the explicitly non-technical framing of the conversational output.

---

## Persona 1 — The Migration Architect

> *"I need to understand what this system does, not how it does it."*

### Profile
Leads the technical planning for a re-implementation or replacement of an inherited legacy system. Responsible for defining the scope and domain boundaries of the new system before any build work begins.

### Goals
- Recover the intent embedded in a legacy codebase independently of its current technology choices.
- Identify domain entities, capabilities, integration touchpoints, and cross-cutting concerns that must be preserved in the new system.
- Produce artefacts (diagrams, user stories, entity maps) that can brief the wider delivery team.

### Needs
- A technology-agnostic wiki that does not reproduce legacy structural decisions.
- Full traceability — every assertion must point back to a specific location in the source so claims can be verified.
- Explicit surfacing of contradictions in the source rather than silent resolution, since disagreements flag high-priority migration risks.
- Architectural diagrams and structured user stories derived automatically from the extracted knowledge.

### Pain Points
| Pain point | How the system addresses it |
|---|---|
| Reading legacy source directly tends to reproduce its structure in the new design | Output is expressed entirely in domain terms, never in technology-specific terms |
| Conflicting signals in different parts of the codebase are invisible | Contradictions are surfaced in a dedicated *Conflicts in source* block |
| Claims cannot be verified without re-reading the entire codebase | Every claim carries numbered citations to originating files and line ranges |
| No portable documentation exists to brief the wider team | Derivative sections produce Mermaid diagrams, Gherkin stories, and persona documents |

### Use Cases Served
- Full wiki generation from a legacy repository
- Review of the *Core Entities*, *Integrations*, and *Hard Specifications* sections
- Conflict review for migration risk prioritisation
- Sharing generated diagrams and user stories as briefing materials

---

## Persona 2 — The Migration Developer

> *"I need to understand a specific subsystem quickly and know which parts of the source back that up."*

### Profile
A developer on the migration team working at the implementation level. Inherits specific domain areas to re-implement and needs targeted, verifiable knowledge about those areas without reading the entire legacy codebase.

### Goals
- Understand the behaviour and boundaries of an assigned domain area.
- Trace any uncertainty back to the exact source location.
- Ask follow-up questions about the system without re-reading multiple files.

### Needs
- Per-section wiki bodies with inline citations.
- Cross-file flow descriptions that show how files and components interact, not just what each file does in isolation.
- An interactive conversational interface grounded in the full wiki for targeted queries.
- Resumable analysis so a large codebase can be processed incrementally and interrupted runs are not lost.

### Pain Points
| Pain point | How the system addresses it |
|---|---|
| Technical debt obscures the boundary between accidental and essential complexity | Technology-agnostic extraction separates domain behaviour from implementation noise |
| No way to ask targeted questions without reading source | Multi-turn chat session grounded in all populated wiki sections |
| Uncertainty about which source files are authoritative | Import and reference graph enriches findings with inter-file context; citations identify exact source spans |
| Repetitive re-runs on large repos are slow | Content-addressed cache replays unchanged file results; interrupted walks resume from the last processed file |

### Use Cases Served
- Querying the interactive chat session for specific domain questions
- Reading per-section markdown with source citations
- Reviewing cross-file flow descriptions produced by the reference graph enrichment
- Verifying claims against cited file locations and line ranges

---

## Persona 3 — The Domain Knowledge Consumer

> *"I need to understand what this system does, but I cannot read the source code."*

### Profile
A stakeholder — for example, a domain expert, product owner, or business analyst — who holds contextual knowledge about what the system is supposed to do but lacks the ability or time to read the codebase directly. May need to validate whether the extracted wiki accurately reflects business intent or to answer specific questions about system behaviour.

### Goals
- Gain a clear, jargon-free understanding of what the system does and why.
- Validate or challenge the extracted domain model against real-world business knowledge.
- Ask specific questions without requiring a technical intermediary.

### Needs
- Plain-language, technology-agnostic output that does not assume programming knowledge.
- A conversational interface for targeted questions rather than having to read structured markdown.
- Assurance that only populated, meaningful content is included in any context provided to the assistant.

### Pain Points
| Pain point | How the system addresses it |
|---|---|
| No readable documentation exists for the legacy system | The generated wiki is expressed in domain terms without implementation-specific language |
| Technical intermediaries are needed to answer basic questions about behaviour | The interactive chat session allows direct conversational querying of the wiki |
| Risk that the AI-generated summary does not reflect ground truth | Full traceability to source and explicit conflict surfacing allow domain experts to challenge assertions |

### Use Cases Served
- Reading generated wiki sections (particularly *Business Domains*, *System Intent*, and *User Personas*)
- Conducting multi-turn chat sessions to interrogate specific capabilities or entities
- Reviewing Gherkin-style user stories for business accuracy

---

## Persona 4 — The Wiki Operator

> *"I need to keep this wiki accurate, complete, and trustworthy as the codebase evolves."*

### Profile
A technical lead, DevOps engineer, or senior developer responsible for running and maintaining the wiki-generation pipeline over time. Focuses on pipeline health, analysis completeness, and quality assurance rather than consuming the wiki content directly.

### Goals
- Run and re-run the pipeline efficiently as the codebase changes.
- Monitor which areas of the codebase produced no useful findings (dead zones).
- Validate that generated sections meet a defined quality bar before the wiki is shared with the wider team.
- Configure the pipeline to match the constraints of the deployment environment (on-premise AI backend, private endpoints, exclusion patterns).

### Needs
- Coverage reports showing per-section file counts, finding counts, and body sizes.
- Identification of dead zones — files that were processed but produced no findings.
- A configurable quality threshold that triggers automatic revision when sections fall below it.
- Support for on-premise or privately hosted AI backends for air-gapped or data-sensitive environments.
- Idempotent workspace initialisation so re-runs do not overwrite existing work.

### Pain Points
| Pain point | How the system addresses it |
|---|---|
| Large repositories make full re-runs prohibitively slow | Two-scope content-addressed cache means only changed files and affected sections are reprocessed |
| Blind spots in the analysis go undetected | Coverage report surfaces dead zones and per-section gaps |
| Generated sections may introduce unsupported claims | Critic-and-reviser pass scores each section and auto-revises below a configurable threshold |
| Interrupted runs waste all completed work | Results are persisted after every completed file; walks resume from the last unprocessed file |
| Different deployment environments require different AI backends | Active backend is selected via environment variable or per-invocation flag; no pipeline code changes needed |

### Use Cases Served
- Running incremental and full wiki-generation pipelines
- Reviewing the coverage and quality report
- Configuring quality thresholds and exclusion patterns
- Selecting and overriding the AI backend for private or on-premise deployments
- Forcing cache invalidation when a clean re-walk is required

---

## Persona Summary

| Persona | Primary interaction | Core output consumed | Key system capability relied on |
|---|---|---|---|
| Migration Architect | CLI — full wiki generation | All eleven sections; diagrams; user stories | Tech-agnostic extraction; conflict surfacing; derivative section synthesis |
| Migration Developer | CLI + interactive chat | Per-section bodies with citations; chat responses | Cross-file context enrichment; conversational querying; incremental caching |
| Domain Knowledge Consumer | Interactive chat; generated markdown | Plain-language wiki sections; Gherkin stories | Conversational session; technology-agnostic output |
| Wiki Operator | CLI — pipeline management and reporting | Coverage and quality reports | Incremental walks; dead zone detection; critic-and-reviser pass; backend configuration |

> **Coverage note:** The upstream sections do not describe any end-user of the *target* legacy system as an audience for wikifi itself. All personas above are consumers of the extraction tool and its outputs, not of the system being analysed.
