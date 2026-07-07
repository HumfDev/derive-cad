from __future__ import annotations

import sys
from pathlib import Path

import typer

from derive_cad.skill.runner import SkillScriptError, run_skill_script
from derive_cad.utils.errors import DeriveCadError
from derive_cad.utils.logging import console

snapshot_app = typer.Typer(
    help="Render STEP snapshots (skills/cad/scripts/snapshot). Needs Viewer GLB sidecars.",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    no_args_is_help=False,
)


@snapshot_app.callback(invoke_without_command=True)
def snapshot(ctx: typer.Context) -> None:
    """Delegate to skills/cad/scripts/snapshot with passthrough arguments."""
    args = list(ctx.args)
    if not args:
        console.print(
            "[bold]Usage:[/bold] dcad snapshot <target.step> [options]\n"
            "[dim]Requires CAD Viewer GLB sidecars (`.model.step.glb`) from STEP generation.[/dim]"
        )
        raise typer.Exit(code=2)

    try:
        result = run_skill_script("snapshot", args, cwd=Path.cwd(), timeout_s=300)
    except SkillScriptError as exc:
        raise DeriveCadError(str(exc)) from exc

    if result.stdout:
        console.print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        sys.stderr.write(result.stderr)
        if not result.stderr.endswith("\n"):
            sys.stderr.write("\n")
    raise typer.Exit(code=result.returncode)
