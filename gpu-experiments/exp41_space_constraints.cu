// Experiment 41: Space Constraints — ECSS/ESA
// Spacecraft constraints: solar panel current, battery voltage, thruster temp, radiation dose
// With mission phase awareness

#include <cstdio>
#include <cuda_runtime.h>

struct SpaceBounds {
    unsigned char solar_current_lo, solar_current_hi;    // 0-30A
    unsigned char battery_voltage_lo, battery_voltage_hi; // 24-38V (28V nominal)
    unsigned char thruster_temp_lo, thruster_temp_hi;     // -40 to +200°C
    unsigned char radiation_dose_lo, radiation_dose_hi;   // 0-50 krad/yr mapped
};

__global__ void space_check(
    const SpaceBounds* bounds,
    const unsigned char* sensors,
    unsigned char* masks,
    unsigned char* phase_alert, // 0=nominal, 1=caution, 2=warning, 3=critical
    int n, int nc
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    const SpaceBounds b = bounds[0];
    const unsigned char* v = &sensors[idx * nc];
    unsigned char mask = 0;
    unsigned char alert = 0;
    
    // Solar panel: power generation critical
    if (v[0] < b.solar_current_lo) { mask |= 0x01; alert = (v[0] < b.solar_current_lo / 2) ? 3 : 2; }
    if (v[0] > b.solar_current_hi) { mask |= 0x02; alert = (alert < 1) ? 1 : alert; }
    
    // Battery: survival critical
    if (v[1] < b.battery_voltage_lo) { mask |= 0x04; alert = (alert < 3) ? 3 : alert; }
    if (v[1] > b.battery_voltage_hi) { mask |= 0x08; alert = (alert < 1) ? 1 : alert; }
    
    // Thruster temp: mission phase dependent
    if (v[2] < b.thruster_temp_lo) { mask |= 0x10; alert = (alert < 2) ? 2 : alert; }
    if (v[2] > b.thruster_temp_hi) { mask |= 0x20; alert = (v[2] > b.thruster_temp_hi + 20) ? 3 : ((alert < 2) ? 2 : alert); }
    
    // Radiation: cumulative dose
    if (v[3] > b.radiation_dose_hi) { mask |= 0x40; alert = (alert < 2) ? 2 : alert; }
    
    masks[idx] = mask;
    phase_alert[idx] = alert;
}

