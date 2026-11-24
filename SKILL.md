---
name: ai-pc-component-design-skill-addon
description: Addon to ai-pcb-design-skill (REQUIRED, v1.2.1+) for designing PC components — FPGA GPU on PCIe 4.0, DDR4/DDR5 VRAM, custom motherboard and RAM, Pi 5 HAT, NVMe/SATA storage and RJ45 LAN. Does NOT work without the base skill. Use when designing a GPU, VRAM, motherboard, Pi 5 HAT, storage or LAN with an AI.
---

# ai-pc-component-design-skill-addon

**Version:** 0.3.4 — 2026-11-24
**What it is:** an addon skill for designing PC components — a custom
FPGA GPU, its VRAM, and a custom motherboard / RAM — on top of
`ai-pcb-design-skill`. It adds only the high-speed, FPGA and
PC-enumeration parts. Everything else (spec, schematic, layout, DRC,
BOM, fab) comes from the base skill.

**Who it is for:** the same user as the base skill — a beginner who
designs boards and lets the AI do the drafting, while the human stays
in charge of every decision that matters — now for a much harder
project: a graphics card.

**How to use it:** load the base skill first, then this file. It works
with any AI backend, like the base skill. If a step needs a tool that
does not exist in your environment (for example `kicad-cli` or
`verilator`), the skill says so and tells you the manual alternative —
it never pretends a check ran when it did not.

---

## 0. Prerequisite — hard stop: this skill does NOT work alone

Read this section first. Nothing below it applies without it.

1. **This addon REQUIRES `ai-pcb-design-skill` v1.2.1 or newer.**
   Before ANY work, load the base `SKILL.md`, confirm its `name` is
   `ai-pcb-design-skill` and its version is >= 1.2.1.
2. **If the base skill is not loaded / not found, STOP.**
   Do not continue, do not guess, do not work from this file alone.
   Say exactly this and wait for the human:
   > `STOP — missing base skill ai-pcb-design-skill v1.2.1+. This addon does not work without it. Load the base skill first.`
3. **The kit enforces the same stop.** `kit/run_all.py`,
   `kit/pcie_check.py` and `kit/vram_check.py` all call
   `kit/require_base.py` first. If the base skill is not found, they
   exit with code `2` (setup missing) and run **no** addon check.
   A missing base is a setup failure, never a pass.
4. **Nothing in this addon replaces the base skill.** The base
   spec format (§2), hard rules (§0), gated workflow (§1), routing
   rules, DRC, BOM, trace-width and fab rules still apply in full.
   This addon only *extends* them. If the two disagree, the base
   skill wins on PCB rules, this addon wins only on PCIe / FPGA /
   VRAM numbers in §3–§9.
5. **A failed base gate stops the addon work too.** If the base
   spec fails `rules_check.py`, or DRC fails, fix the base first.
   Do not proceed to an addon stage on top of a failing base stage.

### 0.1 Hard rules inherited from the base skill

All 10 hard rules of the base skill (§0) apply unchanged, in
particular:

- Never invent a part number, pin, footprint, datasheet value or
  fab limit. If a value cannot be verified, write `UNVERIFIED`
  and cite the file and page where it should be checked.
- When you do not know a value, ASK the user. Never invent a size,
  a voltage, a pin assignment or a part.
- Verify on the web, never from memory. Datasheets and fab limits
  are checked against live sources. Memory is not a source.
- Never disable, filter or loosen a check. A waiver is a human
  decision, written down with a reason.
- The model never decides correctness. The scripts in `kit/` verify
  the design (exit 0 = pass, 1 = fail, 2 = setup missing).
- Never order, upload or publish anything. The order is placed
  only by the human, manually, with human review.
- Never claim a check ran if it did not run.
- Never destroy the user's work. Checkpoint before the first change.
- A failed gate stops the work. Fix the cause, re-run the *same*
  check. If a stage fails 3 times, stop and ask the human.
- The schematic is the design; the layout is only its physical
  implementation.

---

## 1. Gated workflow — addon stages

Work in stages. Each stage ends in a **gate**. The base workflow
(base §1, stages 0–10) still runs underneath; the addon stages run
*inside* it, mostly between base stages 1–4. Editing a board after
a stage passed re-opens the dependent stages.

| Stage | Do | Gate |
|---|---|---|
| A0. Prerequisite | Load base skill, confirm version >= 1.2.1. | `kit/require_base.py` passes. Human confirms base is loaded. |
| A1. Requirements | Write the addon spec (§2): PCIe, FPGA, VRAM, power, display + path (§12), Pi 5 HAT (§13), storage (§14), LAN (§15) if used. | `kit/pcie_check.py` + `kit/vram_check.py` + `kit/storage_check.py` + `kit/lan_check.py`: 0 errors. Human approves the spec. |
| A2. Architecture | Block diagram: FPGA + VRAM + PDN + clocks + display. Pick the FPGA and memory chips from datasheets. | Every active part has MPN + datasheet + footprint. No part without a datasheet. |
| A3. Simulation first | C++/Python reference model, then RTL, then Verilator (§10). | Reference model renders a test triangle. Verilator renders the same frame. |
| A4. Schematic + stackup | Base schematic + 8–14 layer stackup, 85 Ω pairs, sequencing. | Base ERC 0 errors; stackup matches the fab (§3). |
| A5. Layout + checks | Route PCIe/DDR first, then the rest. Run base DRC + addon checks. | `kicad-cli pcb drc`: 0 errors; addon checks 0 errors. |
| A6. Bring-up | Tandem enumeration test, `lspci`, driver load, first frame. | Card appears as VGA controller; display shows a test pattern. Human sign-off. |

**Human review stops:** after the addon spec (A1), after the
architecture (A2), after the simulation renders (A3), and before the
order (base stage 10). **Structural changes need the human:** the
model never changes the FPGA, the PCIe width, the VRAM type or the
layer count without asking.

**Start small, on purpose:** the first working target is PCIe 3.0
x4 or PCIe 4.0 x4 on a ready-made FPGA dev board, not a custom
PCIe 4.0 x16 board. Only when the dev board enumerates, renders and
runs the driver does the design move to a custom PCB.

---

## 2. Spec-first — the addon spec

The addon spec **extends** the base spec (`kit/examples/spec.json`
in the base skill). It never replaces it. A board that uses this
addon has both: a base spec (board, parts, nets) **and** an addon
spec (this section). The kit example is
`kit/examples/spec.json` in this repo.

