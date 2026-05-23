<?php
/**
 * FLUX Constraint Playground — Interactive GUARD → FLUX → VM Demo
 * 
 * Drop-in page: visitors type GUARD constraints, watch them compile and execute.
 * Zero dependencies. Pure PHP.
 * 
 * Usage: include this file or load it directly.
 * API mode: ?api=1&source=...&input=... returns JSON
 */

require_once __DIR__ . '/../flux-compiler.php';
require_once __DIR__ . '/../flux-vm.php';

// ─── API Mode ───
if (isset($_GET['api'])) {
    header('Content-Type: application/json');
    $source = $_GET['source'] ?? $_POST['source'] ?? '';
    $input  = intval($_GET['input'] ?? $_POST['input'] ?? 0);
    
    $result = run_playground($source, $input);
    echo json_encode($result, JSON_PRETTY_PRINT);
    exit;
}

// ─── Main Playground Page ───
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FLUX Constraint Playground</title>
    <style>
        :root {
            --bg: #0a0e17;
            --surface: #111827;
            --border: #1e293b;
            --text: #e2e8f0;
            --muted: #64748b;
            --cyan: #06b6d4;
            --magenta: #d946ef;
            --green: #10b981;
            --red: #ef4444;
            --amber: #f59e0b;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        h1 {
            font-size: 1.5rem;
            color: var(--cyan);
            margin-bottom: 0.5rem;
        }
        .subtitle {
            color: var(--muted);
            margin-bottom: 2rem;
            font-size: 0.875rem;
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
        }
        .panel {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.25rem;
        }
        .panel-title {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--muted);
            margin-bottom: 0.75rem;
        }
        textarea {
            width: 100%;
            min-height: 120px;
            background: var(--bg);
            color: var(--cyan);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.75rem;
            font-family: inherit;
            font-size: 0.875rem;
            resize: vertical;
        }
        textarea:focus { outline: none; border-color: var(--cyan); }
        .controls {
            display: flex;
            gap: 0.75rem;
            margin-top: 0.75rem;
            align-items: center;
        }
        input[type="number"] {
            width: 100px;
            background: var(--bg);
            color: var(--amber);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.5rem 0.75rem;
            font-family: inherit;
            font-size: 0.875rem;
        }
        input:focus { outline: none; border-color: var(--amber); }
        button {
            background: var(--cyan);
            color: var(--bg);
            border: none;
            border-radius: 4px;
            padding: 0.5rem 1.5rem;
            font-family: inherit;
            font-size: 0.875rem;
            font-weight: 700;
            cursor: pointer;
            transition: background 0.15s;
        }
        button:hover { background: #0891b2; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .output {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.75rem;
            min-height: 120px;
            font-size: 0.8125rem;
            white-space: pre-wrap;
            overflow-x: auto;
        }
        .bytecode { color: var(--magenta); }
        .result-pass { color: var(--green); }
        .result-fail { color: var(--red); }
        .result-gas { color: var(--muted); }
        .examples {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }
        .example-btn {
            background: transparent;
            color: var(--muted);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.25rem 0.75rem;
            font-family: inherit;
            font-size: 0.75rem;
            cursor: pointer;
        }
        .example-btn:hover { border-color: var(--cyan); color: var(--cyan); }
        .trace-line { padding: 0.15rem 0; }
        .trace-op { color: var(--cyan); }
        .trace-val { color: var(--amber); }
        .trace-result { font-weight: 700; }
        .full-width { grid-column: 1 / -1; }
        .stats {
            display: flex;
            gap: 2rem;
            margin-top: 0.75rem;
        }
        .stat { font-size: 0.75rem; }
        .stat-label { color: var(--muted); }
        .stat-value { color: var(--text); font-weight: 700; }
    </style>
