import { CTBridge } from "../src/index.js";
import type { Solution, VerificationResult } from "../src/index.js";

// ── Mock PythonBridge ────────────────────────────────────────

jest.mock("../src/python-bridge.js", () => {
  const { EventEmitter } = require("events");

  class MockPythonBridge extends EventEmitter {
    isRunning = true;
    start = jest.fn().mockImplementation(function (this: MockPythonBridge) {
      // Simulate READY on stderr after a tick
      process.nextTick(() => this.emit("stderr", "READY"));
      return Promise.resolve();
    });
    stop = jest.fn();
    call = jest.fn();
  }

  return { PythonBridge: MockPythonBridge, BridgeError: class extends Error { constructor(public code: number, m: string) { super(m); } } };
});

// ── Tests ────────────────────────────────────────────────────

describe("CTBridge", () => {
  let ct: CTBridge;

  beforeEach(() => {
    ct = new CTBridge();
  });

  afterEach(() => {
    ct.destroy();
  });

  test("init starts the bridge", async () => {
    await ct.init();
    expect(ct.isAlive).toBe(true);
  });

  test("solve returns a valid Solution", async () => {
    // Mock the bridge.call to return a fake solution
    const mockCall = (ct as any).bridge.call as jest.Mock;
    mockCall.mockResolvedValue({
      assignments: { x: 3, y: 7 },
      consistent: true,
      solve_time_ms: 12,
    });

    await ct.init();

    const result: Solution = await ct.solve(
      ["x", "y"],
      {
        x: { type: "range", min: 1, max: 10 },
        y: { type: "range", min: 1, max: 10 },
      },
      [{ id: "c1", variables: ["x", "y"], expression: "x + y == 10" }],
    );

    expect(result.assignments).toEqual({ x: 3, y: 7 });
    expect(result.consistent).toBe(true);
    expect(result.solveTimeMs).toBe(12);

    expect(mockCall).toHaveBeenCalledWith("solve", expect.objectContaining({
      method: "backtracking",
    }));
  });

  test("solve accepts explicit method", async () => {
    const mockCall = (ct as any).bridge.call as jest.Mock;
    mockCall.mockResolvedValue({
      assignments: {},
      consistent: false,
      solve_time_ms: 1,
    });

    await ct.init();

    await ct.solve(
      ["a"],
      { a: { type: "set", values: [1] } },
      [],
      "forward_checking",
    );

    expect(mockCall).toHaveBeenCalledWith("solve", expect.objectContaining({
      method: "forward_checking",
    }));
  });

  test("verify returns VerificationResult", async () => {
    const mockCall = (ct as any).bridge.call as jest.Mock;
    mockCall.mockResolvedValue({
      valid: true,
      violations: [],
      checked_count: 2,
    });

    await ct.init();

    const result: VerificationResult = await ct.verify(
      { x: 3, y: 7 },
      [{ id: "c1", variables: ["x", "y"], expression: "x + y == 10" }],
    );

    expect(result.valid).toBe(true);
    expect(result.violations).toEqual([]);
    expect(result.checkedCount).toBe(2);
  });

  test("verify detects violations", async () => {
    const mockCall = (ct as any).bridge.call as jest.Mock;
    mockCall.mockResolvedValue({
      valid: false,
      violations: ["c1"],
      checked_count: 1,
    });

    await ct.init();

    const result = await ct.verify(
      { x: 1, y: 1 },
      [{ id: "c1", variables: ["x", "y"], expression: "x + y == 10" }],
    );

    expect(result.valid).toBe(false);
    expect(result.violations).toContain("c1");
  });

  test("compile returns FLUXBytecode", async () => {
    const mockCall = (ct as any).bridge.call as jest.Mock;
    mockCall.mockResolvedValue({
      instructions: [
        { opcode: 0x10, operands: [1], label: "push_1" },
        { opcode: 0x15, operands: [0], label: "store_x" },
      ],
      variable_map: { x: 0, y: 1 },
      constraint_offsets: { c1: 2 },
      count: 2,
      source_hash: "abc123",
    });

    await ct.init();

    const bytecode = await ct.compile({
      variables: ["x", "y"],
      domains: {
        x: { type: "range", min: 1, max: 10 },
        y: { type: "range", min: 1, max: 10 },
      },
      constraints: [{ id: "c1", variables: ["x", "y"], expression: "x != y" }],
    });

    expect(bytecode.count).toBe(2);
    expect(bytecode.variableMap).toEqual({ x: 0, y: 1 });
    expect(bytecode.sourceHash).toBe("abc123");
  });

  test("destroy stops the bridge", async () => {
    await ct.init();
    expect(ct.isAlive).toBe(true);
    ct.destroy();
    expect((ct as any).bridge.stop).toHaveBeenCalled();
  });
});
