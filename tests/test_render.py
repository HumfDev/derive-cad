import sys

import numpy as np
import pytest
from cad_scripts import SAMPLE_BRACKET_SCRIPT
from PIL import Image

from derive_cad.cad.render import DEFAULT_VIEWS, render_snapshots
from derive_cad.cad.runner import run_script

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        sys.platform == "linux",
        reason="Playwright snapshot rendering is validated on macOS CI runners.",
    ),
]


@pytest.fixture
def generated_step(tmp_path):
    result = run_script(SAMPLE_BRACKET_SCRIPT, run_dir=tmp_path, timeout_s=60)
    return result.step_path


def test_render_snapshots_produces_expected_views(generated_step, tmp_path):
    paths = render_snapshots(generated_step, tmp_path)

    assert len(paths) == len(DEFAULT_VIEWS)
    for path in paths:
        assert path.exists()
        assert path.stat().st_size > 0

        # A silently-blank render would have near-zero pixel variance.
        image = np.asarray(Image.open(path).convert("L"))
        assert image.std() > 1.0
