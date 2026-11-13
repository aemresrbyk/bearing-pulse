"""Checks that the firmware C code gives the same answers as the Python it was trained with.

    python src/train_edge.py     # once: trains, exports model.c, saves the test set
    python tests/test_edge.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import bearing  # noqa: E402
import edge  # noqa: E402


def test_features():
    worst = np.zeros(len(edge.FEATURE_NAMES))
    for num in (97, 105, 118, 130, 108, 133):       # every class, light and heavy load
        x = edge.adxl345(bearing.load(num)[0])
        for i in range(0, len(x) - edge.WINDOW, edge.WINDOW * 4):
            w = x[i:i + edge.WINDOW]
            py, c = edge.features(w), edge.c_features(w)
            worst = np.maximum(worst, np.abs(py - c) / np.maximum(np.abs(py), 1e-3))
    print("max relative error per feature:", dict(zip(edge.FEATURE_NAMES, worst.round(6))))
    assert worst.max() < 1e-4, "C features drift from the Python reference"


def test_model():
    d = np.load(edge.ROOT / ".local" / "edge_testset.npz")
    X = d["X"].astype(np.float32)                    # sklearn also works on float32 features
    c = np.array([edge.c_predict_features(f)[1] for f in X])
    print(f"model: {len(X)} windows, max |C prob - sklearn prob| = {np.abs(c - d['proba']).max():.2e}, "
          f"same label: {(c.argmax(1) == d['proba'].argmax(1)).mean():.3%}")
    assert np.abs(c - d["proba"]).max() < 1e-5


def test_end_to_end():
    # raw samples -> C features -> C model, the exact path the ESP32 runs
    x = edge.adxl345(bearing.load(130)[0])           # outer race fault, 0 HP
    labels = [edge.predict(x[i:i + edge.WINDOW])["label"] for i in range(0, len(x) - edge.WINDOW, edge.WINDOW)]
    share = labels.count("outer") / len(labels)
    print(f"end to end on outer race recording: {share:.1%} 'outer'")
    assert share > 0.9


if __name__ == "__main__":
    test_features()
    test_model()
    test_end_to_end()
    print("ok")
