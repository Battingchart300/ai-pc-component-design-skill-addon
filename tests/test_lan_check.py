"""lan_check: an UNVERIFIED PHY counts as missing (v0.3.6
regression: `phy: "UNVERIFIED"` used to PASS). Same strictness as
the base skill's BOM rule: UNVERIFIED is not a part."""
from conftest import BASE_SPEC, FIXTURES, run_check


def test_valid_spec_passes():
    r = run_check("lan_check.py", BASE_SPEC)
    assert r.returncode == 0, r.stdout


def test_phy_unverified_fails_regression_fixture():
    # tests/fixtures/regression_phy_unverified.json: phy: "UNVERIFIED"
    r = run_check("lan_check.py", FIXTURES / "regression_phy_unverified.json")
    assert r.returncode == 1, r.stdout
    assert "UNVERIFIED" in r.stdout


def test_phy_unverified_fails_mutated(mutated):
    p = mutated({"lan.phy": "UNVERIFIED"})
    r = run_check("lan_check.py", p)
    assert r.returncode == 1, r.stdout


def test_phy_unverified_lowercase_fails(mutated):
    # Base skill convention: comparison is case-insensitive.
    p = mutated({"lan.phy": "unverified"})
    r = run_check("lan_check.py", p)
    assert r.returncode == 1, r.stdout


def test_phy_unverified_whitespace_fails(mutated):
    p = mutated({"lan.phy": "  UNVERIFIED  "})
    r = run_check("lan_check.py", p)
    assert r.returncode == 1, r.stdout


def test_phy_bool_fails(mutated):
    p = mutated({"lan.phy": True})
    r = run_check("lan_check.py", p)
    assert r.returncode == 1, r.stdout


def test_phy_named_part_passes(mutated):
    p = mutated({"lan.phy": "RTL8211F"})
    r = run_check("lan_check.py", p)
    assert r.returncode == 0, r.stdout
