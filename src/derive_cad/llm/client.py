import os
import re

import litellm

from derive_cad.config.models import Config
from derive_cad.config.secrets import get_api_key
from derive_cad.llm.providers import OTHER_PROVIDER_ID, PROVIDERS
from derive_cad.utils.errors import ConfigError
from derive_cad.utils.logging import log_llm_exchange, logger

_FENCE_PATTERN = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_python_code(text: str) -> str:
    """Pull Python source out of an LLM response."""
    match = _FENCE_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def validate_script_structure(script: str) -> None:
    """Contract check: the script must import build123d and define gen_step().
    Execution and export are owned by the runner (see cad/runner.py's
    ENTRYPOINT_FOOTER), so the script itself doesn't need __main__/export_step/argv
    boilerplate — narrowing this contract to two checks removes a source of
    otherwise-brittle format-compliance failures.
    """
    if "build123d" not in script:
        raise ValueError("Script must import build123d.")
    if "def gen_step" not in script:
        raise ValueError("Script must define gen_step().")


def configure_litellm(config: Config) -> None:
    if config.provider == "ollama" and config.ollama_base_url:
        os.environ.setdefault("OLLAMA_API_BASE", config.ollama_base_url)
        return

    if config.provider in (None, "ollama"):
        return

    env_var: str | None = None
    if config.provider == OTHER_PROVIDER_ID:
        env_var = config.api_key_env_var
    else:
        info = PROVIDERS.get(config.provider or "")
        env_var = info.env_var if info else None

    if env_var is None:
        return

    api_key = get_api_key(config.provider or OTHER_PROVIDER_ID, env_var)
    if api_key:
        os.environ[env_var] = api_key


def require_llm_ready(config: Config) -> None:
    if not config.provider or not config.model:
        raise ConfigError("LLM not configured. Run [bold]dcad init[/bold] first.")

    if config.provider == "ollama":
        return

    env_var: str | None = None
    if config.provider == OTHER_PROVIDER_ID:
        env_var = config.api_key_env_var
        if not env_var:
            raise ConfigError(
                "Custom provider is missing its API key env var. "
                "Re-run [bold]dcad init[/bold]."
            )
    else:
        info = PROVIDERS.get(config.provider)
        env_var = info.env_var if info else None

    if env_var and not get_api_key(config.provider, env_var) and not os.environ.get(env_var):
        raise ConfigError(
            f"No API key found for [bold]{env_var}[/bold]. "
            "Re-run [bold]dcad init[/bold] to connect your provider."
        )


def complete(
    config: Config,
    messages: list[dict],
    *,
    max_tokens: int | None = None,
    log_label: str = "complete",
) -> str:
    """Call the configured LLM and return the assistant message text.

    When max_tokens is None (the default), no output cap is sent to the provider —
    the model may use its full context-window allowance for the completion.
    """
    require_llm_ready(config)
    configure_litellm(config)

    logger.info(
        "LLM call start label=%s model=%s max_tokens=%s",
        log_label,
        config.model,
        max_tokens if max_tokens is not None else "unset",
    )
    completion_kwargs: dict = {
        "model": config.model,
        "messages": messages,
    }
    if max_tokens is not None:
        completion_kwargs["max_tokens"] = max_tokens
    try:
        response = litellm.completion(**completion_kwargs)
    except Exception as exc:
        logger.exception("LLM call failed label=%s model=%s: %s", log_label, config.model, exc)
        raise

    content = response.choices[0].message.content or ""
    log_llm_exchange(
        label=log_label,
        model=config.model or "",
        max_tokens=max_tokens,
        messages=messages,
        response=content if content.strip() else "(empty response)",
    )
    if not content.strip():
        logger.error("LLM returned an empty response label=%s model=%s", log_label, config.model)
        raise ConfigError("LLM returned an empty response.")
    return content
