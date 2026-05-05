# GUARD Constraint DSL Tutorial
The **GUARD Constraint DSL** is a CHIPS Alliance open-source declarative language for specifying and enforcing state, temporal, security, and safety constraints on embedded systems, RTL hardware, and cloud-native services. It compiles to runtime checkers, SystemVerilog assertions, test harnesses, and policy enforcement code.

---

## Prerequisites
Install the official GUARD compiler via Rust's Cargo:
```bash
cargo install guard-compiler
# Verify installation
guardc --version # Should print v1.0.0+
```

---

## Core Tutorial Sections
### 1. Syntax Basics: Exact Matches, Ranges, and Domains
All constraints are **named predicates** over system state variables. Basic value checks use three core patterns:
| Pattern | Syntax Example | Description |
|---------|----------------|-------------|
| Exact Match | `power_state == ON` or shorthand `power_state ON` (after type annotations) | Checks if a variable exactly matches a permitted value |
| Range Check | `temp_c >= 0°C && temp_c <= 125°C` or shorthand `temp_c 0°C .. 125°C` | Validates numeric variables fall within an inclusive range |
| Domain Check | `uart_baud in [9600, 19200, 115200]` | Ensures a variable is one of a fixed set of allowed values |

#### Syntax Rules
- Comments use `//` (line) or `/* */` (block)
- Variable names start with a letter, and can include letters, numbers, and underscores
- Physical units (e.g., `°C`, `mV`, `%`) are optional syntactic sugar for numeric values

---

### 2. Logical Combinators
Combine constraints with standard boolean operators (precedence: `NOT` > `AND` > `OR`, use parentheses for grouping):
| Operator | Shorthand |
|----------|-----------|
| AND | `&&` / `and` |
| OR | `||` / `or` |
| NOT | `!` / `not` |
| Implication | `->` / `IMPLIES` (A → B: if A is true, B must also be true) |

---

### 3. Temporal Constraints
Add time/sequence context for hardware/real-time systems. All temporal constraints require a declared clock variable (`type clk: clock`):
1.  **`WITHIN n CYCLES`**: Predicate must be true at least once in the next `n` cycles
2.  **`STABLE FOR n CYCLES`**: Predicate must remain true for `n` consecutive cycles
3.  **`DEADLINE n CYCLES`**: Trigger predicate → consequent predicate must be true within `n` cycles

---

### 4. Security Constraints
Enforce least-privilege access and sandboxing:
1.  **`REQUIRES <capability>`**: The current execution context must possess the named security capability to trigger the constraint
2.  **`SANDBOX <component> allows <var1, var2...>`**: Restricts a component to only access the listed variables

---

### 5. Groups and Metadata
Organize constraints into reusable groups and add metadata for compliance and prioritization:
- Declare groups with `group <name>: { ... constraints ... }`
- Annotations start with `@`:
  - `@priority(level)`: Sets enforcement priority (1 = critical, 5 = low)
  - `@safety(category)`: Tags compliance with safety standards (e.g., `ASIL_B` for automotive ISO 26262)

---

### 6. Type Annotations
Define variable types to enable compile-time validation and shorthand syntax. Supported types:
| Type | Example | Description |
|------|---------|-------------|
| Primitives | `int32`, `bool`, `float32` | Standard numeric/boolean types |
| Enums | `enum { OFF, ON, FAULT }` | Fixed set of named values |
| Bitmasks | `bitmask(8)` | N-bit unsigned bitfield |
| Custom Aliases | `type voltage = int16` | Reusable type shortcuts |

---

### 7. Compilation Targets
The `guardc` compiler generates code for 4 core workflows:
1.  **Runtime Enforcement**: C/Rust/eBPF functions for software runtime checks
2.  **RTL Assertions**: SystemVerilog/Verilog properties for hardware simulation
3.  **Test Harnesses**: UVM/Python testbenches to generate constraint-compliant/violating test cases
4.  **Policy Modules**: Linux Security Module (LSM) or seccomp sandbox rules

#### Common Compilation Commands
```bash
# Generate C runtime checkers
guardc compile --target c my_constraints.guard -o output_checkers.c

# Generate SystemVerilog assertions
guardc compile --target systemverilog my_constraints.guard -o output_assertions.sv

# Export intermediate representation (IR) for debugging
guardc compile --emit-ir my_constraints.guard -o output_ir.json
```

---

### 8. Debugging
#### Common Errors
| Error Message | Fix |
|---------------|-----|
| `variable 'foo' not declared` | Add a type annotation for `foo` |
| `temporal operator requires clock variable` | Declare `type clk: clock` at the top of your file |
| `type mismatch: cannot compare int32 to enum` | Use valid values for the variable's declared type |
| `duplicate constraint name` | Rename one of the conflicting constraints |

