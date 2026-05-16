<?php
/**
 * FLUX Playground — Write GUARD, see it compile and execute in real time
 */
require_once __DIR__ . '/../lib/flux-vm.php';

$title = 'FLUX Playground';
$examples = [
    'evtol' => [
        'name' => 'eVTOL Altitude Check',
        'guard' => "constraint eVTOL_altitude @priority(HARD) {\n    range(0, 15000)\n    bitmask(0x3F)\n}",
        'bytecode' => '1D00961B003F1C3F1B1A20',
        'input' => 8500,
        'description' => 'Check if eVTOL altitude is within safe range [0, 15000] and sensor mask is valid',
    ],
    'automotive' => [
        'name' => 'Automotive Speed Governor',
        'guard' => "constraint speed_governor @priority(HARD) {\n    range(0, 250)\n    thermal(5.0)\n}",
        'bytecode' => '1D00FA1B0005241B1A20',
        'input' => 120,
        'description' => 'Enforce maximum speed and thermal budget for autonomous vehicle',
    ],
    'robotics' => [
        'name' => 'Robot Joint Limits',
        'guard' => "constraint joint_limits @priority(HARD) {\n    range(-180, 180)\n}",
        'bytecode' => '1D4C4CB41B1A20',
        'input' => 45,
        'description' => 'Check robot joint angle is within mechanical limits',
    ],
    'fault' => [
        'name' => 'Constraint Violation (triggers fault)',
        'guard' => "constraint out_of_bounds @priority(HARD) {\n    range(0, 100)\n}",
        'bytecode' => '1D00641B1A20',
        'input' => 200,
        'description' => 'Input value 200 exceeds range [0, 100] — watch the VM fault',
    ],
];

$selected = $_GET['example'] ?? 'evtol';
$current = $examples[$selected] ?? $examples['evtol'];

