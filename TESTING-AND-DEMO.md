# Testing & demoing the premium pipeline

This document covers how to verify and demo the nine premium features
landed in this PR. Every step works from a clean clone — no external
service required for the test suite, and only Ollama (default) or an
Anthropic API key (opt-in) for the live demos.

## Prerequisites

```bash
make hooks                 # one-time, enables the pre-commit + pre-push hooks
uv sync                    # installs anthropic + the other deps (already in uv.lock)
```

## Running the test suite

```bash
make test                  # runs pytest with coverage
```

Expectations:
- **156 tests pass.**
- **Total coverage ≥ 93%.** Every new module is at or above 86%; the
  premium-pipeline modules — `fingerprint`, `cache`, `evidence`,
  `critic`, `report`, `repograph`, `specialized/*`,
  `providers/anthropic_provider` — each carry a dedicated test file.

To run only the suites for the new functionality:

```bash
uv run pytest tests/test_fingerprint.py tests/test_cache.py tests/test_evidence.py \
              tests/test_repograph.py tests/test_specialized.py tests/test_critic.py \
              tests/test_report.py tests/test_anthropic_provider.py -v --no-cov
```

## Demoing each feature

The demos below assume a working Ollama install with the model from
`.wikifi/config.toml` (default `qwen3.6:27b`). If you want the hosted
Anthropic path instead, set `ANTHROPIC_API_KEY` and pass
`--provider anthropic` to the relevant commands; everything else is
identical.

### 1. Source-traceable citations + 5. Contradiction surfacing

Run a walk against this repo:

```bash
make init                  # one-time; idempotent
make walk
```

Open `.wikifi/<section>.md` for any populated primary section
(`entities.md`, `capabilities.md`, `cross_cutting.md`, …). At the bottom
you should see:

```
## Sources
1. `wikifi/extractor.py:115-187`
2. `wikifi/aggregator.py:54-79`
…
```

Where the aggregator detected disagreement across files, the section
also carries a `## Conflicts in source` block enumerating each
position with its sources. Search for it via:

```bash
rg -n '^## Conflicts in source' .wikifi/
```

(For unit-level evidence: `tests/test_evidence.py` exercises citation
rendering and contradiction rendering directly; `tests/test_aggregator.py`
covers the end-to-end "claim → SourceRef" resolution.)

### 2. Incremental walks (content-addressed cache) + 11. Resumability

Run a walk, then run it again immediately:

```bash
make walk                  # first walk: extracts every in-scope file
make walk                  # second walk: cache_hits == files_seen
```

The second invocation prints `cache_hits=N` in the **Extraction** row
of the walk report — that's the number of files served from the cache
without an LLM call.

To force a clean re-walk:

```bash
uv run wikifi walk --no-cache
```

Resumability is the same mechanism: the cache is persisted after every
file finishes, so a `Ctrl-C` mid-walk loses no progress — the next
`wikifi walk` continues from the file that was in flight when the
crash happened.

(Unit evidence: `tests/test_cache.py`, plus
`test_run_walk_persists_cache_for_resumability` in
`tests/test_orchestrator.py`.)

### 3. Cross-file context (import graph)

Open the live extraction prompt for any application file. The walker
includes a `Neighbor files` block listing files this one imports from
or is imported by:

```bash
uv run wikifi walk -v 2>&1 | rg -A3 "Neighbor files" | head
```

You can also inspect the graph directly:

```python
from pathlib import Path
from wikifi.repograph import build_graph
from wikifi.walker import WalkConfig, iter_files

config = WalkConfig(root=Path("."))
files = list(iter_files(config))
graph = build_graph(repo_root=Path("."), files=files)
node = graph.get("wikifi/aggregator.py")
print(node.imports)        # ('wikifi/cache.py', 'wikifi/evidence.py', ...)
print(node.imported_by)    # ('wikifi/orchestrator.py', ...)
```

