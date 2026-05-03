# @superinstance/sonar-vision-tool

[![npm version](https://img.shields.io/npm/v/@superinstance/sonar-vision-tool.svg?style=flat-square)](https://www.npmjs.com/package/@superinstance/sonar-vision-tool)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![TypeScript](https://img.shields.io/badge/%3C%2F%3E-TypeScript-%230074c1.svg?style=flat-square)](https://www.typescriptlang.org/)
[![Node.js](https://img.shields.io/badge/Node.js-%3E%3D18.0-brightgreen?style=flat-square)](https://nodejs.org/)
[![Build Status](https://img.shields.io/github/actions/workflow/status/superinstance/sonar-vision-tool/ci.yml?branch=main&style=flat-square)](https://github.com/superinstance/sonar-vision-tool/actions)

> High-fidelity underwater acoustic simulation and sonar analysis toolkit for Node.js. Model sound propagation, predict sensor performance, and generate realistic sonar returns for physics-based maritime applications.

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
  - [`physics()` – Acoustic Environment](#physics--acoustic-environment)
  - [`ping()` – Travel Time & SNR](#ping--travel-time--snr)
  - [`scan()` – Seafloor Backscatter](#scan--seafloor-backscatter)
  - [`profile()` – Water Column Profile](#profile--water-column-profile)
  - [`detect()` – Active Sonar Detection](#detect--active-sonar-detection)
- [Streaming API](#streaming-api)
- [Error Handling](#error-handling)
- [TypeScript](#typescript)
- [License](#license)

---

## Installation

```bash
npm install @superinstance/sonar-vision-tool
```

**Requirements:** Node.js ≥ 18.0

---

## Quick Start

```javascript
import { SonarVision } from '@superinstance/sonar-vision-tool';

const sonar = new SonarVision({
  salinity: 35,      // PSU
  temperature: 10,   // °C
  depth: 100,        // meters
  frequency: 50000,  // Hz
});

// Compute acoustic physics for the environment
const env = await sonar.physics();
console.log(`Sound speed: ${env.soundSpeed} m/s`);

// Ping a target at 500 m range, 30° bearing
const echo = await sonar.ping({ range: 500, bearing: 30 });
console.log(`Round-trip: ${echo.travelTime} ms, SNR: ${echo.snr} dB`);
```

---

## Configuration

All constructor options are optional and fall back to standard oceanographic defaults.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `salinity` | `number` | `35` | Water salinity in practical salinity units (PSU). Range: `0 – 42` |
| `temperature` | `number` | `10` | Water temperature in °C. Range: `‑2 – 35` |
| `depth` | `number` | `0` | Sensor depth in meters. Range: `0 – 11000` |
| `frequency` | `number` | `50000` | Transducer center frequency in Hz. Range: `100 – 1000000` |
| `pH` | `number` | `8.1` | Seawater pH for absorption models. Range: `7.5 – 8.5` |
| `spreading` | `'spherical' \| 'cylindrical' \| 'hybrid'` | `'spherical'` | Geometric spreading loss model |
| `roughness` | `number` | `0.5` | RMS seafloor roughness in meters. Range: `0 – 10` |
| `sediment` | `'sand' \| 'silt' \| 'clay' \| 'gravel' \| 'rock'` | `'sand'` | Dominant sediment type for backscatter |
| `noiseFloor` | `number` | `-90` | Receiver noise floor in dB re 1 µPa. Range: `‑120 – ‑40` |
| `sourceLevel` | `number` | `220` | Transmit source level in dB re 1 µPa @ 1 m. Range: `100 – 260` |
| `pulseLength` | `number` | `0.001` | Transmit pulse length in seconds. Range: `1e‑6 – 1` |
| `bandwidth` | `number` | `1000` | Receiver bandwidth in Hz. Range: `1 – 1e6` |

```javascript
const sonar = new SonarVision({
  salinity: 34.5,
  temperature: 4,
  depth: 250,
  frequency: 120000,
  sediment: 'clay',
  spreading: 'hybrid',
  sourceLevel: 210,
  noiseFloor: -95,
});
```

---

## API Reference

### `physics()` – Acoustic Environment

Computes the local acoustic environment: sound speed, absorption coefficient, scattering strength, and visibility/attenuation at the configured depth.

**Signature:**
```typescript
async physics(): Promise<PhysicsResult>
```

**Returns:** `PhysicsResult`

| Property | Type | Unit | Description |
|----------|------|------|-------------|
| `soundSpeed` | `number` | m/s | Local speed of sound via Mackenzie (1981) |
| `absorption` | `number` | dB/km | Total absorption (Thorp–Fisher–Simmons) |
| `scattering` | `number` | dB | Volume scattering strength at frequency |
| `visibility` | `number` | m | Estimated acoustic visibility (1-way, 10 dB excess loss) |

**Example:**
```javascript
const phys = await sonar.physics();
// {
//   soundSpeed: 1490.23,
//   absorption: 14.82,
//   scattering: -72.4,
//   visibility: 675.3
// }
```

---

### `ping()` – Travel Time & SNR

Calculates one-way or two-way travel time and signal-to-noise ratio for a target or beacon at a given range and bearing.

**Signature:**
```typescript
async ping(opts: PingOptions): Promise<PingResult>
```

**`PingOptions`:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `range` | `number` | Yes | Slant range to target in meters (`> 0`) |
| `bearing` | `number` | Yes | Horizontal bearing in degrees (`0 – 360`) |
| `elevation` | `number` | No | Vertical elevation in degrees (`-90 – 90`, default: `0`) |
| `targetStrength` | `number` | No | Echo target strength in dB (default: `-30`) |
| `twoWay` | `boolean` | No | Compute round-trip time (default: `true`) |

**Returns:** `PingResult`

| Property | Type | Unit | Description |
|----------|------|------|-------------|
| `travelTime` | `number` | ms | One-way or round-trip time of flight |
| `snr` | `number` | dB | Signal-to-noise ratio at receiver |
| `spreadingLoss` | `number` | dB | Geometric spreading loss |
| `absorptionLoss` | `number` | dB | Cumulative absorption loss |
| `totalLoss` | `number` | dB | Sum of spreading + absorption |

**Example:**
```javascript
const echo = await sonar.ping({
  range: 1200,
  bearing: 45,
  targetStrength: -20,
  twoWay: true,
});
// {
//   travelTime: 1609.1,
//   snr: 18.3,
//   spreadingLoss: 62.1,
//   absorptionLoss: 17.8,
//   totalLoss: 79.9
// }
```

---

### `scan()` – Seafloor Backscatter

Simulates a multibeam or sidescan-like backscatter sweep across a swath of bearings, returning per-beam backscatter intensity and inferred sediment confidence.

**Signature:**
```typescript
async scan(opts: ScanOptions): Promise<ScanResult>
```

**`ScanOptions`:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `ranges` | `number[]` | Yes | Array of slant ranges in meters (ascending) |
| `bearings` | `number[]` | Yes | Array of bearings in degrees |
| `grazingAngle` | `number` | No | Grazing angle in degrees (default: `30`) |
| `resolution` | `number` | No | Along-track resolution in meters (default: `1`) |

**Returns:** `ScanResult`

| Property | Type | Description |
|----------|------|-------------|
| `beams` | `Beam[]` | One entry per `(range, bearing)` pair |
| `swathWidth` | `number` | Approximate seafloor swath width in meters |
| `centerDepth` | `number` | Nadir depth estimate in meters |

Each `Beam`:

| Property | Type | Unit | Description |
|----------|------|------|-------------|
| `range` | `number` | m | Slant range |
| `bearing` | `number` | ° | Beam bearing |
| `backscatter` | `number` | dB | Normalized backscatter intensity |
| `grazing` | `number` | ° | Effective grazing angle |
| `confidence` | `number` | `0 – 1` | Sediment-classification confidence |

**Example:**
```javascript
const scan = await sonar.scan({
  ranges: [50, 100, 200, 400, 800],
  bearings: [-60, -30, 0, 30, 60],
  grazingAngle: 45,
});

for (const beam of scan.beams) {
  console.log(`${beam.range}m @ ${beam.bearing}° → ${beam.backscatter.toFixed(1)} dB`);
}
```

---

### `profile()` – Water Column Profile

Generates a 21-point vertical profile of temperature, salinity, sound speed, and absorption from the surface to the configured sensor depth.

**Signature:**
```typescript
async profile(): Promise<ProfileResult>
```

**Returns:** `ProfileResult`

| Property | Type | Description |
|----------|------|-------------|
| `points` | `ProfilePoint[]` | 21 evenly-spaced depth samples |
| `depthStep` | `number` | Vertical spacing in meters |
| `mixedLayerDepth` | `number` | Estimated mixed-layer depth in meters |
| `soundChannel` | `boolean` | Whether a deep sound channel is detected |

Each `ProfilePoint` (index `0` = surface):

| Property | Type | Unit | Description |
|----------|------|------|-------------|
| `depth` | `number` | m | Water depth of sample |
| `temperature` | `number` | °C | Estimated temperature at depth |
| `salinity` | `number` | PSU | Estimated salinity at depth |
| `soundSpeed` | `number` | m/s | Computed sound speed |
| `absorption` | `number` | dB/km | Absorption coefficient |
| `gradient` | `number` | s⁻¹ | Local sound-speed gradient |

**Example:**
```javascript
const profile = await sonar.profile();

console.log(`Mixed layer: ${profile.mixedLayerDepth} m`);
console.log(`Deep sound channel: ${profile.soundChannel ? 'yes' : 'no'}`);

for (const pt of profile.points) {
  console.log(`${pt.depth}m: ${pt.soundSpeed.toFixed(1)} m/s`);
}
```

---

### `detect()` – Active Sonar Detection

Performs an active-sonar detection pass, returning contact list with estimated range, bearing, and probability of detection for each contact.

**Signature:**
```typescript
async detect(opts: DetectOptions): Promise<DetectResult>
```

**`DetectOptions`:**

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `maxRange` | `number` | No | Maximum search range in meters (default: `sonar.visibility * 2`) |
| `beamwidth` | `number` | No | Horizontal beamwidth in degrees (default: `10`) |
| `sweep` | `number[]` | No | Explicit bearing centers to search (default: `[0, 30, 60, ..., 330]`) |
| `falseAlarmRate` | `number` | No | Desired Pfa (default: `1e-6`) |
| `targetStrength` | `number` | No | Assumed target strength in dB (default: `-30`) |

**Returns:** `DetectResult`

| Property | Type | Description |
|----------|------|-------------|
| `contacts` | `Contact[]` | Detected contacts (may be empty) |
| `sweptBearings` | `number[]` | Bearings actually searched |
| `maxRange` | `number` | Search radius used |
| `probabilityOfDetection` | `number` | Aggregate Pd across swept volume |

Each `Contact`:

| Property | Type | Unit | Description |
|----------|------|------|-------------|
| `range` | `number` | m | Estimated slant range |
| `bearing` | `number` | ° | Estimated bearing |
| `elevation` | `number` | ° | Estimated elevation (0 if unknown) |
| `snr` | `number` | dB | Measured SNR at detection |
| `probability` | `number` | `0 – 1` | Single-look probability of detection |
| `confidence` | `'high' \| 'medium' \| 'low'` | | Contact confidence tier |

**Example:**
```javascript
const detect = await sonar.detect({
  maxRange: 2000,
  beamwidth: 15,
  targetStrength: -25,
  falseAlarmRate: 1e-5,
});

console.log(`Contacts found: ${detect.contacts.length}`);
for (const c of detect.contacts) {
  console.log(
    `  ${c.confidence.toUpperCase()} contact at ` +
    `${c.range}m / ${c.bearing}° (SNR ${c.snr.toFixed(1)} dB)`
  );
}
```

---

## Streaming API

For real-time or large survey simulations, every method exposes a streaming variant that yields incremental results via an `AsyncIterable`.

Streaming method names are suffixed with `Stream`:

| Classic | Streaming |
|---------|-----------|
| `physics()` | `physicsStream()` |
| `ping()` | `pingStream()` |
| `scan()` | `scanStream()` |
| `profile()` | `profileStream()` |
| `detect()` | `detectStream()` |

Each stream yields `{ done: false, value: PartialResult }` chunks and terminates with `{ done: true, result: FinalResult }`.

### Example: Streaming scan

```javascript
const stream = sonar.scanStream({
  ranges: Array.from({ length: 100 }, (_, i) => (i + 1) * 10),
  bearings: Array.from({ length: 36 }, (_, i) => i * 10),
});

for await (const chunk of stream) {
  if (!chunk.done) {
    // chunk.value is a single Beam
    processBeam(chunk.value);
  } else {
    // chunk.result is the full ScanResult
    console.log(`Swath width: ${chunk.result.swathWidth} m`);
  }
}
```

### Example: Streaming profile with progress

```javascript
const stream = sonar.profileStream();
let received = 0;

for await (const chunk of stream) {
  if (!chunk.done) {
    received++;
    const pt = chunk.value;
    console.log(`[${received}/21] ${pt.depth}m → ${pt.soundSpeed.toFixed(1)} m/s`);
  } else {
    console.log('Profile complete:', chunk.result.soundChannel);
  }
}
```

### Example: Aborting a long-running detect stream

```javascript
const controller = new AbortController();

// Abort after 5 seconds
setTimeout(() => controller.abort(), 5000);

try {
  for await (const chunk of sonar.detectStream({ maxRange: 5000 }, controller.signal)) {
    if (!chunk.done && chunk.value.confidence === 'high') {
      console.log('High-confidence contact!', chunk.value);
    }
  }
} catch (err) {
  if (err.name === 'AbortError') {
    console.log('Search aborted by user');
  } else {
    throw err;
  }
}
```

---

## Error Handling

All async methods throw typed `SonarVisionError` instances. Every error carries a `code` string for programmatic handling and a human-readable `message`.

| Code | Meaning | Typical Cause |
|------|---------|---------------|
| `INVALID_CONFIG` | Constructor option out of range | Salinity > 42, negative depth, etc. |
| `INVALID_ARGUMENT` | Method argument out of range | Negative range, bearing > 360 |
| `COMPUTATION_ERROR` | Internal math or model failure | Extreme inputs causing divergence |
| `TIMEOUT` | Computation exceeded deadline | Very large scans without streaming |
| `ABORTED` | Request was cancelled | `AbortSignal` triggered |

**Example:**
```javascript
import { SonarVision, SonarVisionError } from '@superinstance/sonar-vision-tool';

try {
  const sonar = new SonarVision({ temperature: 50 }); // invalid
  await sonar.physics();
} catch (err) {
  if (err instanceof SonarVisionError) {
    console.error(`[${err.code}] ${err.message}`);
    // → [INVALID_CONFIG] temperature must be between -2 and 35 °C
  } else {
    console.error('Unexpected error:', err);
  }
}
```

**Validation helper:**
```javascript
import { validateConfig } from '@superinstance/sonar-vision-tool';

const issues = validateConfig({ temperature: 50, depth: -5 });
// [
//   { field: 'temperature', message: 'must be ≤ 35', value: 50 },
//   { field: 'depth', message: 'must be ≥ 0', value: -5 }
// ]
```

---

## TypeScript

First-class TypeScript support with exported interfaces for all inputs and outputs.

```typescript
import {
  SonarVision,
  SonarConfig,
  PhysicsResult,
  PingOptions,
  PingResult,
  ScanOptions,
  ScanResult,
  ProfileResult,
  DetectOptions,
  DetectResult,
  SonarVisionError,
} from '@superinstance/sonar-vision-tool';

const config: SonarConfig = {
  salinity: 35,
  temperature: 10,
  depth: 100,
  frequency: 50000,
};

const sonar = new SonarVision(config);
const phys: PhysicsResult = await sonar.physics();
```

---

## License

MIT © SuperInstance Labs

```
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
