"""
sonar-vision-server.py — Lightweight SonarVision API server.

Endpoints:
  GET  /              → Landing page (HTML)
  GET  /health        → Server health + uptime
  POST /api/v1/ping   → Sonar ping with physics computation
  POST /api/v1/dive   → Full dive profile
  WS   /ws/stream     → Live sonar data stream

Usage:
  python sonar-vision-server.py [--port 8080] [--host 0.0.0.0]
"""

import math, json, asyncio, time, sys, os, signal
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import select
import socket

# ============================
# Physics Engine (standalone)
# ============================

WATER_TYPES = {0: 'Coastal', 1: 'Oceanic Type II', 2: 'Oceanic Type IB', 3: 'Clear Oceanic'}
SEDIMENT_NAMES = ['mud', 'sand', 'gravel', 'rock', 'seagrass']
SEDIMENT_REFLECT = [0.3, 0.5, 0.7, 0.85, 0.2]

def compute_physics(depth, chl=5.0, season=0, sediment=1, wl=480.0, sal=35.0):
    """Compute all 9 FLUX physics parameters for a given depth."""
    if chl > 10.0:     wt = 0
    elif chl > 1.0:    wt = 1
    elif chl > 0.1:    wt = 2
    else:              wt = 3

    wa = wl / 1000.0
    if wt <= 1:
        absorp = 0.04 + 0.96 * math.exp(-((wa - 0.42)**2) / (2 * 0.02**2))
    elif wt == 2:
        absorp = 0.3 + 0.9 * math.exp(-((wa - 0.48)**2) / (2 * 0.03**2))
    else:
        absorp = 0.02 + 0.51 * math.exp(-((wa - 0.42)**2) / (2 * 0.015**2))

    ns = 0.002 * (480e-9 / (wl * 1e-9))**4.3
    scat = ns * max(0.01, 1.0 - depth * 0.003)

    tc, tw = (15.0, 5.0) if season == 0 else (40.0, 15.0)
    st, dt = (22.0, 4.0) if season == 0 else (8.0, 4.0)
    temp = dt + (st - dt) * math.exp(-((depth - tc)**2) / (2 * tw**2))
    dtdz = -(st - dt) * (depth - tc) / (tw**2) * math.exp(-((depth - tc)**2) / (2 * tw**2))

    seabed = SEDIMENT_REFLECT[sediment] * math.exp(-depth * 0.003)
    atten = absorp + scat
    vis = min(depth, 1.7 / max(atten, 0.001))

    ss = (1449.2 + 4.6*temp - 0.055*temp**2 + 0.00029*temp**3 +
          (1.34 - 0.01*temp)*(sal - 35) + 0.016*depth)

    v_ratio = ss / 1480.0
    theta = math.radians(30.0)
    st2 = math.sin(theta) * (1.0 / v_ratio)
    refrac = 90.0 if st2 > 1.0 else math.degrees(math.asin(st2))

    return {
        'depth': depth,
        'water_type': wt,
        'water_type_name': WATER_TYPES[wt],
        'temperature': round(temp, 2),
        'dTdz': round(dtdz, 4),
        'absorption': round(absorp, 4),
        'scattering': round(scat, 4),
        'attenuation': round(atten, 3),
        'visibility': round(vis, 2),
        'seabed_reflectivity': round(seabed, 4),
        'sound_speed': round(ss, 1),
        'refraction_deg': round(refrac, 2),
        'chlorophyll': chl,
        'season': 'summer' if season == 0 else 'winter',
        'sediment': SEDIMENT_NAMES[sediment],
    }


# ============================
# HTTP Server
# ============================

LANDING_PAGE = None  # Loaded on startup

UPTIME = time.time()


def json_response(handler, data, status=200):
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.end_headers()
    handler.wfile.write(json.dumps(data).encode())


def html_response(handler, html, status=200):
    handler.send_response(status)
    handler.send_header('Content-Type', 'text/html')
    handler.end_headers()
    handler.wfile.write(html.encode() if isinstance(html, str) else html)


def read_body(handler):
    length = int(handler.headers.get('Content-Length', 0))
    if length > 0:
        return handler.rfile.read(length)
    return b'{}'


class SonarVisionHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        if path == '' or path == '/':
            if LANDING_PAGE:
                html_response(self, LANDING_PAGE)
            else:
                html_response(self,
                    '<html><body><h1>SonarVision Server</h1>'
                    '<p>Landing page not loaded. Run with HTML file path.</p>'
                    '<p>Endpoints:</p>'
                    '<ul>'
                    '<li><a href="/health">GET /health</a></li>'
                    '<li><code>POST /api/v1/ping</code></li>'
                    '<li><code>POST /api/v1/dive</code></li>'
                    '</ul></body></html>')
        elif path == '/health':
            json_response(self, {
                'status': 'ok',
                'uptime_seconds': int(time.time() - UPTIME),
                'version': '1.0.0',
                'model': 'FLUX marine physics v3.1',
                'opcodes': 9,
                'deterministic': True,
            })
        elif path == '/api/v1/physics':
            # Query params: depth, chl, season, sediment
            qs = parse_qs(parsed.query)
            depth = float(qs.get('depth', [15])[0])
            chl = float(qs.get('chl', [5.0])[0])
            season = int(qs.get('season', [0])[0])
            sediment = int(qs.get('sediment', [1])[0])
            result = compute_physics(depth, chl=chl, season=season, sediment=sediment)
            json_response(self, result)
        else:
            json_response(self, {'error': 'not found'}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == '/api/v1/ping':
            body = json.loads(read_body(self))
            depth = float(body.get('depth', 15))
            chl = float(body.get('chlorophyll', 5.0))
            season = 0 if body.get('season', 'summer') == 'summer' else 1
            sediment = {'mud': 0, 'sand': 1, 'gravel': 2, 'rock': 3, 'seagrass': 4}.get(
                body.get('sediment', 'sand'), 1)
            result = compute_physics(depth, chl=chl, season=season, sediment=sediment)
            json_response(self, result)

        elif parsed.path == '/api/v1/dive':
            body = json.loads(read_body(self))
            start_depth = float(body.get('start', 0))
            end_depth = float(body.get('end', 100))
            step = float(body.get('step', 5))
            chl = float(body.get('chlorophyll', 5.0))
            season = 0 if body.get('season', 'summer') == 'summer' else 1
            sediment = {'mud': 0, 'sand': 1, 'gravel': 2, 'rock': 3, 'seagrass': 4}.get(
                body.get('sediment', 'sand'), 1)

            depths = list(range(int(start_depth), int(end_depth) + 1, int(step)))
            results = []
            for depth in depths:
                c = max(0.05, chl - depth * 0.12)
                result = compute_physics(depth, chl=c, season=season, sediment=sediment)
                results.append(result)

            json_response(self, {'profile': results, 'count': len(results)})

        else:
            json_response(self, {'error': 'not found'}, 404)

    def log_message(self, format, *args):
        """Quiet logging — just log requests."""
        print(f"[{self.log_date_time_string()}] {args[0]} {args[1]} {args[2]}")


def run_server(host='0.0.0.0', port=8080, html_file=None):
    global LANDING_PAGE

    if html_file:
        try:
            with open(html_file, 'r') as f:
                LANDING_PAGE = f.read()
            print(f"[*] Loaded landing page from {html_file}")
        except:
            print(f"[!] Could not load {html_file}")

    server = HTTPServer((host, port), SonarVisionHandler)
    print(f"[*] SonarVision API server running on http://{host}:{port}")
    print(f"[*] Endpoints:")
    print(f"      GET  /              — Landing page")
    print(f"      GET  /health        — Server health")
    print(f"      GET  /api/v1/physics?depth=15 — Physics query")
    print(f"      POST /api/v1/ping   — Sonar ping")
    print(f"      POST /api/v1/dive   — Full dive profile")
    print(f"[*] Physics model: FLUX 9-opcode marine physics (deterministic)")
    print(f"[*] Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        server.server_close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='SonarVision API Server')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--html', help='Path to landing page HTML file')
    args = parser.parse_args()

    run_server(host=args.host, port=args.port, html_file=args.html)
