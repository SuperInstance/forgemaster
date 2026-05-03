<?php
/**
 * PLATO Tile Renderer — formats tiles as HTML for any PHP page
 */

function render_tiles(array $tiles, bool $show_domain = true): string {
    if (empty($tiles)) return '<p class="empty">No tiles found.</p>';
    
    $html = '<div class="plato-tiles">';
    foreach ($tiles as $tile) {
        $html .= render_single_tile($tile, $show_domain);
    }
    $html .= '</div>';
    return $html;
}

function render_single_tile(array $tile, bool $show_domain = true): string {
    $question = htmlspecialchars($tile['question'] ?? 'Unknown question');
    $answer = markdown_safe($tile['answer'] ?? 'No answer');
    $domain = htmlspecialchars($tile['domain'] ?? '');
    $hash = htmlspecialchars($tile['tile_hash'] ?? substr($tile['id'] ?? '', 0, 8));
    
    $html = '<article class="tile">';
    $html .= '<h4 class="tile-question">' . $question . '</h4>';
    $html .= '<div class="tile-answer">' . $answer . '</div>';
    if ($show_domain && $domain) {
        $html .= '<footer class="tile-meta">';
        $html .= '<span class="tile-domain">' . $domain . '</span>';
        $html .= '<span class="tile-hash">' . $hash . '</span>';
        $html .= '</footer>';
    }
    $html .= '</article>';
    return $html;
}

function render_room_list(array $rooms, string $base_url = '/plato/room'): string {
    if (empty($rooms)) return '<p>No rooms found.</p>';
    
    $html = '<div class="room-list">';
    foreach ($rooms as $room) {
        $id = htmlspecialchars($room['id'] ?? $room['name'] ?? '');
        $count = $room['tile_count'] ?? 0;
        $html .= '<a href="' . $base_url . '/' . urlencode($id) . '" class="room-card">';
        $html .= '<span class="room-name">' . $id . '</span>';
        $html .= '<span class="room-count">' . $count . ' tiles</span>';
        $html .= '</a>';
    }
    $html .= '</div>';
    return $html;
}

function render_room_summary(array $room_data): string {
    $id = htmlspecialchars($room_data['id'] ?? '');
    $tiles = $room_data['tiles'] ?? [];
    
    $html = '<div class="room-summary">';
    $html .= '<h2>' . $id . '</h2>';
    $html .= '<p class="room-stats">' . count($tiles) . ' tiles</p>';
    $html .= render_tiles($tiles);
    $html .= '</div>';
    return $html;
}

/**
 * Safe markdown subset renderer — no external library needed
 */
function markdown_safe(string $text): string {
    // Bold
    $text = preg_replace('/\*\*(.+?)\*\*/', '<strong>$1</strong>', $text);
    // Code
    $text = preg_replace('/`(.+?)`/', '<code>$1</code>', $text);
    // Links
    $text = preg_replace('/\[(.+?)\]\((.+?)\)/', '<a href="$2">$1</a>', $text);
    // Line breaks
    $text = nl2br(htmlspecialchars($text, ENT_QUOTES, 'UTF-8'));
    // Unescape our own HTML tags
    $text = str_replace(['&lt;strong&gt;', '&lt;/strong&gt;', '&lt;code&gt;', '&lt;/code&gt;', '&lt;a href=', '&lt;/a&gt;'], ['<strong>', '</strong>', '<code>', '</code>', '<a href=', '</a>'], $text);
    
    return $text;
}