#### IR Output Example
The emitted JSON IR shows the fully parsed, validated constraints for debugging:
```json
{
  "version": "1.0.0",
  "constraints": [
    {
      "name": "valid_temp_range",
      "predicate": {"op": "<=", "left": {"var": "temp_c"}, "right": {"value": 125, "unit": "°C"}},
      "metadata": {},
      "temporal": null
    }
  ],
  "types": {"temp_c": "int32"}
}
```

---

## 10 Hands-On Worked Examples
Each example includes full input GUARD code, a compilation command, and sample generated output.

---

### Example 1: Exact Match Constraint (Section 1)
**Input**:
```guard
// Example 1: Exact Match Power State Constraint
type power_state: enum { OFF, ON, FAULT }
type power_good: bool

constraint power_good_when_on: power_state == ON IMPLIES power_good == HIGH
```
**Compilation Command**:
```bash
guardc compile --target c example1.guard -o example1_check.c
guardc compile --target systemverilog example1.guard -o example1_asserts.sv
```
**Generated Output**:
1.  C Runtime:
    ```c
    bool check_power_good_when_on(enum power_state power_state, bool power_good) {
      return !(power_state == ON && power_good == false);
    }
    ```
2.  SystemVerilog:
    ```systemverilog
    always_comb assert (power_state == ON -> power_good == 1'b1)
      else $error("Constraint violated: power_good_when_on");
    ```

---

### Example 2: Range Check (Section 1)
**Input**:
```guard
// Example 2: Temperature Range Constraint
type temp_c: int32

constraint valid_temp_range: temp_c -40°C .. 125°C
```
**Compilation Command**: Same as Example 1
**Generated Output**:
1.  C Runtime:
    ```c
    bool check_valid_temp_range(int32_t temp_c) {
      return (temp_c >= -40 && temp_c <= 125);
    }
    ```
2.  SystemVerilog:
    ```systemverilog
    always_comb assert (temp_c >= -40 && temp_c <= 125)
      else $error("Constraint violated: valid_temp_range");
    ```

---

### Example 3: Domain Check (Section 1)
**Input**:
```guard
// Example 3: Allowed UART Baud Rates
type uart_baud: enum { 9600, 19200, 38400, 115200 }

constraint allowed_baud_rates: uart_baud in [9600, 19200, 115200]
```
**Generated Output**:
1.  C Runtime:
    ```c
    bool check_allowed_baud_rates(enum uart_baud uart_baud) {
      return uart_baud == 9600 || uart_baud == 19200 || uart_baud == 115200;
    }
    ```
2.  SystemVerilog:
    ```systemverilog
    always_comb assert (uart_baud inside {9600, 19200, 115200})
      else $error("Constraint violated: allowed_baud_rates");
    ```

---

### Example 4: Logical Combinators (Section 2)
**Input**:
```guard
// Example 4: Combined Warning Conditions
type temp_c: int32
type fan_on: bool
type fault_flag: uint8

constraint warning_condition: (temp_c > 60°C && fan_on == LOW) || (fault_flag & 0x01 != 0)
```
**Generated Output**:
1.  C Runtime:
    ```c
    bool check_warning_condition(int32_t temp_c, bool fan_on, uint8_t fault_flag) {
      return ((temp_c > 60 && !fan_on) || ((fault_flag & 0x01) != 0));
    }
    ```
2.  SystemVerilog:
    ```systemverilog
    always_comb assert ( (temp_c > 60 && fan_on == 1'b0) || (fault_flag & 8'h01) != 0 )
      else $error("Constraint violated: warning_condition");
    ```

---

### Example 5: Temporal `WITHIN n CYCLES` (Section 3)
**Input**:
```guard
// Example 5: UART TX Ready Within 5 Cycles
type clk: clock
type uart_tx_ready: bool

constraint tx_ready_within_cycles: WITHIN 5 CYCLES uart_tx_ready == HIGH
```
**Generated Output**:
1.  C Runtime (software timer ticks):
    ```c
    bool check_tx_ready_within_cycles(bool uart_tx_ready, uint32_t tick_count) {
      static uint32_t last_tick = 0;
      if (uart_tx_ready) { last_tick = tick_count; return true; }
      return (tick_count - last_tick) <= 5;
    }
    ```
2.  SystemVerilog:
    ```systemverilog
    property tx_ready_within_cycles;
      @(posedge clk) eventually [0:5] uart_tx_ready == 1'b1;
    endproperty
    assert property(tx_ready_within_cycles) else $error("tx_ready_within_cycles violated");
    ```

---

### Example 6: Temporal `STABLE FOR n CYCLES` (Section 3)
**Input**:
```guard
// Example 6: Overtemperature Stable for 3 Cycles
type clk: clock
type temp_c: int32

constraint overtemperature_shutdown: temp_c > 100°C STABLE FOR 3 CYCLES
```
**Generated Output**:
1.  C Runtime:
    ```c
    bool check_overtemperature_shutdown(int32_t temp_c, uint32_t tick_count) {
      static uint32_t stable_ticks = 0;
      if (temp_c > 100) { stable_ticks++; return stable_ticks >=3; }
      else { stable_ticks = 0; return false; }
    }
    ```
