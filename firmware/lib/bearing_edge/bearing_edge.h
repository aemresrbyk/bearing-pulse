// Bearing Pulse edge library: features + classifier for one window of ADXL345 samples.
// Plain C99, no allocation, no dependencies: compiles for the ESP32 and for the laptop tests.
#pragma once

#define BE_WINDOW   1024   // samples per window (0.32 s at 3200 Hz)
#define BE_N_BANDS  8
#define BE_N_FEAT   (4 + BE_N_BANDS)   // rms, peak, crest, kurtosis, band0..band7
#define BE_N_CLASS  4                  // normal, inner, ball, outer

#ifdef __cplusplus
extern "C" {
#endif

// x: BE_WINDOW samples in g. out: BE_N_FEAT features (same order as src/edge.py FEATURE_NAMES).
void be_features(const float *x, float *out);

// feat: BE_N_FEAT features. prob: BE_N_CLASS class probabilities (mean of tree leaf distributions).
// Returns the index of the most likely class.
int be_predict(const float *feat, float *prob);

#ifdef __cplusplus
}
#endif
