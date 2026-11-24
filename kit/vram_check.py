#!/usr/bin/env python3
"""vram_check.py — VRAM type / bandwidth checks for an addon spec.

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
VOLTAGES = {"DDR3": 1.5, "DDR4": 1.2, "DDR5": 1.1, "LPDDR4X": 1.1, "GDDR6": None}


def require_base_or_exit(base_skill):
    cmd = [sys.executable, str(HERE / "require_base.py")]
    if base_skill:
        cmd += ["--base-skill", base_skill]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout, end="")
    if r.returncode != 0:
        print("vram_check: ABORTED — base skill missing, no check ran.")
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description="Check VRAM section of an addon spec.")
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
    vram = spec.get("vram")
    if not isinstance(vram, dict):
        print("ERROR: missing 'vram' section in spec")
        print("Audit log: vram_check=FAIL (1 error, 0 warnings), exit=1")
        return 1

    vtype = vram.get("type")
    if vtype not in VOLTAGES:
        errors.append(f"vram.type must be one of {sorted(VOLTAGES)}, got {vtype!r}")
    else:
        # Voltage check: rail voltage must match the memory type.
        power = spec.get("power", {}) if isinstance(spec.get("power"), dict) else {}
        rails = {r.get("rail"): r.get("voltage_v") for r in power.get("rails", []) if isinstance(r, dict)}
        # Find a rail whose name mentions the memory type
        expected = VOLTAGES[vtype]
        if expected is not None:
            found = [v for k, v in rails.items() if vtype in str(k).upper() or "DDR" in str(k).upper()]
            if found and found[0] != expected:
                errors.append(f"vram voltage mismatch: {vtype} needs {expected} V, rail is {found[0]} V")

    cap = vram.get("capacity_gb")
    if not isinstance(cap, (int, float)) or cap < 1:
        errors.append(f"vram.capacity_gb must be >= 1, got {cap!r}")
    width = vram.get("bus_width_bits")
    if width not in (32, 64, 128, 256):
        errors.append(f"vram.bus_width_bits must be 32/64/128/256, got {width!r}")
    rate = vram.get("data_rate_mt_s")
    if not isinstance(rate, (int, float)) or rate <= 0:
        errors.append(f"vram.data_rate_mt_s must be a positive number, got {rate!r}")

    bw = None
    if isinstance(width, (int, float)) and isinstance(rate, (int, float)) and rate > 0:
        bw = (width / 8) * rate / 1000.0
        print(f"VRAM bandwidth: {bw:.1f} GB/s ({width}-bit, {rate} MT/s)")
        if bw < 20.0:
            warnings.append(f"VRAM bandwidth {bw:.1f} GB/s is below ~20 GB/s — 1080p with textures will be slow (see SKILL.md §5).")
        if vtype == "GDDR6":
            warnings.append("GDDR6 needs a GDDR-capable controller/PHY — advanced, not a first build.")

    # BAR2 must cover the VRAM the OS maps (at least the framebuffer;
    # with ReBAR it should cover the whole VRAM).
    pcie = spec.get("pcie", {}) if isinstance(spec.get("pcie"), dict) else {}
    bar2_mb = pcie.get("bar2_mb")
    if isinstance(cap, (int, float)) and isinstance(bar2_mb, (int, float)):
        if pcie.get("resizable_bar") is True and bar2_mb < cap * 1024:
            warnings.append(f"ReBAR is on but BAR2 ({bar2_mb} MB) is smaller than VRAM ({cap} GB) — the whole VRAM will not map at once.")
        if bar2_mb < 256:
            errors.append("pcie.bar2_mb must be >= 256 MB to map a framebuffer.")

    for e in errors:
        print(f"ERROR: {e}")
    for w in warnings:
        print(f"WARNING: {w}")
    print(f"Audit log: vram_check={'FAIL' if errors else 'PASS'} ({len(errors)} errors, {len(warnings)} warnings), exit={1 if errors else 0}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
