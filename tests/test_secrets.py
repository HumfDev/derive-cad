import stat

import keyring.errors

from derive_cad.config import secrets


class _InMemoryKeyring:
    """A minimal fake standing in for a working OS keychain backend."""

    def __init__(self):
        self._store: dict[tuple[str, str], str] = {}

    def set_password(self, service, key, value):
        self._store[(service, key)] = value

    def get_password(self, service, key):
        return self._store.get((service, key))

    def delete_password(self, service, key):
        self._store.pop((service, key), None)


class _BrokenKeyring:
    """Simulates an environment with no usable OS keychain backend."""

    def set_password(self, service, key, value):
        raise keyring.errors.PasswordSetError("no backend available")

    def get_password(self, service, key):
        raise keyring.errors.KeyringError("no backend available")

    def delete_password(self, service, key):
        raise keyring.errors.PasswordDeleteError("no backend available")


def test_keyring_happy_path(derivecad_home, monkeypatch):
    fake = _InMemoryKeyring()
    monkeypatch.setattr(secrets.keyring, "set_password", fake.set_password)
    monkeypatch.setattr(secrets.keyring, "get_password", fake.get_password)

    backend = secrets.set_api_key("openai", "sk-test-123")
    assert backend == "keyring"
    assert secrets.get_api_key("openai") == "sk-test-123"


def test_falls_back_to_file_when_keyring_unavailable(derivecad_home, monkeypatch):
    broken = _BrokenKeyring()
    monkeypatch.setattr(secrets.keyring, "set_password", broken.set_password)
    monkeypatch.setattr(secrets.keyring, "get_password", broken.get_password)

    backend = secrets.set_api_key("anthropic", "sk-ant-456")
    assert backend == "file"

    cred_path = derivecad_home / "credentials.toml"
    assert cred_path.exists()
    mode = stat.S_IMODE(cred_path.stat().st_mode)
    assert mode == stat.S_IRUSR | stat.S_IWUSR

    assert secrets.get_api_key("anthropic") == "sk-ant-456"


def test_env_var_always_wins(derivecad_home, monkeypatch):
    fake = _InMemoryKeyring()
    fake.set_password(secrets.SERVICE_NAME, "openai:api_key", "stored-key")
    monkeypatch.setattr(secrets.keyring, "get_password", fake.get_password)

    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    assert secrets.get_api_key("openai", env_var="OPENAI_API_KEY") == "env-key"
