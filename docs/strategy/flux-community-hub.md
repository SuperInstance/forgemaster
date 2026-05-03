# FLUX Community Hub — Architecture Design

## The Vision

Not a documentation site. A **living playground** where people:
- Write GUARD constraints and watch them compile to FLUX bytecode in real time
- See Safe-TOPS/W scores update live as they adjust parameters
- Browse PLATO knowledge as a living encyclopedia
- Deploy constraint programs to a shared test FPGA
- Watch the fleet's constraint VMs running in real time

## Why PHP

Not WordPress. Raw PHP 8.2+ talking directly to:

1. **PLATO** (`http://147.224.38.131:8847`) — live room/tile queries rendered as HTML
2. **FLUX VM** — PHP FFI calling the Rust `flux-vm` compiled to a shared library
3. **Safe-TOPS/W scorer** — PHP wrapper around the Python benchmark
4. **FLUX assembler** — PHP executing `flux_asm.py` and returning bytecode

PHP gives us:
- No build step — edit a file, refresh, it's live ("on-the-fly changing")
- Direct API calls with `file_get_contents()` / cURL
- Session state for interactive playgrounds
- SQLite for local caching of PLATO tiles
- Zero deployment friction — `git pull` and it's live

## Site Structure

### flux.cocapn.ai (or flux-lang.org)

```
/                       → Landing: what FLUX is, why it matters, 30-second demo
/play                   → GUARD→FLUX playground (interactive, real-time)
/playground             → Full IDE: write GUARD, compile, execute on VM, debug
/benchmark              → Safe-TOPS/W live comparison table
/benchmark/submit       → Submit your chip's score
/learn                  → Tutorials (beginner → expert)
/learn/getting-started  → 5-minute quickstart
/learn/eVTOL            → Full eVTOL constraint example
/learn/automotive       → ISO 26262 constraint example
/learn/medical          → IEC 62304 constraint example
/spec                   → FLUX ISA specification (all 50 opcodes)
/spec/flux-c            → FLUX-C: 42 opcodes, certifiable
/spec/flux-x            → FLUX-X: 247 opcodes, general compute
/spec/temporal          → v3.0 temporal opcodes
/spec/security          → v3.0 security primitives
/spec/ast               → Universal Constraint AST
/packages               → Published packages (auto-generated from crates.io/PyPI)
/packages/flux-vm       → Per-package docs with examples
/plato                  → PLATO knowledge browser (live)
/plato/room/{id}        → Single room with all tiles
/plato/search?q=        → Full-text search across tiles
/fleet                  → Live fleet dashboard (who's online, what's running)
/community              → Discord link, GitHub discussions, contributing guide
/community/examples     → User-submitted constraint programs
```

## The Playground (The Killer Feature)

```
┌──────────────────────────────────────────────────┐
│  FLUX Constraint Playground                       │
│                                                   │
│  ┌─ GUARD Source ─────────┐  ┌─ FLUX Bytecode ─┐ │
│  │ constraint eVTOL_alt   │  │ 1D 00 96        │ │
│  │   @priority(HARD) {    │  │ 1B              │ │
│  │   range(0, 15000)      │  │ 1A 20           │ │
│  │   bitmask(0x3F)        │  │                 │ │
│  │ }                      │  │ 5 bytes         │ │
│  └────────────────────────┘  └─────────────────┘ │
│                                                   │
│  ┌─ Execute ─────────────────────────────────────┐│
│  │ Input: altitude = 8500 ft                     ││
│  │ [▶ Run]                                       ││
│  │                                               ││
│  │ Result: ✅ PASS (gas used: 4/1000)            ││
│  │ Stack trace: PUSH 8500 → BITMASK_RANGE → PASS ││
│  └───────────────────────────────────────────────┘│
│                                                   │
│  Try: change altitude to 20000 → watch it fault   │
│  Try: add thermal(2.5) constraint                 │
│  Share: [Copy Link] [Embed] [Export .flux]        │
└──────────────────────────────────────────────────┘
```

Every example in every tutorial is LIVE — not a code snippet, a running program.

## PHP Architecture