```json
{
  "board": {"name": "Sample FPGA GPU", "layers": 8, "fab": "jlcpcb"},
  "pcie": {
    "generation": 4, "lanes": 8,
    "class_code": "0x030000",
    "vendor_id": "0x10EE", "device_id": "0x1234",
    "bar0_mb": 16, "bar2_mb": 8192,
    "impedance_ohm": 85, "refclk_mhz": 100,
    "tandem": true, "resizable_bar": true
  },
  "fpga": {"part": "XCKU5P", "family": "Kintex UltraScale+"},
  "vram": {
    "type": "DDR4", "capacity_gb": 8,
    "bus_width_bits": 64, "data_rate_mt_s": 2666
  },
  "power": {
    "slot_w": 75, "aux_w": 150, "aux_connector": "8-pin PCIe",
    "rails": [
      {"rail": "VCCINT", "voltage_v": 0.85, "current_a": 20},
      {"rail": "DDR4", "voltage_v": 1.2, "current_a": 5}
    ]
  },
  "display": {"connector": "DisplayPort", "max_resolution": "1920x1080@60"}
}
```

**Lint the addon spec before drawing anything:**

```bash
python kit/run_all.py
# runs require_base.py, then pcie_check.py, then vram_check.py
# and the base rules_check.py on the base spec, if one is given
```

Errors that stop the work: missing `pcie` / `vram` / `power`
section, wrong class code, BAR2 smaller than the framebuffer the
resolution needs, impedance not 85 Ω, refclk not 100 MHz,
`tandem: false` on PCIe 4.0, a VRAM voltage that does not match
its type (DDR4 must be 1.2 V, DDR5 1.1 V, DDR3 1.5 V), estimated
power over the slot + aux budget.

**Rule: nothing is drawn until the base spec has 0 errors AND the
addon spec has 0 errors.** A warning may stay only with a reason
written in a note on the sheet.

---

## 3. PCIe 4.0 — the numbers that matter

| Item | Skill value |
|---|---|
| Speed per lane | **16 GT/s** (PCIe 4.0). PCIe 3.0 is 8 GT/s — use it for the first build. |
| Differential impedance | **85 Ω** (100 Ω is for other interfaces — do not mix them up). |
| Reference clock | **100 MHz HCSL**, low jitter. PCIe does not work with a sloppy clock. |
| AC coupling | Capacitors on the **TX** side of every lane, per the FPGA / PCIe spec. Value and placement from the datasheet, never guessed. |
| Intra-pair skew | Match the two wires of a pair to a fraction of a millimetre. Inter-pair skew is looser, but still matched per the FPGA guide. |
| Stackup | **8–14 layers.** PCIe and DDR signals run over unbroken GND planes. No routing over a plane split. |
| Vias | Unused via stubs act as antennas at 8 GHz. Use **back-drilling** (the fab drills away the unused stub) where the fab offers it. Minimise vias in a pair. |
| Polarity | PCIe lanes are polarity-swappable in the FPGA/SerDes — confirm `polarity_swappable: yes` in the FPGA datasheet before swapping. Never assume it for other interfaces. |

**Power from the slot:** a PCIe slot gives at most **75 W**
(66 W from 12 V + 9 W from 3.3 V). Over that, the board needs an
external **6-pin (+75 W) or 8-pin (+150 W) PCIe power connector**.
Size the connector from the power tree (§4), not from hope.

---

## 4. Power delivery (PDN) + sequencing

A modern FPGA does not run on 3.3 V and 12 V alone. It needs
**6–10 different rails**, for example:

| Rail | Typical value | Notes |
|---|---|---|
| Core (VCCINT) | **0.72 V or 0.85 V**, 20–50 A | The big one. Size by the FPGA datasheet + utilisation, never by guess. |
| DDR | 1.2 V (DDR4) / 1.1 V (DDR5) | See §5. |
| I/O | 1.8 V | FPGA I/O banks. |
| PLL / transceiver | Ultra-clean, per datasheet | Separate regulator / filtering. A noisy PLL rail kills PCIe. |
| Aux / config | Per FPGA datasheet | Configuration and housekeeping. |

**Power sequencing is mandatory:** the rails must turn on in the
exact order in the FPGA datasheet. Wrong order can destroy the
chip. The sequence is a design item, written in the spec and
checked at bring-up — not an afterthought.

**Rules:** power tree first (base §6.1), one current per branch,
regulator by dissipation (< ~1 W LDO, > ~1 W buck), decoupling
per the FPGA datasheet, a solid GND plane next to every power
plane. QSPI flash (§7) gets its own clean rail.

---

## 5. VRAM — DDR4 / DDR5 / GDDR6

The base skill covers DDR2/DDR3 DIMM/SO-DIMM (base §4.11). This
addon extends it to **DDR4 and DDR5 as VRAM on the GPU board**,
and to GDDR6 as a noted, advanced option.

| Memory | Voltage | Typical bandwidth, 64-bit channel |
|---|---|---|
| DDR4-3200 | 1.2 V | ~25.6 GB/s |
| DDR5-4800 | 1.1 V | ~38.4 GB/s |
| GDDR6 | per datasheet | 500+ GB/s on real cards — needs a GDDR-capable controller / PHY, not a beginner part |

Bandwidth, not capacity, is the bottleneck:

```
bandwidth_GBs = (bus_width_bits / 8) * data_rate_MTs / 1000
# example: 64-bit DDR4-3200 -> 8 * 3200 / 1000 = 25.6 GB/s
```

**The FPGA caps the rate, not just the memory:** the memory
controller inside the FPGA may be slower than the memory chips.
Example: Kintex UltraScale+ XCKU5P runs DDR4 at most **2666 MT/s**
(AMD product page + UG583, mid-speed grade) — a DDR4-3200 spec
on that FPGA is wrong, even though DDR4-3200 memory exists.
Lattice CrossLink-NX LIFCL-40 runs DDR3 at most **1066 MT/s**
(datasheet FPGA-DS-02049: DDR3/DDR3L/LPDDR2/LPDDR3 up to 1066 Mbps
x16) — it does **not** support DDR4 at all, so a DDR4 spec on that
FPGA is wrong; the Pi 5 HAT example uses 1 GB DDR3-1066, 32-bit
(2x 4 Gb chips), ~4.3 GB/s.
`kit/vram_check.py` enforces the cap from `kit/config.json`
(`fpga_max_ddr_mt_s`, with a datasheet source) or from
`fpga.max_ddr_mt_s` in the spec itself (with `max_ddr_source`
citing the datasheet). An FPGA part with no entry anywhere is
**UNVERIFIED** — check its datasheet and add the value before
trusting the design.

**Check with the kit:** `kit/vram_check.py` computes the
bandwidth from the spec and compares it with the framebuffer
demand. At 1920×1080, 60 fps, 32-bit colour, one full frame is
~8.3 MB; writing it 60× per second is ~0.5 GB/s — and real
rendering with overdraw and textures needs several times that.
If the bandwidth is below ~20 GB/s, 1080p with textures is a
warning, not a pass-and-forget.

**Other rules:** use the FPGA memory controller (MIG) for the
chosen memory; the controller, the DIMM/chip datasheet and the
FPGA pinout must agree. **Resizable BAR (ReBAR):** without it
the OS can map only a 256 MB window into VRAM at a time and the
rest is paged (slow). With ReBAR on in the PCIe IP and in the
motherboard BIOS, the whole VRAM maps at once — 16 / 32 / 64 GB
are then mappable. **HBM exception:** AMD Virtex UltraScale+
HBM / Intel Stratix 10 MX have HBM2 inside the package
(8–32 GB, up to ~460 GB/s) — real GPU-class bandwidth, but the
chips cost thousands and are not a first build.

