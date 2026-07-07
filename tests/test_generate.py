import pytest

from derive_cad.cad.validation import ValidationTargets
from derive_cad.llm.brief import Brief
from derive_cad.llm.client import extract_python_code, validate_script_structure
from derive_cad.llm.generate import generate_model_from_prompt
from derive_cad.utils.errors import GenerationError

BAD_SCRIPT = """\
from build123d import *


def gen_step() -> Part:
    raise RuntimeError('bad')
"""

VALID_SCRIPT = """\
from build123d import *


def gen_step() -> Part:
    with BuildPart() as part:
        Box(10, 10, 10)
    return part.part
"""

_STUB_BRIEF = Brief(prose="test brief", targets=ValidationTargets(), raw="test brief")


def _design_dir(tmp_path):
    run_dir = tmp_path / "cube"
    run_dir.mkdir()
    return run_dir


def _config(tmp_path):
    from derive_cad.config.models import Config

    return Config(
        provider="openai",
        model="gpt-4o-mini",
        working_dir=str(tmp_path),
        enable_snapshot_review=False,
    )


def test_extract_python_code_from_fence():
    raw = "Here is the code:\n```python\nprint('hi')\n```"
    assert extract_python_code(raw) == "print('hi')"


def test_extract_python_code_plain():
    assert extract_python_code("print('hi')") == "print('hi')"


def test_validate_script_structure_accepts_valid_script():
    validate_script_structure(VALID_SCRIPT)


def test_validate_script_structure_rejects_missing_gen_step():
    script = """\
from build123d import *

def something_else() -> Part:
    return Box(1, 1, 1)
"""
    with pytest.raises(ValueError, match="gen_step"):
        validate_script_structure(script)


def test_generate_model_from_prompt_runs_llm_script(monkeypatch, tmp_path, derivecad_home):
    monkeypatch.setattr("derive_cad.llm.generate.generate_brief", lambda *_: _STUB_BRIEF)
    monkeypatch.setattr(
        "derive_cad.llm.generate._request_script",
        lambda _config, _brief, _prompt: VALID_SCRIPT,
    )

    outcome = generate_model_from_prompt(
        _config(tmp_path),
        "a small cube",
        _design_dir(tmp_path),
        timeout_s=60,
    )
    assert outcome.result.step_path.exists()
    assert outcome.validation_violations == []
    assert not outcome.review.performed


@pytest.mark.integration
def test_generate_model_from_prompt_full_pipeline_with_snapshot_review(
    monkeypatch, tmp_path, derivecad_home
):
    """End-to-end: real sandbox execution and real matplotlib snapshot rendering,
    with only the LLM-calling seams (brief, codegen, vision review) mocked."""
    from derive_cad.config.models import Config

    config = Config(
        provider="openai",
        model="gpt-4o-mini",
        working_dir=str(tmp_path),
        enable_snapshot_review=True,
    )
    monkeypatch.setattr("derive_cad.llm.generate.generate_brief", lambda *_: _STUB_BRIEF)
    monkeypatch.setattr(
        "derive_cad.llm.generate._request_script",
        lambda _config, _brief, _prompt: VALID_SCRIPT,
    )
    monkeypatch.setattr(
        "derive_cad.llm.review.complete",
        lambda *_args, **_kwargs: "PASS\nLooks correct.",
    )

    outcome = generate_model_from_prompt(
        config,
        "a small cube",
        _design_dir(tmp_path),
        timeout_s=60,
    )
    assert outcome.result.step_path.exists()
    assert len(outcome.snapshot_paths) == 3
    for path in outcome.snapshot_paths:
        assert path.exists()
        assert path.stat().st_size > 0
    assert outcome.review.performed is True
    assert outcome.review.passed is True


def test_generate_model_raises_on_invalid_structure(monkeypatch, tmp_path, derivecad_home):
    monkeypatch.setattr("derive_cad.llm.generate.generate_brief", lambda *_: _STUB_BRIEF)
    invalid_script = "from build123d import *\n\ndef not_gen_step():\n    pass\n"
    monkeypatch.setattr(
        "derive_cad.llm.generate._request_script",
        lambda _config, _brief, _prompt: invalid_script,
    )

    with pytest.raises(GenerationError, match="structure validation"):
        generate_model_from_prompt(
            _config(tmp_path),
            "a cube",
            _design_dir(tmp_path),
            timeout_s=60,
        )


def test_generate_model_raises_on_sandbox_failure(monkeypatch, tmp_path, derivecad_home):
    monkeypatch.setattr("derive_cad.llm.generate.generate_brief", lambda *_: _STUB_BRIEF)
    monkeypatch.setattr(
        "derive_cad.llm.generate._request_script",
        lambda _config, _brief, _prompt: BAD_SCRIPT,
    )

    with pytest.raises(GenerationError):
        generate_model_from_prompt(
            _config(tmp_path),
            "a cube",
            _design_dir(tmp_path),
            timeout_s=60,
        )
