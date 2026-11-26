#!/usr/bin/env python3
"""run_all.py — run every addon check, base skill first.

Order: require_base.py -> pcie_check.py -> vram_check.py ->
storage_check.py -> lan_check.py -> base rules_check.py on the
base spec (if --spec is given and the base kit is found).
A missing kit script is a setup failure (exit 2), never a silent
PASS — every step is verified to exist before it runs.
Exit codes: 0 = all pass, 1 = a check failed, 2 = setup missing
(including: base skill missing, kit script missing, spec unreadable).
Standard library only.
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXAMPLE = HERE / "examples" / "spec.json"
# Credit line (v0.3.5): printed once, as the last line, in the
# audit-log footer. No online check, no popup, no behaviour change.
CREDIT = "Made by PTS6845 — https://battingchart300.github.io"
# Every script run_all depends on. Checked up front (fix v0.3.0):
# a missing check must FAIL, never silently pass.
CHECKS = ["require_base.py", "pcie_check.py", "vram_check.py",
          "storage_check.py", "lan_check.py"]


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

    missing = [name for name in CHECKS if not (HERE / name).is_file()]
    if missing:
        for name in missing:
            print(f"ERROR: missing kit script: kit/{name} — cannot run checks.")
        print("Audit log: run_all=FAIL (missing kit script), exit=2")
        return 2

    py = sys.executable
    base_args = ["--base-skill", args.base_skill] if args.base_skill else []

    code = run([py, str(HERE / "require_base.py")] + base_args, "require_base")
    if code != 0:
        print("run_all: STOP — base skill missing. No addon check ran.")
        print(f"Audit log: run_all=FAIL (require_base), exit={code}")
        return code

    for script in ["pcie_check.py", "vram_check.py", "storage_check.py", "lan_check.py"]:
        label = script[:-3]
        code = run([py, str(HERE / script), args.addon_spec] + base_args, label)
        if code != 0:
            print(f"Audit log: run_all=FAIL ({label}), exit={code}")
            return code

    if args.spec:
        # Find the base kit to run its rules_check on the base spec.
        sys.path.insert(0, str(HERE))
        from require_base import find_base_skill

        base_path, _ = find_base_skill(args.base_skill)
        if base_path is None:
            print("run_all: base skill vanished between checks — abort.")
            return 2
        base_rules = Path(base_path) / "kit" / "rules_check.py"
        if not base_rules.is_file():
            print(f"ERROR: missing base check script: {base_rules} — cannot run base rules_check, not a pass.")
            print("Audit log: run_all=FAIL (base rules_check missing), exit=2")
            return 2
        code = run([py, str(base_rules), args.spec], "base rules_check")
        if code != 0:
            print(f"Audit log: run_all=FAIL (base rules_check), exit={code}")
            return code
    print("Audit log: run_all=PASS (require_base, pcie_check, vram_check, storage_check, lan_check), exit=0")
    return 0


if __name__ == "__main__":
    code = main()
    print(CREDIT)
    sys.exit(code)
