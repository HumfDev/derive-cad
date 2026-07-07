from derive_cad.cad.script_safety import check_script_safety

ALLOWED_SCRIPT = """\
from build123d import *
import math
import itertools
from dataclasses import dataclass


def gen_step() -> Part:
    with BuildPart() as part:
        Box(10, 10, 10)
    return part.part
"""


def test_allowed_imports_pass():
    assert check_script_safety(ALLOWED_SCRIPT) == []


def test_cadpy_assembly_import_allowed():
    script = """\
from build123d import *
from cadpy.assembly import AssemblyHelper


def gen_step():
    asm = AssemblyHelper("test")
    return asm.build()
"""
    assert check_script_safety(script) == []


def test_disallowed_os_import_flagged():
    script = "import os\nfrom build123d import *\n"
    violations = check_script_safety(script)
    assert any("os" in v for v in violations)


def test_disallowed_subprocess_import_flagged():
    script = "import subprocess\n"
    violations = check_script_safety(script)
    assert any("subprocess" in v for v in violations)


def test_disallowed_from_import_flagged():
    script = "from socket import socket\n"
    violations = check_script_safety(script)
    assert any("socket" in v for v in violations)


def test_syntax_error_returns_no_violations():
    script = "def broken(:\n"
    assert check_script_safety(script) == []


def test_multiple_disallowed_imports_all_flagged():
    script = "import os\nimport shutil\nimport socket\n"
    violations = check_script_safety(script)
    assert len(violations) == 3
