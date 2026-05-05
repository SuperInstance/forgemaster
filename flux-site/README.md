# flux-site — cocapn.ai Web Presence

> Public-facing website, PHP integration kit, and interactive demos for FLUX.

## Pages

| Page | File | Description |
|------|------|-------------|
| Home | `pages/landing.html` | cocapn.ai homepage |
| Demo | `pages/demo.html` | Interactive flight envelope demo (SVG gauges) |
| Objections | `pages/objections.html` | Top 10 objections answered |
| Safe-TOPS/W | `pages/safe-tops-w-v3.html` | Benchmark comparison (28KB) |
| Compare | `pages/compare.html` | FLUX vs CompCert vs SPARK vs SCADE |
| Proofs | `pages/proofs.html` | Formal proof gallery |
| Timeline | `pages/timeline-v2.html` | PLATO→FLUX lineage (1960-2024) |
| Sales | `pages/sales-one-pager.html` | Engineering manager one-pager |

## PHP Integration Kit

The `php-kit/` directory contains drop-in widgets for Oracle1's website work:

- `constraint-playground.php` — Interactive constraint editor
- `benchmark-table.php` — Performance comparison table
- `plato-browser.php` — PLATO knowledge browser

## Static Assets

- `data/benchmarks.json` — Structured benchmark data (16 systems)
- `static/style.css` — Dark theme CSS

## Deployment

```bash
# Static pages — serve from any web root
cp -r pages/ /var/www/html/

# PHP widgets — drop into any PHP site
cp -r php-kit/ /var/www/html/flux/
```

## License

Apache 2.0
