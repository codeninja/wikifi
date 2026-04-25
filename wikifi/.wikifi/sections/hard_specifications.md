## Hard Specifications

Critical behavior and requirements that must carry forward.


### Carry-Forward Requirements

- Gap from __main__.py: AI provider output was unavailable, so this note preserves deterministic local evidence instead of fabricating unstated intent.
- Aggregation contains explicit guardrail language around must.
- Aggregation contains explicit guardrail language around threshold.
- Aggregation contains explicit guardrail language around fallback.
- Aggregation contains explicit guardrail language around unsupported.
- Gap from aggregation.py: AI provider output was unavailable, so this note preserves deterministic local evidence instead of fabricating unstated intent.
- Gap from cli.py: AI provider output was unavailable, so this note preserves deterministic local evidence instead of fabricating unstated intent.
- Config contains explicit guardrail language around must.
- Config contains explicit guardrail language around fallback.
- Gap from config.py: AI provider output was unavailable, so this note preserves deterministic local evidence instead of fabricating unstated intent.
- Constants contains explicit guardrail language around must.
- Gap from constants.py: AI provider output was unavailable, so this note preserves deterministic local evidence instead of fabricating unstated intent.
- Derivation contains explicit guardrail language around must.
- Derivation contains explicit guardrail language around fallback.
- Gap from derivation.py: AI provider output was unavailable, so this note preserves deterministic local evidence instead of fabricating unstated intent.
- Extraction contains explicit guardrail language around must.
- Extraction contains explicit guardrail language around never.
- Extraction contains explicit guardrail language around strict.
- Extraction contains explicit guardrail language around required.
- Extraction contains explicit guardrail language around threshold.
- Extraction contains explicit guardrail language around fallback.
- Extraction contains explicit guardrail language around unsupported.
- Gap from extraction.py: AI provider output was unavailable, so this note preserves deterministic local evidence instead of fabricating unstated intent.
- Introspection contains explicit guardrail language around threshold.
- Gap from introspection.py: AI provider output was unavailable, so this note preserves deterministic local evidence instead of fabricating unstated intent.
- Models contains explicit guardrail language around fallback.
- Gap from models.py: AI provider output was unavailable, so this note preserves deterministic local evidence instead of fabricating unstated intent.
- Orchestrator contains explicit guardrail language around fallback.
- Orchestrator contains explicit guardrail language around unsupported.
- Gap from orchestrator.py: AI provider output was unavailable, so this note preserves deterministic local evidence instead of fabricating unstated intent.
- Providers contains explicit guardrail language around unsupported.
- Gap from providers.py: AI provider output was unavailable, so this note preserves deterministic local evidence instead of fabricating unstated intent.
- Gap from reporting.py: AI provider output was unavailable, so this note preserves deterministic local evidence instead of fabricating unstated intent.
- Text contains explicit guardrail language around fallback.
- Gap from text.py: AI provider output was unavailable, so this note preserves deterministic local evidence instead of fabricating unstated intent.
- Gap from traversal.py: AI provider output was unavailable, so this note preserves deterministic local evidence instead of fabricating unstated intent.
- Workspace contains explicit guardrail language around fallback.
- Gap from workspace.py: AI provider output was unavailable, so this note preserves deterministic local evidence instead of fabricating unstated intent.

### Behavioral Specifications

| Clause | Statement |
| --- | --- |
| Given | A file is larger than the configured byte threshold. |
| When | The traversal stage reads it. |
| Then | The content is truncated to the configured limit before extraction. |
| Given | A file is unreadable, malformed, binary, or below the minimum content threshold. |
| When | The traversal stage encounters it. |
| Then | The file is skipped, counted, and the pipeline continues. |
| Given | A provider other than the supported local provider is configured. |
| When | The command validates runtime settings. |
| Then | The run fails gracefully with a clear unsupported-provider message. |

### Gap Declaration

Contradiction resolution between source files is reported but not automatically adjudicated beyond preserving evidence.

