<?php
/**
 * PLATO API Client — queries the live PLATO knowledge server
 */
class PlatoClient {
    private string $base_url = 'http://147.224.38.131:8847';
    private int $timeout = 5;

    public function getRooms(string $prefix = ''): array {
        $url = $this->base_url . '/rooms';
        if ($prefix) $url .= '?prefix=' . urlencode($prefix);
        $data = $this->fetch($url);
        return $data['rooms'] ?? [];
    }

    public function getRoom(string $id): array {
        return $this->fetch($this->base_url . '/room/' . urlencode($id));
    }

    public function search(string $query, string $domain = ''): array {
        $url = $this->base_url . '/search?q=' . urlencode($query);
        if ($domain) $url .= '&domain=' . urlencode($domain);
        return $this->fetch($url);
    }

    public function submitTile(string $domain, string $question, string $answer): array {
        $payload = json_encode(['domain' => $domain, 'question' => $question, 'answer' => $answer]);
        $ctx = stream_context_create([
            'http' => [
                'method' => 'POST',
                'header' => "Content-Type: application/json\r\n",
                'content' => $payload,
                'timeout' => $this->timeout,
            ]
        ]);
        $result = @file_get_contents($this->base_url . '/submit', false, $ctx);
        return $result ? json_decode($result, true) : ['error' => 'PLATO unavailable'];
    }

    private function fetch(string $url): array {
        $ctx = stream_context_create(['http' => ['timeout' => $this->timeout]]);
        $result = @file_get_contents($url, false, $ctx);
        return $result ? json_decode($result, true) : [];
    }
}