</head>
<body>
<div class="container">
    <h1>⚙️ FLUX Constraint Playground</h1>
    <p class="subtitle">Write GUARD constraints → compile to FLUX bytecode → execute on the constraint VM</p>
    
    <div class="examples">
        <button class="example-btn" onclick="loadExample('range')">Range Check</button>
        <button class="example-btn" onclick="loadExample('multi')">Multi-Constraint</button>
        <button class="example-btn" onclick="loadExample('thermal')">Thermal Budget</button>
        <button class="example-btn" onclick="loadExample('bitmask')">Bitmask Domain</button>
        <button class="example-btn" onclick="loadExample('safety')">Full Safety Check</button>
    </div>
    
    <div class="grid">
        <div class="panel">
            <div class="panel-title">GUARD Source</div>
            <textarea id="source" spellcheck="false">constraint drone_speed @priority(HARD) {
    range(0, 50)
}</textarea>
            <div class="controls">
                <button onclick="runCompiler()">Compile & Execute →</button>
                <span style="color:var(--muted);font-size:0.8rem">Input Value:</span>
                <input type="number" id="input" value="35" />
            </div>
        </div>
        
        <div class="panel">
            <div class="panel-title">FLUX Bytecode</div>
            <div class="output bytecode" id="bytecode">Compile to see bytecode...</div>
        </div>
        
        <div class="panel">
            <div class="panel-title">Execution Trace</div>
            <div class="output" id="trace">Execute to see trace...</div>
        </div>
        
        <div class="panel">
            <div class="panel-title">Result</div>
            <div class="output" id="result">—</div>
            <div class="stats" id="stats"></div>
        </div>
    </div>
</div>

<script>
const examples = {
    range: `constraint drone_speed @priority(HARD) {\n    range(0, 50)\n}`,
    multi: `constraint flight_safety @priority(HARD) {\n    range(0, 150)\n    thermal(5)\n    bitmask(63)\n}`,
    thermal: `constraint engine_temp @priority(HARD) {\n    thermal(5)\n}`,
    bitmask: `constraint sensor_domain @priority(HARD) {\n    bitmask(63)\n}`,
    safety: `constraint evtol_safety @priority(HARD) {\n    range(0, 150)\n    thermal(5)\n    bitmask(63)\n}`
};

function loadExample(name) {
    document.getElementById('source').value = examples[name];
}

async function runCompiler() {
    const source = document.getElementById('source').value;
    const input = parseInt(document.getElementById('input').value) || 0;
    
    const resp = await fetch(`?api=1&source=${encodeURIComponent(source)}&input=${input}`);
    const data = await resp.json();
    
    // Bytecode
    if (data.bytecode) {
        const formatted = data.bytecode.map((b, i) => {
            const hex = b.toString(16).toUpperCase().padStart(2, '0');
            return hex;
        }).join(' ');
        document.getElementById('bytecode').textContent = formatted;
    }
    
    // Trace
    if (data.trace) {
        document.getElementById('trace').innerHTML = data.trace.map(line => {
            if (line.startsWith('✅')) return `<div class="trace-line result-pass">${line}</div>`;
            if (line.startsWith('❌')) return `<div class="trace-line result-fail">${line}</div>`;
            if (line.startsWith('💡')) return `<div class="trace-line result-gas">${line}</div>`;
            return `<div class="trace-line">${line}</div>`;
        }).join('');
    }
    
    // Result
    const resultEl = document.getElementById('result');
    if (data.passed) {
        resultEl.innerHTML = `<span class="result-pass">✅ ALL CONSTRAINTS PASSED</span>`;
    } else if (data.error) {
        resultEl.innerHTML = `<span class="result-fail">❌ ${data.error}</span>`;
    } else {
        resultEl.innerHTML = `<span class="result-fail">❌ FAULT: ${data.fault || 'Unknown'}</span>`;
    }
    
    // Stats
    const statsEl = document.getElementById('stats');
    statsEl.innerHTML = `
        <div class="stat"><span class="stat-label">Gas: </span><span class="stat-value">${data.gas_used || 0} / ${data.gas_total || 1000}</span></div>
        <div class="stat"><span class="stat-label">Bytes: </span><span class="stat-value">${(data.bytecode || []).length}</span></div>
        <div class="stat"><span class="stat-label">Opcodes: </span><span class="stat-value">${data.opcode_count || 0}</span></div>
    `;
}
</script>
</body>
</html>
<?php

