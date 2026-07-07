from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from build123d import import_step

from derive_cad.skill.runner import run_skill_script_or_raise
from derive_cad.utils.errors import GenerationError
from derive_cad.utils.logging import logger


@dataclass
class GeometryFacts:
    bbox_size: tuple[float, float, float]
    volume: float
    face_count: int
    edge_count: int
    vertex_count: int
    solid_count: int

    @property
    def is_degenerate(self) -> bool:
        """Deterministic sanity check: zero volume or a collapsed bounding box
        means the geometry is structurally broken, independent of whether it
        matches what the user actually asked for (that's a separate, fuzzier
        concern — see the plan's open risks around semantic correctness).
        """
        return self.volume <= 0 or min(self.bbox_size) <= 0


@dataclass
class InspectSummary:
    raw_stdout: str
    facts: GeometryFacts | None
    planes_summary: str | None
    positioning_summary: str | None


def inspect_step(step_path: Path) -> GeometryFacts:
    try:
        shape = import_step(str(step_path))
    except Exception as exc:  # noqa: BLE001 - surface any OCCT read error clearly
        raise GenerationError(f"Failed to read STEP file {step_path}: {exc}") from exc

    bbox = shape.bounding_box()
    return GeometryFacts(
        bbox_size=(bbox.size.X, bbox.size.Y, bbox.size.Z),
        volume=shape.volume,
        face_count=len(shape.faces()),
        edge_count=len(shape.edges()),
        vertex_count=len(shape.vertices()),
        solid_count=len(shape.solids()),
    )


def _parse_facts_from_json(payload: object) -> GeometryFacts | None:
    if not isinstance(payload, dict):
        return None
    bbox = payload.get("bounding_box") or payload.get("bbox")
    if not isinstance(bbox, dict):
        return None
    size = bbox.get("size") or bbox.get("dimensions")
    if not isinstance(size, dict):
        return None
    try:
        return GeometryFacts(
            bbox_size=(float(size["x"]), float(size["y"]), float(size["z"])),
            volume=float(payload.get("volume", 0.0)),
            face_count=int(payload.get("face_count", 0)),
            edge_count=int(payload.get("edge_count", 0)),
            vertex_count=int(payload.get("vertex_count", 0)),
            solid_count=int(payload.get("solid_count", 0)),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _extract_json_blob(text: str) -> object | None:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def inspect_step_with_cadpy(
    step_path: Path,
    *,
    cwd: Path,
    timeout_s: int = 120,
    strict: bool = False,
) -> InspectSummary:
    """Run skills/cad inspect refs baseline and parse compact facts when possible."""
    rel = step_path.name if step_path.parent == cwd.resolve() else str(step_path)
    try:
        result = run_skill_script_or_raise(
            "inspect",
            ["refs", rel, "--facts", "--planes", "--positioning", "--format", "json"],
            cwd=cwd,
            timeout_s=timeout_s,
        )
    except Exception as exc:  # noqa: BLE001
        if strict:
            raise GenerationError(f"cadpy inspect refs failed: {exc}") from exc
        logger.warning("cadpy inspect failed, falling back to build123d facts: %s", exc)
        facts = inspect_step(step_path)
        return InspectSummary(
            raw_stdout="", facts=facts, planes_summary=None, positioning_summary=None
        )

    payload = _extract_json_blob(result.stdout)
    facts = _parse_facts_from_json(payload) if payload else None
    if facts is None:
        try:
            facts = inspect_step(step_path)
        except GenerationError:
            facts = None

    planes_summary = None
    positioning_summary = None
    if isinstance(payload, dict):
        planes = payload.get("planes")
        if planes:
            planes_summary = str(planes)[:500]
        positioning = payload.get("positioning")
        if positioning:
            positioning_summary = str(positioning)[:500]

    return InspectSummary(
        raw_stdout=result.stdout,
        facts=facts,
        planes_summary=planes_summary,
        positioning_summary=positioning_summary,
    )


def run_step_diff(
    left: Path,
    right: Path,
    *,
    cwd: Path,
    timeout_s: int = 120,
) -> str:
    """Run skills/cad inspect diff between two STEP files (--planes)."""

    def _rel(path: Path) -> str:
        return path.name if path.parent == cwd.resolve() else str(path)

    result = run_skill_script_or_raise(
        "inspect",
        ["diff", _rel(left), _rel(right), "--planes"],
        cwd=cwd,
        timeout_s=timeout_s,
    )
    return result.stdout.strip()


def run_measure_check(
    step_path: Path,
    *,
    cwd: Path,
    from_ref: str,
    to_ref: str,
    axis: str | None = None,
    timeout_s: int = 60,
) -> str:
    rel = step_path.name if step_path.parent == cwd.resolve() else str(step_path)
    args = ["measure", rel, "--from", from_ref, "--to", to_ref]
    if axis:
        args.extend(["--axis", axis])
    result = run_skill_script_or_raise("inspect", args, cwd=cwd, timeout_s=timeout_s)
    return result.stdout.strip()


def run_align_check(
    step_path: Path,
    *,
    cwd: Path,
    moving: str,
    target: str,
    mode: str = "flush",
    axis: str | None = None,
    timeout_s: int = 60,
) -> str:
    rel = step_path.name if step_path.parent == cwd.resolve() else str(step_path)
    args = ["align", rel, "--moving", moving, "--target", target, "--mode", mode]
    if axis:
        args.extend(["--axis", axis])
    result = run_skill_script_or_raise("inspect", args, cwd=cwd, timeout_s=timeout_s)
    return result.stdout.strip()
