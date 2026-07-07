"""Stage 3: mandatory snapshot review.

Sends the rendered PNG packet to the SAME configured LLM via litellm's multimodal
image_url content blocks. Gated by vision capability — degrades to a graceful skip
(not a hard failure) for text-only models/providers, mirroring the source repo's
documented skip-and-report policy. This is a secondary, fail-open signal on top of
the deterministic validation-target checks, not a primary gate.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

import litellm

from derive_cad.config.models import Config
from derive_cad.llm.brief import Brief
from derive_cad.llm.client import complete
from derive_cad.llm.prompts import SNAPSHOT_REVIEW_PROMPT


@dataclass
class ReviewResult:
    performed: bool  # False => skipped (disabled / no vision support / render failed)
    passed: bool  # meaningless when performed is False; treated as a pass
    notes: str  # the LLM's findings, or the skip/failure reason


def model_supports_vision(config: Config) -> bool:
    """Delegates to litellm's own model-capability table rather than a
    hand-maintained allowlist — more accurate, and covers every litellm-supported
    model dcad's "Other" provider option can reach."""
    if not config.model:
        return False
    try:
        return bool(litellm.supports_vision(model=config.model))
    except Exception:
        return False


def review_snapshots(config: Config, snapshot_paths: list[Path], brief: Brief) -> ReviewResult:
    if not model_supports_vision(config):
        return ReviewResult(
            performed=False,
            passed=True,
            notes=f"Skipped: {config.model} has no known vision support.",
        )

    content: list[dict] = [
        {"type": "text", "text": f"{SNAPSHOT_REVIEW_PROMPT}\n\nBrief:\n{brief.prose}"}
    ]
    for path in snapshot_paths:
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
        )

    raw = complete(
        config,
        [{"role": "user", "content": content}],
        log_label="snapshot-review",
    )
    first_line, _, rest = raw.strip().partition("\n")
    verdict = first_line.strip().upper()
    if verdict not in ("PASS", "FAIL"):
        # Ambiguous response: fail open (treat as pass) — keeps vision review a soft
        # bonus signal, not a flaky hard gate.
        return ReviewResult(performed=True, passed=True, notes=f"(unparsed verdict) {raw}")
    return ReviewResult(performed=True, passed=verdict == "PASS", notes=rest.strip() or raw)
