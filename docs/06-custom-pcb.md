# Phase 6 — Custom board

**Status:** ⬜ Planned · **Tools:** KiCad, soldering iron

## Goal

Replace the breadboard with one solid board: ESP32 + connector to the ADXL345 + power.
The PCB is **designed** in KiCad to a manufacturable standard; the physical board is **hand-soldered on
perfboard** from the same schematic. Ordering a fabricated PCB is optional and not planned (shipping and
import costs outweigh the benefit for a single prototype).

## Steps

### 18. Design in KiCad
Schematic → footprint assignment → layout → DRC (design rule check) → 3D render → Gerber export.
Files go in `hardware/pcb/`. The Gerbers are what a fab would need, so the design is order-ready.

_Screenshots:_ `images/06-schematic.png`, `images/06-layout.png`, `images/06-3d.png`

### 19. Build on perfboard and test
Same schematic, hand-wired on perfboard. The ESP32 sits on female headers so it can be removed.
The ADXL345 stays bolted to the fan and connects with a short cable, so the board itself doesn't
add its own vibration to the measurement. Flash the Phase 2–5 firmware and compare readings with the
breadboard version.

_Photo:_ `images/06-board.jpg`

## Results

- Cost of the perfboard build:
- Did it work first time?

## What went wrong

_…_

## Done 🎉

← Back to the [main README](../README.md)
