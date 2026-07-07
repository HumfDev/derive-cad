#!/usr/bin/env python3
"""Run the benchmark prompts in benchmarks/cases.py against a real, already-configured
LLM provider and report pass/fail.

Not part of `pytest -q` or default CI: real LLM output is non-deterministic and this
script makes real API calls. Run it before changing prompts, repair guidance, or the
validation-target schema — see CONTRIBUTING.md.

Usage:
    python benchmarks/run_benchmarks.py [--report path/to/report.json]

Requires a provider already configured via env vars or ~/.derivecad/config.toml
(the same resolution `dcad run` uses) — this script does not launch the interactive
setup wizard.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cases import CASES  # noqa: E402

from derive_cad.cad.inspect import inspect_step  # noqa: E402
from derive_cad.cad.validation import check_validation_targets  # noqa: E402
from derive_cad.cli.setup import needs_setup  # noqa: E402
from derive_cad.config.store import resolve_config  # noqa: E402
from derive_cad.llm.generate import generate_model_from_prompt  # noqa: E402
from derive_cad.utils.errors import DeriveCadError  # noqa: E402


def _run_case(config, case, run_dir) -> dict:
    try:
        outcome = generate_model_from_prompt(
            config,
            case.prompt,
            run_dir,
            timeout_s=config.sandbox_timeout_s,
        )
    except DeriveCadError as exc:
        return {"name": case.name, "generated": False, "error": str(exc)}

    facts = inspect_step(outcome.result.step_path)
    violations = check_validation_targets(facts, case.targets)
    return {
        "name": case.name,
        "generated": True,
        "passed": not violations,
        "violations": [v.message for v in violations],
        "visual_review_performed": outcome.review.performed,
        "visual_review_passed": outcome.review.passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=None, help="Write a JSON report here.")
    args = parser.parse_args()

    config = resolve_config(project_dir=Path.cwd())
    if needs_setup(config):
        print(
            "No LLM provider configured. Run `dcad init` first, or set the relevant "
            "provider env vars, before running benchmarks.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    results = []
    with tempfile.TemporaryDirectory(prefix="dcad-benchmarks-") as tmp:
        base_dir = Path(tmp)
        for case in CASES:
            run_dir = base_dir / case.name
            run_dir.mkdir()
            print(f"Running: {case.name}...", flush=True)
            result = _run_case(config, case, run_dir)
            results.append(result)
            if result.get("passed"):
                status = "PASS"
            elif not result["generated"]:
                status = "ERROR"
            else:
                status = "FAIL"
            print(f"  -> {status}")

    passed = sum(1 for r in results if r.get("passed"))
    print(f"\n{passed}/{len(results)} cases passed.")

    if args.report:
        args.report.write_text(json.dumps(results, indent=2))
        print(f"Report written to {args.report}")

    if passed < len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