**Clamshell warning:** 32 GB from single DDR4 chips (16× 2 GB)
needs double-sided mounting and very dense routing. Prefer one
wider channel or fewer, larger chips first.

---

## 6. FPGA GPU core — the graphics pipeline

The GPU core is a massively parallel processor built in
SystemVerilog / Verilog (AMD Vivado or Intel Quartus). Blocks, in
order:

1. **Command Processor** — reads commands from the PC (via PCIe
   into VRAM): "load these vertices, use this shader, use this
   texture, draw 10,000 triangles."
2. **Vertex Shader** — 3D coordinates (X, Y, Z) × 4×4 matrix →
   2D screen coordinates. A small SIMD/SIMT unit: the same
   operation on many data at once.
3. **Primitive Assembly & Clipping** — three vertices become one
   triangle; clip what is off-screen; drop back-facing triangles
   (back-face culling).
4. **Rasterizer** — the heart. Takes a 2D triangle, finds which
   pixels are inside it, and computes barycentric coordinates per
   pixel to interpolate colour, depth (Z) and texture coordinates
   (UV) from the corners.
5. **Fragment / Pixel Shader** — runs your own microcode (your own
   ISA) per pixel: texture colour + light + shadow → final colour.
6. **Texture Unit** — fetches the right texel from VRAM by UV,
   bilinear filtering, small local texture cache so it does not
   wait on VRAM every pixel.
7. **ROP (Render Output Unit)** — depth test (Z-buffer: drop a
   pixel hidden behind a closer one), blending (transparent
   objects mix with the framebuffer), writes the final pixel to
   VRAM.
8. **Display Controller** — reads the finished frame from VRAM
   ~60× per second and sends it out through the transceivers to
   the monitor.

**Own shader ISA:** a simple 32-bit RISC set (add, multiply,
dot-product, load, branch). Start with **fixed-point Q16.16**
instead of IEEE-754 FP32 — it uses a fraction of the logic and
is far easier to get right first. FP32 comes later, if ever.

**Size guide (honest):** a mid-range FPGA such as Kintex
UltraScale+ XCKU5P (~475k logic cells) fits a complete 3D
pipeline with a few parallel pixel/vertex units — roughly the
class of late-1990s / early-2000s cards (3dfx Voodoo 3 to
GeForce 2/3), smooth 3D at 720p/1080p with textures and basic
lighting. The largest FPGAs (Virtex UltraScale+ VU19P, Versal
VP1902, 9–18M cells, tens of thousands of euros) fit dozens of
shader cores — and are used by NVIDIA/AMD to prototype future
chips. **Even the largest FPGA runs logic at ~200–500 MHz**
(signals cross programmable switches), while a fixed-silicon
GPU runs at 2,500–3,000 MHz. An FPGA GPU will not match an
RTX 4090, by physics, not by effort.

**Memory bottleneck + fix:** at 1920×1080 @ 60 fps the board
must write > 124M pixels/second (3× with overdraw). Use
**tile-based rendering** (render 32×32-pixel tiles in fast
internal BRAM/UltraRAM, write only the finished tile to VRAM)
plus Z-cache / texture cache — the same idea as mobile GPUs
and NVIDIA Maxwell/Ada.

---

## 7. BIOS / UEFI — how the PC finds the card

The motherboard (UEFI/BIOS) and the OS must see the card as a
graphics card from the first power-on. Three standards must hold:

### 7.1 PCIe Configuration Space

When the PC powers on, the CPU scans every PCIe slot and reads
the first 256 bytes (PCI Configuration Space). Set in the FPGA
PCIe IP block:

| Field | Value |
|---|---|
| Class Code | **0x030000** — Display Controller, VGA-compatible. (0x030200 = 3D controller, 0x038000 = other display controller — not the same thing.) |
| Vendor ID / Device ID | 16-bit each. For dev/test, the FPGA vendor ID (AMD/Xilinx 0x10EE, Intel 0x1172). The OS pairs the driver by these numbers. |
| BAR0 | **1–16 MB** — control registers (commands, resolution, status). |
| BAR2 | **256 MB – 8 GB** — VRAM / framebuffer, directly writable by the CPU. |

Class code alone is enough for `lspci` / Device Manager to see
the card. It is **not** enough for a picture in the BIOS.

### 7.2 Fast start — enumeration under 100 ms

The motherboard does not wait for slow devices. The card must
answer on the bus **within 100 ms of power-on**, or the BIOS
ignores it completely. Large FPGAs load from external flash in
500 ms – 2 s — too slow.

**Fix in firmware:** **Tandem PCIe** (AMD/Xilinx) or **CvP —
Configuration via Protocol** (Intel). The bitstream splits in
two: (1) a small part — only the PCIe interface — loads in
~20 ms and says "I am here, I am a GPU"; (2) the rest of the
graphics core loads in the background while the BIOS tests RAM.

**Also needed:** **QSPI NOR Flash** on the board. The FPGA
forgets its configuration at power-off; at every boot it must
load from this flash, fast enough to meet the 100 ms rule.

### 7.3 UEFI GOP driver in Expansion ROM

For a picture already in the BIOS (board logo, BIOS setup,
Windows install), add an **Expansion ROM** to the PCIe config.
It holds a compiled **UEFI GOP (Graphics Output Protocol)**
driver (a `.efi` file wrapped in a PCI ROM header), stored in
the card's flash.

What it does: the BIOS downloads the code from the card into
RAM and runs it. The code sets a base resolution on the FPGA
(for example 1024×768 or 1920×1080) and hands the BIOS the
physical address of the VRAM BAR. The BIOS then draws pixels
directly into the card's memory. Legacy VGA BIOS is for old
systems with CSM on; on modern PCIe 4.0 boards with CSM off,
UEFI GOP alone is enough.

**Check in practice:** set Class 0x030000 + BAR0 + BAR2,
enable Tandem PCIe, power on. The card should appear as
"Microsoft Basic Display Adapter" (Windows) or "VGA compatible
controller" (Linux). Add the UEFI GOP ROM and it becomes a
primary display adapter that shows the BIOS.

---

## 8. Motherboard + RAM slots — the PC-component side

This addon extends the base custom-motherboard capability
(base §4.10) from a DIY modular computer to PC components:

- **Motherboard:** the board that joins CPU / RAM / GPU /
  storage through a bus, with power and slots/connectors. Design
  items: bus definition (which signals, which connector, pinout
  documented), power distribution (one rail per block,
  decoupling per block, current budget per slot), slots for the
  modules, mechanical fit (modules must fit and be removable).
