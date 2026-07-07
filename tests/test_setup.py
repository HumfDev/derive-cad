from derive_cad.cli.setup import needs_setup
from derive_cad.config.models import Config


def test_needs_setup_when_unconfigured():
    assert needs_setup(Config()) is True


def test_needs_setup_when_fully_configured():
    assert (
        needs_setup(
            Config(
                provider="openai",
                model="gpt-4o-mini",
                working_dir="/tmp/proj",
            )
        )
        is False
    )


def test_needs_setup_when_missing_provider():
    assert needs_setup(Config(working_dir="/tmp/proj")) is True


def test_needs_setup_when_missing_working_dir():
    assert needs_setup(Config(provider="openai", model="gpt-4o-mini")) is True
