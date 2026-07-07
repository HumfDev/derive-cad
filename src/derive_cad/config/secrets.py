import os
import stat

import keyring
import keyring.errors

from derive_cad.config.paths import credentials_path, ensure_home_dir
from derive_cad.config.toml_io import read_toml, write_toml
from derive_cad.utils.errors import SecretsError

SERVICE_NAME = "derivecad"


def _keyring_key(provider: str) -> str:
    return f"{provider}:api_key"


def set_api_key(provider: str, key: str) -> str:
    """Store an API key. Returns the backend actually used: "keyring" or "file"."""
    try:
        keyring.set_password(SERVICE_NAME, _keyring_key(provider), key)
        return "keyring"
    except keyring.errors.KeyringError:
        _set_api_key_file(provider, key)
        return "file"


def _set_api_key_file(provider: str, key: str) -> None:
    ensure_home_dir()
    path = credentials_path()
    data = read_toml(path)
    data[provider] = {"api_key": key}
    write_toml(path, data)
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # chmod 600


def _get_api_key_file(provider: str) -> str | None:
    path = credentials_path()
    data = read_toml(path)
    entry = data.get(provider)
    if entry is None:
        return None
    return entry.get("api_key")


def get_api_key(provider: str, env_var: str | None = None) -> str | None:
    """Resolve an API key with precedence: env var > keyring > file fallback."""
    if env_var and os.environ.get(env_var):
        return os.environ[env_var]

    try:
        value = keyring.get_password(SERVICE_NAME, _keyring_key(provider))
        if value is not None:
            return value
    except keyring.errors.KeyringError:
        pass

    return _get_api_key_file(provider)


def delete_api_key(provider: str) -> None:
    try:
        keyring.delete_password(SERVICE_NAME, _keyring_key(provider))
    except keyring.errors.KeyringError:
        pass

    path = credentials_path()
    data = read_toml(path)
    if provider in data:
        del data[provider]
        write_toml(path, data)


__all__ = [
    "SecretsError",
    "delete_api_key",
    "get_api_key",
    "set_api_key",
]
