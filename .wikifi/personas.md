# User Personas

Three distinct personas emerge from the aggregate of capabilities, integrations, and stated intent. Each is grounded in what the system demonstrably does; roles the upstreams are silent on are noted as gaps at the end.

---

## Persona 1 — The Onboarding Developer

> *"I have inherited a large codebase I did not write. I need to understand what it does before I can safely change it."*

### Profile
A developer who joins a project mid-life and must build a mental model of an unfamiliar system. The codebase may be a long-lived monorepo where operational knowledge is scattered across files and never captured as coherent documentation.

### Goals
- Quickly form an accurate picture of what the system accomplishes for its users.
- Navigate cross-module flows without reading every file individually.
- Ask follow-up questions when the static documentation raises new ones.

### Needs
| Need | How the system addresses it |
|---|---|
| Intent over implementation | Wiki describes what the system does, not how it is built, so the developer's mental model survives future technology changes |
| Cross-module flow descriptions | The cross-file reference graph is consulted per file so findings describe flows between modules rather than treating each file in isolation |
| Trustworthy claims | Every assertion is anchored to a specific source file and line range, so the developer can verify any claim without trusting unsourced documentation |
| Interactive clarification | An interactive conversational session grounded in the wiki content supports multi-turn questions, with only fully populated sections included to prevent placeholder content from diluting answers |

### Pain Points
- Sheer volume of source material makes manual review impractical.
- Existing documentation, where it exists, describes implementation rather than intent.
- Tribal knowledge is hidden in inconsistencies scattered across files.

### Primary Use Cases
- Reading primary wiki sections (domains, intent, capabilities, entities) to build an initial model.
- Querying the interactive chat session to chase down specific flows or clarify ambiguous sections.
- Reviewing contradiction blocks to understand where the source itself is inconsistent, rather than receiving a silently resolved answer.

---

## Persona 2 — The Migration Lead or Architect

> *"Before I can scope this re-implementation, I need to know the analysis covered the full system and that the resulting wiki is trustworthy enough to act on."*

### Profile
A technical decision-maker — lead architect, principal engineer, or programme manager — who must scope, fund, or execute a re-implementation of a legacy system. They are not reading the source themselves; they are reading the wiki as the evidentiary basis for consequential decisions.

### Goals
- Confirm that the analysis walk covered the full system, not just the easy-to-parse parts.
- Verify that every claim in the wiki can be traced back to a specific source location.
- Identify where the source itself contains contradictions that a migration team will need to resolve.
- Assess documentation quality before committing to use the wiki as migration input.

### Needs
| Need | How the system addresses it |
|---|---|
| Coverage assurance | A coverage and quality report summarises, per section, how many files contributed findings and how complete the analysis was |
| Traceability | Every wiki assertion is rendered with inline citation markers linked to a numbered source footer; any claim can be traced to the originating file and line range |
| Contradiction visibility | Where two or more sources assert incompatible things, the system surfaces an explicit conflict block rather than silently reconciling the disagreement |
| Quality scoring | An optional critic-and-reviser cycle scores section bodies against a structured rubric, producing per-section quality scores and unsupported-claim flags alongside an overall mean score |
| Technology agnosticism | Observations are expressed in domain terms, keeping the wiki legible and actionable even when the underlying technology stack is replaced entirely |

### Pain Points
- Cannot act on documentation that lacks a verifiable source — any unsourced claim introduces risk into a re-implementation plan.
- A partial analysis walk that silently skips complex or malformed files produces a false sense of completeness.
- Silent conflict resolution hides exactly the ambiguities a migration team most needs to know about.

### Primary Use Cases
- Running or reviewing a quality report (with the critic loop enabled) before sign-off.
- Inspecting the coverage report to confirm file contribution counts per section.
- Using contradiction blocks as an explicit work-item list for the migration team.
- Reviewing derivative sections (personas, user stories, diagrams) synthesized from the aggregated primaries.

---

## Persona 3 — The Legacy System Maintainer

> *"The system keeps changing. I cannot afford to rewrite the documentation by hand every time, and I need to know when something has gone inconsistent."*

