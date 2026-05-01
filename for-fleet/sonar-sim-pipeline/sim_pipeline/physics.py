"""FLUX 9-opcode marine physics engine. Self-contained, deterministic."""

import math

WATER_TYPES = {0: 'Coastal', 1: 'Oceanic Type II', 2: 'Oceanic Type IB', 3: 'Clear Oceanic'}
SEDIMENT_NAMES = {0: 'mud', 1: 'sand', 2: 'gravel', 3: 'rock', 4: 'seagrass'}
SEDIMENT_REFLECT = {0: 0.3, 1: 0.5, 2: 0.7, 3: 0.85, 4: 0.2}


class FluxPhysics:
    """Deterministic FLUX 9-opcode marine physics engine."""

    def compute(self, depth, chl=5.0, season=0, sediment=1, wl=480.0, sal=35.0):
        # Handle string inputs
        if isinstance(season, str):
            season = 0 if season == 'summer' else 1
        if isinstance(sediment, str):
            sed_map = {'mud': 0, 'sand': 1, 'gravel': 2, 'rock': 3, 'seagrass': 4}
            sediment = sed_map.get(sediment, 1)

        # Jerlov water type
        wt = 0 if chl > 10 else 1 if chl > 1 else 2 if chl > 0.1 else 3

        # Francois-Garrison absorption
        wa = wl / 1000.0
        if wt <= 1:
            absorp = 0.04 + 0.96 * math.exp(-((wa - 0.42)**2) / (2 * 0.02**2))
        elif wt == 2:
            absorp = 0.3 + 0.9 * math.exp(-((wa - 0.48)**2) / (2 * 0.03**2))
        else:
            absorp = 0.02 + 0.51 * math.exp(-((wa - 0.42)**2) / (2 * 0.015**2))

        # Rayleigh scattering
        ns = 0.002 * (480.0 / wl)**4.3
        scat = ns * max(0.01, 1.0 - depth * 0.003)

        # Thermocline
        tc, tw = (15.0, 5.0) if season == 0 else (40.0, 15.0)
        st, dt = (22.0, 4.0) if season == 0 else (8.0, 4.0)
        temp = dt + (st - dt) * math.exp(-((depth - tc)**2) / (2 * tw**2))
        dtdz = -(st - dt) * (depth - tc) / (tw**2) * math.exp(-((depth - tc)**2) / (2 * tw**2))

        # Seabed
        seabed_refl = SEDIMENT_REFLECT.get(sediment, 0.5) * math.exp(-depth * 0.003)

        # Attenuation
        atten = absorp + scat

        # Visibility (Secchi)
        vis = min(depth, 1.7 / max(atten, 0.001))

        # Mackenzie sound speed
        ss = (1449.2 + 4.6*temp - 0.055*temp**2 + 0.00029*temp**3 +
              (1.34 - 0.01*temp)*(sal - 35) + 0.016*depth)

        # Snell refraction
        v_ratio = ss / 1480.0
        theta = math.sin(math.pi / 6)
        st2 = theta * (1.0 / v_ratio)
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
            'seabed_reflectivity': round(seabed_refl, 4),
            'sound_speed': round(ss, 1),
            'refraction_deg': round(refrac, 2),
            'sediment': SEDIMENT_NAMES[sediment],
        }


