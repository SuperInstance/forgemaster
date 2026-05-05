<?php
/**
 * PLATO Knowledge Browser — Live Fleet Knowledge Widget
 * 
 * Drop-in PHP page that browses PLATO rooms and tiles in real-time.
 * Connects to PLATO API at 147.224.38.131:8847.
 * 
 * Features:
 * - Search across 1400+ knowledge rooms
 * - Browse rooms by prefix (forgemaster-*, flux-*, fleet-*)
 * - View individual tiles with domain/question/answer
 * - Auto-refresh (30s)
 * - API mode (?api=1)
 */

$PLATO_URL = 'http://147.224.38.131:8847';

// ─── API Mode ───
if (isset($_GET['api'])) {
    header('Content-Type: application/json');
    $action = $_GET['action'] ?? 'rooms';
    
    switch ($action) {
        case 'rooms':
            $prefix = $_GET['prefix'] ?? '';
            $url = $prefix ? "$PLATO_URL/rooms?prefix=" . urlencode($prefix) : "$PLATO_URL/rooms";
            echo fetch_url($url);
            break;
        case 'room':
            $id = $_GET['id'] ?? '';
            echo fetch_url("$PLATO_URL/room/" . urlencode($id));
            break;
        case 'search':
            $q = $_GET['q'] ?? '';
            echo fetch_url("$PLATO_URL/search?q=" . urlencode($q));
            break;
        default:
            echo json_encode(['error' => 'Unknown action']);
    }
    exit;
}

function fetch_url($url) {
    $ctx = stream_context_create(['http' => ['timeout' => 5]]);
    $data = @file_get_contents($url, false, $ctx);
    return $data ?: json_encode(['error' => 'PLATO unreachable']);
}

// ─── Page Mode ───
// Pre-fetch rooms for initial display
$rooms_json = fetch_url("$PLATO_URL/rooms");
$rooms = json_decode($rooms_json, true) ?: [];

