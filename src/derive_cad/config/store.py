from pathlib import Path
from typing import Any

from derive_cad.config.models import Config
from derive_cad.config.paths import (
    config_path,
    ensure_home_dir,
    project_config_path,
)
from derive_cad.config.toml_io import read_toml, write_toml


def load_global_config() -> Config:
    return Config(**read_toml(config_path()))


def save_global_config(config: Config) -> Path:
    ensure_home_dir()
    path = config_path()
    write_toml(path, config.model_dump(exclude_none=True))
    return path


def load_project_config(project_dir: Path) -> dict[str, Any]:
    return read_toml(project_config_path(project_dir))


def resolve_config(
    project_dir: Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> Config:
    """Merge config layers with documented precedence:
    CLI flags > per-project .derivecad.toml > global config > built-in defaults.

    (Env vars are handled separately for API keys only, in config.secrets.)
    """
    merged: dict[str, Any] = {}
    merged.update(load_global_config().model_dump(exclude_none=True))
    if project_dir is not None:
        merged.update(load_project_config(project_dir))
    if cli_overrides:
        merged.update({k: v for k, v in cli_overrides.items() if v is not None})
    return Config(**merged)
