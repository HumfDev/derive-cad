from __future__ import annotations

import sys
from pathlib import Path

import typer

from derive_cad.skill.runner import SkillScriptError, run_skill_script
from derive_cad.utils.errors import DeriveCadError
from derive_cad.utils.logging import console

inspect_app = typer.Typer(
    help="Inspect STEP geometry — refs, measure, align, frame, diff (skills/cad/scripts/inspect).",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    no_args_is_help=False,
)


@inspect_app.callback(invoke_without_command=True)
def inspect(ctx: typer.Context) -> None:
    """Delegate to skills/cad/scripts/inspect with passthrough arguments."""
    args = list(ctx.args)
    if not args:
        console.print(
            "[bold]Usage:[/bold] dcad inspect <subcommand> <target> [options]\n"
            "Example: dcad inspect refs model.step --facts --planes --positioning"
        )
        raise typer.Exit(code=2)

    try:
        result = run_skill_script("inspect", args, cwd=Path.cwd(), timeout_s=120)
    except SkillScriptError as exc:
        raise DeriveCadError(str(exc)) from exc

    if result.stdout:
        console.print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        sys.stderr.write(result.stderr)
        if not result.stderr.endswith("\n"):
            sys.stderr.write("\n")
    raise typer.Exit(code=result.returncode)
