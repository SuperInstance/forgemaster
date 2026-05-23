// Experiment 39: Nuclear Constraints — DO-178C Analog for NRC 10 CFR 50
// Uses actual nuclear reactor safety bounds from the constraint library
// This is the highest-stakes domain: reactor coolant, containment, radiation

#include <cstdio>
#include <cuda_runtime.h>

// Nuclear reactor constraints (INT8 mapped from NRC technical specs)
// PWR (Pressurized Water Reactor) typical bounds
struct NuclearBounds {
    unsigned char coolant_temp_lo, coolant_temp_hi;       // 540-620°F
    unsigned char coolant_pressure_lo, coolant_pressure_hi; // 2000-2300 psig
    unsigned char containment_temp_lo, containment_temp_hi; // 70-280°F
    unsigned char radiation_mrem_lo, radiation_mrem_hi;     // 0-100 mrem/hr
};

__global__ void nuclear_check(
    const NuclearBounds* bounds,
    const unsigned char* sensors,
    unsigned char* masks,
    unsigned char* severity,   // 0=ok, 1=warning, 2=critical, 3=emergency
    int n, int nc
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    const NuclearBounds b = bounds[0];
    const unsigned char* v = &sensors[idx * nc];
    unsigned char mask = 0;
    unsigned char sev = 0;
    
    // Coolant temperature: most critical
    if (v[0] > b.coolant_temp_hi) { mask |= 0x01; sev = (v[0] > b.coolant_temp_hi + 20) ? 3 : 2; }
    if (v[0] < b.coolant_temp_lo) { mask |= 0x02; sev = (sev < 2) ? 2 : sev; }
    
    // Coolant pressure: critical
    if (v[1] > b.coolant_pressure_hi) { mask |= 0x04; sev = (v[1] > b.coolant_pressure_hi + 10) ? 3 : (sev < 2 ? 2 : sev); }
    if (v[1] < b.coolant_pressure_lo) { mask |= 0x08; sev = (sev < 1) ? 1 : sev; }
    
    // Containment temperature: warning level
    if (v[2] > b.containment_temp_hi) { mask |= 0x10; sev = (sev < 1) ? 1 : sev; }
    
    // Radiation: escalating severity
    if (v[3] > b.radiation_mrem_hi) { mask |= 0x20; sev = (v[3] > 200) ? 3 : (sev < 2 ? 2 : sev); }
    
    masks[idx] = mask;
    severity[idx] = sev;
}

