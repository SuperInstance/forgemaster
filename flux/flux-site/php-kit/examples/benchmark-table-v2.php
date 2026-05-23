<?php
/**
 * Safe-TOPS/W Benchmark Comparison Table
 * 
 * Drop-in widget showing certified vs uncertified AI hardware.
 * Uses the Safe-TOPS/W scoring system: performance × certification factor.
 */

// ─── Benchmark Data (v2.0 specification) ───

$chips = [
    [
        'name' => 'FLUX-LUCID (projected)',
        'vendor' => 'Cocapn (open)',
        'tops_w' => 20.17,
        's_cert' => 1.0,
        'cert_level' => 'DAL A (target)',
        'cert_standard' => 'DO-254C',
        'category' => 'certified',
        'notes' => 'FPGA RAU + constraint-enforced inference',
    ],
    [
        'name' => 'Hailo-8',
        'vendor' => 'Hailo',
        'tops_w' => 26.0,
        's_cert' => 0.204,
        'cert_level' => 'ASIL B',
        'cert_standard' => 'ISO 26262',
        'category' => 'certified',
        'notes' => 'Automotive-grade ADAS processor',
    ],
    [
        'name' => 'Mobileye EyeQ6',
        'vendor' => 'Intel/Mobileye',
        'tops_w' => 17.0,
        's_cert' => 0.294,
        'cert_level' => 'ASIL B',
        'cert_standard' => 'ISO 26262',
        'category' => 'certified',
        'notes' => 'Production ADAS chip',
    ],
    [
        'name' => 'NVIDIA Orin (safety)',
        'vendor' => 'NVIDIA',
        'tops_w' => 25.0,
        's_cert' => 0.0,
        'cert_level' => 'None',
        'cert_standard' => '—',
        'category' => 'uncertified',
        'notes' => 'Safety features are software-only',
    ],
    [
        'name' => 'NVIDIA H100',
        'vendor' => 'NVIDIA',
        'tops_w' => 51.0,
        's_cert' => 0.0,
        'cert_level' => 'None',
        'cert_standard' => '—',
        'category' => 'uncertified',
        'notes' => 'Data center GPU, no safety cert',
    ],
    [
        'name' => 'Qualcomm SA8775P',
        'vendor' => 'Qualcomm',
        'tops_w' => 30.0,
        's_cert' => 0.0,
        'cert_level' => 'None',
        'cert_standard' => '—',
        'category' => 'uncertified',
        'notes' => 'Automotive SoC, certification pending',
    ],
    [
        'name' => 'Google TPU v5',
        'vendor' => 'Google',
        'tops_w' => 45.0,
        's_cert' => 0.0,
        'cert_level' => 'None',
        'cert_standard' => '—',
        'category' => 'uncertified',
        'notes' => 'Cloud-only, no safety features',
    ],
    [
        'name' => 'AMD MI300X',
        'vendor' => 'AMD',
        'tops_w' => 38.0,
        's_cert' => 0.0,
        'cert_level' => 'None',
        'cert_standard' => '—',
        'category' => 'uncertified',
        'notes' => 'Data center APU, no safety cert',
    ],
];

// Calculate Safe-TOPS/W scores
foreach ($chips as &$chip) {
    $chip['safe_tops_w'] = $chip['tops_w'] * $chip['s_cert'];
}
unset($chip);

// Sort by Safe-TOPS/W descending
usort($chips, fn($a, $b) => $b['safe_tops_w'] <=> $a['safe_tops_w']);

