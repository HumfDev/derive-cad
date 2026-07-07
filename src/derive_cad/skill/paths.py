from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """Return the repository root containing skills/cad."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "skills" / "cad" / "SKILL.md").is_file():
            return parent
    raise RuntimeError(
        "skills/cad not found. Ensure the upstream skills/cad folder is present at repo root."
    )


def cad_skill_dir() -> Path:
    return repo_root() / "skills" / "cad"


def cad_script_main(tool: str) -> Path:
    path = cad_skill_dir() / "scripts" / tool / "__main__.py"
    if not path.is_file():
        raise RuntimeError(f"Missing skills/cad script entrypoint: {path}")
    return path


def reference_doc(name: str) -> Path:
    path = cad_skill_dir() / "references" / name
    if not path.is_file():
        raise RuntimeError(f"Missing skills/cad reference: {path}")
    return path


def step_parts_dir() -> Path:
    return repo_root() / "skills" / "step-parts"


def step_parts_script() -> Path:
    path = step_parts_dir() / "scripts" / "download_step_part.py"
    if not path.is_file():
        raise RuntimeError(f"Missing skills/step-parts script: {path}")
    return path