- **RAM slots:** **DIMM (desktop) and SO-DIMM (laptop)** for
  **DDR4 (1.2 V) and DDR5 (1.1 V)** — the base skill stops at
  DDR2/DDR3; DDR4/DDR5 routing is this addon's scope. DDR
  length matching is a separate step after routing: each byte
  lane tuned to its DQS, DQS/CK pairs first, then address /
  command to CK. Report mismatch in **mm and ps**.
- **Honest limit:** this is a motherboard for your own modular
  computer and for PC components, **not** an x86 motherboard.
  A working DDR board still needs the memory controller's
  datasheet, the DIMM specification, and a human review before
  ordering.
- **Display output:** a physical DisplayPort or HDMI 2.0/2.1
  connector + ESD protection (+ retimer / level-shifter if
  needed — FPGA pins run at 1.2–1.8 V and do not drive HDMI
  voltages directly). Clocking: PCIe needs the 100 MHz HCSL
  clock (§3); memory and display need their own dedicated
  oscillators / PLLs.

---

## 9. Software + driver (PC side)

**The driver is the real project. The board is the easy half.**
A card without a driver is a paperweight that enumerates. Plan
the driver before ordering the PCB — §10 simulation first,
driver second, hardware third.

### 9.1 The ladder — each rung is a separate project

1. **Enumeration (weeks):** the PC sees the card: correct class
   code (0x030000), Vendor/Device ID, BARs map. On Windows it
   shows as "Microsoft Basic Display Adapter" — that is a
   *success* at stage A6, not a failure. It proves enumeration,
   class code and BARs work. No pixels yet.
2. **Custom Linux PCIe driver (months of learning):** a kernel
   module in C: probe by Vendor/Device ID, map BARs, DMA
   transfers, VRAM allocation, interrupts. The Linux PCI core
   and DRM helpers are reused — that part is NOT written from
   scratch.
3. **Dumb framebuffer (the realistic "it shows a picture"
   goal):** a simple DRM driver (`drm_simple_display_pipe`)
   that exposes the VRAM as a framebuffer. Linux shows a desktop
   on your monitor. This is the finish line for a first build.
4. **3D acceleration (years, team-scale — not a first build):**
   OpenGL/Vulkan for games needs a full Mesa Gallium3D driver:
   a shader compiler for YOUR shader ISA, command submission,
   memory management, synchronization. That is the hardest part
   of the whole GPU, harder than the board.

### 9.2 "Prerobiť" an existing driver — what that really means

- **You cannot rework AMDGPU, i915 or nouveau to drive your
  FPGA.** Those drivers are written for one specific chip: its
  registers, its command stream, its shader instruction set.
  Pointing them at different hardware is not an edit, it is a
  rewrite — the hardware backend is new code either way.
- **What CAN be reused:** the Linux PCI core, DRM/KMS helpers,
  GEM memory management, and Mesa's Gallium interface plus
  `softpipe` / `llvmpipe` as reference code for how a driver is
  structured. You reuse the framework, you write the hardware
  part.
- **Windows:** a display driver there means WDDM — no open
  framework to reuse, signing requirements, and no shortcut.
  Linux first, Windows much later if ever.

### 9.3 What this means for games (read before promising fps)

- Without rung 4, **games render on the host GPU, not on your
  card.** The card can only *display* the finished frame.
  Minecraft, or any OpenGL/Vulkan game, will run exactly as fast
  as before — the fps comes from the GPU that renders, not the
  one that displays.
- A PC card also needs a PC with a **PCIe x16 slot**. A mini PC
  (e.g. Intel N95) has no such slot — the card physically does
  not fit. The card belongs in a desktop PC (e.g. the planned
  1st AI PC), not in the mini PC it was meant to speed up.
- Rule: **never promise fps from a card whose rung-4 driver
  does not exist.** A framebuffer is a display, not
  acceleration.

---

## 10. Simulation-first development — no hardware first

Before touching an FPGA or a PCB, the whole chip is designed
on the PC screen:

1. **C++ / Python reference model** — a software simulator of
   your GPU, to prove the rasterizer and shader maths.
2. **RTL code (SystemVerilog)** — rewrite each block in a
   hardware description.
3. **Verilator** — compile the SystemVerilog into a fast C++
   program. On the PC screen you see the real rendered 3D
   image exactly as the future silicon computes it, including
   every single clock tick (waveforms in GTKWave).

Only when the simulation renders correctly does the design go
to a dev board, and only when the dev board works does it go
to a custom PCB. A board ordered before the simulation works
is a respin waiting to happen.

---

## 11. Checks — the kit

The kit is in `kit/`. All scripts are standard library only,
no installation needed. Exit codes: `0` = pass, `1` = fail,
`2` = setup missing (including: base skill missing).

| Script | What it checks |
|---|---|
| `require_base.py` | Finds `ai-pcb-design-skill` (sibling folder, `AI_PCB_SKILL_PATH`, or `--base-skill`), reads the `name:` field from the YAML frontmatter of its `SKILL.md` and requires it to equal exactly `ai-pcb-design-skill`, version >= 1.2.1. Exit 2 if missing, misnamed or old. |
| `pcie_check.py` | Addon spec: PCIe generation/lanes, class code 0x030000, Vendor/Device ID (exactly 4 hex digits), BAR0/BAR2, 85 Ω, 100 MHz, Tandem, ReBAR, slot max 75 W + aux limits (6-pin 75 W, 8-pin 150 W, USB-C 100 W, no connector = 0 W), rails with finite non-negative values, board layers required. Accepts gen 2/3 x1 for a Pi 5 HAT (§13) and gen 3/4 for a PC card. Calls `require_base.py` first. A missing spec file or invalid JSON exits 2, not 1. |
| `vram_check.py` | Addon spec: VRAM type/voltage match (checks `vram.voltage_v` and always cross-checks the power rail
  against the expected voltage for the type; enforces FPGA/memory-type
  compatibility (`fpga_memory_types` in `kit/config.json`)), capacity, bus width, data rate with type limits (DDR3 max 2133, DDR4 max 3200, DDR5 max 6400 MT/s) and the FPGA cap (`fpga.max_ddr_mt_s` from the spec with a datasheet citation, else `kit/config.json` — XCKU5P max 2666 MT/s per AMD, LIFCL-40 max 1066 MT/s per Lattice; other parts UNVERIFIED), bandwidth calculation, framebuffer demand. Calls `require_base.py` first. A missing spec file or invalid JSON exits 2, not 1. |
| `storage_check.py` (v0.2) | Addon spec, optional `storage` section: NVMe (M.2 M-key, PCIe lanes, 3.3 V, boot flag) and SATA (SATA III, 100 Ω pairs, power). Skips with a note if no storage section. Calls `require_base.py` first. |
| `lan_check.py` (v0.2) | Addon spec, optional `lan` section: speed 1/2.5 GbE, PHY present, magnetics present, ESD present. Skips with a note if no LAN section. Calls `require_base.py` first. |
| `run_all.py` | Runs `require_base.py`, `pcie_check.py`, `vram_check.py`, `storage_check.py`, `lan_check.py`, then the base `rules_check.py` on the base spec if `--spec` is given. Prints an audit log. A missing kit script exits 2 with the file named — never a silent PASS. |

