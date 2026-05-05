// Experiment 40: Automotive Constraints — ISO 26262 ASIL-D
// Real automotive safety bounds: brake pressure, steering angle, speed, battery temp
// With ASIL severity levels (QM, A, B, C, D)

#include <cstdio>
#include <cuda_runtime.h>

struct AutoBounds {
    unsigned char speed_lo, speed_hi;           // 0-250 km/h
    unsigned char brake_pressure_lo, brake_pressure_hi; // 0-200 bar
    unsigned char steering_angle_lo, steering_angle_hi; // -540 to +540 deg
    unsigned char battery_temp_lo, battery_temp_hi;      // -20 to +60 °C
};

__global__ void auto_check(
    const AutoBounds* bounds,
    const unsigned char* sensors,
    unsigned char* masks,
    unsigned char* asil,    // ASIL level: 0=QM, 1=A, 2=B, 3=C, 4=D
    int n, int nc
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx >= n) return;
    
    const AutoBounds b = bounds[0];
    const unsigned char* v = &sensors[idx * nc];
    unsigned char mask = 0;
    unsigned char level = 0;
    
    // Speed: ASIL-B for overlimit, ASIL-D for extreme
    if (v[0] > b.speed_hi) {
        mask |= 0x01;
        level = (v[0] > b.speed_hi + 30) ? 4 : 2; // D for extreme, B for over
    }
    
    // Brake pressure: ASIL-D (safety-critical)
    if (v[1] < b.brake_pressure_lo) { mask |= 0x02; level = (level < 4) ? 4 : level; }
    if (v[1] > b.brake_pressure_hi) { mask |= 0x04; level = (level < 3) ? 3 : level; }
    
    // Steering angle: ASIL-D
    if (v[2] < b.steering_angle_lo || v[2] > b.steering_angle_hi) {
        mask |= 0x08;
        level = (level < 4) ? 4 : level;
    }
    
    // Battery temp: ASIL-B
    if (v[3] < b.battery_temp_lo) { mask |= 0x10; level = (level < 2) ? 2 : level; }
    if (v[3] > b.battery_temp_hi) { mask |= 0x20; level = (level < 2) ? 2 : level; }
    
    masks[idx] = mask;
    asil[idx] = level;
}

