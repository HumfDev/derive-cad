# Contributing to dcad

## Releasing

The PyPI package name is **`dcad`** (users install with `pipx install dcad`).

1. Bump `version` in `pyproject.toml` and `src/derive_cad/__about__.py`.
2. Update `CHANGELOG.md`.
3. Create a GitHub release (tag = version, e.g. `v0.1.0`).
4. The [Publish workflow](.github/workflows/publish.yml) uploads the wheel to PyPI when the
   release is published.

Set `PYPI_API_TOKEN` in the repo's `PYPI_API_TOKEN` GitHub environment before the first release.

To build and smoke-test locally:

```bash
bash scripts/publish.sh
```

To upload manually (requires `PYPI_API_TOKEN`):

```bash
PYPI_API_TOKEN=... bash scripts/publish.sh --upload
```

## Dev setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

`dcad` bundles the vendored `packages/cadpy` and `skills/cad` inside the wheel — one install
command is enough.

Run lint and tests before opening a PR:

```bash
ruff check .
pytest -q
```

`pytest` includes a marked `integration` suite (`tests/test_cad_runner.py`,
`tests/test_export.py`, `tests/test_render.py`) that runs the real build123d subprocess
sandbox (and, for `test_render.py`, a real Playwright snapshot render) end-to-end. These are slower
than the unit tests but are the ones that actually prove the CAD pipeline works — don't skip
them locally before submitting a PR that touches `cad/`.

For a PR that changes prompts (`llm/prompts.py`), upstream repair guidance
(`skills/cad/references/repair-loop.md`), or the
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

Register the format in `src/derive_cad/cad/runner.py` (`_SIDECAR_FLAGS`) if
`skills/cad/scripts/step` supports a matching `--<format>` sidecar flag. Exports run through
cadpy during `dcad run` via `export_sidecars()` or inline `run_script(..., sidecar_formats=...)`.

## Vendored `skills/cad` and `packages/cadpy`

This repo vendors the full upstream CAD skill from
[earthtojake/text-to-cad](https://github.com/earthtojake/text-to-cad):

- `skills/cad/` — `SKILL.md`, `references/*.md`, `scripts/step`, `scripts/inspect`, `scripts/snapshot`
- `packages/cadpy/` — STEP generation, selector inspection, assemblies
- `skills/cad/scripts/packages/cadpy` → `../../../../packages/cadpy` (symlink)

Pinned upstream commit: `skills/cad/UPSTREAM_SHA`.

`dcad run` orchestrates the SKILL.md 10-step workflow. Low-level tools are exposed as
`dcad step`, `dcad inspect`, and `dcad snapshot` (passthrough to vendored scripts).

Sync from upstream when needed:

```bash
git clone https://github.com/earthtojake/text-to-cad.git /tmp/text-to-cad-upstream
cp -R /tmp/text-to-cad-upstream/skills/cad ./skills/cad
cp -R /tmp/text-to-cad-upstream/packages/cadpy ./packages/cadpy
ln -sf ../../../../packages/cadpy skills/cad/scripts/packages/cadpy
```

## What we ported from earthtojake/text-to-cad's skill docs

That project's `skills/cad/SKILL.md` and `references/*.md` document a staged workflow:
classify the task, write a CAD brief before coding, generate via `scripts/step`, validate
with `scripts/inspect`, review snapshots, and repair failures per `repair-loop.md`.
`llm/brief.py`, `cad/validation.py`, `cad/render.py`, and `llm/review.py` implement this
against dcad's litellm-based CLI; repair prompts load the vendored `repair-loop.md` directly.

**Not vendored:** `viewer/`, `skills/cad-viewer` (no embedded CAD Viewer UI). `dcad run`
uses Playwright snapshots via `skills/cad/scripts/snapshot` for vision review; `dcad open` opens files in the OS default app.

**Stretch / optional:** `skills/step-parts` purchasable-parts library (`llm/step_parts.py`
logs when absent). Assembly codegen and repair prompts load `references/positioning.md`
when the CAD brief `Task type` indicates an assembly, matching the upstream SKILL.md
reference triggers.

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
