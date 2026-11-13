# Bearing Pulse

**End-to-end vibration fault detection — from a public dataset to my own sensor node, edge ML and custom PCB.**

A small, at-home version of an industrial predictive maintenance system (the kind used to monitor wind turbines and other rotating machines). Every phase is documented as a step-by-step build log, including what went wrong.

> 🚧 Work in progress. Phase 1 is done; hardware phases are published as they are finished.

---

## Why

Rotating machines fail slowly: bearings wear, rotors go out of balance. Vibration shows this long before a breakdown. This project walks the full chain an industrial monitoring system needs:

**sensor → microcontroller → network → database → dashboard → ML model → alarm**

…and also asks the question most demos skip: **when does the model get it wrong?**

## Phases

| # | Phase | What it covers | Status |
|---|-------|----------------|--------|
| 1 | [ML on CWRU bearing data](docs/01-ml-on-cwru-data.md) | FFT, envelope spectrum, features, Random Forest, failure under load change | ✅ Done |
| 2 | [Sensor node + MQTT](docs/02-sensor-node-mqtt.md) | ESP32 + ADXL345, MQTT, InfluxDB, Grafana live dashboard | ⬜ Planned |
| 3 | [Edge features](docs/03-edge-features.md) | RMS / kurtosis / FFT bands computed on the ESP32, own labeled dataset | ⬜ Planned |
| 4 | [TinyML on ESP32](docs/04-tinyml-on-esp32.md) | Model running on the device, alarm in Grafana, robustness test | ⬜ Planned |
| 5 | [Field-ready](docs/05-field-ready.md) | Offline buffering, OTA updates, deep sleep, TLS | ⬜ Planned |
| 6 | [Custom PCB](docs/06-custom-pcb.md) | KiCad board for ESP32 + sensor, ordered and assembled | ⬜ Planned |

Status: ⬜ Planned · 🟨 In progress · ✅ Done

## Repository layout

```
bearing-pulse/
├── README.md        ← you are here
├── BOM.md           ← bill of materials, prices, where to buy
├── docs/            ← one build guide per phase
├── src/bearing.py   ← Phase 1 code: loading, fault frequencies, envelope, features
├── notebooks/       ← Phase 1 Jupyter notebooks (use src/bearing.py)
├── firmware/        ← ESP32 code, one folder per phase
├── hardware/        ← wiring diagrams, KiCad files
├── data/            ← dataset download notes (raw data is not committed)
└── images/          ← photos, plots, GIFs used in the docs
```

## Hardware (short version)

ESP32 DevKit · ADXL345 accelerometer · small 12 V fan or DC motor · breadboard and jumpers.
Full list with prices: [BOM.md](BOM.md)

## Quick start (Phase 1)

```bash
git clone https://github.com/aemresrbyk/bearing-pulse.git
cd bearing-pulse
python3.12 -m venv .venv          # 3.10–3.12; newest Python may lack scipy wheels
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/bearing.py            # self-check, prints "ok"
jupyter notebook notebooks/
```

Dataset download steps: [data/README.md](data/README.md)

## Results

### Phase 1 — CWRU bearing data ([full write-up](docs/01-ml-on-cwru-data.md))

**How:** drive-end vibration, 12 kHz → 2048-sample windows → 17 features (time-domain stats, FFT band energies, envelope amplitude at the bearing fault frequencies) → Random Forest. Train/test split by time inside each recording, so neighbouring windows never leak into the test set.

**Why envelope analysis:** a bearing defect makes a short impact every time a ball passes it. The impacts ring the housing at kHz resonances, so a plain FFT hides the fault frequency. Band-pass (2–5 kHz) → Hilbert envelope → FFT recovers the impact rate, which matches the frequency computed from bearing geometry:

![envelope spectrum](images/01-envelope-spectrum.png)

| Test | Accuracy | Notes |
|------|----------|-------|
| 0 HP, time split | **100 %** | Easy, known result for CWRU 0.007" — not the interesting part |
| Train 0 HP → test 1 / 2 / 3 HP | 100 / 100 / 100 % | Confidence drops 0.97 → 0.83 as the load moves away from training |
| Train 0.007" → test 0.021" defects | **56.5 %** | Every larger inner race fault classified as "ball". Wrong predictions all had confidence < 0.5 |

**What I learned:** the model generalises across load but not across defect size — it learned the spectral fingerprint of one fault severity, not the physics. Its confidence was the warning sign every time, so a deployed system should report confidence and flag low-confidence windows instead of showing a bare label.

Two data traps worth knowing: the CWRU **normal recordings are 48 kHz** while the fault recordings are 12 kHz (verified from matching spectral peaks), and **`99.mat` also contains file 98's signal keys**.

## Author

**Ali Emre Sarıbıyık** — Electrical & Electronics Engineer (Yaşar University). Signal processing, applied ML, embedded systems.

## License

Code: [MIT](LICENSE) · Docs and images: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Acknowledgements

Bearing data: [Case Western Reserve University Bearing Data Center](https://engineering.case.edu/bearingdatacenter).
