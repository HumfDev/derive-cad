import subprocess
from dataclasses import dataclass
from pathlib import Path

from derive_cad.cad.sandbox import run_isolated
from derive_cad.project.workspace import python_executable
from derive_cad.utils.errors import GenerationError


@dataclass
class RunResult:
    run_dir: Path
    script_path: Path
    step_path: Path
    stdout: str
    stderr: str


def run_script(script_source: str, run_dir: Path, timeout_s: int) -> RunResult:
    """Write `script_source` to model.py in run_dir and execute it in a fresh,
    isolated subprocess to produce model.step. Never exec()'d in-process — a
    crash/hang/segfault in the OCP/OCCT kernel can't take down the CLI.
    """
    script_path = run_dir / "model.py"
    step_path = run_dir / "model.step"
    script_path.write_text(script_source)

    stdout_log = run_dir / "stdout.log"
    stderr_log = run_dir / "stderr.log"

    try:
        completed = run_isolated(
            [python_executable(), str(script_path), str(step_path)],
            cwd=run_dir,
            timeout_s=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        stdout_log.write_text(exc.stdout or "")
        stderr_log.write_text(exc.stderr or "")
        raise GenerationError(
            f"Generation timed out after {timeout_s}s. See {stderr_log}."
        ) from exc

    stdout_log.write_text(completed.stdout)
    stderr_log.write_text(completed.stderr)

    if completed.returncode != 0:
        raise GenerationError(
            f"Generation script failed (exit code {completed.returncode}). "
            f"See {stderr_log}:\n{completed.stderr[-2000:]}"
        )

    if not step_path.exists():
        raise GenerationError(
            f"Generation script exited successfully but did not produce {step_path}."
        )

    return RunResult(
        run_dir=run_dir,
        script_path=script_path,
        step_path=step_path,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
