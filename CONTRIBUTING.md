# Contributing to derive-cad

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
`tests/test_export.py`) that runs the real build123d subprocess sandbox end-to-end. These are
slower than the unit tests but are the ones that actually prove the CAD pipeline works —
don't skip them locally before submitting a PR that touches `cad/`.

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
"Other" option in `derivecad init`, so a first-class entry here is about a smoother onboarding
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
