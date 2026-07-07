from derive_cad.llm.prompts import CAD_REPAIR_SYSTEM_PROMPT, CAD_REPAIR_USER_PROMPT


def test_repair_system_prompt_loads_upstream_repair_loop():
    assert "Fillet or chamfer failure" in CAD_REPAIR_SYSTEM_PROMPT
    assert "skills/cad/references/repair-loop.md" in CAD_REPAIR_SYSTEM_PROMPT
    assert "Make the smallest responsible source or command change" in CAD_REPAIR_SYSTEM_PROMPT
    assert "inspection-and-validation.md" in CAD_REPAIR_SYSTEM_PROMPT
    assert "...(truncated)..." not in CAD_REPAIR_SYSTEM_PROMPT


def test_repair_user_prompt_includes_failure_context():
    prompt = CAD_REPAIR_USER_PROMPT.format(
        classification="Fillet or chamfer failure",
        failure_message="STEP generation failed: fillet radius too large",
        stderr="ValueError: Failed creating a fillet",
        violations="- bbox: geometry is degenerate",
        review="(not performed)",
        brief="CAD brief test",
        prompt="make a phone stand",
        previous_script="from build123d import *\n",
    )
    assert "make a phone stand" in prompt
    assert "from build123d import *" in prompt
    assert "fillet radius too large" in prompt
    assert "Fillet or chamfer failure" in prompt
    assert "repair-loop.md" in prompt
