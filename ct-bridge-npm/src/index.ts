import { PythonBridge, BridgeError } from "./python-bridge.js";
import type { FLUXBytecode } from "./flux-types.js";

// ── Public types ─────────────────────────────────────────────

/** A CSP variable identifier. */
export type Variable = string;

/** Domain: explicit set of allowed values, or range spec. */
export type Domain =
  | { type: "set"; values: number[] }
  | { type: "range"; min: number; max: number }
  | { type: "range_step"; min: number; max: number; step: number };

/** Constraint: a boolean predicate over variables. */
export interface Constraint {
  id: string;
  variables: Variable[];
  expression: string; // Python expression, e.g. "x + y == 10"
}

/** Solver method. */
export type SolveMethod = "backtracking" | "forward_checking" | "arc_consistency" | "min_conflicts";

/** A solution: variable → value mapping. */
export interface Solution {
  assignments: Record<Variable, number>;
  consistent: boolean;
  solveTimeMs: number;
}

/** Verification result. */
export interface VerificationResult {
  valid: boolean;
  violations: string[]; // constraint ids that failed
  checkedCount: number;
}

// ── Options ──────────────────────────────────────────────────

export interface CTBridgeOptions {
  pythonPath?: string;
  callTimeout?: number;
  maxRestarts?: number;
}

// ── CTBridge ─────────────────────────────────────────────────

/**
 * Main entry point. Wraps the Python `constraint-theory` package
 * for Node.js via a persistent subprocess bridge.
 */
export class CTBridge {
  private bridge: PythonBridge;

  constructor(private readonly options: CTBridgeOptions = {}) {
    this.bridge = new PythonBridge({
      pythonPath: options.pythonPath,
      callTimeout: options.callTimeout,
      maxRestarts: options.maxRestarts,
    });
  }

  /** Start the underlying Python process. Call once before solve/compile/verify. */
  async init(): Promise<void> {
    await this.bridge.start();
  }

  /** Shut down the Python process. */
  destroy(): void {
    this.bridge.stop();
  }

  /**
   * Solve a CSP.
   *
   * @param variables - Variable names.
   * @param domains - Map of variable → domain.
   * @param constraints - Constraint predicates.
   * @param method - Solver strategy. Default: "backtracking".
   */
  async solve(
    variables: Variable[],
    domains: Record<Variable, Domain>,
    constraints: Constraint[],
    method: SolveMethod = "backtracking",
  ): Promise<Solution> {
    const result = (await this.bridge.call("solve", {
      variables,
      domains,
      constraints,
      method,
    })) as Record<string, unknown>;

    return {
      assignments: (result.assignments ?? {}) as Record<Variable, number>,
      consistent: (result.consistent ?? false) as boolean,
      solveTimeMs: (result.solve_time_ms ?? 0) as number,
    };
  }

  /**
   * Compile a CSP to FLUX bytecode.
   *
   * @param problem - Full problem spec with variables, domains, constraints.
   * @returns FLUX bytecode with instruction list and metadata.
   */
  async compile(problem: {
    variables: Variable[];
    domains: Record<Variable, Domain>;
    constraints: Constraint[];
    method?: SolveMethod;
  }): Promise<FLUXBytecode> {
    const result = (await this.bridge.call("compile", {
      variables: problem.variables,
      domains: problem.domains,
      constraints: problem.constraints,
      method: problem.method ?? "backtracking",
    })) as Record<string, unknown>;

    return {
      instructions: (result.instructions ?? []) as FLUXBytecode["instructions"],
      variableMap: (result.variable_map ?? {}) as Record<string, number>,
      constraintOffsets: (result.constraint_offsets ?? {}) as Record<string, number>,
      count: (result.count ?? 0) as number,
      sourceHash: (result.source_hash ?? "") as string,
    };
  }

  /**
   * Verify that a solution satisfies all constraints.
   *
   * @param solution - Variable → value mapping.
   * @param constraints - Constraints to check.
   */
  async verify(
    solution: Record<Variable, number>,
    constraints: Constraint[],
  ): Promise<VerificationResult> {
    const result = (await this.bridge.call("verify", {
      solution,
      constraints,
    })) as Record<string, unknown>;

    return {
      valid: (result.valid ?? false) as boolean,
      violations: (result.violations ?? []) as string[],
      checkedCount: (result.checked_count ?? 0) as number,
    };
  }

  /** Check if the bridge process is alive. */
  get isAlive(): boolean {
    return this.bridge.isRunning;
  }
}

// Re-export for convenience.
export { PythonBridge, BridgeError } from "./python-bridge.js";
export { FluxOpcode } from "./flux-types.js";
export type { FluxInstruction, FLUXBytecode as FLUXBytecodeType } from "./flux-types.js";