### Profile
A developer or small team responsible for keeping a production system running over months or years. The codebase changes continuously; documentation written at one point in time drifts out of date and becomes a liability rather than an asset.

### Goals
- Keep the wiki accurate as the codebase evolves, without manual documentation effort.
- Know when a recent change has introduced an inconsistency.
- Avoid paying the full analysis cost on every run when only a small part of the codebase changed.

### Needs
| Need | How the system addresses it |
|---|---|
| Automated currency | The system re-analyses changed files on each run without any manual authoring |
| Incremental efficiency | Only files whose content has changed are re-processed; unchanged sections are served from cache; a run in which nothing has changed is a complete no-op |
| Surgical preservation | When only a small subset of findings changes, targeted in-place edits preserve established prose, citation numbering, and unaffected paragraphs verbatim |
| Inconsistency surfacing | Contradiction blocks make newly introduced conflicts visible immediately after the next run |
| Crash resilience | Cache state is persisted after each file, so a crash at any stage resumes from the last completed file rather than restarting from scratch; malformed files are flagged for manual review rather than halting the run |

### Pain Points
- Full rewrites of documentation on every run would erase carefully reviewed prose and reset citation numbering.
- A pipeline that halts on a single unparseable file blocks the entire team.
- Re-running a full analysis on a large codebase just because one file changed is economically and practically unacceptable.

### Primary Use Cases
- Scheduling incremental re-runs after code merges to keep the wiki current.
- Reviewing the post-run report to spot newly surfaced contradictions or newly empty sections.
- Checking flagged files that could not be parsed to decide whether manual review is warranted.

---

## Persona 4 — The Pipeline Operator

> *"This needs to run in an automated environment. I cannot babysit it, and it must not modify content during a reporting pass."*

### Profile
An engineer or team responsible for integrating wiki generation into an automated workflow — for example, a scheduled job that runs after each significant merge. They interact with the system primarily through the command-line interface and configuration, not through the interactive chat.

### Goals
- Run the full pipeline unattended without human intervention.
- Swap the inference backend without changing any pipeline logic.
- Control cost by governing which provider is active and whether prompt caching is used.
- Ensure the reporting pass does not modify any wiki content (making it safe for automated pipelines).

### Needs
| Need | How the system addresses it |
|---|---|
| Single entry point | The command-line interface is the sole external entry point; it delegates entirely to internal modules and contains no domain logic |
| Layered configuration | Configuration is resolved from a per-target config file, environment variables, and built-in defaults in strict precedence order, so each analysed repository can drive its own settings |
| Backend flexibility | The inference backend is selected at runtime via configuration; the abstract provider contract means swapping backends requires no pipeline changes |
| Cost control | Prompt-cache reuse and adaptive reasoning modes make large-scale walks economically viable; the operator can tune these via settings |
| Safe reporting | The reporting pass reads wiki content and notes without modifying them, making it safe to run in automated pipelines |
| Graceful degradation | Synthesis failures preserve raw extracted notes rather than producing blank sections; the run always yields some output |

### Pain Points
- A backend that cannot be swapped creates vendor lock-in at the infrastructure level.
- Calling a hosted inference service for hundreds of per-file passes without cost controls would be cost-prohibitive.
- A pipeline that produces blank sections or halts on failure cannot be trusted in an automated context.

### Primary Use Cases
- Configuring and scheduling unattended wiki generation runs.
- Selecting and rotating inference backends via configuration.
- Reviewing the walk report and coverage statistics as pipeline outputs rather than as interactive documents.

---

## Gaps

The upstream sections are silent on the following potential audiences. These personas cannot be inferred from the available evidence and are declared here as gaps rather than invented:

- **End users of the documented system** — the wiki describes what the system does for its users, but those end users are not themselves users of the wiki-generation system as described in the upstreams.
- **Product managers or business stakeholders** — no upstream section describes non-technical readers consuming the generated wiki for product-level decision-making.
- **Security or compliance reviewers** — no upstream section describes use of the wiki for audit, compliance, or security assessment purposes.
