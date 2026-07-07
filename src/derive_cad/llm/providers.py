from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderInfo:
    id: str
    label: str
    env_var: str | None  # None for providers that need no API key (e.g. local Ollama)
    default_model: str
    models: tuple[str, ...]
    supports_tool_calling: bool = True


PROVIDERS: dict[str, ProviderInfo] = {
    "openai": ProviderInfo(
        id="openai",
        label="OpenAI",
        env_var="OPENAI_API_KEY",
        default_model="gpt-5.4-mini",
        models=(
            "gpt-5.4-nano",
            "gpt-5.4-mini",
            "gpt-5.4",
            "gpt-5.4-pro",
        ),
    ),
    "anthropic": ProviderInfo(
        id="anthropic",
        label="Anthropic",
        env_var="ANTHROPIC_API_KEY",
        default_model="claude-haiku-4-5",
        models=(
            "claude-haiku-4-5",
            "claude-sonnet-5",
            "claude-opus-4-8",
            "claude-fable-5",
        ),
    ),
    "gemini": ProviderInfo(
        id="gemini",
        label="Google Gemini",
        env_var="GEMINI_API_KEY",
        default_model="gemini/gemini-3.5-flash",
        models=(
            "gemini/gemini-3.1-flash-lite",
            "gemini/gemini-2.5-flash",
            "gemini/gemini-3.5-flash",
            "gemini/gemini-3.1-pro-preview",
        ),
    ),
    "groq": ProviderInfo(
        id="groq",
        label="Groq",
        env_var="GROQ_API_KEY",
        default_model="groq/llama-3.3-70b-versatile",
        models=(
            "groq/llama-3.1-8b-instant",
            "groq/meta-llama/llama-4-scout-17b-16e-instruct",
            "groq/llama-3.3-70b-versatile",
            "groq/openai/gpt-oss-120b",
        ),
    ),
    "ollama": ProviderInfo(
        id="ollama",
        label="Ollama (local)",
        env_var=None,
        default_model="ollama/llama3.3",
        models=(
            "ollama/llama3.2",
            "ollama/llama3.3",
            "ollama/llama4",
        ),
        supports_tool_calling=False,
    ),
}

OTHER_PROVIDER_ID = "other"

OPENABLE_ARTIFACTS: dict[str, str] = {
    "step": "model.step",
    "stl": "model.stl",
    "3mf": "model.3mf",
    "glb": "model.glb",
    "py": "model.py",
}


def get_provider(provider_id: str) -> ProviderInfo | None:
    return PROVIDERS.get(provider_id)


def provider_choices() -> list[str]:
    return [*PROVIDERS.keys(), OTHER_PROVIDER_ID]
