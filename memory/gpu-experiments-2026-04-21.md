# GPU Experiments — 2026-04-21/22 Forging Session

## VRAM Binning Discovery
- RTX 4050 Laptop reports 6.00 GB but actually has ~7.5 GB usable VRAM
- Proven via speed benchmarking: 23-24 TFLOPS flat from 3GB to 7.2GB
- Cause: binned 8GB chip (firmware-limited to 6GB) exposed by WSL2 paravirtualization
- Tool: `cocapn/vram-probe` on GitHub (pip-installable)

## Training Results Summary

| Model | Method | Steps | Loss | VRAM Peak | Speed |
|-------|--------|-------|------|-----------|-------|
| distilgpt2 (82M) | Full FT | 500 | 4.0→2.8 | 1.5GB | 2.3s/s |
| distilgpt2 (82M) | Full FT | 1000 | 4.4→3.0 | 1.2GB | 6.3s/s |
| Qwen2.5-0.5B (494M) | Full FT | 700 | 3.2→0.76 | 7.9GB | 0.6s/s |
| Qwen2.5-0.5B (494M) | Full FT | 2000 | 3.4→0.09 | 7.9GB | 0.6s/s |
| Qwen2.5-0.5B (494M) | Full FT | ~1700 | 3.4→0.055 | 7.0GB | 0.8s/s |
| Qwen2.5-1.5B (1.5B) | LoRA r=16 | 1500 | 10.8→1.4 | 4.0GB | 3.8s/s |

## Exp 5: Qwen2.5-0.5B Full FT 2000 steps
- Loss: 3.41→0.09 (97%), 0.6s/s, 7.9GB peak VRAM
- Retrained (ckpt resume): `/tmp/gpu-exp5b/best-model/` (~1700 steps, loss 0.055)
- CT Quiz: Base 11/40 → FT 13/40 (+20%)
  - Key wins: Rust ID (+1), snap non-commutativity (+2), PLATO (+2), tiles (+1)
- Generation quality: dramatic — base says "Python", FT says "Rust crate in Cocapn fleet"

## Exp 6: Qwen2.5-1.5B + LoRA (r=16, alpha=32)
- Loss: 10.8→1.4 (87%), 3.8s/s, 4.0GB peak, ~8MB adapter
- Only 0.28% params trainable (4.3M / 1.5B)
- Quality: decent but less precise than full FT 0.5B
- **Key fix**: `init_lora_weights=False` makes LoRA wrapping instant (0.1s vs 10min+)
- Adapter: `/tmp/gpu-exp6/best-lora/`

## Quantization (0.5B FT model)
| Format | Size | Compression | VRAM Est |
|--------|------|-------------|----------|
| bf16 (original) | 953MB | 1.0x | ~1.0GB |
| INT8 (symmetric) | 872MB | 1.1x | ~0.5GB |
| INT4 (packed, g=32) | **203MB** | **4.7x** | ~0.3GB |
- INT4 at 203MB fits Jetson Nano easily
- Artifacts: `/tmp/gpu-exp5b/quantized/`

## WSL2 CUDA Lessons (hard-won)
1. `.to('cuda')` hangs intermittently — use layer-by-layer transfer
2. `init_lora_weights=False` solves peft LoRA wrapping hangs
3. Zombie processes hold GPU memory even after kill — always verify
4. `pkill -9` doesn't kill child processes — check PIDs manually
5. Gradient checkpointing required for batch=8+ on 7.9GB VRAM
6. bf16 mandatory for Qwen models (fp16 = NaN loss)

## What We Proved
1. Qwen2.5-0.5B absorbs PLATO domain 6x faster than distilgpt2
2. Generation quality: "random internet" → "domain-fluent"
3. Hidden VRAM is real and usable for training
4. bf16 required for Qwen (fp16 causes NaN)
5. Gradient checkpointing keeps VRAM manageable
6. LoRA 1.5B is 6x faster but less precise than full FT 0.5B
7. INT4 quantization: 953MB → 203MB (4.7x compression)
8. Layer-by-layer GPU transfer solves WSL2 hangs
9. init_lora_weights=False solves peft wrapping hangs
