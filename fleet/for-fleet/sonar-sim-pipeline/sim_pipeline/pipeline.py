"""Sonar simulation pipeline.

Ties mission planning -> physics -> ray tracing -> display in one call.
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from .physics import FluxPhysics, JerlovWaterType, get_physics_backend
from .ray_tracer import PingResult, SonarRayTracer, get_ray_tracer_backend
from .mission_planner import Mission, MissionPlanner, SurveyType, Waypoint
from .display import DisplayPing, SonarDisplay

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Result of a full pipeline run."""
    mission: Mission
    pings: tuple[DisplayPing, ...]
    ping_results: tuple[PingResult, ...]
    json_path: str
    ascii_plot: str
    metadata: dict[str, Any]


class Pipeline:
    """End-to-end sonar simulation pipeline."""

    def __init__(
        self,
        survey_type: SurveyType = SurveyType.LAWNMOWER,
        width: float = 500.0,
        height: float = 500.0,
        depth: float = 50.0,
        line_spacing: float | None = None,
        speed: float = 2.5,
        water_type: JerlovWaterType = JerlovWaterType.IA,
        surface_temp: float = 20.0,
        deep_temp: float = 4.0,
        salinity: float = 35.0,
        thermocline_depth: float = 100.0,
        freq: float = 50.0,
        max_range: float = 500.0,
        ray_step: float = 1.0,
        n_beams: int = 101,
        aperture: float = 120.0,
        output_dir: str = "output",
    ) -> None:
        self.survey_type = survey_type
        self.width = width
        self.height = height
        self.depth = depth
        self.line_spacing = line_spacing
        self.speed = speed
        self.water_type = water_type
        self.surface_temp = surface_temp
        self.deep_temp = deep_temp
        self.salinity = salinity
        self.thermocline_depth = thermocline_depth
        self.freq = freq
        self.max_range = max_range
        self.ray_step = ray_step
        self.n_beams = n_beams
        self.aperture = aperture
        self.output_dir = output_dir
        self.planner = MissionPlanner(default_speed=speed, default_depth=depth)
        self.physics = get_physics_backend(water_type=water_type)
        self.tracer = get_ray_tracer_backend(max_range=max_range, step=ray_step, freq=freq)
        self.display = SonarDisplay()
        logger.info(
            "Pipeline initialized: %s survey %.0fx%.0f m, depth=%.1f m, freq=%.1f kHz",
            survey_type.value, width, height, depth, freq,
        )

    def _build_ssp(self) -> Callable[[float], float]:
        def ss_fn(z: float) -> float:
            temp = self.physics.thermocline_gradient(
                self.surface_temp, self.deep_temp, z, self.thermocline_depth
            )
            return self.physics.sound_speed(temp, self.salinity, z)
        return ss_fn

    def _build_absorption_fn(self) -> Callable[[float], float]:
        def abs_fn(z: float) -> float:
            temp = self.physics.thermocline_gradient(
                self.surface_temp, self.deep_temp, z, self.thermocline_depth
            )
            return self.physics.absorption(self.freq, temp, self.salinity, z)
        return abs_fn

    def run(
        self,
        multi_beam: bool = True,
        save_csv: bool = False,
    ) -> PipelineResult:
        mission = self.planner.plan(
            survey_type=self.survey_type,
            width=self.width,
            height=self.height,
            depth=self.depth,
            speed=self.speed,
            line_spacing=self.line_spacing,
        )
        ss_fn = self._build_ssp()
        abs_fn = self._build_absorption_fn()
        ping_results: list[PingResult] = []
        display_pings: list[DisplayPing] = []
        ping_idx = 0
        for wp in mission.waypoints:
            if wp.action != "ping":
                continue
            if multi_beam:
                beams = self.tracer.multi_beam_ping(
                    x=wp.x,
                    z=wp.z,
                    bottom_depth=self.depth,
                    n_beams=self.n_beams,
                    aperture=self.aperture,
                    sound_speed_fn=ss_fn,
                    absorption_fn=abs_fn,
                )
                center = beams[len(beams) // 2]
                beam_returns = tuple(b.bottom_return for b in beams)
                display_pings.append(
                    DisplayPing(
                        ping_index=ping_idx,
                        x=wp.x,
                        y=wp.y,
                        z=wp.z,
                        two_way_time=center.two_way_time,
                        bottom_return=center.bottom_return,
                        range_m=center.range_m,
                        beams=len(beams),
                        beam_returns=beam_returns,
                    )
                )
                ping_results.extend(beams)
            else:
                result = self.tracer.ping(
                    x=wp.x,
                    z=wp.z,
                    azimuth=0.0,
                    depression=math.radians(30.0),
                    bottom_depth=self.depth,
                    sound_speed_fn=ss_fn,
                    absorption_fn=abs_fn,
                )
                display_pings.append(
                    DisplayPing(
                        ping_index=ping_idx,
                        x=wp.x,
                        y=wp.y,
                        z=wp.z,
                        two_way_time=result.two_way_time,
                        bottom_return=result.bottom_return,
                        range_m=result.range_m,
                        beams=1,
                    )
                )
                ping_results.append(result)
            ping_idx += 1
        ascii_plot = self.display.waterfall_ascii(
            display_pings,
            mode="multi_beam" if multi_beam else "single_beam",
        )
        os.makedirs(self.output_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        json_filename = f"sonar_sim_{self.survey_type.value}_{ts}.json"
        json_path = os.path.join(self.output_dir, json_filename)
        mission_meta = {
            "survey_type": self.survey_type.value,
            "width_m": self.width,
            "height_m": self.height,
            "depth_m": self.depth,
            "line_spacing_m": mission.line_spacing,
            "speed_m_s": self.speed,
            "water_type": self.water_type.value,
            "surface_temp_c": self.surface_temp,
            "deep_temp_c": self.deep_temp,
            "salinity_psu": self.salinity,
            "thermocline_depth_m": self.thermocline_depth,
            "frequency_khz": self.freq,
            "n_beams": self.n_beams if multi_beam else 1,
            "aperture_deg": self.aperture,
            "n_pings": len(display_pings),
            "duration_estimate_s": round(mission.duration_estimate_s, 2),
        }
        self.display.save_json(display_pings, json_path, mission_metadata=mission_meta)
        if save_csv:
            csv_filename = f"sonar_sim_{self.survey_type.value}_{ts}.csv"
            csv_path = os.path.join(self.output_dir, csv_filename)
            self.display.save_csv(display_pings, csv_path)
        metadata = {
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "mission": mission_meta,
            "physics": {
                "water_type": self.water_type.value,
                "ssp_surface_m_s": round(ss_fn(0.0), 2),
                "ssp_bottom_m_s": round(ss_fn(self.depth), 2),
            },
        }
        logger.info(
            "Pipeline complete: %d pings, JSON=%s",
            len(display_pings), json_path,
        )
        return PipelineResult(
            mission=mission,
            pings=tuple(display_pings),
            ping_results=tuple(ping_results),
            json_path=json_path,
            ascii_plot=ascii_plot,
            metadata=metadata,
        )
