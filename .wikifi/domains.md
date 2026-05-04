# Domains and Subdomains

## Core Domain

The system's core domain is **automated documentation generation**: transforming a living source repository into a structured, intent-oriented wiki that captures the business and design meaning of a codebase — not just its surface syntax.

## Subdomains

The core domain decomposes into four identifiable subdomains, each with a distinct responsibility boundary.

### Repository Analysis
Responsible for introspecting a source repository: discovering which files exist, understanding their structure, and making their content available for downstream processing. This subdomain is upstream of all others; its output is the raw material the rest of the system consumes.

### Extraction
Responsible for reading individual source artifacts and producing classified, section-oriented findings — structured observations about intent, behaviour, and design that are traceable back to specific source locations. Extraction operates file-by-file and produces the evidence base on which synthesis depends.

### Evidence Synthesis (Aggregation)
Responsible for elevating file-scoped findings into section-scoped narratives. It merges consistent observations, surfaces contradictions explicitly, and attaches traceable provenance to every claim it emits. This subdomain is the epistemic heart of the system: it is where raw notes become authoritative, citeable knowledge.

### Wiki Management
Responsible for governing how the system persists its artefacts — configuration, per-section markdown, extraction notes, and caches — within the target project. This is a generic, infrastructural subdomain: it provides stable storage contracts that the other subdomains depend on without concern for analysis or synthesis logic.

## Subdomain Relationships

| Subdomain | Type | Depends On | Feeds Into |
|---|---|---|---|
| Repository Analysis | Supporting | — | Extraction |
| Extraction | Supporting | Repository Analysis | Evidence Synthesis |
| Evidence Synthesis | Core | Extraction, Wiki Management | Wiki Management |
| Wiki Management | Generic | — | All others (storage) |

Repository Analysis and Extraction together constitute what can be called the **codebase analysis** half of the system. Evidence Synthesis and the human-facing output it produces constitute the **knowledge management** half. The orchestration layer is the explicit seam that wires these two halves together end-to-end.

## Supporting claims
- The system's core domain is automated documentation generation from source repositories. [1][2][3][4]
- Repository Analysis is a supporting subdomain responsible for introspecting the structure and content of source code. [4]
- Extraction is a supporting subdomain that transforms raw source text into classified, section-oriented, citeable findings. [3]
- Evidence Synthesis is the core subdomain that elevates file-scoped observations into section-scoped narratives with traceable provenance and explicit conflict records. [1]
- Wiki Management is a generic subdomain governing the on-disk storage of configuration, section markdown, extraction notes, and caches within the target project. [5]
- The system can be divided into two interacting halves: codebase analysis and knowledge management, with an orchestration layer acting as the seam between them. [2][4]

## Sources
1. `wikifi/aggregator.py:1-17`
2. `wikifi/cli.py:1-9`
3. `wikifi/extractor.py:1-15`
4. `wikifi/orchestrator.py:1-27`
5. `wikifi/wiki.py:1-15`
