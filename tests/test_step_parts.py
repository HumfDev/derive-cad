from derive_cad.llm.step_parts import _mentions_purchasable_parts, check_purchasable_parts


def test_mentions_purchasable_parts_detects_hardware():
    assert _mentions_purchasable_parts("Add M3 socket head screws")
    assert not _mentions_purchasable_parts("Design a phone stand")


def test_check_purchasable_parts_skips_simple_prompt(monkeypatch):
    monkeypatch.setattr(
        "derive_cad.llm.step_parts.search_step_parts",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not search")),
    )
    notes = check_purchasable_parts("Design a rectangular enclosure")
    assert notes == []


def test_check_purchasable_parts_formats_catalog_hits(monkeypatch):
    monkeypatch.setattr(
        "derive_cad.llm.step_parts.search_step_parts",
        lambda *_args, **_kwargs: [
            {
                "id": "m3_socket_12",
                "name": "M3 socket head cap screw 12mm",
                "standard": {"designation": "ISO 4762"},
            },
        ],
    )
    notes = check_purchasable_parts("Use M3 socket head screws")
    assert len(notes) == 1
    assert "M3 socket head cap screw 12mm" in notes[0]
    assert "ISO 4762" in notes[0]
