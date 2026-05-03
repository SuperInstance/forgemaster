//-----------------------------------------------------------------------------
// FLUX Constraint Checker Formal Testbench
// Binds assertions to DUT without modifying production RTL
// For use with SymbiYosys formal verification
//-----------------------------------------------------------------------------
module flux_formal_tb;
bind flux_checker_top flux_formal_assertions formal_bind(.*);
endmodule

module flux_formal_assertions #(
    parameter STACK_DEPTH = 16
)(
    input  logic        clk_100mhz,
    input  logic        rst_n,

    // DUT signals (bound from flux_checker_top)
    input  logic        global_fault,
    input  logic        interlock_out,
    input  logic        vm_nop_force,
    input  logic        safe_status_pin,
    input  logic        tmr_mismatch_any,
    input  logic        stack_bounds_violation,
    input  logic        illegal_opcode_detected
);

//--------------------------------------------------------------------------
//  BASE FORMAL ASSUMPTIONS
//--------------------------------------------------------------------------
initial assume(!rst_n);
always @(posedge clk_100mhz) begin
    assume($stable(rst_n) || $rose(rst_n));
    if (!$past(rst_n)) assume($stable(global_fault));
end
always @(*) if (rst_n) assume(!$isunknown(tmr_mismatch_any));

//--------------------------------------------------------------------------
//  REQUIRED SAFETY PROPERTIES (7 assertions)
//--------------------------------------------------------------------------

// 1. Fault is sticky forever once asserted
a_fault_sticky: assert property (
    disable iff (!rst_n)
    global_fault |=> global_fault
);

// 2. Interlock asserts within 1 cycle of fault
a_interlock_latency: assert property (
    disable iff (!rst_n)
    $rose(global_fault) |-> ##1 interlock_out
);

// 3. All execution forced to NOP during fault
a_safe_nop: assert property (
    disable iff (!rst_n)
    global_fault |-> vm_nop_force
);

// 4. TMR mismatch never goes undetected
a_no_undetected_tmr: assert property (
    disable iff (!rst_n)
    tmr_mismatch_any |=> global_fault
);

// 5. Stack violation propagates to global fault
a_stack_bounds: assert property (
    disable iff (!rst_n)
    stack_bounds_violation |=> global_fault
);

// 6. Illegal opcode propagates to global fault
a_illegal_op_fault: assert property (
    disable iff (!rst_n)
    illegal_opcode_detected |=> global_fault
);

// 7. Safe status pin never enters tri-state during fault
a_safe_pin_active: assert property (
    disable iff (!rst_n)
    global_fault |-> !$isunknown(safe_status_pin)
);

//--------------------------------------------------------------------------
//  FAULT INJECTION FOR COVERAGE
//--------------------------------------------------------------------------
logic inject_tmr_fault, inject_stack_fault, inject_illegal_op_fault;
initial begin
    inject_tmr_fault = $anyseq;
    inject_stack_fault = $anyseq;
    inject_illegal_op_fault = $anyseq;
end

always @(posedge clk_100mhz) begin
    if (rst_n && !global_fault) begin
        if (inject_tmr_fault)         assume(tmr_mismatch_any == 1);
        if (inject_stack_fault)       assume(stack_bounds_violation == 1);
        if (inject_illegal_op_fault)  assume(illegal_opcode_detected == 1);
    end
end

//--------------------------------------------------------------------------
//  COVER PROPERTIES (validate testbench coverage)
//--------------------------------------------------------------------------
cover_normal_operation:    cover property (rst_n ##5 !global_fault);
cover_tmr_fault_trigger:   cover property ($rose(tmr_mismatch_any) ##1 $rose(global_fault));
cover_stack_fault_trigger: cover property ($rose(stack_bounds_violation) ##1 $rose(global_fault));
cover_illegal_op_trigger:  cover property ($rose(illegal_opcode_detected) ##1 $rose(global_fault));
cover_interlock_activate:  cover property ($rose(global_fault) ##1 interlock_out);
cover_fault_sticky:        cover property ($rose(global_fault) ##10 global_fault);

endmodule
