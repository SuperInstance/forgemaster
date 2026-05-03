<?php
/**
 * Drop-in Safe-TOPS/W Benchmark Table
 * Usage: include 'php-kit/examples/benchmark-table.php';
 */
require_once __DIR__ . '/../safe-tops.php';

$table = get_benchmark_table();
?>
<div class="safe-tops-w-table">
    <h3>Safe-TOPS/W Comparison</h3>
    <table>
        <thead>
            <tr>
                <th>Chip</th>
                <th>Raw TOPS/W</th>
                <th>Pass Rate</th>
                <th>Cert Factor</th>
                <th>Safe-TOPS/W</th>
            </tr>
        </thead>
        <tbody>
            <?php foreach ($table as $row): ?>
            <tr class="<?= $row['safe'] > 0 ? 'certified' : '' ?>">
                <td><?= htmlspecialchars($row['chip']) ?></td>
                <td><?= number_format($row['raw'], 1) ?></td>
                <td><?= number_format($row['pass'] * 100, 0) ?>%</td>
                <td><?= number_format($row['cert'], 2) ?></td>
                <td class="safe-score">
                    <strong class="<?= $row['safe'] > 0 ? 'green' : 'dim' ?>">
                        <?= number_format($row['safe'], 2) ?>
                    </strong>
                </td>
            </tr>
            <?php endforeach; ?>
        </tbody>
    </table>
    <p class="footnote">
        Safe-TOPS/W = (raw × pass_rate × cert_factor) / overhead.
        Uncertified hardware scores 0 — not deployable for safety functions.
    </p>
</div>
<style>
.safe-tops-w-table table { width:100%; border-collapse:collapse; font-size:0.9rem; }
.safe-tops-w-table th { text-align:left; padding:0.5rem; border-bottom:2px solid #1e293b; color:#94a3b8; }
.safe-tops-w-table td { padding:0.5rem; border-bottom:1px solid #1e293b; }
.safe-tops-w-table .green { color:#34d399; }
.safe-tops-w-table .dim { color:#475569; }
.safe-tops-w-table .certified td { background:rgba(52,211,153,0.03); }
.safe-tops-w-table .footnote { font-size:0.8rem; color:#64748b; margin-top:0.5rem; }
</style>