// ─── API Mode ───
if (isset($_GET['api'])) {
    header('Content-Type: application/json');
    echo json_encode($chips, JSON_PRETTY_PRINT);
    exit;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Safe-TOPS/W Benchmark</title>
    <style>
        :root {
            --bg: #0a0e17;
            --surface: #111827;
            --border: #1e293b;
            --text: #e2e8f0;
            --muted: #64748b;
            --cyan: #06b6d4;
            --green: #10b981;
            --red: #ef4444;
            --amber: #f59e0b;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            padding: 2rem;
        }
        .container { max-width: 1100px; margin: 0 auto; }
        h1 { color: var(--cyan); font-size: 1.5rem; margin-bottom: 0.5rem; }
        .subtitle { color: var(--muted); font-size: 0.875rem; margin-bottom: 2rem; }
        .formula {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem 1.5rem;
            margin-bottom: 2rem;
            font-size: 1.1rem;
            text-align: center;
        }
        .formula .var { color: var(--cyan); font-weight: 700; }
        .formula .op { color: var(--amber); }
        table {
            width: 100%;
            border-collapse: collapse;
            background: var(--surface);
            border-radius: 8px;
            overflow: hidden;
        }
        th {
            background: #0f172a;
            padding: 0.75rem 1rem;
            text-align: left;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--muted);
            border-bottom: 1px solid var(--border);
        }
        td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
            font-size: 0.8125rem;
        }
        tr:last-child td { border-bottom: none; }
        tr:hover { background: #1e293b33; }
        .score-high { color: var(--green); font-weight: 700; font-size: 1rem; }
        .score-low { color: var(--red); }
        .score-zero { color: var(--muted); font-style: italic; }
        .cert-badge {
            display: inline-block;
            padding: 0.15rem 0.5rem;
            border-radius: 3px;
            font-size: 0.7rem;
            font-weight: 700;
        }
        .cert-yes { background: #064e3b; color: var(--green); }
        .cert-no { background: #1c1917; color: var(--muted); }
        .bar-container {
            width: 100px;
            height: 6px;
            background: var(--border);
            border-radius: 3px;
            overflow: hidden;
            display: inline-block;
            vertical-align: middle;
            margin-left: 0.5rem;
        }
        .bar-fill {
            height: 100%;
            border-radius: 3px;
            transition: width 0.3s ease;
        }
        .bar-certified { background: var(--green); }
        .bar-uncertified { background: var(--red); }
        .footnote {
            margin-top: 1.5rem;
            color: var(--muted);
            font-size: 0.75rem;
            line-height: 1.6;
        }
        .footnote a { color: var(--cyan); }
    </style>
</head>
<body>
<div class="container">
    <h1>⚡ Safe-TOPS/W Benchmark</h1>
    <p class="subtitle">AI inference performance weighted by safety certification level</p>
    
    <div class="formula">
        <span class="var">Safe-TOPS/W</span>
        <span class="op"> = </span>
        <span class="var">TOPS/W</span>
        <span class="op"> × </span>
        <span class="var">S<sub>cert</sub></span>
        <span style="color:var(--muted); font-size:0.8rem;"> where S<sub>cert</sub> ∈ [0.0, 1.0] based on certification level</span>
    </div>
    
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Chip</th>
                <th>Vendor</th>
                <th>TOPS/W</th>
                <th>S<sub>cert</sub></th>
                <th>Certification</th>
                <th>Safe-TOPS/W</th>
                <th></th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($chips as $i => $chip): ?>
            <tr>
                <td style="color:var(--muted)"><?= $i + 1 ?></td>
                <td style="font-weight:700"><?= htmlspecialchars($chip['name']) ?></td>
                <td style="color:var(--muted)"><?= htmlspecialchars($chip['vendor']) ?></td>
                <td><?= number_format($chip['tops_w'], 1) ?></td>
                <td><?= number_format($chip['s_cert'], 3) ?></td>
                <td>
                    <?php if ($chip['s_cert'] > 0): ?>
                        <span class="cert-badge cert-yes"><?= htmlspecialchars($chip['cert_level']) ?></span>
                        <span style="color:var(--muted);font-size:0.7rem"> <?= htmlspecialchars($chip['cert_standard']) ?></span>
                    <?php else: ?>
                        <span class="cert-badge cert-no">UNCERTIFIED</span>
                    <?php endif; ?>
                </td>
                <td class="<?= $chip['safe_tops_w'] > 1 ? 'score-high' : ($chip['safe_tops_w'] > 0 ? 'score-low' : 'score-zero') ?>">
                    <?= number_format($chip['safe_tops_w'], 2) ?>
                </td>
                <td>
                    <div class="bar-container">
                        <div class="bar-fill bar-<?= $chip['category'] ?>" 
                             style="width: <?= min(100, $chip['safe_tops_w'] / 20.17 * 100) ?>%"></div>
                    </div>
                </td>
            </tr>
            <?php endforeach; ?>
        </tbody>
    </table>
    
    <div class="footnote">
        <p><strong>S<sub>cert</sub> values:</strong> DAL A / ASIL D / SIL 4 = 1.0 | ASIL B = 0.2–0.3 | No certification = 0.0</p>
        <p><strong>FLUX-LUCID</strong> scores are projected based on FPGA synthesis (44,243 LUTs, 100MHz, 2.58W) and target DO-254C DAL A certification.</p>
        <p>Full benchmark specification: <a href="https://github.com/SuperInstance/JetsonClaw1-vessel/blob/master/docs/specs/safe-tops-w-benchmark-v1.md">safe-tops-w-benchmark-v1.md</a></p>
        <p>API: add <code>?api=1</code> to this URL for JSON output.</p>
    </div>
</div>
</body>
</html>
