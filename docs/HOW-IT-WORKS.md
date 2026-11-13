# How Bearing Pulse works, end to end

This document explains the project without assuming you can read the code: **what was built, why it
was built that way, and which file it lives in**. Read it in order; each section builds on the one
before. Interview-style questions and answers are at the end.

---

## 0. The big picture

```
 Bearing vibrates ──► accelerometer (ADXL345) ──► ESP32 ──MQTT──► Mosquitto ──► bridge ──► InfluxDB ──► Grafana
                       3200 samples per second      │               (post       (translator) (time-series  (charts +
                                                    │                office)                  database)     alert)
                                         extract features + model
                                         "normal / inner / ball / outer"
```

- **Bearing:** the ball bearing that carries a rotating shaft. When it fails the machine stops, so
  catching it early saves money. Werover does the same thing for wind turbines at a larger scale.
- **Idea:** a damaged bearing vibrates differently. Measure the vibration and teach a computer to tell
  normal from faulty.
- **No hardware yet.** A **simulator** (`sim/node_sim.py`) stands in for the ESP32: it sends real lab
  recordings (CWRU) exactly as the ESP32 will. When the hardware arrives, the simulator is swapped for
  the ESP32 and everything else stays the same.

Phases:

| Phase | What | Status |
|-------|------|--------|
| 1 | Machine learning on a public dataset | Done |
| 2 | Sensor → MQTT → database → Grafana | Software done (with the simulator), hardware pending |
| 3 | Features computed on the device | C code done and tested, own dataset needs hardware |
| 4 | Model on the device + alert | C model and Grafana alert done, running it on the device needs hardware |
| 5 | Field-ready: security, connection loss, OTA, sleep | TLS + password done, the rest needs hardware |
| 6 | Custom board: PCB designed in KiCad, built on perfboard (not ordered) | Not started |

---

## 1. Phase 1: fault detection on public data

Files: `src/bearing.py` (all functions), `notebooks/01…06` (step-by-step experiments),
`docs/01-ml-on-cwru-data.md` (long write-up).

### 1.1 Data: CWRU

Case Western Reserve University seeded small defects into a motor bearing (0.007", 0.014", 0.021" in
diameter, made by electro-discharge machining) and recorded the vibration. Four conditions:
**normal, inner race, ball, outer race**, each recorded at four loads (0, 1, 2, 3 horsepower).

In `bearing.py`:
- `FILES = {97: ("normal", 0), ...}`: which file number is which condition and load. A dictionary:
  the key is the file number, the value is (condition, load).
- `load(num)`: opens one `.mat` file and returns the vibration signal and shaft speed (rpm). It fixes
  two **data traps**, both good stories for an interview:
  1. **Normal recordings are 48 kHz, fault recordings are 12 kHz.** Normal files contain 4× more samples
     per second. Left unfixed, the model would recognise "normal" by its sample rate, not its vibration:
     a cheat. `signal.resample_poly(x, 1, 4)` brings normal files down to 12 kHz. How was it found?
     The spectral peaks only line up with the fault files when the normal files are read as 48 kHz.
  2. **`99.mat` also contains file 98's signal.** So the key must match the file number:
     `m[f"X{num:03d}_DE_time"]`.

### 1.2 Physics: fault frequencies

Each time a ball rolls over a crack in the inner race it makes a small "click". How many clicks per
second can be **computed from the bearing geometry and shaft speed**. `fault_freqs(rpm)` does that:

- `BPFO`: ball pass frequency, outer race
- `BPFI`: ball pass frequency, inner race
- `BSF`: ball spin frequency (for ball defects)
- `FTF`: cage frequency

At 1797 rpm, BPFO ≈ 107 Hz: an outer race defect clicks about 107 times a second.
The `assert`s at the bottom of the file check that these formulas reproduce the multiples CWRU
publishes. The code tests itself.

### 1.3 Why envelope analysis?

The clicks are very short and make the bearing housing **ring at thousands of Hz** (like a bell).
A plain FFT (frequency analysis) shows nothing at 107 Hz; the energy is in the 2-5 kHz ringing.
The fix is three steps (`envelope_spectrum`):

1. **Band-pass filter (2-5 kHz):** keep only the ringing. `signal.butter(4, ...)` is a 4th-order
   Butterworth filter; `sosfiltfilt` runs it forward and backward so the signal isn't shifted in time.
2. **Hilbert envelope:** take the "envelope" (outline) of the ringing. It rises at every click.
   `np.abs(signal.hilbert(...))`.
3. **FFT of the envelope:** how many times per second does the envelope rise? Exactly the fault frequency.

Result in `images/01-envelope-spectrum.png`: the peaks sit right on the computed BPFO/BPFI.

### 1.4 Features

A machine learning model doesn't take the raw signal but numbers that summarise it. `features()`
computes 17 numbers for every **window** of 2048 samples (≈0.17 s):

| Feature | What it tells |
|---------|---------------|
| `rms` | Average vibration power ("how much is it shaking") |
| `peak` | Largest single impact |
| `crest` = peak / rms | Impulsive? High for a damaged bearing because of sharp peaks |
| `kurtosis` | Peakedness. 0 for plain noise, high for impacts |
| `skewness`, `std` | Asymmetry, spread |
| `band0..band7` | Split the spectrum into 8 parts, share of energy in each (log scale) |
| `env_BPFO`, `env_BPFI`, `env_2BSF` | Envelope spectrum height exactly at the fault frequencies |

Why 2×BSF? A damaged ball hits **both** races once per spin.

### 1.5 Model: Random Forest

**Random Forest** = many **decision trees**. Each tree asks questions like "is rms above 0.05? → yes →
is kurtosis above 3? → …" and reaches an answer; the trees vote and the majority wins. Why this model?
It works well with little data, it's explainable and, most importantly for Phase 4, **it can be turned
into if/else code and embedded on the ESP32**.

**Watch out for data leakage:** the first 70 % of every recording is training, the last 30 % is test.
With a random split, neighbouring (almost identical) windows would land in both sets and the model
would score high by memorising. That is called **data leakage**.

### 1.6 Results and the real lesson

| Test | 17 features | 3 envelope features only |
|------|-------------|--------------------------|
| Same load, time split | 100 % | 100 % |
| Train 0 HP → test 1/2/3 HP | 100 % | 100 % |
| Train on 0.007" → test on 0.021" defects | 59.3 % | **97.7 %** |

**The story:** everything looked like 100 %. Tested on a bigger defect, it dropped to 59 %. Why? The
model had memorised the *shape* of the spectrum, and that shape changes with defect size. The envelope
features depend on **physics** (geometry + shaft speed), not on defect size. Using only them gave
97.7 %. The feature set was chosen with a separate validation, not by looking at the test score
(that would be cheating again).

**Limitations (README → Limitations):** 0.014" defects stay at ~37 % with every method, because the fault
signature isn't in those recordings. No model can learn what isn't there. Also, the **confidence score**
(`predict_proba`) is a useful warning: confidence drops before the model starts making mistakes.

---

## 2. Phases 2-4: adapting to a real sensor

### 2.1 The big problem: our sensor is slow

The ADXL345 takes **at most 3200** samples per second. The highest frequency a signal can show is half
the sample rate (Nyquist): **1600 Hz**. Phase 1's key 2-5 kHz band is **invisible**, so the envelope
features can't be used. Knowing and saying this is a plus in an interview.

The solution: cheap features. File: `src/edge.py`.

- `FS = 3200`, `WINDOW = 1024`: a window is 1024 samples = 0.32 s ≈ 9.6 shaft revolutions (enough
  revolutions to see a pattern). 1024 = 2¹⁰ because the FFT is fastest on powers of two. 1024 floats =
  4 kB, which fits in the ESP32's memory.
- `adxl345(x12k)`: turns a CWRU recording into **what an ADXL345 would have measured**. This is how we
  get realistic data without hardware:
  1. `resample_poly(x, 4, 15)`: 12000 × 4 / 15 = 3200 Hz. Filters first, then decimates (decimating
     without a filter turns high frequencies into fake low ones: *aliasing*).
  2. `np.clip(x, -16, 16)`: the sensor can't measure beyond ±16 g.
  3. `round(x / 0.0039) * 0.0039`: the sensor measures in 3.9 mg steps.
