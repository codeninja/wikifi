# Domains and Subdomains

The system is organized around a single **core domain**: automated codebase documentation — the systematic transformation of a living software repository into a structured, technology-agnostic wiki that is kept coherent as the codebase evolves.

Within that core domain, five supporting subdomains have been identified.

---

### Codebase Analysis

This subdomain is responsible for reading every source file and producing structured, section-aligned findings. It breaks into two tightly coupled concerns:

- **File Classification** — assigning each file a semantic kind (e.g., schema definition, migration script, API contract, or general prose). Path-level disambiguation handles ambiguous files.
- **Knowledge Extraction** — consuming the classification to select the appropriate reading strategy (a specialized structured extractor or a general prose extraction path), then producing normalized findings for each predefined wiki section.

### Source Traceability

This subdomain bridges raw analysis and the human-readable wiki. Every claim written into a section must be anchored to a precise location in the source code. The subdomain also surfaces contradictions — cases where two sources make incompatible assertions about the same topic — so that the final wiki reflects genuine uncertainty rather than silent resolution.

### Incremental Content Maintenance

When the underlying evidence for a section changes, this subdomain decides how much of the previously synthesized content to preserve. It models the decision as a three-way classification — **unchanged**, **surgical** (small targeted edits), or **rewrite** (full regeneration) — driven by a churn ratio derived from the delta in the finding set.

### Wiki Persistence

This subdomain owns the authoritative on-disk representation of the wiki: directory naming and layout conventions, idempotent scaffolding, and all read/write operations against section bodies, per-file extraction notes, configuration, and the cache directory.

### Knowledge Presentation

Once a wiki exists, this subdomain makes it accessible. It encompasses two capabilities: conversational question-and-answer over the generated content, and coverage or quality reporting that surfaces gaps or weak sections.

---

### Domain Relationships

| Subdomain | Depends on | Feeds into |
|---|---|---|
| File Classification | — | Knowledge Extraction |
| Knowledge Extraction | File Classification | Source Traceability, Wiki Persistence |
| Source Traceability | Knowledge Extraction | Wiki Persistence, Knowledge Presentation |
| Incremental Content Maintenance | Wiki Persistence, Knowledge Extraction | Wiki Persistence |
| Wiki Persistence | All upstream | Knowledge Presentation |
| Knowledge Presentation | Wiki Persistence | (end user) |

The boundaries described here are defined by domain responsibility, not by any particular module or technology choice.

## Supporting claims
- The core domain is automated codebase documentation: the systematic transformation of a software repository into a structured, technology-agnostic wiki. [1][2]
- A file classification subdomain tags every file with a semantic kind and handles path-level disambiguation for ambiguous files. [3]
- A knowledge extraction subdomain consumes the file classification to select the appropriate reading strategy and produces normalized findings per wiki section. [2][3]
- A source traceability subdomain anchors every narrative claim to a precise codebase location and surfaces contradictions between sources. [4]
- An incremental content maintenance subdomain classifies section updates as unchanged, surgical, or rewrite based on a churn ratio derived from changes in the finding set. [5]
- A wiki persistence subdomain owns the authoritative on-disk layout, idempotent scaffolding, and all read/write operations for section bodies, extraction notes, configuration, and cache. [6]
- A knowledge presentation subdomain provides conversational Q&A over the generated wiki and coverage/quality reporting. [1]

## Sources
1. `wikifi/cli.py:1-11`
2. `wikifi/extractor.py:1-20`
3. `wikifi/specialized/dispatch.py:36-60`
4. `wikifi/evidence.py:1-18`
5. `wikifi/surgical.py:1-34`
6. `wikifi/wiki.py:1-55`
