```systemverilog
// =============================================================================
// flux_rau_interlock_tb.sv
// Self-checking testbench for flux_rau_interlock
// Target: Icarus Verilog (iverilog -g2012)
// =============================================================================

`timescale 1ns / 1ps
`default_nettype none

module flux_rau_interlock_tb;

// ---------------------------------------------------------------------------
// DUT signals
// ---------------------------------------------------------------------------
reg         clk;
reg         rst_n;

reg  [63:0] inference_data;
reg         inference_valid;
wire        inference_ready;

wire [63:0] actuator_data;
wire        actuator_valid;
reg         actuator_ready;

wire [31:0] flux_bytecode_addr;
reg  [7:0]  flux_bytecode_data;

wire        flux_start;
reg         flux_done;
reg         flux_pass;
reg  [7:0]  flux_fault_code;

wire        fault;
wire [7:0]  fault_code;
wire [31:0] checks_total;
wire [31:0] checks_passed;
wire [31:0] checks_failed;

// ---------------------------------------------------------------------------
// Pass / fail tracking
// ---------------------------------------------------------------------------
integer pass_count;
integer fail_count;

task automatic check;
    input        expr;
    input [127:0] msg;
    begin
        if (expr) begin
            $display("  PASS: %0s", msg);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: %0s", msg);
            fail_count = fail_count + 1;
        end
    end
endtask

// ---------------------------------------------------------------------------
// DUT instantiation
// ---------------------------------------------------------------------------
flux_rau_interlock dut (
    .clk               (clk),
    .rst_n             (rst_n),
    .inference_data    (inference_data),
    .inference_valid   (inference_valid),
    .inference_ready   (inference_ready),
    .actuator_data     (actuator_data),
    .actuator_valid    (actuator_valid),
    .actuator_ready    (actuator_ready),
    .flux_bytecode_addr(flux_bytecode_addr),
    .flux_bytecode_data(flux_bytecode_data),
    .flux_start        (flux_start),
    .flux_done         (flux_done),
    .flux_pass         (flux_pass),
    .flux_fault_code   (flux_fault_code),
    .fault             (fault),
    .fault_code        (fault_code),
    .checks_total      (checks_total),
    .checks_passed     (checks_passed),
    .checks_failed     (checks_failed)
);

// ---------------------------------------------------------------------------
// Clock: 10 ns period
// ---------------------------------------------------------------------------
initial clk = 0;
always #5 clk = ~clk;

// ---------------------------------------------------------------------------
// Helper: assert reset for N cycles
// ---------------------------------------------------------------------------
task automatic do_reset;
    input integer cycles;
    integer i;
    begin
        rst_n           = 1'b0;
        inference_valid = 1'b0;
        inference_data  = 64'h0;
        actuator_ready  = 1'b0;
        flux_done       = 1'b0;
        flux_pass       = 1'b1;
        flux_fault_code = 8'h00;
        flux_bytecode_data = 8'hAA;
        for (i = 0; i < cycles; i = i + 1)
            @(posedge clk);
        #1; // small skew past clock edge
        rst_n = 1'b1;
        @(posedge clk);
        #1;
    end
endtask

// ---------------------------------------------------------------------------
// Helper: run one inference word through the RAU.
//   pass_mask[i]=1 → constraint i passes, 0 → fails.
//   fail_code      → flux_fault_code driven when constraint fails.
//   bp_cycles      → extra actuator backpressure cycles after all checks done.
// Returns: 1 if actuator accepted the word, 0 if fault latched.
// ---------------------------------------------------------------------------
localparam NUM_C = 8;

task automatic run_inference;
    input  [63:0]  data_in;
    input  [NUM_C-1:0] pass_mask;  // bit i = pass/fail for constraint i
    input  [7:0]   fail_code;
    input  integer bp_cycles;      // backpressure cycles before actuator_ready
    output integer accepted;       // 1 = actuator saw the word, 0 = fault

    integer c;
    integer timeout;
    begin
        accepted = 0;

        // Present inference word
        @(negedge clk);
        inference_data  = data_in;
        inference_valid = 1'b1;

        // Wait for ready (may be 0 if faulted)
        timeout = 0;
        while (!inference_ready && timeout < 20) begin
            @(posedge clk); #1;
            timeout = timeout + 1;
        end

        if (!inference_ready) begin
            // RAU not accepting — already faulted or stuck
            inference_valid = 1'b0;
            accepted = 0;
            // $display("  [run_inference] inference_ready never asserted");
            return;
        end

        @(posedge clk); #1;
        inference_valid = 1'b0;

        // Step through NUM_C constraints
        for (c = 0; c < NUM_C; c = c + 1) begin
            // Wait for flux_start
            timeout = 0;
            while (!flux_start && timeout < 30) begin
                @(posedge clk); #1;
                timeout = timeout + 1;
            end

            // Set VM result for this constraint
            flux_pass       = pass_mask[c];
            flux_fault_code = fail_code;

            @(posedge clk); #1;   // let start register

            // Assert done for one cycle
            flux_done = 1'b1;
            @(posedge clk); #1;
            flux_done = 1'b0;

            // If this constraint failed, stop iterating
            if (!pass_mask[c]) begin
                c = NUM_C; // break
            end
        end

        // If fault was latched we're done
        if (fault) begin
            accepted = 0;
            return;
        end

        // Apply backpressure then accept
        begin : actuator_handshake
            integer bp;
            actuator_ready = 1'b0;
            for (bp = 0; bp < bp_cycles; bp = bp + 1) begin
                timeout = 0;
                while (!actuator_valid && timeout < 10) begin
                    @(posedge clk); #1;
                    timeout = timeout + 1;
                end
                @(posedge clk); #1;
            end

            // Now accept
            actuator_ready = 1'b1;
            timeout = 0;
            while (!actuator_valid && timeout < 20) begin
                @(posedge clk); #1;
                timeout = timeout + 1;
            end
            @(posedge clk); #1;
            actuator_ready = 1'b0;
            accepted = 1;
        end
    end
endtask

// ---------------------------------------------------------------------------
// Main test sequence
// ---------------------------------------------------------------------------
integer result;

initial begin
    $dumpfile("flux_rau_interlock_tb.vcd");
    $dumpvars(0, flux_rau_interlock_tb);

    pass_count = 0;
    fail_count = 0;

    // =========================================================================
    // 1. Power-on reset check
    // =========================================================================
    $display("\n=== TEST 1: Reset clears all state ===");
    do_reset(4);

    check(fault        == 1'b0,  "fault cleared after reset");
    check(fault_code   == 8'h00, "fault_code cleared after reset");
    check(checks_total == 32'h0, "checks_total cleared after reset");
    check(checks_passed== 32'h0, "checks_passed cleared after reset");
    check(checks_failed== 32'h0, "checks_failed cleared after reset");
    check(inference_ready == 1'b1, "inference_ready asserted after reset");
    check(actuator_valid  == 1'b0, "actuator_valid deasserted after reset");

    // =========================================================================
    // 2. Inference pass-through (all 8 constraints pass)
    // =========================================================================
    $display("\n=== TEST 2: Inference pass-through (all constraints pass) ===");
    do_reset(4);

    run_inference(
        64'hDEAD_BEEF_CAFE_1234,
        8'b1111_1111,   // all 8 pass
        8'h00,
        0,              // no backpressure
        result
    );

    check(result         == 1,                    "actuator accepted the word");
    check(fault          == 1'b0,                 "no fault latched");
    check(checks_total   == 32'd8,                "checks_total == 8");
    check(checks_passed  == 32'd8,                "checks_passed == 8");
    check(checks_failed  == 32'd0,                "checks_failed == 0");

    // Give RAU time to return to IDLE
    repeat(4) @(posedge clk);
    check(inference_ready == 1'b1, "inference_ready re-asserts after pass");

    // =========================================================================
    // 3. Constraint violation — fault latch
    // =========================================================================
    $display("\n=== TEST 3: Constraint violation (constraint 0 fails) ===");
    do_reset(4);

    run_inference(
        64'hBAD_BAD_BAD_BAD_00,
        8'b1111_1110,   // constraint 0 fails (LSB=0)
        8'hAB,
        0,
        result
    );

    check(result         == 0,     "actuator did NOT accept (fault path)");
    check(fault          == 1'b1,  "fault latched on violation");
    check(fault_code     == 8'hAB, "fault_code captured from VM");
    check(checks_failed  == 32'd1, "checks_failed == 1");
    // inference_ready must be low in FAULT_STATE
    repeat(2) @(posedge clk); #1;
    check(inference_ready == 1'b0, "inference_ready deasserted in FAULT_STATE");

    // =========================================================================
    // 4. Reset clears fault state
    // =========================================================================
    $display("\n=== TEST 4: Reset clears fault ===");
    // (still in FAULT_STATE from test 3)
    do_reset(4);

    check(fault          == 1'b0,  "fault cleared by rst_n");
    check(fault_code     == 8'h00, "fault_code cleared by rst_n");
    check(checks_total   == 32'h0, "counters cleared by rst_n");
    check(inference_ready == 1'b1, "inference_ready restored after reset");

    // =========================================================================
    // 5. Violation on a non-zero constraint index (constraint 4 fails)
    // =========================================================================
    $display("\n=== TEST 5: Constraint 4 fails (first 4 pass) ===");
    do_reset(4);

    run_inference(
        64'h1234_5678_9ABC_DEF0,
        8'b1110_1111,   // bits [7:5]=111, bit4=0, bits[3:0]=1111 → constraint 4 fails
        8'hCC,
        0,
        result
    );

    check(fault          == 1'b1,  "fault latched on constraint-4 violation");
    check(fault_code     == 8'hCC, "fault_code == 0xCC");
    // 4 pass + 1 fail
    check(checks_total   == 32'd5, "checks_total == 5 (4 pass + 1 fail)");
    check(checks_passed  == 32'd4, "checks_passed == 4");
    check(checks_failed  == 32'd1, "checks_failed == 1");

    // =========================================================================
    // 6. Multiple consecutive passing inferences
    // =========================================================================
    $display("\n=== TEST 6: Multiple consecutive passing inferences ===");
    do_reset(4);

    run_inference(64'hAAAA_AAAA_AAAA_AAAA, 8'hFF, 8'h00, 0, result);
    check(result == 1, "inference #1 accepted");
    run_inference(64'hBBBB_BBBB_BBBB_BBBB, 8'hFF, 8'h00, 0, result);
    check(result == 1, "inference #2 accepted");
    run_inference(64'hCCCC_CCCC_CCCC_CCCC, 8'hFF, 8'h00, 0, result);
    check(result == 1, "inference #3 accepted");

    check(fault         == 1'b0,   "no fault after 3 passing inferences");
    check(checks_total  == 32'd24, "checks_total == 24 (3×8)");
    check(checks_passed == 32'd24, "checks_passed == 24");
    check(checks_failed == 32'd0,  "checks_failed == 0");

    // =========================================================================
    // 7. Backpressure: actuator holds off for 3 cycles
    // =========================================================================
    $display("\n=== TEST 7: Backpressure (actuator_ready delayed 3 cycles) ===");
    do_reset(4);

    run_inference(
        64'h0123_4567_89AB_CDEF,
        8'hFF,
        8'h00,
        3,      // 3 cycles of backpressure
        result
    );

    check(result == 1,     "inference accepted despite backpressure");
    check(fault  == 1'b0,  "no fault under backpressure");

    // =========================================================================
    // 8. Fault is sticky — stays latched across further inference attempts
    // =========================================================================
    $display("\n=== TEST 8: Fault stickiness (no new inference accepted) ===");
    do_reset(4);

    // Trigger fault
    run_inference(64'hDEAD_0000_0000_0000, 8'b1111_1110, 8'h55, 0, result);
    check(fault == 1'b1, "fault latched");

    // Try to push another inference — should be rejected
    @(negedge clk);
    inference_valid = 1'b1;
    inference_data  = 64'hFFFF_FFFF_FFFF_FFFF;
    repeat(4) @(posedge clk); #1;
    inference_valid = 1'b0;

    check(fault == 1'b1, "fault still asserted after second inference attempt");
    // checks counters must not have advanced beyond the first fault
    check(checks_total  == 32'd1, "checks_total unchanged after stuck fault");

    // =========================================================================
    // 9. Last-known-good preserved in FAULT_STATE
    // =========================================================================
    $display("\n=== TEST 9: Last-known-good in FAULT_STATE ===");
    do_reset(4);

    // First pass a good value so last_known_good is non-zero
    run_inference(64'hCAFE_BABE_DEAD_BEEF, 8'hFF, 8'h00, 0, result);
    check(result == 1, "good inference accepted");

    // Now cause a fault
    run_inference(64'hBAD1_BAD2_BAD3_BAD4, 8'b0000_0000, 8'hFF, 0, result);
    check(fault == 1'b1, "fault latched after second inference");

    // In FAULT_STATE, actuator_data should hold last_known_good
    repeat(2) @(posedge clk); #1;
    check(actuator_data == 64'hCAFE_BABE_DEAD_BEEF,
          "actuator_data == last_known_good in FAULT_STATE");
    check(actuator_valid == 1'b0,
          "actuator_valid deasserted in FAULT_STATE");

    // =========================================================================
    // Summary
    // =========================================================================
    $display("\n=========================================");
    $display("  Results: %0d passed, %0d failed", pass_count, fail_count);
    $display("=========================================\n");

    if (fail_count == 0)
        $display("ALL TESTS PASSED");
    else
        $display("SOME TESTS FAILED");

    $finish;
end

// ---------------------------------------------------------------------------
// Watchdog: abort if simulation runs too long
// ---------------------------------------------------------------------------
initial begin
    #500000;
    $display("WATCHDOG TIMEOUT — simulation hung");
    $finish;
end

endmodule

`default_nettype wire
```
