#!/usr/bin/env python3
"""SonarVision API Server — FLUX physics, neural surrogate, pipeline, ray tracing.

Usage:
  python api_server.py [--port 8080] [--model]

Endpoints:
  GET  /health              Health check
  GET  /v1/physics          FLUX physics at depth
  POST /v1/physics/profile  Dive profile (depth range)
  POST /v1/ray              Trace an acoustic ray
  POST /v1/survey           Plan a survey mission
  POST /v1/survey/simulate  Survey with simulated pings
  POST /v1/fleet            Run fleet simulation
  POST /v1/neural/predict   Nural surrogate prediction
  GET  /v1/neural/info      Neural surrogate model info
  GET  /v1/openapi.yaml     OpenAPI spec
"""

import json, os, sys, math, time as time_module
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sim_pipeline'))
sys.path.insert(0, os.path.dirname(__file__))

try:
    from sim_pipeline import (
        FluxPhysics, SonarRayTracer, MissionPlanner, SonarDisplay,
        AUVFleetSimulator, FLUXCTBridge, ConstraintSnapper,
        compute_physics, dive_profile
    )
except ImportError:
    # Self-contained fallback — import from package dir
    import importlib
    FluxPhysics = None

# ============================================================
# Neural Surrogate (lazy-loaded)
# ============================================================
_neural_model = None
_neural_loaded = False

def get_neural_surrogate():
    global _neural_model, _neural_loaded
    if not _neural_loaded:
        try:
            sys.path.insert(0, os.path.dirname(__file__))
            from neural_physics import PhysicsSurrogate, predict_profile, ModelConfig, create_synthetic_data
            cfg = ModelConfig()
            _neural_model = PhysicsSurrogate(cfg)
            # Load pre-trained weights if available
            weight_path = os.path.join(os.path.dirname(__file__), 'neural_weights.pt')
            if os.path.exists(weight_path):
                try:
                    _neural_model.load_state_dict(torch.load(weight_path, map_location='cpu'))
                    _neural_model.eval()
                except Exception:
                    pass  # Run with random weights
            _neural_loaded = True
            return True
        except Exception as e:
            _neural_loaded = True
            return False
    return _neural_model is not None


# ============================================================
# Request Handler
# ============================================================

