from __future__ import annotations

from derive_cad.cli.passthrough import passthrough_command

step = passthrough_command(
    tool="step",
    usage=(
        "[bold]Usage:[/bold] dcad step <targets...> [options]\n"
        "Example: dcad step model.py -o model.step --stl model.stl"
    ),
    timeout_s=300,
)