```bash
# from this repo root
python kit/run_all.py
python kit/pcie_check.py kit/examples/spec.json
python kit/vram_check.py kit/examples/spec.json
python kit/storage_check.py kit/examples/spec.json
python kit/lan_check.py kit/examples/spec.json
python kit/pcie_check.py kit/examples/spec_pi5_hat.json

# point at a base skill in another place
python kit/run_all.py --base-skill ../ai-pcb-design-skill
```

**A skipped check is a gap, not a pass.** If a tool is missing,
the report says so. The model never declares a board correct —
the scripts do, and a human reviews the result.

---

## 12. Three GPU paths — pick one first (v0.2)

Do not mix the paths in one board. Pick one, write it in the spec,
and design only that path. A board that tries to be all three is a
respin.

### 12.1 Path A — 100% own system: FPGA / mini-chip farm

- **What:** everything is yours — FPGA GPU (§6) and/or a field of
  small chips, own firmware, own driver, from scratch.
- **PCIe:** yes, via the FPGA (§3, §7). **Performance:** retro /
  simple 3D / own compute. **PCB:** high (8–10 layers, DDR4).
- **Use when:** you want to learn and own the whole stack, and
  retro-level 3D is enough.

### 12.2 Path B — modern GPU chip on your own PCB (clone a card)

- **What:** desolder a modern GPU die (AMD RDNA 2/3, NVIDIA RTX
  30/40, Intel Arc) + its GDDR6 from a donor card and put them on
  your own PCB (smaller, better power, water block, extra chips).
- **Firmware lock — hard stop:** modern chips have a hardware root
  of trust. At power-on an internal security processor (AMD PSP,
  NVIDIA Falcon/GSP) verifies the cryptographic signature of the
  firmware (VBIOS). **You cannot write your own firmware for the
  chip, or edit its base code — the chip refuses it and stays
  dead.** Use the original VBIOS exactly from the donor card.
  Use official drivers (or open Linux drivers: `amdgpu` / `xe` /
  `nouveau`). The internal registers are secret and the driver is
  millions of lines — do not try to rewrite it.
- **What you need:** the donor card + its complete schematic /
  boardview (`.pdf` + `.brd`). AMD RX 6600 / 6700 XT / 7600 and
  older NVIDIA RTX 20/30 are the most practical — leaked
  schematics exist in repair forums. **Without the schematic you
  have no chance:** a modern GPU has 1,500–2,500 balls under it
  and the pinout is never published.
- **PCB difficulty — extreme:** 10–14 layers, GDDR6 at 14–20 Gbps,
  PCIe 4.0 at 16 GT/s, trace lengths matched to tenths of a
  millimetre, VRM delivering **100–300 A at under 1 V**.
- **Combination:** add a PCIe 4.0 switch (ASMedia / Microchip) on
  the same board: PCIe 4.0 x8 to the modern GPU, PCIe 4.0 x4 to
  your own mini-chip field, for which you *do* write your own
  firmware and driver. That is the highest difficulty in this
  skill.

| Path | Own firmware + driver | PCIe 4.0 | Graphics | PCB difficulty |
|---|---|---|---|---|
| Modern GPU chip | No (original VBIOS + drivers) | Yes (native) | Modern AAA games | Extreme (12+ layers, GDDR6, 200 A VRM) |
| Own FPGA + mini chips | Yes, 100% | Yes (via FPGA) | Retro / simple 3D | High (8–10 layers, DDR4) |
| Combination (modern GPU + mini chips via switch) | Yes (for your part) | Yes (via switch) | Modern games + own coprocessor | Highest (needs donor schematic) |

### 12.3 Path C — recycled old GPU chip

- **What:** desolder an old GPU die and put it on your own board
  with your mini-chip field, on PCIe 4.0 via a switch/bridge.
- **Hard problems:** (1) **Secret pinouts** — NVIDIA/AMD/Intel
  never publish which of the 1,500+ balls is power, VRAM data or
  PCIe. Without a leaked schematic/boardview for that exact card,
  the chip cannot be wired. (2) **Old PCIe generations** — old
  chips are PCIe 1.0/2.0/3.0 only. For PCIe 4.0 you need an
  expensive PCIe switch/bridge (Broadcom/PLX, ASMedia) that
  translates PCIe 4.0 to the older standard. (3) **Closed
  firmware** — chips from ~2014 on have a security coprocessor
  (PSP/SMU) that verifies the VBIOS signature. Change the board
  or load a modified firmware and the chip blocks and never
  starts.
- **Two workable routes:**
  - **Route A — PCIe switch + two branches:** one PCIe 4.0
    switch (Microchip / ASMedia, buyable with documentation
    after NDA or via distributors) splits the link: one branch
    to an older but documented graphics chip (e.g. Radeon HD
    6000/7000, pre-2013 — lots of open documentation from Linux
    drivers and leaked laptop schematics) for classic 3D +
    monitor output; the other branch to your mini-chip field
    (e.g. dozens of CH32V / RP2350) as your own parallel
    compute coprocessor (physics / AI card on the same PCB).
  - **Route B — old chip with public documentation (easiest to
    bring up):** 3dfx Voodoo 3 / Voodoo 4 (VSA-100) — the
    community has fully mapped the wiring and people build
    modern PCBs with these chips today; or industrial chips
    Silicon Motion SM750 / SM768, Matrox G200 — full register
    and pin documentation is available.
- **Recycling steps:** (1) get the exact chip + schematic /
  boardview; desolder with hot air / BGA rework station, clean,
  reball; (2) copy the power (VRM) and VRAM wiring from the donor
  exactly; (3) add the PCIe 4.0 switch so the board talks PCIe
  4.0 and serves both the old GPU and your mini-chip field.

### 12.4 Mini-chip farm — the worker array (v0.2)

Two different worlds, do not confuse them:

- **74-series TTL logic (e.g. Michael Kamprath):** classic logic
  gates 74HC / 74ACT (74HC00 NAND, 74HC283 adder, 74HC574
  register). Each tiny chip does one elementary thing. Beautiful
  retro card for slow 8-bit computers (a few MHz). **Physically
  incompatible with PCIe 4.0 (16 GHz)** — such a board would be
  room-sized and the signal would fall apart.
- **Field of small MCUs (e.g. Bitluni):** dozens of tiny 32-bit
  RISC-V chips on small boards. Each chip is one "shader core"
  (computes one pixel / one row in parallel with the others).

**Hybrid (two-level) architecture — the only way to PCIe 4.0:**

1. **Main bridge:** one chip at the PCIe edge with PCIe 4.0
   (small FPGA: Artix UltraScale+ or Lattice Avant-E, or a
   PCIe-to-parallel/SPI bridge). It talks to the motherboard
   over PCIe 4.0, presents as a graphics card (Class Code
   0x030000), and holds the VRAM.
