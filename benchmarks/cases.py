"""Benchmark prompts with hand-picked expected validation targets.

Scoped-down analogue of earthtojake/text-to-cad's 10 benchmark prompts. See
benchmarks/run_benchmarks.py for how these are run — deliberately not part of
pytest/CI, since real LLM output is non-deterministic and costs real API calls.
"""

from dataclasses import dataclass

from derive_cad.cad.validation import ValidationTargets


@dataclass
class BenchmarkCase:
    name: str
    prompt: str
    targets: ValidationTargets


CASES: list[BenchmarkCase] = [
    BenchmarkCase(
        name="mounting_plate",
        prompt=(
            "A 100mm by 60mm by 6mm mounting plate with rounded corners and four M4 "
            "clearance holes 10mm in from each corner."
        ),
        targets=ValidationTargets(
            bbox_max=(100.0, 60.0, 6.0), bbox_tolerance_pct=10.0, min_face_count=10
        ),
    ),
    BenchmarkCase(
        name="simple_cube",
        prompt="A solid 40mm cube.",
        targets=ValidationTargets(
            bbox_min=(40.0, 40.0, 40.0),
            bbox_max=(40.0, 40.0, 40.0),
            bbox_tolerance_pct=5.0,
            min_face_count=6,
            min_solid_count=1,
            max_solid_count=1,
        ),
    ),
    BenchmarkCase(
        name="cylinder_with_bore",
        prompt="A 50mm diameter, 30mm tall cylinder with a 10mm through-hole down its axis.",
        targets=ValidationTargets(
            bbox_max=(50.0, 50.0, 30.0), bbox_tolerance_pct=10.0, min_face_count=4
        ),
    ),
    BenchmarkCase(
        name="filleted_bracket",
        prompt="An L-shaped bracket, 80mm by 80mm by 5mm thick, with 3mm fillets on all edges.",
        targets=ValidationTargets(bbox_max=(80.0, 80.0, 5.0), bbox_tolerance_pct=15.0),
    ),
    BenchmarkCase(
        name="pocketed_enclosure_base",
        prompt=(
            "A rectangular enclosure base, 120mm by 80mm by 10mm, with a 5mm-deep pocket "
            "leaving a 2mm wall around the perimeter."
        ),
        targets=ValidationTargets(
            bbox_max=(120.0, 80.0, 10.0), bbox_tolerance_pct=10.0, min_face_count=10
        ),
    ),
    BenchmarkCase(
        name="four_leg_stand",
        prompt="A phone stand at a 45 degree angle, roughly 80mm wide and 100mm tall.",
        targets=ValidationTargets(bbox_tolerance_pct=25.0, min_solid_count=1),
    ),
    BenchmarkCase(
        name="hex_standoff",
        prompt="A hex standoff, 10mm across flats, 20mm tall, with a 3mm through-hole.",
        targets=ValidationTargets(bbox_max=(11.6, 11.6, 20.0), bbox_tolerance_pct=10.0),
    ),
    BenchmarkCase(
        name="counterbore_bracket",
        prompt=(
            "A flat 60mm by 40mm by 6mm bracket with four counterbore holes for M3 screws, "
            "10mm from each corner."
        ),
        targets=ValidationTargets(
            bbox_max=(60.0, 40.0, 6.0), bbox_tolerance_pct=10.0, min_face_count=10
        ),
    ),
]
