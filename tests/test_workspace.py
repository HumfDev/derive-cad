from pathlib import Path

from derive_cad.llm.providers import OPENABLE_ARTIFACTS, PROVIDERS
from derive_cad.project.workspace import (
    allocate_design_dir,
    latest_design_dir,
    list_design_dirs,
    sanitize_folder_name,
)


def test_provider_models_include_default():
    for info in PROVIDERS.values():
        assert info.default_model in info.models


def test_no_retired_gemini_models():
    gemini_models = PROVIDERS["gemini"].models
    assert "gemini/gemini-2.0-flash" not in gemini_models
    assert PROVIDERS["gemini"].default_model == "gemini/gemini-2.5-flash"


def test_openable_artifacts_cover_export_formats():
    assert "step" in OPENABLE_ARTIFACTS
    assert "stl" in OPENABLE_ARTIFACTS
    assert "3mf" in OPENABLE_ARTIFACTS
    assert "glb" in OPENABLE_ARTIFACTS


def test_sanitize_folder_name():
    assert sanitize_folder_name("Phone Stand!") == "phone-stand"
    assert sanitize_folder_name("") == "design"


def test_allocate_design_dir_adds_suffix_for_duplicates(tmp_path: Path):
    working_dir = tmp_path / "projects"
    first = allocate_design_dir(working_dir, "phone-stand")
    second = allocate_design_dir(working_dir, "phone-stand")

    assert first.name == "phone-stand"
    assert second.name == "phone-stand-2"


def test_latest_design_dir_uses_modification_time(tmp_path: Path):
    working_dir = tmp_path / "projects"
    older = working_dir / "older-design"
    newer = working_dir / "newer-design"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    (older / "model.step").write_text("older")
    (newer / "model.step").write_text("newer")

    assert latest_design_dir(working_dir) == newer
    assert list_design_dirs(working_dir)[0] == newer
    assert older in list_design_dirs(working_dir)


def test_latest_design_dir_empty_when_no_designs(tmp_path: Path):
    assert latest_design_dir(tmp_path / "empty") is None
