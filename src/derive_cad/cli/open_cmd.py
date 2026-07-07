from pathlib import Path

import typer

from derive_cad.cli.setup import ensure_configured
from derive_cad.llm.providers import OPENABLE_ARTIFACTS
from derive_cad.project.workspace import latest_run_dir, open_path
from derive_cad.utils.errors import ConfigError
from derive_cad.utils.logging import console

open_app = typer.Typer(
    help="Open the most recent generated CAD files.",
    no_args_is_help=True,
)


def _require_latest_run() -> Path:
    config = ensure_configured(standalone_setup=True)
    working_dir = Path(config.working_dir).expanduser()
    run_dir = latest_run_dir(working_dir)
    if run_dir is None:
        raise ConfigError(
            f"No designs found in {working_dir}. Run [bold]dcad run[/bold] first."
        )
    return run_dir


def _open_artifact(artifact_key: str) -> None:
    run_dir = _require_latest_run()
    filename = OPENABLE_ARTIFACTS[artifact_key]
    path = run_dir / filename
    if not path.exists():
        raise ConfigError(
            f"{path.name} was not found in the latest run ({run_dir.name}). "
            f"Re-run [bold]dcad run[/bold] or check export settings."
        )
    open_path(path)
    console.print(f"Opened {path}")


@open_app.command("recent")
def open_recent() -> None:
    """Open the folder containing the most recent design."""
    run_dir = _require_latest_run()
    open_path(run_dir)
    console.print(f"Opened {run_dir}")


@open_app.command("step")
def open_step() -> None:
    """Open the STEP file from the most recent design."""
    _open_artifact("step")


@open_app.command("stl")
def open_stl() -> None:
    """Open the STL file from the most recent design."""
    _open_artifact("stl")


@open_app.command("3mf")
def open_3mf() -> None:
    """Open the 3MF file from the most recent design."""
    _open_artifact("3mf")


@open_app.command("glb")
def open_glb() -> None:
    """Open the GLB file from the most recent design."""
    _open_artifact("glb")


@open_app.command("py")
def open_py() -> None:
    """Open the generated build123d script from the most recent design."""
    _open_artifact("py")
