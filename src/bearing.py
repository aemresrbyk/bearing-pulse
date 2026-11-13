"""Phase 1 helpers: load CWRU data, bearing fault frequencies, envelope spectrum, features."""
from pathlib import Path

import numpy as np
import scipy.io
from scipy import signal, stats

FS = 12_000          # target sample rate for everything (Hz)
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

# file number -> (condition, load HP). 12 kHz drive-end, 0.007" faults, outer race at 6:00.
FILES = {
    97: ("normal", 0), 98: ("normal", 1), 99: ("normal", 2), 100: ("normal", 3),
    105: ("inner", 0), 106: ("inner", 1), 107: ("inner", 2), 108: ("inner", 3),
    118: ("ball", 0), 119: ("ball", 1), 120: ("ball", 2), 121: ("ball", 3),
    130: ("outer", 0), 131: ("outer", 1), 132: ("outer", 2), 133: ("outer", 3),
}
# 0.021" faults at 0 HP: only used as an out-of-distribution test (bigger defect than training)
FILES_021 = {209: ("inner", 0), 222: ("ball", 0), 234: ("outer", 0)}
CLASSES = ["normal", "inner", "ball", "outer"]
NOMINAL_RPM = {0: 1797, 1: 1772, 2: 1750, 3: 1730}  # used when a file has no RPM key

# SKF 6205-2RS drive-end bearing geometry (inches)
N_BALLS, BALL_D, PITCH_D, CONTACT_ANGLE = 9, 0.3126, 1.537, 0.0


def fault_freqs(rpm):
    """Characteristic fault frequencies in Hz for a given shaft speed."""
    fr = rpm / 60
    r = BALL_D / PITCH_D * np.cos(CONTACT_ANGLE)
    return {
        "shaft": fr,
        "FTF": fr / 2 * (1 - r),                              # cage
        "BPFO": N_BALLS / 2 * fr * (1 - r),                   # outer race
        "BPFI": N_BALLS / 2 * fr * (1 + r),                   # inner race
        "BSF": PITCH_D / (2 * BALL_D) * fr * (1 - r ** 2),    # ball spin
    }


def load(num):
    """Return (drive-end signal at 12 kHz, rpm) for one CWRU file."""
    m = scipy.io.loadmat(RAW / f"{num}.mat")
    # key must match the file number: 99.mat also contains X098_* keys
    x = m[f"X{num:03d}_DE_time"].ravel()
    if num in FILES and FILES[num][0] == "normal":
        # normal baseline is recorded at 48 kHz (verified: its spectral peaks only line up with
        # the 12 kHz fault files when read as 48 kHz)
        x = signal.resample_poly(x, 1, 4)
    rpm_key = f"X{num:03d}RPM"
    rpm = float(m[rpm_key].ravel()[0]) if rpm_key in m else NOMINAL_RPM[FILES[num][1]]  # 98/99 lack RPM
    return x, rpm


def envelope_spectrum(x, fs=FS, band=(2000, 5000)):
    """Band-pass -> Hilbert envelope -> spectrum. Returns (freqs, amplitude)."""
    sos = signal.butter(4, band, btype="bandpass", fs=fs, output="sos")
    env = np.abs(signal.hilbert(signal.sosfiltfilt(sos, x)))
    env -= env.mean()
    amp = np.abs(np.fft.rfft(env)) * 2 / len(env)
    return np.fft.rfftfreq(len(env), 1 / fs), amp


def windows(x, size=2048):
    """Non-overlapping windows, in time order."""
    n = len(x) // size
    return x[: n * size].reshape(n, size)


FEATURE_NAMES = (
    ["rms", "peak", "crest", "kurtosis", "skewness", "std"]
    + [f"band{i}" for i in range(8)]
    + ["env_BPFO", "env_BPFI", "env_BSF"]
)


def features(w, rpm, fs=FS):
    """Time-domain stats, 8 FFT band energies, envelope amplitude at each fault frequency."""
    rms = np.sqrt(np.mean(w ** 2))
    peak = np.max(np.abs(w))
    spec = np.abs(np.fft.rfft(w * np.hanning(len(w)))) ** 2
    bands = [b.sum() for b in np.array_split(spec[1:], 8)]
    bands = np.log10(np.array(bands) / spec[1:].sum())       # relative energy, log scale
    f, env = envelope_spectrum(w, fs)
    ff = fault_freqs(rpm)
    # max envelope amplitude within ±3 % of each fault frequency, at least one bin wide (~6 Hz bins)
    tol = lambda f0: max(0.03 * f0, f[1])
    env_at = [env[np.abs(f - ff[k]) <= tol(ff[k])].max() for k in ("BPFO", "BPFI", "BSF")]
    return np.r_[rms, peak, peak / rms, stats.kurtosis(w), stats.skew(w), w.std(), bands, env_at]


def dataset(loads, size=2048, files=FILES):
    """Feature matrix for the given loads. Returns X, y, file number, position-in-file (0..1)."""
    X, y, src, pos = [], [], [], []
    for num, (cond, load_hp) in files.items():
        if load_hp not in loads:
            continue
        x, rpm = load(num)
        W = windows(x, size)
        X += [features(w, rpm) for w in W]
        y += [cond] * len(W)
        src += [num] * len(W)
        pos += list(np.arange(len(W)) / len(W))
    return np.array(X), np.array(y), np.array(src), np.array(pos)


if __name__ == "__main__":
    # self-check: geometry formulas reproduce CWRU's published multiples of shaft speed
    ff = fault_freqs(60)  # 1 Hz shaft
    assert abs(ff["BPFI"] - 5.4152) < 1e-3 and abs(ff["BPFO"] - 3.5848) < 1e-3
    assert abs(ff["FTF"] - 0.39828) < 1e-3 and abs(2 * ff["BSF"] - 4.7135) < 1e-3
    # self-check: envelope spectrum finds a synthetic 100 Hz modulation on a 3 kHz carrier
    t = np.arange(FS) / FS
    f, a = envelope_spectrum((1 + np.cos(2 * np.pi * 100 * t)) * np.sin(2 * np.pi * 3000 * t))
    assert abs(f[a[f > 10].argmax() + (f <= 10).sum()] - 100) < 1
    print("ok")
