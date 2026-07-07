"""Deterministic comparison of GeometryFacts against a brief's validation targets.

When cadpy is available, optional measure/align checks from the brief JSON are also run
via skills/cad/scripts/inspect.
"""

from dataclasses import dataclass, field
from typing import Literal

from derive_cad.cad.inspect import GeometryFacts

DEFAULT_BBOX_TOLERANCE_PCT = 15.0

ViolationKind = Literal["bbox", "face_count", "solid_count", "measure", "align"]


@dataclass
class MeasureCheck:
    from_ref: str
    to_ref: str
    axis: str | None = None
    expected_mm: float | None = None


@dataclass
class AlignCheck:
    moving: str
    target: str
    mode: str = "flush"
    axis: str | None = None


@dataclass
class ValidationTargets:
    bbox_min: tuple[float, float, float] | None = None
    bbox_max: tuple[float, float, float] | None = None
    bbox_tolerance_pct: float | None = None
    min_face_count: int | None = None
    min_solid_count: int | None = None
    max_solid_count: int | None = None
    notes: str | None = None
    measure_checks: list[MeasureCheck] = field(default_factory=list)
    align_checks: list[AlignCheck] = field(default_factory=list)


@dataclass
class Violation:
    kind: ViolationKind
    message: str


def check_validation_targets(
    facts: GeometryFacts,
    targets: ValidationTargets,
    *,
    default_tolerance_pct: float = DEFAULT_BBOX_TOLERANCE_PCT,
) -> list[Violation]:
    """Compare `facts` against `targets`. Every field of `targets` is independently
    optional; an all-None `ValidationTargets` always returns []."""
    violations: list[Violation] = []
    tol = (
        targets.bbox_tolerance_pct
        if targets.bbox_tolerance_pct is not None
        else default_tolerance_pct
    ) / 100.0

    if targets.bbox_max is not None:
        for actual, limit, axis in zip(facts.bbox_size, targets.bbox_max, "XYZ", strict=True):
            cap = limit * (1 + tol)
            if actual > cap:
                violations.append(
                    Violation(
                        "bbox",
                        f"{axis} size {actual:.2f}mm exceeds target max {limit:.2f}mm "
                        f"(+{tol * 100:.0f}% tolerance = {cap:.2f}mm)",
                    )
                )
    if targets.bbox_min is not None:
        for actual, limit, axis in zip(facts.bbox_size, targets.bbox_min, "XYZ", strict=True):
            floor = limit * (1 - tol)
            if actual < floor:
                violations.append(
                    Violation(
                        "bbox",
                        f"{axis} size {actual:.2f}mm is below target min {limit:.2f}mm "
                        f"(-{tol * 100:.0f}% tolerance = {floor:.2f}mm)",
                    )
                )
    if targets.min_face_count is not None and facts.face_count < targets.min_face_count:
        violations.append(
            Violation(
                "face_count",
                f"face count {facts.face_count} below target minimum {targets.min_face_count}",
            )
        )
    if targets.min_solid_count is not None and facts.solid_count < targets.min_solid_count:
        violations.append(
            Violation(
                "solid_count",
                f"solid count {facts.solid_count} below target minimum "
                f"{targets.min_solid_count}",
            )
        )
    if targets.max_solid_count is not None and facts.solid_count > targets.max_solid_count:
        violations.append(
            Violation(
                "solid_count",
                f"solid count {facts.solid_count} exceeds target maximum "
                f"{targets.max_solid_count}",
            )
        )
    return violations


def run_spec_driven_checks(
    step_path,
    targets: ValidationTargets,
    *,
    cwd,
    enable_cadpy: bool = True,
) -> list[Violation]:
    """Run optional measure/align checks from the brief via cadpy inspect."""
    if not enable_cadpy or (not targets.measure_checks and not targets.align_checks):
        return []

    from pathlib import Path

    from derive_cad.cad.inspect import run_align_check, run_measure_check

    violations: list[Violation] = []
    step = Path(step_path)

    for check in targets.measure_checks:
        try:
            output = run_measure_check(
                step,
                cwd=Path(cwd),
                from_ref=check.from_ref,
                to_ref=check.to_ref,
                axis=check.axis,
            )
            if check.expected_mm is not None and str(check.expected_mm) not in output:
                violations.append(
                    Violation(
                        "measure",
                        f"measure {check.from_ref} -> {check.to_ref} "
                        f"expected ~{check.expected_mm}mm; got: {output[:200]}",
                    )
                )
        except Exception as exc:  # noqa: BLE001
            violations.append(
                Violation("measure", f"measure check failed for {check.from_ref}: {exc}")
            )

    for check in targets.align_checks:
        try:
            output = run_align_check(
                step,
                cwd=Path(cwd),
                moving=check.moving,
                target=check.target,
                mode=check.mode,
                axis=check.axis,
            )
            if "error" in output.lower() or "fail" in output.lower():
                violations.append(
                    Violation("align", f"align {check.moving} -> {check.target}: {output[:200]}")
                )
        except Exception as exc:  # noqa: BLE001
            violations.append(
                Violation("align", f"align check failed for {check.moving}: {exc}")
            )

    return violations
