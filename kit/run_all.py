#!/usr/bin/env python3
"""run_all.py — run every addon check, base skill first.

Order: require_base.py -> pcie_check.py -> vram_check.py ->
base rules_check.py on the base spec (if --spec is given and the
base kit is found). Any failure stops with that script's exit code.
Exit codes: 0 = all pass, 1 = a check failed, 2 = setup missing
(including: base skill missing).
Standard library only.
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXAMPLE = HERE / "examples" / "spec.json"


def run(cmd, label):
    print(f"--- {label}: {' '.join(cmd)}")
    r = subprocess.run(cmd)
    print(f"--- {label}: exit={r.returncode}")
    return r.returncode


def main():
    ap = argparse.ArgumentParser(description="Run all addon checks.")
    ap.add_argument("--addon-spec", default=str(EXAMPLE), help="Addon spec JSON")
    ap.add_argument("--spec", default=None, help="Base spec JSON (base rules_check.py)")
    ap.add_argument("--base-skill", default=None, help="Path to ai-pcb-design-skill repo")
    args = ap.parse_args()

    py = sys.executable
    base_args = ["--base-skill", args.base_skill] if args.base_skill else []

    code = run([py, str(HERE / "require_base.py")] + base_args, "require_base")
    if code != 0:
        print("run_all: STOP — base skill missing. No addon check ran.")
        print("Audit log: run_all=FAIL (require_base), exit=2")
        return 2

    code = run([py, str(HERE / "pcie_check.py"), args.addon_spec] + base_args, "pcie_check")
    if code != 0:
        print("Audit log: run_all=FAIL (pcie_check), exit=1")
        return 1

    code = run([py, str(HERE / "vram_check.py"), args.addon_spec] + base_args, "vram_check")
    if code != 0:
        print("Audit log: run_all=FAIL (vram_check), exit=1")
        return 1

    if args.spec:
        # Find the base kit to run its rules_check on the base spec.
        r = subprocess.run(
            [py, str(HERE / "require_base.py")] + base_args,
            capture_output=True, text=True,
        )
        # require_base prints the path; re-locate it the same way.
        sys.path.insert(0, str(HERE))
        from require_base import find_base_skill

        base_path, _ = find_base_skill(args.base_skill)
        if base_path is None:
            print("run_all: base skill vanished between checks — abort.")
            return 2
        base_rules = Path(base_path) / "kit" / "rules_check.py"
        if base_rules.is_file():
            code = run([py, str(base_rules), args.spec], "base rules_check")
            if code != 0:
                print("Audit log: run_all=FAIL (base rules_check), exit=1")
                return 1
        else:
            print(f"WARNING: base rules_check.py not found at {base_rules} — skipped, listed as a gap.")
    print("Audit log: run_all=PASS (require_base, pcie_check, vram_check), exit=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
