# SonarVision Tool for Open Agents

Integrate real-time underwater sonar physics into any TypeScript agent.
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

// Register with agent toolset
const ts = new ToolSet([tool]);

// Query physics at a specific depth
const result = await tool.execute({
  action: 'physics',
  depth: 15,
  chlorophyll: 4.0,
  season: 'summer',
});

console.log(result);
// {
//   water_type: "Oceanic Type II",
//   visibility: 6.76,
//   sound_speed: 1526.9,
//   temperature: 22.0,
//   dTdz: -0.0000,
//   absorption: 0.241,
//   scattering: 0.0102,
//   attenuation: 0.252,
//   seabed: 0.464,
//   refraction: 31.1
// }
```

## Actions

### `infer` — Depth Profile to Sonar Frame

Send depth profile → receive processed sonar frame.

```typescript
tool.execute({
  action: 'infer',
  depths: [0, 5, 10, 15, 20, 30, 50, 75, 100],
  frequency_khz: 200,
});
```

Returns array of `SonarFrame` objects with raw physics, optionally beamformed.

### `physics` — Deterministic Physics Query

Get all 9 physics parameters for a given depth/environment.

```typescript
tool.execute({
  action: 'physics',
  depth: 30,
  chlorophyll: 0.8,
  season: 'summer',
  sediment: 'sand',
  wavelength: 480,
  salinity: 35,
});
```

Deterministic: same inputs → identical outputs across all agent instances.
Used for multi-agent A2A physics consensus.

### `health` — Server Status

```typescript
tool.execute({ action: 'health' });
// { status: "ok", uptime: 3600, pings: 1042, avg_latency_ms: 12.3 }
```

## Schema (Zod)

```typescript
const SonarVisionSchema = z.object({
  action: z.enum(['infer', 'physics', 'health']),
  depth: z.number().min(0).max(1000).optional(),
  depths: z.array(z.number()).optional(),
  chlorophyll: z.number().min(0).max(30).default(5.0),
  season: z.enum(['summer', 'winter']).default('summer'),
  sediment: z.enum(['mud', 'sand', 'gravel', 'rock', 'seagrass']).default('sand'),
  wavelength: z.number().min(300).max(700).default(480),
  salinity: z.number().min(0).max(45).default(35),
  frequency_khz: z.number().min(10).max(1000).optional(),
  timeout: z.number().min(100).max(30000).default(5000),
});
```

## Physics Model

Uses the FLUX 9-opcode marine physics extension (v3.1):

| Opcode | Function | Model |
|--------|----------|-------|
| B0 | Absorption | Francois-Garrison (wavelength + water type) |
| B1 | Scattering | Rayleigh-like (wavelength + depth) |
| B2 | Water Type | Jerlov classification (chlorophyll) |
| B3 | Thermocline | Gaussian gradient (depth + season) |
| B4 | Seabed | Sediment reflectivity with depth decay |
| B5 | Attenuation | Absorption + Scattering |
| B6 | Visibility | Secchi depth (1.7 / attenuation) |
| B7 | Sound Speed | Mackenzie equation (T, S, z) |
| B8 | Refraction | Snell's law (θ, v₁, v₂) |

**Determinism guarantee:** Given identical input parameters, all physics
operations return bit-identical outputs across all interpreter instances.
This is verified via the FLUX dive demo (21 depths × 9 ops = 189 checks).

## Integration with FLUX

Agents can query FLUX VM physics via A2A opcodes:

```flux
; Agent agent_sonar has this tool registered
TELL R1, agent_sonar, PHYSICS_INQUIRY
ASK  R2, agent_sonar, R1
; R2 now contains { depth: 30, visibility: 6.78, ... }
```

Or directly via the tool:

```typescript
// FLUX bytecode running in the VM calls back to this tool
const physics = await sonarTool.execute({
  action: 'physics',
  depth: vm.read_fp(1),  // F1 = depth register
  chlorophyll: vm.read_fp(2),  // F2 = chlorophyll register
});
```

## Deployment

```yaml
# docker-compose.yml
services:
  sonar-vision:
    build: .
    ports:
      - "8080:8080"
    environment:
      - MODEL_PATH=/models/sonar-vision.onnx
      - PHYSICS_ENGINE=flux

  agent:
    build: ./agent
    environment:
      - SONAR_VISION_ENDPOINT=http://sonar-vision:8080
    depends_on: [sonar-vision]
```

## Examples

### Multi-Agent Physics Consensus

```typescript
// Three agents independently compute physics for the same depth
const agents = [sonarTool, sonarTool2, sonarTool3];
const results = await Promise.all(
  agents.map(a => a.execute({ action: 'physics', depth: 15 }))
);

// All three should return identical results (within 1e-6)
const checksum = results.map(r => JSON.stringify(r));
console.assert(new Set(checksum).size === 1,
  'Determinism violated! Agents disagree on physics.');
```

### Deep Dive Time Series

```typescript
// Record a full dive profile
const depths = Array.from({ length: 21 }, (_, i) => i * 5);
const profile = await Promise.all(
  depths.map(d => sonarTool.execute({ action: 'physics', depth: d }))
);

console.table(profile.map(p => ({
  depth: p.depth,
  type: p.water_type,
  temp: p.temperature,
  visibility: p.visibility,
  sound: p.sound_speed,
})));
```

---

*Part of the SuperInstance fleet ecosystem. Built by Forgemaster ⚒️*
