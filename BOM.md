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
| Soldering iron, solder, flux | 1 set | | Already bought for Phase 2 (see above) |

## What I already had

_List here what was already on the bench before starting._
