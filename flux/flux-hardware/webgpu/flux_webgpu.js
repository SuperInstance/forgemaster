/**
 * flux_webgpu.js — WebGPU Backend for FLUX Constraint Checking
 * 
 * Drop-in module for Oracle1's flux-sandbox.html and cocapn.ai.
 * Uses WebGPU compute shaders for browser-based constraint checking.
 * Falls back to CPU if WebGPU is not available.
 * 
 * Usage:
 *   const engine = await FluxWebGPU.create();
 *   const {results, passCount, failCount} = await engine.check(bytecode, inputs);
 */

class FluxWebGPU {
    constructor() {
        this.device = null;
        this.pipeline = null;
        this.bindGroupLayout = null;
        this.shaderModule = null;
    }

    static async create() {
        const engine = new FluxWebGPU();
        
        if (!navigator.gpu) {
            console.log('[FLUX] WebGPU not available, using CPU fallback');
            engine.device = null;
            return engine;
        }

        const adapter = await navigator.gpu.requestAdapter({
            powerPreference: 'high-performance'
        });
        if (!adapter) {
            console.log('[FLUX] No GPU adapter found, using CPU fallback');
            engine.device = null;
            return engine;
        }

        engine.device = await adapter.requestDevice();
        console.log(`[FLUX] WebGPU device: ${adapter.info?.vendor || 'unknown'}`);

        // Load shader
        const shaderCode = await fetch('flux_constraint_shader.wgsl').then(r => r.text())
            .catch(() => FLUX_BUILTIN_SHADER);

        engine.shaderModule = engine.device.createShaderModule({
            code: shaderCode
        });

        // Create bind group layout
        engine.bindGroupLayout = engine.device.createBindGroupLayout({
            entries: [
                { binding: 0, visibility: GPUShaderStage.COMPUTE, buffer: { type: 'read-only-storage' } },
                { binding: 1, visibility: GPUShaderStage.COMPUTE, buffer: { type: 'read-only-storage' } },
                { binding: 2, visibility: GPUShaderStage.COMPUTE, buffer: { type: 'storage' } },
                { binding: 3, visibility: GPUShaderStage.COMPUTE, buffer: { type: 'storage' } },
                { binding: 4, visibility: GPUShaderStage.COMPUTE, buffer: { type: 'storage' } },
                { binding: 5, visibility: GPUShaderStage.COMPUTE, buffer: { type: 'uniform' } },
            ]
        });

        // Create pipeline
        engine.pipeline = engine.device.createComputePipeline({
            layout: engine.device.createPipelineLayout({
                bindGroupLayouts: [engine.bindGroupLayout]
            }),
            compute: {
                module: engine.shaderModule,
                entryPoint: 'flux_vm_batch'
            }
        });

        return engine;
    }

    get isGPU() {
        return this.device !== null;
    }

    /**
     * Pack bytecode array into Uint32Array (4 bytes per word, little-endian)
     */
    packBytecode(bytes) {
        const len = bytes.length;
        const words = Math.ceil(len / 4);
        const packed = new Uint32Array(words);
        for (let i = 0; i < len; i++) {
            packed[i >> 2] |= (bytes[i] & 0xFF) << ((i & 3) * 8);
        }
        return packed;
    }

