# Flux Constraint Compiler: Developer Experience Design for Aerospace Engineers
This DX design is tailored explicitly for aerospace engineers proficient in C and MATLAB, who have no compiler internals experience, prioritize safety compliance (DO-178C, AS9100), and rely on existing toolchains. Every decision prioritizes familiarity, auditability, and minimal friction with their existing workflows.

---

## 1. Repo Structure (Opinionated, Audience-First)
The repo is structured to separate end-user tools, examples, and compiler code, so engineers can jump straight to working examples without wading through compiler internals:
```
flux/
├── .github/
│   ├── workflows/flux-check.yml # Reusable CI/CD workflow for teams
│   ├── ISSUE_TEMPLATE/ # Targeted templates for aerospace users
│   └── PULL_REQUEST_TEMPLATE/ # Separate templates for code, docs, and examples
├── install/ # Zero-friction installation tools
│   ├── install.sh # Linux/macOS one-line install script
│   ├── install.ps1 # Windows one-line install script
│   └── signed-checksums.txt # Verifiable pre-built binary hashes for air-gapped use
├── examples/ # Copy-paste ready use cases for aerospace workflows
│   ├── README.md # Overview of all examples
│   ├── c/wing_load/ # Constraint on aircraft wing mass struct
│   ├── c/control_law/ # Elevator angle range check (hello world)
│   ├── matlab/pid_controller/ # PID output limit constraints
│   └── simulink/flight_controls/ # Simulink block validation
├── ide/ # Native IDE integration for tools engineers already use
│   ├── vscode/ # VS Code extension with LSP and syntax highlighting
│   └── vim/ # Vim syntax highlighting
├── src/ # Rust compiler code (hidden from casual end users)
│   ├── cli/ # User-friendly command line interface
│   ├── c_parser/ # C macro and syntax parser
│   ├── matlab_parser/ # MATLAB comment constraint parser
│   ├── solver/ # Formal constraint solver (abstracted from users)
│   └── traceability/ # DO-178C/AS9100 compliance tooling
├── testsuite/ # Compiler's internal test suite
├── docs/ # Public website built with MkDocs (non-technical editable)
│   ├── docs/user-guide/compliance.md # Critical DO-178C guidance
│   └── mkdocs.yml
├── contrib/ # Community and contribution guidelines
│   ├── CONTRIBUTING.md # Split for engineers and compiler devs
│   ├── CODE_OF_CONDUCT.md # Adapted Contributor Covenant
│   └── GOVERNANCE.md # Stable, transparent project leadership
├── LICENSE # Apache 2.0 with patent grant (compliant for aerospace use)
├── CHANGELOG.md # Monthly stable release notes with LTS support
└── Cargo.toml # Rust crate manifest
```

---

## 2. README: First 30 Seconds of Onboarding
The top of the README is designed to be fully visible without scrolling, answering every critical question a new user has in 30 seconds:
1.  **Hero Banner**: `Flux: Constraint Checking for C and MATLAB, Built for Aerospace Engineers` with subtext: *Catch safety violations in flight code before they reach flight test—no compiler degree required.*
2.  **Quick Install Boxes** (side-by-side for different user groups):
    - For Rust-enabled workstations: `cargo install flux-compiler --locked`
    - For non-Rust users: `curl -sSL https://flux-lang.org/install.sh | sudo sh` (with a prominent note to read the script first for supply chain security)
    - Offline air-gapped install: Download pre-built tarballs from GitHub Releases, extract, and add to `PATH`
3.  **Core Value Props** (3 bullet points, no jargon):
    ✅ Write formal safety constraints using familiar C macros or MATLAB comments
    ✅ Catch violations automatically at compile time, before deployment
    ✅ Generate audit-ready reports for DO-178C and AS9100 compliance
4.  **Hello World Snippet** (copy-paste ready): The elevator angle control law example (see Section 3) with a one-click copy button
5.  **Quick Links**: Full getting started guide, examples repo, and compliance documentation

---

