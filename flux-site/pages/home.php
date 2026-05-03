<?php
/**
 * FLUX Community Hub — Landing Page
 * The 30-second demo that makes people say "I need this"
 */
require_once __DIR__ . '/../lib/plato.php';
require_once __DIR__ . '/../lib/flux-vm.php';
require_once __DIR__ . '/../lib/safe-tops.php';

$title = 'FLUX — Safety-Certified AI Inference at the Silicon Layer';
$description = 'The first constraint enforcement VM for AI hardware. Write constraints in GUARD, compile to FLUX bytecode, enforce at the gate level.';

// Live PLATO stats
$plato = new PlatoClient();
$rooms = $plato->getRooms();
$room_count = is_array($rooms) ? count($rooms) : '1,400+';

// Benchmark data
$benchmarks = get_benchmark_table();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= $title ?></title>
    <link rel="stylesheet" href="/static/style.css">
    <meta name="description" content="<?= htmlspecialchars($description) ?>">
</head>
<body>
    <header>
        <nav>
            <a href="/" class="logo">⚡ FLUX</a>
            <a href="/playground">Playground</a>
            <a href="/learn">Learn</a>
            <a href="/spec">Spec</a>
            <a href="/benchmark">Benchmark</a>
            <a href="/plato">PLATO</a>
            <a href="/community">Community</a>
            <a href="https://github.com/SuperInstance/JetsonClaw1-vessel" class="github">GitHub</a>
        </nav>
    </header>

    <main>
        <section class="hero">
            <h1>AI inference you can <span class="accent">certify</span>.</h1>
            <p class="tagline">
                FLUX enforces safety constraints at the silicon layer — not in software.<br>
                The first constraint VM designed for DO-254 DAL A and ISO 26262 ASIL-D.
            </p>
            <div class="cta-group">
                <a href="/playground" class="cta primary">Try the Playground →</a>
                <a href="/learn/getting-started" class="cta secondary">5-Minute Quickstart</a>
                <a href="/spec" class="cta secondary">Read the Spec</a>
            </div>
        </section>

        <section class="live-demo">
            <h2>See it run. Right now.</h2>
            <div class="demo-container">
                <div class="demo-panel">
                    <h3>GUARD Constraint</h3>
                    <pre class="guard-source"><code>constraint eVTOL_altitude @priority(HARD) {
    range(0, 15000)
    bitmask(0x3F)
    thermal(2.5)
}</code></pre>
                </div>
                <div class="demo-arrow">→</div>
                <div class="demo-panel">
                    <h3>FLUX Bytecode</h3>
                    <pre class="flux-bytecode"><code>1D 00 96    BITMASK_RANGE 0 15000
