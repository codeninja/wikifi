# Cross-Cutting Concerns

## Observability and Logging

Log verbosity is configured globally before any pipeline stage executes: a verbose flag activates debug-level output, while the default level is informational. Structured log events are emitted at the entry point of each pipeline stage, giving operators a continuous view of progress across the entire run.

All significant failure modes follow a uniform pattern: errors are caught at the point of failure, logged at WARNING level, and a graceful fallback is substituted so that downstream stages are never blocked. Specifically:

- Aggregation failures produce a fallback body that preserves the raw notes, ensuring a section is always written.
- Derivation failures write a fallback body that retains the upstream evidence verbatim rather than leaving the section blank.
- Quality-review failures return the original body with a zero score and a diagnostic annotation rather than propagating the error.

When an inference call returns neither structured output nor any usable text, a diagnostic message surfaces the stop reason, output-token count, and configured resource budget, together with actionable hints so operators can resolve the issue at the point it occurs.

All provider backends share a single error-formatting routine that extracts a vendor-issued request identifier when present, producing uniformly attributable failure messages regardless of which backend is active.

---

## Error Isolation and Graceful Degradation

Errors are scoped as narrowly as possible throughout the pipeline:

- A failure in one file chunk does not abort extraction of the remaining chunks; a failure on one file does not abort the repository walk. Files that fail entirely are counted as skipped rather than silently lost.
- Provider inference failures during interactive sessions are surfaced as inline error messages rather than terminating the session.
- Cache I/O failures (missing files, malformed content, or bad individual entries) are logged as warnings and fall back to an empty cache, preserving pipeline continuity.
- Provider-specific error shapes are never allowed to leak into the orchestration layer; all backends normalize errors through a shared formatting helper before re-raising them.

---

## Data Integrity and Source Provenance

Full source provenance is a non-negotiable invariant: every claim in the output must carry the source file path, line range, and content fingerprint that justifies it. This citation chain is preserved through caching and replay so that any re-walk of the repository can verify claims against the current source.

Content fingerprints serve three cross-cutting roles:

| Role | Effect |
|---|---|
| Cache keying | Stale extraction or aggregation results are never served when source content changes |
| Citation anchoring | Claims in the wiki can be traced to the exact file revision that produced them |
| Dependency-graph invalidation | Cross-file context is invalidated when any referenced file changes |

Files are always hashed as raw bytes rather than decoded text, ensuring that encoding differences never cause the cache and the extractor to disagree on a file's identity. The aggregation cache key deliberately includes each source file's fingerprint and line range in addition to the finding text, so that even if the text is unchanged, a shift in the cited location triggers a cache miss and re-derives citations from fresh evidence.

Contradictions found in the source are never silently merged. They are always rendered explicitly in the output so that data-integrity issues visible in the source are escalated to the team rather than hidden.

Note records are stamped with a UTC timestamp at write time, providing an audit trail of when each per-file extraction was recorded.

Structured inference output is constrained to a strict schema at every pipeline stage, ensuring deterministic parsing and making successive runs straightforwardly diffable.

---

## Hallucination and Fabrication Prevention

Several independent mechanisms work together to ensure all generated content is grounded in extracted evidence:

- **Deterministic structured output**: Temperature is fixed at zero for all structured-output inference calls so that the same input always produces the same structured result across runs. This is treated as a non-negotiable invariant for the extraction path.
- **Placeholder filtering**: A heuristic matches all known empty-section shapes (
