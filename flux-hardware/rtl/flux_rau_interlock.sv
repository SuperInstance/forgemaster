// =============================================================================
// flux_rau_interlock.sv
// FLUX Runtime Assurance Unit — AI Inference Output Interlock
//
// Sits between the AI accelerator and actuator outputs.  Every inference word
// is gated through NUM_CONSTRAINTS FLUX-C constraint programs before being
// forwarded.  A single failing check latches FAULT and drives the actuator to
// last-known-good until hard reset (rst_n).
//
// State machine:
//   IDLE → LOAD_BYTECODE → RUN_CONSTRAINT → CHECK_RESULT
//                ↑_____________________|           |
//                                                  ├─(pass, more)→ LOAD_BYTECODE
//                                                  ├─(pass, done)→ PASS_THROUGH → IDLE
//                                                  └─(fail)      → FAULT_STATE (latched)
//
// Target : Xilinx Artix-7 — portable RTL, zero vendor primitives
// Domain : single synchronous clock, active-low reset
// =============================================================================

`timescale 1ns / 1ps
`default_nettype none

module flux_rau_interlock (
    // ── Clock / Reset ────────────────────────────────────────────────────────
    input  wire        clk,
    input  wire        rst_n,

    // ── Inference input (from AI accelerator) ────────────────────────────────
    input  wire [63:0] inference_data,
    input  wire        inference_valid,
    output wire        inference_ready,

    // ── Actuator output (to actuator) ────────────────────────────────────────
    output reg  [63:0] actuator_data,
    output reg         actuator_valid,
    input  wire        actuator_ready,

    // ── FLUX-C bytecode memory interface (RAU is bus master) ─────────────────
    // RAU drives the address; the FLUX-C VM reads flux_bytecode_data directly
    // from the same memory in the instantiating netlist.
    output reg  [31:0] flux_bytecode_addr,
    input  wire [7:0]  flux_bytecode_data,  // externally routed to FLUX-C VM

    // ── FLUX-C VM control ─────────────────────────────────────────────────────
    output reg         flux_start,           // one-cycle start pulse
    input  wire        flux_done,            // VM asserts when program completes
    input  wire        flux_pass,            // 1 = constraint satisfied
    input  wire [7:0]  flux_fault_code,      // VM-supplied violation code

    // ── Fault reporting ───────────────────────────────────────────────────────
    output reg         fault,               // latched, cleared only by rst_n
    output reg  [7:0]  fault_code,

    // ── Audit counters (saturating at 2^32-1) ────────────────────────────────
    output reg  [31:0] checks_total,
    output reg  [31:0] checks_passed,
    output reg  [31:0] checks_failed
);

// =============================================================================
// Parameters
// =============================================================================

// Number of FLUX-C programs evaluated per inference word.
localparam integer NUM_CONSTRAINTS = 8;

// Base address of constraint bytecode table in program memory.
localparam [31:0] BYTECODE_BASE = 32'h0000_0000;

// Each constraint program occupies exactly 256 bytes (address stride = 2^8).
// Constraint k starts at: BYTECODE_BASE + (k << 8)
localparam integer BYTECODE_SHIFT = 8;

// Saturation ceiling for audit counters.
localparam [31:0] CNT_MAX = 32'hFFFF_FFFF;

// =============================================================================
// State encoding
// =============================================================================

localparam [2:0]
    IDLE            = 3'd0,
    LOAD_BYTECODE   = 3'd1,
    RUN_CONSTRAINT  = 3'd2,
    CHECK_RESULT    = 3'd3,
    PASS_THROUGH    = 3'd4,
    FAULT_STATE     = 3'd5;

// =============================================================================
// Internal registers
// =============================================================================

reg [2:0]  state;

// Snapshot of the inference word being checked — stable across all constraints.
reg [63:0] inference_buf;

// Last value successfully forwarded to the actuator (safe-state fallback).
reg [63:0] last_known_good;

// Which constraint is currently under evaluation (0..NUM_CONSTRAINTS-1).
// 4 bits supports up to 16 constraints.
reg [3:0]  constraint_idx;

// Tracks whether the one-cycle flux_start pulse has been issued this run.
reg        flux_started;

// =============================================================================
// inference_ready
// =============================================================================

// Back-pressure: accept a new inference word only when idle and not faulted.
assign inference_ready = (state == IDLE) && !fault;

// =============================================================================
// Saturating increment helper function
// =============================================================================

function automatic [31:0] sat_inc;
    input [31:0] v;
    sat_inc = (v == CNT_MAX) ? CNT_MAX : v + 32'h1;
endfunction

// =============================================================================
// Main FSM + datapath
// =============================================================================

