import re

from derive_cad.config.models import Config
from derive_cad.llm.client import complete, configure_litellm

_NAMING_PROMPT = """\
You name folders for CAD design projects.
Return ONLY a short folder name: 2-4 lowercase English words separated by hyphens.
Use filesystem-safe characters (a-z, 0-9, hyphens only). No quotes or explanation."""


def sanitize_folder_name(name: str, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return (slug or "design")[:max_len]


def _fallback_name(description: str) -> str:
    return sanitize_folder_name(description)


def suggest_design_name(config: Config, description: str) -> str:
    """Use the configured LLM to suggest a readable folder name for a design."""
    description = description.strip()
    fallback = _fallback_name(description)

    if not config.provider or not config.model:
        return fallback

    configure_litellm(config)
    try:
        response = complete(
            config,
            [
                {"role": "system", "content": _NAMING_PROMPT},
                {
                    "role": "user",
                    "content": f"Design description: {description}",
                },
            ],
            log_label="naming",
        )
        name = sanitize_folder_name(response.splitlines()[0])
        return name or fallback
    except Exception:
        return fallback
