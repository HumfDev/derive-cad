from derive_cad.skill.paths import cad_script_main, cad_skill_dir, repo_root


def test_repo_root_contains_skills_cad():
    root = repo_root()
    assert (root / "skills" / "cad" / "SKILL.md").is_file()


def test_cad_script_entrypoints_exist():
    assert cad_skill_dir().name == "cad"
    for tool in ("step", "inspect", "snapshot"):
        assert cad_script_main(tool).is_file()