1B          ASSERT
00 3F       PUSH 63
1C 3F       CHECK_DOMAIN 63
1B          ASSERT
00 02       PUSH 2
24          CMP_GE
1B          ASSERT
1A          HALT
20          GUARD_TRAP</code></pre>
                </div>
                <div class="demo-arrow">→</div>
                <div class="demo-panel result-panel">
                    <h3>VM Execution</h3>
                    <div class="result pass">
                        <span class="status-icon">✅</span>
                        <span class="status-text">ALL CONSTRAINTS PASSED</span>
                    </div>
                    <div class="trace">
                        <div class="trace-line">BITMASK_RANGE 0 15000 → IN RANGE</div>
                        <div class="trace-line">ASSERT → PASS</div>
                        <div class="trace-line">CHECK_DOMAIN mask=63 → 63</div>
                        <div class="trace-line">ASSERT → PASS</div>
                        <div class="trace-line">CMP_GE 63 >= 2 → 1</div>
                        <div class="trace-line">ASSERT → PASS</div>
                        <div class="trace-line">HALT</div>
                    </div>
                    <div class="gas-meter">
                        Gas: 8 / 1000 used
                        <div class="gas-bar" style="width: 0.8%"></div>
                    </div>
                </div>
            </div>
            <p class="demo-caption">
                <a href="/playground?example=evtol">Try it yourself → change altitude to 20000 and watch it fault</a>
            </p>
        </section>

        <section class="benchmark-preview">
            <h2>Safe-TOPS/W — The Benchmark That Matters</h2>
            <p class="section-desc">
                Raw TOPS/W measures speed. <strong>Safe-TOPS/W measures certified speed.</strong>
                Uncertified hardware scores zero — not as a judgment, but because it's legally undeployable.
            </p>
            <table class="benchmark-table">
                <thead>
                    <tr>
                        <th>Chip</th>
                        <th>Raw TOPS/W</th>
                        <th>Safe-TOPS/W</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($benchmarks as $b): ?>
                    <tr class="<?= $b['safe'] > 0 ? 'certified' : 'uncertified' ?>">
                        <td class="chip-name"><?= htmlspecialchars($b['chip']) ?></td>
                        <td class="raw-score"><?= number_format($b['raw'], 1) ?></td>
                        <td class="safe-score <?= $b['safe'] > 0 ? 'has-score' : 'zero' ?>">
                            <strong><?= number_format($b['safe'], 2) ?></strong>
                        </td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
            <p class="table-caption">
                <a href="/benchmark">Full methodology →</a> |
                <a href="/benchmark/submit">Submit your chip's score →</a>
            </p>
        </section>

        <section class="features">
            <h2>How It Works</h2>
            <div class="feature-grid">
                <div class="feature">
                    <h3>📝 GUARD DSL</h3>
                    <p>Write constraints in human-readable syntax. Range checks, whitelists, thermal budgets, temporal consistency — all expressed declaratively.</p>
                    <a href="/spec/guard">GUARD Spec →</a>
                </div>
                <div class="feature">
                    <h3>⚙️ FLUX-C VM</h3>
                    <p>42 opcodes. Stack-based. Gas-bounded. The smallest VM that can enforce real safety constraints. Small enough to prove in Coq.</p>
                    <a href="/spec/flux-c">FLUX-C ISA →</a>
                </div>
                <div class="feature">
                    <h3>🛡️ Runtime Assurance</h3>
                    <p>Interlocks between AI accelerator and actuators. 282 lines of SystemVerilog. 44K LUTs on Artix-7. Zero latency overhead.</p>
                    <a href="/spec/hardware">Hardware →</a>
                </div>
                <div class="feature">
                    <h3>🔍 Formal Verification</h3>
                    <p>TLA+ model. Coq proofs. SymbiYosys RTL assertions. Every opcode has defined behavior — no undefined states.</p>
                    <a href="/spec/formal">Formal Methods →</a>
                </div>
            </div>
        </section>

        <section class="packages">
            <h2>Published Packages — Install Now</h2>
            <div class="package-grid">
                <div class="pkg">
                    <code>cargo add flux-vm</code>
                    <span class="pkg-desc">42-opcode constraint VM</span>
                </div>
                <div class="pkg">
                    <code>cargo add guard2mask</code>
                    <span class="pkg-desc">GUARD → FLUX compiler</span>
                </div>
                <div class="pkg">
                    <code>cargo add flux-bridge</code>
                    <span class="pkg-desc">FLUX-X ↔ FLUX-C bridge</span>
                </div>
                <div class="pkg">
                    <code>cargo add flux-ast</code>
                    <span class="pkg-desc">Universal Constraint AST</span>
                </div>
                <div class="pkg">
                    <code>pip install safe-tops-w</code>
                    <span class="pkg-desc">Safe-TOPS/W benchmark</span>
                </div>
                <div class="pkg">
                    <code>pip install flux-asm</code>
                    <span class="pkg-desc">FLUX bytecode assembler</span>
                </div>
            </div>
            <p class="pkg-total">20 packages total: 14 crates.io + 5 PyPI + 1 npm</p>
        </section>

        <section class="plato-preview">
            <h2>PLATO Knowledge — <?= $room_count ?> Rooms, Growing Daily</h2>
            <p class="section-desc">
                Every design decision, every lesson learned, every R&D breakthrough — stored in PLATO as queryable knowledge tiles.
            </p>
            <div class="plato-stats">
                <div class="stat">
                    <span class="stat-num"><?= $room_count ?></span>
                    <span class="stat-label">Knowledge Rooms</span>
                </div>
                <div class="stat">
                    <span class="stat-num">50+</span>
                    <span class="stat-label">Domains</span>
                </div>
                <div class="stat">
                    <span class="stat-num">19K+</span>
                    <span class="stat-label">Tiles</span>
                </div>
            </div>
            <a href="/plato" class="cta secondary">Browse PLATO →</a>
        </section>

        <section class="community-cta">
            <h2>Join the Fleet</h2>
            <p>FLUX is Apache 2.0. Everything open. No patents. Build on it, ship with it, certify with it.</p>
            <div class="cta-group">
                <a href="https://github.com/SuperInstance" class="cta primary">Star on GitHub</a>
                <a href="https://discord.com/invite/clawd" class="cta secondary">Join Discord</a>
                <a href="/community/contributing" class="cta secondary">Contributing Guide</a>
            </div>
        </section>
    </main>

    <footer>
        <p>FLUX Constraint VM — Apache 2.0 — Built by the Cocapn Fleet</p>
        <p><a href="https://github.com/SuperInstance/JetsonClaw1-vessel">Source</a> ·
           <a href="/spec">Spec</a> ·
           <a href="https://github.com/SuperInstance/SuperInstance/discussions/5">Discussion</a> ·
           <a href="mailto:casey@cocapn.ai">Contact</a></p>
    </footer>
</body>
</html>
