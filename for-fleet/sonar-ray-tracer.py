"""
Sonar Ray Tracer — propagates acoustic rays through the FLUX physics environment.

Uses the sonar-vision-physics engine for environmental params,
then traces rays through the sound speed profile using geometric acoustics.
"""
import math
from typing import List, Tuple, Optional

try:
    from sonar_vision_physics import FluxPhysics, compute_physics
except ImportError:
    # Fallback inline
    class FluxPhysics:
        def compute(self, depth, chl=5.0, season=0, sediment=1, wl=480.0, sal=35.0):
            wa = wl / 1000.0
            wt = 0 if chl > 10 else 1 if chl > 1 else 2 if chl > 0.1 else 3
            absorp = 0.04 + 0.96 * math.exp(-((wa - 0.42)**2) / (2 * 0.02**2)) if wt <= 1 else \
                     0.3 + 0.9 * math.exp(-((wa - 0.48)**2) / (2 * 0.03**2)) if wt == 2 else \
                     0.02 + 0.51 * math.exp(-((wa - 0.42)**2) / (2 * 0.015**2))
            ns = 0.002 * (480.0 / wl)**4.3
            scat = ns * max(0.01, 1.0 - depth * 0.003)
            tc, tw = (15.0, 5.0) if season == 0 else (40.0, 15.0)
            st, dt = (22.0, 4.0) if season == 0 else (8.0, 4.0)
            temp = dt + (st - dt) * math.exp(-((depth - tc)**2) / (2 * tw**2))
            ss = (1449.2 + 4.6*temp - 0.055*temp**2 + 0.00029*temp**3 +
                  (1.34 - 0.01*temp)*(sal - 35) + 0.016*depth)
            return {
                'depth': depth, 'temperature': temp, 'sound_speed': ss,
                'absorption': absorp, 'scattering': scat,
                'attenuation': absorp + scat,
                'visibility': min(depth, 1.7 / max(absorp + scat, 0.001)),
                'water_type': wt,
            }


