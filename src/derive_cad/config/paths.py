import os
from pathlib import Path


def home_dir() -> Path:
    """The derivecad home directory (~/.derivecad by default).

    Overridable via DERIVECAD_HOME, primarily for tests and CI, so nothing
    ever touches a real user's home directory during automated runs.
    """
    override = os.environ.get("DERIVECAD_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".derivecad"


def config_path() -> Path:
    return home_dir() / "config.toml"


def credentials_path() -> Path:
    return home_dir() / "credentials.toml"


def project_config_filename() -> str:
    return ".derivecad.toml"


def project_config_path(project_dir: Path) -> Path:
    return project_dir / project_config_filename()


def ensure_home_dir() -> Path:
    directory = home_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory
