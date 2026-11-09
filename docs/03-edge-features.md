# Phase 3 — Edge features

**Status:** ⬜ Planned

## Goal

Stop sending raw data. Compute features on the ESP32 and send only those — this is how real field devices save bandwidth and battery.

## Steps

### 10. Features on the ESP32
Same features as Phase 1: RMS, kurtosis, crest factor, FFT band energies.
Compare ESP32 output against the Python implementation on the same recording.

### 11. Build my own labeled dataset
- **Normal:** fan running as-is
- **Fault (imbalance):** tape or a small weight on one blade
- Optional: different speeds / supply voltages

Record, label, save under `data/own/` (format documented in [`data/README.md`](../data/README.md)).

## Results

- Bandwidth: raw vs. features only
- Python vs. ESP32 feature mismatch:

## What went wrong

_…_

## Next

→ [Phase 4 — TinyML on ESP32](04-tinyml-on-esp32.md)