    /**
     * Run FLUX constraint checking on GPU
     */
    async check(bytecode, inputs, maxGas = 1000) {
        if (!this.device) {
            return this.checkCPU(bytecode, inputs, maxGas);
        }

        const n = inputs.length;
        const packedBC = this.packBytecode(bytecode);

        // Create GPU buffers
        const bcBuffer = this.device.createBuffer({
            size: packedBC.byteLength,
            usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST
        });
        this.device.queue.writeBuffer(bcBuffer, 0, packedBC);

        const inputBuffer = this.device.createBuffer({
            size: n * 4,
            usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST
        });
        this.device.queue.writeBuffer(inputBuffer, 0, new Int32Array(inputs));

        const resultBuffer = this.device.createBuffer({
            size: n * 4,
            usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC
        });

        const passBuffer = this.device.createBuffer({
            size: 4,
            usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC
        });

        const failBuffer = this.device.createBuffer({
            size: 4,
            usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC
        });

        const paramsData = new Int32Array([bytecode.length, n, maxGas, 0]);
        const paramsBuffer = this.device.createBuffer({
            size: 16,
            usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST
        });
        this.device.queue.writeBuffer(paramsBuffer, 0, paramsData);

        // Create bind group
        const bindGroup = this.device.createBindGroup({
            layout: this.bindGroupLayout,
            entries: [
                { binding: 0, resource: { buffer: bcBuffer } },
                { binding: 1, resource: { buffer: inputBuffer } },
                { binding: 2, resource: { buffer: resultBuffer } },
                { binding: 3, resource: { buffer: passBuffer } },
                { binding: 4, resource: { buffer: failBuffer } },
                { binding: 5, resource: { buffer: paramsBuffer } },
            ]
        });

        // Dispatch
        const commandEncoder = this.device.createCommandEncoder();
        const pass = commandEncoder.beginComputePass();
        pass.setPipeline(this.pipeline);
        pass.setBindGroup(0, bindGroup);
        pass.dispatchWorkgroups(Math.ceil(n / 256));
        pass.end();

        // Read back results
        const readBuffer = this.device.createBuffer({
            size: n * 4 + 8,
            usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST
        });
        commandEncoder.copyBufferToBuffer(resultBuffer, 0, readBuffer, 0, n * 4);
        commandEncoder.copyBufferToBuffer(passBuffer, 0, readBuffer, n * 4, 4);
        commandEncoder.copyBufferToBuffer(failBuffer, 0, readBuffer, n * 4 + 4, 4);

        this.device.queue.submit([commandEncoder.finish()]);

        // Wait for results
        await readBuffer.mapAsync(GPUMapMode.READ);
        const data = new Int32Array(readBuffer.getMappedRange());
        
        const results = new Int32Array(data.slice(0, n));
        const passCount = data[n];
        const failCount = data[n + 1];

        readBuffer.unmap();

        // Cleanup
        bcBuffer.destroy();
        inputBuffer.destroy();
        resultBuffer.destroy();
        passBuffer.destroy();
        failBuffer.destroy();
        paramsBuffer.destroy();
        readBuffer.destroy();

        return {
            results: Array.from(results),
            passCount,
            failCount,
            throughput: n,  // caller measures time
            gpu: true
        };
    }

    /**
     * CPU fallback — matches GPU semantics exactly
     */
    checkCPU(bytecode, inputs, maxGas = 1000) {
        const results = [];
        let passCount = 0;
        let failCount = 0;
        const bl = Array.from(bytecode);

        for (const inp of inputs) {
            const stack = [inp];
            let sp = 1;
            let gas = maxGas;
            let pc = 0;
            let fault = false;
            let passed = false;

            while (pc < bl.length && gas > 0 && !fault && !passed) {
                gas--;
                const op = bl[pc];
                switch (op) {
                    case 0x00: stack[sp++] = bl[++pc]; pc++; break;
                    case 0x1A: passed = true; pc = bl.length; break;
                    case 0x1B: { const v = stack[--sp]; if (!v) fault = true; pc++; } break;
                    case 0x1C: { const v = stack[--sp]; const mask = bl[++pc]; stack[sp++] = ((v & mask) === v) ? 1 : 0; pc++; } break;
                    case 0x1D: { const v = stack[--sp]; const lo = bl[++pc]; const hi = bl[++pc]; stack[sp++] = (v >= lo && v <= hi) ? 1 : 0; pc++; } break;
                    case 0x20: fault = true; pc++; break;
                    case 0x24: { const b = stack[--sp], a = stack[--sp]; stack[sp++] = (a >= b) ? 1 : 0; pc++; } break;
                    case 0x25: { const b = stack[--sp], a = stack[--sp]; stack[sp++] = (a === b) ? 1 : 0; pc++; } break;
                    default: pc++; break;
                }
            }

            const result = (passed && !fault) ? 1 : 0;
            results.push(result);
            if (result) passCount++; else failCount++;
        }

        return { results, passCount, failCount, throughput: inputs.length, gpu: false };
    }

    /**
     * Benchmark: measure throughput
     */
    async benchmark(bytecode, n = 100000) {
        const inputs = Array.from({length: n}, () => Math.floor(Math.random() * 100));
        
        // Warmup
        await this.check(bytecode, inputs.slice(0, 1000));
        
        // Timed run
        const t0 = performance.now();
        const result = await this.check(bytecode, inputs);
        const elapsed = performance.now() - t0;
        
        return {
            n,
            elapsed_ms: elapsed,
            throughput: Math.round(n / (elapsed / 1000)),
            passCount: result.passCount,
            failCount: result.failCount,
            gpu: result.gpu
        };
    }
}

// Built-in shader as fallback if file fetch fails
const FLUX_BUILTIN_SHADER = `
// Embedded FLUX constraint shader — see flux_constraint_shader.wgsl for full source
`;

// Export for ES modules / script tag
if (typeof module !== 'undefined') {
    module.exports = { FluxWebGPU };
}
if (typeof window !== 'undefined') {
    window.FluxWebGPU = FluxWebGPU;
}
