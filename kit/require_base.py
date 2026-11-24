#!/usr/bin/env python3
"""require_base.py — hard prerequisite check for the addon skill.

This addon does NOT work without ai-pcb-design-skill v1.2.1+.
This script finds the base skill and verifies it. Exit codes:
  0 = base skill found, version OK
  2 = setup missing (base skill not found, or version too old)

Search order for the base skill directory:
  1. --base-skill <path> argument
  2. AI_PCB_SKILL_PATH environment variable
  3. ../ai-pcb-design-skill (sibling of this repo)
  4. ./ai-pcb-design-skill
  5. ~/workspace/ai-pcb-design-skill
  6. parent directories walking up from this file, looking for
     ai-pcb-design-skill as a sibling

Standard library only.
"""
import argparse
import os
import re
import sys
from pathlib import Path

REQUIRED_NAME = "ai-pcb-design-skill"
REQUIRED_VERSION = (1, 2, 1)


def parse_version(text):
    """Parse 'Version: 1.2.1' or '1.2.1' from SKILL.md text."""
    m = re.search(r"Version:\s*(\d+)\.(\d+)\.(\d+)", text)
    if m:
        return tuple(int(x) for x in m.groups())
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    if m:
        return tuple(int(x) for x in m.groups())
    return None


def find_base_skill(explicit=None):
    """Return (path, version) or (None, None).

    An explicit --base-skill path (or AI_PCB_SKILL_PATH) is
    authoritative: if it does not contain a valid base skill,
    this returns (None, None) instead of falling through to
    another copy. That is what makes the dependency hard.
    """
    candidates = []
    authoritative = False
    if explicit:
        candidates.append(Path(explicit))
        authoritative = True
    else:
        env = os.environ.get("AI_PCB_SKILL_PATH")
        if env:
            candidates.append(Path(env))
            authoritative = True

    if authoritative:
        cand = candidates[0].expanduser()
        skill_md = cand / "SKILL.md"
        if not skill_md.is_file():
            return None, None
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
        if f"name: {REQUIRED_NAME}" not in text:
            return None, None
        return cand, parse_version(text)

    here = Path(__file__).resolve()
    # sibling of this repo: <repo>/kit/require_base.py -> <repo>/..
    candidates.append(here.parent.parent.parent / REQUIRED_NAME)
    candidates.append(Path.cwd() / REQUIRED_NAME)
    candidates.append(Path.home() / "workspace" / REQUIRED_NAME)
    # walk up from cwd
    p = Path.cwd().resolve()
    for parent in [p] + list(p.parents):
        candidates.append(parent / REQUIRED_NAME)

    seen = set()
    for cand in candidates:
        cand = cand.expanduser()
        key = str(cand.resolve()) if cand.exists() else str(cand)
        if key in seen:
            continue
        seen.add(key)
        skill_md = cand / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8", errors="ignore")
        if f"name: {REQUIRED_NAME}" not in text:
            continue
        version = parse_version(text)
        return cand, version
    return None, None


def main():
    ap = argparse.ArgumentParser(description="Verify base skill ai-pcb-design-skill is present.")
    ap.add_argument("--base-skill", default=None, help="Path to ai-pcb-design-skill repo")
    args = ap.parse_args()

    path, version = find_base_skill(args.base_skill)
    if path is None:
        print("BASE SKILL MISSING — STOP")
        print("This addon does not work without ai-pcb-design-skill v1.2.1+.")
        print("Load the base skill first, or pass --base-skill <path>,")
        print("or set AI_PCB_SKILL_PATH. No addon check ran.")
        print("Audit log: require_base=FAIL (base not found), exit=2")
        return 2
    if version is None or version < REQUIRED_VERSION:
        have = ".".join(map(str, version)) if version else "unknown"
        need = ".".join(map(str, REQUIRED_VERSION))
        print(f"BASE SKILL TOO OLD — STOP: found v{have}, need v{need}+ at {path}")
        print("Audit log: require_base=FAIL (version), exit=2")
        return 2
    print(f"Base skill OK: {REQUIRED_NAME} v{'.'.join(map(str, version))} at {path}")
    print("Audit log: require_base=PASS, exit=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
