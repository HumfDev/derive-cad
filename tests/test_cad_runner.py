import pytest

from derive_cad.cad.runner import run_script
from derive_cad.utils.errors import GenerationError
from cad_scripts import SAMPLE_BRACKET_SCRIPT

pytestmark = pytest.mark.integration


def test_sample_bracket_script_produces_step(tmp_path):
    result = run_script(SAMPLE_BRACKET_SCRIPT, run_dir=tmp_path, timeout_s=60)

    assert result.step_path.exists()
    assert result.step_path.stat().st_size > 0
    assert (tmp_path / "stdout.log").exists()
    assert (tmp_path / "stderr.log").exists()


def test_broken_script_raises_generation_error(tmp_path):
    with pytest.raises(GenerationError):
        run_script("raise RuntimeError('boom')\n", run_dir=tmp_path, timeout_s=60)


def test_timeout_raises_generation_error(tmp_path):
    with pytest.raises(GenerationError, match="timed out"):
        run_script(
            "import time\ntime.sleep(5)\n",
            run_dir=tmp_path,
            timeout_s=1,
        )
