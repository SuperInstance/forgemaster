"""FLUX 9-opcode marine physics. Self-contained, deterministic."""
import math

WATER_TYPES={0:"Coastal",1:"Oceanic Type II",2:"Oceanic Type IB",3:"Clear Oceanic"}
SEDIMENT_NAMES={0:"mud",1:"sand",2:"gravel",3:"rock",4:"seagrass"}
SEDIMENT_REFLECT={0:0.3,1:0.5,2:0.7,3:0.85,4:0.2}

class FluxPhysics:
    def compute(self,depth,chl=5.0,season=0,sediment=1,wl=480.0,sal=35.0):
        if isinstance(season,str): season=0 if season=="summer" else 1
        if isinstance(sediment,str): sediment={"mud":0,"sand":1,"gravel":2,"rock":3,"seagrass":4}.get(sediment,1)
        wt=0 if chl>10 else 1 if chl>1 else 2 if chl>0.1 else 3
        wa=wl/1000.0
        if wt<=1: ab=0.04+0.96*math.exp(-((wa-0.42)**2)/(2*0.02**2))
        elif wt==2: ab=0.3+0.9*math.exp(-((wa-0.48)**2)/(2*0.03**2))
        else: ab=0.02+0.51*math.exp(-((wa-0.42)**2)/(2*0.015**2))
        ns=0.002*(480.0/wl)**4.3; sc=ns*max(0.01,1.0-depth*0.003)
        tc,tw=(15.0,5.0) if season==0 else (40.0,15.0)
        st,dt=(22.0,4.0) if season==0 else (8.0,4.0)
        te=dt+(st-dt)*math.exp(-((depth-tc)**2)/(2*tw**2))
        sr=SEDIMENT_REFLECT.get(sediment,0.5)*math.exp(-depth*0.003)
        att=ab+sc; vis=min(depth,1.7/max(att,0.001))
        ss=(1449.2+4.6*te-0.055*te**2+0.00029*te**3+(1.34-0.01*te)*(sal-35)+0.016*depth)
        return {"depth":round(depth,1),"water_type":wt,"water_type_name":WATER_TYPES[wt],
                "temperature":round(te,2),"dTdz":round(-(st-dt)*(depth-tc)/(tw**2)*math.exp(-((depth-tc)**2)/(2*tw**2)),4),
                "absorption":round(ab,4),"scattering":round(sc,4),
                "attenuation":round(att,3),"visibility":round(vis,2),
                "seabed_reflectivity":round(sr,4),"sound_speed":round(ss,1),
                "refraction_deg":round(90.0 if ss/1480.0*math.sin(math.pi/6)>1 else math.degrees(math.asin(math.sin(math.pi/6)/(ss/1480.0))),2),
                "sediment":SEDIMENT_NAMES[sediment]}

class SonarRayTracer:
    def __init__(self,max_depth=100.0,layers=200,chl=5.0,season="summer",sediment="sand"):
        self.max_depth=max_depth; self.layers=layers; self.physics=FluxPhysics()
        self.season=0 if isinstance(season,str)&(season=="summer") else 1 if isinstance(season,str) else season
        self.sed={"mud":0,"sand":1,"gravel":2,"rock":3,"seagrass":4}.get(sediment,1) if isinstance(sediment,str) else sediment
        self.chl=chl
        self.depths=[i*max_depth/layers for i in range(layers+1)]
        self.ssp=[self.physics.compute(d,chl=chl,season=self.season,sediment=self.sed)["sound_speed"] for d in self.depths]

def compute_physics(depth, chl=5.0, season="summer", sediment="sand", wl=480.0, sal=35.0):
    return FluxPhysics().compute(depth, chl, season, sediment, wl, sal)

def dive_profile(start=0, end=100, step=5, chl=5.0, season="summer", sediment="sand"):
    phys = FluxPhysics()
    return [phys.compute(float(d), chl=max(0.05, chl-d*0.12), season=season, sediment=sediment) for d in range(start, end+1, step)]

class SonarRayTracer:
    def __init__(self, max_depth=100.0, layers=200, chl=5.0, season="summer", sediment="sand"):
        self.max_depth=max_depth; self.layers=layers; self.physics=FluxPhysics()
        if isinstance(season,str): self.season=0 if season=="summer" else 1
        else: self.season=season
        if isinstance(sediment,str): self.sed={"mud":0,"sand":1,"gravel":2,"rock":3,"seagrass":4}.get(sediment,1)
        else: self.sed=sediment
        self.chl=chl
        self.depths=[i*max_depth/layers for i in range(layers+1)]
        self.ssp=[self.physics.compute(d,chl=chl,season=self.season,sediment=self.sed)["sound_speed"] for d in self.depths]
    def sound_speed_at(self, depth):
        idx=max(0,min(int(depth*self.layers/self.max_depth),self.layers-1))
        frac=(depth-self.depths[idx])/(self.depths[idx+1]-self.depths[idx]) if idx<self.layers else 0
        return self.ssp[idx]+frac*(self.ssp[idx+1]-self.ssp[idx])
    def trace_ray(self, sd, angle, rng, steps=500):
        r, z = 0.0, sd; theta = math.radians(angle); dr = rng/steps; I = 0.0; ray = []
        for _ in range(steps):
            c = self.sound_speed_at(z); dz = dr*math.tan(theta); zn = z+dz
            if zn < 0: zn = -zn; theta = -theta
            elif zn > self.max_depth: zn = 2*self.max_depth-zn; theta = -theta
            cn = self.sound_speed_at(zn); theta += -(cn-c)/max(dz,0.1)/c*dr
            z = zn; r += dr
            I -= 0.5 + self._att_at(z)*abs(dz)*10.0
            ray.append((r, z, cn, I))
            if r >= rng: break
        return ray
    def _att_at(self, depth):
        idx = max(0, min(int(depth*self.layers/self.max_depth), self.layers))
        return self.physics.compute(self.depths[idx], chl=self.chl, season=self.season, sediment=self.sed)["attenuation"]
    def compute_return(self, sd, td, rng):
        out = self.trace_ray(sd, 15.0, rng)
        if not out: return {"error":"No ray path found"}
        last=out[-1]; sb=self.physics.compute(last[1],chl=self.chl,season=self.season,sediment=self.sed)
        sbr=sb["seabed_reflectivity"]; back=self.trace_ray(last[1],-15.0,rng)
        tt,tl=0.0,0.0
        for pts in [out,back]:
            for i in range(1,len(pts)):
                p0,p1=pts[i-1],pts[i]
                d=math.sqrt((p1[0]-p0[0])**2+(p1[1]-p0[1])**2)
                tt+=d/((p0[2]+p1[2])/2)
            tl+=abs(pts[-1][3]-pts[0][3])
        tl+=-10*math.log10(sbr) if sbr>0 else 50.0
        return {"total_travel_time_s":round(tt,4),"total_loss_db":round(tl,1),
                "seabed_reflectivity":round(sbr,4),"seabed_depth_m":round(last[1],1),
                "outbound_steps":len(out),"inbound_steps":len(back)}
    def fan_scan(self, sd=10.0, min_a=-30, max_a=30, nr=13, rng=200.0):
        res = []
        for i in range(nr):
            a = min_a + (max_a-min_a)*i/(nr-1)
            ray = self.trace_ray(sd, a, rng)
            if ray:
                l = ray[-1]
                res.append({"angle_deg": round(a,1), "terminal_depth_m": round(l[1],1),
                            "terminal_range_m": round(l[0],1), "terminal_intensity_db": round(l[3],1),
                            "terminal_sound_speed_mps": round(l[2],1)})
        return res
