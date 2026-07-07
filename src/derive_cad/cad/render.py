"""Playwright + CAD Viewer GLB snapshot renderer for visual review.

Delegates to vendored skills/cad/scripts/snapshot (headless Chromium + GLB sidecars),
matching the upstream snapshot-review.md small packet. Requires the hidden topology
GLB produced alongside STEP generation (`.model.step.glb`).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from derive_cad.skill.runner import SkillScriptError, run_skill_script_or_raise
from derive_cad.utils.errors import DeriveCadError


class RenderError(DeriveCadError):
    """Raised on snapshot render failure. Callers treat this as a soft-skip
    (report and continue), not a hard pipeline failure."""


@dataclass(frozen=True)
class SnapshotView:
    name: str
    camera: str | dict[str, list[float] | float]


# Upstream snapshot-review.md small packet: opposed isos + top + front.
DEFAULT_VIEWS: tuple[SnapshotView, ...] = (
    SnapshotView("iso", "iso"),
    SnapshotView("iso_opposite", {"direction": [-1, 1, -0.8]}),
    SnapshotView("top_ortho", "top"),
    SnapshotView("front_ortho", "front"),
)

_SAVED_SNAPSHOT_RE = re.compile(r"^saved snapshot:\s*(.+)$", re.MULTILINE)


def _topology_glb_path(step_path: Path) -> Path:
    return step_path.parent / f".{step_path.name}.glb"


def _build_snapshot_job(
    step_path: Path,
    run_dir: Path,
    views: tuple[SnapshotView, ...],
) -> dict[str, object]:
    out_rel = "snapshots"
    return {
        "input": step_path.name,
        "mode": "view",
        "outputs": [
            {"path": f"{out_rel}/{view.name}.png", "camera": view.camera}
            for view in views
        ],
        "render": {"viewLabels": True, "padding": 0.12, "sizeProfile": "diagnostic"},
    }


def _parse_saved_paths(stdout: str) -> list[Path]:
    return [Path(match.group(1).strip()) for match in _SAVED_SNAPSHOT_RE.finditer(stdout)]


def render_snapshots(
    step_path: Path,
    run_dir: Path,
    views: tuple[SnapshotView, ...] = DEFAULT_VIEWS,
    *,
    timeout_s: int = 300,
) -> list[Path]:
    """Render the default snapshot packet into run_dir/snapshots/ via Playwright."""
    step_path = step_path.resolve()
    run_dir = run_dir.resolve()
    if not step_path.is_file():
        raise RenderError(f"STEP file not found: {step_path}")

    glb_path = _topology_glb_path(step_path)
    if not glb_path.is_file():
        raise RenderError(
            f"Missing CAD Viewer GLB sidecar for {step_path.name}: {glb_path.name}. "
            "Regenerate STEP via skills/cad/scripts/step so topology GLB is produced."
        )

    out_dir = run_dir / "snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    job = _build_snapshot_job(step_path, run_dir, views)
    job_path = out_dir / "snapshot-job.json"
    job_path.write_text(json.dumps(job, indent=2), encoding="utf-8")

    try:
        rel_job = job_path.relative_to(run_dir).as_posix()
        result = run_skill_script_or_raise(
            "snapshot",
            ["--job", rel_job],
            cwd=run_dir,
            timeout_s=timeout_s,
        )
    except SkillScriptError as exc:
        raise RenderError(str(exc)) from exc

    paths = _parse_saved_paths(result.stdout)
    if len(paths) != len(views):
        raise RenderError(
            f"Expected {len(views)} snapshot PNGs, got {len(paths)}. stdout:\n{result.stdout[-2000:]}"
        )
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise RenderError(f"Snapshot render reported paths that do not exist: {missing}")
    return paths
