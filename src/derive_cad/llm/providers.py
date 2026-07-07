from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderInfo:
    id: str
    label: str
    env_var: str | None  # None for providers that need no API key (e.g. local Ollama)
    default_model: str
    supports_tool_calling: bool = True


PROVIDERS: dict[str, ProviderInfo] = {
    "openai": ProviderInfo(
        id="openai",
        label="OpenAI",
        env_var="OPENAI_API_KEY",
        default_model="gpt-4o-mini",
    ),
    "anthropic": ProviderInfo(
        id="anthropic",
        label="Anthropic",
        env_var="ANTHROPIC_API_KEY",
        default_model="claude-haiku-4-5",
    ),
    "gemini": ProviderInfo(
        id="gemini",
        label="Google Gemini",
        env_var="GEMINI_API_KEY",
        default_model="gemini/gemini-2.0-flash",
    ),
    "groq": ProviderInfo(
        id="groq",
        label="Groq",
        env_var="GROQ_API_KEY",
        default_model="groq/llama-3.3-70b-versatile",
    ),
    "ollama": ProviderInfo(
        id="ollama",
        label="Ollama (local)",
        env_var=None,
        default_model="ollama/llama3.3",
        supports_tool_calling=False,
    ),
}

OTHER_PROVIDER_ID = "other"


def get_provider(provider_id: str) -> ProviderInfo | None:
    return PROVIDERS.get(provider_id)


def provider_choices() -> list[str]:
    return [*PROVIDERS.keys(), OTHER_PROVIDER_ID]
