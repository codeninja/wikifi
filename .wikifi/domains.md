# Domains and Subdomains

## Core Domain

The system's core domain is **codebase knowledge extraction**: ingesting an existing source base, classifying its contents, deriving domain findings from individual files, and synthesising those findings into a structured, technology-agnostic wiki. The primary consumers are migration teams who need to understand business intent, domain structure, and operational behaviour before re-implementing or replacing a legacy system.

## Subdomains

### Repository Introspection
This subdomain concerns discovering and classifying the files that make up a target codebase. Its central responsibility is distinguishing production source that encodes business intent from infrastructure, tooling, and other artefacts that do not. Tech-agnosticism is a first-class constraint here: the classification logic must not rely on recognising any specific language, framework, or runtime.

### Per-File Knowledge Extraction
Once relevant files are identified, each is analysed independently to surface domain findings. This subdomain covers the full extraction loop — examining file content, applying domain heuristics, and producing structured evidence — and forms the first phase of wiki generation (primary sections).

### Section Synthesis and Aggregation
The second phase of wiki generation operates over the evidence produced by per-file extraction. It aggregates findings across files into coherent wiki sections, derives higher-level content that cannot be inferred from any single file, and enforces the dependency ordering between primary (evidence-driven) and derivative (aggregated) sections. This ordering is a structural design constraint, not merely a runtime convention.

### Wiki Authoring and Organisation
A secondary domain governs how extracted knowledge is structured and stored. It defines the taxonomy of sections, distinguishes primary from derivative content, and produces output that a migration team can navigate and consume independently of the source codebase.

### Interactive Knowledge Retrieval
A supporting subdomain exposes the generated wiki to conversational or query-driven access, allowing stakeholders to interrogate extracted knowledge without directly inspecting raw wiki files.

## Cross-Cutting Constraint: Tech-Agnosticism
Tech-agnosticism spans every subdomain. All analysis, extraction, and synthesis must produce domain-level descriptions that are free of references to specific languages, frameworks, or libraries. This constraint is enforced at both the classification stage (repository introspection) and the output stage (section content).

## Subdomain Relationships

| Subdomain | Role | Depends On |
|---|---|---|
| Repository Introspection | Identifies source worth analysing | — |
| Per-File Knowledge Extraction | Produces primary section evidence | Introspection |
| Section Synthesis & Aggregation | Produces derivative sections | Per-File Extraction |
| Wiki Authoring & Organisation | Structures and stores the wiki | Synthesis |
| Interactive Knowledge Retrieval | Queries the completed wiki | Authoring |

## Sources
1. `README.md:28-52`
2. `VISION.md:3-20`
3. `wikifi/cli.py:1-8`
4. `wikifi/introspection.py:19-44`
5. `wikifi/sections.py:1-19`
