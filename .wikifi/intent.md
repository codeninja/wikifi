# Intent and Problem Space

wikifi exists to answer a question that becomes increasingly urgent as software systems age: **what does this codebase actually do, and why?** Raw source code communicates intent only to engineers already steeped in its conventions; it is opaque to architects planning migrations, to onboarding teams, and to stakeholders who need to reason about capability and risk without reading every file.

The system addresses this by walking a repository and producing a **technology-agnostic, evidence-grounded wiki** — documentation that describes a system's purpose, entities, capabilities, and integrations in terms that survive a technology change. Its design is shaped above all by the needs of migration teams: every assertion must be traceable to a precise location in the source, contradictions between files must be surfaced rather than silently resolved, and the output must remain readable when the tool is re-run against an upgraded codebase.

### The problems it is designed to solve

**Navigating unknown repositories at scale.** A large legacy codebase may contain tens of thousands of files, the majority of which are scaffolding, build artifacts, dependency caches, or tests — not intent-bearing application logic. The tool must decide, before reading any file's content, which paths are worth analysing. Without this, processing cost grows with repository size rather than with the amount of meaningful content.

**Translating implementation detail into intent.** Source files express *how* a system works. The wiki must express *what* it does and *why*. This translation cannot be a manual step if the output is to stay current. The same requirement applies to structured contract files — schema definitions, interface specifications, API descriptions, and protocol definitions — which encode authoritative domain models but only in formats that require interpretation to surface as human-readable findings. Targeted, deterministic parsers handle these files more accurately and efficiently than a general prose-generation path, so the system routes them separately.

**Scalability and cost.** Processing a large codebase with an AI-assisted extraction pass is expensive if every file requires the same full-cost call on every run. The system is designed to make repeated walks practical: a content-addressed cache ensures that only files whose bytes have changed trigger new AI calls, and the ability to resume after mid-run interruptions is a direct by-product of the same mechanism. For hosted AI providers, the system exploits prompt-caching facilities so that a large shared system prompt used across hundreds of per-file calls pays a fraction of the standard input-token price, making hosted extraction cost-competitive at scale.

**Preventing hallucination and unsupported claims.** Single-shot synthesis — producing a section in one pass without verification — is the most common source of fabricated detail. The system includes a quality-assurance layer that scores each synthesised section against the upstream evidence, flags unsupported claims, identifies coverage gaps, and optionally rewrites sections that fall below a defined quality threshold. Derivative sections — inferred personas, user stories, and structural diagrams — which emerge only from the aggregate of other sections rather than from individual files, receive this treatment by design.

**Surfacing disagreements, not hiding them.** When two source files make incompatible claims about the same aspect of the system, a naive synthesis would silently pick one or blend them into a misleading statement. The system requires instead that conflicts be named and attributed to specific sources, so that a migration team can investigate rather than inherit a wrong assumption.

**Conversational access to the wiki.** Beyond static documents, the system provides a grounded conversational interface over the generated wiki content, allowing users to query findings in natural language. The assistant is constrained to cite section names and admit gaps rather than invent answers, extending the evidence-grounding guarantee into the interactive surface.

### Constraints that shape the design

| Constraint | What it means in practice |
|---|---|
| Tech-agnosticism | All output is in domain terms; no technology names appear in findings or wiki sections |
| Evidence traceability | Every claim links to the source files that justify it |
| Explicit contradiction handling | Conflicts between files are named, not merged away |
| Local-first operation | Defaults to a locally-hosted inference server; cloud providers are explicit opt-ins |
| Stable output contract | The on-disk wiki layout is versioned and isolated, so existing wikis survive tool upgrades |
| Primary vs. derivative separation | Per-file evidence feeds primary sections; aggregate synthesis produces derivative sections; the distinction is enforced structurally |

## Supporting claims
- The system exists to produce a technology-agnostic wiki from a source code repository, helping users understand what a system does and why, independent of the technologies used to build it. [1][2][3]
- Its design is shaped by the needs of migration teams: every assertion must be traceable to a precise source location and contradictions between files must be surfaced rather than silently resolved. [4][5][6]
- Before reading file content, the system must decide which repository paths contain intent-bearing production code versus scaffolding, tests, or build artifacts. [7][8]
- Structured contract files (schema definitions, interface specifications, API descriptions, protocol definitions) are routed to targeted deterministic parsers rather than the general AI extraction path, because their machine-readable structure can be extracted more accurately that way. [9][10][11][12][13][14]
- A content-addressed cache ensures that only files whose bytes have changed trigger new AI calls on repeated walks, and resumability after mid-run interruptions is a direct by-product of the same mechanism. [15][16]
- For hosted AI providers, prompt-caching facilities are exploited so that a large shared system prompt used across many per-file calls pays a fraction of the normal input-token price, making hosted extraction economically viable at scale. [17]
- A quality-assurance layer scores each synthesised section against upstream evidence, flags unsupported claims and gaps, and optionally rewrites sections that fall below a defined quality threshold. [5]
- Derivative sections — personas, user stories, and structural diagrams — can only emerge from the aggregate of all primary sections; no single file contains enough signal to produce them reliably, so they are synthesised in a separate stage after primary sections are complete. [18][3]
- When source files make incompatible claims, conflicts must be named and attributed to specific sources rather than merged, so migration teams can investigate rather than inherit wrong assumptions. [4]
- The system defaults to a locally-hosted inference server, treating cloud AI providers as explicit opt-ins, reflecting a local-first design philosophy. [19]
- The on-disk wiki layout is treated as a stable, versioned contract between the tool and the projects that consume it, and its definition is kept isolated from other modules. [20]
- The system provides a grounded conversational interface over the generated wiki, constraining the assistant to cite section names and admit gaps rather than fabricate answers. [21]
- The extraction stage enriches per-file analysis by supplying each file's import-graph neighborhood as context, allowing findings to mention cross-file relationships rather than treating each file in isolation. [22]
- A read-only reporting capability answers pre-migration coverage and quality questions — whether the walk covered the entire system and whether the resulting wiki is reliable enough to act on — without modifying any wiki content. [23]

## Sources
1. `wikifi/cli.py:1-10`
2. `wikifi/orchestrator.py:1-17`
3. `wikifi/sections.py:1-19`
4. `wikifi/aggregator.py:1-15`
5. `wikifi/critic.py:1-15`
6. `wikifi/evidence.py:1-18`
7. `wikifi/introspection.py:1-9`
8. `wikifi/walker.py:1-12`
9. `wikifi/specialized/__init__.py:1-12`
10. `wikifi/specialized/dispatch.py:1-13`
11. `wikifi/specialized/models.py:1-8`
12. `wikifi/specialized/openapi.py:1-11`
13. `wikifi/specialized/protobuf.py:1-8`
14. `wikifi/specialized/sql.py:1-13`
15. `wikifi/cache.py:1-20`
16. `wikifi/extractor.py:1-30`
17. `wikifi/providers/anthropic_provider.py:1-19`
18. `wikifi/deriver.py:1-18`
19. `wikifi/config.py:1-26`
20. `wikifi/wiki.py:1-8`
21. `wikifi/chat.py:1-32`
22. `wikifi/repograph.py:1-30`
23. `wikifi/report.py:1-16`