int main() {
    printf("=== Exp39: Nuclear Reactor Constraints (NRC 10 CFR 50) ===\n\n");
    
    int n = 10000000;
    int nc = 4;
    int block = 256;
    int grid = (n + block - 1) / block;
    int iters = 200;
    
    // PWR bounds (INT8 mapped)
    // Coolant temp: 540-620°F → INT8 range
    // Coolant pressure: 2000-2300 psig → INT8 range
    // Containment temp: 70-280°F → INT8 range
    // Radiation: 0-100 mrem/hr normal, up to 500 emergency
    NuclearBounds h_bounds = {
        120, 210,   // coolant temp: normal 540-620°F mapped
        180, 230,   // coolant pressure: 2000-2300 psig mapped
        30, 200,    // containment temp: 70-280°F mapped
        0, 50       // radiation: 0-100 mrem/hr mapped
    };
    
    NuclearBounds* d_bounds;
    unsigned char* d_sensors;
    unsigned char* d_masks;
    unsigned char* d_severity;
    cudaMalloc(&d_bounds, sizeof(NuclearBounds));
    cudaMalloc(&d_sensors, n * nc);
    cudaMalloc(&d_masks, n);
    cudaMalloc(&d_severity, n);
    cudaMemcpy(d_bounds, &h_bounds, sizeof(NuclearBounds), cudaMemcpyHostToDevice);
    
    // Generate realistic nuclear sensor data
    unsigned char* hv = new unsigned char[n * nc];
    for (int i = 0; i < n; i++) {
        // Coolant temp: normally 160-190, with rare excursions
        if (i % 5000 == 0) hv[i*nc+0] = 220; // Overtemp emergency
        else if (i % 2000 == 0) hv[i*nc+0] = 215; // Overtemp warning
        else if (i % 10000 == 0) hv[i*nc+0] = 100; // Undertemp
        else hv[i*nc+0] = 150 + (i * 7) % 50;
        
        // Coolant pressure: normally 195-215
        if (i % 3000 == 0) hv[i*nc+1] = 240; // Overpressure
        else if (i % 8000 == 0) hv[i*nc+1] = 160; // Underpressure
        else hv[i*nc+1] = 195 + (i * 11) % 25;
        
        // Containment temp: normally 40-80
        if (i % 7000 == 0) hv[i*nc+2] = 210; // Containment breach
        else hv[i*nc+2] = 40 + (i * 3) % 45;
        
        // Radiation: normally 5-30
        if (i % 10000 == 0) hv[i*nc+3] = 180; // Radiation emergency
        else if (i % 5000 == 0) hv[i*nc+3] = 80; // High radiation
        else hv[i*nc+3] = 5 + (i * 13) % 30;
    }
    cudaMemcpy(d_sensors, hv, n*nc, cudaMemcpyHostToDevice);
    
    // Warmup
    nuclear_check<<<grid, block>>>(d_bounds, d_sensors, d_masks, d_severity, n, nc);
    cudaDeviceSynchronize();
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start); cudaEventCreate(&stop);
    
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        nuclear_check<<<grid, block>>>(d_bounds, d_sensors, d_masks, d_severity, n, nc);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms;
    cudaEventElapsedTime(&ms, start, stop);
    
    printf("PWR Reactor constraints: 4 sensors × 6 checks per time step\n");
    printf("  Coolant temp (540-620°F), Coolant pressure (2000-2300 psig)\n");
    printf("  Containment temp (70-280°F), Radiation (0-100 mrem/hr)\n\n");
    printf("Throughput: %.1fB checks/sec\n", (double)n*6*iters/(ms/1000)/1e9);
    printf("Frame rate: %.0f Hz (10M sensor readings)\n", 1000.0/(ms/iters));
    
    // Count violations and severity
    nuclear_check<<<grid, block>>>(d_bounds, d_sensors, d_masks, d_severity, n, nc);
    cudaDeviceSynchronize();
    
    unsigned char* hm = new unsigned char[n];
    unsigned char* hs = new unsigned char[n];
    cudaMemcpy(hm, d_masks, n, cudaMemcpyDeviceToHost);
    cudaMemcpy(hs, d_severity, n, cudaMemcpyDeviceToHost);
    
    int violations[6] = {};
    int sev_count[4] = {}; // ok, warning, critical, emergency
    for (int i = 0; i < n; i++) {
        if (hm[i] & 0x01) violations[0]++; // coolant overtemp
        if (hm[i] & 0x02) violations[1]++; // coolant undertemp
        if (hm[i] & 0x04) violations[2]++; // overpressure
        if (hm[i] & 0x08) violations[3]++; // underpressure
        if (hm[i] & 0x10) violations[4]++; // containment
        if (hm[i] & 0x20) violations[5]++; // radiation
        sev_count[hs[i]]++;
    }
    
    printf("\nViolation Report:\n");
    printf("  Coolant overtemp:     %d (%.3f%%)\n", violations[0], 100.0*violations[0]/n);
    printf("  Coolant undertemp:    %d (%.3f%%)\n", violations[1], 100.0*violations[1]/n);
    printf("  Coolant overpressure: %d (%.3f%%)\n", violations[2], 100.0*violations[2]/n);
    printf("  Coolant underpress:   %d (%.3f%%)\n", violations[3], 100.0*violations[3]/n);
    printf("  Containment:          %d (%.3f%%)\n", violations[4], 100.0*violations[4]/n);
    printf("  Radiation:            %d (%.3f%%)\n", violations[5], 100.0*violations[5]/n);
    
    printf("\nSeverity Distribution:\n");
    printf("  OK:       %d (%.2f%%)\n", sev_count[0], 100.0*sev_count[0]/n);
    printf("  Warning:  %d (%.2f%%)\n", sev_count[1], 100.0*sev_count[1]/n);
    printf("  Critical: %d (%.2f%%)\n", sev_count[2], 100.0*sev_count[2]/n);
    printf("  Emergency: %d (%.2f%%)\n", sev_count[3], 100.0*sev_count[3]/n);
    
    printf("\n=== Nuclear reactor monitoring at %.0fB checks/sec ===\n",
           (double)n*6*iters/(ms/1000)/1e9);
    
    delete[] hv; delete[] hm; delete[] hs;
    return 0;
}
