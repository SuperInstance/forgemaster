<?php
/**
 * Drop-in FLUX Constraint Playground
 * Usage: include 'php-kit/examples/constraint-playground.php';
 * 
 * Fully self-contained — compiles GUARD, runs VM, shows results.
 * No external services needed.
 */
require_once __DIR__ . '/../flux-compiler.php';
require_once __DIR__ . '/../flux-vm.php';

// Handle AJAX requests
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action'])) {
    header('Content-Type: application/json');
    
    if ($_POST['action'] === 'compile') {
        $compiler = new FluxCompiler();
        $result = $compiler->compile($_POST['source'] ?? '');
        echo json_encode($result);
        exit;
    }
    
    if ($_POST['action'] === 'execute') {
        $vm = new FluxVM();
        $bytecode = $_POST['bytecode'] ?? '';
        $input = (int)($_POST['input'] ?? 0);
        // Prepend PUSH input
        $full = sprintf('00%02X', min(255, max(0, $input))) . $bytecode;
        echo json_encode($vm->simulate($full));
        exit;
    }
    
    echo json_encode(['error' => 'Unknown action']);
    exit;
}

// Default example
$default_guard = "constraint eVTOL_altitude @priority(HARD) {\n    range(0, 15000)\n    bitmask(0x3F)\n}";
?>
<div class="flux-playground">
    <div class="pg-grid">
        <div class="pg-panel">
            <label><strong>GUARD Source</strong></label>
            <textarea id="pg-source" rows="6"><?= htmlspecialchars($default_guard) ?></textarea>
            <button onclick="fluxCompile()" class="pg-btn">Compile →</button>
        </div>
        <div class="pg-panel">
            <label><strong>FLUX Bytecode</strong></label>
            <pre id="pg-bytecode">Click Compile</pre>
            <label>Input: <input type="number" id="pg-input" value="8500" min="0" max="255" style="width:60px"></label>
            <button onclick="fluxExecute()" class="pg-btn">▶ Run</button>
        </div>
        <div class="pg-panel">
            <label><strong>Result</strong></label>
            <div id="pg-result">Ready</div>
        </div>
    </div>
</div>
<script>
function fluxCompile() {
    const fd = new FormData();
    fd.append('action', 'compile');
    fd.append('source', document.getElementById('pg-source').value);
    fetch(location.href, {method:'POST', body:fd})
        .then(r => r.json())
        .then(d => {
            document.getElementById('pg-bytecode').textContent = d.bytecode_formatted || d.bytecode || 'Error';
            document.getElementById('pg-bytecode').dataset.raw = d.bytecode || '';
        });
}
function fluxExecute() {
    const bc = document.getElementById('pg-bytecode').dataset.raw;
    if (!bc) { alert('Compile first'); return; }
    const fd = new FormData();
    fd.append('action', 'execute');
    fd.append('bytecode', bc);
    fd.append('input', document.getElementById('pg-input').value);
    fetch(location.href, {method:'POST', body:fd})
        .then(r => r.json())
        .then(d => {
            const pass = d.status === 'halted' && !d.fault;
            document.getElementById('pg-result').innerHTML =
                '<div class="pg-' + (pass ? 'pass' : 'fail') + '">' +
                (pass ? '✅ PASS' : '❌ FAULT: ' + (d.fault||'unknown')) +
                '<br><small>Gas: ' + d.gas_used + '/' + (d.gas_used+d.gas_remaining) + '</small>' +
                '</div>';
        });
}
</script>
<style>
.pg-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:1rem; }
.pg-panel { background:#111827; border:1px solid #1e293b; border-radius:6px; padding:1rem; }
.pg-panel textarea { width:100%; background:#0d1117; color:#34d399; border:1px solid #1e293b; font-family:monospace; font-size:0.85rem; padding:0.5rem; }
.pg-panel pre { background:#0d1117; color:#fbbf24; padding:0.5rem; font-family:monospace; font-size:0.85rem; min-height:60px; border-radius:4px; overflow:auto; }
.pg-btn { background:#22d3ee; color:#0a0e17; border:none; padding:0.4rem 1rem; border-radius:4px; cursor:pointer; font-weight:600; margin-top:0.5rem; }
.pg-pass { color:#34d399; } .pg-fail { color:#f87171; }
@media(max-width:768px) { .pg-grid { grid-template-columns:1fr; } }
</style>
