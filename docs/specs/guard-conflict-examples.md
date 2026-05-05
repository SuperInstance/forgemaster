# 10 Concrete GUARD DSL Constraint Conflict Resolution Examples
Each entry includes valid GUARD code, contextual explanation, and explicit compiler behavior aligned with the required syntax and use cases.

---

## Example 1: eVTOL Altitude Floor vs Emergency Landing Override
### GUARD Code
```guard
// Nominal flight: Hard minimum altitude for regular operation
@priority(HARD)
def nominal_altitude_min: current_altitude >= 100

// Emergency landing override: Relax altitude limit, explicitly replaces nominal rule
@priority(HARD)
@override(nominal_altitude_min)
def emergency_landing_min: current_altitude >= 0
```
### Explanation
Creates a direct conflict between the nominal hard 100ft altitude minimum and the emergency landing relaxed 0ft minimum. The `@override` annotation declares the emergency constraint supersedes the nominal rule when active (e.g., eVTOL system failure).
### Compiler Action
1.  **Non-emergency mode**: Only `nominal_altitude_min` is enforced, requiring altitude ≥100ft.
2.  **Emergency mode**: Detects conflicting HARD constraints, uses the explicit override to disable the nominal rule, and enforces `emergency_landing_min` to allow descent to 0ft.

---

## Example 2: Power Budget vs Minimum Compute Requirement
### GUARD Code
```guard
// Hard system-wide power budget cap (500W total)
@priority(HARD)
@conflict(policy=MERGE)
def system_power_budget: total_power_draw <= 500

// Hard minimum compute power for flight control; weakened automatically on conflict
@priority(HARD)
@weaken(new_lower_bound = max(compute_power_draw, 500 - auxiliary_power_draw))
def min_flight_compute: compute_power_draw >= 220
```
### Explanation
Conflict arises when the minimum flight compute power (220W) plus auxiliary system power (e.g., 300W) exceeds the 500W total budget. The `MERGE` policy resolves the overlap by adjusting constraints to fit within the budget.
### Compiler Action
1.  Detects the conflict between the two HARD constraints.
2.  Uses the `@weaken` annotation to lower `min_flight_compute`'s lower bound from 220W to 200W (500W - 300W auxiliary power).
3.  Enforces the adjusted constraint to keep total power within budget while meeting minimum viable compute requirements.

---

## Example 3: Temperature Limit vs Performance Target
### GUARD Code
```guard
// Hard safety temperature limit for avionics (85C max)
@priority(HARD)
@conflict(policy=FAIL_FIRST)
def avionics_temp_limit: avionics_stack_temp <= 85

// Soft performance target: 1000 ops/sec throughput; weakened on conflict
@priority(SOFT)
@weaken(new_lower_bound = calculate_max_throughput_for_temp(85))
def performance_target: throughput >= 1000
```
### Explanation
High system throughput increases avionics heat, pushing temperatures above the 85C hard limit. The `FAIL_FIRST` policy only triggers full failure if no soft constraint weakening is possible.
### Compiler Action
1.  Detects that `throughput >=1000` would exceed the avionics temperature limit.
2.  Uses the `@weaken` annotation to reduce the performance target's lower bound to the maximum throughput allowed under 85C (e.g., 750 ops/sec).
3.  Enforces the adjusted performance target to keep avionics within temperature limits without full system failure.

---

## Example 4: Redundant Cross-Sensor Altitude Constraints
### GUARD Code
```guard
// Redundant primary altimeter check: 100ft minimum altitude
@priority(HARD)
@conflict(policy=MERGE)
def primary_altitude_min: current_altitude >= 100

// Redundant secondary altimeter check: 120ft minimum altitude (conflicting bound)
@priority(HARD)
@conflict(policy=MERGE)
def secondary_altitude_min: current_altitude >= 120
```
### Explanation
Two redundant altitude checks have conflicting minimum bounds. The `MERGE` policy resolves overlapping/redundant constraints by enforcing the strictest compatible bound.
### Compiler Action
1.  Detects the conflicting HARD constraints.
2.  Applies the `MERGE` policy to select the higher minimum altitude (120ft), which satisfies both rules (≥120ft also meets ≥100ft).
3.  Enforces the merged constraint across both sensor systems for consistency.

---

## Example 5: Conflicting Activation Ranges from Two Safety Analyses
### GUARD Code
```guard
// Safety Analysis A: Throttle limit below 1000ft (max 80%)
@priority(HARD)
@conflict(policy=ESCALATE)
def safety_a_throttle_limit: (current_altitude < 1000) => (throttle_pct <= 80)

// Safety Analysis B: Conflicting throttle limit below 1000ft (max 70%)
@priority(HARD)
@conflict(policy=ESCALATE)
def safety_b_throttle_limit: (current_altitude < 1000) => (throttle_pct <= 70)
```
### Explanation
Two independent safety teams produced conflicting critical HARD throttle constraints for low-altitude flight. The `ESCALATE` policy skips automatic resolution and requires human intervention.
### Compiler Action
1.  Detects the conflicting HARD constraints with no automatic resolution path.
2.  Triggers the `ESCALATE` policy and raises a critical alert with both constraint bounds, notifying operators to resolve the safety analysis discrepancy before deployment.

---

