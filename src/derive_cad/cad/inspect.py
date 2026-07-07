from dataclasses import dataclass
from pathlib import Path

from build123d import import_step

from derive_cad.utils.errors import GenerationError


@dataclass
class GeometryFacts:
    bbox_size: tuple[float, float, float]
    volume: float
    face_count: int
    edge_count: int
    vertex_count: int

    @property
    def is_degenerate(self) -> bool:
        """Deterministic sanity check: zero volume or a collapsed bounding box
        means the geometry is structurally broken, independent of whether it
        matches what the user actually asked for (that's a separate, fuzzier
        concern — see the plan's open risks around semantic correctness).
        """
        return self.volume <= 0 or min(self.bbox_size) <= 0


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
    )
