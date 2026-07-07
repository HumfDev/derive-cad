import pytest

from derive_cad.cad.validation import Violation
from derive_cad.llm.repair_loop import (
    PipelineStage,
    RepairContext,
    check_stalemate,
    classify_failure,
    error_signature,
    needs_step_rerun,
    rerun_chain_label,
    validation_failure_stage,
)
from derive_cad.llm.review import ReviewResult
from derive_cad.utils.errors import GenerationError


def _ctx(
    *,
    stage: PipelineStage,
    message: str = "failed",
    stderr: str = "",
    violations: list[Violation] | None = None,
) -> RepairContext:
    return RepairContext(
        failed_stage=stage,
        failure_message=message,
        stderr=stderr,
        violations=violations or [],
        review=None,
        script="from build123d import *\n",
        step_path=None,
    )


def test_classify_failure_fillet():
    ctx = _ctx(
        stage=PipelineStage.STEP,
        stderr="ValueError: Failed creating a fillet with radius 50",
    )
    assert classify_failure(ctx) == "Fillet or chamfer failure"


def test_classify_failure_syntax():
    ctx = _ctx(stage=PipelineStage.CODEGEN, message="structure validation failed")
    assert classify_failure(ctx) == "Source import or syntax failure"


def test_rerun_chain_labels():
    assert "scripts/step" in rerun_chain_label(PipelineStage.STEP)
    assert rerun_chain_label(PipelineStage.SNAPSHOT) == "snapshot"
    assert "inspect refs" in rerun_chain_label(PipelineStage.TARGETS)


def test_needs_step_rerun_rules():
    assert needs_step_rerun(PipelineStage.STEP, script_changed=False) is True
    assert needs_step_rerun(PipelineStage.TARGETS, script_changed=False) is False
    assert needs_step_rerun(PipelineStage.TARGETS, script_changed=True) is True
    assert needs_step_rerun(PipelineStage.SNAPSHOT, script_changed=False) is False


def test_validation_failure_stage_targets():
    violations = [Violation("bbox", "too big")]
    assert validation_failure_stage(violations) == PipelineStage.TARGETS


def test_validation_failure_stage_inspect():
    violations = [Violation("bbox", "cadpy inspect refs failed")]
    assert validation_failure_stage(violations) == PipelineStage.TARGETS


def test_stalemate_raises_after_limit():
    ctx = _ctx(stage=PipelineStage.STEP, stderr="SyntaxError: invalid syntax")
    counts: dict[str, int] = {}
    signature = error_signature(ctx)
    for _ in range(4):
        check_stalemate(ctx, stalemate_counts=counts, limit=5)
    assert counts[signature] == 4
    with pytest.raises(GenerationError, match="stalemate"):
        check_stalemate(ctx, stalemate_counts=counts, limit=5)


def test_stalemate_signature_changes_with_stage():
    a = error_signature(_ctx(stage=PipelineStage.STEP, message="one"))
    b = error_signature(_ctx(stage=PipelineStage.INSPECT, message="one"))
    assert a != b


def test_classify_snapshot_stage():
    ctx = RepairContext(
        failed_stage=PipelineStage.SNAPSHOT,
        failure_message="Visual review failed",
        stderr="",
        violations=[],
        review=ReviewResult(performed=True, passed=False, notes="missing hole"),
        script="",
        step_path=None,
    )
    assert classify_failure(ctx) == "CAD `scripts/snapshot` failure"
