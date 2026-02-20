# Manic Miner: Sprint Edition

A mod of Matthew Smith's classic **Manic Miner** (1983) for the ZX Spectrum, adding modern platformer mechanics while keeping the original level design and feel.

## Features

- **Sprint mode** — Hold number keys 1-5, Sinclair joystick (key 9), or Kempston joystick UP to run faster
- **Slide continuation** — Momentum carries Willy forward after releasing sprint
- **Air control** — Influence your direction mid-jump; sprint jumps have stronger momentum
- **Variable jump height** — Release jump early for a shorter hop (Mario-style)
- **Extended fall distance** — Survive longer falls (18 vs original 12 threshold)
- **Forgiving collision** — Only Willy's middle cells trigger enemy kills, not the corners
- **Regenerating crumbling tiles** — Crumbled floors regenerate after ~10 seconds
- **2x faster air drain** — Time pressure is doubled
- **Infinite lives** — Death restarts the cavern; no game over
- **Sinclair Joystick 1 support** — Keys 6/7/9/0 for left/right/sprint/jump
- **Kempston joystick support**

## For Players

Apply the included IPS patch to your own copy of `MANIC.TAP`:

1. Get a TAP dump of the original Manic Miner (Software Projects release)
2. Verify your TAP matches this SHA-256:
   ```
   0229ca09bb87c58024d68b05a6a5ecd8ac93fb4932d937883722467f86277f4e
   ```
3. Apply `mm_sprint.ips` using any IPS patcher ([Lunar IPS](https://www.romhacking.net/utilities/240/), [Floating IPS](https://www.romhacking.net/utilities/1040/), etc.)
4. Load the patched TAP in your favourite ZX Spectrum emulator

## For Modders

### Requirements

- [pasmo](https://pasmo.speccy.org/) — Z80 cross-assembler
- Python 3

### Building

1. Place your own `MANIC.TAP` in this directory (the build script verifies its SHA-256)
2. Assemble and package:
   ```bash
   pasmo --bin mm_modbase.asm mm_sprint.bin mm_sprint.sym
   python3 build_tap.py
   ```
3. This produces:
   - `mm_sprint.tap` — ready to load in an emulator
   - `mm_sprint.ips` — updated IPS patch

The build script extracts the original's screen attribute loading block so the animated loading screen is preserved.

## Controls

| Action | Keyboard | Sinclair Joystick 1 | Kempston Joystick |
|--------|----------|---------------------|-------------------|
| Left | Q-P row / A-L row | 6 | Left |
| Right | Q-P row / A-L row | 7 | Right |
| Jump | Z-M row | 0 | Fire |
| Sprint | 1-5 or 9 | 9 | Up |

## Credits

- **Manic Miner** by Matthew Smith, published by Bug-Byte Software (1983) and Software Projects
- Disassembly reference from the [Skoolkit Manic Miner project](https://skoolkit.ca/disassemblies/manic_miner/)
- Mod by sharopolis
