"""Sonar ray tracer.

Traces acoustic rays through a sound-speed profile,
applying Snell refraction at each layer boundary.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable

import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RayPoint:
    """A single point along a traced ray."""
    x: float
    z: float
    angle: float
    travel_time: float
    intensity: float
    sound_speed: float


@dataclass(frozen=True, slots=True)
class PingResult:
    """Result of a single sonar ping."""
    azimuth: float
    depression: float
    ray: tuple[RayPoint, ...]
    two_way_time: float
    bottom_return: float
    range_m: float


@runtime_checkable
class RayTracerBackend(Protocol):
    """Protocol for pluggable ray tracers."""

    def trace_ray(self, start_x: float, start_z: float, angle: float, max_range: float, step: float, sound_speed_fn: Callable[[float], float], absorption_fn: Callable[[float], float], bottom_depth: float) -> tuple[RayPoint, ...]:
        ...

    def ping(self, x: float, z: float, azimuth: float, depression: float, bottom_depth: float, sound_speed_fn: Callable[[float], float], absorption_fn: Callable[[float], float]) -> PingResult:
        ...


class SonarRayTracer:
    """Deterministic 2D ray tracer for sonar simulation."""

    def __init__(self, max_range: float = 500.0, step: float = 1.0, freq: float = 50.0) -> None:
        self.max_range = max_range
        self.step = step
        self.freq = freq
        logger.debug("SonarRayTracer initialized: max_range=%.1f, step=%.2f, freq=%.1f", max_range, step, freq)

    def _snell(self, theta1: float, c1: float, c2: float) -> float:
        ratio = (c2 / c1) * math.sin(theta1)
        if abs(ratio) > 1.0:
            return 0.0
        return math.asin(ratio)

    def trace_ray(self, start_x: float, start_z: float, angle: float, max_range: float | None = None, step: float | None = None, sound_speed_fn: Callable[[float], float] | None = None, absorption_fn: Callable[[float], float] | None = None, bottom_depth: float = 50.0) -> tuple[RayPoint, ...]:
        max_r = max_range if max_range is not None else self.max_range
        st = step if step is not None else self.step
        if sound_speed_fn is None:
            sound_speed_fn = lambda z: 1500.0
        if absorption_fn is None:
            absorption_fn = lambda z: 0.0
        points: list[RayPoint] = []
        x = float(start_x)
        z = float(start_z)
        theta = float(angle)
        travel_time = 0.0
        intensity = 1.0
        c_prev = sound_speed_fn(z)
        points.append(RayPoint(x=x, z=z, angle=theta, travel_time=travel_time, intensity=intensity, sound_speed=c_prev))
        while x < start_x + max_r:
            x_new = x + st * math.cos(theta)
            z_new = z + st * math.sin(theta)
            if z_new < 0.0:
                if abs(math.sin(theta)) > 1e-12:
                    frac = (0.0 - z) / (math.sin(theta) * st)
                    x_new = x + frac * st * math.cos(theta)
                    z_new = 0.0
                theta = -theta
                x_new = x + st * math.cos(theta)
                z_new = z + st * math.sin(theta)
                if z_new < 0.0:
                    z_new = 0.0
            if z_new >= bottom_depth:
                if abs(math.sin(theta)) > 1e-12:
                    frac = (bottom_depth - z) / (math.sin(theta) * st)
                    x_new = x + frac * st * math.cos(theta)
                    z_new = bottom_depth
                else:
                    x_new = x + st
                    z_new = bottom_depth
                dx = x_new - x
                dz = z_new - z
                path_len = math.hypot(dx, dz)
                c_new = sound_speed_fn(z_new)
                alpha = absorption_fn(z_new)
                dt = path_len / c_prev if c_prev > 0 else 0.0
                travel_time += dt
                spreading = 1.0 / (1.0 + path_len)
                absorption_loss = 10 ** (-alpha * path_len / 1000.0 / 20.0)
                intensity *= spreading * absorption_loss
                points.append(RayPoint(x=x_new, z=z_new, angle=theta, travel_time=travel_time, intensity=intensity, sound_speed=c_new))
                break
            dx = x_new - x
            dz = z_new - z
            path_len = math.hypot(dx, dz)
            c_new = sound_speed_fn(z_new)
            alpha = absorption_fn(z_new)
            dt = path_len / c_prev if c_prev > 0 else 0.0
            travel_time += dt
            spreading = 1.0 / (1.0 + path_len)
            absorption_loss = 10 ** (-alpha * path_len / 1000.0 / 20.0)
            intensity *= spreading * absorption_loss
            if c_new != c_prev:
                theta_new = self._snell(theta, c_prev, c_new)
                if theta_new != 0.0 or abs(theta) < 1e-6:
                    theta = theta_new
            x, z = x_new, z_new
            c_prev = c_new
            points.append(RayPoint(x=x, z=z, angle=theta, travel_time=travel_time, intensity=intensity, sound_speed=c_prev))
        return tuple(points)

    def ping(self, x: float, z: float, azimuth: float, depression: float, bottom_depth: float, sound_speed_fn: Callable[[float], float] | None = None, absorption_fn: Callable[[float], float] | None = None) -> PingResult:
        ray = self.trace_ray(start_x=x, start_z=z, angle=depression, sound_speed_fn=sound_speed_fn, absorption_fn=absorption_fn, bottom_depth=bottom_depth)
        if not ray:
            return PingResult(azimuth=azimuth, depression=depression, ray=(), two_way_time=0.0, bottom_return=0.0, range_m=0.0)
        last = ray[-1]
        slant_range = math.hypot(last.x - x, last.z - z)
        two_way_time = last.travel_time * 2.0
        incident_angle = abs(last.angle)
        lambert = math.cos(incident_angle) if incident_angle < math.pi / 2 else 0.0
        bottom_return = last.intensity * lambert
        return PingResult(azimuth=azimuth, depression=depression, ray=ray, two_way_time=two_way_time, bottom_return=bottom_return, range_m=slant_range)

    def multi_beam_ping(self, x: float, z: float, bottom_depth: float, n_beams: int = 101, aperture: float = 120.0, sound_speed_fn: Callable[[float], float] | None = None, absorption_fn: Callable[[float], float] | None = None) -> tuple[PingResult, ...]:
        half_aperture = math.radians(aperture / 2.0)
        angles = [-half_aperture + (2.0 * half_aperture * i / max(n_beams - 1, 1)) for i in range(n_beams)]
        results: list[PingResult] = []
        for angle in angles:
            result = self.ping(x=x, z=z, azimuth=0.0, depression=angle, bottom_depth=bottom_depth, sound_speed_fn=sound_speed_fn, absorption_fn=absorption_fn)
            results.append(result)
        return tuple(results)


try:
    from sonar_vision_physics import SonarRayTracer as ExternalSonarRayTracer  # type: ignore[import]
    _HAS_EXTERNAL_TRACER = True
    logger.info("Using external sonar_vision_physics.SonarRayTracer")
except Exception:
    _HAS_EXTERNAL_TRACER = False
    logger.debug("External sonar_vision_physics.SonarRayTracer not available; using built-in")


def get_ray_tracer_backend(max_range: float = 500.0, step: float = 1.0, freq: float = 50.0) -> RayTracerBackend:
    if _HAS_EXTERNAL_TRACER:
        try:
            return ExternalSonarRayTracer(max_range=max_range, step=step, freq=freq)  # type: ignore[return-value]
        except Exception:
            logger.warning("External SonarRayTracer failed; falling back")
    return SonarRayTracer(max_range=max_range, step=step, freq=freq)
