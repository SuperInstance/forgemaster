// ============================================================================
// flux_hdc_judge.v — FLUX HDC 128-bit XOR-Fold Judge (FPGA Synthesizable)
// ============================================================================
// Architecture:
//   - 128-bit folded hypervectors from the HDC knowledge base
//   - XOR + POPCNT = Hamming distance in 1 clock cycle
//   - Similarity = (128 - hamming_distance) / 128
//   - Match if similarity >= threshold
//
// Port interface:
//   clk           : System clock
//   rst_n         : Active-low reset
//   query[127:0]  : 128-bit folded query hypervector
//   stored[127:0] : 128-bit folded stored hypervector
//   threshold[6:0]: Match threshold (0-127 matching bits, e.g. 96 = 75%)
//   similarity[6:0]: Number of matching bits (0-128)
//   match         : High if similarity >= threshold
//   valid         : High when result is ready (combinational, always valid)
// ============================================================================

module flux_hdc_judge (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [127:0] query,
    input  wire [127:0] stored,
    input  wire [6:0]   threshold,   // Match threshold in matching bits (0-127)
    output reg  [6:0]   similarity,  // Number of matching bits
    output reg          match,       // 1 if similarity >= threshold
    output wire         valid        // Always valid (combinational logic)
);

    // =========================================================================
    // Stage 1: XOR to find differing bits
    // =========================================================================
    wire [127:0] diff = query ^ stored;

    // =========================================================================
    // Stage 2: Population count (POPCNT) of diff → Hamming distance
    // =========================================================================
    // Using a balanced tree adder for efficient synthesis
    // 128 bits → 16x 8-bit popcount → add tree → 8-bit result

    // 8-bit population count sub-blocks (16 of them)
    function automatic [2:0] popcnt8;
        input [7:0] v;
        integer i;
        reg [2:0] cnt;
        begin
            cnt = 3'd0;
            for (i = 0; i < 8; i = i + 1)
                cnt = cnt + v[i];
            popcnt8 = cnt;
        end
    endfunction

    wire [2:0] pop [0:15];
    genvar g;
    generate
        for (g = 0; g < 16; g = g + 1) begin : gen_popcnt
            assign pop[g] = popcnt8(diff[g*8 +: 8]);
        end
    endgenerate

    // Add tree: 16 x 3-bit → 4 x 4-bit → 2 x 5-bit → 1 x 7-bit
    wire [3:0] sum4_0 = pop[0]  + pop[1]  + pop[2]  + pop[3];
    wire [3:0] sum4_1 = pop[4]  + pop[5]  + pop[6]  + pop[7];
    wire [3:0] sum4_2 = pop[8]  + pop[9]  + pop[10] + pop[11];
    wire [3:0] sum4_3 = pop[12] + pop[13] + pop[14] + pop[15];

    wire [4:0] sum8_0 = sum4_0 + sum4_1;
    wire [4:0] sum8_1 = sum4_2 + sum4_3;

    wire [6:0] hamming_dist = sum8_0 + sum8_1;

    // =========================================================================
    // Stage 3: Similarity = 128 - Hamming distance
    // =========================================================================
    wire [6:0] sim_bits;
    assign sim_bits = 7'd128 - hamming_dist;  // Wraps cleanly; max 128

    // =========================================================================
    // Stage 4: Match decision (registered for timing closure)
    // =========================================================================
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            similarity <= 7'd0;
            match      <= 1'b0;
        end else begin
            similarity <= sim_bits;
            match      <= (sim_bits >= threshold) ? 1'b1 : 1'b0;
        end
    end

    assign valid = 1'b1;  // Combinational path, always valid after 1 clock

endmodule


// ============================================================================
// flux_hdc_judge_tb.v — Testbench for 128-bit XOR-Fold Judge
// ============================================================================

