# Minimal build123d script used by integration tests.
#
# Uses the return-based gen_step() contract: the script only defines gen_step(),
# which returns the built geometry. cad/runner.py invokes skills/cad/scripts/step
# on model.py — this fixture must not define its own __main__ block.

SAMPLE_BRACKET_SCRIPT = """\
from build123d import *


def gen_step() -> Part:
    with BuildPart() as bracket:
        with BuildSketch() as base:
            Rectangle(60, 40)
            fillet(base.vertices(), radius=4)
        extrude(amount=6)
        with BuildSketch(Plane.XY.offset(6)) as boss_sketch:
            Circle(radius=10)
        extrude(amount=8, mode=Mode.ADD)
        with Locations((-24, -14), (24, -14), (-24, 14), (24, 14)):
            CounterBoreHole(radius=3, counter_bore_radius=5.5, counter_bore_depth=3)
    return bracket.part
"""