- `features(w)`: 12 features: `rms, peak, crest, kurtosis` + `band0..band7`.
  - `kurt = m4 / m2**2 - 3`: the definition of kurtosis (fourth moment / variance squared). The `-3`
    makes Gaussian noise 0 ("excess kurtosis").
  - `np.hanning`: softens the window edges before the FFT. Otherwise the hard cut at the window edges
    creates fake frequencies (*spectral leakage*).
  - `spec[1:]`: drops 0 Hz (DC). It only holds gravity and sensor offset, no fault information.
  - `reshape(8, -1).sum(1)`: 512 frequency bins → 8 bands of 64 bins. Each bin is 3.125 Hz, each band 200 Hz.
  - `log10(bands / bands.sum())`: the **share** of energy, on a log scale. A share is used because if
    the sensor is mounted a bit looser or tighter the total power changes but the distribution doesn't.

### 2.2 The same code in C for the ESP32

The ESP32 can't run Python; it runs C/C++. `firmware/lib/bearing_edge/`:

- `bearing_edge.h`: the "contract". Declares two functions: `be_features` (1024 samples → 12 numbers)
  and `be_predict` (12 numbers → class + probabilities). The `extern "C"` lines let Arduino's C++
  compiler use it too.
- `features.c`: a line-by-line C version of `edge.features()`. Key decisions:
  - `static float re[N], im[N];`: 8 kB of working memory. `static` puts it in permanent memory instead
    of the task stack; the ESP32 task stack is small and the device crashes if it overflows.
  - Sums in `double`: adding up the squares of 1024 numbers in `float` loses precision.
  - `fft()`: a classic radix-2 FFT written by hand, without a library. It first reorders the samples
    ("bit reversal"), then combines them in "butterfly" steps. No dependencies, so it compiles unchanged
    on both the ESP32 and the laptop.
- `model.c`: **not written by hand, generated** (below).

### 2.3 Training the model and exporting it to C: `src/train_edge.py`

- `N_TREES, MAX_DEPTH = 10, 6`: a small forest. 10 trees, each at most 6 questions deep → ~14.5 kB of
  C source. Fits easily on the ESP32.
- `dataset(loads)`: passes the CWRU recordings through `adxl345()`, cuts them into windows, extracts features.
- **Honest accuracy (leave-one-load-out):** leave one load out entirely, train on the other three, test
  on the one left out; repeat four times.

  | Load left out | Accuracy |
  |---|---|
  | 0 HP | 75.9 % |
  | 1 HP | 75.8 % |
  | 2 HP | 100 % |
  | 3 HP | 81.6 % |
  | **Mean** | **83.3 %** |

  Lower than Phase 1's 100 % because the fault signature is weak at 3200 Hz. Expected and explainable.
- `tree_to_c()`: turns each sklearn tree into nested `if (feat[9] <= -1.03) { ... } else { ... }` code.
  At a leaf it adds the class distribution of the training samples that ended there to `prob[]`.
- `export()`: writes the 10 trees + `be_predict` into `model.c`. `be_predict` calls every tree, divides
  the probabilities by 10 (the mean) and returns the most likely class.
- Why our own exporter instead of a tool like `micromlgen`? 40 lines, no dependency, and we know and can
  test exactly what it generates.

### 2.4 Are the three copies the same? `tests/test_edge.py`

The same computation exists three times: Python (for training), C (for the device), and that C compiled
on the laptop (for testing; `edge.lib()` compiles it with `cc` and calls it from Python via `ctypes`).
Tests:

1. `test_features`: do Python and C give the same features for every class and load? Largest
   difference 0.00002 (kurtosis, from float rounding).
2. `test_model`: does the C model give the same probabilities as sklearn? Difference < 0.0000001,
   labels 100 % identical.
