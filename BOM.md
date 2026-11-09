# Bill of Materials

Prices are rough estimates. Update with what you actually paid.

## Phase 1 — software only

Nothing to buy. Any laptop with Python 3.10+ is enough (no GPU needed).

## Phase 2–5 — sensor node

| Part | Qty | Used in | Approx. price | Notes |
|------|-----|---------|---------------|-------|
| ESP32 DevKit (ESP32-WROOM-32) | 1 | 2–5 | | Wi-Fi is required from Phase 2 on |
| ADXL345 accelerometer module | 1 | 2–5 | | Use SPI for higher sample rates |
| Small 12 V fan or DC motor | 1 | 2–4 | | The "machine" under test |
| 12 V adapter (for fan/motor) | 1 | 2–4 | | |
| Breadboard | 1 | 2 | | |
| Jumper wires (M-M, M-F) | 1 set | 2 | | |
| Micro-USB / USB-C data cable | 1 | 2 | | Must support data, not only charging |
| Tape / small weight | — | 3–4 | | Stuck on a fan blade to create imbalance |
| *Optional:* MPU6050 | 1 | 2 | | Backup sensor, noisier than ADXL345 |
| *Optional:* 18650 cell + TP4056 charger | 1 | 5 | | Battery / deep-sleep tests |

## Phase 6 — custom PCB

| Part | Qty | Approx. price | Notes |
|------|-----|---------------|-------|
| PCB order (e.g. JLCPCB, 5 boards) | 1 | | Plus shipping |
| Components for the board | — | | Generated from KiCad BOM |
| Soldering iron, solder, flux | 1 set | | Skip if you already have one |

## What I already had

_List here what was already on the bench before starting._
