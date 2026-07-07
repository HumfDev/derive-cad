from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from derive_cad.cad.sandbox import run_isolated
from derive_cad.project.workspace import python_executable
from derive_cad.skill.paths import cad_script_main
from derive_cad.utils.errors import DeriveCadError


class SkillScriptError(DeriveCadError):
    pass


@dataclass
class SkillScriptResult:
    returncode: int
    stdout: str
    stderr: str


def run_skill_script(
    tool: str,
    args: list[str],
    *,
    cwd: Path,
    timeout_s: int = 120,
) -> SkillScriptResult:
    """Run a vendored skills/cad script with cwd-relative targets."""
    script = cad_script_main(tool)
    cmd = [python_executable(), str(script), *args]
    try:
        completed = run_isolated(cmd, cwd=cwd, timeout_s=timeout_s)
    except subprocess.TimeoutExpired as exc:
        raise SkillScriptError(
            f"skills/cad/scripts/{tool} timed out after {timeout_s}s."
        ) from exc

    return SkillScriptResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def run_skill_script_or_raise(
    tool: str,
    args: list[str],
    *,
    cwd: Path,
    timeout_s: int = 120,
) -> SkillScriptResult:
    result = run_skill_script(tool, args, cwd=cwd, timeout_s=timeout_s)
    if result.returncode != 0:
        tail = result.stderr[-2000:] or result.stdout[-2000:]
        raise SkillScriptError(
            f"skills/cad/scripts/{tool} failed (exit {result.returncode}):\n{tail}"
        )
    return result
