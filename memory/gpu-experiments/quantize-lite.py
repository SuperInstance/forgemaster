"""Lightweight INT8 quant — save state dict directly, measure size, done."""

import os, json, torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_PATH = "/tmp/gpu-exp7/best-model"
OUT = "/tmp/gpu-exp7/quantized"
os.makedirs(OUT, exist_ok=True)

print("Loading tokenizer...")
tok = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True, trust_remote_code=True)
tok.save_pretrained(OUT)

print("Loading model (float32 on CPU)...")
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, local_files_only=True, torch_dtype=torch.float32, trust_remote_code=True).cpu()
model.eval()

fp32_size = sum(p.numel() * p.element_size() for p in model.parameters())
print(f"FP32: {fp32_size/1e6:.0f}MB")

# Save FP32 safetensors for reference
model.save_pretrained(f"{OUT}/fp32")
fp32_disk = sum(os.path.getsize(f"{OUT}/fp32/{f}") for f in os.listdir(f"{OUT}/fp32") if f.endswith(('.safetensors','.bin')))
print(f"FP32 disk: {fp32_disk/1e6:.0f}MB")

# INT8 dynamic quantization
print("\nINT8 dynamic quantization...")
import torch.ao.quantization as quant
model_int8 = quant.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
int8_size = sum(p.numel() * p.element_size() for p in model_int8.parameters())
print(f"INT8 params: {int8_size/1e6:.0f}MB ({fp32_size/int8_size:.1f}x compression)")

# Save INT8 state dict
torch.save(model_int8.state_dict(), f"{OUT}/plato-neural-int8.pt")
int8_disk = os.path.getsize(f"{OUT}/plato-neural-int8.pt")
print(f"INT8 disk: {int8_disk/1e6:.0f}MB")

# Also save as safetensors (smaller)
try:
    from safetensors.torch import save_file
    state = model_int8.state_dict()
    # Filter to only quantized weight tensors
    save_file(state, f"{OUT}/plato-neural-int8.safetensors")
    st_disk = os.path.getsize(f"{OUT}/plato-neural-int8.safetensors")
    print(f"INT8 safetensors: {st_disk/1e6:.0f}MB")
except Exception as e:
    print(f"safetensors save: {e}")
    st_disk = int8_disk

# Quick generation test on INT8 (CPU)
print("\nINT8 generation test (CPU)...")
model_int8.eval()
import time
prompt = "Q: What is constraint theory?\nA:"
inputs = tok(prompt, return_tensors="pt", truncation=True, max_length=256)
t0 = time.time()
with torch.no_grad():
    out = model_int8.generate(**inputs, max_new_tokens=60, do_sample=False, pad_token_id=tok.eos_token_id)
ans = tok.decode(out[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True).strip()
elapsed = time.time() - t0
print(f"  [{elapsed:.1f}s] {ans}")

# Perplexity on 20 tiles (CPU, slow but feasible)
print("\nINT8 perplexity (20 tiles)...")
with open('/tmp/plato-corpus-latest.json') as f:
    tiles = json.load(f)
import random
random.seed(42)
sample = random.sample(tiles, 20)
ppls = []
for tile in sample:
    q, a = tile.get('question',''), tile.get('answer','')
    if not q or not a: continue
    inputs = tok(f"Q: {q}\nA: {a}", return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        loss = model_int8(**inputs, labels=inputs['input_ids']).loss.item()
    ppls.append(torch.exp(torch.tensor(loss)).item())

avg_ppl = sum(ppls)/len(ppls)
med_ppl = sorted(ppls)[len(ppls)//2]
print(f"INT8 Avg PPL (20 tiles): {avg_ppl:.1f}")
print(f"INT8 Median PPL: {med_ppl:.1f}")

results = {
    "fp32_size_mb": round(fp32_size/1e6),
    "int8_params_mb": round(int8_size/1e6),
    "int8_disk_mb": round(int8_disk/1e6),
    "int8_st_mb": round(st_disk/1e6),
    "compression": round(fp32_size/int8_size, 1),
    "int8_avg_ppl_20": round(avg_ppl, 1),
    "int8_median_ppl_20": round(med_ppl, 1),
    "fits_nano": int8_disk < 4e9,
    "fits_orin": int8_disk < 8e9,
}
with open('/tmp/gpu-exp7/quant-results.json', 'w') as f:
    json.dump(results, f, indent=2)
print(f"\n{json.dumps(results, indent=2)}")

del model, model_int8
import gc; gc.collect()
print("Done.")
