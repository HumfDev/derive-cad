from collections.abc import Callable
from dataclasses import dataclass

import questionary
from rich.panel import Panel
from rich.table import Table

from derive_cad.cli.init_cmd import init
from derive_cad.cli.open_cmd import open_3mf, open_glb, open_py, open_recent, open_step, open_stl
from derive_cad.cli.run_cmd import run
from derive_cad.utils.logging import console


@dataclass(frozen=True)
class CommandSpec:
    invocation: str
    description: str


def _run_with_prompt() -> None:
    prompt = questionary.text("Describe what to build:").ask()
    if prompt is None:
        raise SystemExit(1)
    run(prompt)


COMMAND_CATALOG: tuple[CommandSpec, ...] = (
    CommandSpec(
        "run",
        "Full SKILL.md workflow — brief, codegen, step, inspect, snapshot, repair.",
    ),
    CommandSpec(
        "step",
        "Generate STEP/sidecars from model.py (skills/cad/scripts/step).",
    ),
    CommandSpec(
        "inspect",
        "Inspect STEP geometry — refs, measure, align (skills/cad/scripts/inspect).",
    ),
    CommandSpec(
        "snapshot",
        "Render snapshots from STEP (requires Viewer GLB sidecars).",
    ),
    CommandSpec(
        "init",
        "Reconfigure your LLM provider and working folder.",
    ),
    CommandSpec(
        "open recent",
        "Open the folder containing the most recent design.",
    ),
    CommandSpec(
        "open stl",
        "Open the STL file from the most recent design.",
    ),
    CommandSpec(
        "open step",
        "Open the STEP file from the most recent design.",
    ),
    CommandSpec(
        "open 3mf",
        "Open the 3MF file from the most recent design.",
    ),
    CommandSpec(
        "open glb",
        "Open the GLB file from the most recent design.",
    ),
    CommandSpec(
        "open py",
        "Open the generated build123d script from the most recent design.",
    ),
)

COMMANDS_BY_INVOCATION = {spec.invocation: spec for spec in COMMAND_CATALOG}


def command_handlers() -> dict[str, Callable[[], None]]:
    """Resolve handlers at call time so tests can monkeypatch underlying commands."""
    return {
        "run": _run_with_prompt,
        "init": init,
        "open recent": open_recent,
        "open stl": open_stl,
        "open step": open_step,
        "open 3mf": open_3mf,
        "open glb": open_glb,
        "open py": open_py,
    }


def _render_command_table() -> None:
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Command", style="cyan")
    table.add_column("Description")
    for spec in COMMAND_CATALOG:
        table.add_row(spec.invocation, spec.description)
    console.print(
        Panel(
            table,
            title="dcad commands",
            subtitle="Browse commands; step/inspect/snapshot run from shell",
        )
    )


def run_command(invocation: str) -> None:
    """Run a catalog command by its invocation string."""
    handlers = command_handlers()
    if invocation not in handlers:
        raise SystemExit(f"Unknown command: {invocation}")
    handlers[invocation]()


def commands() -> None:
    """Browse all dcad commands and run one interactively."""
    _render_command_table()

    choices = [
        questionary.Choice(f"{spec.invocation} — {spec.description}", value=spec.invocation)
        for spec in COMMAND_CATALOG
        if spec.invocation in command_handlers()
    ]
    selected = questionary.select("Select a command to run:", choices=choices).ask()
    if selected is None:
        raise SystemExit(1)

    run_command(selected)
