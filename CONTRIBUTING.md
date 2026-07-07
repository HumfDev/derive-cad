# Contributing to dcad

## Releasing

The PyPI package name is **`dcad`** (users install with `pipx install dcad`).

1. Bump `version` in `pyproject.toml` and `src/derive_cad/__about__.py`.
2. Update `CHANGELOG.md`.
3. Create a GitHub release (tag = version, e.g. `v0.1.0`).
4. The [Publish workflow](.github/workflows/publish.yml) uploads the wheel to PyPI when the
   release is published.

Set `PYPI_API_TOKEN` in the repo's `pypi` GitHub environment before the first release.

## Dev setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run lint and tests before opening a PR:

```bash
ruff check .
pytest -q
```

`pytest` includes a marked `integration` suite (`tests/test_cad_runner.py`,
`tests/test_export.py`, `tests/test_render.py`) that runs the real build123d subprocess
sandbox (and, for `test_render.py`, a real matplotlib render) end-to-end. These are slower
than the unit tests but are the ones that actually prove the CAD pipeline works — don't skip
them locally before submitting a PR that touches `cad/`.

For a PR that changes prompts (`llm/prompts.py`), repair guidance (`llm/repair.py`), or the
brief's validation-target schema (`llm/brief.py`, `cad/validation.py`), also run
`python benchmarks/run_benchmarks.py` against a real configured provider — see
`benchmarks/cases.py` and the "What we ported" section below.

## Platform caveats worth knowing before touching `cad/sandbox.py`

- **No musllinux/Alpine wheels** for build123d's OCP binding — anything Docker-based needs a
  glibc base image (`python:3.12-slim`, not `-alpine`).
- **Windows has no `resource` module** — the POSIX memory/CPU resource limits in
  `cad/sandbox.py` are a documented gap on Windows, not silently ignored. The subprocess
  timeout is the cross-platform backstop against runaway generation scripts.
- **macOS's `RLIMIT_AS` frequently can't be lowered** below the process's already-mapped
  virtual address space (dyld's shared cache alone can reserve several GB), so the memory
  limit in `cad/sandbox.py` is applied best-effort and never blocks launching the subprocess
  if `setrlimit` fails.

## Secrets

This project handles real API keys. Never commit real keys, `credentials.toml`, or any
fixture containing a live secret. Tests exercise the secrets layer against fake/mocked
keyring backends (see `tests/test_secrets.py`) — no real OS keychain is touched in CI.

## Adding a new LLM provider

Add an entry to `PROVIDERS` in `src/derive_cad/llm/providers.py` with its env var name and a
sensible default model string. Users can already reach any litellm-supported provider via the
"Other" option in `dcad init`, so a first-class entry here is about a smoother onboarding
experience, not enabling something otherwise impossible.

## Adding a new export format

Add a `step_to_<format>` function to `src/derive_cad/cad/export.py` built directly on
build123d's own exporter APIs, and register it in `_EXPORTERS`.

## A note on the reference project's `cadpy` package

`earthtojake/text-to-cad` (a different kind of project — an agent *skill*, not a standalone
CLI) has an internal `packages/cadpy` wrapper around STEP/STL/GLB export and geometry
inspection. We deliberately did **not** vendor it: it's unpublished (no PyPI release, no
license/API-stability guarantee) and its build requires monorepo-only tooling it's coupled
to. `cad/export.py` and `cad/inspect.py` are a from-scratch reimplementation directly against
build123d's public APIs instead. Please don't re-propose vendoring it.

## What we ported from earthtojake/text-to-cad's skill docs, and what we didn't

That project's `skills/cad/SKILL.md` and `references/*.md` document a staged workflow for
agentic coding tools (Claude Code, Codex) that already have their own model and file/bash
tools: classify the task, write a CAD brief before coding, generate, validate
deterministically, review a mandatory snapshot, and repair failures by classified category
rather than a generic retry. `llm/brief.py`, `cad/validation.py`, `cad/render.py`,
`llm/review.py`, and `llm/repair.py` mirror that *process* — guidance text adapted, not
copied verbatim, and re-implemented against dcad's own litellm-based architecture (that
project has no LLM API layer of its own; its "LLM" is whichever coding agent is already
running).

Deliberately not ported, because they require the unvendored `cadpy` selector system or an
assembly/joint model dcad doesn't have:

- Selector-ref `measure`/`align`/`frame`/`diff` checks — dcad has one flat bbox/face/solid
  -count comparison against brief-derived validation targets instead (`cad/validation.py`).
- Assembly positioning/joint-mismatch repair category.
- Selector-fragility repair category.
- The purchasable-parts library check (no such library in dcad).

Two additional, smaller pieces were added alongside the port, in response to review of an
earlier scaffold plan for this repo:

- `cad/script_safety.py` — an AST-based import allowlist for LLM-generated scripts, run
  before the sandbox ever executes them. It only catches plain `import`/`from` statements,
  not `__import__()`/`importlib`/`eval`/`exec` obfuscation — layered defense on top of the
  subprocess sandbox in `cad/sandbox.py`, not a replacement for it.
- `benchmarks/run_benchmarks.py` — ~8 benchmark prompts (`benchmarks/cases.py`) with
  hand-picked expected validation targets, mirroring earthtojake's 10 benchmark prompts.
  Run this against a real configured provider before changing prompts, repair guidance, or
  the validation-target schema. Deliberately **not** part of `pytest -q` or CI: it makes
  real API calls and real LLM output is non-deterministic.
