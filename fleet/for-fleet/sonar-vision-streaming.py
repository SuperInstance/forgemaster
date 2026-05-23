"""
sonar-vision-streaming.py — Asyncio-based WebSocket streaming server.

Streams live sonar physics data at configurable rates.
Supports dive simulation (0→100m), pause/resume/reset commands.

Usage:
  python sonar-vision-streaming.py [--port 8081] [--rate 5]
  # Connect via: ws://localhost:8081
  # Send: "reset", "pause", "resume", "goto:50"
"""

import asyncio
import json
import math
import signal
import time
import struct
import sys


# ============================
# Physics Engine
# ============================

WATER_TYPES = {0: 'Coastal', 1: 'Oceanic Type II', 2: 'Oceanic Type IB', 3: 'Clear Oceanic'}
SEDIMENT_NAMES = ['mud', 'sand', 'gravel', 'rock', 'seagrass']
SEDIMENT_REFLECT = [0.3, 0.5, 0.7, 0.85, 0.2]


class FluxPhysics:
    """Deterministic underwater physics engine (FLUX 9-opcode model)."""

    def compute(self, depth: float, chl: float = 5.0, season: int = 0,
                sediment: int = 1, wl: float = 480.0, sal: float = 35.0) -> dict:
        # Water type
        if chl > 10.0:
            wt = 0
        elif chl > 1.0:
            wt = 1
        elif chl > 0.1:
            wt = 2
        else:
            wt = 3

        # Absorption
        wa = wl / 1000.0
        if wt <= 1:
            absorp = 0.04 + 0.96 * math.exp(-((wa - 0.42)**2) / (2 * 0.02**2))
        elif wt == 2:
            absorp = 0.3 + 0.9 * math.exp(-((wa - 0.48)**2) / (2 * 0.03**2))
        else:
            absorp = 0.02 + 0.51 * math.exp(-((wa - 0.42)**2) / (2 * 0.015**2))

        # Scattering
        ns = 0.002 * (480e-9 / (wl * 1e-9))**4.3
        scat = ns * max(0.01, 1.0 - depth * 0.003)

        # Thermocline
        tc, tw = (15.0, 5.0) if season == 0 else (40.0, 15.0)
        st, dt = (22.0, 4.0) if season == 0 else (8.0, 4.0)
        temp = dt + (st - dt) * math.exp(-((depth - tc)**2) / (2 * tw**2))
        dtdz = -(st - dt) * (depth - tc) / (tw**2) * math.exp(-((depth - tc)**2) / (2 * tw**2))

        # Seabed
        seabed = SEDIMENT_REFLECT[sediment] * math.exp(-depth * 0.003)

        # Attenuation
        atten = absorp + scat

        # Visibility
        vis = min(depth, 1.7 / max(atten, 0.001))

        # Sound speed
        ss = (1449.2 + 4.6*temp - 0.055*temp**2 + 0.00029*temp**3 +
              (1.34 - 0.01*temp)*(sal - 35) + 0.016*depth)

        # Refraction
        v_ratio = ss / 1480.0
        theta = math.radians(30.0)
        st2 = math.sin(theta) * (1.0 / v_ratio)
        refrac = 90.0 if st2 > 1.0 else math.degrees(math.asin(st2))

        return {
            'depth': round(depth, 1),
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
            'sediment': SEDIMENT_NAMES[sediment],
        }


# ============================
# Dive Simulation
# ============================

class DiveSimulator:
    """Simulates a dive profile from surface to depth and back."""

    def __init__(self, max_depth: float = 100.0, rate_hz: float = 5.0,
                 descent_speed: float = 3.0):  # m/s ~ 3 knots
        self.physics = FluxPhysics()
        self.max_depth = max_depth
        self.rate_hz = rate_hz
        self.descent_speed = descent_speed
        self.current_depth = 0.0
        self.descending = True
        self.paused = False
        self.samples = 0
        self.start_time = time.time()

    def step(self) -> dict:
        """Advance one simulation step, return physics frame."""
        if not self.paused:
            if self.descending:
                self.current_depth += self.descent_speed / self.rate_hz
                if self.current_depth >= self.max_depth:
                    self.current_depth = self.max_depth
                    self.descending = False
            else:
                self.current_depth -= self.descent_speed / self.rate_hz
                if self.current_depth <= 0:
                    self.current_depth = 0.0
                    self.descending = True

        self.current_depth = max(0.0, min(self.max_depth, self.current_depth))
        self.samples += 1

        chl = max(0.05, 8.0 - self.current_depth * 0.12)
        frame = self.physics.compute(self.current_depth, chl=chl)
        frame['frame_id'] = self.samples
        frame['elapsed'] = round(time.time() - self.start_time, 3)
        frame['diving'] = self.descending
        return frame

    def reset(self) -> None:
        self.current_depth = 0.0
        self.descending = True
        self.paused = False
        self.samples = 0

    def goto(self, depth: float) -> None:
        self.current_depth = max(0.0, min(self.max_depth, depth))

    def set_paused(self, paused: bool) -> None:
        self.paused = paused


