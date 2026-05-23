// FLUX-C Constraint Checker — Formal Verification Model
// Simplified for SymbiYosys formal proofs

`define OP_HALT     8'h1A
`define OP_ASSERT   8'h1B
`define OP_RANGE    8'h1D
`define OP_BOOL_AND 8'h26
`define OP_BOOL_OR  8'h27

module flux_checker_sby #(
    parameter int MAX_GAS       = 1024,
    parameter int STACK_DEPTH   = 64,
    parameter int DATA_WIDTH    = 256
)(
    input  wire             clk,
    input  wire             rst,

    // Instruction stream (driven by formal or testbench)
    input  wire [7:0]       opcode,
    input  wire [DATA_WIDTH-1:0] imm,      // immediate operand
    input  wire [DATA_WIDTH-1:0] lo_val,   // RANGE lower bound
    input  wire [DATA_WIDTH-1:0] hi_val,   // RANGE upper bound
    input  wire             instr_valid,

    // Outputs
    output reg              pass,
    output reg              fault,
    output reg              halted,
    output reg [15:0]       gas_used
);

    // ── Stack ──────────────────────────────────────────────
    reg [DATA_WIDTH-1:0] stack [0:STACK_DEPTH-1];
    reg [$clog2(STACK_DEPTH+1)-1:0] sp;   // stack pointer (next free slot)

    // ── Bounded model assumptions ──────────────────────────
    // Constrain inputs so formal doesn't explore impossible states
    wire [DATA_WIDTH-1:0] stack_top    = (sp > 0) ? stack[sp-1] : {DATA_WIDTH{1'b0}};
    wire [DATA_WIDTH-1:0] stack_second = (sp > 1) ? stack[sp-2] : {DATA_WIDTH{1'b0}};

    // ── Main execution ────────────────────────────────────
    always @(posedge clk) begin
        if (rst) begin
            sp       <= 0;
            pass     <= 0;
            fault    <= 0;
            halted   <= 0;
            gas_used <= 0;
        end else if (!halted && instr_valid && (gas_used < MAX_GAS)) begin
            gas_used <= gas_used + 1;

            case (opcode)
                // ── HALT ──────────────────────────────────
                `OP_HALT: begin
                    halted <= 1'b1;
                    // pass = no faults occurred
                    pass   <= ~fault;
                end

                // ── ASSERT ────────────────────────────────
                // Pops top of stack; if zero → fault
                `OP_ASSERT: begin
                    if (sp > 0) begin
                        if (stack_top == 0)
                            fault <= 1'b1;
                        sp <= sp - 1;
                    end else begin
                        fault <= 1'b1;  // stack underflow
                    end
                end

                // ── RANGE(lo, hi) ─────────────────────────
                // Checks if imm is within [lo_val, hi_val].
                // Pushes 1 if in range, 0 otherwise.
                `OP_RANGE: begin
                    if (lo_val <= hi_val) begin
                        // Normal range: push 1 if in range
                        stack[sp] <= (imm >= lo_val && imm <= hi_val)
                                     ? {DATA_WIDTH{1'b1}}
                                     : {DATA_WIDTH{1'b0}};
                    end else begin
                        // Inverted range: always fault
                        fault     <= 1'b1;
                        stack[sp] <= {DATA_WIDTH{1'b0}};
                    end
                    sp <= sp + 1;
                end

                // ── BOOL_AND ──────────────────────────────
                // Pops two, pushes (a AND b)
                `OP_BOOL_AND: begin
                    if (sp >= 2) begin
                        stack[sp-2] <= (stack_top != 0 && stack_second != 0)
                                       ? {DATA_WIDTH{1'b1}}
                                       : {DATA_WIDTH{1'b0}};
                        sp <= sp - 1;
                    end else begin
                        fault <= 1'b1;
                    end
                end

                // ── BOOL_OR ───────────────────────────────
                // Pops two, pushes (a OR b)
                `OP_BOOL_OR: begin
                    if (sp >= 2) begin
                        stack[sp-2] <= (stack_top != 0 || stack_second != 0)
                                       ? {DATA_WIDTH{1'b1}}
                                       : {DATA_WIDTH{1'b0}};
                        sp <= sp - 1;
                    end else begin
                        fault <= 1'b1;
                    end
                end

                default: ; // NOP
            endcase
        end
    end

    // ════════════════════════════════════════════════════════
    //  Formal Properties
    // ════════════════════════════════════════════════════════

    // P1: Gas never exceeds MAX_GAS
    assert property (@(posedge clk) gas_used <= MAX_GAS)
        else $error("P1 FAIL: gas_used exceeded MAX_GAS");

    // P2: Stack pointer never overflows
    assert property (@(posedge clk) sp < STACK_DEPTH)
        else $error("P2 FAIL: stack pointer overflow");

    // P3: Stack pointer never underflows (unsigned, so < is impossible —
    //     we check sp == 0 when trying to pop)
    assert property (@(posedge clk)
        disable iff (rst)
        (opcode == `OP_ASSERT && instr_valid && !halted) |-> (sp > 0 || fault))
        else $error("P3 FAIL: stack underflow without fault");

    // P4: Once halted, stays halted
    assert property (@(posedge clk)
        disable iff (rst)
        halted |=> halted)
        else $error("P4 FAIL: halted de-asserted after set");

    // P5: RANGE with lo <= hi pushes 1 for in-range values
    assert property (@(posedge clk)
        disable iff (rst)
        (opcode == `OP_RANGE && instr_valid && !halted &&
         lo_val <= hi_val && imm >= lo_val && imm <= hi_val &&
         gas_used < MAX_GAS && sp + 1 < STACK_DEPTH)
        |=> stack[sp-1] != 0)
        else $error("P5 FAIL: RANGE in-range didn't push 1");

    // P6: BOOL_AND(1,1) = 1
    assert property (@(posedge clk)
        disable iff (rst)
        (opcode == `OP_BOOL_AND && instr_valid && !halted &&
         sp >= 2 && stack_top != 0 && stack_second != 0 &&
         gas_used < MAX_GAS)
        |=> stack[sp] != 0)
        else $error("P6a FAIL: BOOL_AND(1,1) != 1");

    // P6b: BOOL_AND(0,1) = 0
    assert property (@(posedge clk)
        disable iff (rst)
        (opcode == `OP_BOOL_AND && instr_valid && !halted &&
         sp >= 2 && (stack_top == 0) && stack_second != 0 &&
         gas_used < MAX_GAS)
        |=> stack[sp] == 0)
        else $error("P6b FAIL: BOOL_AND(0,1) != 0");

    // ── Cover properties ───────────────────────────────────

    // C1: pass = 1 is reachable
    cover property (@(posedge clk) pass == 1'b1);

    // C2: fault = 1 is reachable
    cover property (@(posedge clk) fault == 1'b1);

endmodule