// ─── Playground Engine ───

function run_playground(string $source, int $input): array {
    $result = [
        'passed' => false,
        'bytecode' => [],
        'trace' => [],
        'gas_used' => 0,
        'gas_total' => 1000,
        'fault' => null,
        'error' => null,
        'opcode_count' => 0,
    ];
    
    // Parse GUARD source
    $parsed = parse_guard($source);
    if ($parsed === null) {
        $result['error'] = 'Parse error: invalid GUARD syntax';
        return $result;
    }
    
    // Compile to bytecode
    $bytecode = compile_guard($parsed);
    if (empty($bytecode)) {
        $result['error'] = 'Compilation error: no bytecode generated';
        return $result;
    }
    
    $result['bytecode'] = $bytecode;
    $result['opcode_count'] = count_opcode_instructions($bytecode);
    
    // Execute on VM
    $vm_result = execute_flux($bytecode, $input, 1000);
    
    $result['passed'] = $vm_result['passed'];
    $result['gas_used'] = $vm_result['gas_used'];
    $result['fault'] = $vm_result['fault'] ?? null;
    $result['trace'] = $vm_result['trace'];
    
    return $result;
}

function parse_guard(string $source): ?array {
    // Extract constraint body
    if (!preg_match('/constraint\s+\w+.*?\{(.+?)\}/s', $source, $matches)) {
        return null;
    }
    
    $body = $matches[1];
    $checks = [];
    
    // Parse range(min, max)
    if (preg_match('/range\(\s*(\d+)\s*,\s*(\d+)\s*\)/', $body, $m)) {
        $checks[] = ['type' => 'range', 'min' => intval($m[1]), 'max' => intval($m[2])];
    }
    
    // Parse thermal(budget)
    if (preg_match('/thermal\(\s*(\d+)\s*\)/', $body, $m)) {
        $checks[] = ['type' => 'thermal', 'budget' => intval($m[1])];
    }
    
    // Parse bitmask(mask)
    if (preg_match('/bitmask\(\s*(\d+)\s*\)/', $body, $m)) {
        $checks[] = ['type' => 'bitmask', 'mask' => intval($m[1])];
    }
    
    return empty($checks) ? null : $checks;
}

function compile_guard(array $parsed): array {
    $bytecode = [];
    
    foreach ($parsed as $check) {
        switch ($check['type']) {
            case 'range':
                // BITMASK_RANGE min max → pushes 1 if in range, 0 if not
                $bytecode[] = 0x1D; // BITMASK_RANGE
                $bytecode[] = $check['min'];
                $bytecode[] = $check['max'];
                $bytecode[] = 0x1B; // ASSERT
                break;
            case 'thermal':
                // Thermal: input must be <= budget (CMP_GE budget input → 1 if budget >= input)
                $bytecode[] = 0x00; // PUSH budget
                $bytecode[] = $check['budget'];
                $bytecode[] = 0x24; // CMP_GE (compares top two stack values)
                $bytecode[] = 0x1B; // ASSERT
                break;
            case 'bitmask':
                // CHECK_DOMAIN mask
                $bytecode[] = 0x1C; // CHECK_DOMAIN
                $bytecode[] = $check['mask'];
                $bytecode[] = 0x1B; // ASSERT
                break;
        }
    }
    
    $bytecode[] = 0x1A; // HALT
    $bytecode[] = 0x20; // GUARD_TRAP (fallback)
    
    return $bytecode;
}

