import sys

import typer

from derive_cad.__about__ import __version__
from derive_cad.cli.commands_cmd import commands
from derive_cad.cli.init_cmd import init
from derive_cad.cli.inspect_cmd import inspect
from derive_cad.cli.open_cmd import open_app
from derive_cad.cli.passthrough import PASSTHROUGH_CONTEXT
from derive_cad.cli.run_cmd import run
from derive_cad.cli.snapshot_cmd import snapshot
from derive_cad.cli.step_cmd import step
from derive_cad.utils.errors import DeriveCadError
from derive_cad.utils.logging import error_console

app = typer.Typer(
    name="dcad",
    help=(
        "Text to CAD from your terminal — generate STEP/STL/3MF/GLB files "
        "from plain-language descriptions."
    ),
    no_args_is_help=True,
)

app.command(name="init")(init)
app.command(name="run")(run)
app.command(name="commands")(commands)
app.command(name="step", context_settings=PASSTHROUGH_CONTEXT)(step)
app.command(name="inspect", context_settings=PASSTHROUGH_CONTEXT)(inspect)
app.command(name="snapshot", context_settings=PASSTHROUGH_CONTEXT)(snapshot)
app.add_typer(open_app, name="open")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"dcad {__version__}")
        raise typer.Exit()


@app.callback()
def main_options(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the dcad version and exit.",
    ),
) -> None:
    """dcad — text to CAD from your terminal."""


def main() -> None:
    try:
        app()
    except DeriveCadError as exc:
        error_console.print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