# ============================
# WebSocket Server (stdlib)
# ============================

class WebSocketConnection:
    """Minimal WebSocket server using stdlib asyncio."""

    WS_GUID = b'258EAFA5-E914-47DA-95CA-5AB9DC11B85B'

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.open = True

    @classmethod
    async def handshake(cls, reader, writer) -> 'WebSocketConnection':
        data = await reader.readuntil(b'\r\n\r\n')
        request = data.decode('utf-8', errors='replace')

        key = None
        for line in request.split('\r\n'):
            if line.lower().startswith('sec-websocket-key:'):
                key = line.split(':', 1)[1].strip()
                break

        if not key:
            writer.write(b'HTTP/1.1 400 Bad Request\r\n\r\n')
            await writer.drain()
            writer.close()
            raise ValueError('Missing Sec-WebSocket-Key')

        import hashlib
        import base64
        accept = base64.b64encode(
            hashlib.sha1(key.encode() + cls.WS_GUID).digest()
        ).decode()

        response = (
            'HTTP/1.1 101 Switching Protocols\r\n'
            'Upgrade: websocket\r\n'
            'Connection: Upgrade\r\n'
            f'Sec-WebSocket-Accept: {accept}\r\n'
            'Access-Control-Allow-Origin: *\r\n'
            '\r\n'
        )
        writer.write(response.encode())
        await writer.drain()

        conn = cls(reader, writer)
        return conn

    async def recv(self) -> str | None:
        """Receive one WebSocket text message."""
        try:
            # Read frame header
            header = await self.reader.readexactly(2)
            if not header:
                return None
            b0, b1 = header[0], header[1]
            opcode = b0 & 0x0F
            masked = (b1 >> 7) & 0x01
            length = b1 & 0x7F

            if length == 126:
                raw = await self.reader.readexactly(2)
                length = struct.unpack('!H', raw)[0]
            elif length == 127:
                raw = await self.reader.readexactly(8)
                length = struct.unpack('!Q', raw)[0]

            if masked:
                mask_key = await self.reader.readexactly(4)
                payload = await self.reader.readexactly(length)
                payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
            else:
                payload = await self.reader.readexactly(length)

            if opcode == 0x08:  # Close
                self.open = False
                return None
            elif opcode == 0x09:  # Ping
                await self._send_frame(0x0A, payload)  # Pong
                return await self.recv()
            elif opcode == 0x01:  # Text
                return payload.decode('utf-8')

        except (asyncio.IncompleteReadError, ConnectionResetError):
            self.open = False
            return None

    async def send(self, message: str) -> None:
        """Send a WebSocket text message."""
        if not self.open:
            return
        try:
            payload = message.encode('utf-8')
            await self._send_frame(0x01, payload)
        except (ConnectionResetError, BrokenPipeError):
            self.open = False

    async def _send_frame(self, opcode: int, payload: bytes) -> None:
        header = bytearray()
        header.append(0x80 | opcode)

        length = len(payload)
        if length < 126:
            header.append(length)
        elif length < 65536:
            header.append(126)
            header.extend(struct.pack('!H', length))
        else:
            header.append(127)
            header.extend(struct.pack('!Q', length))

        self.writer.write(bytes(header))
        self.writer.write(payload)
        await self.writer.drain()

    async def close(self) -> None:
        if self.open:
            try:
                await self._send_frame(0x08, b'')
            except:
                pass
            self.open = False
            try:
                self.writer.close()
            except:
                pass