3. `test_end_to_end`: raw signal → C features → C model, the exact path the ESP32 runs. 100 % "outer"
   on the outer race recording.

Run: `python tests/test_edge.py` → prints `ok` at the end.

### 2.5 The data path: MQTT → InfluxDB → Grafana

**MQTT** = lightweight messaging for devices. A device publishes to a "topic"; anyone interested
subscribes to it. **Mosquitto** is the program that runs this post office (the broker).

Topic layout: `bearingpulse/<node>/<kind>`, e.g. `bearingpulse/node1/model`. Three kinds of message:

| Kind | Content | When |
|---|---|---|
| `raw` | Raw samples (packets of 256) | Phase 2: send everything |
| `features` | 12 features | Phase 3: the device summarises, far less data |
| `model` | 12 features + `label` + `confidence` | Phase 4: the device decides |

**`sim/node_sim.py`**: the fake node. Passes a CWRU recording through `adxl345()` and sends it to MQTT
in real time (paced with `time.sleep`). `--cycle` goes normal → inner → ball → outer. It adds `truth`
(the right answer) to each message; only the simulator has it, so Grafana can show "what the model said"
next to "what it really was".

**`bridge/mqtt_to_influx.py`** (the bridge): listens to MQTT and writes messages to the database.
- `to_lines()`: converts a JSON message into InfluxDB's "line protocol":
  `model,node=node1,truth=inner rms=0.12,...,label="inner",fault=1.0 1794577285000000000`
  (measurement, tags, fields, nanosecond timestamp).
- The `fault` field: the model label is text (`"inner"`); a Grafana alert needs a number. Fault = 1,
  normal = 0.
- **Batched writes:** writing every message on its own can't keep up (each write waits ~0.5 s), so
  messages collect in the `pending` list and `flush_forever()` writes them all at once every second.
- `lock`: MQTT runs in one thread, writing in another; they must not touch the same list at the same time.
- Error handling: a malformed message doesn't kill the bridge (it's skipped); if the database is down
  the batch is put back and retried. No data is lost.
- Subscribing inside `on_connect`: if the connection drops, the subscription is renewed automatically
  on reconnect.

**InfluxDB 3**: a time-series database, built for "this value at this moment" data.

**Grafana** (`grafana/`): dashboard and alert. Thanks to the `provisioning/` folder the setup isn't
clicked together by hand but loaded from files, so the dashboard comes with the repo. It shows: what
the device says, its confidence, prediction vs truth, raw vibration, RMS/kurtosis, band energies.

**`scripts/stack.sh`**: starts/stops everything with one command (`start` / `stop`). Starts each program
in the background, saves its process ID (PID) in `.local/pids/` (needed to stop it), waits until
InfluxDB is ready (`/health`), then starts the bridge. All data and logs live in `.local/`, which is
not committed.

---

## 3. Phase 5: field-ready (software part)

### 3.1 Security: TLS + password

In the field the sensor will talk over Wi-Fi. Without protection anyone on the network could read the
data or send a fake "all normal" message. Two locks:

- **TLS** (the padlock in HTTPS): the connection is encrypted and the device verifies that the server
  really is ours.
- **Username + password:** the broker only accepts devices it knows.

`scripts/make_certs.sh`:
- Sets up our own small **certificate authority (CA)** (`ca.crt`). For a public website, organisations
  like Let's Encrypt do this; for a closed system your own CA is enough and common.
