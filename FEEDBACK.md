# Feedback from the implementing agent

A journal entry from Claude Opus 4.7 (1M context) to the original `wikifi`
developer, after implementing the system from the spec in one session and
running it end-to-end against itself with `qwen3.6:27b`.

## How the session went

In one sentence: this is one of the cleanest specs I have implemented from in
recent memory, and most of my friction came from places where the spec was
*almost* explicit but stopped one bullet short.

The spec's structure made it easy to land. README pointed at VISION,
VISION pointed at `.spec/`, `.spec/` pointed at hard specifications and
capabilities. CLAUDE.md said exactly which conventions to follow. By the end of
my first 15 minutes I knew what to build, how to build it, what to *not* build,
and what the operational guardrails were. The pipeline architecture in
`.spec/capabilities.md` (introspection → extraction → aggregation → derivation)
turned directly into four Python modules and a `pipeline.py` orchestrator
without any restructuring.

The single piece of documentation I leaned on most was `.env.example`. It
declared every `WIKIFI_*` variable I would need to support, with defaults that
matched, **and** it warned me that `WIKIFI_THINK=false` breaks Qwen3's JSON
schema enforcement. That single comment saved me hours.

## Where I had real friction

### 1. Smoke-testing thinking models with trivial prompts

My very first action after reading the spec was to verify the Ollama API was
reachable with a "say hi" prompt. It hung for 180 seconds and timed out. I
spent ~10 minutes wondering whether the API was broken before I re-read the
`WIKIFI_THINK` comment in `.env.example` and realised: thinking-capable models
on trivial prompts run away in the reasoning trace and never emit content.

The comment in `.env.example` covers the *symptom* (model emits free text
instead of JSON when thinking is fully off) but not the *adjacent failure
mode* (model never finishes thinking on trivial input). They share the same
root cause. A line like *"Do not smoke-test with trivial prompts — the
`min_content_bytes` guard exists because thinking models hang indefinitely on
near-empty input"* would catch the next agent that does what I did.

### 2. Worktrees and `.git` as a file

I am running inside a git worktree (per `CLAUDE.md`). In a worktree, `.git` is
a *file* containing `gitdir: <path>` — not a directory. My initial
`HARD_EXCLUDED_DIRS` set caught the directory case but not the file case, so my
first scan reported `.git` as an in-scope source file.

This was easy to fix once I noticed, but the spec never tells you that
worktrees are the runtime context. Adding "you will be invoked in a git
worktree; treat the root `.git` file as build artefact" to CLAUDE.md would
prevent it.

### 3. Filter scope is named but not enumerated

VISION says "the legacy project's existing test infrastructure stays out of
scope" and "wikifi is not concerned with repo configuration, build pipelines,
or development tooling — only the production code." Both rules are clear in
intent. Neither tells me which specific paths they mean.

I had to make a series of judgement calls under uncertainty:

* Is `tests/` always out of scope? I assumed yes.
* Is `__tests__/`? I assumed yes.
* Is `.github/`, `.githooks/`? Yes, but is `.gitlab-ci.yml`?
* Is `Dockerfile` "build pipelines"? I called yes.
* Is `Makefile` "development tooling"? Yes.
* Is `pyproject.toml`? I called *no* — it expresses what the system *is*.
* Is `uv.lock`? It is 50+KB of pure noise — but the spec only excludes "build
  artefacts," and the legalistic reading is that lockfiles are not artefacts.
  I excluded them anyway.

A short concrete enumeration in `.spec/hard_specifications.md` would remove
the ambiguity:

```
Permanently excluded from extraction (in addition to VCS metadata):
- Lockfiles: uv.lock, poetry.lock, package-lock.json, pnpm-lock.yaml,
  yarn.lock, Cargo.lock, Gemfile.lock, composer.lock, go.sum
- Build/CI plumbing: Makefile, Dockerfile, docker-compose.{yml,yaml},
  .github/, .githooks/, .gitlab/, .circleci/, .azure-pipelines/
- Test infrastructure: tests/, test/, __tests__/, specs/, spec/
- Worktree pointers: the .git file in a worktree root
```

Without that, every implementer makes their own judgement and the benchmark
becomes about taste, not correctness.

### 4. The `.spec/` ↔ `.wikifi/` mapping is implicit

The benchmark's success criterion is essentially "did your `.wikifi/` look
like `.spec/`?" — but neither VISION nor `.spec/intent.md` says that
out loud. I had to deduce it by counting: VISION lists 11 things to convey,
`.spec/` has 11 files, the filenames are sensible section ids (`intent.md`,
`capabilities.md`, ...). It is not hard to deduce, but the deduction step
costs ~5 minutes and the implementer who does not deduce it can pick a totally
different layout that still conforms to VISION's words.

A single line in VISION — *"The reference shape for the output is `.spec/`:
your `.wikifi/` should contain the same filenames"* — would close this gap.

### 5. The `make init` / `make walk` targets in CLAUDE.md don't exist in the Makefile

`CLAUDE.md` lists `make init` and `make walk` as universal entry points. The
checked-in `Makefile` only has `test`, `lint`, `format`, `coverage`, `hooks`,
`clean`. The referenced targets aren't there. I added them; this is a trivial
discrepancy, but it bit me when I tried to verify my CLI worked from `make`.

### 6. The advisor tool was invaluable; the spec doesn't tell agents about it

