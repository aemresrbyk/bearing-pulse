# Bill of Materials

Prices are rough estimates. Update with what you actually paid.

## Phase 1 — software only

Nothing to buy. Any laptop with Python 3.10+ is enough (no GPU needed).

## Phase 2–5 — sensor node

| Part | Qty | Used in | Approx. price | Notes |
|------|-----|---------|---------------|-------|
| ESP32 DevKit (ESP32-WROOM-32) | 1 | 2–5 | 469.90 TL | Robotistan ESP-32S, 30 pin. Wi-Fi is required from Phase 2 on |
| ADXL345 accelerometer module | 1 | 2–5 | 199.90 TL | Robotistan GY-291. Headers come unsoldered. Use SPI for higher sample rates |
| Small 12 V fan or DC motor | 1 | 2–4 | 212.00 TL | XMER 80×80×25 mm, 12 V 0.30 A, 2 wires. The "machine" under test |
| 12 V adapter (for fan/motor) | 1 | 2–4 | 152.10 TL | Weiron 12 V 2 A, 5.5×2.5 mm plug. Plug cut off and soldered to the fan wires (barrel-jack terminals are 2.1 mm and would sit loose) |
| Soldering iron set | 1 | 2, 6 | 908.99 TL | Wellhise S90, temperature-controlled. Needed for the ADXL345 headers and the Phase 6 board |
| Breadboard | 1 | 2 | — | Already had |
| Jumper wires (M-M, F-F, M-F) | 1 set | 2 | — | Already had |
| USB-C to micro-USB data cable | 1 | 2 | — | Already had. ESP32 board is micro-USB; cable must carry data, not only charge |
| Small cable ties (2.5×100 mm) | 100 | 2 | 98.20 TL | Sensor tied through its holes to the fan frame. Rigid on purpose: foam tape would damp the vibration we measure |
| Electrical tape | 1 | 3–4 | 89.90 TL | 3M Temflex. Small weight taped to a fan blade = imbalance fault |
| Heat-shrink tubing set | 1 | 2 | 218.18 TL | Insulates the adapter-to-fan solder joints |
| Wire stripper / cutter | 1 | 2 | — | Already had. Cuts the adapter plug, strips the wires |
| Multimeter | 1 | 2 | — | Already had. Checks adapter polarity before soldering |
| *Optional:* MPU6050 | 1 | 2 | | Backup sensor, noisier than ADXL345 |
| *Optional:* 18650 cell + TP4056 charger | 1 | 5 | | Battery / deep-sleep tests |

## Phase 6 — custom board (designed in KiCad, built on perfboard)

| Part | Qty | Approx. price | Notes |
|------|-----|---------------|-------|
| Perfboard 7×9 cm, FR4, double-sided, plated holes | 2 | 135.50 TL each | One spare. 2.54 mm pitch |
| Female pin headers 1×40, 2.54 mm | 4 strips | 185.50 TL | Cut to 2×15 (ESP32 plugs in, removable) + 1×8 (sensor cable) |
| Hook-up wire | — | — | Already had: cut jumper wires. Point-to-point wiring on the back |
| Soldering iron, solder | 1 set | — | Already bought for Phase 2 (see above) |
| *Not planned:* fabricated PCB (e.g. JLCPCB) | — | | Design is order-ready (Gerbers in `hardware/pcb/`), but not ordered |

## What I already had

_List here what was already on the bench before starting._
