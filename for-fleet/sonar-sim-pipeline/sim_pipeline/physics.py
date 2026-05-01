"""FLUX 9-opcode deterministic underwater acoustics. Self-contained."""
import math

WATER_TYPES = {0: "Coastal", 1: "Oceanic Type II", 2: "Oceanic Type IB", 3: "Clear Oceanic"}
SEDIMENT_NAMES = {0: "mud", 1: "sand", 2: "gravel", 3: "rock", 4: "seagrass"}
SEDIMENT_REFLECT = {0: 0.3, 1: 0.5, 2: 0.7, 3: 0.85, 4: 0.2}


class FluxPhysics:
    """Deterministic underwater acoustics engine matching FLUX ISA opcodes 0xB0-0xB8."""

    def compute(self, depth, chl=5.0, season=0, sediment=1, wl=480.0, sal=35.0):
        """Compute marine physics at a single depth point.

        Args:
            depth: Water depth in meters
            chl: Chlorophyll concentration (mg/m3)
            season: 0=summer, 1=winter (or string 'summer'/'winter')
            sediment: 0=mud,1=sand,2=gravel,3=rock,4=seagrass (or string)
            wl: Wavelength in nm (default 480)
            sal: Salinity in PSU (default 35)
        Returns:
            dict with temperature, sound_speed, absorption, visibility, etc.
        """
        if isinstance(season, str):
            season = 0 if season == "summer" else 1
        if isinstance(sediment, str):
            sediment = {"mud": 0, "sand": 1, "gravel": 2,
                        "rock": 3, "seagrass": 4}.get(sediment, 1)

        # Water type from chlorophyll
        wt = 0 if chl > 10 else 1 if chl > 1 else 2 if chl > 0.1 else 3

        # Francois-Garrison absorption (PHY_ABSORB opcode 0xB0)
        wa = wl / 1000.0
        if wt <= 1:
            ab = 0.04 + 0.96 * math.exp(-((wa - 0.42)**2) / (2 * 0.02**2))
        elif wt == 2:
            ab = 0.3 + 0.9 * math.exp(-((wa - 0.48)**2) / (2 * 0.03**2))
        else:
            ab = 0.02 + 0.51 * math.exp(-((wa - 0.42)**2) / (2 * 0.015**2))

        # Rayleigh scattering (PHY_SCATTER opcode 0xB1)
        ns = 0.002 * (480.0 / wl)**4.3
        sc = ns * max(0.01, 1.0 - depth * 0.003)

        # Gaussian thermocline (PHY_TEMP opcode 0xB2)
        tc, tw = (15.0, 5.0) if season == 0 else (40.0, 15.0)
        st, dt = (22.0, 4.0) if season == 0 else (8.0, 4.0)
        te = dt + (st - dt) * math.exp(-((depth - tc)**2) / (2 * tw**2))
        dtdz = -(st - dt) * (depth - tc) / (tw**2) * math.exp(-((depth - tc)**2) / (2 * tw**2))

        # Seabed reflectivity (PHY_REFLECT opcode 0xB3)
        sr = SEDIMENT_REFLECT.get(sediment, 0.5) * math.exp(-depth * 0.003)

        # Total attenuation and visibility
        att = ab + sc
        vis = min(depth, 1.7 / max(att, 0.001))

        # Mackenzie sound speed (PHY_SSP opcode 0xB4)
        ss = (1449.2 + 4.6*te - 0.055*te**2 + 0.00029*te**3 +
              (1.34 - 0.01*te)*(sal - 35) + 0.016*depth)

        # Snell refraction angle (PHY_REFRAC opcode 0xB8)
        c0 = 1480.0
        sin_theta = math.sin(math.radians(15)) / max(ss / c0, 0.001)
        refr = math.degrees(math.asin(sin_theta)) if abs(sin_theta) <= 1 else 90.0

        return dict(
            depth=round(depth, 1),
            water_type=wt,
            water_type_name=WATER_TYPES[wt],
            temperature=round(te, 2),
            dTdz=round(dtdz, 4),
            absorption=round(ab, 4),
            scattering=round(sc, 4),
            attenuation=round(att, 3),
            visibility=round(vis, 2),
            seabed_reflectivity=round(sr, 4),
            sound_speed=round(ss, 1),
            refraction_deg=round(refr, 2),
            sediment=SEDIMENT_NAMES[sediment],
        )


def compute_physics(depth, chl=5.0, season="summer", sediment="sand",
                    wl=480.0, sal=35.0):
    """Convenience: compute physics at a single depth."""
    return FluxPhysics().compute(depth, chl, season, sediment, wl, sal)