- Creates a broker certificate signed by that CA. The `SAN` line says which addresses it is valid for
  (localhost, 127.0.0.1, optionally the laptop's network IP, which the ESP32 will connect to).
- If `.env` doesn't exist, generates a random password (`openssl rand -hex 16`) and stores it **hashed**
  with `mosquitto_passwd` (not as plain text).
- Everything lives in `.local/` and `.env`, both in `.gitignore`. **The password never goes to GitHub.**

`services/mosquitto.conf`: two doors.
- `1883`, `127.0.0.1` only: only programs on this laptop (the bridge) can use it, no password.
- `8883`, whole network: for devices coming from outside. TLS + password required (`allow_anonymous false`).
- `per_listener_settings true`: each door has its own rules.

The simulator with `--tls` connects exactly like the ESP32 (8883, verifies the broker with the CA,
password from `.env`). Tested: right password → data arrived; wrong password and no password →
`not authorised`, rejected.

### 3.2 Alert: `grafana/provisioning/alerting/rules.yml`

"Alert when more than half of a node's predictions in the last minute are faults, for 30 seconds."

- **A:** per node, the mean of `fault` over the last 60 s (0.8 = 80 % of windows said fault).
- **B:** take the last value. **C:** is it above 0.5?
- `for: 30s`: the condition must hold for 30 seconds.
- Averaging + waiting means **one wrong prediction doesn't fire the alert**. In the field, false alarms
  teach people to ignore alarms.
- `noDataState: OK`: no data at all doesn't count as a "fault"; a node going offline is a different problem.

Tested: inner race data → alert fired; normal data → it cleared.

### 3.3 Not done yet (waiting for hardware)

- **The ESP32 main program:** connect to Wi-Fi, read the ADXL345, call `be_features` + `be_predict`,
  publish over TLS MQTT. The library is ready; the program that uses it is written with the hardware.
- **Connection loss (15):** keep results in memory while Wi-Fi is down, send them when it's back.
- **OTA (16):** update the device over the air. **Deep sleep:** sleep between measurements to save battery.
- **Own data (11), own model (12), robustness test (14):** with the fan.

---

## 4. Run it yourself

```bash
cd ~/Desktop/projects/bearing-pulse
source .venv/bin/activate
python src/bearing.py                                   # Phase 1 self-check → ok
python tests/test_edge.py                               # C == Python tests → ok
scripts/stack.sh start                                  # start the stack
python sim/node_sim.py --mode model --cycle --tls       # fake sensor (Ctrl+C to stop)
```

Open http://localhost:3000 → "Bearing Pulse" dashboard. When done: `scripts/stack.sh stop`.

---

## 5. Questions you may be asked

**"Why envelope analysis?"**
A bearing defect makes short impacts; the impacts ring the housing at kHz frequencies. A plain FFT
doesn't show the fault frequency. Band-pass filtering and taking the envelope reveals the impact rate,
which is the fault frequency.

**"You got 100 %. Is the model good?"**
No, 100 % is on the same conditions. Tested on a bigger defect it fell to 59 %; the model had memorised
the spectrum shape, not the physics. Physics-based envelope features brought it to 97.7 %. Also, CWRU
defects are artificial and from one rig; that's not field accuracy.

**"How did you prevent data leakage?"**
Windows were split by time, not randomly (start of each recording for training, end for testing). The
feature set was chosen with separate cross-validation, not by looking at the test score.

**"Why no envelope analysis on the ESP32?"**
The ADXL345 samples at most 3200 Hz, so Nyquist is 1600 Hz; the ringing band is 2-5 kHz. It's physically
invisible. So I used time-domain statistics + band energies up to 1600 Hz: 83 % accuracy under load
change. A faster sensor (e.g. an analog MEMS accelerometer + ADC) would do better.

**"How did you get the model onto the ESP32?"**
I trained a small Random Forest (10 trees, depth 6) and wrote a script that turns every tree into
if/else C code. Tests compile the C code on the laptop and compare it with Python: probability
difference < 10⁻⁷.

**"Why send features or decisions instead of raw data?"**
Raw data is ~3200 numbers per second; features are 12 numbers per window. Bandwidth and battery. In the
field (a wind turbine), connectivity is expensive and unreliable.

**"How did you secure it?"**
The only port open to the network is 8883: TLS (broker verified with my own CA) + username/password
(stored hashed). The passwordless port listens on localhost only. Secrets are not committed.

**"How do you avoid false alarms?"**
The alert looks at a one-minute average, not a single window, and waits for it to last 30 seconds. The
model also reports a confidence score; low confidence means "not sure".

**"What would you do differently?"**
Pick a faster-sampling sensor (so envelope analysis also runs on the device), and collect real, slowly
progressing wear data; CWRU defects are artificial and static.
