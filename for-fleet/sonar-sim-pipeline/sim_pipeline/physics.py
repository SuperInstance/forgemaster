"""FLUX physics engine for sonar simulation.

Implements deterministic underwater acoustics with:
- Francois-Garrison absorption
- Jerlov water type optical attenuation
- Mackenzie sound speed
- Thermocline gradient
- Snell refraction

All calculations are deterministic (no randomness).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

import logging

logger = logging.getLogger(__name__)


class JerlovWaterType(Enum):
    """Jerlov water classification for optical/light attenuation."""
    I = "I"
    IA = "IA"
    IB = "IB"
    II = "II"
    III = "III"
    COASTAL_1 = "C1"
    COASTAL_3 = "C3"
    COASTAL_5 = "C5"
    COASTAL_7 = "C7"
    COASTAL_9 = "C9"


@dataclass(frozen=True, slots=True)
class SeawaterProperties:
    """Physical properties of seawater at a given point."""
    temperature: float
    salinity: float
    depth: float
    ph: float = 8.0


@dataclass(frozen=True, slots=True)
class AcousticPoint:
    """A point in the acoustic medium with derived properties."""
    x: float
    y: float
    z: float
    temperature: float
    salinity: float
    sound_speed: float
    absorption: float
    pressure: float


@runtime_checkable
class PhysicsBackend(Protocol):
    """Protocol for pluggable physics backends."""

    def sound_speed(self, temp: float, salinity: float, depth: float) -> float:
        ...

    def absorption(self, freq: float, temp: float, salinity: float, depth: float, ph: float) -> float:
        ...

    def snell_refraction(self, theta1: float, c1: float, c2: float) -> float:
        ...

    def thermocline_gradient(self, surface_temp: float, deep_temp: float, depth: float, thermocline_depth: float) -> float:
        ...


class FluxPhysics:
    """Deterministic FLUX physics engine."""

    JERLOV_KD: dict[JerlovWaterType, float] = {
        JerlovWaterType.I: 0.02,
        JerlovWaterType.IA: 0.03,
        JerlovWaterType.IB: 0.04,
        JerlovWaterType.II: 0.05,
        JerlovWaterType.III: 0.08,
        JerlovWaterType.COASTAL_1: 0.15,
        JerlovWaterType.COASTAL_3: 0.25,
        JerlovWaterType.COASTAL_5: 0.35,
        JerlovWaterType.COASTAL_7: 0.50,
        JerlovWaterType.COASTAL_9: 0.80,
    }

    def __init__(self, water_type: JerlovWaterType = JerlovWaterType.IA) -> None:
        self.water_type = water_type
        self.kd = self.JERLOV_KD.get(water_type, 0.03)
        logger.debug("FluxPhysics initialized: water_type=%s, kd=%.4f", water_type.value, self.kd)

    def sound_speed(self, temp: float, salinity: float, depth: float) -> float:
        t = temp
        s = salinity
        d = depth
        return (
            1448.96
            + 4.591 * t
            - 5.304e-2 * t**2
            + 2.374e-4 * t**3
            + 1.340 * (s - 35.0)
            + 1.630e-2 * d
            + 1.675e-7 * d**2
            - 1.025e-2 * t * (s - 35.0)
            - 7.139e-13 * t * d**3
        )

    def absorption(self, freq: float, temp: float, salinity: float, depth: float, ph: float = 8.0) -> float:
        f = freq
        t = temp
        s = salinity
        d = depth
        p_h = ph
        f1 = 0.78 * math.sqrt(s / 35.0) * math.exp(t / 26.0)
        alpha1 = 0.106 * (f1 * f**2) / (f1**2 + f**2) * math.exp((p_h - 8.0) / 0.56)
        f2 = 42.0 * math.exp(t / 17.0)
        alpha2 = 0.52 * (1.0 + t / 43.0) * (s / 35.0) * (f2 * f**2) / (f2**2 + f**2) * math.exp(-d / 6000.0)
        alpha3 = 0.00049 * f**2 * math.exp(-(t / 27.0 + d / 17000.0))
        return alpha1 + alpha2 + alpha3

    def snell_refraction(self, theta1: float, c1: float, c2: float) -> float:
        ratio = (c2 / c1) * math.sin(theta1)
        if abs(ratio) > 1.0:
            return 0.0
        return math.asin(ratio)

    def thermocline_gradient(self, surface_temp: float, deep_temp: float, depth: float, thermocline_depth: float = 100.0) -> float:
        if thermocline_depth <= 0:
            return deep_temp
        return deep_temp + (surface_temp - deep_temp) * math.exp(-depth / thermocline_depth)

    def pressure(self, depth: float, latitude: float = 45.0) -> float:
        lat_rad = math.radians(latitude)
        g = 9.780327 * (1.0 + 5.3024e-3 * math.sin(lat_rad)**2 - 5.8e-6 * math.sin(2.0 * lat_rad)**2)
        return 1.01325 + (1027.0 * g * depth) / 1e4

    def build_acoustic_profile(self, x: float, y: float, z: float, surface_temp: float, deep_temp: float, salinity: float, thermocline_depth: float = 100.0, freq: float = 50.0) -> AcousticPoint:
        temp = self.thermocline_gradient(surface_temp, deep_temp, z, thermocline_depth)
        ss = self.sound_speed(temp, salinity, z)
        abs_coeff = self.absorption(freq, temp, salinity, z)
        press = self.pressure(z)
        return AcousticPoint(x=x, y=y, z=z, temperature=temp, salinity=salinity, sound_speed=ss, absorption=abs_coeff, pressure=press)

    def jerlov_scatter_proxy(self, depth: float) -> float:
        return 1.0 - math.exp(-self.kd * depth)


try:
    from sonar_vision_physics import FluxPhysics as ExternalFluxPhysics  # type: ignore[import]
    _HAS_EXTERNAL_PHYSICS = True
    logger.info("Using external sonar_vision_physics.FluxPhysics")
except Exception:
    _HAS_EXTERNAL_PHYSICS = False
    logger.debug("External sonar_vision_physics not available; using built-in FluxPhysics")


def get_physics_backend(water_type: JerlovWaterType = JerlovWaterType.IA) -> PhysicsBackend:
    if _HAS_EXTERNAL_PHYSICS:
        try:
            return ExternalFluxPhysics(water_type=water_type.value)  # type: ignore[return-value]
        except Exception:
            logger.warning("External FluxPhysics failed to initialize; falling back")
    return FluxPhysics(water_type=water_type)
