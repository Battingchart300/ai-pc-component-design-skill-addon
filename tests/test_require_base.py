"""require_base: the addon does not work without the base skill."""
import subprocess
import sys

from conftest import BASE_SKILL, KIT


def test_base_skill_present_passes():
    r = subprocess.run(
        [sys.executable, str(KIT / "require_base.py"),
         "--base-skill", str(BASE_SKILL)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_missing_base_skill_fails_exit_2(tmp_path):
    r = subprocess.run(
        [sys.executable, str(KIT / "require_base.py"),
         "--base-skill", str(tmp_path / "no-such-skill")],
        capture_output=True, text=True)
    assert r.returncode == 2, r.stdout


def test_check_aborts_without_base(tmp_path):
    # A check script must exit 2 and run no check when the base
    # skill is missing (hard dependency).
    from conftest import BASE_SPEC
    r = subprocess.run(
        [sys.executable, str(KIT / "pcie_check.py"), str(BASE_SPEC),
         "--base-skill", str(tmp_path / "no-such-skill")],
        capture_output=True, text=True)
    assert r.returncode == 2, r.stdout
    assert "ABORTED" in r.stdout
