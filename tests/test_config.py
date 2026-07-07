from derive_cad.config.models import Config
from derive_cad.config.store import (
    load_global_config,
    resolve_config,
    save_global_config,
)


def test_default_config_when_nothing_saved(derivecad_home):
    config = load_global_config()
    assert config.provider is None
    assert config.sandbox_timeout_s == 60
    assert config.default_export_formats == ["stl"]


def test_save_and_round_trip(derivecad_home):
    original = Config(provider="openai", model="gpt-4o-mini", working_dir="/tmp/proj")
    path = save_global_config(original)
    assert path.exists()

    reloaded = load_global_config()
    assert reloaded.provider == "openai"
    assert reloaded.model == "gpt-4o-mini"
    assert reloaded.working_dir == "/tmp/proj"


def test_per_project_override_precedence(derivecad_home, tmp_path):
    save_global_config(Config(provider="openai", model="gpt-4o-mini"))

    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    (project_dir / ".derivecad.toml").write_bytes(b'model = "gpt-4o"\n')

    resolved = resolve_config(project_dir=project_dir)
    assert resolved.provider == "openai"  # inherited from global
    assert resolved.model == "gpt-4o"  # overridden per-project


def test_cli_flag_beats_everything(derivecad_home, tmp_path):
    save_global_config(Config(provider="openai", model="gpt-4o-mini"))
    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    (project_dir / ".derivecad.toml").write_bytes(b'model = "gpt-4o"\n')

    resolved = resolve_config(project_dir=project_dir, cli_overrides={"model": "claude-haiku-4-5"})
    assert resolved.model == "claude-haiku-4-5"


def test_max_generation_attempts_migrates_to_max_repair_attempts(derivecad_home):
    import warnings

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        config = Config(max_generation_attempts=7)
    assert config.max_repair_attempts == 7
    assert any("max_generation_attempts is deprecated" in str(w.message) for w in caught)


def test_default_repair_is_unlimited(derivecad_home):
    config = load_global_config()
    assert config.max_repair_attempts is None
    assert config.repair_stalemate_limit == 5
