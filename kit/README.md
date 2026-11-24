# kit — addon checks

All scripts are standard library only, no installation needed.
Windows: use `python`. macOS/Linux: use `python3`.

**The base skill is required first.** Every script calls
`require_base.py` before it checks anything. If
`ai-pcb-design-skill` v1.2.1+ is not found, the script exits `2`
and runs **no** addon check.

## How the base skill is found

1. `--base-skill <path>`
2. `AI_PCB_SKILL_PATH` environment variable
3. `../ai-pcb-design-skill` (sibling of this repo)
4. `./ai-pcb-design-skill`
5. `~/workspace/ai-pcb-design-skill`
6. Walking up from the current directory, `ai-pcb-design-skill` as a sibling

## Scripts

| Script | What it checks |
|---|---|
| `require_base.py` | Base skill present, `SKILL.md` exists, version >= 1.2.1. Exit 2 if missing/old. |
| `pcie_check.py <addon-spec.json>` | PCIe generation/lanes, class code 0x030000, Vendor/Device ID, BAR0/BAR2, 85 Ω, 100 MHz, Tandem on PCIe 4.0, slot+aux power budget, 8+ layers on PCIe 4.0. Gen 2/3 x1 accepted for a Pi 5 HAT. |
| `vram_check.py <addon-spec.json>` | VRAM type/voltage match (DDR4 1.2 V, DDR5 1.1 V), capacity, bus width, data rate, bandwidth in GB/s, BAR2 vs VRAM with ReBAR. |
| `storage_check.py <addon-spec.json>` (v0.2) | Optional `storage`: NVMe M.2 M-key / lanes / form factor / 3.3 V / boot flag, SATA III / ports / power. Skips with a note if no storage section. |
| `lan_check.py <addon-spec.json>` (v0.2) | Optional `lan`: RJ45, 1/2.5 GbE, PHY, magnetics, ESD. Skips with a note if no LAN section. |
| `run_all.py` | Runs require_base, pcie_check, vram_check, storage_check, lan_check, then the base `rules_check.py` if `--spec` (base spec) is given. |

Exit codes: `0` = pass, `1` = fail, `2` = setup missing.

## Examples

```bash
python kit/run_all.py
python kit/pcie_check.py kit/examples/spec.json
python kit/vram_check.py kit/examples/spec.json
python kit/storage_check.py kit/examples/spec.json
python kit/lan_check.py kit/examples/spec.json
python kit/run_all.py --addon-spec kit/examples/spec_pi5_hat.json
python kit/run_all.py --base-skill ../ai-pcb-design-skill
```

`kit/examples/spec.json` is a sample FPGA GPU addon spec that
**passes** all addon checks (8 GB DDR4-3200, 64-bit, 25.6 GB/s,
PCIe 4.0 x8, Class 0x030000, BAR0 16 MB, BAR2 8192 MB, Tandem on,
NVMe M.2 2280 x4 + SATA x2, RJ45 1GbE).
`kit/examples/spec_pi5_hat.json` is a sample Pi 5 HAT addon spec
that **passes** (PCIe 2.0 x1, 4 layers, CrossLink-NX bridge +
32× CH32V003, 1 GB DDR4, NVMe 2230 x1, RJ45 1GbE).
