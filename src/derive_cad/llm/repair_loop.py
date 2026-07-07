"""Upstream repair-loop.md orchestration: classify, repair LLM, partial stage reruns."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from derive_cad.cad.inspect import InspectSummary, run_step_diff
from derive_cad.cad.render import RenderError, render_snapshots
from derive_cad.cad.runner import RunResult, run_script
from derive_cad.cad.script_safety import check_script_safety
from derive_cad.cad.validation import Violation
from derive_cad.config.models import Config
from derive_cad.llm.brief import Brief
from derive_cad.llm.client import complete, extract_python_code, validate_script_structure
from derive_cad.llm.prompts import CAD_REPAIR_USER_PROMPT, cad_repair_system_prompt
from derive_cad.llm.review import ReviewResult, review_snapshots
from derive_cad.utils.errors import GenerationError
from derive_cad.utils.logging import console, log_section, logger


class PipelineStage(StrEnum):
    CODEGEN = "codegen"
    STEP = "step"
    INSPECT = "inspect"
    TARGETS = "targets"
    SNAPSHOT = "snapshot"


@dataclass
class RepairContext:
    failed_stage: PipelineStage
    failure_message: str
    stderr: str
    violations: list[Violation]
    review: ReviewResult | None
    script: str
    step_path: Path | None
    inspect_summary: InspectSummary | None = None


def number_script_lines(script: str) -> str:
    return "\n".join(f"{i + 1:4d}| {line}" for i, line in enumerate(script.splitlines()))


def _snapshot_infra_failure(combined: str) -> bool:
    return any(
        word in combined
        for word in (
            "render failed",
            "snapshot render",
            "playwright",
            "glb",
            "snapshot cli",
            "snapshot error",
            "snapshot job",
        )
    )


def _snapshot_semantic_failure(notes: str) -> bool:
    lowered = notes.lower()
    positioning_words = ("align", "position", "positioning", "joint", "offset", "datum")
    if any(word in lowered for word in positioning_words):
        return True
    return any(
        word in lowered
        for word in ("hole", "feature", "pattern", "missing", "asymmetric", "asymmetry")
    )


def classify_failure(ctx: RepairContext) -> str:
    """Map stderr/violations to a repair-loop.md section name."""
    combined = f"{ctx.failure_message}\n{ctx.stderr}\n".lower()
    combined += " ".join(v.message.lower() for v in ctx.violations)

    if ctx.failed_stage == PipelineStage.SNAPSHOT:
        review_notes = ctx.review.notes if ctx.review and ctx.review.performed else ""
        if review_notes and _snapshot_semantic_failure(review_notes):
            if any(word in review_notes.lower() for word in ("align", "position", "joint")):
                return "Positioning or joint mismatch"
            return "Missing feature"
        if _snapshot_infra_failure(combined):
            return "CAD `scripts/snapshot` failure"
        if ctx.review and ctx.review.performed and not ctx.review.passed:
            return "Missing feature"
        return "CAD `scripts/snapshot` failure"
    if ctx.failed_stage == PipelineStage.CODEGEN:
        return "Source import or syntax failure"
    if ctx.review and ctx.review.performed and not ctx.review.passed:
        return "Missing feature"
    if "fillet" in combined or "chamfer" in combined:
        return "Fillet or chamfer failure"
    if any(word in combined for word in ("align", "positioning", "joint", "assemblyhelper")):
        return "Positioning or joint mismatch"
    if any(word in combined for word in ("selector", "index out of", "edges()", "faces()")):
        return "Selector fragility"
    if "bbox" in combined or "bounding" in combined or "scale" in combined:
        return "Wrong scale or bounding box"
    if any(v.kind in ("measure", "align") for v in ctx.violations):
        return "Missing feature"
    if "syntax" in combined or "import" in combined or "gen_step" in combined:
        return "Source import or syntax failure"
    if "degenerate" in combined or "boolean" in combined or "zero thickness" in combined:
        return "Invalid or missing geometry"
    return "Invalid or missing geometry"


def error_signature(ctx: RepairContext) -> str:
    location = parse_failure_location(ctx.stderr)
    return f"{ctx.failed_stage}|{classify_failure(ctx)}|{location}|{ctx.failure_message[:240]}"


def parse_failure_location(stderr: str) -> str:
    for pattern in (
        r'File "[^"]*model\.py", line (\d+)',
        r'model\.py["\']?, line (\d+)',
    ):
        match = re.search(pattern, stderr)
        if match:
            return f"model.py line {match.group(1)}"
    match = re.search(r"(\w+(?:Error|Exception)):", stderr)
    if match:
        return match.group(1)
    return "unknown location"


def format_violations(violations: list[Violation]) -> str:
    if not violations:
        return "(none)"
    return "\n".join(f"- {v.kind}: {v.message}" for v in violations)


def format_review(review: ReviewResult | None) -> str:
    if review is None or not review.performed:
        return "(not performed)"
    verdict = "FAIL" if not review.passed else "PASS"
    return f"{verdict} — {review.notes}"


def format_inspect_context(summary: InspectSummary | None) -> str:
    if summary is None:
        return "(cadpy inspect summary unavailable)"
    parts: list[str] = []
    if summary.planes_summary:
        parts.append(f"planes: {summary.planes_summary}")
    if summary.positioning_summary:
        parts.append(f"positioning: {summary.positioning_summary}")
    if summary.raw_stdout and not parts:
        parts.append(summary.raw_stdout[:1500])
    return "\n".join(parts) if parts else "(no planes/positioning in inspect output)"


def rerun_chain_label(stage: PipelineStage, *, script_changed: bool = False) -> str:
    if stage == PipelineStage.SNAPSHOT and script_changed:
        return "scripts/step → inspect refs → targets → snapshot"
    chains: dict[PipelineStage, str] = {
        PipelineStage.CODEGEN: "scripts/step → inspect refs → targets → snapshot",
        PipelineStage.STEP: "scripts/step → inspect refs → targets → snapshot",
        PipelineStage.INSPECT: "inspect refs → targets → snapshot",
        PipelineStage.TARGETS: "inspect refs → targets → snapshot",
        PipelineStage.SNAPSHOT: "snapshot",
    }
    return chains[stage]


def needs_step_rerun(failed_stage: PipelineStage | None, *, script_changed: bool) -> bool:
    if failed_stage is None:
        return True
    if failed_stage in (PipelineStage.CODEGEN, PipelineStage.STEP):
        return True
    if failed_stage in (PipelineStage.INSPECT, PipelineStage.TARGETS, PipelineStage.SNAPSHOT):
        return script_changed
    return False


def validation_failure_stage(violations: list[Violation]) -> PipelineStage:
    if any(v.kind in ("bbox", "face_count", "solid_count", "measure", "align") for v in violations):
        return PipelineStage.TARGETS
    return PipelineStage.INSPECT


def append_repair_log(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text.rstrip() + "\n")


def log_repair_progress(
    *,
    attempt: int,
    ctx: RepairContext,
    repair_log: Path,
    script_changed: bool,
) -> None:
    classification = classify_failure(ctx)
    location = parse_failure_location(ctx.stderr)
    chain = rerun_chain_label(ctx.failed_stage, script_changed=script_changed)
    lines = [
        f"Repair {attempt} — classified: {classification}",
        f"  location: {location}",
        "  editing model.py (smallest responsible section)",
        f"  rerunning: {chain}",
    ]
    if ctx.inspect_summary:
        inspect_ctx = format_inspect_context(ctx.inspect_summary)
        lines.append(f"  inspect context: {inspect_ctx[:300]}")
    block = "\n".join(lines)
    console.print(f"[yellow]{block}[/yellow]")
    append_repair_log(
        repair_log,
        f"\n--- Repair {attempt} ---\n{block}\nscript_changed={script_changed}\n",
    )
    logger.info(block)


def request_repair_script(
    config: Config,
    *,
    ctx: RepairContext,
    brief: Brief,
    prompt: str,
) -> str:
    classification = classify_failure(ctx)
    inspect_note = ""
    if ctx.inspect_summary:
        inspect_note = format_inspect_context(ctx.inspect_summary)

    user_prompt = CAD_REPAIR_USER_PROMPT.format(
        classification=classification,
        failure_message=ctx.failure_message,
        stderr=(ctx.stderr[-2000:] or "(empty)") + (
            f"\n\nInspect planes/positioning:\n{inspect_note}" if inspect_note else ""
        ),
        violations=format_violations(ctx.violations),
        review=format_review(ctx.review),
        brief=brief.prose,
        prompt=prompt,
        previous_script=number_script_lines(ctx.script),
    )
    raw = complete(
        config,
        [
            {
                "role": "system",
                "content": cad_repair_system_prompt(is_assembly=brief.is_assembly),
            },
            {"role": "user", "content": user_prompt},
        ],
        log_label="repair",
    )
    return extract_python_code(raw)


def preserve_previous_step(step_path: Path, run_dir: Path) -> Path | None:
    if not step_path.is_file():
        return None
    prev = run_dir / "model.prev.step"
    shutil.copy(step_path, prev)
    return prev


def log_step_diff(
    *,
    run_dir: Path,
    prev_step: Path,
    new_step: Path,
    repair_log: Path,
    timeout_s: int,
) -> None:
    try:
        diff_text = run_step_diff(prev_step, new_step, cwd=run_dir, timeout_s=timeout_s)
    except Exception as exc:  # noqa: BLE001
        logger.warning("inspect diff after repair failed: %s", exc)
        append_repair_log(repair_log, f"inspect diff failed: {exc}")
        return
    if not diff_text.strip():
        diff_text = "(no diff output)"
    log_section("INSPECT DIFF (after repair)", diff_text)
    append_repair_log(repair_log, f"inspect diff:\n{diff_text[:4000]}\n")


def run_step_stage(
    script: str,
    *,
    run_dir: Path,
    timeout_s: int,
    prev_result: RunResult | None,
    repair_log: Path,
) -> RunResult:
    prev_step = prev_result.step_path if prev_result else None
    if prev_step is not None:
        preserve_previous_step(prev_step, run_dir)
    result = run_script(script, run_dir=run_dir, timeout_s=timeout_s)
    prev_copy = run_dir / "model.prev.step"
    if prev_copy.is_file():
        log_step_diff(
            run_dir=run_dir,
            prev_step=prev_copy,
            new_step=result.step_path,
            repair_log=repair_log,
            timeout_s=timeout_s,
        )
    return result


def run_snapshot_stage(
    config: Config,
    *,
    brief: Brief,
    result: RunResult,
    run_dir: Path,
) -> tuple[list[Path], ReviewResult]:
    try:
        snapshot_paths = render_snapshots(result.step_path, run_dir)
        review = review_snapshots(config, snapshot_paths, brief)
    except RenderError as exc:
        return [], ReviewResult(
            performed=False, passed=True, notes=f"Snapshot render failed: {exc}"
        )
    return snapshot_paths, review


def check_codegen_stage(script: str) -> tuple[PipelineStage | None, str, str, list[Violation]]:
    try:
        validate_script_structure(script)
    except ValueError as exc:
        return PipelineStage.CODEGEN, f"Generated script failed structure validation: {exc}", "", []

    safety_violations = check_script_safety(script)
    if safety_violations:
        return (
            PipelineStage.CODEGEN,
            f"Generated script failed safety check: {safety_violations}",
            "",
            [],
        )
    return None, "", "", []


def check_stalemate(
    ctx: RepairContext,
    *,
    stalemate_counts: dict[str, int],
    limit: int,
) -> None:
    signature = error_signature(ctx)
    stalemate_counts[signature] = stalemate_counts.get(signature, 0) + 1
    count = stalemate_counts[signature]
    if count >= limit:
        raise GenerationError(
            f"Repair stalemate after {count} identical failures "
            f"({classify_failure(ctx)} at {parse_failure_location(ctx.stderr)}): "
            f"{ctx.failure_message}"
        )
