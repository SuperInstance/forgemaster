# @superinstance/sonar-vision-tool

[![npm version](https://img.shields.io/npm/v/@superinstance/sonar-vision-tool.svg)](https://www.npmjs.com/package/@superinstance/sonar-vision-tool)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Types](https://img.shields.io/badge/types-included-blue.svg)](https://www.npmjs.com/package/@superinstance/sonar-vision-tool)

Real-time underwater sonar physics for any TypeScript agent. Computes acoustic propagation, depth profiles, object detection, and seafloor characterization from first-principles oceanographic models.

Works with `@openagents/toolset` — register, query, stream.

## Installation

```bash
npm install @superinstance/sonar-vision-tool
```

## Quick Start

```typescript
import { ToolSet } from '@openagents/toolset';
import { SonarVisionTool } from '@superinstance/sonar-vision-tool';

const tool = new SonarVisionTool({
  endpoint: 'http://localhost:8080',
  timeout: 5000,
});

const ts = new ToolSet([tool]);

// Query physics at a specific depth
const result = await tool.execute({
  action: 'physics',
  depth: 15,
  chlorophyll: 4.0,
  season: 'summer',
});
```

## Actions

### `physics` — Underwater Physics at Depth

Computes sound speed, absorption, scattering, attenuation, visibility, and thermocline gradient at a given depth.

```typescript
const physics = await tool.execute({
  action: 'physics',
  depth: 25,           // meters
  chlorophyll: 3.5,    // mg/m³ (turbidity proxy)
  season: 'summer',    // 'summer' | 'winter' | 'spring' | 'fall'
});
// Returns:
// {
//   water_type: "Oceanic Type II",
//   visibility: 6.76,       // meters (Secchi depth)
//   sound_speed: 1526.9,    // m/s
//   temperature: 22.0,      // °C
//   dTdz: -0.0000,          // °C/m (thermocline gradient)
//   absorption: 0.241,      // dB/km
//   scattering: 0.0102,     // volume scattering strength
//   attenuation: 0.252,     // total path loss rate
//   seabed: 0.464,          // bottom reflection coefficient
//   refraction: 31.1        // ray bending angle in degrees
// }
```

### `ping` — Acoustic Ping Simulation

Simulates an active sonar ping and returns travel time, spreading loss, and SNR.

```typescript
const ping = await tool.execute({
  action: 'ping',
  depth: 30,
  target_range: 500,   // meters to target
  frequency: 12000,    // Hz
  source_level: 220,   // dB re 1 µPa
});
// Returns:
// {
//   travel_time: 0.327,       // seconds (round trip / 2)
//   spreading_loss: 53.98,    // dB (cylindrical spreading)
//   absorption_loss: 0.12,    // dB at frequency
//   total_loss: 54.10,        // dB
//   snr: 28.4,                // signal-to-noise ratio dB
//   detection: true           // target detectable
// }
```

### `profile` — Depth Profile Generation

Generates a 21-point water column profile from surface to seabed.

```typescript
const profile = await tool.execute({
  action: 'profile',
  max_depth: 200,      // meters
  chlorophyll: 4.0,
  season: 'summer',
});
// Returns: array of 21 { depth, sound_speed, temperature, absorption, visibility } objects
// sampled at ~10m intervals from 0 to max_depth
```

### `detect` — Active Sonar Object Detection

Detects objects using active sonar with range and bearing estimation.

```typescript
const detection = await tool.execute({
  action: 'detect',
  depth: 50,
  bearing: 45,         // degrees from bow
  frequency: 15000,
  pulse_length: 0.01,  // seconds
  source_level: 225,
  target_strength: 15, // dB (submarine ~15, fish school ~-20)
});
// Returns:
// {
//   range: 342.7,             // estimated meters
//   bearing: 44.8,            // estimated degrees
//   snr: 18.2,               // dB
//   detection_confidence: 0.91,
//   doppler_shift: 0.0,      // Hz (0 if stationary)
//   classification_hint: "hard_target"
// }
```

### `scan` — Seafloor Scan

Characterizes the seafloor using backscatter analysis.

```typescript
const scan = await tool.execute({
  action: 'scan',
  depth: 80,
  frequency: 12000,
  swathe_width: 500,   // meters
});
// Returns:
// {
//   backscatter_strength: -32.4,  // dB
//   terrain_type: "sandy_mud",
//   roughness: 0.15,              // surface roughness index
//   sediment_classification: "fine_grained",
//   bathymetry_points: [...]      // depth map across swathe
// }
```

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `endpoint` | `string` | `http://localhost:8080` | SonarVision server URL |
| `timeout` | `number` | `5000` | Request timeout in ms |
| `retries` | `number` | `2` | Retry count on failure |
| `retryDelay` | `number` | `1000` | Delay between retries (ms) |
| `cacheTTL` | `number` | `30000` | Cache lifetime for physics results (ms) |
| `waterModel` | `string` | `'standard'` | Ocean model: `'standard'` or `'arctic'` |

## Streaming / Real-Time

For continuous sensor feeds, use the WebSocket interface:

```typescript
import { SonarVisionStream } from '@superinstance/sonar-vision-tool';

const stream = new SonarVisionStream({
  endpoint: 'ws://localhost:8080/stream',
  depth: 30,
  frequency: 12000,
});

stream.on('physics', (data) => {
  console.log(`Sound speed at ${data.depth}m: ${data.sound_speed} m/s`);
});

stream.on('detection', (target) => {
  console.log(`Contact: bearing ${target.bearing}°, range ${target.range}m`);
});

stream.on('error', (err) => {
  console.error('Stream error:', err.message);
});

await stream.start();
// ... later
await stream.stop();
```

## Error Handling

All errors extend `SonarVisionError` with machine-readable codes:

```typescript
try {
  const result = await tool.execute({ action: 'physics', depth: 15 });
} catch (err) {
  if (err instanceof SonarVisionError) {
    switch (err.code) {
      case 'DEPTH_OUT_OF_RANGE':
        // depth must be 0-11000m
        break;
      case 'FREQUENCY_INVALID':
        // frequency must be 1-1000000 Hz
        break;
      case 'ENDPOINT_UNREACHABLE':
        // server down or wrong URL
        break;
      case 'TIMEOUT':
        // request exceeded configured timeout
        break;
      case 'INVALID_ACTION':
        // unknown action name
        break;
    }
    console.error(`[${err.code}] ${err.message}`);
  }
}
```

## Integration with @openagents/toolset

```typescript
import { ToolSet } from '@openagents/toolset';
import { SonarVisionTool, SonarVisionStream } from '@superinstance/sonar-vision-tool';

const sonar = new SonarVisionTool({ endpoint: 'http://sonar.fleet:8080' });
const ts = new ToolSet([sonar]);

// Agent automatically discovers the 'sonar' tool
// and can call tool.execute() with natural language parameters
```

## Physics Models

The tool implements first-principles oceanographic models:

- **Sound speed:** Mackenzie equation (1981) — temperature, salinity, depth
- **Absorption:** Francois-Garrison model — frequency, temperature, pH, depth
- **Scattering:** Volume scattering from chlorophyll concentration
- **Visibility:** Secchi depth from turbidity models
- **Spreading loss:** Cylindrical (shallow) / spherical (deep) transition
- **Refraction:** Snell's law ray tracing through thermocline

## License

MIT © [SuperInstance](https://github.com/SuperInstance)

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). PRs welcome.

## Changelog

See [CHANGELOG.md](./CHANGELOG.md).
