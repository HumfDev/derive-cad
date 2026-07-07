"""STEP -> STL/3MF/GLB conversion.

Implemented directly against build123d's own exporter APIs (export_stl,
export_gltf, the Mesher class) rather than vendoring the reference project's
unpublished `cadpy` package — see the plan's decision log for why.
"""

from pathlib import Path
from typing import Literal

from build123d import Mesher, export_gltf, export_stl, import_step

from derive_cad.utils.errors import ExportError

ExportFormat = Literal["stl", "3mf", "glb"]


def _load(step_path: Path):
    try:
        return import_step(str(step_path))
    except Exception as exc:  # noqa: BLE001 - surface any OCCT read error clearly
        raise ExportError(f"Failed to read STEP file {step_path}: {exc}") from exc


def step_to_stl(step_path: Path, stl_path: Path) -> Path:
    shape = _load(step_path)
    export_stl(shape, str(stl_path))
    return stl_path


def step_to_3mf(step_path: Path, threemf_path: Path) -> Path:
    shape = _load(step_path)
    mesher = Mesher()
    mesher.add_shape(shape)
    mesher.write(str(threemf_path))
    return threemf_path


def step_to_glb(step_path: Path, glb_path: Path) -> Path:
    shape = _load(step_path)
    export_gltf(shape, str(glb_path), binary=True)
    return glb_path


_EXPORTERS = {
    "stl": step_to_stl,
    "3mf": step_to_3mf,
    "glb": step_to_glb,
}


def export_format(step_path: Path, output_path: Path, fmt: ExportFormat) -> Path:
    try:
        exporter = _EXPORTERS[fmt]
    except KeyError as exc:
        raise ExportError(f"Unsupported export format: {fmt!r}") from exc
    return exporter(step_path, output_path)
