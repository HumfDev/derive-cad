from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from derive_cad.cad.export import export_format
from derive_cad.cad.inspect import inspect_step
from derive_cad.cad.runner import run_script
from derive_cad.cad.templates import BARE_PIPELINE_SCRIPT
from derive_cad.config.store import resolve_config
from derive_cad.project.workspace import new_run_dir
from derive_cad.utils.errors import ConfigError
from derive_cad.utils.logging import console


def run(
    prompt: str | None = typer.Argument(
        None,
        help=(
            "Describe what to build. Milestone 1 ignores this and always generates "
            "the fixed demo bracket — natural-language generation lands in Milestone 2."
        ),
    ),
) -> None:
    """Generate a CAD model and export it to the configured formats."""
    config = resolve_config(project_dir=Path.cwd())
    if not config.working_dir:
        raise ConfigError("No working folder configured. Run `derivecad init` first.")
    working_dir = Path(config.working_dir).expanduser()
    working_dir.mkdir(parents=True, exist_ok=True)

    if prompt:
        console.print(
            "[yellow]Milestone 1 ignores prompt text — generating the fixed demo "
            "bracket. Natural-language generation is coming in Milestone 2.[/yellow]"
        )

    run_dir = new_run_dir(working_dir, description=prompt or "demo")
    with console.status("Running fixed demo geometry..."):
        result = run_script(
            BARE_PIPELINE_SCRIPT, run_dir=run_dir, timeout_s=config.sandbox_timeout_s
        )
        facts = inspect_step(result.step_path)

        exported = {}
        for fmt in config.default_export_formats:
            out_path = run_dir / f"model.{fmt}"
            exported[fmt] = export_format(result.step_path, out_path, fmt)

    table = Table(show_header=False, box=None)
    table.add_row("STEP", str(result.step_path))
    for fmt, path in exported.items():
        table.add_row(fmt.upper(), str(path))
    bx, by, bz = facts.bbox_size
    table.add_row(
        "Geometry",
        f"bbox: {bx:.1f} x {by:.1f} x {bz:.1f} mm   "
        f"volume: {facts.volume:.1f} mm³   faces: {facts.face_count}",
    )

    console.print(Panel(table, title="✓ Generation complete", style="green"))
