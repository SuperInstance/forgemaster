<?php
/**
 * FLUX Community Hub — Router
 * All URLs flow through here. PHP serves HTML, no build step.
 */

// Simple router — map URL paths to page files
$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$uri = rtrim($uri, '/') ?: '/';

// Route table
$routes = [
    '/' => 'home.php',
    '/playground' => 'playground.php',
    '/play' => 'playground.php',
];

// Static files — let the web server handle these normally
if (preg_match('/\.(css|js|png|jpg|svg|ico|flux)$/', $uri)) {
    $file = __DIR__ . '/static' . $uri;
    if (file_exists($file)) {
        $mime = mime_content_type($file);
        header("Content-Type: $mime");
        readfile($file);
        exit;
    }
    http_response_code(404);
    echo 'Not found';
    exit;
}

// Find matching route
$page_file = $routes[$uri] ?? null;

if ($page_file && file_exists(__DIR__ . '/pages/' . $page_file)) {
    require __DIR__ . '/pages/' . $page_file;
    exit;
}

// Try exact page match (e.g., /learn → pages/learn.php)
$direct = __DIR__ . '/pages' . $uri . '.php';
if (file_exists($direct)) {
    require $direct;
    exit;
}

// 404
http_response_code(404);
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>404 — FLUX</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header>
        <nav>
            <a href="/" class="logo">⚡ FLUX</a>
            <a href="/playground">Playground</a>
            <a href="/learn">Learn</a>
            <a href="/spec">Spec</a>
        </nav>
    </header>
    <main style="text-align:center; padding:4rem;">
        <h1>404</h1>
        <p>Constraint not found.</p>
        <a href="/" class="cta primary">Back to Home</a>
    </main>
</body>
</html>
