# ai-pc-component-design-skill-addon

Addon to `ai-pcb-design-skill` for designing PC components — FPGA GPU on PCIe 4.0, DDR4/DDR5 VRAM, custom motherboard and RAM.

**Version:** 0.3.4 — 2026-11-24

## Changelog

### v0.3.4 — 2026-11-24

Codex audit fixes (ChatGPT Codex / GPT-6 audit of v0.3.3):

- **VRAM voltage contradiction is now an error** — the power-rail
  cross-check runs always (a DDR4 rail at 5 V with `vram.voltage_v = 1.2`
  used to PASS).
- **FPGA/memory-type compatibility** — new `fpga_memory_types`
  table in `kit/config.json` (LIFCL-40: DDR3/DDR3L/LPDDR2/LPDDR3
  only; XCKU5P: DDR4/DDR3). LIFCL-40 + DDR4 used to PASS.
- **No more tracebacks on wrong `vram.type`** (list/dict is a clean
  error, exit 1).
- **Missing `kit/config.json`** is now a setup failure (exit 2),
  not a silent fallback to defaults.
- **`lan.phy` must name a PHY chip** — boolean `true` no longer
  passes.
- **Docs math fixed (§12.5):** 8,192 chips ~270 W, ~2.2 kW is the
  whole system.

### v0.3.3 — 2026-11-24

- **JSON root type (P0):** all four check scripts (`pcie_check.py`,
  `vram_check.py`, `lan_check.py`, `storage_check.py`) now reject a
  spec whose JSON root is not an object (e.g. a list) with a clean
  error and exit 2 — they used to crash with a Python traceback.
- **BAR sizes must be powers of two (P1):** `pcie.bar0_mb` and
  `pcie.bar2_mb` must be 1/2/4/8/16 and 256/512/1024/... MB — a size
  like 300 MB used to pass the range check.
- **Power tree is required (P1):** a spec with no `power.rails` is
  now an error, not a warning — a missing power tree cannot be
  checked.
- **VRAM voltage must be confirmed (P1):** `vram.voltage_v` or a
  power rail named after the memory type must state the voltage
  (DDR3 1.5 V, DDR4 1.2 V, DDR5 1.1 V) — an unconfirmed voltage used
  to pass.
- Regression fixtures in `kit/examples/`: `regression_bar2_300.json`,
  `regression_array_root.json`, `regression_no_rails.json`,
  `regression_vram_no_voltage.json`.

### v0.3.2 — 2026-11-24

- **Driver section (§9 rewritten):** the driver ladder
  (enumeration -> custom Linux PCIe driver -> dumb framebuffer ->
  Mesa Gallium3D), what "reworking" a driver really means
  (AMDGPU / i915 / nouveau cannot be pointed at an FPGA; only
  the Linux / DRM framework is reusable), and why a card
  without a rung-4 driver gives zero fps in games (§9.3) —
  plus the PCIe x16 slot requirement (a mini PC has none).
- **MCU-cluster GPU (§12.5, bitluni Supercluster 2 style):**
  one chip per pixel, controller tree (1 per 32 workers), SPI,
  resolution math (320x200 = 64,000 chips), power math
  (~10 mA per chip, 8,192 chips ~270 W, ~2.2 kW whole system), flashing rig,
  raymarching workload, no PCIe / no games. The repo has no
  visible LICENSE — reference only, do not copy its files.
  Plus hardware lessons from the build video: own crystal per
  chip (no shared clock), crosstalk rules, blade splitting,
  respin budget, power as its own project.

### v0.3.1 — 2026-11-24

- **Pi 5 HAT VRAM fixed to DDR3** — LIFCL-40 has no DDR4 (datasheet FPGA-DS-02049: DDR3 max 1066 MT/s). Example is now 1 GB DDR3-1066, 32-bit, ~4.3 GB/s; config lists the DDR3 type max (2133 MT/s) and the LIFCL-40 cap (1066 MT/s).

### v0.3.0 — 2026-11-24

- **Validation hardened** (from Claude AI + ChatGPT reviews of v0.2.0): `require_base.py` now requires an exact frontmatter `name:` match — a misnamed skill no longer passes as the base. `run_all.py` fails (exit 2) if a kit script is missing. Missing spec file / invalid JSON exits 2 in every check.
- **Power limits enforced** — slot max 75 W, 6-pin aux 75 W, 8-pin aux 150 W, USB-C 100 W, no connector = 0 W aux. Vendor/Device ID must be exactly 4 hex digits. Rails must be finite and non-negative; board layers are required. Bad values fail cleanly (exit 1), never with a traceback.
- **VRAM limits enforced** — `vram.voltage_v` checked against the type; data-rate limits per type (DDR4 max 3200, DDR5 max 6400 MT/s) plus the FPGA cap (`fpga.max_ddr_mt_s`, XCKU5P max 2666 MT/s per AMD). Example spec fixed to DDR4-2666 (21.3 GB/s).
- **Class code fixed** — 0x030000 VGA, 0x030200 3D controller, 0x038000 other display controller.
- **Pi 5 HAT lane fix** — the single lane belongs to the FPGA bridge OR NVMe, not both; NVMe removed from the Pi 5 HAT example.
- **Legal section (§18)** — donor schematics/boardview, VBIOS, Vendor ID, EU selling rules (CE/EMC, RoHS, WEEE, RED).
- **CI** — `.github/workflows/ci.yml`: kit checks on both examples, Python 3.9–3.13, misnamed-base negative test.

