#!/usr/bin/env python3
"""
Cocapn Fleet API Gateway
Routes all fleet services through a single entry point.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError
import json
import time
import threading

# Service registry
SERVICES = {
    'plato':    {'host': '147.224.38.131', 'port': 8847, 'health': '/rooms'},
    'mud':      {'host': '147.224.38.131', 'port': 4042, 'health': '/'},
    'arena':    {'host': '147.224.38.131', 'port': 4044, 'health': '/'},
    'terminal': {'host': '147.224.38.131', 'port': 4060, 'health': '/'},
    'dashboard':{'host': '147.224.38.131', 'port': 4046, 'health': '/'},
}

# Rate limiting (in-memory)
rate_limit = {}
RATE_WINDOW = 60  # seconds
RATE_MAX = 100    # requests per window

def check_rate_limit(agent_id):
    """Return True if request is allowed."""
    now = time.time()
    if agent_id not in rate_limit:
        rate_limit[agent_id] = []
    # Clean old entries
    rate_limit[agent_id] = [t for t in rate_limit[agent_id] if now - t < RATE_WINDOW]
    if len(rate_limit[agent_id]) >= RATE_MAX:
        return False
    rate_limit[agent_id].append(now)
    return True

def proxy_request(service_name, path, method='GET', data=None, headers=None):
    """Forward request to backend service."""
    svc = SERVICES.get(service_name)
    if not svc:
        return 404, {'error': f'Unknown service: {service_name}'}
    
    url = f"http://{svc['host']}:{svc['port']}{path}"
    req = Request(url, data=data, headers=headers or {}, method=method)
    try:
        resp = urlopen(req, timeout=10)
        body = resp.read()
        try:
            return resp.status, json.loads(body)
        except:
            return resp.status, body.decode('utf-8', errors='replace')
    except URLError as e:
        return 502, {'error': f'Service {service_name} unavailable: {e}'}
    except Exception as e:
        return 500, {'error': str(e)}

def check_all_health():
    """Check health of all services."""
    results = {}
    for name, svc in SERVICES.items():
        try:
            url = f"http://{svc['host']}:{svc['port']}{svc['health']}"
            resp = urlopen(url, timeout=5)
            results[name] = {'status': 'UP', 'code': resp.status}
        except:
            results[name] = {'status': 'DOWN', 'code': None}
    return results

class GatewayHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._handle('GET')
    
    def do_POST(self):
        self._handle('POST')
    
    def _handle(self, method):
        # Parse path: /{service}/...
        parts = self.path.strip('/').split('/')
        
        # Health check
        if self.path == '/health':
            health = check_all_health()
            self._json(200, {'gateway': 'UP', 'services': health})
            return
        
        # API docs
        if self.path == '/':
            self._json(200, {
                'gateway': 'Cocapn Fleet API Gateway',
                'version': '0.1.0',
                'services': list(SERVICES.keys()),
                'endpoints': {
                    '/health': 'Service health check',
                    '/{service}/*': 'Proxy to backend service',
                }
            })
            return
        
        if len(parts) < 1:
            self._json(400, {'error': 'Invalid path. Use /{service}/...'})
            return
        
        service = parts[0]
        path = '/' + '/'.join(parts[1:]) if len(parts) > 1 else '/'
        
        # Rate limit
        agent_id = self.headers.get('X-Agent-ID', 'anonymous')
        if not check_rate_limit(agent_id):
            self._json(429, {'error': 'Rate limit exceeded'})
            return
        
        # Read body for POST
        data = None
        if method == 'POST':
            content_len = int(self.headers.get('Content-Length', 0))
            if content_len:
                data = self.rfile.read(content_len)
        
        # Proxy
        status, body = proxy_request(service, path, method, data, dict(self.headers))
        self._json(status, body)
    
    def _json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Agent-ID')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Agent-ID')
        self.end_headers()
    
    def log_message(self, format, *args):
        # Could log to PLATO here
        pass

if __name__ == '__main__':
    port = 8000
    server = HTTPServer(('0.0.0.0', port), GatewayHandler)
    print(f'Fleet API Gateway running on port {port}')
    print(f'Services: {list(SERVICES.keys())}')
    server.serve_forever()
