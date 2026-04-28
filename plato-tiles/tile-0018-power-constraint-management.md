# GPU Power Constraint Management

**Core Concept:** GPU power constraints enforce maximum energy consumption to stay within hardware TDP (Thermal Design Power), supply limits, and battery capacity for mobile/edge devices. Power management balances performance against energy budgets.

**Power Limits:**

**GPU Power Specifications:**

| GPU | TDP (Typical) | Peak Power | Power Supply | Battery Life Impact |
|-----|--------------|------------|--------------|---------------------|
| RTX 4050 (Desktop) | 115W | 150W | PSU: 450W+ | N/A |
| RTX 4050 (Mobile) | 35-85W | 115W | Laptop PSU | 2-4 hours |
| Jetson Orin Nano | 7-15W | 25W | Battery/12V | 4-8 hours |
| Jetson Orin NX | 10-25W | 35W | Battery/12V | 3-6 hours |

**Power Components:**
- **GPU Core:** Computation power (dynamic)
- **VRAM:** Memory power (read/write)
- **Fans:** Cooling power (variable)
- **PCIe Interface:** Data transfer power
- **Display/Video:** Output power (if connected)

**Power Constraint Formulation:**

**Instantaneous Power:**
```
P_instant(t) ≤ P_TDP_max  ∀ t

Where:
P_instant(t) = current power draw
P_TDP_max = rated thermal design power
```

**Average Power (Battery Life):**
```
(1/T) ∫₀ᵀ P_instant(t) dt ≤ P_average_max

Ensures battery lasts for duration T
```

**Energy Budget:**
```
∫₀ᵀ P_instant(t) dt ≤ E_battery_total

Energy constraint for battery-powered devices
```

**Power Modeling:**

**GPU Power Draw:**
```
P_total = P_core + P_memory + P_fan + P_other

P_core = C_dyn * V² * f + P_leakage
P_memory = P_read * read_rate + P_write * write_rate
P_fan = K_fan * RPM³ (fan power ∝ speed³)
```

**Precision Power Impact:**

| Precision | Energy Per Operation | Throughput | Energy Efficiency |
|-----------|---------------------|------------|-------------------|
| FP32 | 1.0x (baseline) | 1.0x | 1.0x |
| TF32 | 0.75x | 2.0x | 2.67x |
| FP16 | 0.5x | 2.0x | 4.0x |
| INT8 | 0.25x | 4.0x | 16.0x |

**Conclusion:** Lower precision = dramatically better energy efficiency

**Adaptive Power Management:**

**1. Dynamic Power Capping:**
```
IF P_instant > P_warning THEN
    Reduce power limit by 10%
    Result: Immediate power reduction, slight performance drop
END IF
```

**2. Precision Scaling:**
```
IF P_instant > P_TDP_high THEN
    Switch: FP32 → TF32 → FP16 → INT8
    Result: 2-16x power reduction
END IF
```

**3. Frequency Scaling:**
```
IF battery_level < 20% THEN
    Reduce clock frequency to extend battery life
    Result: Linear power reduction
END IF
```

**4. Workload Scheduling:**
```
IF charging AND P_available > P_TDP THEN
    Run high-power kernels (FP32, full frequency)
ELSE IF discharging THEN
    Switch to low-power mode (FP16, reduced frequency)
END IF
```

**GPU Power Queries:**

**NVML:**
```cpp
unsigned int power_mw;
nvmlDeviceGetPowerUsage(device, &power_mw);  // Milliwatts
float power_watts = power_mw / 1000.0f;

unsigned int power_limit_mw;
nvmlDeviceGetPowerManagementLimit(device, &power_limit_mw);

nvmlDeviceSetPowerManagementLimit(device, new_limit_mw);
```

**Marine GPU Edge Power Controller:**

**Operational Modes:**

**Mode 1: Wall-Powered (Docked)**
- Power limit: 150W (full performance)
- Precision: FP32 preferred
- Frequency: Maximum
- Workload: All kernels

**Mode 2: Battery-Powered (Mobile)**
- Power limit: 50W (balanced)
- Precision: TF32 preferred
- Frequency: Reduced 20%
- Workload: Critical kernels only

**Mode 3: Emergency (Battery < 10%)**
- Power limit: 15W (minimal)
- Precision: FP16/INT8
- Frequency: Reduced 60%
- Workload: Safety-critical only (Kalman, constraints)

**Power-Aware Scheduling:**

**Task Power Budgeting:**
```python
def assign_power_budget(tasks, total_power_budget):
    """Distribute power budget across tasks"""
    remaining = total_power_budget
    budgets = {}

    for task in sorted(tasks, key=deadline):
        required = task.min_power
        optimal = task.optimal_power

        if remaining >= optimal:
            budgets[task.id] = optimal
            remaining -= optimal
        elif remaining >= required:
            budgets[task.id] = required
            remaining -= required
        else:
            # Defer task
            defer(task)

    return budgets
```

**Constraint Formulation:**
```
Variables: Power allocation to each kernel
Domains: [P_min, P_max] for each kernel
Constraints:
  - Σ P_i ≤ P_total (total power budget)
  - P_i ≥ P_required (minimum required power)
  - Throughput_i ≥ T_deadline_i (deadline constraints)
Objective: Maximize Σ throughput_i
```

**Real-Time Power Monitoring (Jetson Orin):**

**Sampling Rate:** 5 Hz (every 200 ms)
**Prediction:** Exponential moving average
**Action Threshold:** 5W margin below limit

**Jetson Power Rail Monitoring:**

| Power Rail | Voltage | Current | Monitoring |
|------------|---------|---------|------------|
| CPU | 0.8-1.2V | 0-30A | Yes |
| GPU | 0.6-1.0V | 0-20A | Yes |
| Memory | 1.1V | 0-5A | Yes |
| Fan | 5V | 0-2A | Yes |
| Total | 12V | 0-10A | Yes |

**Marine Environment Power:**

**Power Sources:**
- **Wall Power (Docked):** Unlimited, 120V AC → 12V DC converter
- **Battery (Undocked):** 12V Li-ion, 100-400 Wh
- **Solar:** Optional, trickle charging
- **Auxiliary:** Generator, wind turbine

**Power Challenges:**
- **Salt water corrosion:** Electrical connections degrade
- **Vibration:** Battery cells damaged over time
- **Temperature extremes:** Battery capacity varies ±20%

**Energy Budgeting Example:**

**Mission:** 8-hour autonomous patrol
**Battery:** 200 Wh (Jetson Orin NX)
**Safety reserve:** 20% (40 Wh)
**Usable energy:** 160 Wh

**Workload breakdown:**
- Sensor fusion: 5W × 8h = 40 Wh (25%)
- Constraint checking: 3W × 8h = 24 Wh (15%)
- Sonar processing: 15W × 4h = 60 Wh (37.5%)
- Display/UI: 2W × 8h = 16 Wh (10%)
- Overhead: 6W × 8h = 48 Wh (30% - oversubscribed!)

**Solution:** Reduce sonar processing time to 2 hours (30 Wh), increase constraint checking duty cycle.

**Constraint Theory Connection:**
Power constraints are resource constraints analogous to thermal constraints—the CSP framework handles both uniformly. Multi-objective optimization balances power vs. performance vs. accuracy.

**Provenance:** Forgemaster (power management)
**Chain:** Marine GPU Edge energy-aware scheduling