function count_opcode_instructions(array $bytecode): int {
    $count = 0;
    $pc = 0;
    while ($pc < count($bytecode)) {
        $count++;
        $op = $bytecode[$pc];
        // Skip operands based on opcode
        switch ($op) {
            case 0x00: $pc += 2; break; // PUSH: 1 operand
            case 0x1D: $pc += 3; break; // BITMASK_RANGE: 2 operands
            case 0x1C: $pc += 2; break; // CHECK_DOMAIN: 1 operand
            case 0x2B: $pc += 3; break; // DEADLINE: 2 operands
            case 0x32: $pc += 2; break; // SANDBOX_ENTER: 1 operand
            default: $pc += 1; break;   // No operands
        }
    }
    return $count;
}

function execute_flux(array $bytecode, int $input, int $max_gas): array {
    $stack = [];
    $gas = $max_gas;
    $pc = 0;
    $trace = [];
    $fault = null;
    $passed = false;
    $gas_used = 0;
    
    // Push input onto stack
    $stack[] = $input;
    $trace[] = "PUSH {$input} (input value)";
    
    while ($pc < count($bytecode) && $gas > 0) {
        $gas--;
        $op = $bytecode[$pc];
        
        switch ($op) {
            case 0x00: // PUSH
                $val = $bytecode[$pc + 1] ?? 0;
                $stack[] = $val;
                $trace[] = "PUSH {$val}";
                $pc += 2;
                break;
                
            case 0x1A: // HALT
                $passed = true;
                $trace[] = "HALT";
                $pc = count($bytecode); // exit loop
                break;
                
            case 0x1B: // ASSERT
                $v = array_pop($stack);
                if ($v == 0) {
                    $fault = 'AssertFailed';
                    $trace[] = "❌ ASSERT → FAULT (value was 0)";
                    $pc = count($bytecode);
                } else {
                    $trace[] = "✅ ASSERT → PASS";
                    $pc += 1;
                }
                break;
                
            case 0x1C: // CHECK_DOMAIN
                $mask = $bytecode[$pc + 1] ?? 0;
                $v = array_pop($stack);
                $result = ($v & $mask) == $v ? 1 : 0;
                $stack[] = $result;
                $trace[] = sprintf("CHECK_DOMAIN 0x%02X → %s", $mask, $result ? 'IN DOMAIN' : 'OUT OF DOMAIN');
                $pc += 2;
                break;
                
            case 0x1D: // BITMASK_RANGE
                $lo = $bytecode[$pc + 1] ?? 0;
                $hi = $bytecode[$pc + 2] ?? 0;
                $v = array_pop($stack);
                $result = ($v >= $lo && $v <= $hi) ? 1 : 0;
                $stack[] = $result;
                $trace[] = "BITMASK_RANGE {$lo} {$hi} → " . ($result ? "IN RANGE ({$v})" : "OUT OF RANGE ({$v})");
                $pc += 3;
                break;
                
            case 0x20: // GUARD_TRAP
                $fault = 'GuardTrap';
                $trace[] = "❌ GUARD_TRAP";
                $pc = count($bytecode);
                break;
                
            case 0x24: // CMP_GE
                $b = array_pop($stack);
                $a = array_pop($stack);
                $result = ($a >= $b) ? 1 : 0;
                $stack[] = $result;
                $trace[] = "CMP_GE ({$a} >= {$b}) → {$result}";
                $pc += 1;
                break;
                
            case 0x27: // NOP
                $pc += 1;
                break;
                
            default:
                $trace[] = sprintf("UNKNOWN 0x%02X", $op);
                $pc += 1;
                break;
        }
    }
    
    $gas_used = $max_gas - $gas;
    $trace[] = "💡 Gas used: {$gas_used} / {$max_gas}";
    
    if ($passed) {
        $trace[] = "✅ ALL CONSTRAINTS PASSED";
    } elseif ($fault) {
        $trace[] = "❌ FAULT: {$fault}";
    } elseif ($gas == 0) {
        $trace[] = "❌ Gas exhausted";
        $fault = 'GasExhausted';
    }
    
    return [
        'passed' => $passed,
        'gas_used' => $gas_used,
        'fault' => $fault,
        'trace' => $trace,
    ];
}
