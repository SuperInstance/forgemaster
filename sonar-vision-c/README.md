# SonarVision — Real-time Underwater Acoustic Physics Engine

**C99 + CUDA** implementation targeting Jetson Xavier (sm_72) for sensor-rate sonar array processing.

## Physics Models

### Sound Speed: Mackenzie 1981

Nine-term equation for sound speed in the oceans:

```
c = 1448.96 + 4.591T - 5.304e-2·T² + 2.374e-4·T³
    + 1.340(S-35) + 1.630e-2·D + 1.675e-7·D²
    - 1.025e-2·T(S-35) - 7.139e-13·T·D³
```

**Reference:** Mackenzie, K.V. (1981). "Nine-term equation for sound speed in the oceans." *J. Acoust. Soc. Am.* 70(3), 807–812.

**Valid ranges:** T = −2 to 30°C, S = 30–40 PSU, D = 0–12000 m  
**Accuracy:** ±0.07 m/s

### Absorption: Francois-Garrison 1982

Full three-relaxation model with pH dependency:

```
α = (A₁·f₁·f²)/(f²+f₁²) + (A₂·P₂·f₂·f²)/(f²+f₂²) + A₃·P₃·f²
```

- **f₁** — Boric acid relaxation (pH-dependent)
- **f₂** — Magnesium sulfate relaxation
- **A₃** — Pure water absorption

**References:**
- Francois, R.E. & Garrison, G.R. (1982). "Sound absorption based on ocean measurements: Part I & II." *J. Acoust. Soc. Am.* 72(6), 1879–1890.
- Erratum: *JASA* 73(3), 1983, p. 938.

**Valid ranges:** f = 0.4–1000 kHz, pH = 7–9

### Ray Tracing: Snell's Law

Acoustic ray tracing through layered medium with constant-gradient interpolation:

- Snell's law: cos(θ)/c = const along each ray
- Constant-gradient layers produce circular arc paths
- Surface and bottom reflections
- Shallow water and deep water modes

**Reference:** Jensen, F.B. et al. (2011). *Computational Ocean Acoustics.* Springer, 2nd ed., Ch. 2.

### Sonar Equation

```
SE = SL − TL − (NL − DI) + TS − DT
```

Detection probability via Rice (1944) model with standard-normal CDF approximation (Abramowitz & Stegun 26.2.17).

Range prediction by bisection search for SE = 0 crossing.

**References:**
- Urick, R.J. (1983). *Principles of Underwater Sound.* 3rd ed., McGraw-Hill.
- Rice, S.O. (1944). "Mathematical analysis of random noise." *Bell Syst. Tech. J.* 23, 282–332.

### Reverberation

- **Volume:** Scattering from biological/physical inhomogeneities
- **Surface:** Chapman-Harris model for wind-driven surface roughness
- **Bottom:** Lambert's law: BS(θ) = Bs·sin²θ

**Reference:** Urick (1983), Ch. 8–9.

## API Reference

### Sound Speed

```c
sv_error_t sv_mackenzie(double temp, double salinity, double depth, double *speed);
sv_error_t sv_mackenzie_batch(const double *temps, const double *sals,
                              const double *depths, double *out, int n);
```

### Absorption

```c
sv_error_t sv_absorption(double freq, double temp, double salinity,
                         double depth, double ph, double *alpha);
sv_error_t sv_absorption_batch(const double *freqs, const double *temps,
                               const double *sals, const double *depths,
                               const double *phs, double *out, int n);
```

### Ray Tracing

```c
sv_error_t sv_ray_trace(const sv_ssp_t *ssp, double src_depth,
                        double angle, double max_range,
                        sv_ray_mode_t mode, int max_bounces,
                        sv_ray_result_t *res);
```

### Sonar Equation

```c
sv_error_t sv_sonar_equation(const sv_sonar_params_t *p, double range,
                             sv_sonar_result_t *res);
```

### Reverberation

