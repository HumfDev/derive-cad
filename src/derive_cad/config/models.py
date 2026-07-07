from typing import Literal

from pydantic import BaseModel, Field

SecretsBackend = Literal["keyring", "file"]


class Config(BaseModel):
    """Non-secret derivecad configuration.

    Resolved with precedence: CLI flags > per-project .derivecad.toml >
    env vars (API keys only) > global ~/.derivecad/config.toml > these defaults.
    """

    provider: str | None = None
    model: str | None = None
    ollama_base_url: str | None = None
    working_dir: str | None = None
    default_export_formats: list[str] = Field(default_factory=lambda: ["stl"])
    sandbox_timeout_s: int = 60
    secrets_backend: SecretsBackend = "keyring"

    model_config = {"extra": "ignore"}
