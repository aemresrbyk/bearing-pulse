# Phase 5 — Field-ready

**Status:** ⬜ Planned

## Goal

Turn the demo into something that would survive outside the desk: lost Wi-Fi, remote updates, battery, security.

## Steps

### 15. Survive connection loss
Buffer readings in memory (or flash) when Wi-Fi/MQTT is down; send them when the link returns. Test by turning the router off.

### 16. OTA updates and deep sleep
- Update firmware over Wi-Fi without a USB cable
- Deep sleep between measurements; measure current draw and estimate battery life

### 17. Security
MQTT with TLS and username/password. No open broker.

## Results

- Data lost during a 5-minute outage:
- Current draw (active / sleep):
- Estimated battery life:

## What went wrong

_…_

## Next

→ [Phase 6 — Custom PCB](06-custom-pcb.md)
