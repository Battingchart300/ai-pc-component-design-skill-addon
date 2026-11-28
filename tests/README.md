# Tests — ai-pc-component-design-skill-addon

Run from the repo root:

```sh
PYTHONPATH=$HOME/.local/lib/python3.12/site-packages python3 -m pytest
```

(`pytest` is not installed system-wide on this machine.)

Each `test_*_check.py` runs the matching `kit/*_check.py` script as a
subprocess on `kit/examples/spec.json` (the valid base spec) or on a
mutated copy of it, with `--base-skill` pointing at the sibling
`ai-pcb-design-skill` repo (the hard dependency).

`tests/fixtures/` holds the regression fixtures for v0.3.6 — one full
spec per fixed bug, each failing before the fix and passing after it:

- `regression_pcie_lanes_bool.json` — `pcie.lanes: true` must FAIL
- `regression_nvme_lanes_bool.json` — `storage.nvme.lanes: true` must FAIL
- `regression_phy_unverified.json` — `lan.phy: "UNVERIFIED"` must FAIL
