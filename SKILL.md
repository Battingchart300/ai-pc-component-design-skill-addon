---
name: ai-pc-component-design-skill-addon
description: Addon to ai-pcb-design-skill (REQUIRED, v1.2.1+) for designing PC components — FPGA GPU on PCIe 4.0, DDR4/DDR5 VRAM, custom motherboard and RAM. Does NOT work without the base skill. Use when designing a GPU, VRAM, motherboard or high-speed PC component with an AI.
---

# ai-pc-component-design-skill-addon

**Version:** 0.1.0 — 2026-11-24
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
| A1. Requirements | Write the addon spec (§2): PCIe, FPGA, VRAM, power, display. | `kit/pcie_check.py` + `kit/vram_check.py`: 0 errors. Human approves the spec. |
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
    "bus_width_bits": 64, "data_rate_mt_s": 3200
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
| Class Code | **0x030000** — Display Controller, VGA-compatible (0x038000 = 3D controller without its own display output) |
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

- **Linux DRM/KMS driver (best path):** a kernel module in C
  that registers the PCIe device (by Vendor ID / Device ID),
  manages VRAM allocation and sets the monitor resolution.
- **User-space library (Mesa / Vulkan / OpenGL):** in the
  open-source Mesa 3D project, a custom backend can translate
  standard graphics calls from games into instructions for
  your FPGA.
- **Windows first sight:** without a custom driver the card
  shows as "Microsoft Basic Display Adapter" — that is a
  *success* at stage A6, not a failure. It proves enumeration,
  class code and BARs work. The custom driver comes after.

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
| `require_base.py` | Finds `ai-pcb-design-skill` (sibling folder, `AI_PCB_SKILL_PATH`, or `--base-skill`), checks `SKILL.md` exists and version >= 1.2.1. Exit 2 if missing. |
| `pcie_check.py` | Addon spec: PCIe generation/lanes, class code, Vendor/Device ID, BAR0/BAR2, 85 Ω, 100 MHz, Tandem, ReBAR, slot+aux power budget. Calls `require_base.py` first. |
| `vram_check.py` | Addon spec: VRAM type/voltage match, capacity, bus width, data rate, bandwidth calculation, framebuffer demand. Calls `require_base.py` first. |
| `run_all.py` | Runs `require_base.py`, `pcie_check.py`, `vram_check.py`, then the base `rules_check.py` on the base spec if `--spec` is given. Prints an audit log. |

```bash
# from this repo root
python kit/run_all.py
python kit/pcie_check.py kit/examples/spec.json
python kit/vram_check.py kit/examples/spec.json

# point at a base skill in another place
python kit/run_all.py --base-skill ../ai-pcb-design-skill
```

**A skipped check is a gap, not a pass.** If a tool is missing,
the report says so. The model never declares a board correct —
the scripts do, and a human reviews the result.

---

## 12. Honest limits

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

---

## License

MIT — see `LICENSE`. The base skill `ai-pcb-design-skill` stays
a separate repo under its own MIT license. This addon does not
re-license it.
