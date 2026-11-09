# Data

Raw data is **not** committed to this repo. Download it into `data/raw/` (ignored by git).

## CWRU Bearing Data Center (Phase 1)

Source: https://engineering.case.edu/bearingdatacenter

Files used (12 kHz drive-end, 0.007" fault diameter):

| Condition | Load | File | Signal key |
|-----------|------|------|------------|
| Normal | 0 HP | | `X..._DE_time` |
| Inner race fault | 0 HP | | `X..._DE_time` |
| Ball fault | 0 HP | | `X..._DE_time` |
| Outer race fault (6:00) | 0 HP | | `X..._DE_time` |
| Same four conditions | 1–3 HP | | used in step 5b (load-change test) |

Notes:
- Normal baseline files may be sampled at 48 kHz — resample to 12 kHz with `scipy.signal.resample_poly` before mixing with fault data.
- Shaft speed at 0 HP ≈ 1797 rpm.

## Own data (Phase 3+)

Recorded from the ESP32 + ADXL345 node. Format and labeling notes go here.