class SonarRayTracer:
    """Geometric acoustic ray tracer through FLUX physics environment.
    
    Traces rays from a source through a layered sound speed profile
    computed from the FLUX physics engine. Rays refract according to
    Snell's law and attenuate according to absorption + spreading.
    """
    
    def __init__(self, max_depth: float = 100.0, layers: int = 200,
                 chl: float = 5.0, season: str = 'summer', sediment: str = 'sand'):
        self.max_depth = max_depth
        self.layers = layers
        self.physics = FluxPhysics()
        self.season = 0 if season == 'summer' else 1
        self.sed = {'mud': 0, 'sand': 1, 'gravel': 2, 'rock': 3, 'seagrass': 4}.get(sediment, 1)
        self.chl = chl
        self._build_profile()
    
    def _build_profile(self):
        """Build the layered sound speed profile from FLUX physics."""
        self.depths = [i * self.max_depth / self.layers for i in range(self.layers + 1)]
        self.ssp = []  # Sound speed profile
        self.temps = []
        self.attens = []
        for d in self.depths:
            p = self.physics.compute(d, chl=self.chl, season=self.season,
                                     sediment=self.sed)
            self.ssp.append(p['sound_speed'])
            self.temps.append(p['temperature'])
            self.attens.append(p['attenuation'])
    
    def sound_speed_at(self, depth: float) -> float:
        """Interpolate sound speed at a given depth."""
        idx = int(depth * self.layers / self.max_depth)
        idx = max(0, min(idx, self.layers - 1))
        frac = (depth - self.depths[idx]) / (self.depths[idx+1] - self.depths[idx]) \
               if idx < self.layers else 0
        return self.ssp[idx] + frac * (self.ssp[idx + 1] - self.ssp[idx])
    
    def trace_ray(self, source_depth: float, angle_deg: float,
                  target_range: float, steps: int = 500) -> List[Tuple[float, float, float, float]]:
        """Trace a single acoustic ray.
        
        Args:
            source_depth: Starting depth (m)
            angle_deg: Launch angle from horizontal (deg). Positive = downward
            target_range: Maximum horizontal range (m)
            steps: Number of integration steps
            
        Returns:
            List of (range_m, depth_m, sound_speed_mps, intensity_db) points
        """
        ray = []
        r, z = 0.0, source_depth
        theta = math.radians(angle_deg)
        c0 = self.sound_speed_at(z)
        dr = target_range / steps
        
        # Initial intensity (reference 0 dB)
        intensity = 0.0
        spreading_loss_per_step = 0.5  # dB per step (cylindrical spreading)
        
        for _ in range(steps):
            c = self.sound_speed_at(z)
            
            # Snell's law: sin(theta) / c = constant
            # But in a layered medium, we use ray invariants
            # n(z) * sin(theta) = constant, where n = c0/c(z)
            n_ratio = c0 / c
            
            # Update angle via Snell's law in the gradient
            # For small steps, theta_new = theta_old + gradient contribution
            dz = dr * math.tan(theta)
            z_new = z + dz
            
            if z_new < 0:
                # Surface reflection (phase flip)
                z_new = -z_new
                theta = -theta
            elif z_new > self.max_depth:
                # Bottom reflection (seabed)
                z_new = 2 * self.max_depth - z_new
                theta = -theta
            
            # Refraction: sound speed gradient turns the ray
            c_new = self.sound_speed_at(z_new)
            dc_dz = (c_new - c) / max(dz, 0.1)
            theta += -dc_dz / c * dr  # Eikonal equation approximation
            
            z = z_new
            r += dr
            
            # Attenuation: absorption + spreading
            atten = self._attenuation_at(z)
            step_loss = spreading_loss_per_step + atten * abs(dz) * 10.0
            intensity -= step_loss
            
            ray.append((r, z, c_new, intensity))
            
            if r >= target_range:
                break
        
        return ray
    
    def _attenuation_at(self, depth: float) -> float:
        idx = int(depth * self.layers / self.max_depth)
        idx = max(0, min(idx, self.layers))
        return self.attens[idx]
    
    def compute_return(self, source_depth: float, target_depth: float,
                       target_range: float) -> dict:
        """Compute the sonar return for a given source-target geometry.
        
        Models: outbound ray + seabed reflection + inbound ray.
        """
        # Downward ray to seabed at target range
        outbound = self.trace_ray(source_depth, 15.0, target_range)
        if not outbound:
            return {'error': 'No ray path found'}
        
        # Seabed reflection
        last = outbound[-1]
        seabed_depth = last[1]
        seabed_hit = self.physics.compute(seabed_depth, chl=self.chl,
                                           season=self.season, sediment=self.sed)
        seabed_refl = seabed_hit['seabed_reflectivity']
        
        # Return ray (upward)
        inbound = self.trace_ray(seabed_depth, -15.0, target_range)
        
        # Total travel time and loss
        total_time = 0.0
        total_loss = 0.0
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
            'seabed_depth_m': round(seabed_depth, 1),
            'outbound_steps': len(outbound),
            'inbound_steps': len(inbound),
        }
    
    def fan_scan(self, source_depth: float = 10.0,
                 min_angle: float = -30, max_angle: float = 30,
                 num_rays: int = 13, target_range: float = 200.0) -> List[dict]:
        """Emit a fan of rays and compute returns."""
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


def demo():
    """Run a complete sonar ping simulation."""
    print("=== SONAR RAY TRACER DEMO ===")
    print()
    
    tracer = SonarRayTracer(max_depth=100.0, chl=4.0, season='summer')
    
    p = tracer.physics.compute(15.0, chl=4.0, season=0)
    print(f"Environment: {p['water_type_name']}, T={p['temperature']:.1f}C, "
          f"c={p['sound_speed']:.0f} m/s")
    print()
    
    # Single ray
    print("--- Single Ray: 15 degrees downward from 10m ---")
    ray = tracer.trace_ray(10.0, 15.0, 100.0)
    for i, (r, z, c, db) in enumerate(ray):
        if i % 50 == 0 or i == len(ray) - 1:
            print(f"  r={r:6.1f}m  z={z:6.1f}m  c={c:7.1f}m/s  loss={db:6.1f}dB")
    
    print()
    
    # Sonar return
    ret = tracer.compute_return(10.0, 50.0, 100.0)
    print("--- Sonar Return (10m source, 100m range, 50m target) ---")
    for k, v in ret.items():
        print(f"  {k}: {v}")
    
    print()
    
    # Fan scan
    print("--- Fan Scan (13 rays, -30 to +30 degrees) ---")
    scan = tracer.fan_scan(source_depth=10.0)
    print(f"  {'Angle':>6} {'Depth':>8} {'Range':>8} {'Intensity':>10} {'c':>8}")
    for s in scan:
        print(f"  {s['angle_deg']:>5.1f}° {s['terminal_depth_m']:>7.1f}m "
              f"{s['terminal_range_m']:>7.1f}m {s['terminal_intensity_db']:>8.1f}dB "
              f"{s['terminal_sound_speed_mps']:>7.0f}m/s")
    
    return tracer


if __name__ == '__main__':
    demo()
