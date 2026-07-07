from __future__ import annotations

import json
import logging
from pathlib import Path

from rich.console import Console

from derive_cad.config.paths import ensure_home_dir, home_dir

console = Console()
error_console = Console(stderr=True, style="bold red")

LOGGER_NAME = "derive_cad"
logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.DEBUG)
logger.propagate = False

_run_handler: logging.FileHandler | None = None
_session_handler: logging.FileHandler | None = None


def _message_block(title: str, body: str) -> str:
    separator = "=" * 72
    return f"\n{separator}\n{title}\n{separator}\n{body.rstrip()}\n"


def format_messages_for_log(messages: list[dict]) -> str:
    """Serialize LLM messages for logs; omit base64 image payloads."""
    sanitized: list[dict] = []
    for message in messages:
        role = message.get("role", "?")
        content = message.get("content")
        if isinstance(content, str):
            sanitized.append({"role": role, "content": content})
            continue
        if isinstance(content, list):
            parts: list[dict] = []
            for part in content:
                if not isinstance(part, dict):
                    parts.append({"type": "unknown", "value": repr(part)})
                    continue
                if part.get("type") == "image_url":
                    url = part.get("image_url", {}).get("url", "")
                    if url.startswith("data:"):
                        parts.append(
                            {
                                "type": "image_url",
                                "url": f"<data-url omitted, {len(url)} chars>",
                            }
                        )
                    else:
                        parts.append(part)
                    continue
                parts.append(part)
            sanitized.append({"role": role, "content": parts})
            continue
        sanitized.append({"role": role, "content": repr(content)})
    return json.dumps(sanitized, indent=2, ensure_ascii=False)


def configure_run_logging(run_dir: Path) -> Path:
    """Attach per-run and session file handlers. Returns the run log path."""
    global _run_handler, _session_handler

    run_dir.mkdir(parents=True, exist_ok=True)
    run_log_path = run_dir / "generation.log"

    if _run_handler is not None:
        logger.removeHandler(_run_handler)
        _run_handler.close()
        _run_handler = None

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    _run_handler = logging.FileHandler(run_log_path, encoding="utf-8")
    _run_handler.setLevel(logging.DEBUG)
    _run_handler.setFormatter(formatter)
    logger.addHandler(_run_handler)

    if _session_handler is None:
        ensure_home_dir()
        session_log_path = home_dir() / "dcad.log"
        _session_handler = logging.FileHandler(session_log_path, encoding="utf-8")
        _session_handler.setLevel(logging.DEBUG)
        _session_handler.setFormatter(formatter)
        logger.addHandler(_session_handler)

    logger.info("Run logging started: %s", run_log_path)
    logger.info("Session log: %s", home_dir() / "dcad.log")
    return run_log_path


def log_llm_exchange(
    *,
    label: str,
    model: str,
    max_tokens: int | None,
    messages: list[dict],
    response: str,
) -> None:
    cap = str(max_tokens) if max_tokens is not None else "unset (provider default)"
    logger.info(
        _message_block(
            f"LLM REQUEST — {label}",
            f"model: {model}\nmax_tokens: {cap}\n\n"
            f"messages:\n{format_messages_for_log(messages)}",
        )
    )
    logger.info(_message_block(f"LLM RESPONSE — {label}", response))


def log_section(title: str, body: str) -> None:
    logger.info(_message_block(title, body))
