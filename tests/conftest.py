import pytest


@pytest.fixture
def derivecad_home(tmp_path, monkeypatch):
    home = tmp_path / ".derivecad"
    monkeypatch.setenv("DERIVECAD_HOME", str(home))
    return home
