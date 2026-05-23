# flux-site — PHP Integration Kit for FLUX & PLATO

Drop-in PHP files for adding FLUX constraint enforcement and PLATO knowledge browsing to any website.

**Zero dependencies.** No Composer, no framework, no build step. Just `require_once`.

## Quick Start

```bash
# Copy the kit into your PHP project
cp -r php-kit/ /var/www/html/flux/

# Open in browser
open http://localhost/flux/examples/constraint-playground-v2.php
```

## Files

### Core Libraries

| File | Purpose | Size |
|------|---------|------|
| `plato.php` | PLATO API client (rooms, tiles, search, submit) | ~3KB |
| `flux-vm.php` | FLUX VM simulator (pure PHP) | ~5KB |
| `flux-compiler.php` | GUARD → FLUX compiler (pure PHP) | ~4KB |
| `safe-tops.php` | Safe-TOPS/W benchmark scorer | ~2KB |
| `flux-tiles.php` | PLATO tiles → formatted HTML renderer | ~2KB |

### Drop-In Pages (just `include` or link directly)

| File | What It Shows | Preview |
|------|--------------|---------|
| `constraint-playground-v2.php` | Interactive GUARD→FLUX→VM demo | Type constraints, see bytecode, execute live |
| `benchmark-table-v2.php` | Safe-TOPS/W comparison (8 chips) | Certified vs uncertified, bar charts |
| `plato-browser-v2.php` | Live PLATO knowledge browser | Search rooms, view tiles, prefix filter |

### Landing Page

| File | Purpose |
|------|---------|
| `../index-v2.php` | Community hub homepage (hero, stats, features, links) |

### Tutorials (Markdown)

| Tutorial | Topic | Length |
|----------|-------|--------|
| `tutorial-5-min-quickstart.md` | Write first constraint, compile, execute | 3.8KB |
| `tutorial-temporal-constraints.md` | DEADLINE, CHECKPOINT/REVERT, DRIFT | 5.1KB |
| `tutorial-security-primitives.md` | SANDBOX, CAP_GRANT/REVOKE, SEAL, AUDIT | 6.5KB |
| `tutorial-multi-agent-delegation.md` | Tell, Ask, CoIterate, Fork, A2A protocol | 6.0KB |
| `tutorial-formal-verification.md` | Coq proofs, SymbiYosys, semantic gap | 6.4KB |
| `tutorial-hardware-implementation.md` | RAU FSM, AXI4-Lite, FPGA, ASIC | 6.4KB |
| `tutorial-universal-ast.md` | 7 node types, combinators, generation | 5.7KB |

## PLATO API

All files connect to the PLATO knowledge base:

```
http://147.224.38.131:8847
```

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/rooms` | GET | List all rooms |
| `/rooms?prefix=flux` | GET | Filter by prefix |
| `/room/{id}` | GET | Get room with tiles |
| `/search?q=query` | GET | Search across tiles |
| `/submit` | POST | Submit new tile |

Every widget that connects to PLATO has an **API mode** — add `?api=1` to the URL for JSON output.

## Usage Examples

### Embed PLATO tiles on a page

```php
<?php
require_once 'php-kit/plato.php';
require_once 'php-kit/flux-tiles.php';

$plato = new PlatoClient();
$room = $plato->getRoom('flux-isa');
echo render_tiles($room);
?>
```

### Run a constraint check

```php
<?php
require_once 'php-kit/flux-compiler.php';
require_once 'php-kit/flux-vm.php';

$c = new FluxCompiler();
$bytecode = $c->compile('constraint alt { range(0, 150) }');

$vm = new FluxVM();
$result = $vm->execute($bytecode, 100);  // Input: 100
echo $result['passed'] ? '✅ PASS' : '❌ FAIL';
?>
```

### Show benchmark table

```php
<?php
require_once 'php-kit/safe-tops.php';
$table = get_benchmark_table();
foreach ($table as $chip) {
    echo "{$chip['name']}: {$chip['safe_tops_w']} Safe-TOPS/W\n";
}
?>
```

## Architecture

```
GUARD source → flux-compiler.php → FLUX bytecode → flux-vm.php → PASS/FAULT
                                        ↓
                              flux_c_to_x.py (Python bridge)
                                        ↓
                              flux-isa (Oracle1's Python VM)
```

The PHP kit is self-contained — it compiles and executes constraints without needing the Rust or Python packages. For full 256-opcode support, use the Python bridge to connect to Oracle1's `flux-isa`.

## Integration with Oracle1's Repos

| FM Package | Oracle1 Package | Bridge |
|------------|----------------|--------|
| guard2mask (Rust) | flux-isa (Python) | flux_c_to_x.py |
| guard2map (Rust) | flux-compiler (Python) | Multi-compiler test |
| flux-bridge (Rust) | flux-plato-bridge (Python) | Shared PLATO endpoint |

Both compilers produce compatible FLUX-X 4-byte bytecode. Proven by `test_multi_compiler.py` (5/5 tests).

## License

Apache 2.0 — same as all Cocapn fleet code.

## Fleet

- **Forgemaster ⚒️** — constraint theory, Rust crates, this PHP kit
- **Oracle1 🔮** — fleet coordination, flux-isa, flux-compiler, sites
- **CCC 🦀** — frontend design, fleet orchestration, TUTOR onboarding

Fleet discussion: https://github.com/SuperInstance/SuperInstance/discussions/5
