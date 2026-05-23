# Competitive Landscape: AI Safety Hardware
## Hermes-70B

Here is the competitive landscape table for AI safety hardware:

| Company          | Product         | Safety Approach                   | Certification Level | Safe-TOPS/W | Weakness                                    | Our Advantage                         |
|------------------|-----------------|-----------------------------------|---------------------|--------------|--------------------------------------------|--------------------------------------|
| NVIDIA           | Jetson Orin AGX | GPU inference, ASIL D via lockstep| ASIL D              | 1.5          | No runtime verification                    | Runtime verification, higher Safe-TOPS/W |
| Mobileye         | EyeQ6H          | RSS software model, ASIL D        | ASIL D              | 2.0          | White-box rules, lower Safe-TOPS/W         | Black-box verification, higher Safe-TOPS/W |
| Hailo            | Hailo-8         | Edge TPU, ASIL B                   | ASIL B              | 0.5          | Lockstep only, lower certification        | Higher certification, runtime verification |
| Taalas           | HC1             | Compute-in-memory, ASIL D claim   | ASIL D (claim)     | 1.0          | Unproven technology, lower Safe-TOPS/W     | Proven technology, higher Safe-TOPS/W     |
| Groq             | LPU             | High throughput                   | None                | 0.1          | No safety certification                    | Safety certification, runtime verification |
| Google           | TPU v5e         | Datacenter only                   | None                | N/A          | No safety story, datacenter only          | Automotive focus, safety certification   |
| Qualcomm         | SA8650          | Automotive SoC, ASIL B/D split     | ASIL B/D            | 1.5          | Split certification, lower Safe-TOPS/W     | Unified certification, higher Safe-TOPS/W  |
| Tesla            | FSD HW4         | Custom inference                  | None (internal)     | 0.5          | No external certification                  | External certification, runtime verification |
| Intel            | Habana Gaudi    | AI training                       | None                | N/A          | No safety focus, training only            | Safety focus, inference                 |
| FLUX-LUCID (us)  | FLUX-LUCID      | Hardware constraint ISA, DAL A    | DAL A (path)        | 3.0          | New entrant, unproven in market           | Novel approach, highest Safe-TOPS/W      |

Our main advantages are our novel hardware constraint ISA approach, which allows for runtime verification and a path to DAL A certification. We also have the highest Safe-TOPS/W rating in the industry. However, we are a new entrant and our technology is still unproven in the market compared to more established competitors.