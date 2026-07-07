from __future__ import annotations

from derive_cad.cli.passthrough import passthrough_command

snapshot = passthrough_command(
    tool="snapshot",
    usage=(
        "[bold]Usage:[/bold] dcad snapshot <target.step> [options]\n"
        "[dim]Requires CAD Viewer GLB sidecars (`.model.step.glb`) from STEP generation.[/dim]"
    ),
    timeout_s=300,
)
