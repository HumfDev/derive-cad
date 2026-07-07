from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from derive_cad.cad.inspect import InspectSummary, inspect_step, inspect_step_with_cadpy
from derive_cad.cad.runner import RunResult
from derive_cad.cad.validation import Violation, check_validation_targets, run_spec_driven_checks
from derive_cad.config.models import Config
from derive_cad.llm.brief import Brief, generate_brief, write_brief_md
from derive_cad.llm.client import complete, extract_python_code
from derive_cad.llm.prompts import CAD_CODEGEN_USER_PROMPT, CAD_SYSTEM_PROMPT
from derive_cad.llm.repair_loop import (
    PipelineStage,
    RepairContext,
    append_repair_log,
    check_codegen_stage,
    check_stalemate,
    log_repair_progress,
    needs_step_rerun,
    request_repair_script,
    run_snapshot_stage,
    run_step_stage,
    validation_failure_stage,
)
from derive_cad.llm.review import ReviewResult
from derive_cad.llm.step_parts import check_purchasable_parts
from derive_cad.utils.errors import DeriveCadError, GenerationError
from derive_cad.utils.logging import log_section, logger


@dataclass
class GenerationOutcome:
    result: RunResult
    brief: Brief
    validation_violations: list[Violation]
    inspect_summary: InspectSummary | None
    snapshot_paths: list[Path]
    review: ReviewResult
    attempts: int


def _generate_brief_or_fallback(config: Config, prompt: str, run_dir: Path) -> Brief:
    logger.info("Stage 3/10 — CAD brief for prompt: %r", prompt)
    try:
        brief = generate_brief(config, prompt)
        logger.info("CAD brief generated successfully")
    except DeriveCadError as exc:
        logger.warning("CAD brief generation failed, using fallback: %s", exc)
        from derive_cad.cad.validation import ValidationTargets

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


def _validate_generated_model(
    config: Config,
    brief: Brief,
    result: RunResult,
) -> tuple[list[Violation], InspectSummary | None]:
    violations: list[Violation] = []
    summary: InspectSummary | None = None
    facts = None

    if config.enable_cadpy_inspection:
        try:
            summary = inspect_step_with_cadpy(
                result.step_path,
                cwd=result.run_dir,
                timeout_s=config.sandbox_timeout_s,
                strict=True,
            )
            facts = summary.facts
            if facts is None:
                violations.append(
                    Violation("bbox", "cadpy inspect refs did not produce geometry facts")
                )
        except GenerationError as exc:
            violations.append(Violation("bbox", str(exc)))
    else:
        facts = inspect_step(result.step_path)

    if facts is not None:
        violations.extend(
            check_validation_targets(
                facts, brief.targets, default_tolerance_pct=config.bbox_tolerance_pct
            )
        )
        violations.extend(
            run_spec_driven_checks(
                result.step_path,
                brief.targets,
                cwd=result.run_dir,
                enable_cadpy=config.enable_cadpy_inspection,
            )
        )
        if facts.is_degenerate:
            violations.append(
                Violation("bbox", "geometry is degenerate (zero volume or collapsed bbox)")
            )
    return violations, summary


def _attempt_limit_reached(config: Config, attempt: int) -> bool:
    return config.max_repair_attempts is not None and attempt >= config.max_repair_attempts