2. **Worker field:** the rest of the board is covered with
   dozens / hundreds of cheap legged chips. The bridge sends
   them data (triangles / textures) over fast parallel buses
   or dozens of SPI lines; the small chips compute in parallel
   and send finished pixels back; the bridge sends them to the
   monitor.

**Cheap worker chips (DIY community, v0.2):**

| Chip | Price | Package | Notes |
|---|---|---|---|
| WCH CH32V003 / CH32V006 | ~0.10–0.15 € | SOIC-8 / SOP-16 / TSSOP-20 | 48 MHz RISC-V, 2–8 KB RAM, 16–64 KB Flash. Ideal as a mass field of simple pixel shaders. |
| WCH CH570D / CH571 (the chip in the Bitluni photo) | ~0.25 € | — | 100 MHz RISC-V, more RAM (12 KB), faster I/O. |
| Raspberry Pi RP2040 / RP2350 | ~0.70–1.00 € | QFN | 2 cores (133–150 MHz), PIO (Programmable I/O) — receives data from the bridge fast without loading the CPU, can even generate HDMI/DVI directly. |

**PCB rule for the farm:** one bridge + a grid of 32 / 64 workers.
Route data from the bridge as a bus / star, not as chaos: one
shared parallel bus or grouped SPI lines, short traces, one
power rail per group with decoupling per chip (base §4.6).
The farm is a coprocessor, not a replacement for the bridge —
without the bridge there is no PCIe.

### 12.5 MCU-cluster GPU — one chip per pixel (bitluni Supercluster 2 style)

Reference build: bitluni, "I made a GPU at home" (YouTube),
designs + code: github.com/bitluni/Supercluster2. No LICENSE file
was visible in that repo (checked 2026-11-24) — treat it as
reference only. Do not copy its files; your board is your own
work from the architecture described here.

**The idea — no FPGA, no PCIe:** each tiny RISC-V
microcontroller IS one pixel. It computes its own pixel colour
(raymarching / patterns) and drives its own RGB LED. The display
IS the array of chips + LEDs. This is a standalone sculpture /
raymarcher, not a PC graphics card — there is no PCIe link and
no monitor output.

**Reference numbers (Supercluster 2 prototype):**

- Workers: 8,192x WCH CH570 (32-bit RISC-V, up to 100 MHz,
  ~12 KB memory, hardware multiplier, ~$0.13 each in bulk).
- Controllers: 256x larger controller chips (CH32V208 class),
  each manages 32 workers.
- Comms: SPI buses, 32 workers share one bus; controllers
  coordinate; the host talks to controllers, never to workers
  directly.
- Boards: modular blades, each a grid of worker chips + RGB
  LEDs (one board = 16x32 pixel block), plugged into a central
  backplane (circular, Cray-1-inspired).
- Resolution math: pixels = chips. 320x200 needs 64,000 chips
  (~$8,000 just for the MCUs); Full HD would need 2M+ chips.
  One chip per pixel does not scale to HD.
- Power: ~10 mA per worker at 3.3 V — the 8,192 workers alone
  draw ~270 W (~82 A). The whole 8,192-chip prototype draws
  ~2,161 W (~655 A at 3.3 V, workers + controllers + LEDs +
  converters) — a 3 kW ATX PSU + custom
  12 V -> 3.3 V buck converters. Power is the first wall, not
  logic.
- Programming: flashing thousands of chips by hand takes weeks.
  Bitluni modified a 3D printer with pogo pins on the gantry +
  Python scripts to flash each board. Budget a flashing rig,
  not just a programmer.
- Workload: distributed raymarching, synchronized LED patterns.
  No OpenGL, no Vulkan, no games. See §9.3.

**Design rules for a cluster GPU in this skill:**

- Resolution first: pick the resolution, then the chip count,
  then the power budget — in that order. Never the other way
  round.
- Power budget: I_total = N_workers x ~10 mA (+ controllers).
  Size the 3.3 V rail and the 12 V -> 3.3 V converters for that
  current with margin; hundreds of amps need bus bars / thick
  copper, not traces.
- Controller tree: 1 controller per ~32 workers, one SPI bus
  per group.
- Start small: one blade (e.g. 16x32 = 512 pixels) proves the
  architecture, the SPI tree, the power and the flashing rig
  before any bigger array.
- Video output is the LED array itself. If you want a real
  monitor signal, that is a separate project — a controller
  that collects pixels and drives VGA/HDMI (see §13 for the
  Pi 5 HAT path instead).
- Cost check before ordering: N_workers x unit price +
  controllers + LEDs + blades + PSU. The chips are the cheap
  part.

**Hardware lessons from the build (half a year of work):**

- **No shared clock:** one clock signal for thousands of chips
  collapses under electrical loading. Every worker gets its own
  crystal oscillator.
- **Crosstalk is real at this density:** 6-layer boards with
  ground planes on the inner layers, traces staggered so signals
  on adjacent levels do not bleed into each other.
- **The fab has limits too:** one giant board was too complex
  for the manufacturer's ordering system — it had to be split
  into modular blades (32 rows of 32 chips each), each blade
  split into two pieces and assembled separately. Design in
  blades from the start, not as a rescue.
