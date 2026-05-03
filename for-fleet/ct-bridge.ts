/**
 * @superinstance/constraint-theory — TypeScript bridge to constraint-theory Python package
 * 
 * Spawns Python subprocess, sends JSON commands, returns parsed results.
 * Requires: Python 3.8+, constraint-theory package (pip install constraint-theory)
 * 
 * Designed by Forgemaster ⚒️ for fleet agent integration
 */

import { spawn, ChildProcess } from 'child_process';
import { EventEmitter } from 'events';

// ── Types ─────────────────────────────────────────────────────

export interface Variable {
  name: string;
  domain: number[];
}

export interface Constraint {
  type: 'all_different' | 'equal' | 'not_equal' | 'less_than' | 'greater_than' | 'custom';
  variables: string[];
  expression?: string; // For custom constraints, e.g. "x + y == z"
}

export interface SolveRequest {
  cmd: 'solve';
  variables: Record<string, number[]>;
  constraints: Constraint[];
  options?: {
    max_solutions?: number;
    timeout_ms?: number;
    method?: 'backtracking' | 'arc_consistency' | 'forward_checking';
  };
}

export interface SolveResult {
  status: 'solved' | 'unsatisfiable' | 'timeout';
  solutions: Record<string, number>[];
  solve_time_ms: number;
  nodes_explored: number;
}

export interface PropagateRequest {
  cmd: 'propagate';
  variables: Record<string, number[]>;
  constraints: Constraint[];
}

export interface PropagateResult {
  status: 'consistent' | 'inconsistent';
  reduced_domains: Record<string, number[]>;
  domains_reduced: number;
}

export interface VersionRequest {
  cmd: 'version';
}

export type CTRequest = SolveRequest | PropagateRequest | VersionRequest;
export type CTResult = SolveResult | PropagateResult | { version: string };

// ── Python Bridge ─────────────────────────────────────────────

const PYTHON_SCRIPT = `
import sys
import json

try:
    from constraint_theory import CSP, Solver
except ImportError:
    print(json.dumps({"error": "constraint-theory not installed. pip install constraint-theory"}))
    sys.exit(1)

def solve(req):
    variables = req.get("variables", {})
    constraints = req.get("constraints", [])
    options = req.get("options", {})
    
    solver = Solver()
    
    # Add variables and domains
    for name, domain in variables.items():
        solver.add_variable(name, domain)
    
    # Add constraints
    for c in constraints:
        ctype = c.get("type")
        cvars = c.get("variables", [])
        if ctype == "all_different":
            solver.add_constraint(cvars, "all_different")
        elif ctype == "equal":
            solver.add_constraint(cvars, "equal")
        elif ctype == "not_equal":
            solver.add_constraint(cvars, "not_equal")
        elif ctype == "less_than":
            solver.add_constraint(cvars, "less_than")
        elif ctype == "greater_than":
            solver.add_constraint(cvars, "greater_than")
        elif ctype == "custom" and c.get("expression"):
            solver.add_constraint(cvars, c["expression"])
    
    max_sol = options.get("max_solutions", 10)
    timeout = options.get("timeout_ms", 30000) / 1000.0
    
    solutions = solver.solve(max_solutions=max_sol, timeout=timeout)
    
    return {
        "status": "solved" if solutions else "unsatisfiable",
        "solutions": solutions,
        "solve_time_ms": solver.solve_time * 1000,
        "nodes_explored": solver.nodes_explored
    }

def propagate(req):
    variables = req.get("variables", {})
    constraints = req.get("constraints", [])
    
    solver = Solver()
    for name, domain in variables.items():
        solver.add_variable(name, domain)
    for c in constraints:
        ctype = c.get("type")
        cvars = c.get("variables", [])
        solver.add_constraint(cvars, ctype)
    
    result = solver.propagate()
    
    return {
        "status": "consistent" if result.consistent else "inconsistent",
        "reduced_domains": result.domains,
        "domains_reduced": result.reduced_count
    }

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        req = json.loads(line)
        cmd = req.get("cmd")
        if cmd == "solve":
            result = solve(req)
        elif cmd == "propagate":
            result = propagate(req)
        elif cmd == "version":
            from constraint_theory import __version__
            result = {"version": __version__}
        else:
            result = {"error": f"Unknown command: {cmd}"}
        print(json.dumps(result), flush=True)
    except Exception as e:
        print(json.dumps({"error": str(e)}), flush=True)
`;

export class ConstraintTheoryBridge extends EventEmitter {
  private process: ChildProcess | null = null;
  private buffer: string = '';
  private pending: {
    resolve: (value: CTResult) => void;
    reject: (reason: Error) => void;
  } | null = null;
  private pythonPath: string;