(Unit evidence: `tests/test_repograph.py`, plus
`test_extract_repo_injects_neighbor_context_when_graph_supplied` in
`tests/test_extractor.py`.)

### 4. Type-aware extractors (SQL / OpenAPI / Protobuf / GraphQL / migrations)

Drop a SQL file into a target project and run a walk:

```bash
mkdir -p /tmp/demo && cd /tmp/demo && git init -q
cat > schema.sql <<'EOF'
CREATE TABLE customer (
  id INTEGER PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL
);
CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  customer_id INTEGER REFERENCES customer(id),
  total INTEGER NOT NULL
);
CREATE INDEX idx_orders_customer ON orders (customer_id);
EOF
uv run --project /home/user/wikifi wikifi init
uv run --project /home/user/wikifi wikifi walk
```

The walk report's **Extraction** row shows `specialized=1`. The
findings produced for `entities.md`, `integrations.md` (the FK), and
`cross_cutting.md` (the index + UNIQUE invariants) come from the
deterministic SQL parser — no LLM call was made for `schema.sql`.

The same routing covers `*.proto`, `*.graphql`, OpenAPI YAML / JSON
specs, and any SQL file under `migrations/` / `alembic/` /
`db/migrate/` directories.

(Unit evidence: `tests/test_specialized.py` covers each parser;
`test_extract_repo_routes_sql_through_specialized_extractor` in
`tests/test_extractor.py` covers the end-to-end routing.)

### 6. Critic + reviser pass on derivatives

Re-run the walk with `--review`:

```bash
uv run wikifi walk --review
```

The walk report shows `sections_revised=N` in the **Derivation** row —
that's how many derivative sections (personas / user stories /
diagrams) the critic flagged as below the score threshold and the
reviser improved.

(Unit evidence: `tests/test_critic.py` covers the critic loop and the
"only accept revision if it scores at least as well" guard. Integration:
`test_run_walk_review_flag_invokes_critic`.)

### 8. Coverage + quality report

After a walk:

```bash
uv run wikifi report           # purely structural; no LLM calls
uv run wikifi report --score   # adds critic-derived quality scores
```

Output is a markdown table of every section (files contributing,
findings count, body size, score, headline gap):

```
| Section | Files | Findings | Body | Score | Headline gap |
| --- | --- | --- | --- | --- | --- |
| `entities` | 12 | 47 | 5132 | 9/10 | — |
| `cross_cutting` | 4 | 9 | 1421 | 6/10 | unsupported: rate-limit policy |
…
```

(Unit evidence: `tests/test_report.py`.)

### 9. Anthropic provider with prompt caching

Set the API key and switch the provider for a walk:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
WIKIFI_PROVIDER=anthropic uv run wikifi walk
# or:
uv run wikifi walk --provider anthropic
```

The provider sets `cache_control: {"type": "ephemeral"}` on the system
prompt block. After the first per-file extraction call writes the
cache, subsequent calls within the cache window read it for ~10% of
the input price.

To verify caching is active in the wild, intercept the SDK's response:

```python
from wikifi.providers.anthropic_provider import AnthropicProvider
provider = AnthropicProvider(model="claude-opus-4-7", think="high")
# After two calls with the same system prompt:
# response.usage.cache_read_input_tokens > 0
```

(Unit evidence: `tests/test_anthropic_provider.py` locks in the
`cache_control` placement, the `messages.parse` structured-output
contract, the thinking → effort translation, and the APIError →
RuntimeError mapping. `test_build_provider_returns_anthropic_when_selected`
in `tests/test_orchestrator.py` covers dispatch.)

## Tearing down

The premium-pipeline state lives entirely under `.wikifi/`:

```
.wikifi/
  config.toml
  *.md                    # rendered sections (committable)
  .notes/                 # per-section JSONL findings (gitignored)
  .cache/                 # extraction + aggregation caches (gitignored)
```

Delete `.wikifi/.cache/` to drop the cache and force a full re-walk;
delete the whole directory to start over.
