import os
from pathlib import Path

import litellm
import questionary
from rich.panel import Panel

from derive_cad.config.models import Config
from derive_cad.config.secrets import set_api_key
from derive_cad.config.store import load_global_config, resolve_config, save_global_config
from derive_cad.llm.providers import OTHER_PROVIDER_ID, PROVIDERS, provider_choices
from derive_cad.utils.logging import console

DEFAULT_WORKING_DIR = str(Path.home() / "derivecad-projects")
MAX_KEY_VALIDATION_ATTEMPTS = 3


def needs_setup(config: Config) -> bool:
    return not config.working_dir or not config.provider


def _select_model(provider_id: str, existing: Config) -> str:
    info = PROVIDERS[provider_id]
    choices = [questionary.Choice(model, value=model) for model in info.models]
    default = existing.model if existing.model in info.models else info.default_model
    model = questionary.select("Model to use:", choices=choices, default=default).ask()
    if model is None:
        raise SystemExit(1)
    return model


def _select_provider(existing: Config) -> tuple[str, str, str | None, str | None]:
    """Returns (provider_id, model, env_var, ollama_base_url)."""
    choices = []
    for pid in provider_choices():
        if pid == OTHER_PROVIDER_ID:
            choices.append(questionary.Choice("Other (custom litellm model string)", value=pid))
        else:
            choices.append(questionary.Choice(PROVIDERS[pid].label, value=pid))

    default = existing.provider if existing.provider in provider_choices() else None
    provider_id = questionary.select(
        "Which LLM provider would you like to connect?",
        choices=choices,
        default=default,
    ).ask()
    if provider_id is None:
        raise SystemExit(1)

    if provider_id == OTHER_PROVIDER_ID:
        model = questionary.text(
            "Enter the litellm model string (e.g. mistral/mistral-large-latest):"
        ).ask()
        env_var = questionary.text(
            "Enter the environment variable name this provider's API key should be read from:"
        ).ask()
        if model is None or env_var is None:
            raise SystemExit(1)
        return provider_id, model, env_var, None

    info = PROVIDERS[provider_id]
    if provider_id == "ollama":
        base_url = questionary.text(
            "Ollama base URL:", default="http://localhost:11434"
        ).ask()
        if base_url is None:
            raise SystemExit(1)
        model = _select_model(provider_id, existing)
        return provider_id, model, None, base_url

    model = _select_model(provider_id, existing)
    return provider_id, model, info.env_var, None


def _validate_key(model: str, env_var: str, api_key: str) -> bool:
    os.environ[env_var] = api_key
    try:
        with console.status("Validating API key..."):
            litellm.completion(
                model=model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
        return True
    except Exception as exc:  # noqa: BLE001 - surface any provider error to the user
        console.print(f"[red]Validation failed:[/red] {exc}")
        return False


def _collect_and_store_key(provider_id: str, model: str, env_var: str) -> str:
    for attempt in range(1, MAX_KEY_VALIDATION_ATTEMPTS + 1):
        api_key = questionary.password(f"API key for {env_var}:").ask()
        if api_key is None:
            raise SystemExit(1)

        if _validate_key(model, env_var, api_key):
            break
        if attempt == MAX_KEY_VALIDATION_ATTEMPTS:
            if not questionary.confirm(
                "Validation failed after multiple attempts. Save this key anyway?",
                default=False,
            ).ask():
                raise SystemExit(1)
            break

    backend = set_api_key(provider_id, api_key)
    if backend == "file":
        console.print(
            "[yellow]No OS keychain backend detected (common in CI/containers/headless "
            "Linux). Falling back to a config-file-based store at "
            "~/.derivecad/credentials.toml. This is LESS SECURE — the key will be "
            "readable by anything with file access.[/yellow]"
        )
    return backend


def _select_working_dir(existing: Config) -> str:
    default = existing.working_dir or DEFAULT_WORKING_DIR
    while True:
        raw = questionary.text("Working folder for generated CAD files:", default=default).ask()
        if raw is None:
            raise SystemExit(1)
        path = Path(raw).expanduser()
        if path.exists() and not path.is_dir():
            console.print(f"[red]{path} exists and is not a directory.[/red]")
            continue
        if not path.exists():
            if questionary.confirm(f"{path} does not exist. Create it?", default=True).ask():
                path.mkdir(parents=True, exist_ok=True)
            else:
                continue
        return str(path)


def run_setup_wizard(*, existing: Config | None = None, standalone: bool = True) -> Config:
    """Interactive first-time setup. Saves config and returns the merged result."""
    if existing is None:
        existing = load_global_config()

    console.print(
        Panel(
            "Connect an LLM provider and pick a working folder for generated CAD files. "
            "Re-run [bold]dcad init[/bold] any time to change these settings.",
            title="dcad setup",
        )
    )

    provider_id, model, env_var, ollama_base_url = _select_provider(existing)

    secrets_backend = existing.secrets_backend
    if env_var is not None:
        secrets_backend = _collect_and_store_key(provider_id, model, env_var)

    working_dir = _select_working_dir(existing)

    config = Config(
        provider=provider_id,
        model=model,
        api_key_env_var=env_var if provider_id == OTHER_PROVIDER_ID else None,
        ollama_base_url=ollama_base_url,
        working_dir=working_dir,
        secrets_backend=secrets_backend,
    )
    save_global_config(config)

    next_steps = (
        "Next: run [bold]dcad run \"your design\"[/bold] to generate your first model."
        if standalone
        else "Continuing to generation..."
    )
    console.print(
        Panel(
            f"Provider: {provider_id}\n"
            f"Model: {model}\n"
            f"Working folder: {working_dir}\n"
            f"Secrets backend: {secrets_backend}\n\n"
            f"{next_steps}",
            title="Setup complete",
            style="green",
        )
    )
    return config


def ensure_configured(*, standalone_setup: bool = False) -> Config:
    """Return resolved config, running the setup wizard inline when needed."""
    config = resolve_config(project_dir=Path.cwd())
    if needs_setup(config):
        return run_setup_wizard(existing=config, standalone=standalone_setup)
    return config
