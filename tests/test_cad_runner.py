import pytest
from cad_scripts import SAMPLE_BRACKET_SCRIPT

from derive_cad.cad.runner import run_script
from derive_cad.utils.errors import GenerationError

pytestmark = pytest.mark.integration


def test_sample_bracket_script_produces_step(tmp_path):
    result = run_script(SAMPLE_BRACKET_SCRIPT, run_dir=tmp_path, timeout_s=60)

    assert result.step_path.exists()
    assert result.step_path.stat().st_size > 0
    assert (tmp_path / "stdout.log").exists()
    assert (tmp_path / "stderr.log").exists()


def test_broken_script_raises_generation_error(tmp_path):
    script = """\
from build123d import *


def gen_step() -> Part:
    raise RuntimeError('boom')
"""
    with pytest.raises(GenerationError):
        run_script(script, run_dir=tmp_path, timeout_s=60)


def test_timeout_raises_generation_error(tmp_path):
    script = """\
from build123d import *
import time


def gen_step() -> Part:
    time.sleep(5)
    with BuildPart() as part:
        Box(1, 1, 1)
    return part.part
"""
    with pytest.raises(GenerationError, match="timed out"):
        run_script(script, run_dir=tmp_path, timeout_s=1)