def generate_model_from_prompt(
    config: Config,
    prompt: str,
    run_dir: Path,
    *,
    timeout_s: int,
) -> GenerationOutcome:
    """SKILL.md flow: brief -> codegen -> step -> inspect -> targets -> snapshot -> repair."""
    logger.info("Stage 1/10 — Classify task: new part generation from prompt")
    brief = _generate_brief_or_fallback(config, prompt, run_dir)
    part_notes = check_purchasable_parts(prompt, run_dir=run_dir)
    if part_notes:
        parts_block = "\n".join(f"- {n}" for n in part_notes)
        brief = Brief(
            prose=f"{brief.prose}\n\nPurchasable parts:\n{parts_block}",
            targets=brief.targets,
            raw=brief.raw,
        )

    repair_log = run_dir / "repair.log"
    repair_log.write_text("repair log\n", encoding="utf-8")

    logger.info(
        "Generation starting run_dir=%s model=%s provider=%s max_repair_attempts=%s stalemate=%s",
        run_dir,
        config.model,
        config.provider,
        config.max_repair_attempts,
        config.repair_stalemate_limit,
    )

    script = ""
    prev_script = ""
    failed_stage: PipelineStage | None = None
    failure_message = ""
    stderr = ""
    violations: list[Violation] = []
    review = ReviewResult(performed=False, passed=True, notes="")
    result: RunResult | None = None
    inspect_summary: InspectSummary | None = None
    stalemate_counts: dict[str, int] = {}
    attempt = 0

    while True:
        attempt += 1
        logger.info("Attempt %s — pipeline cycle", attempt)

        if attempt == 1:
            logger.info("Stage 6/10 — Codegen")
            script = _request_script(config, brief, prompt)
        else:
            ctx = RepairContext(
                failed_stage=failed_stage or PipelineStage.STEP,
                failure_message=failure_message,
                stderr=stderr,
                violations=violations,
                review=review if review.performed else None,
                script=prev_script,
                step_path=result.step_path if result else None,
                inspect_summary=inspect_summary,
            )
            check_stalemate(
                ctx,
                stalemate_counts=stalemate_counts,
                limit=config.repair_stalemate_limit,
            )
            log_repair_progress(
                attempt=attempt,
                ctx=ctx,
                repair_log=repair_log,
                script_changed=True,
            )
            logger.info("Stage 10/10 — Repair loop (%s)", attempt)
            script = request_repair_script(config, ctx=ctx, brief=brief, prompt=prompt)

        log_section("EXTRACTED SCRIPT", script)
        script_changed = script != prev_script
        prev_script = script

        codegen_stage, failure_message, stderr, violations = check_codegen_stage(script)
        if codegen_stage is not None:
            failed_stage = codegen_stage
            if _attempt_limit_reached(config, attempt):
                raise GenerationError(failure_message)
            continue

        if needs_step_rerun(failed_stage, script_changed=script_changed):
            logger.info("Stage 7/10 — STEP generation via skills/cad/scripts/step")
            try:
                result = run_step_stage(
                    script,
                    run_dir=run_dir,
                    timeout_s=timeout_s,
                    prev_result=result,
                    repair_log=repair_log,
                )
            except GenerationError as exc:
                failed_stage = PipelineStage.STEP
                failure_message = str(exc)
                stderr_log = run_dir / "stderr.log"
                stderr = stderr_log.read_text() if stderr_log.exists() else ""
                violations = []
                append_repair_log(repair_log, f"STEP failure: {failure_message}")
                if _attempt_limit_reached(config, attempt):
                    raise
                continue
        elif result is None:
            raise GenerationError("Internal error: STEP result missing after repair cycle.")

        logger.info("Stage 8/10 — Validation via skills/cad/scripts/inspect")
        violations, inspect_summary = _validate_generated_model(config, brief, result)
        if violations:
            failed_stage = validation_failure_stage(violations)
            failure_message = f"Generated model failed validation: {violations}"
            stderr = result.stderr
            append_repair_log(repair_log, f"{failed_stage} failure: {failure_message}")
            if _attempt_limit_reached(config, attempt):
                raise GenerationError(failure_message)
            continue

        snapshot_paths: list[Path] = []
        if config.enable_snapshot_review:
            logger.info("Stage 9/10 — Snapshot review (skills/cad/scripts/snapshot)")
            snapshot_paths, review = run_snapshot_stage(
                config, brief=brief, result=result, run_dir=run_dir
            )
        else:
            review = ReviewResult(
                performed=False,
                passed=True,
                notes="Snapshot review disabled (enable_snapshot_review=False).",
            )

        if review.performed and not review.passed:
            failed_stage = PipelineStage.SNAPSHOT
            failure_message = f"Visual review failed: {review.notes}"
            stderr = result.stderr
            append_repair_log(repair_log, f"SNAPSHOT failure: {failure_message}")
            if _attempt_limit_reached(config, attempt):
                raise GenerationError(failure_message)
            continue

        logger.info("Generation succeeded on attempt %s", attempt)
        return GenerationOutcome(
            result=result,
            brief=brief,
            validation_violations=[],
            inspect_summary=inspect_summary,
            snapshot_paths=snapshot_paths,
            review=review,
            attempts=attempt,
        )
