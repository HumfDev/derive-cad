import sys

import typer

from derive_cad.__about__ import __version__
from derive_cad.cli.init_cmd import init
from derive_cad.cli.run_cmd import run
from derive_cad.utils.errors import DeriveCadError
from derive_cad.utils.logging import error_console

app = typer.Typer(
    name="derivecad",
    help=(
        "Text to CAD from your terminal — generate STEP/STL/3MF/GLB files "
        "from plain-language descriptions."
    ),
    no_args_is_help=True,
)

app.command(name="init")(init)
app.command(name="run")(run)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"derivecad {__version__}")
        raise typer.Exit()


@app.callback()
def main_options(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the derivecad version and exit.",
    ),
) -> None:
    """derivecad — text to CAD from your terminal."""


def main() -> None:
    try:
        app()
    except DeriveCadError as exc:
        error_console.print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
