# Firmware (ESP32)

One folder per phase:

| Folder | Phase |
|--------|-------|
| `02-mqtt-raw/` | 2 — read ADXL345, publish raw data over MQTT |
| `03-edge-features/` | 3 — compute features on device |
| `04-tinyml/` | 4 — on-device classifier |
| `05-field-ready/` | 5 — buffering, OTA, deep sleep, TLS |

Credentials: copy `secrets.example.h` to `secrets.h` and fill in your Wi-Fi and MQTT details. `secrets.h` is git-ignored.
