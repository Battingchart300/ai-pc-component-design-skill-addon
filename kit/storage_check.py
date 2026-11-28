#!/usr/bin/env python3
"""storage_check.py — NVMe / SATA checks for an addon spec (v0.2).

The `storage` section is OPTIONAL. If it is absent, this script
prints a note and exits 0 — it does not fail a board without storage.
If it is present, it is validated.

Calls require_base.py FIRST. If the base skill is missing, exits 2
and runs no addon check — this addon does not work without it.

Exit codes: 0 = pass / skipped, 1 = fail (bad spec values),
2 = setup missing (base missing, spec file missing, spec not
valid JSON).
Standard library only.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def require_base_or_exit(base_skill):
    cmd = [sys.executable, str(HERE / "require_base.py")]
    if base_skill:
        cmd += ["--base-skill", base_skill]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout, end="")
    if r.returncode != 0:
        print("storage_check: ABORTED — base skill missing, no check ran.")
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description="Check storage section of an addon spec.")
    ap.add_argument("spec", help="Addon spec JSON file")
    ap.add_argument("--base-skill", default=None, help="Path to ai-pcb-design-skill repo")
    args = ap.parse_args()

    if not require_base_or_exit(args.base_skill):
        return 2

    try:
        text = Path(args.spec).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"ERROR: spec file not found: {args.spec}")
        print("Audit log: storage_check=FAIL (setup missing), exit=2")
        return 2
    except OSError as e:
        print(f"ERROR: cannot read spec {args.spec}: {e}")
        print("Audit log: storage_check=FAIL (setup missing), exit=2")
        return 2
    try:
        spec = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"ERROR: spec is not valid JSON: {e}")
        print("Audit log: storage_check=FAIL (setup missing), exit=2")
        return 2
    if not isinstance(spec, dict):
        print(f"ERROR: spec must be a JSON object, got {type(spec).__name__} "
              "(e.g. a list) — check the file's root type")
        print("Audit log: storage_check=FAIL (setup missing), exit=2")
        return 2

    storage = spec.get("storage")
    if storage is None:
        print("NOTE: no 'storage' section in spec — storage_check skipped (not a failure).")
        print("Audit log: storage_check=SKIP (0 errors, 0 warnings), exit=0")
        return 0
    if not isinstance(storage, dict):
        print("ERROR: 'storage' must be an object")
        return 1

    errors, warnings = [], []

    nvme = storage.get("nvme")
    if nvme is not None:
        if not isinstance(nvme, dict):
            errors.append("storage.nvme must be an object")
        else:
            if nvme.get("connector") != "M.2 M-key":
                errors.append(f"storage.nvme.connector must be 'M.2 M-key', got {nvme.get('connector')!r}")
            # lanes must be a positive integer. A boolean is NOT a lane
            # count: in Python True == 1, so `lanes: true` used to pass
            # the membership test below (True in (1, 2, 4)). Reject
            # booleans and non-integers explicitly first (v0.3.6).
            nlanes = nvme.get("lanes")
            if isinstance(nlanes, bool) or not isinstance(nlanes, int):
                errors.append(f"storage.nvme.lanes must be an integer 1/2/4 — a boolean is not a lane count, got {nlanes!r}")
            elif nlanes not in (1, 2, 4):
                errors.append(f"storage.nvme.lanes must be 1/2/4, got {nlanes!r}")
            if nvme.get("form_factor") not in ("2230", "2242", "2280"):
                errors.append(f"storage.nvme.form_factor must be 2230/2242/2280, got {nvme.get('form_factor')!r}")
            if nvme.get("power_v") != 3.3:
                errors.append(f"storage.nvme.power_v must be 3.3, got {nvme.get('power_v')!r}")
            if nvme.get("boot") is True:
                warnings.append("NVMe boot is flagged — verify the host BIOS/firmware supports booting from NVMe before ordering.")
            # Lane budget: NVMe lanes come from the same PCIe budget
            # as the FPGA bridge. The bridge endpoint always occupies
            # at least 1 host lane, so NVMe fits only when
            # 1 (bridge) + nvme.lanes <= pcie.lanes. Sharing the
            # lane(s) without a declared PCIe switch is an ERROR
            # (v0.3.5, Codex audit wave 2) — a lane used twice is a
            # short in the plan, not a saving (SKILL.md §13/§14).
            pcie = spec.get("pcie", {}) if isinstance(spec.get("pcie"), dict) else {}
            switch = pcie.get("switch")
            has_switch = (isinstance(switch, dict)
                          and isinstance(switch.get("part"), str)
                          and switch["part"].strip() != "")
            total = pcie.get("lanes")
            nlanes = nvme.get("lanes")
            if (isinstance(total, int) and not isinstance(total, bool)
                    and isinstance(nlanes, int) and not isinstance(nlanes, bool)):
                if 1 + nlanes > total:
                    if has_switch:
                        warnings.append(
                            f"NVMe shares the PCIe lane(s) with the FPGA bridge via switch "
                            f"{switch['part'].strip()!r} — verify the switch part and datasheet "
                            f"(port widths, Gen, power) before ordering; a switch multiplexes, "
                            f"it does not create bandwidth.")
                    else:
                        errors.append(
                            f"NVMe shares the PCIe lane(s) with the FPGA bridge: the bridge needs "
                            f"1 lane and NVMe needs {nlanes}, but the spec has only {total} total "
                            f"lane(s) — declare a PCIe switch (pcie.switch: {{\"part\": \"<switch chip>\"}}) "
                            f"or drop NVMe (one lane = bridge OR NVMe, see SKILL.md §13/§14).")

    sata = storage.get("sata")
    if sata is not None:
        if not isinstance(sata, dict):
            errors.append("storage.sata must be an object")
        else:
            if sata.get("ports") not in (1, 2, 4):
                errors.append(f"storage.sata.ports must be 1/2/4, got {sata.get('ports')!r}")
            if sata.get("speed") != "SATA III":
                errors.append(f"storage.sata.speed must be 'SATA III', got {sata.get('speed')!r}")
            if sata.get("power_v") not in ([5], [5, 12], [12, 5]):
                errors.append(f"storage.sata.power_v must list 5 V (SSD) or 5 V + 12 V (HDD), got {sata.get('power_v')!r}")

    if nvme is None and sata is None:
        warnings.append("storage section is present but has neither 'nvme' nor 'sata' — nothing to check.")

    for e in errors:
        print(f"ERROR: {e}")
    for w in warnings:
        print(f"WARNING: {w}")
    print(f"Audit log: storage_check={'FAIL' if errors else 'PASS'} ({len(errors)} errors, {len(warnings)} warnings), exit={1 if errors else 0}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
