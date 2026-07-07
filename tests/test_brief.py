from derive_cad.llm.brief import parse_brief, write_brief_md

WELL_FORMED = """\
CAD brief:
- Model: mounting_plate

```json
{
  "bbox_min": null,
  "bbox_max": [100, 60, 6],
  "bbox_tolerance_pct": 10,
  "min_face_count": 8,
  "min_solid_count": 1,
  "max_solid_count": 1,
  "notes": "four M4 holes"
}
```
"""

MALFORMED_JSON = """\
CAD brief:
- Model: broken

```json
{ this is not valid json,,, }
```
"""

MISSING_FENCE = """\
CAD brief:
- Model: no_json_here
- Task type: new part
"""

WRONG_TYPE_FIELD = """\
CAD brief:
- Model: partial

```json
{
  "bbox_min": "not-a-triplet",
  "bbox_max": [10, 20, 30],
  "min_face_count": "six"
}
```
"""


def test_parse_brief_well_formed():
    brief = parse_brief(WELL_FORMED)
    assert brief.targets.bbox_min is None
    assert brief.targets.bbox_max == (100.0, 60.0, 6.0)
    assert brief.targets.bbox_tolerance_pct == 10.0
    assert brief.targets.min_face_count == 8
    assert brief.targets.min_solid_count == 1
    assert brief.targets.max_solid_count == 1
    assert brief.targets.notes == "four M4 holes"
    assert "mounting_plate" in brief.prose
    assert "```json" not in brief.prose


def test_parse_brief_malformed_json_degrades_to_none_targets():
    brief = parse_brief(MALFORMED_JSON)
    assert brief.targets.bbox_min is None
    assert brief.targets.bbox_max is None
    assert "broken" in brief.prose


def test_parse_brief_missing_fence_degrades_to_none_targets():
    brief = parse_brief(MISSING_FENCE)
    assert brief.targets.bbox_max is None
    assert brief.targets.min_face_count is None
    assert "no_json_here" in brief.prose


def test_parse_brief_wrong_typed_field_only_affects_that_field():
    brief = parse_brief(WRONG_TYPE_FIELD)
    assert brief.targets.bbox_min is None  # wrong type -> degrades
    assert brief.targets.bbox_max == (10.0, 20.0, 30.0)  # still parses
    assert brief.targets.min_face_count is None  # wrong type -> degrades


def test_write_brief_md_writes_raw_verbatim(tmp_path):
    brief = parse_brief(WELL_FORMED)
    path = write_brief_md(tmp_path, brief)
    assert path == tmp_path / "brief.md"
    assert path.read_text().strip() == WELL_FORMED.strip()


ASSEMBLY_BRIEF = """\
CAD brief:
- Model: enclosure assembly
- Task type: assembly (two parts: base and lid)
- Units: millimeters

```json
{
  "bbox_min": null,
  "bbox_max": [120, 80, 35],
  "min_solid_count": 2,
  "max_solid_count": 2
}
```
"""


PART_BRIEF = """\
CAD brief:
- Model: mounting_plate
- Task type: new part
- Units: millimeters

```json
{}
```
"""


def test_parse_brief_is_assembly_true():
    brief = parse_brief(ASSEMBLY_BRIEF)
    assert brief.is_assembly is True


def test_parse_brief_is_assembly_false_for_part():
    brief = parse_brief(PART_BRIEF)
    assert brief.is_assembly is False


def test_parse_brief_is_assembly_false_when_task_type_missing():
    brief = parse_brief(WELL_FORMED)
    assert brief.is_assembly is False


BRIEF_WITH_STRAY_PYTHON = """\
CAD brief:
- Model: phone_stand
- Task type: new part

```python
from build123d import *

with BuildPart() as phone_stand:
    Box(1, 1, 1)

if __name__ == "__main__":
    pass
```

```json
{
  "bbox_min": null,
  "bbox_max": [70, 90, 72],
  "min_solid_count": 1
}
```
"""


def test_parse_brief_strips_stray_python_from_prose():
    brief = parse_brief(BRIEF_WITH_STRAY_PYTHON)
    assert brief.targets.bbox_max == (70.0, 90.0, 72.0)
    assert "phone_stand" in brief.prose
    assert "build123d" not in brief.prose
    assert "__main__" not in brief.prose
    assert "```" not in brief.prose
