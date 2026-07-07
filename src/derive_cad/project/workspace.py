import re
import sys
from datetime import UTC, datetime
from pathlib import Path


def _slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return (slug or "run")[:max_len]


def new_run_dir(working_dir: Path, description: str = "run") -> Path:
    """Create a fresh, timestamped scratch directory for one generation attempt,
    nested inside the user's working folder so scripts/artifacts/logs stay
    co-located and inspectable (see plan: never run in the CLI's own install dir).
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = working_dir / ".runs" / f"{timestamp}-{_slugify(description)}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def python_executable() -> str:
    return sys.executable
