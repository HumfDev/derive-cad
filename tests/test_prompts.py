from derive_cad.llm.prompts import (
    CAD_REPAIR_SYSTEM_PROMPT,
    CAD_SYSTEM_PROMPT,
    cad_repair_system_prompt,
    cad_system_prompt,
)


def test_part_codegen_prompt_excludes_positioning():
    prompt = cad_system_prompt(is_assembly=False)
    assert "build123d modeling patterns" in prompt.lower() or "Modeling patterns" in prompt
    assert "STEP generation" in prompt
    assert "AssemblyHelper pattern" not in prompt


def test_assembly_codegen_prompt_includes_positioning():
    prompt = cad_system_prompt(is_assembly=True)
    assert "AssemblyHelper pattern" in prompt
    assert "face_to_face" in prompt


def test_part_repair_prompt_excludes_positioning():
    prompt = cad_repair_system_prompt(is_assembly=False)
    assert "Fillet or chamfer failure" in prompt
    assert "AssemblyHelper pattern" not in prompt


def test_assembly_repair_prompt_includes_positioning():
    prompt = cad_repair_system_prompt(is_assembly=True)
    assert "AssemblyHelper pattern" in prompt


def test_default_prompt_constants_match_part_task():
    assert CAD_SYSTEM_PROMPT == cad_system_prompt(is_assembly=False)
    assert CAD_REPAIR_SYSTEM_PROMPT == cad_repair_system_prompt(is_assembly=False)
