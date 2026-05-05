---

## 1. `.github/ISSUE_TEMPLATE/bug_report.yml`
```yaml
name: Bug Report
about: Report a compiler bug (miscompilation, parser error, codegen bug, performance regression). For safety-critical issues, use the Safety Concern template.
title: "[BUG] "
labels: ["bug", "needs-triage"]
assignees: []
body:
  - type: dropdown
    id: bug_type
    attributes:
      label: Bug Type
      description: Select the category of bug you are reporting
      options:
        - Miscompilation (incorrect code generation leading to wrong program behavior)
        - Parser Error (valid code rejected, invalid code accepted, parser crash)
        - Codegen Bug (incorrect assembly/IR generation, invalid binary output)
        - Performance Regression (slower compile times, larger binary size, slower runtime performance)
        - Other
      default: 0
    validations:
      required: true
  - type: textarea
    id: summary
    attributes:
      label: Bug Summary
      description: A clear, concise description of the bug and its impact
    validations:
      required: true
  - type: textarea
    id: safety_context
    attributes:
      label: Safety-Critical Context
      description: Does this bug affect safety-critical functionality? Does it violate compliance with ISO 26262, IEC 61508, DO-178C, MISRA C/C++, or other safety standards? Explain the safety impact here.
    validations:
      required: true
  - type: textarea
    id: steps_to_reproduce
    attributes:
      label: Step-by-Step Reproduction
      description: Detailed steps to trigger the bug, including any compiler commands or workflows
    validations:
      required: true
  - type: textarea
    id: mre
    attributes:
      label: Minimal Reproducible Example (MRE)
      description: Attach or link to the smallest possible code snippet, compiler configuration, and test case that reproduces the bug. For parser/codegen bugs, include full source code. For performance regressions, include benchmark data.
      render: c
    validations:
      required: true
  - type: textarea
    id: compiler_env
    attributes:
      label: Compiler Environment
      description: Details about your setup
      value: |
        Compiler Version/Git Commit Hash: 
        Target Architecture/Host OS: 
        Optimization Level (O0/O1/O2/Os/Ofast): 
        Custom Safety/Compliance Flags:
    validations:
      required: true
  - type: textarea
    id: observed_behavior
    attributes:
      label: Observed Behavior
      description: What actually happened? Include error messages, binary output, crashes, or performance metrics
    validations:
      required: true
  - type: textarea
    id: expected_behavior
    attributes:
      label: Expected Behavior
      description: What did you expect to happen instead?
    validations:
      required: true
  - type: textarea
    id: additional_context
    attributes:
      label: Additional Context
      description: Logs, screenshots, related issues, audit trails, or other relevant information
```

---

## 2. `.github/ISSUE_TEMPLATE/feature_request.yml`
```yaml
name: Feature Request
about: Request a new feature (new constraint type, target platform, safety optimization, etc.)
title: "[FEATURE] "
labels: ["feature", "needs-triage"]
assignees: []
body:
  - type: dropdown
    id: feature_category
    attributes:
      label: Feature Category
      description: Select the type of feature you are requesting
      options:
        - New Safety Constraint Type (e.g. MISRA Rule, ISO C standard compliance check)
        - New Target Architecture/Platform Support
        - New Safety-Preserving Optimization Pass
        - New Safety Compliance Tooling (e.g. certification report generation, compliance auditing)
        - General Tooling Improvement (IDE integration, CI/CD wrappers)
        - Other
      default: 0
    validations:
      required: true
  - type: textarea
    id: summary
    attributes:
      label: Feature Summary
      description: A clear, concise description of the requested feature
    validations:
      required: true
  - type: textarea
    id: use_case
    attributes:
      label: Use Case & Stakeholder Value
      description: Explain who benefits from this feature, what problem it solves, and how it enables safety-critical development
    validations:
      required: true
  - type: textarea
    id: compliance_requirements
    attributes:
      label: Safety Compliance Requirements
      description: List all safety standards (ISO 26262, IEC 61508, DO-178C, MISRA, etc.) this feature must align with
    validations:
      required: true
  - type: textarea
    id: proposed_implementation
    attributes:
      label: Proposed Implementation Details (Optional)
      description: Suggested design, reference implementations, or standard specifications to guide development
  - type: input
    id: target_users
    attributes:
      label: Target Users/Teams
      description: Who will use this feature? (e.g. automotive embedded teams, aerospace engineers, internal dev teams)
    validations:
      required: true
  - type: textarea
    id: additional_context
    attributes:
      label: Additional Context
      description: Benchmarks, mockups, related issues, or other relevant information
```

---