always_ff @(posedge clk) begin
    if (!rst_n) begin
        // ── Synchronous reset ─────────────────────────────────────────────────
        state              <= IDLE;
        inference_buf      <= 64'h0;
        last_known_good    <= 64'h0;
        constraint_idx     <= 4'h0;
        flux_started       <= 1'b0;
        flux_bytecode_addr <= BYTECODE_BASE;
        flux_start         <= 1'b0;
        actuator_data      <= 64'h0;
        actuator_valid     <= 1'b0;
        fault              <= 1'b0;
        fault_code         <= 8'h0;
        checks_total       <= 32'h0;
        checks_passed      <= 32'h0;
        checks_failed      <= 32'h0;
    end else begin
        // Default: deassert all one-cycle pulses.
        flux_start <= 1'b0;

        case (state)

            // ──────────────────────────────────────────────────────────────────
            // IDLE
            // Wait for an inference word from the AI accelerator.
            // Latch the word and arm the constraint iterator.
            // ──────────────────────────────────────────────────────────────────
            IDLE: begin
                actuator_valid <= 1'b0;
                constraint_idx <= 4'h0;
                flux_started   <= 1'b0;

                if (inference_valid && !fault) begin
                    inference_buf      <= inference_data;
                    // Pre-load address for constraint 0.
                    flux_bytecode_addr <= BYTECODE_BASE;
                    state              <= LOAD_BYTECODE;
                end
            end

            // ──────────────────────────────────────────────────────────────────
            // LOAD_BYTECODE
            // Compute and register the byte-code start address for the current
            // constraint index.  One cycle is consumed here so the address is
            // stable before the VM is started.
            //   addr = BYTECODE_BASE + constraint_idx * 256
            //        = BYTECODE_BASE + {constraint_idx, 8'h00}
            // ──────────────────────────────────────────────────────────────────
            LOAD_BYTECODE: begin
                flux_started       <= 1'b0;
                flux_bytecode_addr <= BYTECODE_BASE +
                                      {20'h0, constraint_idx, 8'h0};
                state              <= RUN_CONSTRAINT;
            end

            // ──────────────────────────────────────────────────────────────────
            // RUN_CONSTRAINT
            // Issue a single-cycle flux_start pulse to the FLUX-C VM, then
            // wait for flux_done.  The guard on flux_started ensures the pulse
            // is issued exactly once regardless of how many cycles flux_done
            // takes to arrive.
            // ──────────────────────────────────────────────────────────────────
            RUN_CONSTRAINT: begin
                if (!flux_started) begin
                    flux_start   <= 1'b1;   // one-cycle pulse
                    flux_started <= 1'b1;
                end else if (flux_done) begin
                    flux_started <= 1'b0;
                    state        <= CHECK_RESULT;
                end
            end

            // ──────────────────────────────────────────────────────────────────
            // CHECK_RESULT
            // Evaluate the VM outcome.  On failure, latch fault immediately.
            // On success, either advance to the next constraint or pass through.
            // All counters saturate rather than wrap.
            // ──────────────────────────────────────────────────────────────────
            CHECK_RESULT: begin
                checks_total <= sat_inc(checks_total);

                if (!flux_pass) begin
                    // ── Constraint violated ──────────────────────────────────
                    checks_failed <= sat_inc(checks_failed);
                    fault         <= 1'b1;
                    fault_code    <= flux_fault_code;
                    state         <= FAULT_STATE;
                end else begin
                    // ── Constraint satisfied ─────────────────────────────────
                    checks_passed <= sat_inc(checks_passed);

                    if (constraint_idx == 4'(NUM_CONSTRAINTS - 1)) begin
                        // All NUM_CONSTRAINTS programs passed.
                        state <= PASS_THROUGH;
                    end else begin
                        // Advance to next constraint program.
                        constraint_idx <= constraint_idx + 4'h1;
                        state          <= LOAD_BYTECODE;
                    end
                end
            end

            // ──────────────────────────────────────────────────────────────────
            // PASS_THROUGH
            // All constraints satisfied.  Present buffered inference data to the
            // actuator and wait for the downstream ready handshake.
            // Latch last_known_good only after the actuator accepts.
            // ──────────────────────────────────────────────────────────────────
            PASS_THROUGH: begin
                actuator_data  <= inference_buf;
                actuator_valid <= 1'b1;

                if (actuator_ready) begin
                    last_known_good <= inference_buf;  // update safe-state value
                    actuator_valid  <= 1'b0;
                    state           <= IDLE;
                end
            end

            // ──────────────────────────────────────────────────────────────────
            // FAULT_STATE  (terminal until rst_n)
            // Drive actuator with the last-known-good value.
            // Deassert actuator_valid so the downstream sees no new commands.
            // The fault output stays asserted; fault_code is preserved.
            // Only a rst_n deassertion escapes this state.
            // ──────────────────────────────────────────────────────────────────
            FAULT_STATE: begin
                actuator_data  <= last_known_good;
                actuator_valid <= 1'b0;
                // fault remains 1'b1 — cleared only by rst_n
            end

            // ──────────────────────────────────────────────────────────────────
            default: state <= IDLE;

        endcase
    end
end

// =============================================================================
// Note on flux_bytecode_data
// =============================================================================
// This port is an input to the RAU but is not consumed internally.  In the
// parent netlist, flux_bytecode_data is wired in parallel to the FLUX-C VM's
// data input.  The RAU acts as address-bus master; the VM reads the opcodes
// directly.  The port is present on this module boundary to make the complete
// memory interface visible at the RAU level for synthesis hierarchy and
// formal verification purposes.
// =============================================================================

endmodule

`default_nettype wire
