from derive_cad.cad.inspect import GeometryFacts
from derive_cad.cad.validation import ValidationTargets, check_validation_targets


def _facts(**overrides):
    defaults = dict(
        bbox_size=(100.0, 60.0, 6.0),
        volume=1000.0,
        face_count=10,
        edge_count=20,
        vertex_count=10,
        solid_count=1,
    )
    defaults.update(overrides)
    return GeometryFacts(**defaults)


def test_all_none_targets_always_passes():
    facts = _facts()
    assert check_validation_targets(facts, ValidationTargets()) == []


def test_bbox_within_tolerance_passes():
    facts = _facts(bbox_size=(102.0, 59.0, 6.0))
    targets = ValidationTargets(bbox_max=(100.0, 60.0, 6.0), bbox_tolerance_pct=10.0)
    assert check_validation_targets(facts, targets) == []


def test_bbox_exceeds_max_flagged():
    facts = _facts(bbox_size=(150.0, 60.0, 6.0))
    targets = ValidationTargets(bbox_max=(100.0, 60.0, 6.0), bbox_tolerance_pct=10.0)
    violations = check_validation_targets(facts, targets)
    assert len(violations) == 1
    assert violations[0].kind == "bbox"
    assert "X size" in violations[0].message


def test_bbox_below_min_flagged():
    facts = _facts(bbox_size=(50.0, 60.0, 6.0))
    targets = ValidationTargets(bbox_min=(100.0, 60.0, 6.0), bbox_tolerance_pct=10.0)
    violations = check_validation_targets(facts, targets)
    assert len(violations) == 1
    assert violations[0].kind == "bbox"


def test_default_tolerance_used_when_not_specified():
    facts = _facts(bbox_size=(112.0, 60.0, 6.0))
    targets = ValidationTargets(bbox_max=(100.0, 60.0, 6.0))
    violations = check_validation_targets(facts, targets, default_tolerance_pct=15.0)
    assert violations == []


def test_min_face_count_flagged():
    facts = _facts(face_count=4)
    targets = ValidationTargets(min_face_count=6)
    violations = check_validation_targets(facts, targets)
    assert len(violations) == 1
    assert violations[0].kind == "face_count"


def test_min_solid_count_flagged():
    facts = _facts(solid_count=0)
    targets = ValidationTargets(min_solid_count=1)
    violations = check_validation_targets(facts, targets)
    assert len(violations) == 1
    assert violations[0].kind == "solid_count"


def test_max_solid_count_flagged():
    facts = _facts(solid_count=3)
    targets = ValidationTargets(max_solid_count=1)
    violations = check_validation_targets(facts, targets)
    assert len(violations) == 1
    assert violations[0].kind == "solid_count"
