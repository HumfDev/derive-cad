"""From-scratch STEP -> PNG snapshot renderer for the mandatory visual-review stage.

Built on build123d's own tessellate() output plus matplotlib's mplot3d, with flat
per-triangle shading computed from face normals against one fixed light direction —
enough to read proportions, feature presence, and gross asymmetry, not a
photorealistic renderer. No VTK/Open3D/trimesh/pyrender dependency; this is a
deliberate lightness tradeoff, not an attempt to match a real CAD viewer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from build123d import import_step
from matplotlib import pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from derive_cad.utils.errors import DeriveCadError


class RenderError(DeriveCadError):
    """Raised on tessellation/render failure. Callers treat this as a soft-skip
    (report and continue), not a hard pipeline failure."""


@dataclass(frozen=True)
class ViewSpec:
    name: str
    elev: float
    azim: float


# Trimmed from the source repo's 4-view default packet (iso, iso_opposite, top_ortho,
# front_ortho) to 3 — low marginal value for dcad's single-part scope.
DEFAULT_VIEWS: tuple[ViewSpec, ...] = (
    ViewSpec("iso", elev=30, azim=45),
    ViewSpec("top_ortho", elev=90, azim=-90),
    ViewSpec("front_ortho", elev=0, azim=-90),
)

_LIGHT_DIRECTION = np.array([0.4, -0.5, 0.8])
_LIGHT_DIRECTION = _LIGHT_DIRECTION / np.linalg.norm(_LIGHT_DIRECTION)
_BASE_COLOR = np.array([0.55, 0.65, 0.80])
_AMBIENT = 0.35


def _load_triangles(step_path: Path, tolerance: float) -> tuple[np.ndarray, np.ndarray]:
    try:
        shape = import_step(str(step_path))
        vertices, triangles = shape.tessellate(tolerance)
    except Exception as exc:  # noqa: BLE001 - surface any OCCT/tessellation error clearly
        raise RenderError(f"Failed to tessellate {step_path}: {exc}") from exc

    if not triangles:
        raise RenderError(f"{step_path} tessellated to zero triangles.")

    verts = np.array([(v.X, v.Y, v.Z) for v in vertices])
    tris = np.array(triangles)
    return verts, tris


def _shaded_faces(verts: np.ndarray, tris: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    face_verts = verts[tris]  # (n_tris, 3, 3)
    edge1 = face_verts[:, 1] - face_verts[:, 0]
    edge2 = face_verts[:, 2] - face_verts[:, 0]
    normals = np.cross(edge1, edge2)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normals = normals / norms

    intensity = _AMBIENT + (1 - _AMBIENT) * np.clip(normals @ _LIGHT_DIRECTION, 0, 1)
    colors = np.clip(_BASE_COLOR[None, :] * intensity[:, None], 0, 1)
    return face_verts, colors


def render_view(
    step_path: Path,
    output_path: Path,
    view: ViewSpec,
    *,
    tolerance: float = 0.2,
) -> Path:
    """Render one PNG view of step_path's tessellated geometry to output_path."""
    verts, tris = _load_triangles(step_path, tolerance)
    face_verts, colors = _shaded_faces(verts, tris)

    fig = plt.figure(figsize=(6, 6), dpi=150)
    ax = fig.add_subplot(projection="3d")
    collection = Poly3DCollection(face_verts, facecolor=colors, edgecolor="black", linewidths=0.1)
    ax.add_collection3d(collection)

    mins = verts.min(axis=0)
    maxs = verts.max(axis=0)
    center = (mins + maxs) / 2
    radius = max((maxs - mins).max() / 2, 1e-6) * 1.1
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=view.elev, azim=view.azim)
    ax.set_axis_off()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return output_path


def render_snapshots(
    step_path: Path,
    run_dir: Path,
    views: tuple[ViewSpec, ...] = DEFAULT_VIEWS,
) -> list[Path]:
    """Render the default snapshot packet into run_dir/snapshots/<view>.png."""
    out_dir = run_dir / "snapshots"
    return [render_view(step_path, out_dir / f"{view.name}.png", view) for view in views]
