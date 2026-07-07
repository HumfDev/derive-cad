"""Stage 1: produce a natural-language CAD brief plus a small machine-checkable block
of validation targets, before any build123d source is written.

Ported *process*, not code, from earthtojake/text-to-cad's references/cad-brief.md —
see CONTRIBUTING.md.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from derive_cad.cad.validation import ValidationTargets
from derive_cad.config.models import Config
from derive_cad.llm.client import complete
from derive_cad.llm.prompts import CAD_BRIEF_PROMPT

_JSON_FENCE = re.compile(r"```json\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


@dataclass
class Brief:
    prose: str  # brief text, JSON fence stripped — fed into codegen prompts
    targets: ValidationTargets  # all-None if parsing failed or the block was absent
    raw: str  # full unparsed LLM response — persisted verbatim to brief.md


def _as_triplet(value: object) -> tuple[float, float, float] | None:
    if not isinstance(value, list) or len(value) != 3:
        return None
    try:
        return (float(value[0]), float(value[1]), float(value[2]))
    except (TypeError, ValueError):
        return None


def _as_number(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _as_int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _parse_targets(raw: str) -> ValidationTargets:
    """Lenient parse: any problem (no fence / invalid JSON / wrong key types)
    degrades to an all-None ValidationTargets. Never raises. The prose brief is
    unaffected by a parse failure here — codegen still gets the full brief either
    way."""
    match = _JSON_FENCE.search(raw)
    if not match:
        return ValidationTargets()
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return ValidationTargets()
    if not isinstance(data, dict):
        return ValidationTargets()
    return ValidationTargets(
        bbox_min=_as_triplet(data.get("bbox_min")),
        bbox_max=_as_triplet(data.get("bbox_max")),
        bbox_tolerance_pct=_as_number(data.get("bbox_tolerance_pct")),
        min_face_count=_as_int(data.get("min_face_count")),
        min_solid_count=_as_int(data.get("min_solid_count")),
        max_solid_count=_as_int(data.get("max_solid_count")),
        notes=data.get("notes") if isinstance(data.get("notes"), str) else None,
    )


def parse_brief(raw: str) -> Brief:
    prose = _JSON_FENCE.sub("", raw).strip() or raw.strip()
    return Brief(prose=prose, targets=_parse_targets(raw), raw=raw)


def generate_brief(config: Config, prompt: str) -> Brief:
    """One LLM call. Raises only what complete() raises (ConfigError for an
    unreachable/misconfigured LLM) — callers decide the fallback."""
    raw = complete(
        config,
        [
            {"role": "system", "content": CAD_BRIEF_PROMPT},
            {"role": "user", "content": prompt},
        ],
        log_label="brief",
    )
    return parse_brief(raw)


def write_brief_md(run_dir: Path, brief: Brief) -> Path:
    """Persist the full raw brief (prose + JSON block) alongside model.py/model.step
    for user visibility."""
    path = run_dir / "brief.md"
    path.write_text(brief.raw.strip() + "\n")
    return path