2.  SystemVerilog:
    ```systemverilog
    property overtemperature_shutdown;
      @(posedge clk) (temp_c > 100) [*3];
    endproperty
    assert property(overtemperature_shutdown) else $error("overtemperature_shutdown violated");
    ```

---

### Example 7: Temporal `DEADLINE n CYCLES` (Section 3)
**Input**:
```guard
// Example 7: UART TX Deadline Constraint
type clk: clock
type uart_tx_enable: bool
type uart_tx_ready: bool

constraint tx_deadline: uart_tx_enable == HIGH -> DEADLINE 10 CYCLES uart_tx_ready == HIGH
```
**Generated Output**:
1.  C Runtime:
    ```c
    bool check_tx_deadline(bool uart_tx_enable, bool uart_tx_ready, uint32_t tick_count) {
      static uint32_t enable_tick = 0;
      if (uart_tx_enable) { enable_tick = tick_count; return true; }
      if (uart_tx_ready) { return true; }
      return (tick_count - enable_tick) <=10;
    }
    ```
2.  SystemVerilog:
    ```systemverilog
    property tx_deadline;
      @(posedge clk) (uart_tx_enable == 1'b1) |-> eventually [0:10] uart_tx_ready == 1'b1;
    endproperty
    assert property(tx_deadline) else $error("tx_deadline violated");
    ```

---

### Example 8: Security Constraints (Section 4)
**Input**:
```guard
// Example 8: Flash Write Security Rules
type flash_write_enabled: bool

constraint flash_write_permissions: REQUIRES FLASH_WRITE_CAP WHEN flash_write_enabled == HIGH
SANDBOX uart_component allows uart_rx_data, uart_baud_select
```
**Generated Output**:
1.  eBPF Capability Check:
    ```c
    int bpf_check_flash_write_permissions(bool flash_write_enabled, u32 caps) {
      if (flash_write_enabled && !(caps & (1 << FLASH_WRITE_CAP))) return -EPERM;
      return 0;
    }
    ```
2.  Seccomp Sandbox Rule: Restricts `uart_component` to only access `uart_rx_data` and `uart_baud_select`

---

### Example 9: Groups and Metadata (Section 5)
**Input**:
```guard
// Example 9: Grouped Motor Safety Constraints
type temp_c: int32
type current_ma: uint32
type motor_enabled: bool

group motor_safety_constraints:
  @priority(1)
  @safety(ASIL_B)
  {
    constraint overtemp: temp_c <= 100°C
    constraint overcurrent: current_ma <= 5000
    constraint motor_enabled_only_when_safe: motor_enabled IMPLIES (temp_c <= 80°C && current_ma <= 4000)
  }

@priority(2)
constraint fan_control: fan_speed > 0% WHEN temp_c > 60°C
```
**Generated Output**:
1.  C Runtime Grouped Check:
    ```c
    bool check_motor_safety_constraints(int32_t temp_c, uint32_t current_ma, bool motor_enabled) {
      bool ok1 = (temp_c <= 100);
      bool ok2 = (current_ma <= 5000);
      bool ok3 = !(motor_enabled && (temp_c >80 || current_ma >4000));
      return ok1 && ok2 && ok3;
    }
    bool check_fan_control(int32_t temp_c, int32_t fan_speed) {
      return !(temp_c >60 && fan_speed <=0);
    }
    ```
2.  Compliance Report: Includes priority and ASIL_B metadata for regulatory audits

---

### Example 10: Type Annotations (Section 6)
**Input**:
```guard
// Example 10: Type-Annotated Battery Constraints
// Define custom types
type status_code: enum { OK, WARNING, FAULT }
type control_word: bitmask(16)
type sensor_reading: int16

// Annotate variables
type battery_voltage: sensor_reading
type error_status: status_code
type device_control: control_word

// Constraints using type shorthand
constraint battery_voltage_ok: battery_voltage >= 3000mV && battery_voltage <= 4200mV
constraint valid_error_status: error_status in [OK, WARNING, FAULT]
constraint valid_control_bits: (device_control & 0b1111000000000000) == 0
```
**Generated Output**:
1.  Type-Safe C Runtime:
    ```c
    bool check_battery_voltage_ok(int16_t battery_voltage) {
      return (battery_voltage >= 3000 && battery_voltage <= 4200);
    }
    bool check_valid_error_status(enum status_code error_status) {
      return error_status == OK || error_status == WARNING || error_status == FAULT;
    }
    bool check_valid_control_bits(uint16_t device_control) {
      return ((device_control & 0xF000) == 0);
    }
    ```
2.  Compile-Time Validation: Catches invalid code like `error_status == 5` (5 is not a valid `status_code` enum value)
