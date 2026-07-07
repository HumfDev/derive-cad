from derive_cad.config.models import Config
from derive_cad.llm.naming import sanitize_folder_name, suggest_design_name


def test_suggest_design_name_fallback_without_provider():
    config = Config()
    name = suggest_design_name(config, "phone stand with 45 degree angle")
    assert name == "phone-stand-with-45-degree-angle"


def test_suggest_design_name_uses_llm_response(monkeypatch):
    config = Config(provider="openai", model="gpt-4o-mini")

    monkeypatch.setattr(
        "derive_cad.llm.naming.complete",
        lambda *_args, **_kwargs: "angled-phone-stand",
    )
    assert suggest_design_name(config, "phone stand") == "angled-phone-stand"


def test_suggest_design_name_falls_back_when_llm_fails(monkeypatch):
    config = Config(provider="openai", model="gpt-4o-mini")

    def fake_complete(*_args, **_kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("derive_cad.llm.naming.complete", fake_complete)
    assert suggest_design_name(config, "gear box") == "gear-box"


def test_sanitize_folder_name_strips_invalid_characters():
    assert sanitize_folder_name('  "Bracket Demo"  ') == "bracket-demo"