## 3. First Example: "Hello World" of Constraint Checking
The goal is to use code an aerospace engineer would write daily, with zero new syntax. We provide both C and MATLAB versions:
### C Example (Embedded Flight Controls)
```c
#include <flux.h>

// Formal constraint tied to DO-178C Table A-7, Requirement SW-HW-001
FLUX_FUNCTION_CONSTRAINT(
    elevator_angle >= -30.0f && elevator_angle <= 30.0f,
    "DO-178C SW-HW-001: Elevator angle must stay within +/-30 degrees"
);

// Standard flight control law function
float calculate_lift(float elevator_angle) {
    return 0.5f * 1.225f * 10.0f * elevator_angle * elevator_angle;
}

int main() {
    calculate_lift(45.0f); // Flux will catch this invalid input at compile time
    return 0;
}
```
### MATLAB Example (Simulink Workflow)
```matlab
% Formal constraint tied to the same DO-178C requirement
#flux: CONSTRAINT(elevator_angle >= -30 && elevator_angle <= 30, "DO-178C SW-HW-001")
function lift = calculate_lift(elevator_angle)
    lift = 0.5 * 1.225 * 10 * elevator_angle.^2;
end

% Flux will flag this invalid call when run via `flux check matlab/control_law.m`
calculate_lift(45);
```
Running `flux check` on this file will immediately catch the invalid 45-degree elevator input, with a compliance-focused error message (see Section 4).

---

## 4. Error Messages: Audit-Friendly, Context-Rich
Aerospace engineers need error messages that prove compliance, not just point to a bug. We contrast bad vs. good outputs:
### Bad Error Message (Generic Static Analyzer)
```
error: constraint check failed
--> src/control_law.c:45
```
This provides no context, no traceability, and forces engineers to dig for details.
### Good Error Message (Flux Standard Output)
```
🚨 FLIGHT SAFETY CONSTRAINT VIOLATED: DO-178C SW-HW-001
  --> src/fcs/control_law.c:45:25
   |
45 |     calculate_lift(45.0f);
   |                         ^^^^^^
   |
   ✅ Expected: elevator_angle ∈ [-30.0°, 30.0°]
   ❌ Actual: 45.0°
   📍 Constraint defined at: src/fcs/control_law.h:12
   📜 Traceability: Tied to AS9100 Rev D Clause 3.5.2 and DO-178C SW-HW-001
```
This includes every detail an auditor requires: violation type, exact code location, expected/actual values, constraint definition location, and compliance traceability links.

For solver errors (e.g., unsupported symbolic math), Flux provides plain-English guidance instead of compiler internals:
> `Error: Flux does not support symbolic division in constraints. Use a constant divisor instead (e.g. `x / 10` instead of `x / y`).`

---

## 5. IDE Integration: Work with Tools You Already Use
Flux integrates natively with the IDEs aerospace engineers rely on, with zero custom setup:
### VS Code Extension (Primary Target)
Published to the VS Code Marketplace as *Flux Constraint Checker*, with:
- Real-time linting as you type, so you catch errors before saving
- Syntax highlighting for Flux C macros and MATLAB comment directives
- Hover tooltips that show constraint traceability and compliance links
- One-click `Run Flux Check` right from the editor context menu
- Integration with the official MATLAB VS Code extension for Simulink and MATLAB files
### Cross-Editor LSP
A built-in Language Server Protocol server works with Neovim, Emacs, and Vim, so engineers using non-VS Code editors still get real-time feedback.
### Simulink Plugin
A lightweight plugin that lets you add constraints directly to Simulink block inputs/outputs, and run checks as part of the Simulink verification pipeline.

---

## 6. Debugging: No Compiler Internals Required
Aerospace engineers rarely need to debug the compiler itself, but when they do, Flux provides user-friendly debug tools that avoid jargon:
- **Verbose Mode**: `flux check --verbose` shows high-level constraint solving steps without dumping raw IR
- **Inspect Command**: `flux inspect src/control_law.c` lists all constraints in a file, their traceability IDs, and solver state
- **Debug Logs**: Persistent debug logs written to `~/.flux/debug.log` (customizable via `--log-file`) for bug reports
- **Traceability Mode**: `flux check --trace` shows every constraint being validated as the compiler processes your code, so you can debug why a valid constraint is being flagged incorrectly

All debug tools are optional—default output is clean and focused on user code, not compiler internals.

---

## 7. Testing: Validate Constraints for Compliance
Engineers need to prove that their safety constraints work as intended, so Flux includes built-in test tooling tailored to aerospace workflows:
### Writing Tests
Test files use familiar syntax for both C and MATLAB:
#### C Test File
```c
#include <flux.h>
#include <flux_test.h>

// Test that the elevator angle constraint catches invalid inputs
FLUX_TEST(test_elevator_too_high) {
    calculate_lift(45.0f); // Should fail constraint check
}

// Test that valid inputs pass the constraint
FLUX_TEST(test_elevator_ok) {
    calculate_lift(15.0f); // Should pass
}

int main() {
    FLUX_RUN_TESTS();
}
```
#### MATLAB Test File
```matlab
#flux: TEST(test_elevator_too_high)
function test_elevator_too_high()
    calculate_lift(45); % Should fail
end

#flux: TEST(test_elevator_ok)
function test_elevator_ok()
    calculate_lift(15); % Should pass
end

flux_run_tests();
```
### Test Features for Compliance
- **Coverage Reporting**: `flux test --coverage` generates a report showing which constraints were validated by tests, perfect for DO-178C audit trails
- **Strict Compliance Mode**: `flux test --strict` fails if any constraint is not covered by a test, ensuring 100% of safety constraints are validated
- **Integration with Existing Frameworks**: Works with Unity, CMocka (C), and MATLAB's built-in test harness, so you don't have to rewrite existing test suites

