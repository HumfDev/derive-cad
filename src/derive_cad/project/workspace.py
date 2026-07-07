import platform
import subprocess
import sys
from pathlib import Path


def sanitize_folder_name(name: str, max_len: int = 48) -> str:
    """Re-export for tests; canonical implementation lives in llm.naming."""
    from derive_cad.llm.naming import sanitize_folder_name as _sanitize

    return _sanitize(name, max_len=max_len)


def allocate_design_dir(working_dir: Path, name: str) -> Path:
    """Create a new design folder directly under the working directory."""
    working_dir.mkdir(parents=True, exist_ok=True)
    base = sanitize_folder_name(name)
    candidate = working_dir / base
    if not candidate.exists():
        candidate.mkdir(parents=True)
        return candidate

    suffix = 2
    while True:
        candidate = working_dir / f"{base}-{suffix}"
        if not candidate.exists():
            candidate.mkdir(parents=True)
            return candidate
        suffix += 1


def new_design_dir(working_dir: Path, name: str) -> Path:
    """Allocate a human-readable design folder for one generation attempt."""
    return allocate_design_dir(working_dir, name)


def _is_design_dir(path: Path) -> bool:
    return path.is_dir() and not path.name.startswith(".") and (path / "model.step").is_file()


def list_design_dirs(working_dir: Path) -> list[Path]:
    """Return design folders newest-first (by last modified time)."""
    if not working_dir.is_dir():
        return []

    designs: list[Path] = []
    for path in working_dir.iterdir():
        if _is_design_dir(path):
            designs.append(path)

    return sorted(designs, key=lambda path: path.stat().st_mtime, reverse=True)


def latest_design_dir(working_dir: Path) -> Path | None:
    designs = list_design_dirs(working_dir)
    return designs[0] if designs else None


# Backward-compatible aliases used elsewhere in the CLI.
list_run_dirs = list_design_dirs
latest_run_dir = latest_design_dir


def open_path(path: Path) -> None:
    """Open a file or folder with the platform default handler."""
    resolved = path.resolve()
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", str(resolved)], check=True)
    elif system == "Windows":
        subprocess.run(["explorer", str(resolved)], check=True)
    else:
        subprocess.run(["xdg-open", str(resolved)], check=True)


def python_executable() -> str:
    return sys.executable
