from __future__ import annotations

from derive_cad.cli.passthrough import passthrough_command

inspect = passthrough_command(
    tool="inspect",
    usage=(
        "[bold]Usage:[/bold] dcad inspect <subcommand> <target> [options]\n"
        "Example: dcad inspect refs model.step --facts --planes --positioning"
    ),
)
