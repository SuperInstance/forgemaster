### Synthesizable Verilog-2001 Hyperdimensional Constraint Judge Module
```verilog
module hdc_judge #(
    parameter BRAM_ADDR_WIDTH = 8,    // 256 entries default (2^8)
    parameter DB_VECTOR_WIDTH = 128    // 128-bit hypervectors default
)(
    // Global Clock/Reset
    input  wire                        aclk,
    input  wire                        aresetn,

    // AXI4-Lite Slave Interface
    // Write Address Channel
    input  wire [31:0]                 s_axi_awaddr,
    input  wire                        s_axi_awvalid,
    output reg                         s_axi_awready,
    // Write Data Channel
    input  wire [31:0]                 s_axi_wdata,
    input  wire [3:0]                  s_axi_wstrb,
    input  wire                        s_axi_wvalid,
    output reg                         s_axi_wready,
    // Write Response Channel
    output reg  [1:0]                  s_axi_bresp,
    output reg                         s_axi_bvalid,
    input  wire                        s_axi_bready,
    // Read Address Channel
    input  wire [31:0]                 s_axi_araddr,
    input  wire                        s_axi_arvalid,
    output reg                         s_axi_arready,
    // Read Data Channel
    output reg  [31:0]                 s_axi_rdata,
    output reg  [1:0]                  s_axi_rresp,
    output reg                         s_axi_rvalid,
    input  wire                        s_axi_rready,

    // BRAM Master Interface for Constraint Database
    output reg  [BRAM_ADDR_WIDTH-1:0]  m_bram_addr,
    output reg                         m_bram_en,
    input  wire [DB_VECTOR_WIDTH-1:0]  m_bram_dout,

    // Status Outputs for Testbench/System
    output reg                         done_out
);

// Local Parameters for AXI Register Map
localparam ADDR_QUERY_LOW_0  = 2'h0;  // 0x00: Lower 32b of 64b query lower half
localparam ADDR_QUERY_LOW_1  = 2'h1;  // 0x04: Upper 32b of 64b query lower half
localparam ADDR_QUERY_HIGH_0 = 2'h2;  // 0x08: Lower 32b of 64b query upper half
localparam ADDR_QUERY_HIGH_1 = 2'h3;  // 0x0C: Upper 32b of 64b query upper half + trigger
localparam ADDR_THRESHOLD    = 2'h4;  // 0x10: Similarity threshold
localparam ADDR_SCORE        = 2'h5;  // 0x14: Best match similarity score (RO)
localparam ADDR_BEST_IDX     = 2'h6;  // 0x18: Best match index (RO)

// Internal Registers
reg  [63:0]                  query_low_reg;       // Lower 64b of 128b query vector
reg  [63:0]                  query_high_reg;      // Upper 64b of 128b query vector
assign query_reg = {query_high_reg, query_low_reg}; // Full 128b query

reg  [31:0]                  threshold_reg;       // Configurable similarity threshold
reg  [31:0]                  best_score_reg;      // Highest valid similarity score
reg  [BRAM_ADDR_WIDTH-1:0]   best_idx_reg;        // Index of best matching vector
reg  [BRAM_ADDR_WIDTH-1:0]   bram_addr_reg;       // Current BRAM read address
reg  [DB_VECTOR_WIDTH-1:0]   bram_dout_reg;       // Latched BRAM output (1 cycle latency)
reg  [DB_VECTOR_WIDTH-1:0]   xor_reg;             // Pipeline stage 1: XOR(query, DB vector)
reg  [6:0]                   popcount_reg;        // Pipeline stage 2: Hamming distance
reg                          processing_reg;      // Active processing flag
reg                          done_reg;            // Processing complete flag
assign done_out = done_reg;

// Internal AXI Transaction Registers
reg  [31:0]                  axi_awaddr_reg;
reg                         axi_awready_reg;
reg                         axi_wready_reg;
reg                         query_low_written;
reg                         query_high_written;
reg                         start_processing_reg;

// ------------------------------
// Combinational Popcount Tree (128-bit)
// ------------------------------
function [6:0] popcount_128;
    input [DB_VECTOR_WIDTH-1:0] in;
    reg [6:0] sum_half1, sum_half2;
    begin
        sum_half1 = popcount_64(in[DB_VECTOR_WIDTH-1:DB_VECTOR_WIDTH/2]);
        sum_half2 = popcount_64(in[(DB_VECTOR_WIDTH/2)-1:0]);
        popcount_128 = sum_half1 + sum_half2;
    end
endfunction

function [5:0] popcount_64;
    input [63:0] in;
    reg [5:0] sum_half1, sum_half2;
    begin
        sum_half1 = popcount_32(in[63:32]);
        sum_half2 = popcount_32(in[31:0]);
        popcount_64 = sum_half1 + sum_half2;
    end
endfunction

function [4:0] popcount_32;
    input [31:0] in;
    reg [4:0] sum_half1, sum_half2;
    begin
        sum_half1 = popcount_16(in[31:16]);
        sum_half2 = popcount_16(in[15:0]);
        popcount_32 = sum_half1 + sum_half2;
    end
endfunction

function [3:0] popcount_16;
    input [15:0] in;
    reg [3:0] sum_half1, sum_half2;
    begin
        sum_half1 = popcount_8(in[15:8]);
        sum_half2 = popcount_8(in[7:0]);
        popcount_16 = sum_half1 + sum_half2;
    end
endfunction

function [2:0] popcount_8;
    input [7:0] in;
    reg [2:0] sum_half1, sum_half2;
    begin
        sum_half1 = popcount_4(in[7:4]);
        sum_half2 = popcount_4(in[3:0]);
        popcount_8 = sum_half1 + sum_half2;
    end
endfunction

function [1:0] popcount_4;
    input [3:0] in;
    reg [1:0] sum_half1, sum_half2;
    begin
        sum_half1 = popcount_2(in[3:2]);
        sum_half2 = popcount_2(in[1:0]);
        popcount_4 = sum_half1 + sum_half2;
    end
endfunction

function [1:0] popcount_2;
    input [1:0] in;
    begin
        case(in)
            2'b00: popcount_2 = 2'd0;
            2'b01: popcount_2 = 2'd1;
            2'b10: popcount_2 = 2'd1;
            2'b11: popcount_2 = 2'd2;
        endcase
    end
endfunction

// ------------------------------
// AXI4-Lite Write Channel Logic
// ------------------------------
always @(posedge aclk or negedge aresetn) begin
    if (!aresetn) begin
        s_axi_awready      <= 1'b0;
        s_axi_wready       <= 1'b0;
        s_axi_bvalid       <= 1'b0;
        s_axi_bresp        <= 2'b00;
        axi_awaddr_reg     <= 32'h0;
        axi_awready_reg    <= 1'b0;
        axi_wready_reg     <= 1'b0;
        query_low_reg      <= 64'h0;
        query_high_reg     <= 64'h0;
        threshold_reg      <= 32'h0;
        query_low_written  <= 1'b0;
        query_high_written <= 1'b0;
        start_processing_reg <= 1'b0;
    end else begin
        // Write Address Handshake
        s_axi_awready <= ~s_axi_awvalid & ~axi_awready_reg;
        if (s_axi_awvalid && s_axi_awready) begin
            axi_awaddr_reg     <= s_axi_awaddr;
            axi_awready_reg    <= 1'b1;
        end else begin
            axi_awready_reg    <= 1'b0;
        end

        // Write Data Handshake + Register Writes
        s_axi_wready <= ~s_axi_wvalid & ~axi_wready_reg;
        if (s_axi_wvalid && s_axi_wready) begin
            axi_wready_reg <= 1'b1;
            start_processing_reg <= 1'b0;

            case(axi_awaddr_reg[31:2])
                ADDR_QUERY_LOW_0: begin
                    query_low_reg[31:0]  <= s_axi_wdata;
                    query_low_written    <= 1'b1;
                end
                ADDR_QUERY_LOW_1: begin
                    query_low_reg[63:32] <= s_axi_wdata;
                    query_low_written    <= 1'b1;
                end
                ADDR_QUERY_HIGH_0: begin
                    query_high_reg[31:0] <= s_axi_wdata;
                    query_high_written   <= 1'b1;
                end
                ADDR_QUERY_HIGH_1: begin
                    query_high_reg[63:32] <= s_axi_wdata;
                    query_high_written    <= 1'b1;
                    start_processing_reg <= 1'b1; // Trigger processing on final query write
                end
                ADDR_THRESHOLD: begin
                    threshold_reg <= s_axi_wdata;
                end
                default: ; // Ignore invalid addresses
            endcase
        end else begin
            axi_wready_reg <= 1'b0;
            start_processing_reg <= 1'b0;
        end

        // Write Response Handshake
        if (axi_awready_reg && axi_wready_reg) begin
            s_axi_bvalid <= 1'b1;
            s_axi_bresp  <= 2'b00; // OKAY response
        end else if (s_axi_bready && s_axi_bvalid) begin
            s_axi_bvalid <= 1'b0;
        end

        // Clear write flags when processing starts
        if (start_processing_reg) begin
            query_low_written  <= 1'b0;
            query_high_written <= 1'b0;
        end
    end
end

// ------------------------------
// AXI4-Lite Read Channel Logic
// ------------------------------
always @(posedge aclk or negedge aresetn) begin
    if (!aresetn) begin
        s_axi_arready  <= 1'b0;
        s_axi_rvalid   <= 1'b0;
        s_axi_rdata    <= 32'h0;
        s_axi_rresp    <= 2'b00;
        axi_araddr_reg <= 32'h0;
        axi_arready_reg<= 1'b0;
    end else begin
        // Read Address Handshake
        s_axi_arready <= ~s_axi_arvalid & ~axi_arready_reg;
        if (s_axi_arvalid && s_axi_arready) begin
            axi_araddr_reg  <= s_axi_araddr;
            axi_arready_reg <= 1'b1;
        end else begin
            axi_arready_reg <= 1'b0;
        end

        // Read Data Response
        if (axi_arready_reg) begin
            s_axi_rvalid <= 1'b1;
            case(axi_araddr_reg[31:2])
                ADDR_QUERY_LOW_0:  s_axi_rdata <= query_low_reg[31:0];
                ADDR_QUERY_LOW_1:  s_axi_rdata <= query_low_reg[63:32];
                ADDR_QUERY_HIGH_0: s_axi_rdata <= query_high_reg[31:0];
                ADDR_QUERY_HIGH_1: s_axi_rdata <= query_high_reg[63:32];
                ADDR_THRESHOLD:    s_axi_rdata <= threshold_reg;
                ADDR_SCORE:        s_axi_rdata <= best_score_reg;
                ADDR_BEST_IDX:     s_axi_rdata <= {{24{1'b0}}, best_idx_reg};
                default:           s_axi_rdata <= 32'h0;
            endcase
            s_axi_rresp <= 2'b00; // OKAY response
        end else if (s_axi_rready && s_axi_rvalid) begin
            s_axi_rvalid <= 1'b0;
        end
    end
end

// ------------------------------
// Processing Pipeline + BRAM Control
// ------------------------------
always @(posedge aclk or negedge aresetn) begin
    if (!aresetn) begin
        bram_addr_reg   <= {BRAM_ADDR_WIDTH{1'b0}};
        bram_dout_reg   <= {DB_VECTOR_WIDTH{1'b0}};
        xor_reg         <= {DB_VECTOR_WIDTH{1'b0}};
        popcount_reg    <= 7'h0;
        best_score_reg  <= 32'h0;
        best_idx_reg    <= {BRAM_ADDR_WIDTH{1'b0}};
        processing_reg  <= 1'b0;
        done_reg        <= 1'b0;
        m_bram_addr     <= {BRAM_ADDR_WIDTH{1'b0}};
        m_bram_en       <= 1'b0;
    end else begin
        m_bram_en       <= 1'b0;
        m_bram_addr     <= bram_addr_reg;

        // Handle processing start trigger
        if (start_processing_reg) begin
            processing_reg  <= 1'b1;
            best_score_reg  <= 32'h0;
            best_idx_reg    <= {BRAM_ADDR_WIDTH{1'b0}};
            bram_addr_reg   <= {BRAM_ADDR_WIDTH{1'b0}};
            done_reg        <= 1'b0;
        end else if (processing_reg) begin
            m_bram_en <= 1'b1;
            // Latched BRAM output to account for 1-cycle BRAM read latency
            bram_dout_reg <= m_bram_dout;

            // Pipeline Stage 1: XOR query with stored database vector
            xor_reg <= query_reg ^ bram_dout_reg;

            // Pipeline Stage 2: Compute Hamming distance (popcount)
            popcount_reg <= popcount_128(xor_reg);

            // Update best match if current score is valid and higher than previous best
            if (popcount_reg >= threshold_reg[6:0]) begin
                if (popcount_reg > best_score_reg[6:0]) begin
                    best_score_reg <= {{25{1'b0}}, popcount_reg};
                    best_idx_reg   <= bram_addr_reg;
                end
            end

            // Increment BRAM address for next cycle
            bram_addr_reg <= bram_addr_reg + 1'b1;

            // Mark processing complete when last address is read
            if (bram_addr_reg == ({BRAM_ADDR_WIDTH{1'b1}} - 1)) begin
                processing_reg <= 1'b0;
                done_reg        <= 1'b1;
            end
        end else begin
            bram_addr_reg <= {BRAM_ADDR_WIDTH{1'b0}};
            done_reg      <= 1'b0;
        end
    end
end

endmodule
```

---

### Testbench Module
```verilog
module hdc_judge_tb;

// Testbench Parameters
localparam CLK_PERIOD      = 4;    // 250MHz clock (4ns period)
localparam BRAM_DEPTH      = 256;
localparam VECTOR_WIDTH    = 128;

// Testbench Signals
reg                         aclk;
reg                         aresetn;

// AXI4-Lite Signals
reg [31:0]                  s_axi_awaddr;
reg                         s_axi_awvalid;
wire                        s_axi_awready;
reg [31:0]                  s_axi_wdata;
reg [3:0]                   s_axi_wstrb;
reg                         s_axi_wvalid;
wire                        s_axi_wready;
wire [1:0]                  s_axi_bresp;
wire                        s_axi_bvalid;
reg                         s_axi_b