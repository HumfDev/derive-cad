from derive_cad.cli.commands_cmd import (
    COMMAND_CATALOG,
    COMMANDS_BY_INVOCATION,
    run_command,
)


def test_command_catalog_lists_all_commands():
    invocations = {spec.invocation for spec in COMMAND_CATALOG}
    assert invocations == {
        "run",
        "init",
        "open recent",
        "open stl",
        "open step",
        "open 3mf",
        "open glb",
        "open py",
    }


def test_commands_by_invocation_matches_catalog():
    assert len(COMMANDS_BY_INVOCATION) == len(COMMAND_CATALOG)
    for spec in COMMAND_CATALOG:
        assert COMMANDS_BY_INVOCATION[spec.invocation] is spec


def test_run_command_dispatches_to_handler(monkeypatch):
    called = []

    def fake_open_stl() -> None:
        called.append("open stl")

    monkeypatch.setattr("derive_cad.cli.commands_cmd.open_stl", fake_open_stl)
    run_command("open stl")
    assert called == ["open stl"]
