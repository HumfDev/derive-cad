"""Purchasable parts search via vendored skills/step-parts (upstream)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from derive_cad.project.workspace import python_executable
from derive_cad.skill.paths import step_parts_dir, step_parts_script
from derive_cad.utils.logging import logger

_PURCHASABLE_HINTS = re.compile(
    r"\b("
    r"screw|bolt|nut|washer|bearing|standoff|motor|servo|connector|"
    r"fastener|socket head|hex|ISO\s*\d+|M\d+\b|step\.parts|catalog part"
    r")\b",
    re.IGNORECASE,
)


def _mentions_purchasable_parts(prompt: str) -> bool:
    return _PURCHASABLE_HINTS.search(prompt) is not None


def search_step_parts(query: str, *, limit: int = 5, timeout_s: float = 20.0) -> list[dict]:
    script = step_parts_script()
    cmd = [
        python_executable(),
        str(script),
        query,
        "--limit",
        str(limit),
    ]
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    if completed.returncode != 0:
        tail = completed.stderr[-1000:] or completed.stdout[-1000:]
        raise RuntimeError(f"step-parts search failed: {tail}")
    payload = json.loads(completed.stdout)
    items = payload.get("items", payload if isinstance(payload, list) else [])
    return [item for item in items if isinstance(item, dict)]


def check_purchasable_parts(prompt: str, *, run_dir: Path | None = None) -> list[str]:
    """Search step.parts when the prompt mentions catalog hardware; non-blocking on failure."""
    if not step_parts_dir().is_dir():
        logger.info(
            "Stage 4/10 — Purchasable parts: skills/step-parts not installed; "
            "using envelope geometry when needed."
        )
        return []

    if not _mentions_purchasable_parts(prompt):
        logger.info(
            "Stage 4/10 — Purchasable parts: no catalog keywords; skipping search."
        )
        return []

    logger.info("Stage 4/10 — Purchasable parts: searching step.parts catalog")
    try:
        items = search_step_parts(prompt, limit=5)
    except Exception as exc:  # noqa: BLE001
        logger.warning("step-parts search failed (continuing without catalog hits): %s", exc)
        return []

    notes: list[str] = []
    for item in items[:5]:
        name = item.get("name") or item.get("id") or "unknown part"
        part_id = item.get("id", "")
        standard = item.get("standard")
        std_text = ""
        if isinstance(standard, dict):
            std_text = standard.get("designation") or standard.get("number") or ""
        line = f"{name} ({part_id})"
        if std_text:
            line += f" — {std_text}"
        notes.append(line)

    if run_dir is not None and notes:
        catalog_path = run_dir / "step-parts.json"
        catalog_path.write_text(json.dumps({"query": prompt, "items": items[:5]}, indent=2))

    if notes:
        logger.info("Stage 4/10 — Purchasable parts: %s catalog hit(s)", len(notes))
    else:
        logger.info("Stage 4/10 — Purchasable parts: no catalog matches")
    return notes
