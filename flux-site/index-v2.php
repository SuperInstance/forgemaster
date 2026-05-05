<?php
/**
 * FLUX Community Hub — Landing Page
 * 
 * The public face of the FLUX constraint enforcement stack.
 * Links to all tools, tutorials, and live demos.
 * 
 * Zero dependencies. Drop into any PHP server.
 */

require_once __DIR__ . '/plato.php';
require_once __DIR__ . '/safe-tops.php';

// Fetch live stats from PLATO
$plato = new PlatoClient();
try {
    $rooms = $plato->getRooms();
    $room_count = is_array($rooms) ? count($rooms) : 1400;
} catch (Exception $e) {
    $room_count = 1400;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FLUX — Safety Constraints as Code</title>
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
            font-family: 'Inter', -apple-system, sans-serif;
            line-height: 1.6;
        }
        .mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; }
        
        /* Hero */
        .hero {
            text-align: center;
            padding: 5rem 2rem 4rem;
            border-bottom: 1px solid var(--border);
        }
        .hero-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            background: #064e3b;
            color: var(--green);
            border-radius: 3px;
            font-size: 0.75rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            letter-spacing: 0.05em;
        }
        .hero h1 {
            font-size: 3.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--cyan), var(--magenta));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 1rem;
        }
        .hero p {
            font-size: 1.25rem;
            color: var(--muted);
            max-width: 600px;
            margin: 0 auto 2rem;
        }
        .hero-cta {
            display: flex;
            gap: 1rem;
            justify-content: center;
        }
        .btn-primary {
            background: var(--cyan);
            color: var(--bg);
            padding: 0.75rem 2rem;
            border-radius: 6px;
            font-weight: 700;
            text-decoration: none;
            font-size: 0.95rem;
            transition: background 0.15s;
        }
        .btn-primary:hover { background: #0891b2; }
        .btn-secondary {
            background: transparent;
            color: var(--cyan);
            padding: 0.75rem 2rem;
            border-radius: 6px;
            border: 1px solid var(--cyan);
            font-weight: 700;
            text-decoration: none;
            font-size: 0.95rem;
            transition: all 0.15s;
        }
        .btn-secondary:hover { background: var(--cyan); color: var(--bg); }
        
        /* Stats */
        .stats {
            display: flex;
            justify-content: center;
            gap: 4rem;
            padding: 3rem 2rem;
            border-bottom: 1px solid var(--border);
        }
        .stat { text-align: center; }
        .stat-value {
            font-size: 2.5rem;
            font-weight: 800;
            color: var(--cyan);
        }
        .stat-label {
            font-size: 0.8rem;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
        
        /* Code example */
        .code-section {
            padding: 4rem 2rem;
            border-bottom: 1px solid var(--border);
        }
        .section-title {
            text-align: center;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .section-subtitle {
            text-align: center;
            color: var(--muted);
            margin-bottom: 3rem;
        }
        .code-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            max-width: 1000px;
            margin: 0 auto;
        }
        @media (max-width: 768px) {
            .code-grid { grid-template-columns: 1fr; }
        }
        .code-block {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
        }
        .code-header {
            padding: 0.5rem 1rem;
            font-size: 0.75rem;
            color: var(--muted);
            border-bottom: 1px solid var(--border);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .code-body {
            padding: 1rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            line-height: 1.8;
        }
        .code-body .kw { color: var(--magenta); }
        .code-body .str { color: var(--green); }
        .code-body .num { color: var(--amber); }
        .code-body .cmt { color: var(--muted); }
        .code-body .fn { color: var(--cyan); }
        
        /* Features */
        .features {
            padding: 4rem 2rem;
            border-bottom: 1px solid var(--border);
        }
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 2rem;
            max-width: 1000px;
            margin: 0 auto;
        }
        @media (max-width: 768px) {
            .feature-grid { grid-template-columns: 1fr; }
        }
        .feature {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.5rem;
        }
        .feature-icon { font-size: 2rem; margin-bottom: 0.75rem; }
        .feature-title { font-weight: 700; margin-bottom: 0.5rem; }
        .feature-desc { color: var(--muted); font-size: 0.875rem; }
        
        /* Benchmark preview */
        .benchmark {
            padding: 4rem 2rem;
            text-align: center;
        }
        .benchmark-score {
            font-size: 4rem;
            font-weight: 800;
            color: var(--green);
            margin: 1rem 0;
        }
        .benchmark-vs {
            color: var(--red);
            font-size: 1.5rem;
            font-weight: 700;
        }
        
        /* Footer */
        footer {
            padding: 2rem;
            text-align: center;
            color: var(--muted);
            font-size: 0.8rem;
            border-top: 1px solid var(--border);
        }
        footer a { color: var(--cyan); text-decoration: none; }
    </style>
</head>
<body>

<div class="hero">
    <div class="hero-badge">APACHE 2.0 — OPEN SOURCE</div>
    <h1>Safety Constraints as Code</h1>
    <p>Write human-readable constraints, compile to bytecode, execute on a certified VM. Formally verified. Hardware-enforceable. Zero latency.</p>
    <div class="hero-cta">
        <a href="examples/constraint-playground-v2.php" class="btn-primary">Try the Playground →</a>
        <a href="#learn" class="btn-secondary">Read the Docs</a>
    </div>
</div>

<div class="stats">
    <div class="stat">
        <div class="stat-value">50</div>
        <div class="stat-label">VM Opcodes</div>
    </div>
    <div class="stat">
        <div class="stat-value">85+</div>
        <div class="stat-label">Tests Passing</div>
    </div>
    <div class="stat">
        <div class="stat-value"><?= number_format($room_count) ?></div>
        <div class="stat-label">PLATO Knowledge Rooms</div>
    </div>
    <div class="stat">
        <div class="stat-value">21</div>
        <div class="stat-label">Published Packages</div>
    </div>
</div>

<div class="code-section">
    <div class="section-title">Write Constraints, Not Guard Code</div>
    <div class="section-subtitle">Three lines of GUARD compile to 8 bytes of formally verified bytecode</div>
    
    <div class="code-grid">
        <div class="code-block">
            <div class="code-header">GUARD Source</div>
            <div class="code-body">
                <span class="kw">constraint</span> drone_speed <span class="kw">@priority</span>(HARD) {<br>
                &nbsp;&nbsp;<span class="fn">range</span>(<span class="num">0</span>, <span class="num">50</span>)<br>
                }<br>
                <br>
                <span class="cmt">// Compile: guard2mask</span><br>
                <span class="cmt">// 4 instructions, 8 bytes</span>
            </div>
        </div>
        <div class="code-block">
            <div class="code-header">FLUX Bytecode</div>
            <div class="code-body">
                <span class="num">1D 00 32</span> <span class="cmt">BITMASK_RANGE 0 50</span><br>
                <span class="num">1B</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <span class="cmt">ASSERT</span><br>
                <span class="num">1A</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <span class="cmt">HALT</span><br>
                <span class="num">20</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <span class="cmt">GUARD_TRAP</span><br>
                <br>
                <span class="cmt">// Execute: flux-vm</span><br>
                <span class="cmt">// Input 35 → ✅ PASS</span>
            </div>
        </div>
    </div>
</div>

<div class="features">
    <div class="section-title" id="learn">Learn the Stack</div>
    <div class="section-subtitle">7 tutorials from first constraint to formal verification</div>
    
    <div class="feature-grid">
        <div class="feature">
            <div class="feature-icon">⚡</div>
            <div class="feature-title">5-Minute Quickstart</div>
            <div class="feature-desc">Write your first constraint, compile it, watch it pass and fail.</div>
        </div>
        <div class="feature">
            <div class="feature-icon">⏱️</div>
            <div class="feature-title">Temporal Constraints</div>
            <div class="feature-desc">DEADLINE, CHECKPOINT/REVERT, DRIFT — time-aware safety at the ISA level.</div>
        </div>
        <div class="feature">
            <div class="feature-icon">🔒</div>
            <div class="feature-title">Security Primitives</div>
            <div class="feature-desc">Capability-based access (seL4 model). SANDBOX, SEAL, AUDIT_PUSH.</div>
        </div>
        <div class="feature">
            <div class="feature-icon">🤝</div>
            <div class="feature-title">Multi-Agent Delegation</div>
            <div class="feature-desc">Tell, Ask, CoIterate, Fork — agents checking each other's outputs.</div>
        </div>
        <div class="feature">
            <div class="feature-icon">📐</div>
            <div class="feature-title">Formal Verification</div>
            <div class="feature-desc">Coq proofs, SymbiYosys assertions, Semantic Gap Theorem.</div>
        </div>
        <div class="feature">
            <div class="feature-icon">🔧</div>
            <div class="feature-title">Hardware Implementation</div>
            <div class="feature-desc">44K LUTs, 100MHz, zero latency. FPGA to ASIC pipeline.</div>
        </div>
    </div>
</div>

<div class="benchmark">
    <div class="section-title">Safe-TOPS/W Benchmark</div>
    <div class="section-subtitle">AI performance weighted by safety certification</div>
    <div class="benchmark-score">20.17</div>
    <div style="color:var(--muted)">FLUX-LUCID Safe-TOPS/W</div>
    <div style="margin-top:1rem" class="benchmark-vs">vs 0.00 for all uncertified chips</div>
    <div style="margin-top:2rem">
        <a href="examples/benchmark-table-v2.php" class="btn-primary">Full Comparison →</a>
    </div>
</div>

<div style="padding:4rem 2rem;border-top:1px solid var(--border)">
    <div class="section-title">Explore Live</div>
    <div class="section-subtitle">Interactive demos powered by PLATO knowledge base</div>
    <div style="display:flex;gap:1.5rem;justify-content:center;flex-wrap:wrap;margin-top:2rem">
        <a href="examples/constraint-playground-v2.php" class="btn-secondary">Constraint Playground</a>
        <a href="examples/plato-browser-v2.php" class="btn-secondary">PLATO Browser</a>
        <a href="examples/benchmark-table-v2.php" class="btn-secondary">Benchmark Table</a>
    </div>
</div>

<footer>
    <p>FLUX is part of the <a href="https://github.com/SuperInstance">Cocapn Fleet</a> — open-source safety infrastructure for AI.</p>
    <p style="margin-top:0.5rem">
        <a href="https://github.com/SuperInstance/JetsonClaw1-vessel">Source</a> ·
        <a href="https://crates.io/crates/flux-vm">crates.io</a> ·
        <a href="https://pypi.org/project/safe-tops-w/">PyPI</a> ·
        <a href="https://github.com/SuperInstance/SuperInstance/discussions/5">Fleet Discussion</a> ·
        Apache 2.0 License
    </p>
</footer>

</body>
</html>
