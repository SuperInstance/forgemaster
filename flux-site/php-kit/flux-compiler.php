<?php
/**
 * GUARD → FLUX Compiler — Pure PHP, no external dependencies
 * Compiles GUARD DSL constraints to FLUX-C bytecode hex strings
 */

class FluxCompiler {
    /**
     * Compile GUARD source to FLUX bytecode
     */
    public function compile(string $guard_source): array {
        $errors = [];
        $bytecode = '';
        $constraint_count = 0;
        
        // Parse constraints
        preg_match_all('/constraint\s+(\w+)\s*(?:@priority\((\w+)\))?\s*\{([^}]+)\}/s', $guard_source, $matches, PREG_SET_ORDER);
        
        foreach ($matches as $match) {
            $name = $match[1];
            $priority = $match[2] ?? 'DEFAULT';
            $body = $match[3];
            $constraint_count++;
            
            // Parse checks in the constraint body
            // range(lo, hi)
            if (preg_match('/range\(([^,]+),\s*([^)]+)\)/', $body, $rm)) {
                $lo = $this->parseValue($rm[1]);
                $hi = $this->parseValue($rm[2]);
                if ($lo === null || $hi === null) {
                    $errors[] = "Invalid range values in constraint '$name'";
                    continue;
                }
                $lo_byte = min(255, max(0, (int)$lo));
                $hi_byte = min(255, max(0, (int)$hi));
                $bytecode .= sprintf('1D%02X%02X', $lo_byte, $hi_byte); // BITMASK_RANGE
                $bytecode .= '1B'; // ASSERT
            }
            
            // bitmask(mask)
            if (preg_match('/bitmask\((0x[0-9A-Fa-f]+|\d+)\)/', $body, $bm)) {
                $mask = intval($bm[1], 0);
                $mask_byte = min(255, max(0, $mask));
                $bytecode .= sprintf('00%02X', $mask_byte); // PUSH mask
                $bytecode .= sprintf('1C%02X', $mask_byte); // CHECK_DOMAIN
                $bytecode .= '1B'; // ASSERT
            }
            
            // thermal(budget)
            if (preg_match('/thermal\(([^)]+)\)/', $body, $tm)) {
                $budget = min(255, max(0, (int)(float)$tm[1]));
                $bytecode .= sprintf('00%02X', $budget); // PUSH budget
                $bytecode .= '24'; // CMP_GE
                $bytecode .= '1B'; // ASSERT
            }
            
            // sparsity(count)
            if (preg_match('/sparsity\(([^)]+)\)/', $body, $sm)) {
                $count = min(255, max(0, (int)$sm[1]));
                $bytecode .= sprintf('00%02X', $count); // PUSH count
                $bytecode .= '24'; // CMP_GE
                $bytecode .= '1B'; // ASSERT
            }
        }
        
        // Add HALT + GUARD_TRAP (pass/fail endpoints)
        $bytecode .= '1A20';
        
        return [
            'bytecode' => strtoupper($bytecode),
            'bytecode_formatted' => $this->formatBytecode($bytecode),
            'bytecode_length' => strlen($bytecode) / 2,
            'constraint_count' => $constraint_count,
            'errors' => $errors,
            'disassembly' => $this->disassemble($bytecode),
        ];
    }
    
    private function parseValue(string $val): ?float {
        $val = trim($val);
        if (is_numeric($val)) return (float)$val;
        return null;
    }
    
    private function formatBytecode(string $hex): string {
        return trim(chunk_split(strtoupper($hex), 2, ' '));
    }
    
    private function disassemble(string $hex): array {
        $bytes = array_values(unpack('C*', hex2bin($hex)));
        $ops = [];
        $i = 0;
        
        while ($i < count($bytes)) {
            $op = $bytes[$i];
            switch ($op) {
                case 0x00: $ops[] = sprintf('PUSH 0x%02X', $bytes[$i+1] ?? 0); $i += 2; break;
                case 0x1A: $ops[] = 'HALT'; $i += 1; break;
                case 0x1B: $ops[] = 'ASSERT'; $i += 1; break;
                case 0x1C: $ops[] = sprintf('CHECK_DOMAIN 0x%02X', $bytes[$i+1] ?? 0); $i += 2; break;
                case 0x1D: $ops[] = sprintf('BITMASK_RANGE %d %d', $bytes[$i+1] ?? 0, $bytes[$i+2] ?? 0); $i += 3; break;
                case 0x20: $ops[] = 'GUARD_TRAP'; $i += 1; break;
                case 0x24: $ops[] = 'CMP_GE'; $i += 1; break;
                default: $ops[] = sprintf('UNKNOWN 0x%02X', $op); $i += 1; break;
            }
        }
        return $ops;
    }
}
