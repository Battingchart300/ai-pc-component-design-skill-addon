"""Shared helpers for the PC addon pytest suite (v0.3.6)."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "kit"
BASE_SKILL = ROOT.parent / "ai-pcb-design-skill"
BASE_SPEC = KIT / "examples" / "spec.json"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_spec(path=BASE_SPEC):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_spec(tmp_path, spec, name="spec.json"):
    p = tmp_path / name
    p.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return str(p)


def set_path(spec, dotted, value):
    """Set a dotted path (list indices as digits) in a nested spec."""
    parts = dotted.split(".")
    node = spec
    for part in parts[:-1]:
        node = node[int(part)] if part.isdigit() else node[part]
    last = parts[-1]
    if last.isdigit():
        node[int(last)] = value
    else:
        node[last] = value


def run_check(script, spec_path, base_skill=str(BASE_SKILL)):
    """Run a kit validator script on a spec file (positional spec
    arg); returns CompletedProcess."""
    cmd = [sys.executable, str(KIT / script), str(spec_path)]
    if base_skill is not None:
        cmd += ["--base-skill", base_skill]
    return subprocess.run(cmd, capture_output=True, text=True)


@pytest.fixture
def mutated(tmp_path):
    """Return a helper: mutated(overrides) -> path of a spec file
    built from kit/examples/spec.json with dotted-path overrides."""
    def _mutate(overrides, base=BASE_SPEC):
        spec = load_spec(base)
        for dotted, value in overrides.items():
            set_path(spec, dotted, value)
        return write_spec(tmp_path, spec)
    return _mutate
