#!/usr/bin/env python3
"""
SonarTelemetryStream — WebSocket endpoint for fleet dashboard integration
Designed by Forgemaster ⚒️ for real-time sonar physics broadcasting

Deploy on Oracle1 as systemd service on port 4052 (NOT 4051).
Fleet dashboard subscribes to ws://oracle1:4052/stream
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Optional

try:
    import websockets
except ImportError:
    print("pip install websockets")
    raise

# ── Physics Engine (inline for standalone deployment) ─────────

def mackenzie_sound_speed(depth: float, temp: float = 20.0, salinity: float = 35.0) -> float:
    """Mackenzie equation (1981) for sound speed in seawater."""
    D = depth
    T = temp
    S = salinity
    c = (1448.96 + 4.591 * T - 0.05304 * T**2 + 2.374e-4 * T**3
         + 1.340 * (S - 35) + 1.630e-2 * D + 1.675e-7 * D**2
         - 1.025e-2 * T * (S - 35) - 7.139e-13 * T * D**3)
    return round(c, 1)

def francois_absorption(freq_khz: float, depth: float, temp: float = 20.0) -> float:
    """Francois-Garrison absorption model (simplified). Returns dB/km."""
    f = freq_khz
    # Boric acid contribution
    f1 = 0.78 * ((temp / 35) ** 0.5) * 10 ** (temp / 26)
    A1 = 0.106 * (f1 * f) / (f1**2 + f**2)
    # Magnesium sulfate contribution
    f2 = 42.0 * 10 ** (temp / 17)
    A2 = 0.52 * (1 + temp / 43) * (S := 35, 0.0)[1] if False else 0.52 * (1 + temp / 43) * (f2 * f) / (f2**2 + f**2)
    # Pure water absorption
    A3 = 0.00049 * f**2
    # Depth correction
    P = 1.0 - 3.0e-5 * depth
    alpha = (A1 + A2 + A3) * P
    return round(alpha * 1000, 3)  # dB/km

def compute_physics(depth: float, freq_khz: float = 12.0, temp: float = 20.0, chlorophyll: float = 3.0) -> dict:
    """Compute full physics snapshot at depth."""
    sound_speed = mackenzie_sound_speed(depth, temp)
    absorption = francois_absorption(freq_khz, depth, temp)
    # Scattering from chlorophyll (empirical)
    scattering = 0.003 * chlorophyll ** 0.5
    # Visibility (Secchi depth approximation)
    visibility = max(1.0, 15.0 / (1.0 + chlorophyll * 0.5))
    # Attenuation (total path loss rate)
    attenuation = absorption + scattering * 1000
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "depth": depth,
        "sound_speed": sound_speed,
        "temperature": temp,
        "absorption_dB_km": absorption,
        "scattering": round(scattering, 4),
        "visibility_m": round(visibility, 1),
        "attenuation_dB_km": round(attenuation, 3),
        "frequency_kHz": freq_khz,
    }

# ── WebSocket Server ───────────────────────────────────────────

connected_clients = set()
current_depth = 0.0
DIVE_SPEED = 2.0  # meters per tick
MAX_DEPTH = 200.0
TICK_INTERVAL = 2.0  # seconds between physics updates

async def telemetry_broadcaster():
    """Broadcast physics data to all connected clients."""
    global current_depth
    
    while True:
        if connected_clients:
            # Simulate dive profile: surface to max_depth and back
            physics = compute_physics(current_depth)
            message = json.dumps({
                "type": "physics",
                "data": physics
            })
            
            # Broadcast to all clients
            disconnected = set()
            for client in connected_clients:
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(client)
            
            connected_clients -= disconnected
            
            # Advance depth
            current_depth += DIVE_SPEED
            if current_depth > MAX_DEPTH:
                current_depth = 0.0
        
        await asyncio.sleep(TICK_INTERVAL)

async def handle_client(websocket, path=None):
    """Handle individual client connections."""
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            # Allow clients to send commands
            try:
                cmd = json.loads(message)
                if cmd.get("action") == "set_depth":
                    global current_depth
                    current_depth = float(cmd.get("depth", 0))
                    await websocket.send(json.dumps({"type": "ack", "depth": current_depth}))
                elif cmd.get("action") == "ping":
                    # Acoustic ping simulation
                    target_range = cmd.get("range", 500)
                    travel_time = 2 * target_range / mackenzie_sound_speed(current_depth)
                    await websocket.send(json.dumps({
                        "type": "ping_result",
                        "travel_time_s": round(travel_time, 4),
                        "range_m": target_range,
                        "depth_m": current_depth
                    }))
            except json.JSONDecodeError:
                pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)

async def main():
    """Start the telemetry server."""
    print(f"SonarTelemetryStream starting on port 4052")
    print(f"Dive profile: 0-{MAX_DEPTH}m, {DIVE_SPEED}m/tick, {TICK_INTERVAL}s interval")
    
    async with websockets.serve(handle_client, "0.0.0.0", 4052):
        await telemetry_broadcaster()

if __name__ == "__main__":
    asyncio.run(main())
