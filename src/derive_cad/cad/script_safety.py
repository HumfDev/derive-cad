"""Lightweight import allowlist for LLM-generated build123d scripts.

Layered on top of the existing subprocess sandbox (cad/sandbox.py, unchanged) — this
runs before the script is ever executed and rejects obvious filesystem/network/process
access. It is not a hard security boundary: it only inspects plain `import`/`from ... import`
statements, not `__import__()`/`importlib`/`eval`/`exec` obfuscation. Its job is to raise
the bar against an LLM naively reaching for `os`/`shutil`/`socket`/`subprocess`, not to
replace the sandbox.
"""

import ast

ALLOWED_MODULES = frozenset(
    {
        "build123d",
        "math",
        "itertools",
        "dataclasses",
        "typing",
        "functools",
        "collections",
        "enum",
        "copy",
    }
)


def check_script_safety(script: str) -> list[str]:
    """Return a list of violation strings, one per disallowed import. Empty = safe.
    A script that fails to parse returns [] — syntax failures are handled separately
    by the syntax/import failure class downstream, not double-reported here."""
    try:
        tree = ast.parse(script)
    except SyntaxError:
        return []

    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_MODULES:
                    violations.append(f"disallowed import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root not in ALLOWED_MODULES:
                violations.append(f"disallowed import: {node.module}")
    return violations
