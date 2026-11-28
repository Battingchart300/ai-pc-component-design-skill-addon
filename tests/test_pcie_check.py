"""pcie_check: lanes must be a positive integer; booleans are not
lane counts (v0.3.6 regression: `lanes: true` used to PASS because
in Python True == 1)."""
from conftest import BASE_SPEC, FIXTURES, run_check


def test_valid_spec_passes():
    r = run_check("pcie_check.py", BASE_SPEC)
    assert r.returncode == 0, r.stdout


def test_lanes_bool_true_fails_regression_fixture():
    # tests/fixtures/regression_pcie_lanes_bool.json: lanes: true
    r = run_check("pcie_check.py", FIXTURES / "regression_pcie_lanes_bool.json")
    assert r.returncode == 1, r.stdout
    assert "pcie.lanes must be an integer" in r.stdout
    assert "boolean is not a lane count" in r.stdout


def test_lanes_bool_true_fails_mutated(mutated):
    p = mutated({"pcie.lanes": True})
    r = run_check("pcie_check.py", p)
    assert r.returncode == 1, r.stdout


def test_lanes_bool_false_fails(mutated):
    p = mutated({"pcie.lanes": False})
    r = run_check("pcie_check.py", p)
    assert r.returncode == 1, r.stdout


def test_lanes_string_fails(mutated):
    p = mutated({"pcie.lanes": "8"})
    r = run_check("pcie_check.py", p)
    assert r.returncode == 1, r.stdout


def test_lanes_invalid_int_fails(mutated):
    p = mutated({"pcie.lanes": 3})
    r = run_check("pcie_check.py", p)
    assert r.returncode == 1, r.stdout
    assert "pcie.lanes must be 1/4/8/16" in r.stdout


def test_lanes_valid_values_pass(mutated):
    for lanes in (1, 4, 8, 16):
        # gen 4 + x1 is legal here (the gen-2 x1-only rule does not apply)
        p = mutated({"pcie.lanes": lanes})
        r = run_check("pcie_check.py", p)
        assert r.returncode == 0, (lanes, r.stdout)
