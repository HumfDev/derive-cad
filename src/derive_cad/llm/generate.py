from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from derive_cad.cad.inspect import inspect_step
from derive_cad.cad.render import RenderError, render_snapshots
from derive_cad.cad.runner import RunResult, run_script
from derive_cad.cad.script_safety import check_script_safety
from derive_cad.cad.validation import ValidationTargets, Violation, check_validation_targets
from derive_cad.config.models import Config
from derive_cad.llm.brief import Brief, generate_brief, write_brief_md
from derive_cad.llm.client import complete, extract_python_code, validate_script_structure
from derive_cad.llm.prompts import CAD_CODEGEN_USER_PROMPT, CAD_SYSTEM_PROMPT
from derive_cad.llm.review import ReviewResult, review_snapshots
from derive_cad.utils.errors import DeriveCadError, GenerationError
from derive_cad.utils.logging import log_section, logger


@dataclass
class GenerationOutcome:
    result: RunResult
    brief: Brief
    validation_violations: list[Violation]
    snapshot_paths: list[Path]
    review: ReviewResult


def _generate_brief_or_fallback(config: Config, prompt: str, run_dir: Path) -> Brief:
    logger.info("Generating CAD brief for prompt: %r", prompt)
    try:
        brief = generate_brief(config, prompt)
        logger.info("CAD brief generated successfully")
    except DeriveCadError as exc:
        logger.warning("CAD brief generation failed, using fallback: %s", exc)
        brief = Brief(
            prose=f"CAD brief unavailable; proceeding directly from user prompt:\n{prompt}",
            targets=ValidationTargets(),
            raw="(brief generation failed; proceeding from raw prompt)",
        )
    write_brief_md(run_dir, brief)
    log_section(
        "CAD BRIEF",
        f"prose:\n{brief.prose}\n\ntargets:\n{brief.targets}\n\nraw:\n{brief.raw}",
    )
    return brief


def _request_script(config: Config, brief: Brief, prompt: str) -> str:
    raw = complete(
        config,
        [
            {"role": "system", "content": CAD_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": CAD_CODEGEN_USER_PROMPT.format(brief=brief.prose, prompt=prompt),
            },
        ],
        log_label="codegen",
    )
    return extract_python_code(raw)


def generate_model_from_prompt(
    config: Config,
    prompt: str,
    run_dir: Path,
    *,
    timeout_s: int,
) -> GenerationOutcome:
    """Generate build123d source via LLM and execute it once.

    Sequence: brief (once, graceful fallback) -> codegen -> structure/safety checks ->
    sandbox run -> validation-target check -> optional snapshot + vision review.
    """
    brief = _generate_brief_or_fallback(config, prompt, run_dir)

    logger.info(
        "Generation starting run_dir=%s model=%s provider=%s",
        run_dir,
        config.model,
        config.provider,
    )

    script = _request_script(config, brief, prompt)
    log_section("EXTRACTED SCRIPT", script)

    try:
        validate_script_structure(script)
    except ValueError as exc:
        logger.error("Structure validation failed: %s", exc)
        raise GenerationError(f"Generated script failed structure validation: {exc}") from exc

    safety_violations = check_script_safety(script)
    if safety_violations:
        logger.error("Script safety check failed: %s", safety_violations)
        raise GenerationError(f"Generated script failed safety check: {safety_violations}")

    result = run_script(script, run_dir=run_dir, timeout_s=timeout_s)

    facts = inspect_step(result.step_path)
    violations = check_validation_targets(
        facts, brief.targets, default_tolerance_pct=config.bbox_tolerance_pct
    )
    if facts.is_degenerate or violations:
        detail = "geometry is degenerate" if facts.is_degenerate else f"violations: {violations}"
        logger.error("Validation targets failed: %s", detail)
        raise GenerationError(f"Generated model failed validation: {detail}")

    snapshot_paths: list[Path] = []
    if config.enable_snapshot_review:
        try:
            snapshot_paths = render_snapshots(result.step_path, run_dir)
            review = review_snapshots(config, snapshot_paths, brief)
        except RenderError as exc:
            review = ReviewResult(
                performed=False, passed=True, notes=f"Snapshot render failed: {exc}"
            )
            logger.warning("Snapshot render failed: %s", exc)
    else:
        review = ReviewResult(
            performed=False,
            passed=True,
            notes="Snapshot review disabled (enable_snapshot_review=False).",
        )

    if review.performed and not review.passed:
        logger.error("Visual review failed: %s", review.notes)
        raise GenerationError(f"Visual review failed: {review.notes}")

    logger.info("Generation succeeded")
    return GenerationOutcome(
        result=result,
        brief=brief,
        validation_violations=violations,
        snapshot_paths=snapshot_paths,
        review=review,
    )
