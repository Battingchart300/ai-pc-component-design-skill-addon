#!/usr/bin/env python3
"""pcie_check.py — PCIe / enumeration checks for an addon spec.

Calls require_base.py FIRST. If the base skill is missing, exits 2
and runs no addon check — this addon does not work without it.

Exit codes: 0 = pass, 1 = fail, 2 = setup missing (base missing).
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
        print("pcie_check: ABORTED — base skill missing, no check ran.")
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description="Check PCIe section of an addon spec.")
    ap.add_argument("spec", help="Addon spec JSON file")
    ap.add_argument("--base-skill", default=None, help="Path to ai-pcb-design-skill repo")
    args = ap.parse_args()

    if not require_base_or_exit(args.base_skill):
        return 2

    try:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: cannot read spec: {e}")
        return 1

    errors, warnings = [], []

    pcie = spec.get("pcie")
    if not isinstance(pcie, dict):
        print("ERROR: missing 'pcie' section in spec")
        print("Audit log: pcie_check=FAIL (1 error, 0 warnings), exit=1")
        return 1

    gen = pcie.get("generation")
    if gen not in (2, 3, 4):
        errors.append(f"pcie.generation must be 2, 3 or 4 (2 = Pi 5 HAT only), got {gen!r}")
    if gen == 2 and pcie.get("lanes") != 1:
        errors.append(f"pcie generation 2 is Pi 5 HAT only and must be x1, got x{pcie.get('lanes')!r}")
    if pcie.get("lanes") not in (1, 4, 8, 16):
        errors.append(f"pcie.lanes must be 1/4/8/16, got {pcie.get('lanes')!r}")
    if str(pcie.get("class_code", "")).lower() != "0x030000":
        errors.append(f"pcie.class_code must be 0x030000 (VGA Display Controller), got {pcie.get('class_code')!r}")
    if not pcie.get("vendor_id") or not pcie.get("device_id"):
        errors.append("pcie.vendor_id and pcie.device_id are required (16-bit each)")
    bar0 = pcie.get("bar0_mb")
    if not isinstance(bar0, (int, float)) or not (1 <= bar0 <= 16):
        errors.append(f"pcie.bar0_mb must be 1-16 MB (control registers), got {bar0!r}")
    bar2 = pcie.get("bar2_mb")
    if not isinstance(bar2, (int, float)) or bar2 < 256:
        errors.append(f"pcie.bar2_mb must be >= 256 MB (VRAM), got {bar2!r}")
    if pcie.get("impedance_ohm") != 85:
        errors.append(f"pcie.impedance_ohm must be 85, got {pcie.get('impedance_ohm')!r}")
    if pcie.get("refclk_mhz") != 100:
        errors.append(f"pcie.refclk_mhz must be 100 (HCSL), got {pcie.get('refclk_mhz')!r}")
    if gen == 4 and pcie.get("tandem") is not True:
        errors.append("pcie.tandem must be true on PCIe 4.0 (enumeration under 100 ms, else BIOS ignores the card)")
    if gen == 3 and pcie.get("tandem") is not True:
        warnings.append("pcie.tandem is false on PCIe 3.0 — enable Tandem/CvP if the host BIOS enumerates fast.")
    if gen == 2:
        warnings.append("PCIe 2.0 x1 is a Pi 5 HAT link (~500 MB/s) — a starter, not a PC card (see SKILL.md §13).")
    if gen == 4 and pcie.get("lanes") == 16:
        warnings.append("PCIe 4.0 x16 on a first custom board is very hard — start at x4/x8 on a dev board (see SKILL.md §1).")

    # Power budget: slot 75 W + aux
    power = spec.get("power", {}) if isinstance(spec.get("power"), dict) else {}
    slot_w = power.get("slot_w", 75)
    aux_w = power.get("aux_w", 0)
    rails = power.get("rails", [])
    est_a = sum(r.get("current_a", 0) * r.get("voltage_v", 0) for r in rails if isinstance(r, dict))
    # est_a here is actually watts (V*A); name it est_w
    est_w = est_a
    if est_w > slot_w + aux_w:
        errors.append(f"power: estimated {est_w:.1f} W exceeds slot ({slot_w} W) + aux ({aux_w} W) budget")
    if est_w > 75 and not aux_w:
        errors.append("power: over 75 W needs a 6-pin or 8-pin PCIe aux connector (slot alone is 75 W max)")
    if not power.get("rails"):
        warnings.append("power.rails is empty — write the power tree (rails + currents) before routing.")

    board = spec.get("board", {}) if isinstance(spec.get("board"), dict) else {}
    layers = board.get("layers")
    if isinstance(layers, int) and gen == 4 and layers < 8:
        errors.append(f"board.layers={layers} is too few for PCIe 4.0 — use 8-14 layers with unbroken GND planes")
    if isinstance(layers, int) and gen == 2 and layers < 4:
        errors.append(f"board.layers={layers} is too few for a Pi 5 HAT — use 4-6 layers")

    for e in errors:
        print(f"ERROR: {e}")
    for w in warnings:
        print(f"WARNING: {w}")
    print(f"Audit log: pcie_check={'FAIL' if errors else 'PASS'} ({len(errors)} errors, {len(warnings)} warnings), exit={1 if errors else 0}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
