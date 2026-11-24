#!/usr/bin/env python3
"""vram_check.py — VRAM type / bandwidth checks for an addon spec.

Calls require_base.py FIRST. If the base skill is missing, exits 2
and runs no addon check — this addon does not work without it.

Exit codes: 0 = pass, 1 = fail (bad spec values), 2 = setup missing
(base missing, spec file missing, spec not valid JSON).
Standard library only.
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VOLTAGES = {"DDR3": 1.5, "DDR4": 1.2, "DDR5": 1.1, "LPDDR4X": 1.1, "GDDR6": None}
# Max data rate the MEMORY TYPE supports (MT/s). Only types with a
# verified limit are listed — others are UNVERIFIED, not invented.
MAX_RATE = {"DDR4": 3200, "DDR5": 6400}


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
        print("vram_check: ABORTED — base skill missing, no check ran.")
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
    ap = argparse.ArgumentParser(description="Check VRAM section of an addon spec.")
    ap.add_argument("spec", help="Addon spec JSON file")
    ap.add_argument("--base-skill", default=None, help="Path to ai-pcb-design-skill repo")
    args = ap.parse_args()

    if not require_base_or_exit(args.base_skill):
        return 2

    spec, err = load_spec(args.spec)
    if err is not None:
        print(f"Audit log: vram_check=FAIL (setup missing), exit={err}")
        return err

    cfg = load_config()
    vram_cfg = cfg.get("vram", {}) if isinstance(cfg.get("vram"), dict) else {}
    max_rate = dict(MAX_RATE)
    if isinstance(vram_cfg.get("max_data_rate_mt_s"), dict):
        for k, v in vram_cfg["max_data_rate_mt_s"].items():
            if is_num(v):
                max_rate[k] = v
    fpga_limits = vram_cfg.get("fpga_max_ddr_mt_s", {})
    if not isinstance(fpga_limits, dict):
        fpga_limits = {}

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
        expected = VOLTAGES[vtype]
        if expected is not None:
            # 1) The spec's own voltage field, if present, must match.
            #    A 1.5 V DDR4 used to pass because this field was ignored.
            if "voltage_v" in vram:
                vv = vram.get("voltage_v")
                if not is_num(vv) or vv != expected:
                    errors.append(f"vram.voltage_v must be {expected} V for {vtype}, got {vv!r}")
            else:
                # 2) Fallback: a power rail named after the memory type.
                power = spec.get("power", {}) if isinstance(spec.get("power"), dict) else {}
                rails = {r.get("rail"): r.get("voltage_v") for r in power.get("rails", []) if isinstance(r, dict)}
                found = [v for k, v in rails.items() if vtype in str(k).upper() or "DDR" in str(k).upper()]
                if found and (not is_num(found[0]) or found[0] != expected):
                    errors.append(f"vram voltage mismatch: {vtype} needs {expected} V, rail is {found[0]} V")

    cap = vram.get("capacity_gb")
    if not is_num(cap) or cap < 1:
        errors.append(f"vram.capacity_gb must be a finite number >= 1, got {cap!r}")
    width = vram.get("bus_width_bits")
    if width not in (32, 64, 128, 256):
        errors.append(f"vram.bus_width_bits must be 32/64/128/256, got {width!r}")
    rate = vram.get("data_rate_mt_s")
    if not is_num(rate) or rate <= 0:
        errors.append(f"vram.data_rate_mt_s must be a positive finite number, got {rate!r}")
    elif vtype in max_rate and rate > max_rate[vtype]:
        errors.append(f"vram.data_rate_mt_s {rate} exceeds the {vtype} max of {max_rate[vtype]} MT/s")

    # FPGA data-rate cap: the memory controller in the FPGA may be
    # slower than the memory type. Precedence: spec override (with a
    # datasheet citation) > config.json lookup by FPGA part > type max.
    # A part with no entry anywhere is UNVERIFIED, not silently fine.
    if is_num(rate) and rate > 0 and vtype in VOLTAGES:
        fpga = spec.get("fpga", {}) if isinstance(spec.get("fpga"), dict) else {}
        part = fpga.get("part")
        limit = None
        if is_num(fpga.get("max_ddr_mt_s")):
            limit = fpga["max_ddr_mt_s"]
            if not fpga.get("max_ddr_source"):
                warnings.append(f"fpga.max_ddr_mt_s {limit} has no datasheet citation (fpga.max_ddr_source) — add one.")
        elif isinstance(part, str) and part in fpga_limits and is_num(fpga_limits[part]):
            limit = fpga_limits[part]
        if limit is not None and rate > limit:
            errors.append(f"vram.data_rate_mt_s {rate} exceeds the FPGA {part} max of {limit} MT/s (see kit/config.json fpga_max_ddr_mt_s)")
        elif limit is None and part:
            warnings.append(f"fpga.max_ddr_mt_s for {part} is UNVERIFIED — check the FPGA datasheet and add it to kit/config.json.")

    bw = None
    if isinstance(width, (int, float)) and is_num(rate):
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
    if is_num(cap) and is_num(bar2_mb):
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