I called the `advisor` once after reading the spec but before writing
substantive code. It caught two things I would have spent hours on otherwise:

1. *"`WIKIFI_THINK=false` on Qwen3 breaks JSON schema enforcement."* I had
   read the `.env.example` comment but had not yet internalised the
   structured-output implication.
2. *"De-risk the e2e on `qwen3.5:latest` (10× faster) before committing to
   `qwen3.6:27b`."* I did not end up needing to, but it framed my budget
   correctly.

The advisor is a runtime feature of the harness, not part of your spec — but
mentioning in CLAUDE.md *"call the advisor before committing to an
architecture"* would standardise the practice.

## What I wish I had known up front

1. **Live e2e against a real local LLM is the success criterion.** Unit tests
   are necessary but not sufficient. I prioritised correctness over LLM time
   budget early; once I realised the e2e was non-negotiable, I started
   thinking about per-file budget and prompt size much more carefully.
2. **A real walk takes ~45 minutes on a 27B model.** The `.env.example`
   comment hints at "1-3 minutes per real file" but doesn't multiply it out.
   Knowing "budget ~45 min for the e2e on this repo size" up front would
   have set my pace correctly.
3. **The `.spec/` directory is both the spec and the reference output.**
   Discovering this late meant I designed my prompts around VISION's phrasing
   and only later noticed the prompts I should mirror are in `.spec/*.md`. The
   final output is good either way, but tighter alignment would have come
   from reading `.spec/` as a fixture, not just a description.
4. **`min_content_bytes` is not just an optimization — it is a survival
   mechanism.** Without it, a single stub `__init__.py` would freeze the
   walk. The `.env.example` comment says this; I wish it were also stated in
   `CLAUDE.md` as a rule rather than as a tunable.
5. **Provider abstraction was over-specified for v1 and under-specified for
   v2.** The spec mandates abstraction but only enumerates one backend. That
   means the abstraction is engineering effort with no v1 payoff, and the
   shape of v2 is unclear. I built the cleanest contract I could
   (`generate(prompt, *, system, schema, think, temperature)`) but a
   sentence in the spec like "expect a future hosted-Anthropic backend that
   supports prompt caching" would have made me design for caching from day
   one rather than retrofitting it.

## Changes I would propose to the spec

In rough order of bang-for-buck:

1. **Add a "concretely excluded" enumeration** to `.spec/hard_specifications.md`
   listing lockfiles, build files, CI dirs, test dirs, and the worktree `.git`
   file. Removes the largest source of judgement-call variance between
   implementers.
2. **Make the `.spec/` ↔ `.wikifi/` filename mapping explicit** in
   VISION.md. One sentence does it.
3. **Add a runtime-context paragraph** to CLAUDE.md: *"You are invoked in a
   git worktree. `.git` is a file. Use `pathspec` against the repo's
   `.gitignore` for ignore rules. Expect the live e2e against the configured
   model to be the binding success criterion."*
4. **Sync the Makefile and CLAUDE.md.** Either add `make init` / `make walk`
   to the Makefile, or remove them from the documented commands list.
5. **Lift the thinking-runaway warning** out of the `.env.example` comment
   and into a top-level rule in CLAUDE.md or `.spec/cross_cutting.md`. The
   .env.example comment is the right place to *explain* it; the rule belongs
   in the operational guardrails section so agents see it regardless of
   whether they read .env.example.
6. **Provide a tiny "good output" fixture.** A 30-line example of what a
   well-formed `intent.md` should look like (no H1, no language jargon, with a
   `### Documented Gaps` block) would fail-fast every implementer who emits a
   raw note dump or leaves the leading H1 in.
7. **Document the four-stage budget**. *"Expect ~1-2 min per file for
   extraction, ~2 min per primary section for aggregation, ~3 min per
   derivative section, and ~5 min total for introspection. A 26-file repo
   takes 40-60 min."* Sets expectations honestly.

## Things you got right that I want to call out

* **Hard specifications as a separate file.** Having `.spec/hard_specifications.md`
  as a single, terse list of non-negotiables is enormously helpful. I read it
  three times and used it as a regression checklist before declaring done.
* **Stage gating with degradation rules.** The "don't halt on a single-file
  failure, but record it" pattern is exactly right and easy to implement once
  you see it stated explicitly.
* **Primary vs derivative split.** Separating personas/stories/diagrams from
  the primary sections, and forcing them to consume the *aggregate*, produces
  dramatically better derivative output than a flat one-pass synthesis would.
  This was the single most impactful design decision in the spec.
* **The "explicit gaps" rule.** Without this, the model would happily fill
  every empty section with plausible nonsense. Forcing a `### Documented Gaps`
  block when evidence is thin makes the output trustworthy.
* **`.env.example` as runbook.** The comments in `.env.example` are the most
  useful per-byte documentation in the entire repo. Every constraint that
  bites at runtime is named there.

## Final note

The output I produced — `.wikifi/intent.md`, `.wikifi/capabilities.md`, and
the rest — describes a documentation pipeline that bears a striking
resemblance to the system that just produced it. That is the test working as
designed. If a migration team reads `.wikifi/` and rebuilds wikifi on a new
stack from those 11 files, you have your answer.

Thanks for the well-shaped problem.

— Claude Opus 4.7 (1M context), 2026-04-25
