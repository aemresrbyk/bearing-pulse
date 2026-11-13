"""Phase 3-4: features and classifier for the ESP32 + ADXL345 node.

The ADXL345 samples at most 3200 Hz, so Phase 1's 2-5 kHz envelope band is out of reach. The edge
features are cheap time-domain stats plus 8 FFT band energies up to 1600 Hz.

Three implementations of the same thing, kept in step by tests/test_edge.py:
  - features() here: NumPy reference, used for training
  - firmware/lib/bearing_edge/features.c: what runs on the ESP32
  - c_features(): that C code compiled for the laptop and called through ctypes
"""
import ctypes
import subprocess
from pathlib import Path

import numpy as np
from scipy import signal

ROOT = Path(__file__).resolve().parent.parent
C_DIR = ROOT / "firmware" / "lib" / "bearing_edge"
LIB = ROOT / ".local" / "libbearing_edge.so"

FS = 3200            # ADXL345 maximum output data rate (Hz)
WINDOW = 1024        # 0.32 s ≈ 9.6 shaft revolutions at 1797 rpm; power of 2 for the FFT; 4 kB of floats
N_BANDS = 8          # 0-1600 Hz in 200 Hz bands
LSB_G, RANGE_G = 0.0039, 16
FEATURE_NAMES = ["rms", "peak", "crest", "kurtosis"] + [f"band{i}" for i in range(N_BANDS)]
CLASSES = ["normal", "inner", "ball", "outer"]


def adxl345(x12k):
    """What the ADXL345 would have measured: 12 kHz -> 3200 Hz, clipped to ±16 g, 3.9 mg steps."""
    x = signal.resample_poly(x12k, 4, 15)          # 12000 * 4 / 15 = 3200, anti-aliased
    return np.round(np.clip(x, -RANGE_G, RANGE_G) / LSB_G) * LSB_G


def features(w):
    """Reference implementation. Written with plain NumPy so the C version can mirror it line by line."""
    w = np.asarray(w, dtype=np.float64)
    rms = np.sqrt(np.mean(w ** 2))
    peak = np.max(np.abs(w))
    d = w - w.mean()
    m2, m4 = np.mean(d ** 2), np.mean(d ** 4)
    kurt = m4 / m2 ** 2 - 3                         # excess kurtosis: 0 for Gaussian noise, high for impacts
    spec = np.abs(np.fft.rfft(w * np.hanning(len(w)))) ** 2
    bands = spec[1:].reshape(N_BANDS, -1).sum(1)    # drop DC, 512 bins -> 8 bands of 64
    return np.r_[rms, peak, peak / rms, kurt, np.log10(bands / bands.sum())]


def features_dict(w):
    return dict(zip(FEATURE_NAMES, map(float, c_features(w))))


# ---------- C library (same code as the firmware) ----------

_lib = None


def lib():
    """Compile the firmware C code for the laptop (once) and load it."""
    global _lib
    if _lib is None:
        srcs = sorted(C_DIR.glob("*.c"))
        if not LIB.exists() or any(s.stat().st_mtime > LIB.stat().st_mtime for s in [*srcs, *C_DIR.glob("*.h")]):
            LIB.parent.mkdir(exist_ok=True)
            subprocess.run(["cc", "-O2", "-shared", "-fPIC", "-o", LIB, *srcs, "-lm"], check=True)
        _lib = ctypes.CDLL(str(LIB))
        F = ctypes.POINTER(ctypes.c_float)
        _lib.be_features.argtypes = [F, F]
        _lib.be_predict.argtypes = [F, F]
        _lib.be_predict.restype = ctypes.c_int
    return _lib


def _f32(a):
    a = np.ascontiguousarray(a, dtype=np.float32)
    return a, a.ctypes.data_as(ctypes.POINTER(ctypes.c_float))


def c_features(w):
    assert len(w) == WINDOW
    w, wp = _f32(w)
    out, op = _f32(np.zeros(len(FEATURE_NAMES)))
    lib().be_features(wp, op)
    return out


def c_predict_features(f):
    f, fp = _f32(f)
    prob, pp = _f32(np.zeros(len(CLASSES)))
    k = lib().be_predict(fp, pp)
    return k, prob


def predict(w):
    """What the device publishes: label + confidence, computed by the C code."""
    k, prob = c_predict_features(c_features(w))
    return {"label": CLASSES[k], "confidence": round(float(prob[k]), 3)}
