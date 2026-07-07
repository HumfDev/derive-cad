from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from derive_cad.cad.export import export_format
from derive_cad.cad.inspect import inspect_step
from derive_cad.cli.setup import ensure_configured
from derive_cad.config.models import Config
from derive_cad.llm.generate import GenerationOutcome, generate_model_from_prompt
from derive_cad.llm.naming import suggest_design_name
from derive_cad.project.workspace import new_design_dir
from derive_cad.utils.errors import ConfigError
from derive_cad.utils.logging import configure_run_logging, console, log_section, logger


def _export_and_report(
    config: Config,
    design_dir: Path,
    outcome: GenerationOutcome,
) -> GenerationOutcome:
    result = outcome.result
    facts = inspect_step(result.step_path)

    exported = {}
    for fmt in config.default_export_formats:
        out_path = design_dir / f"model.{fmt}"
        exported[fmt] = export_format(result.step_path, out_path, fmt)

    table = Table(show_header=False, box=None)
    table.add_row("Folder", str(design_dir))
    table.add_row("STEP", str(result.step_path))
    for fmt, path in exported.items():
        table.add_row(fmt.upper(), str(path))
    bx, by, bz = facts.bbox_size
    table.add_row(
        "Geometry",
        f"bbox: {bx:.1f} x {by:.1f} x {bz:.1f} mm   "
        f"volume: {facts.volume:.1f} mm³   faces: {facts.face_count}",
    )
    table.add_row("Brief", str(design_dir / "brief.md"))
    if outcome.validation_violations:
        table.add_row(
            "Validation targets",
            f"[yellow]{len(outcome.validation_violations)} unresolved[/yellow]",
        )
    table.add_row(
        "Snapshots",
        ", ".join(str(p) for p in outcome.snapshot_paths) or "[dim]none[/dim]",
    )
    if outcome.review.performed:
        style = "green" if outcome.review.passed else "yellow"
        table.add_row("Visual review", f"[{style}]{outcome.review.notes[:200]}[/{style}]")
    else:
        table.add_row("Visual review", f"[dim]skipped — {outcome.review.notes}[/dim]")

    console.print(Panel(table, title="✓ Generation complete", style="green"))
    console.print(
        "[dim]Open outputs: [bold]dcad open stl[/bold] · "
        "[bold]dcad open recent[/bold][/dim]"
    )
    return outcome


def generate_model(config: Config, prompt: str) -> GenerationOutcome:
    """Generate a CAD model from a natural-language prompt via the configured LLM."""
    working_dir = Path(config.working_dir).expanduser()
    working_dir.mkdir(parents=True, exist_ok=True)

    with console.status("Naming design folder..."):
        folder_name = suggest_design_name(config, prompt)
        design_dir = new_design_dir(working_dir, folder_name)

    run_log = configure_run_logging(design_dir)
    log_section(
        "RUN START",
        f"prompt: {prompt}\n"
        f"provider: {config.provider}\n"
        f"model: {config.model}\n"
        f"working_dir: {working_dir}\n"
        f"design_dir: {design_dir}\n"
        f"log_file: {run_log}",
    )
    logger.info("User prompt: %s", prompt)

    with console.status(f"Generating design with {config.model}..."):
        outcome = generate_model_from_prompt(
            config,
            prompt,
            design_dir,
            timeout_s=config.sandbox_timeout_s,
        )

    return _export_and_report(config, design_dir, outcome)


def run(
    prompt: str = typer.Argument(
        ...,
        help="Describe what to build in plain English.",
    ),
) -> None:
    """Generate a CAD model and export it to the configured formats."""
    cleaned = prompt.strip()
    if not cleaned:
        raise ConfigError(
            'Describe what to build. Example: [bold]dcad run "phone stand with 45° angle"[/bold]'
        )

    config = ensure_configured(standalone_setup=False)
    generate_model(config, prompt=cleaned)