def dive_profile(start=0, end=100, step=5, chl=5.0, season="summer",
                 sediment="sand"):
    """Convenience: compute physics profile across a depth range."""
    phys = FluxPhysics()
    return [phys.compute(float(d), chl=max(0.05, chl - d * 0.12),
                         season=season, sediment=sediment)
            for d in range(start, end + 1, step)]


class SonarRayTracer:
    """Geometric acoustic ray tracer through depth-varying SSP."""

    def __init__(self, max_depth=100.0, layers=200, chl=5.0,
                 season="summer", sediment="sand"):
        self.max_depth = max_depth
        self.layers = layers
        self.chl = chl
        self.season = 0 if (isinstance(season, str) and
                           season == "summer") else 1
        self.sediment = 1 if isinstance(sediment, str) else sediment
        if isinstance(sediment, str):
            self.sediment = {"mud": 0, "sand": 1, "gravel": 2,
                             "rock": 3, "seagrass": 4}.get(sediment, 1)

        self.depths = [i * max_depth / layers for i in range(layers + 1)]
        self.ssp = [
            FluxPhysics().compute(d, chl=chl, season=self.season,
                                  sediment=self.sediment)["sound_speed"]
            for d in self.depths
        ]

    def sound_speed_at(self, depth):
        idx = max(0, min(int(depth * self.layers / self.max_depth),
                        self.layers - 1))
        frac = ((depth - self.depths[idx]) /
                (self.depths[idx + 1] - self.depths[idx])
                if idx < self.layers else 0)
        return self.ssp[idx] + frac * (self.ssp[idx + 1] - self.ssp[idx])

    def _att_at(self, depth):
        idx = max(0, min(int(depth * self.layers / self.max_depth),
                        self.layers))
        return FluxPhysics().compute(self.depths[idx], chl=self.chl,
                                      season=self.season,
                                      sediment=self.sediment)["attenuation"]

    def trace_ray(self, sd, angle, rng, steps=500):
        r, z = 0.0, sd
        theta = math.radians(angle)
        dr = rng / steps
        I = 0.0
        ray = []
        for _ in range(steps):
            c = self.sound_speed_at(z)
            dz = dr * math.tan(theta)
            zn = z + dz
            if zn < 0:
                zn = -zn
                theta = -theta
            elif zn > self.max_depth:
                zn = 2 * self.max_depth - zn
                theta = -theta
            cn = self.sound_speed_at(zn)
            s2 = math.sin(theta) * cn / max(c, 0.1)
            theta = math.asin(s2) if abs(s2) <= 1 else -theta
            z = zn
            r += dr
            I -= 0.5 + self._att_at(z) * abs(dz) * 10.0
            ray.append((r, z, cn, I))
            if r >= rng:
                break
        return ray

    def compute_return(self, sd, td, rng):
        out = self.trace_ray(sd, 15.0, rng)
        if not out:
            return dict(error="No ray path", total_travel_time_s=-1,
                        total_loss_db=-1)
        last = out[-1]
        sb = FluxPhysics().compute(last[1], chl=self.chl,
                                   season=self.season,
                                   sediment=self.sediment)
        sbr = sb["seabed_reflectivity"]
        back = self.trace_ray(last[1], -15.0, rng)
        tt, tl = 0.0, 0.0
        for pts in [out, back]:
            for i in range(1, len(pts)):
                p0, p1 = pts[i-1], pts[i]
                d = math.sqrt((p1[0]-p0[0])**2 + (p1[1]-p0[1])**2)
                tt += d / ((p0[2] + p1[2]) / 2)
            tl += abs(pts[-1][3] - pts[0][3])
        tl += -10 * math.log10(sbr) if sbr > 0 else 50.0
        return dict(total_travel_time_s=round(tt, 4),
                    total_loss_db=round(tl, 1),
                    seabed_reflectivity=round(sbr, 4),
                    seabed_depth_m=round(last[1], 1),
                    outbound_steps=len(out), inbound_steps=len(back))

    def fan_scan(self, sd=10.0, rng=200.0, min_a=-30, max_a=30, nr=13):
        res = []
        for i in range(nr):
            a = min_a + (max_a - min_a) * i / (nr - 1)
            ray = self.trace_ray(sd, a, rng)
            if ray:
                l = ray[-1]
                res.append(dict(angle_deg=round(a, 1),
                                terminal_depth_m=round(l[1], 1),
                                terminal_range_m=round(l[0], 1),
                                terminal_intensity_db=round(l[3], 1)))
        return res
