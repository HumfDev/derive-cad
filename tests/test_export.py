import pytest

from derive_cad.cad.export import step_to_3mf, step_to_glb, step_to_stl
from derive_cad.cad.inspect import inspect_step
from derive_cad.cad.runner import run_script
from derive_cad.cad.templates import BARE_PIPELINE_SCRIPT

pytestmark = pytest.mark.integration


@pytest.fixture
def generated_step(tmp_path):
    result = run_script(BARE_PIPELINE_SCRIPT, run_dir=tmp_path, timeout_s=60)
    return result.step_path


def test_inspect_known_bracket_dimensions(generated_step):
    facts = inspect_step(generated_step)

    assert facts.bbox_size == pytest.approx((60.0, 40.0, 14.0), abs=1e-6)
    assert facts.volume > 0
    assert facts.face_count > 0
    assert not facts.is_degenerate


def test_step_to_stl(generated_step, tmp_path):
    stl_path = step_to_stl(generated_step, tmp_path / "model.stl")
    assert stl_path.exists()
    assert stl_path.stat().st_size > 0


def test_step_to_3mf(generated_step, tmp_path):
    threemf_path = step_to_3mf(generated_step, tmp_path / "model.3mf")
    assert threemf_path.exists()
    assert threemf_path.stat().st_size > 0


def test_step_to_glb(generated_step, tmp_path):
    glb_path = step_to_glb(generated_step, tmp_path / "model.glb")
    assert glb_path.exists()
    assert glb_path.stat().st_size > 0
