"""The Milestone 1 "bare pipeline" fixed geometry.

This script is written to a real .py file and executed in a fresh subprocess
by cad.runner — never exec()'d in-process — so the sandboxing story (timeout,
process isolation, resource limits) applies to it exactly like it will to
LLM-generated scripts in Milestone 2.
"""

BARE_PIPELINE_SCRIPT = '''\
from build123d import *


def build() -> Part:
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


def gen_step(output_path: str) -> None:
    export_step(build(), output_path)


if __name__ == "__main__":
    import sys

    gen_step(sys.argv[1])
'''
