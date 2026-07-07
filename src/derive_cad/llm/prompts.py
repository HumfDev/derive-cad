from __future__ import annotations

from functools import lru_cache

from derive_cad.skill.paths import reference_doc


@lru_cache(maxsize=16)
def _load_reference(name: str) -> str:
    try:
        return reference_doc(name).read_text()
    except RuntimeError:
        return ""


_CODEGEN_OUTPUT_CONTRACT = """\
Output format (strict):
- Your response MUST be a complete Python script.
- Start with `from build123d import *` and define `def gen_step()` returning the STEP-ready
  shape or labeled compound (see step-generation.md).
- Do not call export_step() or write an `if __name__ == "__main__"` block — skills/cad/scripts/step
  handles execution and export.
- The script MUST be complete and syntactically valid Python.
- Your entire response must be the Python script and nothing else.
- Do not write explanations outside the code.
- Prefer starting directly with `from build123d import *` (no markdown fence). If you use a
  ```python fence, you MUST include the closing ``` on its own line after the last line of code.
"""

_REPAIR_OUTPUT_CONTRACT = """\
Output contract:
- Return ONLY a complete replacement Python script.
- Start with `from build123d import *` and define `def gen_step()` returning the STEP-ready
  shape or labeled compound.
- Do not call export_step() or add `if __name__ == "__main__"` — skills/cad/scripts/step
  handles execution and export.
- Apply the smallest responsible source change for the classified failure, then the full
  script will be rerun through scripts/step and validation.
"""


@lru_cache(maxsize=2)
def cad_system_prompt(*, is_assembly: bool = False) -> str:
    """Codegen system prompt with upstream reference docs per SKILL.md triggers."""
    sections = [
        """\
You are a CAD code generator. Write complete, runnable Python scripts using build123d.

You will receive a CAD brief in the user message — dimensions, features, units, and
validation targets already derived from the request. Follow it directly; don't re-derive
or second-guess it.

Rules:
- Start with: from build123d import *
- Define def gen_step() that returns the STEP-ready shape or labeled compound
- Do not call export_step() yourself and do not write an
  `if __name__ == "__main__"` block — skills/cad/scripts/step handles execution and export.
- Use BuildPart, BuildSketch, extrude, fillet, revolve, etc. as needed
- Order operations: base solid, major features, subtractive cuts, fillets/chamfers last
- Keep geometry solid and manufacturable (no zero-thickness shells)
- Use named parameters and verbose native labels on major features
""",
        "Modeling patterns (skills/cad/references/build123d-modeling.md):\n"
        + _load_reference("build123d-modeling.md"),
    ]
    if is_assembly:
        sections.append(
            "Assembly positioning (skills/cad/references/positioning.md):\n"
            + _load_reference("positioning.md")
        )
    sections.append(
        "STEP generation (skills/cad/references/step-generation.md):\n"
        + _load_reference("step-generation.md")
    )
    sections.append(_CODEGEN_OUTPUT_CONTRACT)
    return "\n\n".join(sections)


@lru_cache(maxsize=2)
def cad_repair_system_prompt(*, is_assembly: bool = False) -> str:
    """Repair system prompt with upstream reference docs per SKILL.md triggers."""
    sections = [
        """\
You repair failed build123d scripts for a STEP-first CAD pipeline.

Follow skills/cad/references/repair-loop.md exactly:

"""
        + _load_reference("repair-loop.md"),
        "Inspection and validation (skills/cad/references/inspection-and-validation.md):\n\n"
        + _load_reference("inspection-and-validation.md"),
    ]
    if is_assembly:
        sections.append(
            "Assembly positioning (skills/cad/references/positioning.md):\n"
            + _load_reference("positioning.md")
        )
    sections.append(_REPAIR_OUTPUT_CONTRACT)
    return "\n\n".join(sections)


