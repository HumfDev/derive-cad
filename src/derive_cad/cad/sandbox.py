import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

if sys.platform != "win32":
    import resource

# Generous defaults — degenerate LLM-authored geometry (huge fillet radii,
# runaway boolean operations) can legitimately need more memory/CPU than simple
# test fixtures; these are meant to catch true runaways, not to be a tight budget.
DEFAULT_MEMORY_LIMIT_BYTES = 4 * 1024 * 1024 * 1024  # 4 GiB
DEFAULT_CPU_LIMIT_S = 120


def _posix_resource_limiter(
    memory_limit_bytes: int, cpu_limit_s: int
) -> Callable[[], None] | None:
    if sys.platform == "win32":
        # No RLIMIT equivalent without job objects; documented gap (see CONTRIBUTING.md).
        return None

    def _limit() -> None:
        # Best-effort: on macOS, RLIMIT_AS frequently can't be lowered below the
        # process's already-mapped virtual address space (dyld's shared cache
        # alone can reserve several GB), so setrlimit can fail even though the
        # process itself uses far less real memory. Never let a resource-limit
        # failure block launching the subprocess — the timeout is the primary
        # backstop against runaway generation scripts.
        try:
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))
        except (ValueError, OSError):
            pass
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit_s, cpu_limit_s))
        except (ValueError, OSError):
            pass

    return _limit


def run_isolated(
    args: list[str],
    cwd: Path,
    timeout_s: int,
    memory_limit_bytes: int = DEFAULT_MEMORY_LIMIT_BYTES,
    cpu_limit_s: int = DEFAULT_CPU_LIMIT_S,
) -> subprocess.CompletedProcess:
    """Run a subprocess in isolation: fresh interpreter, dedicated cwd, timeout,
    and (on POSIX) memory/CPU resource limits. Raises subprocess.TimeoutExpired
    on timeout — callers translate that into a GenerationError.
    """
    preexec_fn = _posix_resource_limiter(memory_limit_bytes, cpu_limit_s)
    return subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_s,
        preexec_fn=preexec_fn,
    )