class StreamingServer:
    """WebSocket server that streams FLUX physics data."""

    def __init__(self, host: str = '0.0.0.0', port: int = 8081,
                 rate_hz: float = 5.0, max_depth: float = 100.0):
        self.host = host
        self.port = port
        self.rate_hz = rate_hz
        self.simulator = DiveSimulator(max_depth=max_depth, rate_hz=rate_hz)
        self.connections: list[WebSocketConnection] = []
        self.running = True

    async def handle_client(self, reader, writer) -> None:
        try:
            conn = await WebSocketConnection.handshake(reader, writer)
            self.connections.append(conn)
            peer = writer.get_extra_info('peername', ('?', 0))
            print(f'[+] Client connected: {peer[0]}:{peer[1]}')

            # Send initial frame immediately
            frame = self.simulator.step()
            await conn.send(json.dumps(frame))

            while self.running and conn.open:
                msg = await conn.recv()
                if msg is None:
                    break

                # Handle client commands
                msg = msg.strip().lower()
                if msg == 'reset':
                    self.simulator.reset()
                    await conn.send(json.dumps({'type': 'status', 'message': 'reset'}))
                elif msg == 'pause':
                    self.simulator.set_paused(True)
                    await conn.send(json.dumps({'type': 'status', 'message': 'paused'}))
                elif msg == 'resume' or msg == 'start':
                    self.simulator.set_paused(False)
                    await conn.send(json.dumps({'type': 'status', 'message': 'resumed'}))
                elif msg.startswith('goto:'):
                    try:
                        depth = float(msg.split(':')[1])
                        self.simulator.goto(depth)
                        frame = self.simulator.step()
                        await conn.send(json.dumps(frame))
                    except (ValueError, IndexError):
                        await conn.send(json.dumps(
                            {'type': 'error', 'message': 'Invalid depth'}))
                elif msg == 'help':
                    await conn.send(json.dumps({
                        'type': 'help',
                        'commands': ['reset', 'pause', 'resume', 'goto:<depth>', 'help']
                    }))

        except (ValueError, asyncio.IncompleteReadError) as e:
            print(f'[-] Connection error: {e}')
        finally:
            if conn in self.connections:
                self.connections.remove(conn)
            try:
                writer.close()
            except:
                pass
            print(f'[-] Client disconnected ({writer.get_extra_info("peername", ("?", 0))[0]})')

    async def stream_data(self) -> None:
        """Background task: push frames to all connected clients at rate_hz."""
        interval = 1.0 / self.rate_hz
        while self.running:
            t0 = time.time()
            frame = self.simulator.step()
            payload = json.dumps(frame)

            dead_conns = []
            for conn in self.connections[:]:
                if conn.open:
                    await conn.send(payload)
                else:
                    dead_conns.append(conn)
            for conn in dead_conns:
                if conn in self.connections:
                    self.connections.remove(conn)

            elapsed = time.time() - t0
            await asyncio.sleep(max(0, interval - elapsed))

    async def start(self) -> None:
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f'[*] SonarVision WebSocket streaming on ws://{self.host}:{self.port}')
        print(f'[*] Stream rate: {self.rate_hz} Hz, max depth: {self.simulator.max_depth}m')
        print(f'[*] Commands: reset, pause, resume, goto:<depth>')
        print(f'[*] Press Ctrl+C to stop')

        # Create streaming task
        stream_task = asyncio.create_task(self.stream_data())

        # Handle shutdown
        stop = asyncio.Future()

        def shutdown():
            if not stop.done():
                stop.set_result(True)

        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, shutdown)
            except NotImplementedError:
                # Windows
                pass

        async with server:
            await stop  # Wait for shutdown signal

        self.running = False
        stream_task.cancel()

        # Close all connections
        for conn in self.connections[:]:
            await conn.close()
        self.connections.clear()

        print('[*] Server stopped')


def main():
    import argparse
    parser = argparse.ArgumentParser(description='SonarVision WebSocket Streamer')
    parser.add_argument('--host', default='0.0.0.0', help='Bind address')
    parser.add_argument('--port', type=int, default=8081, help='WebSocket port')
    parser.add_argument('--rate', type=float, default=5.0, help='Stream rate (Hz)')
    parser.add_argument('--max-depth', type=float, default=100.0, help='Max dive depth (m)')
    args = parser.parse_args()

    server = StreamingServer(args.host, args.port, args.rate, args.max_depth)
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print('\n[*] Interrupted')


if __name__ == '__main__':
    main()