module flux_hdc_judge_tb;

    reg          clk;
    reg          rst_n;
    reg  [127:0] query;
    reg  [127:0] stored;
    reg  [6:0]   threshold;
    wire [6:0]   similarity;
    wire         match;
    wire         valid;

    // Instantiate DUT
    flux_hdc_judge dut (
        .clk(clk),
        .rst_n(rst_n),
        .query(query),
        .stored(stored),
        .threshold(threshold),
        .similarity(similarity),
        .match(match),
        .valid(valid)
    );

    // Clock generation: 100MHz (10ns period)
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    // Test stimulus
    integer pass_count;
    integer fail_count;

    task check_case;
        input [127:0] q;
        input [127:0] s;
        input [6:0]   thresh;
        input [6:0]   expected_sim;
        input         expected_match;
        input [255:0] desc;  // Up to 32 chars
        begin
            @(posedge clk);
            query     <= q;
            stored    <= s;
            threshold <= thresh;
            @(posedge clk);
            #1;  // Small delay for outputs to settle
            
            if (similarity === expected_sim && match === expected_match) begin
                pass_count = pass_count + 1;
            end else begin
                fail_count = fail_count + 1;
                $display("FAIL: %0s", desc);
                $display("  Expected: sim=%0d match=%0b  Got: sim=%0d match=%0b",
                         expected_sim, expected_match, similarity, match);
            end
        end
    endtask

    initial begin
        pass_count = 0;
        fail_count = 0;
        
        // Reset
        rst_n = 0;
        query = 128'd0;
        stored = 128'd0;
        threshold = 7'd96;  // 75% default
        #20 rst_n = 1;
        
        $display("=== FLUX HDC Judge Testbench ===");
        $display("");
        
        // Test 1: Identical vectors → 128/128 match
        check_case(128'hFFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF,
                   128'hFFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF,
                   7'd96, 7'd128, 1'b1, "Identical vectors");
        
        // Test 2: Complement vectors → 0/128 match
        check_case(128'hFFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF,
                   128'h0000_0000_0000_0000_0000_0000_0000_0000,
                   7'd96, 7'd0, 1'b0, "Complement vectors");
        
        // Test 3: Differ by 1 bit → 127/128 match
        check_case(128'hFFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF,
                   128'hFFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFE,
                   7'd96, 7'd127, 1'b1, "Differ by 1 bit");
        
        // Test 4: Differ by 64 bits → 64/128 match
        check_case(128'hFFFF_FFFF_FFFF_FFFF_0000_0000_0000_0000,
                   128'h0000_0000_0000_0000_FFFF_FFFF_FFFF_FFFF,
                   7'd96, 7'd0, 1'b0, "Differ by 64 bits");
        
        // Test 5: Half identical → 64/128 match
        check_case(128'hAAAA_AAAA_AAAA_AAAA_AAAA_AAAA_AAAA_AAAA,
                   128'hAAAA_AAAA_AAAA_AAAA_5555_5555_5555_5555,
                   7'd96, 7'd64, 1'b0, "Half identical");
        
        // Test 6: Low threshold (50%) — 64/128 should match
        check_case(128'hAAAA_AAAA_AAAA_AAAA_AAAA_AAAA_AAAA_AAAA,
                   128'hAAAA_AAAA_AAAA_AAAA_5555_5555_5555_5555,
                   7'd64, 7'd64, 1'b1, "Low threshold 50%");
        
        // Test 7: Known pattern — alternating bits
        check_case(128'hAAAA_AAAA_AAAA_AAAA_AAAA_AAAA_AAAA_AAAA,
                   128'hAAAA_AAAA_AAAA_AAAA_AAAA_AAAA_AAAA_AAAA,
                   7'd96, 7'd128, 1'b1, "Alternating identical");
        
        // Test 8: 75% match exactly at threshold
        // 96 bits matching, 32 bits different
        check_case(128'hFFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF,
                   128'hFFFF_FFFF_FFFF_FFFF_FFFF_FFFF_0000_0000,
                   7'd96, 7'd96, 1'b1, "Exactly at threshold");
        
        // Test 9: Just below threshold (95/128)
        check_case(128'hFFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF,
                   128'hFFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FE00,  // 9 bits different
                   7'd120, 7'd119, 1'b0, "Just below high threshold");
        
        // Test 10: All zeros
        check_case(128'd0, 128'd0, 7'd96, 7'd128, 1'b1, "Both zero");
        
        $display("");
        $display("=== Results: %0d passed, %0d failed ===", pass_count, fail_count);
        
        if (fail_count > 0)
            $display("SOME TESTS FAILED");
        else
            $display("ALL TESTS PASSED");
        
        $finish;
    end

    // Timeout watchdog
    initial begin
        #1000;
        $display("ERROR: Simulation timeout!");
        $finish;
    end

endmodule
