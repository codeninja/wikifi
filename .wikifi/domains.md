# Domains and Subdomains

## Core Domain

The system's core domain is **automated documentation synthesis**: ingesting an arbitrary source repository and producing a structured, intent-bearing wiki that describes the codebase in technology-agnostic terms. The central concern is not the mechanics of reading files, but the act of surfacing *business intent* — distinguishing what a system does from the accidental details of how it is implemented.

## Subdomains

### Repository Introspection
Before any analysis begins, the system must decide which parts of a repository carry production intent and which represent infrastructure, tooling, or generated artefacts. This subdomain owns that classification decision. A defining constraint is **tech-agnosticism**: the introspection logic must not rely on recognising specific languages, frameworks, or conventions, so that it generalises across any codebase.

### Knowledge Extraction
Once relevant files are identified, this subdomain is responsible for extracting structured, intent-bearing findings from each one. It encompasses file classification, content chunking, querying an inference backend for structured observations, and persisting those observations with precise citations for downstream use. The output of this subdomain is the raw evidential record.

### Section Synthesis
The documentation produced by the system is split along a clear dependency boundary:

| Subdomain tier | Description | Pipeline position |
|---|---|---|
| **Primary sections** | Built from per-file evidence produced by the extraction subdomain | Stages 2–3 |
| **Derivative sections** | Synthesised by aggregating across all primary-section findings | Stage 4 |

This ordering is a first-class design constraint: derivative sections cannot be produced until all primary evidence is available. The boundary between the two tiers is enforced structurally, not merely by convention.

### Artefact Persistence
Two distinct storage concerns are separated within the system. *Committed wiki content* — the section markdown files that are versioned alongside the target project — is kept apart from *local working state*, which includes per-file extraction notes and a content-addressed cache. The persistence subdomain owns this boundary and ensures that working state is never accidentally treated as part of the published record.

## Subdomain Relationships

The subdomains form a directed dependency chain:

```
Repository Introspection
        ↓
  Knowledge Extraction  →  Artefact Persistence (working state)
        ↓
  Section Synthesis
        ↓
  Artefact Persistence (committed wiki content)
```

No subdomain reaches backwards in this chain; the pipeline ordering is the authoritative expression of inter-subdomain dependency.

## Supporting claims
- The core domain is automated documentation synthesis: extracting business intent from a source repository and producing a technology-agnostic wiki. [1][2]
- The repository introspection subdomain decides which parts of a codebase encode business intent versus infrastructure or tooling. [2]
- A defining constraint of repository introspection is tech-agnosticism — the analysis must not depend on recognising any specific language or framework. [2]
- The knowledge extraction subdomain covers file classification, content chunking, inference-backend querying, and persisting findings with citations. [1]
- Documentation sections are divided into primary sections (built from per-file evidence) and derivative sections (synthesised from aggregates of primary sections), with the ordering enforced as a structural constraint. [3]
- Two distinct storage concerns exist: committed wiki content and local working state (extraction notes and cache); the persistence subdomain enforces this boundary. [4]

## Sources
1. `wikifi/extractor.py`
2. `wikifi/introspection.py:19-44`
3. `wikifi/sections.py:1-19`
4. `wikifi/wiki.py:1-50`
