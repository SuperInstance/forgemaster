/**
 * Spectral analysis — entropy, Hurst exponent, autocorrelation.
 *
 * Pure TypeScript, zero dependencies.
 */

import type { SpectralSummary } from "./types.js";

// Precomputed 1/e
const INV_E = 1.0 / Math.E;

// ---- Entropy ------------------------------------------------------------

/**
 * Shannon entropy via histogram binning (bits).
 */
export function entropy(data: number[], bins: number = 10): number {
  const n = data.length;
  if (n < 2) return 0.0;

  let minVal = data[0];
  let maxVal = data[0];
  for (let i = 1; i < n; i++) {
    if (data[i] < minVal) minVal = data[i];
    else if (data[i] > maxVal) maxVal = data[i];
  }

  if (maxVal === minVal) return 0.0;

  const invRange = bins / (maxVal - minVal);
  const counts = new Array<number>(bins).fill(0);

  for (let i = 0; i < n; i++) {
    let idx = Math.floor((data[i] - minVal) * invRange);
    if (idx >= bins) idx = bins - 1;
    counts[idx]++;
  }

  const invN = 1.0 / n;
  const invLog2 = 1.0 / Math.log(2);
  let h = 0.0;
  for (let i = 0; i < bins; i++) {
    const c = counts[i];
    if (c > 0) {
      const p = c * invN;
      h -= p * Math.log(p) * invLog2;
    }
  }
  return h;
}

// ---- Autocorrelation ----------------------------------------------------

/**
 * Normalized autocorrelation up to maxLag.
 */
export function autocorrelation(data: number[], maxLag?: number): number[] {
  const n = data.length;
  if (n < 2) return [1.0];

  if (maxLag === undefined) maxLag = Math.floor(n / 2);
  maxLag = Math.min(maxLag, n - 1);

  const invN = 1.0 / n;
  let sum = 0;
  for (let i = 0; i < n; i++) sum += data[i];
  const mean = sum * invN;

  // Center and compute variance in one pass
  const centered = new Float64Array(n);
  for (let i = 0; i < n; i++) centered[i] = data[i] - mean;

  let r0 = 0;
  for (let i = 0; i < n; i++) r0 += centered[i] * centered[i];
  r0 *= invN;

  if (r0 === 0) return [1.0].concat(new Array<number>(maxLag).fill(0.0));

  const invR0 = 1.0 / r0;
  const result = new Array<number>(maxLag + 1);

  for (let lag = 0; lag <= maxLag; lag++) {
    let rk = 0;
    const limit = n - lag;
    for (let t = 0; t < limit; t++) {
      rk += centered[t] * centered[t + lag];
    }
    result[lag] = rk * invN * invR0;
  }

  return result;
}

// ---- Hurst exponent (R/S method) ----------------------------------------

/**
 * Estimate Hurst exponent via R/S analysis.
 */
export function hurstExponent(data: number[]): number {
  const n = data.length;
  if (n < 20) return 0.5;

  const invN = 1.0 / n;
  let sum = 0;
  for (let i = 0; i < n; i++) sum += data[i];
  const meanVal = sum * invN;

  const centered = new Float64Array(n);
  for (let i = 0; i < n; i++) centered[i] = data[i] - meanVal;

  // Geometric progression of test sizes
  const testSizes: number[] = [];
  let s = 16;
  while (s <= Math.floor(n / 2)) {
    testSizes.push(s);
    const next = s * 2 <= Math.floor(n / 2) ? s * 2 : Math.floor(s * 1.5);
    if (next === testSizes[testSizes.length - 1]) break;
    s = next;
  }

  if (testSizes.length === 0) {
    if (n >= 8) testSizes.push(Math.floor(n / 4));
    else testSizes.push(n);
    // Filter too-small
    for (let i = testSizes.length - 1; i >= 0; i--) {
      if (testSizes[i] < 4) testSizes.splice(i, 1);
    }
  }

  const sizes: number[] = [];
  const rsValues: number[] = [];

  for (const size of testSizes) {
    if (size < 4 || size > n) continue;

    const numSubseries = Math.floor(n / size);
    if (numSubseries < 1) continue;

    const invSize = 1.0 / size;
    let rsSum = 0;
    let rsCount = 0;

    for (let i = 0; i < numSubseries; i++) {
      const start = i * size;
      // Sub-mean
      let subSum = 0;
      for (let j = start; j < start + size; j++) subSum += centered[j];
      const subMean = subSum * invSize;

      // Cumulative deviations with inline min/max
      let running = 0;
      let cumMin = 0;
      let cumMax = 0;
      for (let j = start; j < start + size; j++) {
        running += centered[j] - subMean;
        if (running < cumMin) cumMin = running;
        else if (running > cumMax) cumMax = running;
      }
      const r = cumMax - cumMin;

      // Variance
      let var_ = 0;
      for (let j = start; j < start + size; j++) {
        const d = centered[j] - subMean;
        var_ += d * d;
      }
      var_ *= invSize;

      if (var_ > 1e-20) {
        rsSum += r / Math.sqrt(var_);
        rsCount++;
      }
    }

    if (rsCount > 0) {
      const avgRs = rsSum / rsCount;
      if (avgRs > 0) {
        sizes.push(size);
        rsValues.push(avgRs);
      }
    }
  }

  if (sizes.length < 2) return 0.5;

  // Linear regression on log-log
  const nPts = sizes.length;
  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
  for (let i = 0; i < nPts; i++) {
    const lx = Math.log(sizes[i]);
    const ly = Math.log(rsValues[i]);
    sumX += lx;
    sumY += ly;
    sumXY += lx * ly;
    sumX2 += lx * lx;
  }

  const denom = nPts * sumX2 - sumX * sumX;
  if (denom === 0) return 0.5;

  const h = (nPts * sumXY - sumX * sumY) / denom;
  return Math.max(0, Math.min(1, h));
}

// ---- Spectral summary ---------------------------------------------------

/**
 * Compute a complete spectral summary of a signal.
 */
export function spectralSummary(
  data: number[],
  bins: number = 10,
  maxLag?: number,
): SpectralSummary {
  const h = entropy(data, bins);
  const hurstVal = hurstExponent(data);
  const acf = autocorrelation(data, maxLag);

  const acfLag1 = acf.length > 1 ? acf[1] : 0.0;

  let decayLag = acf.length;
  const threshold = INV_E; // 1/e ≈ 0.3679
  for (let i = 1; i < acf.length; i++) {
    if (Math.abs(acf[i]) < threshold) {
      decayLag = i;
      break;
    }
  }

  const isStationary = (0.4 <= hurstVal && hurstVal <= 0.6) && Math.abs(acfLag1) < 0.3;

  return Object.freeze({
    entropyBits: h,
    hurst: hurstVal,
    autocorrLag1: acfLag1,
    autocorrDecay: decayLag,
    isStationary,
  });
}

/**
 * Compute spectral summary for multiple time series.
 */
export function spectralBatch(
  seriesList: number[][],
  bins: number = 10,
  maxLag?: number,
): SpectralSummary[] {
  return seriesList.map((data) => spectralSummary(data, bins, maxLag));
}