```
index.php              → Router (all URLs flow through here)
├── lib/
│   ├── plato.php      → PLATO API client (GET /rooms, GET /room/{id})
│   ├── flux-vm.php    → FLUX VM bridge (FFI or proc call to Rust binary)
│   ├── flux-asm.php   → Assembler bridge (calls flux_asm.py)
│   ├── safe-tops.php  → Safe-TOPS/W scorer
│   ├── markdown.php   → Markdown renderer (Parsedown)
│   └── cache.php      → SQLite-backed PLATO tile cache
├── pages/
│   ├── home.php       → Landing page
│   ├── playground.php → Interactive playground
│   ├── learn.php      → Tutorial system
│   ├── spec.php       → ISA specification viewer
│   ├── plato.php      → PLATO browser
│   ├── benchmark.php  → Safe-TOPS/W comparison
│   └── fleet.php      → Fleet dashboard
├── static/
│   ├── flux-playground.js  → Client-side playground logic
│   ├── flux-syntax.css     → Syntax highlighting for GUARD
│   └── style.css           → Site theme (cocapn-cli abyssal aesthetic)
└── templates/
    ├── header.php     → Nav, meta, theme
    ├── footer.php     → Community links, footer
    └── playground.php → Reusable playground component
```

## PLATO Integration (The Wow Factor)

```php
<?php
// Live PLATO room viewer — queries the actual PLATO server
$room_id = $_GET['room'] ?? 'flux-isa-architecture';
$tiles = plato_get_room($room_id);
?>
<section class="plato-room">
    <h2><?= htmlspecialchars($room_id) ?> — <?= count($tiles) ?> tiles</h2>
    <?php foreach ($tiles as $tile): ?>
    <article class="tile">
        <h3><?= htmlspecialchars($tile['question']) ?></h3>
        <p><?= markdown_render($tile['answer']) ?></p>
        <footer>Domain: <?= $tile['domain'] ?> | Hash: <?= $tile['hash'] ?></footer>
    </article>
    <?php endforeach; ?>
</section>
```

This is a LIVE view of PLATO's knowledge. No static rebuild. Query the API, render HTML. When someone submits a new tile, it appears immediately.

## FLUX VM Bridge (The Hard Part)

Two approaches:

### Option A: PHP → Rust binary via proc_open
```php
<?php
function flux_execute($bytecode_hex, $gas = 1000) {
    $binary = hex2bin($bytecode_hex);
    $tmpfile = tempnam(sys_get_temp_dir(), 'flux_');
    file_put_contents($tmpfile, $binary);
    
    $output = shell_exec("flux-runner $tmpfile $gas 2>&1");
    unlink($tmpfile);
    
    return json_decode($output, true);
}
```

### Option B: PHP → HTTP API → Rust service
```php
<?php
function flux_execute($bytecode_hex, $gas = 1000) {
    $payload = json_encode(['bytecode' => $bytecode_hex, 'gas' => $gas]);
    $result = file_get_contents(
        'http://localhost:4053/execute',
        false,
        stream_context_create(['http' => ['method' => 'POST', 'content' => $payload]])
    );
    return json_decode($result, true);
}
```

Option B is better — the Rust VM runs as a persistent service, no startup overhead.

## Deployment

```bash
# On the server
git clone https://github.com/cocapn/flux-site /var/www/flux
cd /var/www/flux
composer install   # just Parsedown + maybe a routing lib
# That's it. PHP serves directly.

# For the Rust VM service
cargo build --release --bin flux-runner-service
./target/release/flux-runner-service &  # listens on :4053
```

No Node.js. No webpack. No React. PHP serves HTML, Rust runs VM, PLATO serves knowledge.

## Content Plan (Viral Loop)

### Week 1: Getting Started
- "Write your first constraint in 5 minutes"
- "GUARD DSL cheat sheet" (single-page reference)
- "FLUX vs. Rust assertions: when to use each"

### Week 2: Real Examples
- "eVTOL flight envelope in 20 lines of GUARD"
- "ISO 26262 ASIL-D compliance with FLUX"
- "Thermal throttling as a constraint program"

### Week 3: Advanced
- "Multi-agent coordination with DelegateNode"
- "Temporal constraints: CHECKPOINT and REVERT explained"
- "Building your own FLUX-compatible hardware monitor"

### Week 4: Community
- "Submit your constraint program to the gallery"
- "Safe-TOPS/W benchmark your hardware"
- "Contributing to FLUX: a guide for newcomers"

Each tutorial has an EMBEDDED PLAYGROUND. Every code example runs live.

## What Makes This Go Viral

1. **The playground** — zero-install, zero-signup, type GUARD and see it run
2. **The benchmark** — everyone wants to see their chip's score (even if it's 0)
3. **The PLATO browser** — living documentation that grows daily
4. **The examples** — real aerospace/automotive/medical use cases, not toy demos
5. **The speed** — PHP → PLATO → HTML in <100ms. No JavaScript framework. No hydration.

## Priority

1. Build the playground (this is the hook)
2. Build the PLATO browser (this is the wow)
3. Write 3 tutorials (this is the on-ramp)
4. Add Safe-TOPS/W live comparison (this is the controversy)
5. Submit to Hacker News (this is the spark)
