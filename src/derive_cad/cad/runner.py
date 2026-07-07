from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from derive_cad.skill.runner import run_skill_script_or_raise
from derive_cad.utils.errors import ExportError, GenerationError
from derive_cad.utils.logging import logger

ExportFormat = Literal["stl", "3mf", "glb"]

_SIDECAR_FLAGS: dict[ExportFormat, str] = {
    "stl": "--stl",
    "3mf": "--3mf",
    "glb": "--glb",
}


@dataclass
class RunResult:
    run_dir: Path
    script_path: Path
    step_path: Path
    stdout: str
    stderr: str
    sidecar_paths: dict[str, Path] = field(default_factory=dict)


def _write_script(script_source: str, run_dir: Path) -> Path:
    script_path = run_dir / "model.py"
    script_path.write_text(script_source)
    logger.info("Wrote script to %s (%s bytes)", script_path, len(script_source))
    return script_path


def _sidecar_args(formats: list[str], run_dir: Path) -> tuple[list[str], dict[str, Path]]:
    args: list[str] = []
    paths: dict[str, Path] = {}
    for fmt in formats:
        try:
            flag = _SIDECAR_FLAGS[fmt]  # type: ignore[literal-required]
        except KeyError as exc:
            raise ExportError(f"Unsupported export format: {fmt!r}") from exc
        out_path = run_dir / f"model.{fmt}"
        args.extend([flag, out_path.name])
        paths[fmt] = out_path
    return args, paths


def _run_step_generation(
    script_path: Path,
    step_path: Path,
    *,
    timeout_s: int,
    sidecar_formats: list[str] | None = None,
) -> tuple[str, str, dict[str, Path]]:
    """Generate STEP (and optional sidecars) via vendored skills/cad/scripts/step."""
    args = [script_path.name, "-o", step_path.name]
    sidecar_paths: dict[str, Path] = {}
    if sidecar_formats:
        sidecar_args, sidecar_paths = _sidecar_args(sidecar_formats, script_path.parent)
        args.extend(sidecar_args)
    result = run_skill_script_or_raise("step", args, cwd=script_path.parent, timeout_s=timeout_s)
    return result.stdout, result.stderr, sidecar_paths


def run_script(
    script_source: str,
    run_dir: Path,
    timeout_s: int,
    *,
    sidecar_formats: list[str] | None = None,
) -> RunResult:
    """Write build123d source to model.py and generate model.step via cadpy."""
    run_dir.mkdir(parents=True, exist_ok=True)
    script_path = _write_script(script_source, run_dir)
    step_path = run_dir / "model.step"
    stdout_log = run_dir / "stdout.log"
    stderr_log = run_dir / "stderr.log"

    logger.info(
        "STEP generation via skills/cad/scripts/step timeout_s=%s cwd=%s sidecars=%s",
        timeout_s,
        run_dir,
        sidecar_formats or [],
    )
    try:
        stdout, stderr, sidecar_paths = _run_step_generation(
            script_path,
            step_path,
            timeout_s=timeout_s,
            sidecar_formats=sidecar_formats,
        )
    except Exception as exc:
        stderr_log.write_text(str(exc))
        logger.error("STEP generation failed: %s", exc)
        raise GenerationError(f"STEP generation failed: {exc}") from exc

    stdout_log.write_text(stdout)
    stderr_log.write_text(stderr)

    if not step_path.exists():
        logger.error("STEP generation succeeded but file missing at %s", step_path)
        raise GenerationError(
            f"STEP generation did not produce {step_path}. See {stderr_log}."
        )

    for fmt, path in sidecar_paths.items():
        if not path.exists():
            raise GenerationError(f"STEP generation did not produce sidecar {path} ({fmt}).")

    logger.info("Produced STEP at %s", step_path)
    return RunResult(
        run_dir=run_dir,
        script_path=script_path,
        step_path=step_path,
        stdout=stdout,
        stderr=stderr,
        sidecar_paths=sidecar_paths,
    )


def export_sidecars(
    script_path: Path,
    formats: list[str],
    *,
    timeout_s: int,
) -> dict[str, Path]:
    """Export STL/3MF/GLB sidecars from an existing model.py via cadpy step."""
    if not formats:
        return {}
    run_dir = script_path.parent
    step_path = run_dir / "model.step"
    sidecar_args, sidecar_paths = _sidecar_args(formats, run_dir)
    args = [script_path.name, "-o", step_path.name, *sidecar_args]
    run_skill_script_or_raise("step", args, cwd=run_dir, timeout_s=timeout_s)
    missing = [str(path) for path in sidecar_paths.values() if not path.exists()]
    if missing:
        raise ExportError(f"Export did not produce: {', '.join(missing)}")
    return sidecar_paths
