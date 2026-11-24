#!/usr/bin/env python3
"""pcie_check.py — PCIe / enumeration checks for an addon spec.

Calls require_base.py FIRST. If the base skill is missing, exits 2
and runs no addon check — this addon does not work without it.

Exit codes: 0 = pass, 1 = fail (bad spec values), 2 = setup missing
(base missing, spec file missing, spec not valid JSON).
Standard library only.
"""
import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# PCIe power limits (PCIe spec, see SKILL.md §3-§4). A slot gives at
# most 75 W; a 6-pin aux connector adds 75 W, an 8-pin adds 150 W,
# USB-C PD adds up to 100 W. No aux connector means 0 W aux.
SLOT_MAX_W = 75
AUX_MAX_W = {"6-pin": 75, "8-pin": 150, "USB-C": 100}

HEX_ID = re.compile(r"0x[0-9A-Fa-f]{4}$")


def is_num(x):
    """A real, finite number — rejects bool, strings, None and NaN."""
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def load_config():
    try:
        cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


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


def load_spec(path):
    """Return (spec, error_exit). error_exit is None on success, else 2
    for a missing file or unparseable JSON (setup missing, not a spec
    failure). Values inside a readable spec are checked later and
    fail with exit 1 instead."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"ERROR: spec file not found: {path}")
        return None, 2
    except OSError as e:
        print(f"ERROR: cannot read spec {path}: {e}")
        return None, 2
    try:
        return json.loads(text), None
    except json.JSONDecodeError as e:
        print(f"ERROR: spec is not valid JSON: {e}")
        return None, 2


def main():
    ap = argparse.ArgumentParser(description="Check PCIe section of an addon spec.")
    ap.add_argument("spec", help="Addon spec JSON file")
    ap.add_argument("--base-skill", default=None, help="Path to ai-pcb-design-skill repo")
    args = ap.parse_args()

    if not require_base_or_exit(args.base_skill):
        return 2

    spec, err = load_spec(args.spec)
    if err is not None:
        print(f"Audit log: pcie_check=FAIL (setup missing), exit={err}")
        return err

    cfg = load_config()
    pcie_cfg = cfg.get("pcie", {}) if isinstance(cfg.get("pcie"), dict) else {}
    slot_max = pcie_cfg.get("slot_power_w", SLOT_MAX_W)
    aux_max = {
        "6-pin": pcie_cfg.get("aux_6pin_w", 75),
        "8-pin": pcie_cfg.get("aux_8pin_w", 150),
        "USB-C": pcie_cfg.get("aux_usbc_w", 100),
    }

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
    # Vendor / Device ID: exactly 4 hex digits, e.g. 0x10EE.
    # Presence alone is not enough — 0xZZZZ used to pass.
    for field in ("vendor_id", "device_id"):
        val = pcie.get(field)
        if not isinstance(val, str) or not HEX_ID.match(val):
            errors.append(f"pcie.{field} must be a 4-hex-digit ID like 0x10EE, got {val!r}")
    bar0 = pcie.get("bar0_mb")
    if not is_num(bar0) or not (1 <= bar0 <= 16):
        errors.append(f"pcie.bar0_mb must be 1-16 MB (control registers), got {bar0!r}")
    bar2 = pcie.get("bar2_mb")
    if not is_num(bar2) or bar2 < 256:
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

    # Power budget: slot max 75 W + aux, by connector type.
    # slot_w / aux_w are taken from the spec, but they are CHECKED
    # against the PCIe limits — a made-up 300 W slot used to pass.
    power = spec.get("power", {}) if isinstance(spec.get("power"), dict) else {}
    slot_w = power.get("slot_w", 75)
    aux_w = power.get("aux_w", 0)
    aux_conn = power.get("aux_connector")
    if not is_num(slot_w) or slot_w < 0 or slot_w > slot_max:
        errors.append(f"power.slot_w must be a number 0-{slot_max} W (PCIe slot max), got {slot_w!r}")
        slot_w = 0 if not is_num(slot_w) else max(0, min(slot_w, slot_max))
    if not is_num(aux_w) or aux_w < 0:
        errors.append(f"power.aux_w must be a non-negative number, got {aux_w!r}")
        aux_w = 0
    if aux_conn:
        kind = next((k for k in aux_max if k in str(aux_conn)), None)
        if kind is None:
            errors.append(f"power.aux_connector {aux_conn!r} is unknown — use a 6-pin PCIe, 8-pin PCIe or USB-C connector")
        elif aux_w > aux_max[kind]:
            errors.append(f"power.aux_w {aux_w} W exceeds the {kind} aux limit of {aux_max[kind]} W (connector: {aux_conn!r})")
    elif aux_w:
        errors.append(f"power.aux_w is {aux_w} W but no power.aux_connector is declared — aux power without a connector is 0 W")
    rails = power.get("rails", [])
    if not isinstance(rails, list):
        errors.append(f"power.rails must be a list, got {rails!r}")
        rails = []
    est_w = 0.0
    for r in rails:
        if not isinstance(r, dict):
            errors.append(f"power.rails entry must be an object, got {r!r}")
            continue
        v, a = r.get("voltage_v"), r.get("current_a")
        if not is_num(v) or v <= 0:
            errors.append(f"power rail {r.get('rail')!r}: voltage_v must be a positive number, got {v!r}")
            continue
        if not is_num(a) or a < 0:
            errors.append(f"power rail {r.get('rail')!r}: current_a must be a non-negative number, got {a!r}")
            continue
        est_w += v * a
    if est_w > slot_w + aux_w:
        errors.append(f"power: estimated {est_w:.1f} W exceeds slot ({slot_w} W) + aux ({aux_w} W) budget")
    if est_w > 75 and not aux_w:
        errors.append("power: over 75 W needs a 6-pin or 8-pin PCIe aux connector (slot alone is 75 W max)")
    if not power.get("rails"):
        warnings.append("power.rails is empty — write the power tree (rails + currents) before routing.")

    board = spec.get("board", {}) if isinstance(spec.get("board"), dict) else {}
    layers = board.get("layers")
    if not isinstance(layers, int) or isinstance(layers, bool) or layers <= 0:
        errors.append(f"board.layers is required — a positive integer (layer count), got {layers!r}")
    else:
        if gen == 4 and layers < 8:
            errors.append(f"board.layers={layers} is too few for PCIe 4.0 — use 8-14 layers with unbroken GND planes")
        if gen == 2 and layers < 4:
            errors.append(f"board.layers={layers} is too few for a Pi 5 HAT — use 4-6 layers")

    for e in errors:
        print(f"ERROR: {e}")
    for w in warnings:
        print(f"WARNING: {w}")
    print(f"Audit log: pcie_check={'FAIL' if errors else 'PASS'} ({len(errors)} errors, {len(warnings)} warnings), exit={1 if errors else 0}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
