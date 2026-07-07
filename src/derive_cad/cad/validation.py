"""Deterministic comparison of GeometryFacts against a brief's validation targets.

Scope note (deliberate reduction vs. earthtojake/text-to-cad): this replaces that
project's selector-ref `measure`/`align`/`frame`/`diff` system and its assembly
positioning/joint checks with one flat bbox + face/solid-count comparison. The
selector system requires the unvendored `cadpy` library; dcad has no assembly/joint
model at all. See CONTRIBUTING.md.
"""

from dataclasses import dataclass
from typing import Literal

from derive_cad.cad.inspect import GeometryFacts

DEFAULT_BBOX_TOLERANCE_PCT = 15.0

ViolationKind = Literal["bbox", "face_count", "solid_count"]


@dataclass
class ValidationTargets:
    bbox_min: tuple[float, float, float] | None = None
    bbox_max: tuple[float, float, float] | None = None
    bbox_tolerance_pct: float | None = None
    min_face_count: int | None = None
    min_solid_count: int | None = None
    max_solid_count: int | None = None
    notes: str | None = None


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