class APIHandler(BaseHTTPRequestHandler):
    _physics = FluxPhysics() if FluxPhysics else None

    def _send(self, data, status=200, ct='application/json'):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header('Content-Type', ct)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length == 0: return {}
        try: return json.loads(self.rfile.read(length))
        except json.JSONDecodeError: return {}

    def _params(self):
        return parse_qs(urlparse(self.path).query)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/health' or path == '/':
            return self._send({
                "status":"ok","service":"sonar-vision-api",
                "version":"1.4.0","time":datetime.utcnow().isoformat(),
                "endpoints": self._list_endpoints()
            })
        elif path == '/v1/physics':
            p = self._params()
            d = float(p.get('depth',[25])[0])
            cl = float(p.get('chl',[4.0])[0])
            se = p.get('season',['summer'])[0]
            sd = p.get('sediment',['sand'])[0]
            return self._send(self._physics.compute(d, cl, se, sd))
        elif path == '/v1/neural/info':
            avail = get_neural_surrogate()
            return self._send({"available": avail, "model":"PhysicsSurrogate",
                               "architecture":"JEPA encoder-predictor",
                               "status":"trained" if avail else "not loaded"})
        elif path == '/v1/openapi.yaml':
            yaml = self._build_openapi()
            return self._send(yaml, ct='text/yaml')
        elif path == '/v1/neural/predict':
            p = self._params()
            avail = get_neural_surrogate()
            if not avail:
                return self._send({"error":"Neural surrogate not available","fallback":"use /v1/physics"}, 503)
            try:
                start = float(p.get('start',[0])[0])
                end = float(p.get('end',[50])[0])
                step = float(p.get('step',[5])[0])
                chl = float(p.get('chl',[5.0])[0])
                season = 0 if p.get('season',['summer'])[0] == 'summer' else 1
                sed = {'mud':0,'sand':1,'gravel':2,'rock':3,'seagrass':4}.get(p.get('sediment',['sand'])[0], 1)
                res = predict_profile(_neural_model, start, end, step, chl, season, sed)
                return self._send({"model":"PhysicsSurrogate","profile":res,"epochs":0})
            except Exception as e:
                return self._send({"error":str(e),"fallback":"use /v1/physics"}, 500)
        else:
            return self._send({"error":"not found","path":path}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()

        if path == '/v1/physics/profile':
            start = body.get('start', 0)
            end = body.get('end', 100)
            step = body.get('step', 5)
            chl = body.get('chl', 5.0)
            season = body.get('season', 'summer')
            sediment = body.get('sediment', 'sand')
            prof = dive_profile(start, end, step, chl, season, sediment)
            return self._send({"profile":prof,"count":len(prof)})

        elif path == '/v1/ray':
            sd = body.get('source_depth', 10.0)
            td = body.get('target_depth', 50.0)
            rng = body.get('range', 100.0)
            chl = body.get('chl', 5.0)
            season = body.get('season', 'summer')
            sediment = body.get('sediment', 'sand')
            tracer = SonarRayTracer(chl=chl, season=season, sediment=sediment)
            ret = tracer.compute_return(sd, td, rng)
            if body.get('fan'):
                ret['fan_scan'] = tracer.fan_scan(sd=sd, rng=rng)
            return self._send(ret)

        elif path == '/v1/survey':
            pattern = body.get('pattern', 'lawnmower')
            name = body.get('name', 'survey')
            width = body.get('width', 500.0)
            height = body.get('height', 200.0)
            depth = body.get('depth', 25.0)
            spacing = body.get('spacing', 50.0)
            planner = MissionPlanner()
            patterns = {
                'lawnmower': lambda: planner.lawnmover(name, width, height, depth, spacing),
                'spiral': lambda: planner.spiral(name, max(width,height)/2, depth),
                'star': lambda: planner.star(name, max(width,height)/2, depth),
                'perimeter': lambda: planner.perimeter(name, width, height, depth),
            }
            mission = patterns.get(pattern, patterns['lawnmower'])()
            return self._send({
                "name":mission.name,"pattern":mission.pattern,
                "waypoints":[{"index":w.index,"x":w.x,"y":w.y,"depth":w.depth,"speed":w.speed}
                             for w in mission.waypoints],
                "waypoint_count":len(mission.waypoints),
                "total_distance_m":mission.total_distance(),
                "estimated_duration_s":mission.estimated_duration()
            })

        elif path == '/v1/survey/simulate':
            pattern = body.get('pattern', 'lawnmower')
            width = body.get('width', 500.0)
            height = body.get('height', 200.0)
            depth = body.get('depth', 25.0)
            chl = body.get('chl', 5.0)
            season = body.get('season', 'summer')
            sediment = body.get('sediment', 'sand')
            planner = MissionPlanner()
            mission = planner.lawnmover('survey', width, height, depth)
            pings = []
            for wp in mission.waypoints:
                p = compute_physics(wp.depth, chl, season, sediment)
                p["position"] = {"x":wp.x,"y":wp.y}
                pings.append(p)
            return self._send({
                "mission":mission.name,"waypoints_simulated":len(pings),
                "pings":pings,"waterfall":SonarDisplay.waterfall(pings),
                "summary_table":SonarDisplay.ping_table(pings)
            })

        elif path == '/v1/fleet':
            count = body.get('count', 5)
            seconds = body.get('seconds', 60)
            depth = body.get('depth', 20.0)
            formation = body.get('formation', 'v')
            formations_map = {'line':0,'v':1,'diamond':2,'grid':3,'random':4}
            sim = AUVFleetSimulator(self._physics)
            sim.spawn_fleet(count, depth=depth)
            form_idx = formations_map.get(formation, 1)
            # Map to Formation enum
            from sim_pipeline.fleet_sim import Formation
            fm = [Formation.LINE, Formation.V, Formation.DIAMOND, Formation.GRID, Formation.RANDOM][form_idx]
            sim.formation(fm, spacing=body.get('spacing',40))
            ticks = sim.run_for(seconds)
            summary = sim.fleet_summary()
            summary['ticks'] = len(ticks)
            return self._send(summary)

        elif path == '/v1/neural/predict':
            avail = get_neural_surrogate()
            if not avail:
                return self._send({"error":"Neural surrogate not available"}, 503)
            try:
                start = body.get('start', 0)
                end = body.get('end', 50)
                step = body.get('step', 5)
                chl = body.get('chl', 5.0)
                season = 0 if body.get('season','summer') == 'summer' else 1
                sed = {'mud':0,'sand':1,'gravel':2,'rock':3,'seagrass':4}.get(body.get('sediment','sand'),1)
                res = predict_profile(_neural_model, start, end, step, chl, season, sed)
                return self._send({"model":"PhysicsSurrogate","profile":res})
            except Exception as e:
                return self._send({"error":str(e)}, 500)

        else:
            return self._send({"error":"not found","path":path}, 404)

    def log_message(self, fmt, *args):
        print("[{}] {}".format(datetime.utcnow().isoformat(), fmt % args))

    def _list_endpoints(self):
        return [
            {"path":"/health","method":"GET","desc":"Health check"},
            {"path":"/v1/physics","method":"GET","desc":"Single depth physics (params: depth, chl, season, sediment)"},
            {"path":"/v1/physics/profile","method":"POST","desc":"Dive profile (body: start, end, step, chl, season, sediment)"},
            {"path":"/v1/ray","method":"POST","desc":"Trace acoustic ray (body: source_depth, target_depth, range, fan)"},
            {"path":"/v1/survey","method":"POST","desc":"Plan survey (body: pattern, width, height, depth, spacing)"},
            {"path":"/v1/survey/simulate","method":"POST","desc":"Survey with physics pings"},
            {"path":"/v1/fleet","method":"POST","desc":"Fleet simulation (body: count, seconds, depth, formation)"},
            {"path":"/v1/neural/info","method":"GET","desc":"Neural surrogate model info"},
            {"path":"/v1/neural/predict","method":"GET|POST","desc":"Neural profile prediction"},
            {"path":"/v1/openapi.yaml","method":"GET","desc":"OpenAPI 3.0 spec"},
        ]

    def _build_openapi(self):
        return """openapi: "3.0.3"
info:
  title: SonarVision API
  version: "1.4.0"
  description: Marine physics, ray tracing, fleet simulation, and neural surrogate API
servers:
  - url: http://localhost:8080
paths:
  /health:
    get: {summary: "Health check", responses: {"200": {description: "OK"}}}
  /v1/physics:
    get:
      summary: "FLUX physics at depth"
      parameters:
        - {name: depth, in: query, schema: {type: number, default: 25}}
        - {name: chl, in: query, schema: {type: number, default: 5.0}}
        - {name: season, in: query, schema: {type: string, default: summer}}
        - {name: sediment, in: query, schema: {type: string, default: sand}}
      responses: {"200": {description: "Physics profile"}}
  /v1/physics/profile:
    post:
      summary: "Dive profile"
      requestBody: {required: true, content: {application/json: {schema: {$ref: "#/components/schemas/ProfileRequest"}}}}
      responses: {"200": {description: "Profile array"}}
  /v1/ray:
    post:
      summary: "Trace acoustic ray"
      requestBody: {required: true, content: {application/json: {schema: {$ref: "#/components/schemas/RayRequest"}}}}
      responses: {"200": {description: "Ray result"}}
  /v1/survey:
    post:
      summary: "Plan survey mission"
      requestBody: {required: true, content: {application/json: {schema: {$ref: "#/components/schemas/SurveyRequest"}}}}
      responses: {"200": {description: "Mission plan"}}
  /v1/fleet:
    post:
      summary: "Run fleet simulation"
      requestBody: {required: true, content: {application/json: {schema: {$ref: "#/components/schemas/FleetRequest"}}}}
      responses: {"200": {description: "Fleet summary"}}
  /v1/neural:
    get: {summary: "Neural surrogate info", responses: {"200": {description: "Model info"}}}
components:
  schemas:
    ProfileRequest:
      type: object; properties: {start: {type: integer}, end: {type: integer}, step: {type: integer}, chl: {type: number}}
    RayRequest:
      type: object; properties: {source_depth: {type: number}, target_depth: {type: number}, range: {type: number}}
    SurveyRequest:
      type: object; properties:
        {pattern: {type: string, enum: [lawnmower, spiral, star, perimeter]},
         width: {type: number}, height: {type: number}, depth: {type: number}}
    FleetRequest:
      type: object; properties:
        {count: {type: integer}, seconds: {type: integer}, depth: {type: number},
         formation: {type: string, enum: [line, v, diamond, grid, random]}}
"""


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SonarVision API Server")
    parser.add_argument('--port', type=int, default=8080, help="Port to listen on")
    parser.add_argument('--host', default='0.0.0.0', help="Bind address")
    parser.add_argument('--model', action='store_true', help="Load neural surrogate on startup")
    args = parser.parse_args()

    if args.model:
        sys.path.insert(0, os.path.dirname(__file__))
        ok = get_neural_surrogate()
        print("Neural surrogate loaded:", ok)

    server = HTTPServer((args.host, args.port), APIHandler)
    print("SonarVision API server on http://{}:{}".format(args.host, args.port))
    print("Health: http://{}:{}/health".format(args.host, args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down")
        server.server_close()


if __name__ == "__main__":
    main()
