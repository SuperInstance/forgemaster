<?php
/**
 * Drop-in PLATO Knowledge Browser
 * Usage: include 'php-kit/examples/plato-browser.php';
 * 
 * URL parameters:
 *   ?room=flux-isa-architecture  → show specific room
 *   ?prefix=flux                 → filter rooms by prefix
 *   ?q=constraint                → search tiles
 */
require_once __DIR__ . '/../plato.php';
require_once __DIR__ . '/../flux-tiles.php';

$plato = new PlatoClient();
$room_id = $_GET['room'] ?? '';
$prefix = $_GET['prefix'] ?? '';
$query = $_GET['q'] ?? '';

?>
<div class="plato-browser">
    <div class="plato-search">
        <form method="get">
            <input type="text" name="q" value="<?= htmlspecialchars($query) ?>" placeholder="Search PLATO knowledge...">
            <button type="submit">Search</button>
        </form>
    </div>

    <?php if ($query): ?>
        <h3>Search results for "<?= htmlspecialchars($query) ?>"</h3>
        <?php
        $results = $plato->search($query);
        if (!empty($results['tiles'] ?? [])) {
            echo render_tiles($results['tiles']);
        } else {
            echo '<p>No results found.</p>';
        }
        ?>

    <?php elseif ($room_id): ?>
        <?php
        $room = $plato->getRoom($room_id);
        echo render_room_summary($room);
        ?>
        <a href="?prefix=<?= urlencode($prefix) ?>">← Back to room list</a>

    <?php else: ?>
        <h3>PLATO Knowledge Rooms <?= $prefix ? '(' . htmlspecialchars($prefix) . '*)' : '' ?></h3>
        <?php
        $rooms = $plato->getRooms($prefix);
        echo render_room_list($rooms, '?room=');
        ?>
    <?php endif; ?>
</div>
<style>
.plato-browser { font-family: sans-serif; }
.plato-search { margin-bottom:1.5rem; }
.plato-search input { padding:0.5rem; width:300px; font-size:1rem; }
.plato-search button { padding:0.5rem 1rem; }
.plato-tiles { display:flex; flex-direction:column; gap:1rem; }
.plato-tiles .tile { padding:1rem; border:1px solid #1e293b; border-radius:6px; background:#111827; }
.plato-tiles .tile-question { color:#22d3ee; margin-bottom:0.5rem; }
.plato-tiles .tile-answer { color:#94a3b8; font-size:0.9rem; }
.plato-tiles .tile-meta { display:flex; justify-content:space-between; margin-top:0.5rem; font-size:0.75rem; color:#64748b; }
.room-list { display:grid; grid-template-columns:repeat(auto-fill,minmax(250px,1fr)); gap:0.5rem; }
.room-card { display:flex; justify-content:space-between; padding:0.75rem; border:1px solid #1e293b; border-radius:4px; color:#e2e8f0; text-decoration:none; }
.room-card:hover { border-color:#22d3ee; }
.room-name { font-family:monospace; font-size:0.85rem; }
.room-count { color:#64748b; font-size:0.8rem; }
</style>
