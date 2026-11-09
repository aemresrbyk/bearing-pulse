# Phase 1 — ML on CWRU bearing data

**Status:** ⬜ Planned · **Time:** ~7–9 h · **Hardware:** none

## Goal

Classify bearing condition (normal / inner race / outer race / ball fault) from vibration signals, using classic signal processing plus a simple ML model — and then show where the model breaks.

## You need

- Python 3.10+, packages in [`requirements.txt`](../requirements.txt)
- CWRU data files → see [`data/README.md`](../data/README.md)

## Steps

### 0. Setup (15 min)
Virtual environment, install packages, `git init`.

### 1. Understand the physics (30 min)
Bearing fault frequencies and why each fault shows up at a different one:
- **BPFO** — outer race
- **BPFI** — inner race
- **BSF** — ball spin
- Shaft speed ≈ 1797 rpm at 0 HP

_Write the formulas and the values you computed here._

### 2. Load and plot the data (1 h)
`scipy.io.loadmat`, `..._DE_time` signal, plot the first 0.1 s of each condition.
⚠️ Normal data may be 48 kHz — resample to 12 kHz.

_Plot:_ `images/01-raw-signals.png`

### 3. FFT and envelope spectrum (1.5 h)
Plain FFT → band-pass filter → `scipy.signal.hilbert` envelope → FFT of the envelope.
Mark the expected fault frequencies on the plot.

_Plot:_ `images/01-envelope-spectrum.png`

### 4. Feature extraction (1 h)
2048-sample windows. Features: RMS, peak, crest factor, kurtosis, band energies.

### 5. Classification (1 h)
Random Forest + confusion matrix.
Split **by time inside each recording** (first 70 % train, last 30 % test). A random split leaks neighbouring windows into the test set and inflates accuracy.

_Plot:_ `images/01-confusion-matrix.png`

### 5b. When is the model wrong? (~1 h)
Train on 0 HP, test on 1–3 HP (a change in operating conditions, i.e. distribution shift).
- How much does accuracy drop?
- On wrong predictions, is the model still confident (`predict_proba`)?

This is the most important result of the phase.

### 6. Write-up (1 h)
Update this page and the main README with plots and numbers.

## Results

| Test | Accuracy | Notes |
|------|----------|-------|
| 0 HP → 0 HP (time split) | | |
| 0 HP → 1 HP | | |
| 0 HP → 2 HP | | |
| 0 HP → 3 HP | | |

## Limitations

_What the model can't do, and why it matters for a real machine._

## What went wrong

_Honest notes: bugs, wrong assumptions, things that took longer than expected._

## Next

→ [Phase 2 — Sensor node + MQTT](02-sensor-node-mqtt.md)
