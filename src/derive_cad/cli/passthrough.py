from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import typer

from derive_cad.skill.runner import SkillScriptError, run_skill_script
from derive_cad.utils.errors import DeriveCadError
from derive_cad.utils.logging import console

PASSTHROUGH_CONTEXT = {
    "allow_extra_args": True,
    "ignore_unknown_options": True,
}


def passthrough_command(
    *,
    tool: str,
    usage: str,
    timeout_s: int = 120,
) -> Callable[[typer.Context], None]:
    def handler(ctx: typer.Context) -> None:
        args = list(ctx.args)
        if not args:
            console.print(usage)
            raise typer.Exit(code=2)

        try:
            result = run_skill_script(tool, args, cwd=Path.cwd(), timeout_s=timeout_s)
        except SkillScriptError as exc:
            raise DeriveCadError(str(exc)) from exc

        if result.stdout:
            console.print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            sys.stderr.write(result.stderr)
            if not result.stderr.endswith("\n"):
                sys.stderr.write("\n")
        raise typer.Exit(code=result.returncode)

    return handler