class SonarRayTracer:
    """Geometric acoustic ray tracer using Snell's law through FLUX physics."""

    def __init__(self, max_depth=100.0, layers=200, chl=5.0,
                 season='summer', sediment='sand'):
        self.max_depth = max_depth
        self.layers = layers
        self.physics = FluxPhysics()
        self.season = 0 if isinstance(season, str) and season == 'summer' else \
                      1 if isinstance(season, str) else season
        sed_map = {'mud': 0, 'sand': 1, 'gravel': 2, 'rock': 3, 'seagrass': 4}
        self.sed = sed_map.get(sediment, 1) if isinstance(sediment, str) else sediment
        self.chl = chl
        self._build_profile()

    def _build_profile(self):
        self.depths = [i * self.max_depth / self.layers for i in range(self.layers + 1)]
        self.ssp = []
        for d in self.depths:
            p = self.physics.compute(d, chl=self.chl, season=self.season, sediment=self.sed)
            self.ssp.append(p['sound_speed'])

    def sound_speed_at(self, depth):
        idx = int(depth * self.layers / self.max_depth)
        idx = max(0, min(idx, self.layers - 1))
        frac = (depth - self.depths[idx]) / (self.depths[idx+1] - self.depths[idx]) \
               if idx < self.layers else 0
        return self.ssp[idx] + frac * (self.ssp[idx + 1] - self.ssp[idx])

    def trace_ray(self, source_depth, angle_deg, target_range, steps=500):
        ray = []
        r, z = 0.0, source_depth
        theta = math.radians(angle_deg)
        c0 = self.sound_speed_at(z)
        dr = target_range / steps
        intensity = 0.0
        for _ in range(steps):
            c = self.sound_speed_at(z)
            dz = dr * math.tan(theta)
            z_new = z + dz
            if z_new < 0:
                z_new = -z_new
                theta = -theta
            elif z_new > self.max_depth:
                z_new = 2 * self.max_depth - z_new
                theta = -theta
            c_new = self.sound_speed_at(z_new)
            dc_dz = (c_new - c) / max(dz, 0.1)
            theta += -dc_dz / c * dr
            z = z_new
            r += dr
            intensity -= 0.5 + self._attenuation_at(z) * abs(dz) * 10.0
            ray.append((r, z, c_new, intensity))
            if r >= target_range:
                break
        return ray

    def _attenuation_at(self, depth):
        idx = int(depth * self.layers / self.max_depth)
        idx = max(0, min(idx, self.layers))
        p = self.physics.compute(self.depths[idx], chl=self.chl, season=self.season,
                                 sediment=self.sed)
        return p['attenuation']

    def compute_return(self, source_depth, target_depth, target_range):
        outbound = self.trace_ray(source_depth, 15.0, target_range)
        if not outbound:
            return {'error': 'No ray path found'}
        last = outbound[-1]
        seabed_p = self.physics.compute(last[1], chl=self.chl, season=self.season,
                                        sediment=self.sed)
        seabed_refl = seabed_p['seabed_reflectivity']
        inbound = self.trace_ray(last[1], -15.0, target_range)
        total_time, total_loss = 0.0, 0.0
        for points in [outbound, inbound]:
            for i in range(1, len(points)):
                p0, p1 = points[i-1], points[i]
                dist = math.sqrt((p1[0] - p0[0])**2 + (p1[1] - p0[1])**2)
                c_avg = (p0[2] + p1[2]) / 2.0
                total_time += dist / c_avg
            total_loss += abs(points[-1][3] - points[0][3])
        total_loss += -10 * math.log10(seabed_refl) if seabed_refl > 0 else 50.0
        return {
            'total_travel_time_s': round(total_time, 4),
            'total_loss_db': round(total_loss, 1),
            'seabed_reflectivity': round(seabed_refl, 4),
            'seabed_depth_m': round(last[1], 1),
            'outbound_steps': len(outbound),
            'inbound_steps': len(inbound),
        }

    def fan_scan(self, source_depth=10.0, min_angle=-30, max_angle=30,
                 num_rays=13, target_range=200.0):
        results = []
        for i in range(num_rays):
            angle = min_angle + (max_angle - min_angle) * i / (num_rays - 1)
            ray = self.trace_ray(source_depth, angle, target_range)
            if ray:
                last = ray[-1]
                results.append({
                    'angle_deg': round(angle, 1),
                    'terminal_depth_m': round(last[1], 1),
                    'terminal_range_m': round(last[0], 1),
                    'terminal_intensity_db': round(last[3], 1),
                    'terminal_sound_speed_mps': round(last[2], 1),
                })
        return results


def compute_physics(depth, chl=5.0, season='summer', sediment='sand', wl=480.0, sal=35.0):
    """Convenience: single ping. Accepts str season/sediment."""
    return FluxPhysics().compute(depth, chl, season, sediment, wl, sal)


def dive_profile(start=0, end=100, step=5, chl=5.0, season='summer', sediment='sand'):
    """Compute physics for a range of depths."""
    depths = list(range(start, end + 1, step))
    phys = FluxPhysics()
    return [phys.compute(d, chl=max(0.05, chl - d * 0.12),
                         season=season, sediment=sediment) for d in depths]
