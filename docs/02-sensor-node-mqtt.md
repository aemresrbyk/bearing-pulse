# Phase 2 — Sensor node + MQTT

**Status:** ⬜ Planned · **Hardware:** ESP32, ADXL345, fan/motor, breadboard

## Goal

Build my own vibration sensor node and stream live data to a dashboard on my laptop.

```
ADXL345 → ESP32 → Wi-Fi → MQTT broker (Mosquitto) → InfluxDB → Grafana
```

## You need

- Parts from [BOM.md](../BOM.md) (Phase 2–5 section)
- Arduino IDE or PlatformIO with ESP32 support
- Mosquitto, InfluxDB, Grafana on the laptop (Docker is the easiest way)

## Steps

### 7. Wire the sensor
ADXL345 ↔ ESP32 over SPI (or I2C to start). Mount the sensor firmly on the fan/motor housing.
Read raw X/Y/Z acceleration over serial.

_Wiring diagram:_ `hardware/02-wiring.png`
_Photo:_ `images/02-setup.jpg`

### 8. Send over MQTT
ESP32 connects to Wi-Fi and publishes to the broker.
Topic layout, e.g. `bearingpulse/node1/raw`.
Keep Wi-Fi and MQTT credentials in `firmware/secrets.h` (git-ignored).

### 9. Store and visualise
MQTT → InfluxDB → Grafana live panel.

_Screenshot:_ `images/02-grafana.png`

## Results

- Sample rate reached:
- Message rate / latency:

## What went wrong

_…_

## Next

→ [Phase 3 — Edge features](03-edge-features.md)