  constructor(pythonPath: string = 'python3') {
    super();
    this.pythonPath = pythonPath;
  }

  async start(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.process = spawn(this.pythonPath, ['-c', PYTHON_SCRIPT], {
        stdio: ['pipe', 'pipe', 'pipe'],
      });

      this.process.stdout!.on('data', (data: Buffer) => {
        this.buffer += data.toString();
        this.processBuffer();
      });

      this.process.stderr!.on('data', (data: Buffer) => {
        this.emit('error', new Error(`Python stderr: ${data.toString()}`));
      });

      this.process.on('error', (err: Error) => {
        reject(err);
      });

      this.process.on('close', (code: number) => {
        this.emit('close', code);
        if (this.pending) {
          this.pending.reject(new Error(`Process exited with code ${code}`));
          this.pending = null;
        }
      });

      // Wait a beat for process to start
      setTimeout(resolve, 100);
    });
  }

  private processBuffer(): void {
    const lines = this.buffer.split('\n');
    this.buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.trim() || !this.pending) continue;
      try {
        const result = JSON.parse(line);
        if (result.error) {
          this.pending.reject(new Error(result.error));
        } else {
          this.pending.resolve(result);
        }
        this.pending = null;
      } catch {
        // Skip malformed lines
      }
    }
  }

  async execute<T extends CTResult>(request: CTRequest): Promise<T> {
    if (!this.process?.stdin) {
      throw new Error('Bridge not started. Call start() first.');
    }

    return new Promise((resolve, reject) => {
      this.pending = { resolve, reject };
      this.process!.stdin!.write(JSON.stringify(request) + '\n');

      // Timeout
      const timeout = request.cmd === 'solve' 
        ? (request as SolveRequest).options?.timeout_ms || 30000
        : 10000;
      
      setTimeout(() => {
        if (this.pending) {
          this.pending.reject(new Error(`Timeout after ${timeout}ms`));
          this.pending = null;
        }
      }, timeout);
    });
  }

  async stop(): Promise<void> {
    if (this.process) {
      this.process.kill();
      this.process = null;
    }
  }
}

// ── Convenience API ───────────────────────────────────────────

export class ConstraintTheory {
  private bridge: ConstraintTheoryBridge;

  constructor(pythonPath: string = 'python3') {
    this.bridge = new ConstraintTheoryBridge(pythonPath);
  }

  async start(): Promise<void> {
    await this.bridge.start();
  }

  async solve(
    variables: Record<string, number[]>,
    constraints: Constraint[],
    options?: SolveRequest['options']
  ): Promise<SolveResult> {
    return this.bridge.execute<SolveResult>({
      cmd: 'solve',
      variables,
      constraints,
      options,
    });
  }

  async propagate(
    variables: Record<string, number[]>,
    constraints: Constraint[]
  ): Promise<PropagateResult> {
    return this.bridge.execute<PropagateResult>({
      cmd: 'propagate',
      variables,
      constraints,
    });
  }

  async version(): Promise<string> {
    const result = await this.bridge.execute<{ version: string }>({ cmd: 'version' });
    return result.version;
  }

  async stop(): Promise<void> {
    await this.bridge.stop();
  }
}

// ── Demo ──────────────────────────────────────────────────────

async function demo() {
  const ct = new ConstraintTheory();
  await ct.start();

  console.log('Constraint Theory Bridge Demo');
  console.log('Version:', await ct.version());

  // Solve a simple Sudoku row
  const result = await ct.solve(
    { // Variables with domains 1-9
      v1: [1,2,3,4,5,6,7,8,9],
      v2: [1,2,3,4,5,6,7,8,9],
      v3: [1,2,3,4,5,6,7,8,9],
      v4: [1,2,3,4,5,6,7,8,9],
    },
    [
      { type: 'all_different', variables: ['v1','v2','v3','v4'] },
      { type: 'less_than', variables: ['v1','v4'] },
    ],
    { max_solutions: 5, timeout_ms: 5000 }
  );

  console.log('Solve result:', JSON.stringify(result, null, 2));

  // Arc consistency propagation
  const prop = await ct.propagate(
    { x: [1,2,3,4,5], y: [3,4,5,6,7], z: [1,2,3,4,5,6,7] },
    [
      { type: 'less_than', variables: ['x', 'y'] },
      { type: 'all_different', variables: ['x', 'y', 'z'] },
    ]
  );

  console.log('Propagation:', JSON.stringify(prop, null, 2));

  await ct.stop();
}

// Run demo if executed directly
if (typeof require !== 'undefined' && require.main === module) {
  demo().catch(console.error);
}
