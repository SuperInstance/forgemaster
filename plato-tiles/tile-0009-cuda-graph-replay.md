# CUDA Graph Replay Performance

**Core Concept:** CUDA Graphs capture a sequence of kernel launches and memory operations as a single unit, enabling replay with reduced CPU overhead and improved GPU utilization—critical for real-time sensor fusion pipelines.

**Traditional Stream Launch Overhead:**
- Each kernel launch: ~5-10 µs CPU overhead
- Memory copy operations: additional overhead
- Launch latency scales with operation count
- Pipeline with 30 operations: ~150-300 µs overhead

**CUDA Graph Benefits:**
- **Single Launch:** Entire graph launches in ~30 µs total
- **Pre-recorded Operations:** No per-op validation during replay
- **Batch Optimization:** Driver can reorder/merge operations
- **Reduced CPU-GPU Sync:** Fewer context switches

**Graph Creation Workflow:**
```cpp
cudaGraph_t graph;
cudaGraphExec_t graphExec;

// Begin capture
cudaStreamBeginCapture(stream, cudaStreamCaptureModeGlobal);

// Record operations (kernel launches, memcopies, etc.)
kernel1<<<grid, block, 0, stream>>>(args1);
cudaMemcpyAsync(dst, src, size, cudaMemcpyDeviceToDevice, stream);
kernel2<<<grid, block, 0, stream>>>(args2);

// End capture
cudaStreamEndCapture(stream, &graph);

// Instantiate executable graph
cudaGraphInstantiate(&graphExec, graph, NULL, NULL, 0);

// Replay (can be called repeatedly)
cudaGraphLaunch(graphExec, stream);
```

**Performance Results (Marine GPU Edge Pipeline):**

| Metric | Stream Launches | CUDA Graph | Speedup |
|--------|----------------|------------|---------|
| Total Time | 30.8 ms | 17.9 ms | **1.73x** |
| CPU Overhead | ~250 µs | ~30 µs | 8.3x |
| GPU Utilization | ~85% | ~96% | 1.13x |

**Pipeline Composition (30 operations):**
1. NMEA parse kernel (10 operations for concurrent streams)
2. Kalman prediction
3. Kalman measurement update
4. Sonar TVG compute
5. Sonar dB conversion
6. Constraint propagation
7. Result aggregation
8. Memory copies (host ↔ device)

**Dynamic Parameter Handling:**
CUDA Graphs require fixed structure, but support runtime parameters:
- **Kernel Arguments:** Use `cudaGraphExecKernelNodeSetParams()`
- **Memory Pointers:** Update via `cudaGraphExecMemcpyNodeSetParams()`
- **Graph Update API:** Allows selective node parameter updates

**Limitations:**
- **Static Structure:** Cannot add/remove nodes after instantiation
- **Memory Dependencies:** Fixed allocation requirements
- **Conditional Branches:** Not supported within graph (use multiple graphs)

**Marine Edge Application:**
- **Fixed Sensor Configuration:** Same sensors every boot
- **Repeating Pipeline:** 324 Hz loop execution
- **Predictable Workload:** No dynamic task addition
- **Perfect Fit:** CUDA Graph replay ideal

**Constraint Theory Connection:**
The pipeline itself is a constraint satisfaction process—each stage has input/output constraints, temporal deadlines, and precision requirements. CUDA Graph ensures these constraints are met with minimal overhead.

**Provenance:** Forgemaster (GPU optimization experiments)
**Chain:** marine-pipeline target, RTX 4050 benchmarks
