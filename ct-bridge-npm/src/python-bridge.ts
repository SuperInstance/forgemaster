import { spawn, ChildProcess } from "child_process";
import { EventEmitter } from "events";

/** JSON-RPC style request envelope. */
interface JsonRpcRequest {
  jsonrpc: "2.0";
  id: number;
  method: string;
  params: Record<string, unknown>;
}

/** JSON-RPC style response envelope. */
interface JsonRpcResponse {
  jsonrpc: "2.0";
  id: number;
  result?: unknown;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
}

export interface PythonBridgeOptions {
  /** Path to python binary. Default: "python3". */
  pythonPath?: string;
  /** Maximum restart attempts before giving up. Default: 3. */
  maxRestarts?: number;
  /** Timeout in ms for each call. Default: 30000. */
  callTimeout?: number;
  /** Custom PYTHONPATH. */
  pythonPathEnv?: string;
}

/**
 * Manages a persistent Python subprocess for constraint-theory calls.
 * Communicates via JSON-RPC over stdin/stdout.
 */
export class PythonBridge extends EventEmitter {
  private proc: ChildProcess | null = null;
  private nextId = 1;
  private pending = new Map<
    number,
    { resolve: (v: unknown) => void; reject: (e: Error) => void; timer: ReturnType<typeof setTimeout> }
  >();
  private buffer = "";
  private restartCount = 0;
  private opts: Required<Pick<PythonBridgeOptions, "pythonPath" | "maxRestarts" | "callTimeout">> &
    Pick<PythonBridgeOptions, "pythonPathEnv">;

  constructor(private readonly options: PythonBridgeOptions = {}) {
    super();
    this.opts = {
      pythonPath: options.pythonPath ?? "python3",
      maxRestarts: options.maxRestarts ?? 3,
      callTimeout: options.callTimeout ?? 30_000,
      pythonPathEnv: options.pythonPathEnv,
    };
  }

  /** Start the Python subprocess. */
  async start(): Promise<void> {
    if (this.proc && !this.proc.killed) return;

    const env = { ...process.env };
    if (this.opts.pythonPathEnv) {
      env.PYTHONPATH = this.opts.pythonPathEnv;
    }

    this.proc = spawn(
      this.opts.pythonPath,
      ["-m", "constraint_theory.bridge", "--jsonrpc"],
      {
        stdio: ["pipe", "pipe", "pipe"],
        env,
      },
    );

    this.proc.stdout!.on("data", (chunk: Buffer) => this.onStdout(chunk));
    this.proc.stderr!.on("data", (chunk: Buffer) => {
      const msg = chunk.toString().trim();
      if (msg) this.emit("stderr", msg);
    });

    this.proc.on("exit", (code, signal) => {
      this.emit("exit", { code, signal });
      // Reject all pending calls.
      for (const [id, p] of this.pending) {
        clearTimeout(p.timer);
        p.reject(new Error(`Python process exited (code=${code}, signal=${signal})`));
        this.pending.delete(id);
      }
      this.proc = null;
      // Auto-restart if within limits.
      if (this.restartCount < this.opts.maxRestarts) {
        this.restartCount++;
        this.emit("restarting", this.restartCount);
        this.start().catch(() => {});
      }
    });

    // Wait for ready signal.
    await new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error("Python bridge startup timeout")), 10_000);
      const onStderr = (msg: string) => {
        if (msg.includes("READY")) {
          clearTimeout(timeout);
          this.removeListener("stderr", onStderr);
          resolve();
        }
      };
      this.on("stderr", onStderr);
      this.once("exit", () => {
        clearTimeout(timeout);
        this.removeListener("stderr", onStderr);
        reject(new Error("Python process died during startup. Is constraint-theory installed?"));
      });
    });

    this.restartCount = 0;
  }

  /** Send a JSON-RPC call and return the result. */
  async call(method: string, params: Record<string, unknown> = {}): Promise<unknown> {
    if (!this.proc || this.proc.killed) {
      await this.start();
    }

    const id = this.nextId++;
    const request: JsonRpcRequest = { jsonrpc: "2.0", id, method, params };

    return new Promise<unknown>((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Call timeout: ${method} (id=${id})`));
      }, this.opts.callTimeout);

      this.pending.set(id, { resolve, reject, timer });

      const payload = JSON.stringify(request) + "\n";
      this.proc!.stdin!.write(payload, (err) => {
        if (err) {
          clearTimeout(timer);
          this.pending.delete(id);
          reject(new Error(`Write error: ${err.message}`));
        }
      });
    });
  }

  /** Kill the Python subprocess. */
  stop(): void {
    if (this.proc && !this.proc.killed) {
      this.proc.kill("SIGTERM");
      this.proc = null;
    }
    for (const [, p] of this.pending) {
      clearTimeout(p.timer);
      p.reject(new Error("Bridge stopped"));
    }
    this.pending.clear();
  }

  /** Check if the subprocess is alive. */
  get isRunning(): boolean {
    return this.proc !== null && !this.proc.killed;
  }

  private onStdout(chunk: Buffer): void {
    this.buffer += chunk.toString();
    const lines = this.buffer.split("\n");
    this.buffer = lines.pop()!; // keep incomplete line

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const resp: JsonRpcResponse = JSON.parse(trimmed);
        const pending = this.pending.get(resp.id);
        if (pending) {
          clearTimeout(pending.timer);
          this.pending.delete(resp.id);
          if (resp.error) {
            pending.reject(new BridgeError(resp.error.code, resp.error.message, resp.error.data));
          } else {
            pending.resolve(resp.result);
          }
        }
      } catch {
        this.emit("unparseable", trimmed);
      }
    }
  }
}

/** Error thrown when the Python bridge returns an error response. */
export class BridgeError extends Error {
  constructor(
    public readonly code: number,
    message: string,
    public readonly data?: unknown,
  ) {
    super(message);
    this.name = "BridgeError";
  }
}
