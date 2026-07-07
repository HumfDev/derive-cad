# derive-cad

Text to CAD from your terminal. Connect an LLM API key, pick a working folder, and describe
what you want to build — `derivecad` generates real CAD files (STEP, STL, 3MF, GLB) on disk.

> **Status: Milestone 1.** The plumbing (config, secrets, sandboxed generation, export,
> geometry inspection) is in place and produces a real fixed demo part end-to-end. The
> natural-language LLM loop (describe a part in plain English and get a custom model back)
> is Milestone 2 and not yet implemented — `derivecad run` currently always generates the
> same demo bracket, ignoring any prompt text, to prove the pipeline works before the agent
> loop is layered on top.

## How it works

An LLM (in Milestone 2) writes [build123d](https://github.com/gumyr/build123d) — a Python
parametric CAD library built on the OpenCASCADE kernel — which is executed in a sandboxed
subprocess to produce a STEP file, exported to your requested formats, and validated with
deterministic geometry checks (bounding box, volume, face count). Failures feed back into a
repair loop that rewrites the source and tries again.

## Install

```bash
pip install -e ".[dev]"   # from a clone of this repo; PyPI package coming later
```

> **Note:** `derive-cad` depends on `build123d`, which pulls in a prebuilt OpenCASCADE
> binding (`cadquery-ocp-novtk`, ~60MB per platform). Plain `pip install` works out of the
> box on macOS (arm64/x86_64), Linux (manylinux x86_64/aarch64), and Windows (x64) — no
> conda required. **Alpine/musl Docker images are not supported** (no musllinux wheels are
> published); use a glibc base image such as `python:3.12-slim` if you containerize this.

Requires Python 3.10–3.14.

## Quickstart

```bash
derivecad init   # connect an LLM provider + API key, choose a working folder
derivecad run    # generate a model (Milestone 1: always the fixed demo bracket)
```

`derivecad run` writes `model.step` + your configured export formats (default: `model.stl`)
into a timestamped run directory under `<working_dir>/.runs/`, along with the generated
Python source and stdout/stderr logs.

## Supported LLM providers

| Provider  | Env var            | Notes                          |
|-----------|---------------------|---------------------------------|
| OpenAI    | `OPENAI_API_KEY`    |                                  |
| Anthropic | `ANTHROPIC_API_KEY` |                                  |
| Gemini    | `GEMINI_API_KEY`    |                                  |
| Groq      | `GROQ_API_KEY`      |                                  |
| Ollama    | *(none)*            | Local, no API key required.     |
| Other     | *(you choose)*      | Any [litellm](https://github.com/BerriAI/litellm)-supported model string + env var. |

API keys are stored in your OS keychain via [`keyring`](https://github.com/jaraco/keyring).
If no OS keychain backend is available (common in CI/containers/headless Linux), `derivecad
init` falls back to `~/.derivecad/credentials.toml` (mode 600) and warns you that this is
less secure. An already-set environment variable always takes precedence over stored config.

## Supported output formats

STEP, STL, 3MF, GLB.

## Configuration

- Global config: `~/.derivecad/config.toml`
- Per-project override: `.derivecad.toml` in your working folder
- Precedence: CLI flags > per-project config > env vars (API keys only) > global config > defaults

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