## 3. `.github/ISSUE_TEMPLATE/safety_concern.yml`
```yaml
name: Safety Concern Report (CRITICAL)
about: Report a critical safety-related issue with the compiler. Only use this for issues that pose actual safety risk or compliance violations.
title: "[SAFETY CRITICAL] "
labels: ["critical", "safety", "needs-triage", "high-priority"]
assignees: []
body:
  - type: textarea
    id: summary
    attributes:
      label: Safety Concern Summary
      description: A clear, concise description of the safety issue and its potential impact
    validations:
      required: true
  - type: dropdown
    id: severity
    attributes:
      label: Severity Level (Aligned with IEC 61508/ISO 26262)
      description: Select the severity rating for this safety issue
      options:
        - Critical: Risk of death, serious injury, total system failure, or violation of mandatory safety regulations
        - High: Significant safety risk, potential for harm or non-compliance with critical safety requirements
        - Medium: Minor safety risk, limited impact on safety-critical functions
        - Low: No direct safety risk, but may affect compliance with non-mandatory safety standards
      default: 0
    validations:
      required: true
  - type: dropdown
    id: affected_standard
    attributes:
      label: Affected Safety Standard
      options:
        - ISO 26262 (Automotive Functional Safety)
        - IEC 61508 (General Industrial Functional Safety)
        - DO-178C (Aerospace Software)
        - MISRA C/C++ (Embedded Coding Standards)
        - Other (specify below)
      default: 0
    validations:
      required: true
  - type: input
    id: other_standard
    attributes:
      label: Other Safety Standard
      description: If you selected "Other", please specify the exact safety standard
  - type: dropdown
    id: affected_component
    attributes:
      label: Affected Compiler Component
      options:
        - Parser/Semantic Analyzer
        - Type Checker
        - Safety Constraint Solver
        - Code Generator
        - Optimizer
        - Build/Tooling Pipeline
        - Documentation/Compliance Reporting
        - Other
      default: 0
    validations:
      required: true
  - type: textarea
    id: steps_to_reproduce
    attributes:
      label: Step-by-Step Reproduction
      description: Detailed steps to trigger the safety issue
    validations:
      required: true
  - type: textarea
    id: mre
    attributes:
      label: Minimal Reproducible Example (MRE)
      description: Attach or link to the smallest code snippet that demonstrates the safety issue. This is required for triage.
      render: c
    validations:
      required: true
  - type: dropdown
    id: compliance_violation
    attributes:
      label: Does this issue violate existing safety compliance certifications?
      options:
        - Yes
        - No
        - Unknown
      default: 0
    validations:
      required: true
  - type: input
    id: affected_users
    attributes:
      label: Estimated Affected User/Project Count
      description: How many users or projects are impacted? (e.g. "All automotive users", "3 internal aerospace projects")
    validations:
      required: true
  - type: textarea
    id: workarounds
    attributes:
      label: Mitigation Workarounds
      description: Are there any known workarounds to avoid the safety issue?
  - type: textarea
    id: additional_context
    attributes:
      label: Additional Safety Context
      description: Audit logs, crash reports, compliance documentation, or other critical safety-related information
```

---

## 4. `.github/pull_request_template.md`
```markdown
# Pull Request Template

## PR Title Guidelines
Follow [Conventional Commits](https://www.conventionalcommits.org/) format:
`<type>(<scope>): <description>`
Examples:
- `fix(codegen): correct miscompilation of safety-critical integer constraints`
- `feat(constraints): add MISRA C Rule 10.1 compliance check`
- `docs: update ISO 26262 compliance documentation for v1.2.0`

---

## Description
Please include:
1. What problem this PR solves
2. Safety-critical considerations or risks introduced/mitigated
3. Links to related issues using `Fixes #XXXX`, `Relates to #XXXX`

---

## Mandatory Checklist
### 🧪 Testing
- [ ] Added unit tests for all new/modified safety-critical functionality
- [ ] Added integration tests for compiler compliance with safety standards
- [ ] All existing tests pass (run `make test-all` or project-specific test command)
- [ ] Tested the minimal reproducible example from the associated issue (if applicable)
- [ ] Verified no regressions in existing safety compliance checks

### 🔨 Build & Quality
- [ ] Compiles without new warnings using project strict build flags (`-Wall -Wextra -Werror -pedantic -fsanitize=address,undefined`)
- [ ] No new memory leaks or undefined behavior (validated with ASAN/UBSAN)
- [ ] Removed all debug print statements and unused code
- [ ] Followed the project's coding style guidelines

### 🛡️ Safety Impact Assessment
- [ ] Assessed safety risk level: `No Risk` / `Low Risk` / `Medium Risk` / `High Risk` / `Critical Risk`
- [ ] Documented safety impact and mitigation steps in this PR description
- [ ] Verified this change does not violate existing safety standards (MISRA, ISO 26262, etc.)
- [ ] Updated compliance documentation (certification reports, constraint lists, etc.) if needed

### 📝 Changelog & Documentation
- [ ] Added a clear entry to `CHANGELOG.md` following the project's format
- [ ] Updated user/developer documentation (CLI docs, compliance guides, target support)
- [ ] Added comments to complex or safety-critical code sections

### 🔗 Associated Work
- [ ] Linked all related issues and PRs using `Fixes #XXXX`, `Relates to #XXXX`
- [ ] Assigned appropriate reviewers for safety-critical changes

### 🧹 Self Review
- [ ] Performed a full self-review of all code changes
- [ ] Confirmed all new functions/variables have clear, descriptive names
```