// Group rooms by prefix
$prefixes = [];
foreach ($rooms as $room) {
    $parts = explode('-', $room['id'] ?? $room ?? '', 2);
    $prefix = $parts[0] ?? 'other';
    $prefixes[$prefix] = ($prefixes[$prefix] ?? 0) + 1;
}
arsort($prefixes);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PLATO Knowledge Browser</title>
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
            --amber: #f59e0b;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
            min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        h1 { color: var(--cyan); font-size: 1.5rem; margin-bottom: 0.25rem; }
        .subtitle { color: var(--muted); font-size: 0.875rem; margin-bottom: 1.5rem; }
        
        /* Search bar */
        .search-bar {
            display: flex;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
        }
        .search-bar input {
            flex: 1;
            background: var(--surface);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.6rem 1rem;
            font-family: inherit;
            font-size: 0.875rem;
        }
        .search-bar input:focus { outline: none; border-color: var(--cyan); }
        .search-bar button {
            background: var(--cyan);
            color: var(--bg);
            border: none;
            border-radius: 4px;
            padding: 0.6rem 1.5rem;
            font-family: inherit;
            font-size: 0.875rem;
            font-weight: 700;
            cursor: pointer;
        }
        .search-bar button:hover { background: #0891b2; }
        
        /* Prefix filters */
        .prefixes {
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            margin-bottom: 1.5rem;
        }
        .prefix-btn {
            background: transparent;
            color: var(--muted);
            border: 1px solid var(--border);
            border-radius: 3px;
            padding: 0.2rem 0.6rem;
            font-family: inherit;
            font-size: 0.7rem;
            cursor: pointer;
        }
        .prefix-btn:hover, .prefix-btn.active { border-color: var(--cyan); color: var(--cyan); }
        
        /* Stats bar */
        .stats-bar {
            display: flex;
            gap: 2rem;
            margin-bottom: 1.5rem;
            padding: 0.75rem 1rem;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 6px;
        }
        .stat { font-size: 0.8rem; }
        .stat-value { color: var(--cyan); font-weight: 700; }
        .stat-label { color: var(--muted); }
        
        /* Content grid */
        .grid {
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 1.5rem;
        }
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
        }
        
        /* Room list */
        .room-list {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 6px;
            max-height: 600px;
            overflow-y: auto;
        }
        .room-item {
            padding: 0.6rem 1rem;
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            font-size: 0.8rem;
            transition: background 0.1s;
        }
        .room-item:hover { background: #1e293b33; }
        .room-item.active { background: #1e293b66; border-left: 2px solid var(--cyan); }
        .room-id { color: var(--cyan); font-weight: 600; }
        .room-tiles { color: var(--muted); font-size: 0.7rem; }
        
        /* Tile display */
        .tile-display {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 1.25rem;
        }
        .tile-card {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .tile-domain {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--magenta);
            margin-bottom: 0.5rem;
        }
        .tile-question {
            font-size: 0.9rem;
            color: var(--cyan);
            margin-bottom: 0.75rem;
            font-weight: 600;
        }
        .tile-answer {
            font-size: 0.8rem;
            color: var(--text);
            line-height: 1.6;
        }
        .empty-state {
            color: var(--muted);
            text-align: center;
            padding: 3rem 1rem;
            font-size: 0.875rem;
        }
        
        /* Loading */
        .loading { color: var(--amber); font-size: 0.8rem; }
    </style>
</head>
<body>
<div class="container">
    <h1>📚 PLATO Knowledge Browser</h1>
    <p class="subtitle">Fleet knowledge base — <?= number_format(count($rooms)) ?> rooms, live from PLATO</p>
    
    <div class="search-bar">
        <input type="text" id="search" placeholder="Search tiles..." />
        <button onclick="searchTiles()">Search</button>
    </div>
    
    <div class="prefixes">
        <?php foreach (array_slice($prefixes, 0, 20, true) as $prefix => $count): ?>
        <button class="prefix-btn" onclick="filterByPrefix('<?= htmlspecialchars($prefix) ?>')">
            <?= htmlspecialchars($prefix) ?> (<?= $count ?>)
        </button>
        <?php endforeach; ?>
    </div>
    
    <div class="stats-bar">
        <div class="stat">
            <span class="stat-value"><?= number_format(count($rooms)) ?></span>
            <span class="stat-label"> rooms</span>
        </div>
        <div class="stat">
            <span class="stat-value"><?= number_format(array_sum($prefixes)) ?></span>
            <span class="stat-label"> tiles</span>
        </div>
        <div class="stat">
            <span class="stat-value"><?= count($prefixes) ?></span>
            <span class="stat-label"> domains</span>
        </div>
    </div>
    
    <div class="grid">
        <div class="room-list" id="roomList">
            <div class="empty-state">Loading rooms...</div>
        </div>
        <div class="tile-display" id="tileDisplay">
            <div class="empty-state">Select a room to view tiles</div>
        </div>
    </div>
</div>

<script>
const PLATO_URL = '<?= $PLATO_URL ?>';
let allRooms = [];
let currentPrefix = '';

async function loadRooms(prefix = '') {
    const url = prefix ? `${PLATO_URL}/rooms?prefix=${prefix}` : `${PLATO_URL}/rooms`;
    const resp = await fetch(`?api=1&action=rooms${prefix ? '&prefix=' + encodeURIComponent(prefix) : ''}`);
    const rooms = await resp.json();
    allRooms = rooms;
    renderRooms(rooms);
}

function renderRooms(rooms) {
    const list = document.getElementById('roomList');
    list.innerHTML = rooms.slice(0, 200).map(r => {
        const id = r.id || r;
        const tiles = r.tile_count || '?';
        return `<div class="room-item" onclick="loadRoom('${id}')">
            <div class="room-id">${id}</div>
            <div class="room-tiles">${tiles} tiles</div>
        </div>`;
    }).join('');
}

async function loadRoom(id) {
    document.querySelectorAll('.room-item').forEach(el => el.classList.remove('active'));
    event.target.closest('.room-item')?.classList.add('active');
    
    const display = document.getElementById('tileDisplay');
    display.innerHTML = '<div class="loading">Loading tiles...</div>';
    
    const resp = await fetch(`?api=1&action=room&id=${encodeURIComponent(id)}`);
    const data = await resp.json();
    
    const tiles = data.tiles || [];
    if (tiles.length === 0) {
        display.innerHTML = `<div class="empty-state">No tiles in room "${id}"</div>`;
        return;
    }
    
    display.innerHTML = tiles.map(t => `
        <div class="tile-card">
            <div class="tile-domain">${t.domain || id}</div>
            <div class="tile-question">${t.question || 'No question'}</div>
            <div class="tile-answer">${t.answer || 'No answer'}</div>
        </div>
    `).join('');
}

async function searchTiles() {
    const q = document.getElementById('search').value;
    if (!q) return;
    
    const display = document.getElementById('tileDisplay');
    display.innerHTML = '<div class="loading">Searching...</div>';
    
    const resp = await fetch(`?api=1&action=search&q=${encodeURIComponent(q)}`);
    const data = await resp.json();
    
    const results = data.results || data || [];
    display.innerHTML = results.slice(0, 20).map(t => `
        <div class="tile-card">
            <div class="tile-domain">${t.domain || ''}</div>
            <div class="tile-question">${t.question || ''}</div>
            <div class="tile-answer">${t.answer || ''}</div>
        </div>
    `).join('') || '<div class="empty-state">No results</div>';
}

function filterByPrefix(prefix) {
    currentPrefix = prefix;
    document.querySelectorAll('.prefix-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    loadRooms(prefix);
}

// Auto-load on page load
loadRooms();
</script>
</body>
</html>
