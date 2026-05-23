# GPU Thermal Constraint Management

**Core Concept:** GPU thermal constraints enforce maximum operating temperatures to prevent hardware damage, maintain performance stability, and ensure predictable behavior. Thermal management is a real-time constraint satisfaction problem balancing workload, power, and cooling.

**Thermal Limits:**

**NVIDIA GPU Temperature Ranges:**

| GPU | T_Junction Max | Throttling Begins | Critical Shutdown |
|-----|---------------|-------------------|-------------------|
| RTX 4050 (Ada) | 87°C | ~83°C | 95°C |
| Jetson Orin (ARM) | 100°C | ~85°C | 105°C |
| Typical Industrial | 105°C | ~90°C | 115°C |

**Temperature Sensors:**
- **GPU Core:** Main junction temperature
- **Memory (VRM):** VRAM temperature
- **Hotspot:** Hottest point on die (can exceed core by 10°C)
- **Ambient:** Case/enclosure temperature

**Thermal Constraint Formulation:**

**Constraint 1: Core Temperature**
```
T_core(t) ≤ T_junction_max  ∀ t

Where:
T_core(t) = current core temperature at time t
T_junction_max = 87°C (RTX 4050)
```

**Constraint 2: Temperature Derivative**
```
dT_core/dt ≤ ΔT_max_rate

Prevents rapid temperature spikes that could damage silicon
```

**Constraint 3: Average Temperature**
```
(1/τ) ∫₀ᵗ T_core(τ) dτ ≤ T_average_max

Prevents long-term overheating (degradation)
```

**Thermal Modeling:**

**Simple First-Order Model:**
```
dT_core/dt = (P_thermal * R_thermal) - (T_core - T_ambient) / C_thermal

Where:
P_thermal = power draw (Watts)
R_thermal = thermal resistance (K/W)
C_thermal = thermal capacitance (J/K)
T_ambient = ambient temperature
```

**GPU Power Draw:**
```
P_total = P_dynamic + P_static + P_memory + P_fan

P_dynamic = C * V² * f (switching power)
P_static = I_leakage * V (leakage current)
```

**Adaptive Thermal Management:**

**1. Precision Scaling:**
```
IF T_core > T_throttle_high THEN
    Switch: FP32 → TF32 → FP16
    Result: ~50% power reduction, acceptable accuracy loss
END IF
```

**2. Frequency Scaling:**
```
IF T_core > T_warning THEN
    Reduce clock frequency (MHz)
    Power ∝ frequency
    Result: Linear power reduction
END IF
```

**3. Workload Throttling:**
```
IF T_core > T_critical THEN
    Pause/defer non-critical kernels
    Run only safety-critical kernels (sensor fusion, constraints)
END IF
```

**4. Fan Speed Control:**
```
Fan_RPM = f(T_core, P_draw)

Lookup table:
- T < 70°C: Fan at 30%
- 70°C < T < 80°C: Fan at 50%
- T > 80°C: Fan at 100%
```

**GPU Thermal Queries:**

**NVML (NVIDIA Management Library):**
```cpp
#include <nvml.h>

nvmlDevice_t device;
nvmlDeviceGetHandleByIndex(0, &device);

unsigned int temp;
nvmlDeviceGetTemperature(device, NVML_TEMPERATURE_GPU, &temp);

unsigned int power;
nvmlDeviceGetPowerUsage(device, &power);  // Milliwatts

nvmlThermalSettings_t settings;
nvmlDeviceGetThermalSettings(device, NVML_THERMAL_GPU, &settings);
```

**CUDA Runtime:**
```cpp
int temp;
cudaDeviceGetAttribute(&temp, cudaDevAttrMaxTexture1DWidth, 0);
// Note: Limited thermal access in CUDA runtime; prefer NVML
```

**Marine GPU Edge Thermal Controller:**

**Controller State Machine:**
```
State: NORMAL (T < 70°C)
    - Run full workload
    - FP32 precision
    - Maximum frequency

    ↓ (T > 70°C)

State: THROTTLE_LOW (70°C < T < 80°C)
    - Run full workload
    - Switch to TF32 precision
    - Maintain frequency

    ↓ (T > 80°C)

State: THROTTLE_HIGH (80°C < T < 85°C)
    - Drop non-critical kernels
    - Switch to FP16 precision
    - Reduce frequency by 20%

    ↓ (T > 85°C)

State: CRITICAL (T > 85°C)
    - Only safety-critical kernels (Kalman, constraints)
    - Minimal precision required
    - Maximum frequency reduction
    - Alert operator

    ↓ (T < 75°C)

State: RECOVERY
    - Gradually restore workload
    - Ramp up precision and frequency
```

**Constraint-Aware Scheduling with Thermal:**

**Scoring Function Modification:**
```
S(task) = w_t * (1 - T_core / T_max)
        + w_p * (1 - P_draw / P_max)
        + w_m * (1 - memory_usage / M_max)
        + w_d * (deadline_buffer / deadline)
        + w_a * precision_match(task, hardware)
        + w_thermal * thermal_load(task, T_core)

Where:
thermal_load(task, T_core) = predicted_temp_rise * (T_core / T_max)²
```

**Real-Time Thermal Monitoring (RTX 4050):**

**Sampling Rate:** 10 Hz (every 100 ms)
**Prediction:** Linear extrapolation 1 second ahead
**Action Threshold:** 2°C margin below limits

**GPU Performance Impact:**

**No Throttling (T < 70°C):**
- 100% performance
- FP32: 15 TFLOPS
- TF32: 30 TFLOPS
- FP16: 60 TFLOPS

**Light Throttling (70°C < T < 80°C):**
- 90% performance
- Precision: TF32
- Minimal accuracy loss

**Heavy Throttling (80°C < T < 85°C):**
- 60% performance
- Precision: FP16
- Noticeable accuracy degradation

**Critical Mode (T > 85°C):**
- 30% performance
- Only safety kernels
- Accuracy trade-off acceptable for safety

**Marine Environment Considerations:**

**Ambient Temperature:**
- Tropics: 30-35°C ambient → Higher GPU temperature
- Arctic: -10°C ambient → Excellent cooling
- Enclosed bridge: Poor airflow → Higher temperatures

**Salt Spray:**
- Fan corrosion risk → Reduced cooling capacity
- Solution: Liquid cooling, sealed enclosures

**Vibration:**
- Mechanical fan wear → Thermal degradation over time
- Solution: Solid-state cooling (heat pipes, liquid)

**Constraint Theory Connection:**
Thermal constraints are hard resource constraints—no solution can exceed T_max. The thermal controller solves a dynamic CSP: maintain feasibility (T ≤ T_max) while maximizing performance (throughput, precision).

**Provenance:** Forgemaster (thermal management)
**Chain:** Marine GPU Edge adaptive thermal controller
