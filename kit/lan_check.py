#!/usr/bin/env python3
"""lan_check.py — RJ45 LAN checks for an addon spec (v0.2).

The `lan` section is OPTIONAL. If it is absent, this script prints
a note and exits 0 — it does not fail a board without LAN.
If it is present, it is validated. An RJ45 jack alone is not a
network port: PHY + magnetics + ESD are required.

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
        print("lan_check: ABORTED — base skill missing, no check ran.")
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description="Check LAN section of an addon spec.")
    ap.add_argument("spec", help="Addon spec JSON file")
    ap.add_argument("--base-skill", default=None, help="Path to ai-pcb-design-skill repo")
    args = ap.parse_args()

    if not require_base_or_exit(args.base_skill):
        return 2

    try:
        text = Path(args.spec).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"ERROR: spec file not found: {args.spec}")
        print("Audit log: lan_check=FAIL (setup missing), exit=2")
        return 2
    except OSError as e:
        print(f"ERROR: cannot read spec {args.spec}: {e}")
        print("Audit log: lan_check=FAIL (setup missing), exit=2")
        return 2
    try:
        spec = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"ERROR: spec is not valid JSON: {e}")
        print("Audit log: lan_check=FAIL (setup missing), exit=2")
        return 2
    if not isinstance(spec, dict):
        print(f"ERROR: spec must be a JSON object, got {type(spec).__name__} "
              "(e.g. a list) — check the file's root type")
        print("Audit log: lan_check=FAIL (setup missing), exit=2")
        return 2

    lan = spec.get("lan")
    if lan is None:
        print("NOTE: no 'lan' section in spec — lan_check skipped (not a failure).")
        print("Audit log: lan_check=SKIP (0 errors, 0 warnings), exit=0")
        return 0
    if not isinstance(lan, dict):
        print("ERROR: 'lan' must be an object")
        return 1

    errors, warnings = [], []

    if lan.get("connector") != "RJ45":
        errors.append(f"lan.connector must be 'RJ45', got {lan.get('connector')!r}")
    if lan.get("speed") not in ("1GbE", "2.5GbE"):
        errors.append(f"lan.speed must be '1GbE' or '2.5GbE' (10GbE is advanced, not a first build), got {lan.get('speed')!r}")
    phy = lan.get("phy")
    if not isinstance(phy, str) or not phy.strip():
        errors.append("lan.phy must name a PHY chip (e.g. 'RTL8211F') — a boolean true is not a part; a MAC must not connect directly to an RJ45 jack (PHY chip needed, with datasheet)")
    if lan.get("magnetics") is not True:
        errors.append("lan.magnetics must be true — magnetics (in the jack or discrete, per PHY datasheet) are required")
    if lan.get("esd") is not True:
        errors.append("lan.esd must be true — ESD diodes on the jack side, close to the connector")
    if lan.get("poe") is True:
        warnings.append("PoE is flagged — it needs a PoE PD controller + isolation, do not wire 48 V to the jack directly.")

    for e in errors:
        print(f"ERROR: {e}")
    for w in warnings:
        print(f"WARNING: {w}")
    print(f"Audit log: lan_check={'FAIL' if errors else 'PASS'} ({len(errors)} errors, {len(warnings)} warnings), exit={1 if errors else 0}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
