"""Vendored skills/cad integration — paths and script runners."""

from derive_cad.skill.paths import cad_skill_dir, repo_root
from derive_cad.skill.runner import SkillScriptError, run_skill_script

__all__ = [
    "cad_skill_dir",
    "repo_root",
    "run_skill_script",
    "SkillScriptError",
]
