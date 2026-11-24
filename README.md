# ai-pc-component-design-skill-addon

Addon to `ai-pcb-design-skill` for designing PC components — FPGA GPU on PCIe 4.0, DDR4/DDR5 VRAM, custom motherboard and RAM.

**Version:** 0.1.0 — 2026-11-24

> **REQUIRED: this addon does NOT work without the base skill.**
> It requires `ai-pcb-design-skill` **v1.2.1 or newer**. Load the base
> skill first. If the base skill is missing, this addon stops — in the
> docs (§0) and in the kit scripts (exit code `2`).

## What it adds on top of the base skill

The base skill teaches PCB design from a prompt to Gerbers: spec,
schematic, layout, DRC, BOM, fab. This addon adds only the PC-component
parts:

- **PCIe 4.0** — 16 GT/s per lane, 85 Ω pairs, 100 MHz HCSL clock, AC coupling on TX, back-drilling, 8–14 layer stackup
- **Power delivery** — 6–10 rails (0.72/0.85 V core at 20–50 A, 1.2 V DDR, 1.8 V I/O), power sequencing, 75 W slot limit + 6/8-pin aux power
- **VRAM** — DDR4/DDR5 (GDDR6 noted as advanced), MIG controller, bandwidth calculation, Resizable BAR
- **FPGA GPU core** — command processor, vertex shader, rasterizer, fragment shader, texture unit, ROP, display controller, own shader ISA (fixed-point first)
- **BIOS / UEFI** — Class Code 0x030000, BAR0/BAR2, Tandem PCIe / CvP under 100 ms, QSPI flash, UEFI GOP in Expansion ROM
- **Motherboard + RAM** — DIMM/SO-DIMM DDR4/DDR5, bus definition, power per slot, DisplayPort/HDMI output
- **Driver** — Linux DRM/KMS, Mesa/Vulkan backend
- **Simulation first** — C++/Python reference model, SystemVerilog, Verilator + GTKWave, before any hardware

## What it does NOT do

- It does **not** replace the base skill. Spec format, hard rules, DRC, BOM, trace-width and fab rules are inherited from the base skill. If the two disagree, the base skill wins on PCB rules.
- It does **not** make an FPGA GPU cheap or fast. A mid-range FPGA fits a 3D pipeline roughly in the class of late-1990s / early-2000s cards, at 200–500 MHz logic. It will not match an RTX 4090.
- It does **not** design custom silicon / ASICs. It designs a board around an existing FPGA.

## Repository structure

```
ai-pc-component-design-skill-addon/
├── SKILL.md            # the addon skill (the whole workflow)
├── README.md           # this file
├── LICENSE             # MIT
└── kit/
    ├── README.md       # kit usage
    ├── config.json     # user-editable thresholds
    ├── require_base.py # finds + verifies the base skill, exit 2 if missing
    ├── pcie_check.py   # PCIe / enumeration checks on an addon spec
    ├── vram_check.py   # VRAM type / bandwidth checks on an addon spec
    ├── run_all.py      # runs require_base + pcie + vram (+ base rules_check)
    └── examples/
        └── spec.json   # sample FPGA GPU addon spec (passes)
```

## Quick start

```bash
# 1. Put the base skill next to this repo (or point at it):
#    ../ai-pcb-design-skill   OR   set AI_PCB_SKILL_PATH
#    OR   python kit/run_all.py --base-skill ../ai-pcb-design-skill

# 2. Run all addon checks on the example
python kit/run_all.py

# 3. Check your own addon spec
python kit/pcie_check.py my-gpu/spec.json
python kit/vram_check.py my-gpu/spec.json
```

All scripts are standard library only — no installation needed.
Windows: use `python` (PowerShell). macOS/Linux: use `python3`.

Exit codes: `0` = pass, `1` = fail, `2` = setup missing (including: base skill missing).

## Works with any AI

Like the base skill, this addon is backend-agnostic: Claude Code,
ChatGPT, a local model, or an API (e.g. NVIDIA NIM). Load the base
`SKILL.md` first, then this `SKILL.md`, and run the kit scripts
locally. If a step needs a tool that does not exist in your
environment, the skill says so and tells you the manual alternative —
it never pretends a check ran when it did not.

## Honest limits

- A skill is a workflow + checklists + review. The model still
  hallucinates footprints and pinouts — that is why every pin, value
  and footprint must be verified against a datasheet, and why the kit
  scripts and a human review are gates, not formalities.
- The FPGA alone, the 8–14 layer PCB, back-drilling and assembly cost
  real money — hundreds to thousands of euros before the first frame.
- Start on a ready-made FPGA dev board at PCIe 3.0 x4, not on a custom
  PCIe 4.0 x16 board. Only when the dev board enumerates, renders and
  runs the driver does the design move to a custom PCB.

## License

MIT — see `LICENSE`.
