# Data

Raw data is **not** committed to this repo. Download it into `data/raw/` (ignored by git).

## CWRU Bearing Data Center (Phase 1)

Source: https://engineering.case.edu/bearingdatacenter

Files used (12 kHz drive-end, 0.007" fault diameter):

| Condition | Load | File | Signal key |
|-----------|------|------|------------|
| Normal | 0 / 1 / 2 / 3 HP | 97 / 98 / 99 / 100 | `X097_DE_time` … |
| Inner race fault | 0 / 1 / 2 / 3 HP | 105 / 106 / 107 / 108 | `X105_DE_time` … |
| Ball fault | 0 / 1 / 2 / 3 HP | 118 / 119 / 120 / 121 | `X118_DE_time` … |
| Outer race fault (6:00) | 0 / 1 / 2 / 3 HP | 130 / 131 / 132 / 133 | `X130_DE_time` … |
| 0.014" faults (inner / ball / outer) | 0 HP | 169 / 185 / 197 | leave-one-severity-out (notebook 06) |
| 0.021" faults (inner / ball / outer) | 0 HP | 209 / 222 / 234 | defect-size shift (notebooks 05, 06) |

Download all of them:

```bash
mkdir -p data/raw && cd data/raw
for n in 97 98 99 100 105 106 107 108 118 119 120 121 130 131 132 133 169 185 197 209 222 234; do
  curl -fLO https://engineering.case.edu/sites/default/files/$n.mat
done
```

Notes:
- Normal baseline files **are** sampled at 48 kHz (verified: read as 48 kHz, their spectral peaks match the 12 kHz fault files). `src/bearing.py` resamples them with `scipy.signal.resample_poly(x, 1, 4)`.
- `99.mat` also contains `X098_*` keys — always build the key from the file number.
- 98 and 99 have no RPM field; nominal 1772 / 1750 rpm is used.
- Shaft speed at 0 HP ≈ 1797 rpm.

## Own data (Phase 3+)

Recorded from the ESP32 + ADXL345 node. Format and labeling notes go here.
