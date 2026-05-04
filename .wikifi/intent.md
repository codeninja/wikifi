# Intent and Problem Space

wikifi exists to produce a structured, technology-agnostic wiki from an arbitrary source code repository — explaining **what a system does and why**, independent of the languages, frameworks, or infrastructure used to build it. Its primary audience is the team inheriting or migrating an existing codebase: architects and engineers who need a trustworthy, actionable picture of domain entities, capabilities, and integrations without spending days reading raw source files.

### The core problem

Large and legacy codebases resist quick comprehension. Source files encode intent implicitly, mixed with scaffolding, build artifacts, tests, and dependency code that carry no domain signal. At the same time, certain structured artifacts — database schemas, API contracts, protocol definitions — express intent with machine-readable precision that general-purpose analysis handles poorly. Any naive, uniform approach to understanding a codebase either drowns in noise or misses the highest-fidelity evidence.

Beyond individual files, some concepts — user personas, end-to-end user stories, system-level diagrams — only emerge from the *aggregate* of capabilities, entities, and integrations, and simply cannot be read from any single file in isolation.

wikifi addresses all of this by treating repository understanding as a structured, multi-stage extraction problem rather than a documentation-writing task.

### For whom

The system is designed explicitly around the needs of **migration teams and technical architects** who must understand a live system well enough to redesign or replatform it. Every design choice — traceability of claims to source locations, surfacing of contradictions rather than silently merging them, quality scoring before handoff — is oriented toward answering the question: *can we trust this wiki enough to act on it?*

### Constraints that shape the design

**Trust and traceability over convenience.** The system refuses to silently resolve disagreements between source files. Every synthesized claim must trace back to the specific files that justified it, and a dedicated quality-assurance pass flags unsupported claims and coverage gaps before output is delivered.

**Technology neutrality.** All output is expressed in domain terms — entities, capabilities, integrations, personas — never in terms of the implementation technology. This ensures the wiki remains useful even when the migration replaces the entire stack.

**Local-first operation.** The default configuration routes all inference through a locally-hosted model to avoid cloud API dependencies. Hosted providers are explicit opt-ins, reflecting a philosophy of keeping sensitive source code within the operator's own infrastructure unless otherwise chosen.

**Quality over speed.** The system prioritises documentation quality over processing throughput. Guards prevent runaway behaviour on near-empty or oversized files, and higher-order sections are synthesized only after all primary evidence has been assembled.

**Scalability on large codebases.** Re-processing a large legacy codebase on every run is impractical. Content-addressed caching ensures only changed files require new analysis, making repeated full-repository walks economical and enabling recovery after mid-run failures. Structured contract files bypass general-model processing entirely when deterministic parsing is more accurate and less costly.

**Stable output contract.** The on-disk layout produced by wikifi is treated as a contract with the target project: it must remain stable across tool upgrades so that existing wikis stay readable and can be updated incrementally without full regeneration.

## Supporting claims
- wikifi exists to produce a technology-agnostic wiki explaining what a system does and why, independent of the technologies used to build it. [1][2][3][4][5]
- Its primary audience is migration teams and architects who need a trustworthy picture of a codebase without manual source-reading. [6][7][8][9][10][11]
- Some concepts — personas, user stories, diagrams — only emerge from the aggregate of capabilities and entities and cannot be extracted from individual files. [12][5]
- The system refuses to silently resolve contradictions; every claim must trace back to the specific source files that justified it. [13][7]
- A quality-assurance pass flags unsupported claims and coverage gaps before output is delivered, so migration teams can trust the result without manually verifying every claim. [6][8]
- The default configuration routes inference through a locally-hosted model; hosted providers are explicit opt-ins reflecting a local-first philosophy. [14]
- The system prioritises documentation quality over processing throughput, with guards against runaway behaviour on near-empty or oversized files. [1]
- Content-addressed caching makes repeated full-repository walks economical and enables recovery after mid-run failures; only changed files require new analysis. [15][16]
- Structured contract files bypass general-model processing when deterministic parsing is more accurate and less costly. [17][18][19][20]
- The on-disk layout is treated as a stable contract with the target project, kept consistent across tool upgrades so existing wikis remain readable. [21]

## Sources
1. `.env.example:1-2`
2. `wikifi/cli.py:1-10`
3. `wikifi/introspection.py:1-9`
4. `wikifi/orchestrator.py:1-17`
5. `wikifi/sections.py:1-19`
6. `wikifi/critic.py:1-15`
7. `wikifi/evidence.py:1-18`
8. `wikifi/report.py:1-16`
9. `wikifi/specialized/openapi.py:1-11`
10. `wikifi/specialized/protobuf.py:1-8`
11. `wikifi/specialized/sql.py:1-13`
12. `wikifi/deriver.py:1-18`
13. `wikifi/aggregator.py:1-15`
14. `wikifi/config.py:1-26`
15. `wikifi/cache.py:1-20`
16. `wikifi/extractor.py:1-30`
17. `wikifi/repograph.py:1-30`
18. `wikifi/specialized/__init__.py:1-12`
19. `wikifi/specialized/dispatch.py:1-13`
20. `wikifi/specialized/models.py:1-8`
21. `wikifi/wiki.py:1-8`
