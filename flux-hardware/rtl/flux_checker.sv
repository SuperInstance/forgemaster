// =============================================================================
// FLUX-C Constraint Checker VM — Synthesizable SystemVerilog
// =============================================================================
// Stack-based bytecode VM that evaluates FLUX-C constraint expressions.
// Opcodes: HALT, ASSERT, CHECK_DOMAIN, RANGE, BOOL_AND, BOOL_OR, DUP, SWAP.
// All other opcodes treated as NOP (pc increments by 1).
// =============================================================================

module flux_checker #(
    parameter int STACK_DEPTH = 64,
    parameter int ADDR_W      = 8,       // bytecode address width (256 entries)
    parameter int MAX_GAS     = 16'hFFFF // default gas budget
)(
    input  logic             clk,
    input  logic             rst_n,
    input  logic             start,
    input  logic [7:0]       bytecode [0:255], // instruction memory
    input  logic [31:0]      input_val,

    output logic             done,
    output logic             pass,
    output logic             fault,
    output logic [15:0]      gas_used
);

    // -------------------------------------------------------------------------
    // FSM states
    // -------------------------------------------------------------------------
    typedef enum logic [2:0] {
        S_IDLE    = 3'd0,
        S_FETCH   = 3'd1,
        S_DECODE  = 3'd2,
        S_EXECUTE = 3'd3,
        S_CHECK   = 3'd4   // CHECK_DONE
    } state_t;

    state_t state;

    // -------------------------------------------------------------------------
    // Opcodes
    // -------------------------------------------------------------------------
    localparam logic [7:0]
        OP_HALT         = 8'h1A,
        OP_ASSERT       = 8'h1B,
        OP_CHECK_DOMAIN = 8'h1C,
        OP_RANGE        = 8'h1D,
        OP_BOOL_AND     = 8'h26,
        OP_BOOL_OR      = 8'h27,
        OP_DUP          = 8'h28,
        OP_SWAP         = 8'h29;

    // -------------------------------------------------------------------------
    // Architectural registers
    // -------------------------------------------------------------------------
    logic [ADDR_W-1:0]  pc;
    logic [15:0]         gas;
    logic [31:0]         stack [0:STACK_DEPTH-1];
    logic [$clog2(STACK_DEPTH)-1:0] sp;  // stack pointer (next free slot)

    // Intermediate fetch / decode registers
    logic [7:0]  ir;          // instruction register
    logic [31:0] operand_a;
    logic [31:0] operand_b;
    logic [7:0]  imm_byte;    // immediate byte (mask / lo)
    logic [7:0]  imm_byte2;   // second immediate byte (hi)
    logic [31:0] result;
    logic        result_valid;

    // -------------------------------------------------------------------------
    // Stack helpers (combinational)
    // -------------------------------------------------------------------------
    // Top of stack is at stack[sp-1].  sp points to next free slot.

    function automatic logic [31:0] peek();
        return (sp == 0) ? 32'd0 : stack[sp - 1];
    endfunction

    function automatic logic [31:0] peek2();
        return (sp <= 1) ? 32'd0 : stack[sp - 2];
    endfunction

    // -------------------------------------------------------------------------
    // Output assignment
    // -------------------------------------------------------------------------
    assign gas_used = MAX_GAS - gas;  // gas consumed so far

    // -------------------------------------------------------------------------
    // Main sequential logic
    // -------------------------------------------------------------------------
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            // Reset
            state <= S_IDLE;
            pc    <= {ADDR_W{1'b0}};
            gas   <= MAX_GAS;
            sp    <= {$clog2(STACK_DEPTH){1'b0}};
            done  <= 1'b0;
            pass  <= 1'b0;
            fault <= 1'b0;
            ir    <= 8'd0;
            operand_a  <= 32'd0;
            operand_b  <= 32'd0;
            imm_byte   <= 8'd0;
            imm_byte2  <= 8'd0;
            result     <= 32'd0;
            result_valid <= 1'b0;
            for (int i = 0; i < STACK_DEPTH; i++)
                stack[i] <= 32'd0;
        end else begin
            case (state)
                // =============================================================
                // S_IDLE — wait for start signal
                // =============================================================
                S_IDLE: begin
                    done  <= 1'b0;
                    pass  <= 1'b0;
                    fault <= 1'b0;
                    if (start) begin
                        // Push input_val onto stack
                        stack[0] <= input_val;
                        sp       <= {$clog2(STACK_DEPTH){1'b1}} + 1'b1; // sp = 1
                        pc       <= {ADDR_W{1'b0}};
                        gas      <= MAX_GAS;
                        state    <= S_FETCH;
                    end
                end

                // =============================================================
                // S_FETCH — load instruction, decrement gas
                // =============================================================
                S_FETCH: begin
                    if (gas == 16'd0) begin
                        // Out of gas → fault
                        fault <= 1'b1;
                        done  <= 1'b1;
                        pass  <= 1'b0;
                        state <= S_IDLE;
                    end else begin
                        gas <= gas - 16'd1;
                        ir  <= bytecode[pc];
                        state <= S_DECODE;
                    end
                end

                // =============================================================
                // S_DECODE — read operands from stack / immediates
                // =============================================================
                S_DECODE: begin
                    result_valid <= 1'b0;

                    case (ir)
                        OP_ASSERT: begin
                            operand_a <= peek();
                        end

                        OP_CHECK_DOMAIN: begin
                            operand_a <= peek();
                            imm_byte  <= bytecode[pc + 8'd1]; // mask
                        end

                        OP_RANGE: begin
                            operand_a <= peek();
                            imm_byte  <= bytecode[pc + 8'd1]; // lo
                            imm_byte2 <= bytecode[pc + 8'd2]; // hi
                        end

                        OP_BOOL_AND,
                        OP_BOOL_OR: begin
                            operand_a <= peek2(); // a (deeper)
                            operand_b <= peek();  // b (top)
                        end

                        OP_DUP: begin
                            operand_a <= peek();
                        end

                        OP_SWAP: begin
                            operand_a <= peek();
                            operand_b <= peek2();
                        end

                        default: ; // NOP — no operands
                    endcase

                    state <= S_EXECUTE;
                end

                // =============================================================
                // S_EXECUTE — perform operation, update stack
                // =============================================================
                S_EXECUTE: begin
                    case (ir)
                        // -----------------------------------------------------
                        OP_HALT: begin
                            done  <= 1'b1;
                            pass  <= ~fault;
                            state <= S_IDLE;
                        end

                        // -----------------------------------------------------
                        OP_ASSERT: begin
                            if (operand_a == 32'd0)
                                fault <= 1'b1;
                            // Pop one element
                            if (sp > 0) begin
                                sp <= sp - 1'b1;
                                stack[sp - 1] <= 32'd0; // clear
                            end
                            pc    <= pc + 8'd1;
                            state <= S_CHECK;
                        end

                        // -----------------------------------------------------
                        OP_CHECK_DOMAIN: begin
                            // val & mask == val  →  all set bits in val are in mask
                            result = (operand_a & {24'd0, imm_byte}) == operand_a ? 32'd1 : 32'd0;
                            // Pop old top, push result
                            if (sp > 0)
                                stack[sp - 1] <= result;
                            pc    <= pc + 8'd2; // opcode + mask
                            state <= S_CHECK;
                        end

                        // -----------------------------------------------------
                        OP_RANGE: begin
                            // lo/hi are zero-extended to 32-bit for comparison
                            result = (operand_a >= {24'd0, imm_byte} &&
                                      operand_a <= {24'd0, imm_byte2}) ? 32'd1 : 32'd0;
                            // Pop old top, push result
                            if (sp > 0)
                                stack[sp - 1] <= result;
                            pc    <= pc + 8'd3; // opcode + lo + hi
                            state <= S_CHECK;
                        end

                        // -----------------------------------------------------
                        OP_BOOL_AND: begin
                            result = (operand_a != 32'd0 && operand_b != 32'd0) ? 32'd1 : 32'd0;
                            // Pop two, push result
                            if (sp > 1) begin
                                sp <= sp - 2'd1;
                                stack[sp - 2] <= result;
                                stack[sp - 1] <= 32'd0; // clear
                            end else if (sp == 1) begin
                                sp <= 1;
                                stack[0] <= result;
                            end
                            pc    <= pc + 8'd1;
                            state <= S_CHECK;
                        end

                        // -----------------------------------------------------
                        OP_BOOL_OR: begin
                            result = (operand_a != 32'd0 || operand_b != 32'd0) ? 32'd1 : 32'd0;
                            // Pop two, push result
                            if (sp > 1) begin
                                sp <= sp - 2'd1;
                                stack[sp - 2] <= result;
                                stack[sp - 1] <= 32'd0;
                            end else if (sp == 1) begin
                                sp <= 1;
                                stack[0] <= result;
                            end
                            pc    <= pc + 8'd1;
                            state <= S_CHECK;
                        end

                        // -----------------------------------------------------
                        OP_DUP: begin
                            // Push copy of TOS
                            if (sp < STACK_DEPTH) begin
                                stack[sp] <= operand_a;
                                sp <= sp + 1'b1;
                            end
                            pc    <= pc + 8'd1;
                            state <= S_CHECK;
                        end

                        // -----------------------------------------------------
                        OP_SWAP: begin
                            if (sp >= 2) begin
                                stack[sp - 1] <= operand_b; // old second
                                stack[sp - 2] <= operand_a; // old top
                            end
                            pc    <= pc + 8'd1;
                            state <= S_CHECK;
                        end

                        // -----------------------------------------------------
                        default: begin
                            // NOP — skip one byte
                            pc    <= pc + 8'd1;
                            state <= S_CHECK;
                        end
                    endcase
                end

                // =============================================================
                // S_CHECK — check done conditions, loop back
                // =============================================================
                S_CHECK: begin
                    if (done) begin
                        state <= S_IDLE;
                    end else if (gas == 16'd0) begin
                        fault <= 1'b1;
                        done  <= 1'b1;
                        pass  <= 1'b0;
                        state <= S_IDLE;
                    end else begin
                        state <= S_FETCH;
                    end
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
