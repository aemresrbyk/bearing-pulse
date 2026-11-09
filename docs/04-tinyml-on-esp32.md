# Phase 4 — TinyML on ESP32

**Status:** ⬜ Planned

## Goal

Run the classifier on the device itself and raise an alarm without the laptop doing any ML.

## Steps

### 12. Train a small model
Phase 1 method on the Phase 3 dataset. Keep it small (few trees, shallow depth) so it fits in ESP32 memory.

### 13. Deploy to the ESP32
Convert with `micromlgen` (Random Forest → C code). Alternative: Edge Impulse.
Device publishes `normal` / `fault` + confidence over MQTT → alarm panel in Grafana.

_GIF:_ `images/04-alarm.gif` (tape on blade → alarm fires)

### 14. Robustness test
Change fan speed / voltage / mounting. Does the model still work, or does it fail like in Phase 1 step 5b?

## Results

| Condition | Accuracy | Notes |
|-----------|----------|-------|
| Same as training | | |
| Different speed | | |
| Sensor re-mounted | | |

- Model size / RAM used:
- Inference time:

## What went wrong

_…_

## Next

→ [Phase 5 — Field-ready](05-field-ready.md)
