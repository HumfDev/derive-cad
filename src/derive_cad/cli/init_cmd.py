from derive_cad.cli.setup import run_setup_wizard
from derive_cad.config.store import load_global_config


def init() -> None:
    """Reconfigure your LLM provider and working folder."""
    run_setup_wizard(existing=load_global_config(), standalone=True)
