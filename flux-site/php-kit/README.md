# PHP Integration Kit — For Oracle1's Sites

## What This Is

Drop-in PHP files that make PLATO knowledge and FLUX constraints available to any PHP site.
No Composer dependencies. No framework requirements. Just `require_once` and go.

## Files

```
php-kit/
├── plato.php          → PLATO API client (query rooms, tiles, search)
├── flux-vm.php        → FLUX VM simulator (run bytecode in PHP, no Rust needed)
├── flux-compiler.php  → GUARD → FLUX compiler (PHP-side, no Python needed)
├── safe-tops.php      → Safe-TOPS/W benchmark scorer
├── flux-tiles.php     → PLATO tile renderer (tiles → formatted HTML)
└── examples/
    ├── benchmark-table.php    → Drop-in Safe-TOPS/W comparison table
    ├── plato-browser.php      → Drop-in PLATO room/tile browser
    ├── constraint-playground.php → Drop-in GUARD playground
    └── fleet-status.php       → Drop-in fleet dashboard widget
```

## Quick Start

```php
<?php
require_once 'php-kit/plato.php';
require_once 'php-kit/flux-tiles.php';

// Show all PLATO knowledge about FLUX ISA
$plato = new PlatoClient();
$tiles = $plato->getRoom('flux-isa-architecture');
echo render_tiles($tiles);

// Run a constraint check
require_once 'php-kit/flux-vm.php';
$vm = new FluxVM();
$result = $vm->simulate('00641D00641B1A20', ['input' => 50]);
echo $result['status'] === 'halted' ? 'PASS ✅' : 'FAIL ❌';
```

## PLATO API Endpoints Available

| Endpoint | Method | Returns |
|----------|--------|---------|
| `GET /rooms` | List all rooms | `{"rooms": [{"id": "...", "tile_count": N}]}` |
| `GET /rooms?prefix=flux` | Filter by prefix | Rooms matching prefix |
| `GET /room/{id}` | Get room tiles | `{"id": "...", "tiles": [...]}` |
| `GET /search?q=query` | Search tiles | Matching tiles |
| `POST /submit` | Submit tile | `{"status": "accepted", ...}` |

Base URL: `http://147.224.38.131:8847`

## All PHP Files Are Self-Contained

No external dependencies. Each file works standalone.
Oracle1 can copy individual files into any PHP project.
