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

_ASSEMBLY_BRIEF = Brief(
    prose="CAD brief:\n- Task type: assembly\n",
    targets=ValidationTargets(),
    raw="CAD brief:\n- Task type: assembly\n",
)


def _design_dir(tmp_path):
    run_dir = tmp_path / "cube"
    run_dir.mkdir(exist_ok=True)
    return run_dir


def _config(tmp_path):
    from derive_cad.config.models import Config

    return Config(
        provider="openai",
        model="gpt-4o-mini",
        working_dir=str(tmp_path),
        enable_snapshot_review=False,
        max_repair_attempts=1,
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


def test_request_script_uses_assembly_codegen_prompt(monkeypatch, tmp_path):
    from derive_cad.llm.generate import _request_script

    captured: dict[str, str] = {}

    def fake_complete(_config, messages, *, log_label):
        captured["system"] = messages[0]["content"]
        return VALID_SCRIPT

    monkeypatch.setattr("derive_cad.llm.generate.complete", fake_complete)
    _request_script(_config(tmp_path), _ASSEMBLY_BRIEF, "two-piece enclosure")
    assert "AssemblyHelper pattern" in captured["system"]


@pytest.mark.integration
def test_generate_model_from_prompt_full_pipeline_with_snapshot_review(
    monkeypatch, tmp_path, derivecad_home
):
    """End-to-end: real sandbox execution; LLM seams and snapshot render mocked."""
    from derive_cad.config.models import Config
    from derive_cad.llm.review import ReviewResult

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
    run_dir = _design_dir(tmp_path)
    fake_snapshots = [
        run_dir / "snapshots" / "iso.png",
        run_dir / "snapshots" / "top_ortho.png",
    ]
    for path in fake_snapshots:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"png")

    monkeypatch.setattr(
        "derive_cad.llm.repair_loop.render_snapshots",
        lambda *_args, **_kwargs: fake_snapshots,
    )
    monkeypatch.setattr(
        "derive_cad.llm.repair_loop.review_snapshots",
        lambda *_args, **_kwargs: ReviewResult(performed=True, passed=True, notes="ok"),
    )

    outcome = generate_model_from_prompt(
        config,
        "a small cube",
        run_dir,
        timeout_s=60,
    )
    assert outcome.result.step_path.exists()
    assert len(outcome.snapshot_paths) == 2
    assert outcome.review.performed is True
    assert outcome.review.passed is True


def test_generate_accepts_advisory_visual_fail(monkeypatch, tmp_path, derivecad_home):
    """Vision FAIL is advisory when deterministic validation passes."""
    from derive_cad.config.models import Config
    from derive_cad.llm.review import ReviewResult

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
    run_dir = _design_dir(tmp_path)
    fake_snapshots = [run_dir / "snapshots" / "iso.png"]
    fake_snapshots[0].parent.mkdir(parents=True, exist_ok=True)
    fake_snapshots[0].write_bytes(b"png")

    monkeypatch.setattr(
        "derive_cad.llm.repair_loop.render_snapshots",
        lambda *_args, **_kwargs: fake_snapshots,
    )
    monkeypatch.setattr(
        "derive_cad.llm.repair_loop.review_snapshots",
        lambda *_args, **_kwargs: ReviewResult(
            performed=True,
            passed=False,
            notes="hole pattern looks asymmetric",
        ),
    )

    outcome = generate_model_from_prompt(
        config,
        "a small cube",
        run_dir,
        timeout_s=60,
    )
    assert outcome.attempts == 1
    assert outcome.review.performed is True
    assert outcome.review.passed is False
    assert outcome.result.step_path.exists()


def test_generate_repair_reruns_step_when_script_changes(monkeypatch, tmp_path, derivecad_home):
    from derive_cad.cad.validation import Violation
    from derive_cad.config.models import Config

    config = Config(
        provider="openai",
        model="gpt-4o-mini",
        working_dir=str(tmp_path),
        enable_snapshot_review=False,
        max_repair_attempts=2,
    )
    monkeypatch.setattr("derive_cad.llm.generate.generate_brief", lambda *_: _STUB_BRIEF)
    monkeypatch.setattr(
        "derive_cad.llm.generate._request_script",
        lambda _config, _brief, _prompt: VALID_SCRIPT,
    )

    repaired_script = VALID_SCRIPT.replace("Box(10, 10, 10)", "Box(12, 12, 12)")
    step_calls = {"n": 0}
    validate_calls = {"n": 0}
    run_dir = _design_dir(tmp_path)

    def fake_run_step_stage(script, *, run_dir, timeout_s, prev_result, repair_log):
        step_calls["n"] += 1
        from derive_cad.cad.runner import run_script

        return run_script(script, run_dir=run_dir, timeout_s=timeout_s)

    def fake_validate(_config, _brief, result):
        validate_calls["n"] += 1
        if validate_calls["n"] == 1:
            return [Violation("bbox", "too big")], None
        return [], None

    monkeypatch.setattr("derive_cad.llm.generate.run_step_stage", fake_run_step_stage)
    monkeypatch.setattr("derive_cad.llm.generate._validate_generated_model", fake_validate)
    monkeypatch.setattr(
        "derive_cad.llm.generate.request_repair_script",
        lambda _config, *, ctx, brief, prompt: repaired_script,
    )

    outcome = generate_model_from_prompt(
        config,
        "a small cube",
        run_dir,
        timeout_s=60,
    )
    assert outcome.attempts == 2
    assert step_calls["n"] == 2


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


def test_generate_repair_stalemate(monkeypatch, tmp_path, derivecad_home):
    """Repeated identical STEP failures stop after repair_stalemate_limit."""
    from derive_cad.config.models import Config

    config = Config(
        provider="openai",
        model="gpt-4o-mini",
        working_dir=str(tmp_path),
        enable_snapshot_review=False,
        repair_stalemate_limit=2,
    )
    monkeypatch.setattr("derive_cad.llm.generate.generate_brief", lambda *_: _STUB_BRIEF)
    monkeypatch.setattr(
        "derive_cad.llm.generate._request_script",
        lambda _config, _brief, _prompt: BAD_SCRIPT,
    )
    repair_calls = {"n": 0}

    def fake_repair(_config, *, ctx, brief, prompt):
        repair_calls["n"] += 1
        return BAD_SCRIPT

    monkeypatch.setattr("derive_cad.llm.generate.request_repair_script", fake_repair)

    with pytest.raises(GenerationError, match="stalemate"):
        generate_model_from_prompt(
            config,
            "a cube",
            _design_dir(tmp_path),
            timeout_s=60,
        )
    assert repair_calls["n"] == 1