int main() {
    printf("=== Exp40: Automotive Constraints (ISO 26262 ASIL-D) ===\n\n");
    
    int n = 10000000;
    int nc = 4;
    int block = 256;
    int grid = (n + block - 1) / block;
    int iters = 200;
    
    AutoBounds h_bounds = {
        0, 230,    // speed: 0-250 km/h
        20, 200,   // brake: min 20 bar (pedal applied), max 200 bar
        30, 225,   // steering: -540 to +540 deg mapped
        40, 200    // battery: -20 to +60 °C mapped
    };
    
    AutoBounds* d_bounds;
    unsigned char* d_sensors, *d_masks, *d_asil;
    cudaMalloc(&d_bounds, sizeof(AutoBounds));
    cudaMalloc(&d_sensors, n * nc);
    cudaMalloc(&d_masks, n);
    cudaMalloc(&d_asil, n);
    cudaMemcpy(d_bounds, &h_bounds, sizeof(AutoBounds), cudaMemcpyHostToDevice);
    
    unsigned char* hv = new unsigned char[n * nc];
    for (int i = 0; i < n; i++) {
        // Speed: normally 60-180, with overspeed injection
        if (i % 3000 == 0) hv[i*nc+0] = 240; // Extreme overspeed
        else if (i % 1500 == 0) hv[i*nc+0] = 235; // Overspeed
        else hv[i*nc+0] = 60 + (i * 7) % 130;
        
        // Brake: normally 40-120, with low pressure injection
        if (i % 5000 == 0) hv[i*nc+1] = 10; // Brake failure
        else if (i % 2000 == 0) hv[i*nc+1] = 210; // Overpressure
        else hv[i*nc+1] = 40 + (i * 11) % 85;
        
        // Steering: normally centered (100-160)
        if (i % 8000 == 0) hv[i*nc+2] = 20; // Full lock anomaly
        else if (i % 4000 == 0) hv[i*nc+2] = 240; // Full lock other way
        else hv[i*nc+2] = 100 + (i * 3) % 60;
        
        // Battery: normally 80-160
        if (i % 10000 == 0) hv[i*nc+3] = 210; // Overtemp
        else if (i % 6000 == 0) hv[i*nc+3] = 30; // Undertemp
        else hv[i*nc+3] = 80 + (i * 13) % 85;
    }
    cudaMemcpy(d_sensors, hv, n*nc, cudaMemcpyHostToDevice);
    
    auto_check<<<grid, block>>>(d_bounds, d_sensors, d_masks, d_asil, n, nc);
    cudaDeviceSynchronize();
    
    cudaEvent_t start, stop;
    cudaEventCreate(&start); cudaEventCreate(&stop);
    
    cudaEventRecord(start);
    for (int i = 0; i < iters; i++)
        auto_check<<<grid, block>>>(d_bounds, d_sensors, d_masks, d_asil, n, nc);
    cudaEventRecord(stop); cudaEventSynchronize(stop);
    float ms;
    cudaEventElapsedTime(&ms, start, stop);
    
    printf("Automotive constraints: speed + brake + steering + battery\n");
    printf("ISO 26262 ASIL levels: QM, A, B, C, D\n\n");
    printf("Throughput: %.1fB checks/sec\n", (double)n*6*iters/(ms/1000)/1e9);
    printf("Frame rate: %.0f Hz (10M sensors)\n", 1000.0/(ms/iters));
    
    // Violation report
    auto_check<<<grid, block>>>(d_bounds, d_sensors, d_masks, d_asil, n, nc);
    cudaDeviceSynchronize();
    
    unsigned char* hm = new unsigned char[n];
    unsigned char* ha = new unsigned char[n];
    cudaMemcpy(hm, d_masks, n, cudaMemcpyDeviceToHost);
    cudaMemcpy(ha, d_asil, n, cudaMemcpyDeviceToHost);
    
    int violations[6] = {};
    int asil_count[5] = {};
    for (int i = 0; i < n; i++) {
        if (hm[i] & 0x01) violations[0]++; // overspeed
        if (hm[i] & 0x02) violations[1]++; // brake low
        if (hm[i] & 0x04) violations[2]++; // brake high
        if (hm[i] & 0x08) violations[3]++; // steering
        if (hm[i] & 0x10) violations[4]++; // battery undertemp
        if (hm[i] & 0x20) violations[5]++; // battery overtemp
        if (ha[i] < 5) asil_count[ha[i]]++;
    }
    
    printf("\nViolation Report:\n");
    printf("  Overspeed:        %d (%.3f%%)\n", violations[0], 100.0*violations[0]/n);
    printf("  Brake low press:  %d (%.3f%%)\n", violations[1], 100.0*violations[1]/n);
    printf("  Brake high press: %d (%.3f%%)\n", violations[2], 100.0*violations[2]/n);
    printf("  Steering anomaly: %d (%.3f%%)\n", violations[3], 100.0*violations[3]/n);
    printf("  Battery undertemp:%d (%.3f%%)\n", violations[4], 100.0*violations[4]/n);
    printf("  Battery overtemp: %d (%.3f%%)\n", violations[5], 100.0*violations[5]/n);
    
    printf("\nASIL Severity Distribution:\n");
    printf("  QM (no issue):    %d (%.2f%%)\n", asil_count[0], 100.0*asil_count[0]/n);
    printf("  ASIL-A:           %d (%.2f%%)\n", asil_count[1], 100.0*asil_count[1]/n);
    printf("  ASIL-B:           %d (%.2f%%)\n", asil_count[2], 100.0*asil_count[2]/n);
    printf("  ASIL-C:           %d (%.2f%%)\n", asil_count[3], 100.0*asil_count[3]/n);
    printf("  ASIL-D:           %d (%.2f%%)\n", asil_count[4], 100.0*asil_count[4]/n);
    
    printf("\n=== Automotive safety at %.0fB checks/sec with ASIL classification ===\n",
           (double)n*6*iters/(ms/1000)/1e9);
    
    delete[] hv; delete[] hm; delete[] ha;
    return 0;
}
