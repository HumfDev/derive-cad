from derive_cad.cad.validation import ValidationTargets
from derive_cad.config.models import Config
from derive_cad.llm.brief import Brief
from derive_cad.llm.review import model_supports_vision, review_snapshots

_BRIEF = Brief(prose="test brief", targets=ValidationTargets(), raw="test brief")


def test_model_supports_vision_true_for_known_vision_model():
    config = Config(provider="openai", model="gpt-4o-mini")
    assert model_supports_vision(config) is True


def test_model_supports_vision_false_for_text_only_model():
    config = Config(provider="ollama", model="ollama/llama3.3")
    assert model_supports_vision(config) is False


def test_model_supports_vision_false_when_no_model_configured():
    config = Config()
    assert model_supports_vision(config) is False


def test_review_snapshots_skips_for_non_vision_model(tmp_path):
    config = Config(provider="ollama", model="ollama/llama3.3")
    result = review_snapshots(config, [], _BRIEF)
    assert result.performed is False
    assert result.passed is True
    assert "vision" in result.notes.lower()


def test_review_snapshots_pass_verdict(monkeypatch, tmp_path):
    config = Config(provider="openai", model="gpt-4o-mini")
    monkeypatch.setattr(
        "derive_cad.llm.review.complete",
        lambda *_args, **_kwargs: "PASS\nLooks correct.",
    )
    png = tmp_path / "iso.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    result = review_snapshots(config, [png], _BRIEF)
    assert result.performed is True
    assert result.passed is True
    assert result.notes == "Looks correct."


def test_review_snapshots_fail_verdict(monkeypatch, tmp_path):
    config = Config(provider="openai", model="gpt-4o-mini")
    monkeypatch.setattr(
        "derive_cad.llm.review.complete",
        lambda *_args, **_kwargs: "FAIL\nHole pattern looks asymmetric.",
    )
    png = tmp_path / "iso.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    result = review_snapshots(config, [png], _BRIEF)
    assert result.performed is True
    assert result.passed is False
    assert "asymmetric" in result.notes


def test_review_snapshots_ambiguous_verdict_fails_open(monkeypatch, tmp_path):
    config = Config(provider="openai", model="gpt-4o-mini")
    monkeypatch.setattr(
        "derive_cad.llm.review.complete",
        lambda *_args, **_kwargs: "Hmm, hard to say.",
    )
    png = tmp_path / "iso.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    result = review_snapshots(config, [png], _BRIEF)
    assert result.performed is True
    assert result.passed is True
    assert "unparsed verdict" in result.notes
