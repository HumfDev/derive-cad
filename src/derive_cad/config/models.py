import warnings
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

SecretsBackend = Literal["keyring", "file"]


class Config(BaseModel):
    """Non-secret derivecad configuration.

    Resolved with precedence: CLI flags > per-project .derivecad.toml >
    env vars (API keys only) > global ~/.derivecad/config.toml > these defaults.
    """

    provider: str | None = None
    model: str | None = None
    api_key_env_var: str | None = None
    ollama_base_url: str | None = None
    working_dir: str | None = None
    default_export_formats: list[str] = Field(default_factory=lambda: ["stl"])
    sandbox_timeout_s: int = 60
    secrets_backend: SecretsBackend = "keyring"
    enable_snapshot_review: bool = True
    enable_cadpy_inspection: bool = True
    max_repair_attempts: int | None = None
    repair_stalemate_limit: int = 5
    max_generation_attempts: int | None = None
    bbox_tolerance_pct: float = 15.0

    model_config = {"extra": "ignore"}

    @model_validator(mode="before")
    @classmethod
    def _migrate_max_generation_attempts(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        legacy = data.get("max_generation_attempts")
        if legacy is not None and data.get("max_repair_attempts") is None:
            warnings.warn(
                "max_generation_attempts is deprecated; use max_repair_attempts instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            data = dict(data)
            data["max_repair_attempts"] = legacy
        return data