```c
sv_error_t sv_reverberation(sv_reverb_type_t type,
                            const sv_reverb_params_t *p,
                            double range, const sv_ssp_t *ssp,
                            double *rl);
```

### CUDA Batch API

```c
sv_error_t sv_cuda_create(int device_id, sv_cuda_ctx_t **ctx);
sv_error_t sv_cuda_destroy(sv_cuda_ctx_t *ctx);
sv_error_t sv_cuda_mackenzie(sv_cuda_ctx_t *ctx, ...);
sv_error_t sv_cuda_absorption(sv_cuda_ctx_t *ctx, ...);
sv_error_t sv_cuda_ray_trace(sv_cuda_ctx_t *ctx, ...);
```

## Building

### CPU-only (default)

```bash
make cpu        # libsonarvision.a + libsonarvision.so
make test       # build + run validation tests
```

### With CUDA (requires nvcc, Jetson Xavier or sm_72 GPU)

```bash
make all        # CPU + CUDA libraries
```

### Compiler Flags

| Flag | Purpose |
|------|---------|
| `-std=c99` | C99 compliance |
| `-O2` | Optimized |
| `-ffast-math` | Fast floating-point (no NaN/Inf checks) |
| `-march=native` | CPU-specific optimizations |
| `-arch=sm_72` | Jetson Xavier CUDA arch |

## Jetson Deployment Notes

### Xavier NX / AGX Xavier

- **GPU:** Volta (sm_72), 384–512 CUDA cores
- **Memory:** Unified (CPU/GPU share 8–32 GB)
- **Power modes:** 10W / 15W / 30W (MAXN)
- **Latency target:** <10 ms per sonar ping at sensor rate (10–30 Hz)

### Optimization Tips

1. **Use pinned memory** — `cudaMallocHost` for zero-copy on Jetson's unified memory
2. **Batch size ≥ 10K** — GPU overhead amortized at ≥10,240 points
3. **Stream overlap** — Pipeline compute/transfer with async streams
4. **Half precision** — Consider `__half` for 2× throughput on Volta tensor cores
5. **Constant cache** — Small SSPs (<4 KB) fit in CUDA constant cache

### Power/Thermal

- Monitor with `jtop` or `tegrastats`
- `nvpmodel -m 0` for MAXN mode (30W)
- `jetson_clocks` to maximize clocks

## File Structure

```
sonar-vision-c/
├── include/
│   └── sonar_vision.h          # Public C API
├── src/
│   ├── mackenzie.c             # Sound speed (Mackenzie 1981)
│   ├── francois_garrison.c     # Absorption (Francois-Garrison 1982)
│   ├── ray_trace.c             # Acoustic ray tracing
│   ├── sonar_equation.c        # Full sonar equation
│   ├── reverberation.c         # Reverberation models
│   └── version.c               # Version string
├── cuda/
│   ├── sonar_cuda.cu           # GPU kernels
│   └── host_api.cu             # Host-side CUDA interface
├── test/
│   └── test_physics.c          # Validation tests
├── Makefile
└── README.md
```

## Error Codes

| Code | Meaning |
|------|---------|
| `SV_OK` | Success |
| `SV_ERR_TEMP_RANGE` | Temperature outside −2..30°C |
| `SV_ERR_SAL_RANGE` | Salinity outside 30..40 PSU |
| `SV_ERR_DEPTH_RANGE` | Depth outside 0..12000 m |
| `SV_ERR_FREQ_RANGE` | Frequency outside 0.4..1000 kHz |
| `SV_ERR_PH_RANGE` | pH outside 7..9 |
| `SV_ERR_NULL_PTR` | NULL pointer argument |
| `SV_ERR_SIZE_ZERO` | Batch size = 0 |
| `SV_ERR_SSP_SHORT` | Sound-speed profile < 2 points |
| `SV_ERR_CUDA` | CUDA runtime error |
| `SV_ERR_PARAM` | Generic invalid parameter |

## License

MIT