# Default part-task prompts (tests and callers that do not pass is_assembly).
CAD_SYSTEM_PROMPT = cad_system_prompt(is_assembly=False)
CAD_REPAIR_SYSTEM_PROMPT = cad_repair_system_prompt(is_assembly=False)

CAD_CODEGEN_USER_PROMPT = """\
{brief}

Original request: {prompt}
"""

CAD_BRIEF_PROMPT = """\
You write a CAD brief BEFORE any code is written. Follow skills/cad/references/cad-brief.md.

""" + _load_reference("cad-brief.md") + """

Produce:

1. Prose in exactly this format:

CAD brief:
- Model: <part or assembly name>
- Task type: <new part, assembly, modification, inspection, secondary output>
- Units: <explicit or assumed; default millimeters>
- Coordinate convention: <origin, base plane, up axis>
- Overall dimensions: <width/depth/height or equivalent>
- Functional features: <holes, slots, ribs, bosses, pockets, shells, text, etc.>
- Positioning/mating: <only if relevant; see positioning.md>
- Validation targets: <what should be checked: bbox range, min faces, min solids, measure checks>
- Assumptions: <only meaningful inferred choices>

You are writing for a non-interactive CLI: you cannot ask the user a follow-up question.
If information is missing and fit/safety/compliance is not at stake, proceed and record your
choice under Assumptions.

Do not include Python source, pseudocode, or any ```python``` fenced blocks in the brief.
Output prose bullet notes and the JSON validation block only.

2. Immediately after the prose, emit a fenced JSON block (```json ... ```) with EXACTLY these
   nullable keys and no others:
   {{
     "bbox_min": [size_x, size_y, size_z] | null,
     "bbox_max": [size_x, size_y, size_z] | null,
     "bbox_tolerance_pct": number | null,
     "min_face_count": integer | null,
     "min_solid_count": integer | null,
     "max_solid_count": integer | null,
     "notes": string | null,
     "measure_checks": [
       {{"from_ref": "#...", "to_ref": "#...", "axis": "x|y|z", "expected_mm": number}}
     ] | null,
     "align_checks": [
       {{"moving": "#...", "target": "#...", "mode": "flush|center", "axis": "x|y|z"}}
     ] | null
   }}

   bbox_min and bbox_max are per-axis **extents (sizes in mm)**, not world-space corner
   coordinates. Example: a 100 x 60 x 6 mm plate → "bbox_max": [100, 60, 6]. When the
   origin is off-center, still emit sizes (e.g. 50 x 50 x 50), not min/max corner coords.

   measure_checks and align_checks are usually null at brief time because selector refs
   (#f1, etc.) do not exist until after the first STEP is generated. Do not invent refs.
   Rely on bbox/face/solid targets for automated checks.

   Use null for anything you did not derive a confident target for.
"""

SNAPSHOT_REVIEW_PROMPT = """\
You are reviewing rendered snapshot(s) of a generated CAD part against its brief. The images
are flat-shaded triangle-mesh renders (not photorealistic) — judge overall proportions,
presence/absence of stated features, and gross asymmetry or scale errors; do not comment on
shading, texture, or anti-aliasing artifacts.

Respond with a first line of exactly PASS or FAIL, then on following lines explain what you
saw. If you flag a defect, describe it in terms that map to a measurable check (e.g. "hole
pattern looks asymmetric" rather than "looks a bit off").
"""

CAD_REPAIR_USER_PROMPT = """\
A build123d script failed during the CAD pipeline. Follow repair-loop.md: read the output,
classify the failure, and return a complete repaired script.

Classified failure (hint): {classification}

Failure message:
{failure_message}

Stderr excerpt:
{stderr}

Validation violations:
{violations}

Visual review:
{review}

CAD brief:
{brief}

Original request: {prompt}

Previous script (repair the smallest responsible section; return a complete replacement):
```python
{previous_script}
```

Change the smallest responsible source section; return the complete replacement script.
"""