// Handle AJAX execution request
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action'])) {
    header('Content-Type: application/json');
    $vm = new FluxVM();

    if ($_POST['action'] === 'execute') {
        $bytecode = $_POST['bytecode'] ?? '';
        $input = (int)($_POST['input'] ?? 0);

        // Prepend PUSH input to the bytecode
        $input_bytecode = sprintf('00%02X', min(255, max(0, $input)));
        $full_bytecode = $input_bytecode . $bytecode;

        $result = $vm->simulate($full_bytecode);
        echo json_encode($result);
        exit;
    }

    if ($_POST['action'] === 'compile') {
        // Simplified compilation — map GUARD patterns to bytecode
        $source = $_POST['source'] ?? '';
        $bytecode = '';

        if (preg_match('/range\((\d+),\s*(\d+)\)/', $source, $m)) {
            $lo = min(255, (int)$m[1]);
            $hi = min(255, (int)$m[2]);
            $bytecode .= sprintf('1D%02X%02X1B', $lo, $hi); // BITMASK_RANGE lo hi ASSERT
        }
        if (preg_match('/bitmask\((0x[0-9A-Fa-f]+|\d+)\)/', $source, $m)) {
            $mask = intval($m[1], 0);
            $mask = min(255, $mask);
            $bytecode .= sprintf('00%02X1C%02X1B', $mask, $mask); // PUSH mask, CHECK_DOMAIN mask, ASSERT
        }
        if (preg_match('/thermal\(([\d.]+)\)/', $source, $m)) {
            $budget = min(255, (int)(float)$m[1]);
            $bytecode .= sprintf('00%02X241B', $budget); // PUSH budget, CMP_GE, ASSERT
        }
        $bytecode .= '1A20'; // HALT, GUARD_TRAP

        echo json_encode(['bytecode' => $bytecode, 'source_length' => strlen($source)]);
        exit;
    }

    echo json_encode(['error' => 'Unknown action']);
    exit;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= $title ?> — FLUX</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header>
        <nav>
            <a href="/" class="logo">⚡ FLUX</a>
            <a href="/playground" style="color: var(--accent-cyan)">Playground</a>
            <a href="/learn">Learn</a>
            <a href="/spec">Spec</a>
            <a href="/benchmark">Benchmark</a>
            <a href="https://github.com/SuperInstance/JetsonClaw1-vessel" class="github">GitHub</a>
        </nav>
    </header>

    <main>
        <h1>FLUX Playground</h1>
        <p class="section-desc">Write GUARD constraints, compile to FLUX bytecode, execute on the VM. All in the browser.</p>

        <div class="example-selector">
            <strong>Examples:</strong>
            <?php foreach ($examples as $key => $ex): ?>
                <a href="/playground?example=<?= $key ?>" class="example-btn <?= $key === $selected ? 'active' : '' ?>">
                    <?= htmlspecialchars($ex['name']) ?>
                </a>
            <?php endforeach; ?>
        </div>

        <p class="example-desc"><?= htmlspecialchars($current['description']) ?></p>

        <div class="playground-container">
            <div class="playground-panel">
                <h3>📝 GUARD Source</h3>
                <textarea id="guard-source" rows="8" spellcheck="false"><?= htmlspecialchars($current['guard']) ?></textarea>
                <button id="compile-btn" class="cta primary">Compile →</button>
            </div>

            <div class="playground-panel">
                <h3>⚙️ FLUX Bytecode</h3>
                <pre id="flux-bytecode" class="bytecode-display"><?= chunk_split(strtoupper($current['bytecode']), 2, ' ') ?></pre>
                <div class="input-control">
                    <label>Input Value: <input type="number" id="input-value" value="<?= $current['input'] ?>" min="0" max="255"></label>
                </div>
                <button id="execute-btn" class="cta primary">▶ Execute</button>
            </div>

            <div class="playground-panel">
                <h3>📊 VM Result</h3>
                <div id="vm-result" class="vm-result">
                    <p class="hint">Click Execute to run the constraint program</p>
                </div>
                <div id="vm-trace" class="trace" style="display:none;"></div>
            </div>
        </div>

        <section class="opcode-reference">
            <h2>Opcode Quick Reference</h2>
            <table class="opcode-table">
                <thead><tr><th>Hex</th><th>Mnemonic</th><th>Effect</th></tr></thead>
                <tbody>
                    <tr><td>0x00</td><td>PUSH val</td><td>Push value onto stack</td></tr>
                    <tr><td>0x1A</td><td>HALT</td><td>Normal termination</td></tr>
                    <tr><td>0x1B</td><td>ASSERT</td><td>Trap if stack top is 0</td></tr>
                    <tr><td>0x1C</td><td>CHECK_DOMAIN mask</td><td>Bitwise AND with mask</td></tr>
                    <tr><td>0x1D</td><td>BITMASK_RANGE lo hi</td><td>Check if in [lo, hi]</td></tr>
                    <tr><td>0x20</td><td>GUARD_TRAP</td><td>Immediate safety fault</td></tr>
                    <tr><td>0x24</td><td>CMP_GE</td><td>Compare greater-or-equal</td></tr>
                </tbody>
            </table>
            <p><a href="/spec">Full ISA specification (50 opcodes) →</a></p>
        </section>
    </main>

    <script>
    const guardSource = document.getElementById('guard-source');
    const fluxBytecode = document.getElementById('flux-bytecode');
    const inputValue = document.getElementById('input-value');
    const vmResult = document.getElementById('vm-result');
    const vmTrace = document.getElementById('vm-trace');

    let currentBytecode = '<?= $current['bytecode'] ?>';

    document.getElementById('compile-btn').addEventListener('click', async () => {
        const formData = new FormData();
        formData.append('action', 'compile');
        formData.append('source', guardSource.value);

        const resp = await fetch('/playground', { method: 'POST', body: formData });
        const data = await resp.json();

        if (data.bytecode) {
            currentBytecode = data.bytecode;
            fluxBytecode.textContent = data.bytecode.match(/.{1,2}/g).join(' ').toUpperCase();
        }
    });

    document.getElementById('execute-btn').addEventListener('click', async () => {
        const formData = new FormData();
        formData.append('action', 'execute');
        formData.append('bytecode', currentBytecode);
        formData.append('input', inputValue.value);

        vmResult.innerHTML = '<p>Executing...</p>';

        const resp = await fetch('/playground', { method: 'POST', body: formData });
        const data = await resp.json();

        if (data.error) {
            vmResult.innerHTML = '<div class="result fail"><span class="status-icon">⚠️</span> ' + data.error + '</div>';
            return;
        }

        const isPass = data.status === 'halted' && !data.fault;
        vmResult.innerHTML = `
            <div class="result ${isPass ? 'pass' : 'fail'}">
                <span class="status-icon">${isPass ? '✅' : '❌'}</span>
                <span class="status-text">${isPass ? 'ALL CONSTRAINTS PASSED' : 'FAULT: ' + (data.fault || 'Unknown')}</span>
            </div>
            <div class="gas-meter">
                Gas: ${data.gas_used} / ${data.gas_used + data.gas_remaining} used
                <div class="gas-bar" style="width: ${(data.gas_used / (data.gas_used + data.gas_remaining)) * 100}%"></div>
            </div>
        `;

        if (data.trace && data.trace.length > 0) {
            vmTrace.style.display = 'block';
            vmTrace.innerHTML = data.trace.map(t => '<div class="trace-line">' + t + '</div>').join('');
        }
    });

    // Auto-execute on load
    document.getElementById('execute-btn').click();
    </script>

    <style>
    .example-selector { margin: 1.5rem 0; display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; }
    .example-btn {
        padding: 0.4rem 0.8rem;
        border: 1px solid var(--border);
        border-radius: 4px;
        font-size: 0.85rem;
        color: var(--text-secondary);
    }
    .example-btn.active { border-color: var(--accent-cyan); color: var(--accent-cyan); }
    .example-desc { color: var(--text-secondary); margin-bottom: 1.5rem; }

    .playground-container { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; }
    .playground-panel {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1.5rem;
    }
    .playground-panel h3 { color: var(--accent-cyan); font-size: 0.85rem; margin-bottom: 1rem; font-family: var(--font-mono); }
    textarea {
        width: 100%;
        background: var(--bg-code);
        color: var(--accent-green);
        border: 1px solid var(--border);
        border-radius: 4px;
        padding: 1rem;
        font-family: var(--font-mono);
        font-size: 0.9rem;
        resize: vertical;
    }
    .bytecode-display {
        background: var(--bg-code);
        color: var(--accent-amber);
        padding: 1rem;
        border-radius: 4px;
        font-family: var(--font-mono);
        font-size: 0.9rem;
        min-height: 100px;
    }
    .input-control { margin: 1rem 0; }
    .input-control input {
        background: var(--bg-code);
        border: 1px solid var(--border);
        color: var(--text-primary);
        padding: 0.4rem 0.8rem;
        border-radius: 4px;
        font-family: var(--font-mono);
        width: 80px;
    }
    .vm-result .hint { color: var(--text-secondary); font-style: italic; }
    .result.fail { background: rgba(248, 113, 113, 0.1); border: 1px solid rgba(248, 113, 113, 0.3); }
    .vm-result { min-height: 80px; }
    button { margin-top: 1rem; }

    .opcode-reference { margin-top: 3rem; }
    .opcode-table { width: 100%; border-collapse: collapse; font-family: var(--font-mono); font-size: 0.85rem; }
    .opcode-table th, .opcode-table td { padding: 0.5rem 1rem; border-bottom: 1px solid var(--border); text-align: left; }

    @media (max-width: 900px) {
        .playground-container { grid-template-columns: 1fr; }
    }
    </style>
</body>
</html>
