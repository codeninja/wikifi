# Domains and Subdomains

## Core Domain

The system's core domain is **codebase knowledge extraction**: reasoning about an arbitrary repository's structure, intent, and behaviour, then representing that understanding as a technology-agnostic, human-readable wiki. The domain is explicitly decoupled from any recognition of specific languages, frameworks, or runtimes — tech-agnosticism is a first-class constraint enforced at the analysis level, not merely a presentation concern.

## Primary Subdomains

### Repository Introspection
This subdomain covers the initial act of understanding a repository: discovering which paths exist, classifying files by kind, resolving import relationships, and deciding which parts of the codebase encode genuine business intent versus infrastructure or tooling noise. The output is a curated inclusion set that drives all downstream work.

### Per-File Knowledge Extraction
Operating over the inclusion set produced by introspection, this subdomain extracts intent-bearing findings from individual source files, organised by wiki section. It encompasses caching and memoisation of extraction results, cross-file context derived from the import graph, and chunk-level deduplication to prevent redundant evidence.

### Documentation Synthesis
This subdomain aggregates per-file findings into coherent wiki sections and then derives higher-level artifacts (narrative summaries, personas, diagrams) from those aggregates. A critical design constraint enforced structurally is the **dependency ordering** between primary evidence extraction and derivative synthesis: derivative sections may only consume content that primary sections have already produced.

## Secondary Subdomains

| Subdomain | Responsibility |
|---|---|
| **Provider Abstraction** | Decouples extraction and synthesis intelligence from any specific inference backend, allowing local and hosted providers to be swapped without altering the pipeline. |
| **Wiki Authoring & Organisation** | Governs how extracted knowledge is structured, stored on the filesystem, and made navigable for consumers such as migration teams. |
| **Interactive Knowledge Retrieval** | Supports on-demand querying of the generated wiki, enabling a conversational interface over the accumulated knowledge base. |

## Domain Relationships

Repository Introspection feeds Per-File Extraction, which in turn feeds Documentation Synthesis — forming a directed, stage-ordered pipeline. Provider Abstraction is a horizontal supporting concern that all three primary subdomains depend on. Wiki Authoring & Organisation governs the output representation consumed by Interactive Knowledge Retrieval. Quality assurance of generated content is an ancillary concern cross-cutting the extraction and synthesis stages.

## Supporting claims
- The core domain is codebase knowledge extraction: reasoning about an arbitrary repository's structure, intent, and behaviour and representing that understanding as a technology-agnostic wiki. [1][2][3][4]
- Tech-agnosticism is a first-class constraint at the analysis level, not merely a presentation concern. [5]
- The repository introspection subdomain covers discovering and classifying files, resolving import relationships, and deciding which parts of a codebase encode business intent versus infrastructure or tooling. [1][6][5]
- The per-file knowledge extraction subdomain extracts intent-bearing findings per wiki section, and encompasses caching/memoisation, import-graph-based cross-file context, and chunk-level deduplication. [1][3]
- The documentation synthesis subdomain aggregates per-file findings into wiki sections and derives higher-level artifacts such as narrative summaries, personas, and diagrams. [1][4][7]
- The dependency ordering between primary evidence extraction and derivative synthesis is a first-class design constraint enforced structurally. [7]
- Provider abstraction is a secondary domain that decouples extraction intelligence from any specific inference backend. [8]
- Wiki authoring and organisation is a secondary domain governing how extracted knowledge is structured and stored for consumption by a migration team. [2]
- Interactive knowledge retrieval against the generated wiki is a supporting subdomain. [6]

## Sources
1. `README.md:32-55`
2. `VISION.md:3-20`
3. `wikifi/extractor.py`
4. `wikifi/orchestrator.py:1-16`
5. `wikifi/introspection.py:19-44`
6. `wikifi/cli.py:1-8`
7. `wikifi/sections.py:1-19`
8. `README.md:57-63`