### v0.2.0 — 2026-11-24

- **Three GPU paths (§12)** — 100% own FPGA/mini-chip system, modern GPU chip on your own PCB (VBIOS lock, donor schematic required), recycled old GPU chip (Voodoo 3 / SM750 / Matrox G200 documented) + mini-chip farm (74HC TTL vs CH32V003 / CH570 / RP2040, bridge + worker array).
- **Raspberry Pi 5 HAT (§13)** — the starter path: PCIe 2.0 x1 (3.0 overclock), FFC, 4–6 layers, ~15–30 € for 5 boards.
- **Storage (§14)** — NVMe M.2 M-key + SATA III, with `kit/storage_check.py` and a Pi 5 HAT example.
- **LAN (§15)** — RJ45 1/2.5 GbE (PHY + magnetics + ESD), with `kit/lan_check.py`.
- **Extra PC I/O (§16)** — USB-C 3.x + hub, M.2 E-key WiFi/BT, RTC + TPM, PWM fan + temperature sensor.
- `pcie_check.py` now accepts gen 2/3 x1 for a Pi 5 HAT.

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
- **VRAM** — DDR4/DDR5 (GDDR6 noted as advanced), MIG controller, bandwidth calculation, Resizable BAR, data-rate limits incl. the FPGA cap (XCKU5P max 2666 MT/s)
- **FPGA GPU core** — command processor, vertex shader, rasterizer, fragment shader, texture unit, ROP, display controller, own shader ISA (fixed-point first)
- **BIOS / UEFI** — Class Code 0x030000, BAR0/BAR2, Tandem PCIe / CvP under 100 ms, QSPI flash, UEFI GOP in Expansion ROM
- **Motherboard + RAM** — DIMM/SO-DIMM DDR4/DDR5, bus definition, power per slot, DisplayPort/HDMI output
- **Driver** — Linux DRM/KMS, Mesa/Vulkan backend
- **Simulation first** — C++/Python reference model, SystemVerilog, Verilator + GTKWave, before any hardware
- **v0.2: three GPU paths** — own FPGA/mini-chip system, modern GPU chip (VBIOS lock), recycled old GPU chip + mini-chip farm
- **v0.2: Pi 5 HAT** — PCIe 2.0 x1 (3.0 overclock), FFC, 4–6 layers, the starter path
- **v0.2: storage + LAN + extra I/O** — NVMe / SATA SSD, RJ45 1/2.5 GbE (PHY + magnetics + ESD), USB-C, M.2 E-key WiFi/BT, RTC + TPM, PWM fan

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
├── .github/workflows/ci.yml # CI: kit checks on both examples, Py 3.9-3.13
└── kit/
    ├── README.md       # kit usage
    ├── config.json     # user-editable thresholds
    ├── require_base.py # finds + verifies the base skill, exit 2 if missing
    ├── pcie_check.py   # PCIe / enumeration checks on an addon spec
    ├── vram_check.py   # VRAM type / bandwidth checks on an addon spec
    ├── storage_check.py # NVMe / SATA checks (v0.2, optional section)
    ├── lan_check.py    # RJ45 LAN checks (v0.2, optional section)
    ├── run_all.py      # runs require_base + pcie + vram + storage + lan (+ base rules_check)
    └── examples/
        ├── spec.json   # sample FPGA GPU addon spec (passes)
        └── spec_pi5_hat.json # sample Pi 5 HAT addon spec (passes)
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

Exit codes: `0` = pass, `1` = fail, `2` = setup missing (including: base skill missing, kit script missing, spec file missing, spec not valid JSON).

## Legal

Short version (SKILL.md §18 has the full text, and it is not legal advice): use only legally obtained donor material — leaked schematics/boardview may be copyrighted or trade secrets. VBIOS is copyrighted, do not distribute it. Vendor ID `0x10EE` is Xilinx's — fine for lab, selling needs your own PCI-SIG ID. Selling in the EU needs CE/EMC, RoHS, WEEE, and RED for WiFi/BT.

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
