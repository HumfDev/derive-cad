import pytest
from cad_scripts import SAMPLE_BRACKET_SCRIPT

from derive_cad.cad.inspect import inspect_step
from derive_cad.cad.runner import export_sidecars, run_script

pytestmark = pytest.mark.integration


@pytest.fixture
def generated_step(tmp_path):
    result = run_script(SAMPLE_BRACKET_SCRIPT, run_dir=tmp_path, timeout_s=60)
    return result


def test_inspect_known_bracket_dimensions(generated_step):
    facts = inspect_step(generated_step.step_path)

    assert facts.bbox_size == pytest.approx((60.0, 40.0, 14.0), abs=1e-6)
    assert facts.volume > 0
    assert facts.face_count > 0
    assert not facts.is_degenerate


def test_step_to_stl(generated_step):
    paths = export_sidecars(generated_step.script_path, ["stl"], timeout_s=120)
    stl_path = paths["stl"]
    assert stl_path.exists()
    assert stl_path.stat().st_size > 0


def test_step_to_3mf(generated_step):
    paths = export_sidecars(generated_step.script_path, ["3mf"], timeout_s=120)
    threemf_path = paths["3mf"]
    assert threemf_path.exists()
    assert threemf_path.stat().st_size > 0


def test_step_to_glb(generated_step):
    paths = export_sidecars(generated_step.script_path, ["glb"], timeout_s=120)
    glb_path = paths["glb"]
    assert glb_path.exists()
    assert glb_path.stat().st_size > 0