## Example 6: Nested Constraint Groups (Layer Norms Within Global Bounds)
### GUARD Code
```guard
// Global hard temperature constraint for entire data center
@priority(HARD)
@conflict(policy=MERGE)
def global_data_center_temp: total_data_center_temp <= 85

// Nested group: Aisle 1 thermal constraints
@group(aisle_1_thermal) {
    // Aisle-specific soft rack temperature limit
    @priority(SOFT)
    def aisle1_rack_temp: rack_1_temp <= 70

    // Conflicting nested constraint: Exceeds global temperature limit
    @priority(SOFT)
    def aisle1_emergency_cooling: rack_1_temp <= 90
}

// Nested group: Aisle 2 thermal constraints
@group(aisle_2_thermal) {
    @priority(SOFT)
    def aisle2_rack_temp: rack_2_temp <= 70
}
```
### Explanation
The nested aisle 1 group has a constraint allowing rack temperatures up to 90F, which violates the global hard 85F data center limit. The compiler resolves the conflict by aligning the nested rule to the global bound.
### Compiler Action
1.  Detects the conflict between the global HARD constraint and the nested `aisle1_emergency_cooling` rule.
2.  Uses the `MERGE` policy to clamp the nested constraint's upper bound from 90F to 85F, aligning it with the global limit.
3.  Retains the `aisle1_rack_temp` rule at 70F as it complies with the updated global bound.

---

## Example 7: Runtime vs Compile-Time Conflict Detection
### GUARD Code
```guard
// Compile-time hard constraint: Component voltage rating (enforced pre-deployment)
@priority(HARD)
@constraint_type(COMPILE_TIME)
@conflict(policy=FAIL_FIRST)
def component_voltage_rating: supply_voltage <= 12

// Runtime soft constraint: Misconfigured operational limit (conflicts with compile-time rule)
@priority(SOFT)
@constraint_type(RUNTIME)
def operational_voltage_limit: supply_voltage <= 15
```
### Explanation
A misconfigured runtime voltage limit exceeds the component's hard compile-time voltage rating, creating a conflict. Compile-time constraints are validated pre-deployment to catch issues early.
### Compiler Action
1.  Runs pre-deployment validation for compile-time constraints.
2.  Detects the conflict between the HARD compile-time rule and SOFT runtime rule.
3.  Automatically weakens the runtime constraint's upper bound to 12V to match the compile-time limit, and alerts the operator to the misconfiguration. If the runtime constraint was marked HARD, deployment is blocked entirely.

---

## Example 8: Multi-Agent Constraint Merging (Two Autonomous Agents)
### GUARD Code
```guard
// Navigation agent: Hard minimum throttle to reach assigned waypoint
@priority(HARD)
@conflict(policy=MERGE)
def nav_min_throttle: throttle_pct >= 45

// Payload safety agent: Soft maximum throttle to prevent payload shift
@priority(SOFT)
@conflict(policy=MERGE)
def payload_max_throttle: throttle_pct <= 55
```
### Explanation
Two autonomous agents submit conflicting constraints: the navigation agent requires a minimum throttle to reach its waypoint, while the payload agent limits throttle to protect cargo. The `MERGE` policy resolves the conflict by aligning constraints to their overlapping valid range.
### Compiler Action
1.  Detects the conflict when the navigation agent requires 60% throttle (exceeding the payload's 55% limit).
2.  Prioritizes the HARD navigation constraint and weakens the SOFT payload constraint's upper bound to 100%, allowing the required throttle while preserving payload safety as much as possible.
3.  Enforces the adjusted constraints to satisfy both agents' requirements.

---

## Example 9: Constraint Versioning (v1 vs v2 of Same Constraint)
### GUARD Code
```guard
// Legacy v1.0.0 nominal altitude minimum constraint
@priority(HARD)
@version("v1.0.0")
def nominal_altitude_min: current_altitude >= 100

// Current v2.0.0 nominal altitude minimum constraint; explicitly overrides v1
@priority(HARD)
@version("v2.0.0")
@override(nominal_altitude_min)
def nominal_altitude_min_v2: current_altitude >= 120
```
### Explanation
Two versions of the same nominal altitude constraint exist with conflicting minimum bounds. The `@override` annotation declares the newer v2 constraint replaces the legacy v1 rule.
### Compiler Action
1.  Detects the version conflict between the two HARD constraints.
2.  Uses the explicit `@override` link to prioritize the v2.0.0 constraint, disabling the v1.0.0 rule entirely.
3.  Enforces the updated 120ft minimum altitude across all systems. If no override was specified, the compiler triggers the `ESCALATE` policy to alert operators to the version discrepancy.

---

## Example 10: Graceful Degradation (Weaken All SOFT Constraints Before Failing)
### GUARD Code
```guard
// Hard safety constraint: Battery charge must stay above 20%
@priority(HARD)
@conflict(policy=MERGE)
def min_battery_charge: battery_soc >= 20

// Soft performance constraint 1: Cruise speed ≥30 knots (weakened in 5kt steps)
@priority(SOFT)
@weaken(strategy=LOWER_BOUND, step_size=5)
def cruise_speed_min: cruise_speed >= 30

// Soft performance constraint 2: Cabin temperature 20-24C (weakened in 1C steps)
@priority(SOFT)
@weaken(strategy=RANGE, step_size=1)
def cabin_temp_range: cabin_temp between 20 and 24

// Soft performance constraint 3: Infotainment display active (lowest priority)
@priority(SOFT)
def infotainment_active: infotainment_power = true
```
### Explanation
Enforcing all soft performance constraints would drain battery power below the hard 20% limit. Graceful degradation weakens lowest-priority soft constraints first to resolve conflicts without full system failure.
### Compiler Action
1.  Detects that enforcing all three soft constraints would violate the `min_battery_charge` rule.
2.  First disables the lowest-priority `infotainment_active` constraint to save power.
3.  If battery levels remain too low, weakens the `cruise_speed_min` lower bound by 5kt to 25.
4.  If still needed, expands the `cabin_temp_range` from 20-24C to 18-26C.
5.  If all soft constraints are weakened and the conflict persists, triggers a critical failure alert.