- **First boards will have defects:** defective / intermittent
  chips, traces that need relocating, MOSI and MISO crossed
  ("no matter how hard you try, you will get rx and tx wrong
  on the first try" — bitluni). Budget a respin and a bring-up
  plan per blade, not per array.
- **Power is its own project:** 3 kW ATX PSU + high-efficiency
  buck converters (Murata) for 650+ A at 3.3 V. Cooling: fans
  in v1, immersion cooling was planned but not used.
- **Files status:** bitluni planned to publish all design files
  as open source with the next part; a v2 targeting ~32,000
  chips was already in development. Check the repo before
  assuming the files are out.

---

## 13. Raspberry Pi 5 HAT — the starter path (v0.2)

**Start here.** The Pi 5 HAT is the best and simplest place to
begin a custom GPU / compute-field board.

- **Link:** Raspberry Pi 5 exposes **PCIe 2.0 x1** on its side
  (unofficially overclockable in the OS to **PCIe 3.0 x1**).
  Not PCIe 4.0 — but for developing your own GPU card or
  mini-chip field it is a huge advantage.
- **Connection — cheap:** no expensive gold PCIe edge connector.
  A plain **16-pin 0.5 mm FFC connector** (a few cents) on your
  HAT + a short flat cable to the Pi 5 is enough.
- **PCB — easy:** one lane (x1) at PCIe 2.0 (5 GT/s) or 3.0
  (8 GT/s) needs **no 12 layers and no back-drilling**. A
  **4-layer or 6-layer PCB in free KiCad** is enough. 5 boards
  from JLCPCB cost ~15–30 €.
- **OS + driver — open:** Raspberry Pi OS (Linux) gives direct
  kernel access. Compile your own Linux PCIe / DRM driver in C
  and test data transfer immediately, without risking an
  expensive PC motherboard.
- **Power:** power the HAT from the Pi 5 via the 40-pin GPIO
  header + PCIe FFC, or add your own USB-C power input on the
  HAT if you fit dozens of small chips.
- **What fits on the HAT:** one small cheap PCIe-to-parallel /
  SPI bridge (e.g. Lattice CrossLink-NX or Gowin GW2A with
  PCIe 2.0) + a grid of 16 / 32 / 64 × CH32V003 / CH570 /
  RP2350 as an external graphics or AI accelerator; or your own
  2D/3D chip with HDMI output. People already run real AMD cards
  on a Pi 5 (RX 460 / 580 / 6600, open `amdgpu` drivers) via an
  FFC-to-PCIe-x16 adapter — the same path works for your own chip.
- **Limit vs PC:** one lane only — ~500 MB/s (PCIe 2.0) to
  ~900 MB/s (PCIe 3.0), vs PCIe 4.0 x16 at ~32,000 MB/s on a PC.
  For prototyping your architecture, writing your own driver
  and rendering 720p/1080p, that is plenty.
- **VRAM is DDR3, not DDR4:** the CrossLink-NX bridge (LIFCL-40)
  supports DDR3/DDR3L/LPDDR2/LPDDR3 only, up to 1066 MT/s — no
  DDR4 (datasheet FPGA-DS-02049). The example uses 1 GB DDR3-1066,
  32-bit (2x 4 Gb chips), ~4.3 GB/s.
- **Spec for a Pi 5 HAT:** see `kit/examples/spec_pi5_hat.json`
  — PCIe generation 2 (or 3 if overclocked), lanes 1, FFC
  connector, 4 layers, bridge FPGA + 32 workers. `pcie_check.py`
  accepts generation 2/3 with lanes 1 for a Pi 5 HAT (see §11).
- **One lane, one user:** the Pi 5 has exactly ONE PCIe lane.
  It belongs to the FPGA bridge OR to an NVMe SSD — not both at
  once. The example spec has no NVMe section for that reason.
  If you want both, add a PCIe switch (see §12.2) and write the
  lane budget in the spec; a lane used twice is a short in the
  plan, not a saving (see also §14).

---

## 14. Storage — NVMe / SATA SSD (v0.2)

Storage is a PC component on the same board, not an afterthought.
The base skill already covers M.2 NVMe via PCIe on a CM5 carrier
(base §4.7); this addon adds it as a first-class PC-component
option.

| Option | Interface | Speed | Connector |
|---|---|---|---|
| NVMe SSD | PCIe (M.2 M-key, x1 / x2 / x4) | PCIe 3.0 x4 ~3.5 GB/s, PCIe 4.0 x4 ~7 GB/s | M.2 2230 / 2242 / 2280, M-key |
| SATA SSD / HDD | SATA III (AHCI) | 6 Gb/s (~550 MB/s) | SATA data (7-pin) + SATA power (15-pin) |

**Rules:**
- **NVMe:** differential pairs 85 Ω (§3), short traces, 3.3 V
  power (check the SSD's power draw — some need 5–8 W), M.2
  screw / standoff at the right length (2280 = 80 mm). Boot
  from NVMe must be supported by the host BIOS / firmware —
  verify before ordering, do not assume it.
- **SATA:** SATA data pairs are 100 Ω differential, length
  matched, ESD on the connector. SATA power needs 5 V + 12 V
  (HDD) or 5 V only (most SATA SSDs) — check the drive's label.
  AHCI controller in the host / FPGA, or a SATA controller chip
  with a datasheet.
- **Do not share lanes silently:** an M.2 slot that takes PCIe
  lanes takes them from the GPU / switch budget (§3, §12.2).
  Write the lane budget in the spec: total lanes in = GPU lanes
  + NVMe lanes + other lanes. A lane used twice is a short in
  the plan, not a saving.
- **Check:** `kit/storage_check.py` validates the storage
  section (type, lanes, connector, power, boot flag).

---

## 15. LAN — RJ45 Ethernet (v0.2)

An RJ45 connector alone is not a network port. A working LAN
port needs a PHY + magnetics + protection.

| Speed | PHY / controller | Notes |
|---|---|---|
| 1 GbE | 1 GbE PHY (e.g. Realtek / Microchip, per datasheet) | Most common, easiest. |
| 2.5 GbE | 2.5 GbE PHY | Needs a 2.5 GbE-capable PHY + magnetics rated for it. |
| 10 GbE | 10 GbE PHY / SFP+ | Advanced — not a first build. |

**Rules:**
- **Chain:** MAC (in host / FPGA / SoC) → PHY chip → magnetics
  (transformer, usually inside the RJ45 jack or as a separate
  part) → RJ45 jack → cable. Never connect a MAC directly to
  an RJ45 jack without magnetics + PHY.
- **Magnetics:** use a jack with integrated magnetics, or a
  discrete magnetics part matched to the PHY datasheet. The
  PHY datasheet names the exact magnetics — follow it.
- **Pairs:** TX/RX differential pairs 100 Ω, length matched,
  short, over a solid GND plane, away from switching regulators
  and PCIe pairs.
- **Protection:** ESD diodes on the jack side, close to the
  connector. LEDs (link / activity) per the PHY datasheet.
- **PoE (optional):** Power over Ethernet needs a PoE PD
  controller + isolation — do not add it by wiring 48 V to the
  jack. If PoE is wanted, it is its own spec item with its own
  datasheet.
- **Check:** `kit/lan_check.py` validates the LAN section
  (speed, PHY present, magnetics present, ESD present).

---

## 16. Extra PC I/O — USB-C, WiFi, RTC/TPM, cooling (v0.2)

Small items that make a PC component usable, each with its own
datasheet — never a guessed part.

- **USB-C 3.x + USB hub:** USB-C connector with CC resistors
  (5.1 kΩ pull-downs for a sink, base §4.2), ESD on D+/D−,
  90 Ω pairs for USB 2.0 / 3.x. A hub chip needs its datasheet
  + crystal + power. USB-C power delivery (PD) is its own
  controller — do not improvise it.
- **WiFi / Bluetooth — M.2 E-key:** an M.2 E-key slot (PCIe x1
  + USB 2.0) for a WiFi/BT module, with antenna connectors
  (I-PEX / u.FL) + keep-out under the antenna. The module's
  datasheet + the host driver must agree; a module without a
  Linux driver is a dead slot.
- **RTC + TPM:** RTC battery (CR2032 holder, correct polarity,
  no charging a non-rechargeable cell) + crystal per the RTC
  datasheet; TPM header (or onboard TPM chip) per the host
  datasheet — a TPM footprint without a matching header pinout
  is useless.
- **Cooling — PWM fan + temperature sensor:** 4-pin PWM fan
  header (PWM + tach), temperature sensor (I²C) near the FPGA /
  GPU / VRM, fan curve in firmware. A fan without a tach wire
  cannot report a stall; a sensor far from the hot part measures
  the wrong temperature.

---

## 17. Honest limits

- A skill is a workflow + checklists + review. It does not make
  an FPGA GPU cheap, fast or easy. The FPGA alone, the 8–14 layer
  PCB, back-drilling and assembly cost real money — hundreds to
  thousands of euros before the first frame.
- An FPGA GPU will not match a commercial GPU. See §6: 200–500 MHz
  logic, DDR bandwidth 20–50 GB/s per channel vs GDDR6/7 at
  500–1000+ GB/s on real cards, unless HBM FPGAs are used.
- The model cannot click wires in EasyEDA / Vivado. Layout goes
  through the tool the user uses — or the user finishes it with
  the mouse. The skill never claims a board is routed when it is
  not.
- DRC 0/0 does not mean manufacturable. The base DFM gate and
  the visual check exist for exactly that reason.
- This addon does not design custom silicon / ASICs. It designs
  a board around an existing FPGA, it does not design the chip
  itself.
- A modern GPU chip (Path B, §12.2) cannot run your own firmware.
  The VBIOS signature lock is hardware, not a setting to turn off.
  Without the donor schematic the chip cannot be wired at all.
- A card without a rung-4 Mesa driver does not accelerate games
  — it only displays what the host GPU rendered. See §9.3.
- A chip-per-pixel GPU needs one chip per pixel — 320x200 is
  64,000 chips and ~2 kW. It is a showpiece / raymarcher, not
  a PC card. See §12.5.
- A Pi 5 HAT (§13) is a starter, not a PC card: one PCIe lane,
  ~500–900 MB/s. It proves the architecture and the driver; it
  does not prove a PCIe 4.0 x16 board.
- NVMe / SATA / LAN (§14–§15) need their own controller, PHY
  and driver. A connector without the chip behind it is an
  empty slot.

---

## 18. Legal — read this first (not legal advice)

I am not a lawyer. This section is a short list of risks, not
legal advice — when in doubt, ask a real lawyer or do not do it.

- **Donor schematics / boardview from forums:** leaked
  schematics and boardview files may be copyrighted or trade
  secrets. Use only legally obtained material: official
  reference designs, public documentation, and your own
  measurements of your own card.
- **VBIOS:** the VBIOS of a donor card is copyrighted firmware.
  Use it only on your own card for your own lab use. Do not
  copy it, share it or distribute it.
- **Vendor ID:** `0x10EE` belongs to AMD/Xilinx. Using it in a
  lab prototype is fine. Selling a board needs your own Vendor
  ID from PCI-SIG.
- **Selling in the EU:** a board sold in the EU needs CE/EMC,
  RoHS, WEEE, and RED if it has WiFi/BT. This skill does not
  cover certification — budget for it before selling anything.

---

## Changelog

### v0.3.4 — 2026-11-24

Codex audit fixes (ChatGPT Codex / GPT-6 audit of v0.3.3 — 160 tests):

- **VRAM voltage contradiction is now an error:** the power-rail
  cross-check runs always, not only when `vram.voltage_v` is absent
  — a DDR4 rail at 5 V with `vram.voltage_v = 1.2` used to PASS.
- **FPGA/memory-type compatibility:** new `fpga_memory_types` table
  in `kit/config.json` (LIFCL-40: DDR3/DDR3L/LPDDR2/LPDDR3 only,
  XCKU5P: DDR4/DDR3) — a type the FPGA does not support is an error
  (LIFCL-40 + DDR4 used to PASS).
- **No more tracebacks on wrong types:** `vram.type` given as a list
  or dict is a clean error (exit 1), not a Python traceback.
- **Missing `kit/config.json` is a setup failure:** exit 2 with a
  clear error — the scripts used to fall back to built-in defaults
  silently.
- **`lan.phy` must name a PHY chip:** a boolean `true` used to pass;
  now it must be a non-empty string (a part name).
- **Docs math fixed (§12.5):** 8,192 chips at ~10 mA × 3.3 V is
  ~270 W for the chips alone; ~2.2 kW is the whole prototype system
  (controllers, LEDs, converters, fans).

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

- **Pi 5 HAT VRAM fixed to DDR3:** the LIFCL-40 bridge does **not**
  support DDR4 (datasheet FPGA-DS-02049: DDR3/DDR3L/LPDDR2/LPDDR3
  up to 1066 Mbps x16). The Pi 5 HAT example was wrongly DDR4-1600;
  it is now 1 GB DDR3-1066, 32-bit (2x 4 Gb chips), ~4.3 GB/s, with
  the DDR3 rail at 1.5 V. `kit/config.json` now lists the DDR3 type
  max (2133 MT/s) and the LIFCL-40 FPGA cap (1066 MT/s), and §5 /
  §13 say so. The XCKU5P example stays DDR4-2666 — that FPGA does
  support DDR4.

### v0.3.0 — 2026-11-24

- **Validation hardened (reviews of v0.2.0):** `require_base.py`
  now reads the `name:` field from the base `SKILL.md` YAML
  frontmatter and requires an exact match — a misnamed skill
  (including this addon itself) no longer passes as the base.
  `run_all.py` fails (exit 2) if a kit script is missing,
  instead of silently passing. Missing spec file / invalid JSON
  exits 2 in every check script.
- **Power limits enforced:** slot max 75 W, 6-pin aux 75 W,
  8-pin aux 150 W, USB-C 100 W, no connector = 0 W aux.
  Vendor/Device ID must be exactly 4 hex digits (`0xZZZZ`
  fails). Rails must have finite non-negative values; board
  layers are required. Bad values fail cleanly (exit 1), never
  with a Python traceback.
- **VRAM limits enforced:** `vram.voltage_v` is now checked
  against the type (DDR4 1.2 V, DDR5 1.1 V, DDR3 1.5 V); data
  rate limits per type (DDR4 max 3200, DDR5 max 6400 MT/s) plus
  the FPGA cap (`fpga.max_ddr_mt_s`, XCKU5P max 2666 MT/s per
  AMD — other parts UNVERIFIED). Example spec fixed to
  DDR4-2666 (21.3 GB/s).
- **Class code fixed (§7.1):** 0x030000 VGA, 0x030200 3D
  controller, 0x038000 other display controller (was wrong).
- **Pi 5 HAT lane fix (§13):** the single lane belongs to the
  FPGA bridge OR NVMe, not both — NVMe removed from the Pi 5
  HAT example.
- **Legal section (§18)** and CI (`.github/workflows/ci.yml`):
  kit checks on both examples, Python 3.9–3.13, plus a
  misnamed-base negative test.

### v0.2.0 — 2026-11-24

- Three GPU paths (§12), Pi 5 HAT (§13), storage (§14), LAN
  (§15), extra PC I/O (§16).

---

## License

MIT — see `LICENSE`. The base skill `ai-pcb-design-skill` stays
a separate repo under its own MIT license. This addon does not
re-license it.