int main() {
    printf("=== Exp41: Spacecraft Constraints (ECSS/ESA) ===\n\n");
    
    int n = 10000000;
    int nc = 4;
    int block = 256;
    int grid = (n + block - 1) / block;
    int iters = 200;
    
    SpaceBounds h_bounds = {
        40, 220,    // solar: 0-30A (mapped)
        160, 240,   // battery: 24-38V (28V nominal, mapped)
        20, 200,    // thruster: -40 to +200°C
        0, 180      // radiation: 0-50 krad/yr
    };
    
    SpaceBounds* d_bounds;
    unsigned char* d_sensors, *d_masks, *d_alerts;
    cudaMalloc(&d_bounds, sizeof(SpaceBounds));
    cudaMalloc(&d_sensors, n * nc);
    cudaMalloc(&d_masks, n);
    cudaMalloc(&d_alerts, n);
    cudaMemcpy(d_bounds, &h_bounds, sizeof(SpaceBounds), cudaMemcpyHostToDevice);
    
    unsigned char* hv = new unsigned char[n * nc];
    for (int i = 0; i < n; i++) {
        // Solar: normally 80-180, with eclipse events
        if (i % 5000 == 0) hv[i*nc+0] = 10; // Eclipse
        else if (i % 3000 == 0) hv[i*nc+0] = 230; // Solar flare overcurrent
        else hv[i*nc+0] = 80 + (i * 7) % 105;
        
        // Battery: normally 170-210
        if (i % 8000 == 0) hv[i*nc+1] = 140; // Low voltage emergency
        else if (i % 4000 == 0) hv[i*nc+1] = 250; // Overvoltage
        else hv[i*nc+1] = 170 + (i * 11) % 45;
        
        // Thruster: normally 50-150
        if (i % 6000 == 0) hv[i*nc+2] = 220; // Overtemp
        else if (i % 12000 == 0) hv[i*nc+2] = 10; // Undertemp
        else hv[i*nc+2] = 50 + (i * 3) % 105;
        
        // Radiation: normally low, occasional spikes
        if (i % 7000 == 0) hv[i*nc+3] = 200; // SPE event
        else hv[i*nc+3] = 10 + (i * 13) % 50;
    }
    cudaMemcpy(d_sensors, hv, n*nc, cudaMemcpyHostToDevice);
    
    space_check<<<grid, block>>>(d_bounds, d_sensors, d_masks, d_alerts, n, nc);
    cudaDeviceSynchronize();
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start); cudaEventCreate(&stop);
    
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        space_check<<<grid, block>>>(d_bounds, d_sensors, d_masks, d_alerts, n, nc);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms;
    cudaEventElapsedTime(&ms, start, stop);
    
    printf("Spacecraft constraints: solar + battery + thruster + radiation\n");
    printf("ECSS alert levels: nominal, caution, warning, critical\n\n");
    printf("Throughput: %.1fB checks/sec\n", (double)n*7*iters/(ms/1000)/1e9);
    printf("Frame rate: %.0f Hz (10M sensor readings)\n", 1000.0/(ms/iters));
    
    space_check<<<grid, block>>>(d_bounds, d_sensors, d_masks, d_alerts, n, nc);
    cudaDeviceSynchronize();
    
    unsigned char* hm = new unsigned char[n];
    unsigned char* ha = new unsigned char[n];
    cudaMemcpy(hm, d_masks, n, cudaMemcpyDeviceToHost);
    cudaMemcpy(ha, d_alerts, n, cudaMemcpyDeviceToHost);
    
    int violations[7] = {};
    int alert_count[4] = {};
    for (int i = 0; i < n; i++) {
        if (hm[i] & 0x01) violations[0]++; // solar low
        if (hm[i] & 0x02) violations[1]++; // solar high
        if (hm[i] & 0x04) violations[2]++; // battery low
        if (hm[i] & 0x08) violations[3]++; // battery high
        if (hm[i] & 0x10) violations[4]++; // thruster low
        if (hm[i] & 0x20) violations[5]++; // thruster high
        if (hm[i] & 0x40) violations[6]++; // radiation
        if (ha[i] < 4) alert_count[ha[i]]++;
    }
    
    printf("\nViolation Report:\n");
    printf("  Solar low (eclipse):  %d (%.3f%%)\n", violations[0], 100.0*violations[0]/n);
    printf("  Solar high (flare):   %d (%.3f%%)\n", violations[1], 100.0*violations[1]/n);
    printf("  Battery undervolt:    %d (%.3f%%)\n", violations[2], 100.0*violations[2]/n);
    printf("  Battery overvolt:     %d (%.3f%%)\n", violations[3], 100.0*violations[3]/n);
    printf("  Thruster undertemp:   %d (%.3f%%)\n", violations[4], 100.0*violations[4]/n);
    printf("  Thruster overtemp:    %d (%.3f%%)\n", violations[5], 100.0*violations[5]/n);
    printf("  Radiation dose:       %d (%.3f%%)\n", violations[6], 100.0*violations[6]/n);
    
    printf("\nECSS Alert Distribution:\n");
    printf("  Nominal:   %d (%.2f%%)\n", alert_count[0], 100.0*alert_count[0]/n);
    printf("  Caution:   %d (%.3f%%)\n", alert_count[1], 100.0*alert_count[1]/n);
    printf("  Warning:   %d (%.3f%%)\n", alert_count[2], 100.0*alert_count[2]/n);
    printf("  Critical:  %d (%.3f%%)\n", alert_count[3], 100.0*alert_count[3]/n);
    
    printf("\n=== Spacecraft monitoring at %.0fB checks/sec ===\n",
           (double)n*7*iters/(ms/1000)/1e9);
    
    delete[] hv; delete[] hm; delete[] ha;
    return 0;
}
