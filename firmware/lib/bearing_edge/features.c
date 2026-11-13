// Mirrors features() in src/edge.py. tests/test_edge.py checks both give the same numbers.
#include <math.h>
#include "bearing_edge.h"

#define N BE_WINDOW
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Working buffers are static: 8 kB that would otherwise sit on the ESP32 task stack.
static float re[N], im[N];

// In-place iterative radix-2 FFT (N must be a power of two).
static void fft(float *xr, float *xi) {
    for (int i = 1, j = 0; i < N; i++) {             // bit-reversal permutation
        int bit = N >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j |= bit;
        if (i < j) {
            float t = xr[i]; xr[i] = xr[j]; xr[j] = t;
            t = xi[i]; xi[i] = xi[j]; xi[j] = t;
        }
    }
    for (int len = 2; len <= N; len <<= 1) {         // butterflies
        double ang = -2 * M_PI / len;
        for (int i = 0; i < N; i += len) {
            for (int k = 0; k < len / 2; k++) {
                float wr = (float)cos(ang * k), wi = (float)sin(ang * k);
                float ur = xr[i + k], ui = xi[i + k];
                float vr = xr[i + k + len / 2] * wr - xi[i + k + len / 2] * wi;
                float vi = xr[i + k + len / 2] * wi + xi[i + k + len / 2] * wr;
                xr[i + k] = ur + vr; xi[i + k] = ui + vi;
                xr[i + k + len / 2] = ur - vr; xi[i + k + len / 2] = ui - vi;
            }
        }
    }
}

void be_features(const float *x, float *out) {
    // Time domain. Sums in double: 1024 squared samples lose precision in float.
    double s = 0, s2 = 0, peak = 0;
    for (int i = 0; i < N; i++) {
        s += x[i];
        s2 += (double)x[i] * x[i];
        if (fabs(x[i]) > peak) peak = fabs(x[i]);
    }
    double mean = s / N, rms = sqrt(s2 / N);
    double m2 = 0, m4 = 0;
    for (int i = 0; i < N; i++) {
        double d = x[i] - mean, d2 = d * d;
        m2 += d2; m4 += d2 * d2;
    }
    m2 /= N; m4 /= N;
    out[0] = (float)rms;
    out[1] = (float)peak;
    out[2] = (float)(peak / rms);
    out[3] = (float)(m4 / (m2 * m2) - 3);

    // Spectrum: Hann window (symmetric, like np.hanning), FFT, power in 8 equal bands without DC.
    for (int i = 0; i < N; i++) {
        re[i] = x[i] * (float)(0.5 - 0.5 * cos(2 * M_PI * i / (N - 1)));
        im[i] = 0;
    }
    fft(re, im);
    double band[BE_N_BANDS] = {0}, total = 0;
    const int per = (N / 2) / BE_N_BANDS;             // 64 bins per band
    for (int b = 1; b <= N / 2; b++) {                // bins 1..512 (rfft has N/2+1 bins)
        double p = (double)re[b] * re[b] + (double)im[b] * im[b];
        band[(b - 1) / per] += p;
        total += p;
    }
    for (int k = 0; k < BE_N_BANDS; k++) out[4 + k] = (float)log10(band[k] / total);
}
