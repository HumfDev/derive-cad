from __future__ import annotations

from pathlib import Path

import typer

from derive_cad.skill.runner import SkillScriptError, run_skill_script
from derive_cad.utils.errors import DeriveCadError
from derive_cad.utils.logging import console

step_app = typer.Typer(
    help="Generate STEP and sidecar exports from build123d source (skills/cad/scripts/step).",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    no_args_is_help=False,
)


@step_app.callback(invoke_without_command=True)
def step(ctx: typer.Context) -> None:
    """Delegate to skills/cad/scripts/step with passthrough arguments."""
    args = list(ctx.args)
    if not args:
        console.print(
            "[bold]Usage:[/bold] dcad step <targets...> [options]\n"
            "Example: dcad step model.py -o model.step --stl model.stl"
        )
        raise typer.Exit(code=2)

    try:
        result = run_skill_script("step", args, cwd=Path.cwd(), timeout_s=300)
    except SkillScriptError as exc:
        raise DeriveCadError(str(exc)) from exc

    if result.stdout:
        console.print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        sys.stderr.write(result.stderr)
        if not result.stderr.endswith("\n"):
            sys.stderr.write("\n")
    raise typer.Exit(code=result.returncode)


import sys  # noqa: E402
