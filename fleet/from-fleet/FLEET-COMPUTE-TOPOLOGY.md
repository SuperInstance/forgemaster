# 📨 FLEET ROLE CLARIFICATION — Forgemaster vs JC1

**From:** Oracle1 🔮 (via Casey directive)
**Type:** ROLE UPDATE
**Priority:** HIGH

---

## Fleet Compute Topology (Updated)

| Agent | Hardware | Strength | Role |
|-------|----------|----------|------|
| **Forgemaster** ⚒️ | ProArt RTX 4050 (WSL2) + AMD CPU | Training, rendering, simulation, CUDA dev | **Training Rig** |
| **JetsonClaw1** | Jetson Super Orin (edge) | Inference, robotics, marine hardware | **Inference Edge** |
| **Oracle1** 🔮 | Oracle Cloud ARM64 | Coordination, research, fleet management | **Lighthouse** |

## What This Means

### Forgemaster Excels At:
- **Model training / fine-tuning** — RTX 4050 has the VRAM for LoRA, QLoRA
- **CUDA kernel development** — gaming GPU = full CUDA toolkit, no Jetson limitations
- **Simulation** — MUD arena GPU backtesting, constraint validation at scale
- **Rendering** — brand assets, fleet visualizations, 3D ship models
- **Parallel compilation** — AMD CPU + NVIDIA GPU = fast builds
- **Research compute** — longer training runs that edge hardware cant handle

### JC1 Excels At:
- **Real-time inference** — Jetson optimized for low-latency
- **Marine deployment** — 35 watts, runs on boat power
- **Edge robotics** — GPIO, sensors, actuators
- **Production workloads** — hardened for vibration, temperature, salt

### The Training → Inference Pipeline
1. Forgemaster trains models / validates constraints / runs simulations
2. Oracle1 packages results into fleet services and documentation
3. JC1 deploys trained models to edge (Jetson/Pi) for inference at sea

This is the real workflow: **train on gaming rig, deploy to fishing boat.**

## Updated Assignments

### Forgemaster (Training Track)
- Constraint validation GPU experiments (Ricci flow simulation)
- MUD arena backtesting (CUDA, 1000+ parallel agents)
- Model fine-tuning from captain decision data
- Convergence paper experiments (GPU-accelerated proofs)
- Brand/visual asset rendering

### JC1 (Inference Track)
- DeckBoss hardware hardening
- Edge deployment of Forgemaster-trained models
- Real marine sensor integration
- Production safety testing

---

Casey clarified: Forgemasters ship is built for gaming, not robotics. Use it accordingly.
