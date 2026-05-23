<?php
/**
 * FLUX VM Bridge — executes constraint bytecode via Rust service
 */
class FluxVM {
    private string $vm_url = 'http://localhost:4053';

    public function execute(string $bytecode_hex, int $gas = 1000): array {
        $payload = json_encode([
            'bytecode' => $bytecode_hex,
            'gas' => $gas,
            'input' => []
        ]);
        $ctx = stream_context_create([
            'http' => [
                'method' => 'POST',
                'header' => "Content-Type: application/json\r\n",
                'content' => $payload,
                'timeout' => 5,
            ]
        ]);
        $result = @file_get_contents($this->vm_url . '/execute', false, $ctx);
        if ($result) return json_decode($result, true);
        return ['error' => 'VM service unavailable', 'status' => 'offline'];
    }

    public function assemble(string $guard_source): array {
        $payload = json_encode(['source' => $guard_source]);
        $ctx = stream_context_create([
            'http' => [
                'method' => 'POST',
                'header' => "Content-Type: application/json\r\n",
                'content' => $payload,
                'timeout' => 5,
            ]
        ]);
        $result = @file_get_contents($this->vm_url . '/assemble', false, $ctx);
        if ($result) return json_decode($result, true);
        return ['error' => 'Assembler unavailable'];
    }

    /**
     * Simulate execution locally (no Rust service needed)
     * Interprets a simplified subset for demo purposes
     */
    public function simulate(string $bytecode_hex, array $inputs = []): array {
        $bytes = array_values(unpack('C*', hex2bin($bytecode_hex)));
        $stack = [];
        $pc = 0;
        $gas = 1000;
        $halted = false;
        $fault = null;
        $trace = [];

        while ($pc < count($bytes) && $gas > 0 && !$halted && !$fault) {
            $gas--;
            $op = $bytes[$pc];
            $op_hex = sprintf('0x%02X', $op);

            switch ($op) {
                case 0x00: // PUSH
                    $val = $bytes[$pc + 1] ?? 0;
                    array_push($stack, $val);
                    $trace[] = "PUSH $val";
                    $pc += 2;
                    break;
                case 0x01: // POP
                    array_pop($stack);
                    $trace[] = "POP";
                    $pc += 1;
                    break;
                case 0x1A: // HALT
                    $halted = true;
                    $trace[] = "HALT";
                    $pc += 1;
                    break;
                case 0x1B: // ASSERT
                    $v = array_pop($stack);
                    if ($v === 0 || $v === null) {
                        $fault = 'AssertFailed';
                        $trace[] = "ASSERT → FAULT";
                    } else {
                        $trace[] = "ASSERT → PASS";
                    }
                    $pc += 1;
                    break;
                case 0x1D: // BITMASK_RANGE
                    $lo = $bytes[$pc + 1] ?? 0;
                    $hi = $bytes[$pc + 2] ?? 0;
                    $val = array_pop($stack) ?? 0;
                    $pass = ($val >= $lo && $val <= $hi) ? 1 : 0;
                    array_push($stack, $pass);
                    $trace[] = "BITMASK_RANGE $lo $hi → " . ($pass ? "IN RANGE" : "OUT OF RANGE");
                    $pc += 3;
                    break;
                case 0x1C: // CHECK_DOMAIN
                    $mask = $bytes[$pc + 1] ?? 0;
                    $val = array_pop($stack) ?? 0;
                    $result = $val & $mask;
                    array_push($stack, $result);
                    $trace[] = "CHECK_DOMAIN mask=$mask → $result";
                    $pc += 2;
                    break;
                case 0x20: // GUARD_TRAP
                    $fault = 'GuardTrap';
                    $trace[] = "GUARD_TRAP";
                    $pc += 1;
                    break;
                case 0x24: // CMP_GE
                    $b = array_pop($stack) ?? 0;
                    $a = array_pop($stack) ?? 0;
                    array_push($stack, $a >= $b ? 1 : 0);
                    $trace[] = "CMP_GE $a >= $b → " . ($a >= $b ? 1 : 0);
                    $pc += 1;
                    break;
                case 0x27: // NOP
                    $trace[] = "NOP";
                    $pc += 1;
                    break;
                default:
                    $trace[] = "UNKNOWN $op_hex";
                    $pc += 1;
                    break;
            }
        }

        if ($gas <= 0 && !$halted && !$fault) {
            $fault = 'GasExhausted';
        }

        return [
            'status' => $fault ? 'fault' : ($halted ? 'halted' : 'running'),
            'fault' => $fault,
            'gas_used' => 1000 - $gas,
            'gas_remaining' => $gas,
            'stack' => $stack,
            'trace' => $trace,
            'pc' => $pc,
        ];
    }
}
