/**
 * FLUX-C Constraint Checker VM — JavaScript wrapper
 * Loads the WASM module and provides a friendly FluxVM class.
 * Falls back to a pure-JS interpreter if WASM is unavailable.
 */

const OP = {
  HALT: 0x1a, ASSERT: 0x1b, RANGE: 0x1d,
  BOOL_AND: 0x26, BOOL_OR: 0x27, DUP: 0x28, SWAP: 0x29,
};

/* ── Pure JS fallback interpreter ── */
function jsCheck(bytecode, input) {
  const stack = [input];
  let gas = 0;
  for (let pc = 0; pc < bytecode.length; pc++) {
    if (++gas >= 0xffff) return 2;
    const op = bytecode[pc];
    switch (op) {
      case OP.HALT: return stack.pop() === 0 ? 0 : 1;
      case OP.ASSERT: { if (!stack.pop()) return 1; break; }
      case OP.RANGE: { const h=stack.pop(),l=stack.pop(),v=stack.pop(); stack.push(v>=l&&v<=h?1:0); break; }
      case OP.BOOL_AND: { const b=stack.pop(),a=stack.pop(); stack.push(a&&b?1:0); break; }
      case OP.BOOL_OR:  { const b=stack.pop(),a=stack.pop(); stack.push(a||b?1:0); break; }
      case OP.DUP:  { stack.push(stack[stack.length-1]); break; }
      case OP.SWAP: { const t=stack[stack.length-1]; stack[stack.length-1]=stack[stack.length-2]; stack[stack.length-2]=t; break; }
      default: return 3;
    }
  }
  return stack.length && stack[0] !== 0 ? 1 : 0;
}

/* ── FluxVM class ── */
class FluxVM {
  constructor() { this._wasm = null; this._mem = null; }

  async init(wasmUrl = 'flux_vm.wasm') {
    try {
      const resp = await fetch(wasmUrl);
      const { instance } = await WebAssembly.instantiate(await resp.arrayBuffer(), {});
      this._wasm = instance.exports;
      this._mem  = this._wasm.memory;
    } catch (_) {
      this._wasm = null;  // will use JS fallback
    }
    return this;
  }

  /** Check a single value. Returns 0=pass, 1=fail, 2=gas, 3=error. */
  check(value, bytecode) {
    if (!this._wasm) return jsCheck(bytecode, value);
    const mem = new Uint8Array(this._mem.buffer);
    const bcOff = 64;                           // offset for bytecode
    mem.set(bytecode, bcOff);
    return this._wasm.flux_check(bcOff, bytecode.length, value);
  }

  /** Batch-check an array of values. Returns array of result codes. */
  batch(values, bytecode, maxGas = 0xffff) {
    if (!this._wasm) return values.map(v => jsCheck(bytecode, v));

    const mem = new Uint8Array(this._mem.buffer);
    const bcOff   = 64;
    const inOff   = bcOff + bytecode.length + 4 & ~3;   // align 4
    const outOff  = inOff + values.length * 4;
    const needed  = outOff + values.length * 4;

    if (this._mem.buffer.byteLength < needed) {
      this._mem.grow(Math.ceil((needed - this._mem.buffer.byteLength) / 65536));
    }
    const mem2 = new Uint8Array(this._mem.buffer);
    mem2.set(bytecode, bcOff);
    const inArr = new Int32Array(this._mem.buffer, inOff, values.length);
    inArr.set(values);

    this._wasm.flux_batch(bcOff, bytecode.length, inOff, outOff, values.length, maxGas);

    const outArr = new Int32Array(this._mem.buffer, outOff, values.length);
    return Array.from(outArr);
  }
}

// ESM / CJS dual export
if (typeof module !== 'undefined') module.exports = { FluxVM };
else if (typeof globalThis !== 'undefined') globalThis.FluxVM = FluxVM;