---

## 8. CI/CD: Auditable, Reusable Workflow
The included GitHub Actions workflow is tailored for aerospace teams, with compliance baked in:
```yaml
name: Flux Constraint Checks
on: [push, pull_request]

jobs:
  flux-compliance-check:
    runs-on: ubuntu-latest
    steps:
      - name: Check out code
        uses: actions/checkout@v4

      # Install Flux via official pre-built action (no manual setup)
      - name: Install Flux
        uses: flux-lang/action@v1
        with:
          version: latest

      # Run strict constraint checks on all C/MATLAB files
      - name: Run Flux Compliance Checks
        run: flux check --strict --recursive ./src ./matlab

      # Run all Flux tests and generate audit-ready coverage report
      - name: Run Flux Tests
        run: flux test --recursive ./tests

      # Enforce minimum test coverage for compliance (90% is standard for DO-178C)
      - name: Validate Constraint Test Coverage
        run: flux test --coverage-min 90

      # Upload coverage report for audit trails
      - name: Upload Compliance Report
        uses: actions/upload-artifact@v4
        with:
          name: flux-audit-report
          path: flux-coverage.xml
```
This workflow runs on every push and pull request, enforces compliance rules, and generates artifacts for internal and external audits.

---

## 9. Documentation Website: Structured for Aerospace Users
The public docs site (hosted at flux-lang.org) is organized to answer every question an aerospace engineer has, with a dedicated compliance section:
1.  **Home Page**: Same as the README, with a demo video of Flux in VS Code
2.  **Getting Started**: Step-by-step guide to installing Flux, adding your first constraint, and running checks
3.  **User Guide**:
    - C Integration: Macros, struct constraints, and traceability
    - MATLAB/Simulink Integration: Scripts, functions, and Simulink block validation
    - CLI Reference: All commands, flags, and compliance modes
    - Error Message Reference: Explanations and fixes for every Flux error
    - **Compliance Playbook**: Detailed guidance on using Flux for DO-178C, AS9100, and other aerospace standards
4.  **Troubleshooting**: Common issues like air-gapped installation, missing header files, and false positives
5.  **Contributing**: Link to the repo's contribution guidelines

The compliance playbook is a critical unique selling point: it includes sample audit reports, traceability best practices, and guidance on mapping Flux constraints to formal aerospace requirements.

---

## 10. Community & Contribution: Tailored for Aerospace Engineers
The project's community is focused on solving aerospace-specific problems, not general compiler development:
### CONTRIBUTING.md Split for Two Audiences
1.  **For Aerospace Engineers**: How to contribute examples, fix documentation, or request new compliance features (no Rust experience required)
2.  **For Compiler Devs**: How to build Flux from source, contribute to the solver, or add new language support
### Issue Templates
- **Bug Report**: Asks for Flux version, code sample, error message, and debug logs
- **Feature Request**: For new constraint types or IDE integration
- **Compliance Question**: Targeted for engineers asking about DO-178C or AS9100 mapping
- **Example Request**: For new aerospace-specific use cases (e.g., structural load constraints, fuel system limits)
### PR Templates
Separate templates for examples, documentation fixes, and code contributions, to streamline review for both engineers and compiler devs
### Community Channels
- Discord server with dedicated channels for C, MATLAB/Simulink, and compliance questions
- GitHub Discussions for Q&A and community support
- Monthly community calls for aerospace engineers using Flux to share best practices

---

## Core Design Principles
Every part of this DX is built on three non-negotiable rules for the target audience:
1.  **No Compiler Jargon**: Avoid terms like "IR", "solver backend", or "constraint zonotopes"—explain everything in plain English
2.  **Compliance First**: Every feature ties back to DO-178C and AS9100 requirements, from error messages to test coverage reports
3.  **Work With Existing Tools**: Flux integrates with C/MATLAB/Simulink toolchains, not replaces them, so engineers don't have to learn new workflows
4.  **Air-Gapped Friendly**: Offline installation, no external dependencies, and pre-built binaries for isolated aerospace systems