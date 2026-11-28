"""storage_check: nvme.lanes must be a positive integer; booleans
are not lane counts (v0.3.6 regression: `nvme.lanes: true` used to
PASS because in Python True == 1)."""
from conftest import BASE_SPEC, FIXTURES, run_check


def test_valid_spec_passes():
    r = run_check("storage_check.py", BASE_SPEC)
    assert r.returncode == 0, r.stdout


def test_nvme_lanes_bool_true_fails_regression_fixture():
    # tests/fixtures/regression_nvme_lanes_bool.json: nvme.lanes: true
    r = run_check("storage_check.py", FIXTURES / "regression_nvme_lanes_bool.json")
    assert r.returncode == 1, r.stdout
    assert "storage.nvme.lanes must be an integer" in r.stdout
    assert "boolean is not a lane count" in r.stdout


def test_nvme_lanes_bool_true_fails_mutated(mutated):
    p = mutated({"storage.nvme.lanes": True})
    r = run_check("storage_check.py", p)
    assert r.returncode == 1, r.stdout


def test_nvme_lanes_bool_false_fails(mutated):
    p = mutated({"storage.nvme.lanes": False})
    r = run_check("storage_check.py", p)
    assert r.returncode == 1, r.stdout


def test_nvme_lanes_invalid_int_fails(mutated):
    p = mutated({"storage.nvme.lanes": 3})
    r = run_check("storage_check.py", p)
    assert r.returncode == 1, r.stdout
    assert "storage.nvme.lanes must be 1/2/4" in r.stdout


def test_nvme_lanes_valid_values_pass(mutated):
    # NVMe lanes share the PCIe budget with the FPGA bridge (1 lane),
    # so only lanes that fit in pcie.lanes=8 pass the budget check.
    for lanes in (1, 2, 4):
        p = mutated({"storage.nvme.lanes": lanes})
        r = run_check("storage_check.py", p)
        assert r.returncode == 0, (lanes, r.stdout)
