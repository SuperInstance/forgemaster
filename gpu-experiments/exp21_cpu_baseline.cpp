// Experiment 21: CPU scalar baseline — for Safe-TOPS/W denominator
// We need actual CPU performance to calculate Safe-TOPS/W properly
// This gives us the CPU reference speed and validates GPU correctness

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <chrono>

struct uchar8 { unsigned char a,b,c,d,e,f,g,h; };

int main() {
    printf("=== CPU Scalar Baseline ===\n");
    printf("For Safe-TOPS/W benchmark comparison\n\n");
    
    int sizes[] = {1000, 10000, 100000, 1000000, 10000000, 50000000};
    
    for (int s = 0; s < 6; s++) {
        int n = sizes[s];
        
        uchar8 *bounds = new uchar8[n];
        int *values = new int[n];
        int *results = new int[n];
        
        // Same data pattern as GPU experiments
        for (int i = 0; i < n; i++) {
            bounds[i] = {(unsigned char)((i*7+30)%250), (unsigned char)((i*11+40)%250),
                         (unsigned char)((i*13+50)%250), (unsigned char)((i*17+60)%250),
                         (unsigned char)((i*19+70)%250), (unsigned char)((i*23+80)%250),
                         (unsigned char)((i*29+90)%250), (unsigned char)((i*31+100)%250)};
            values[i] = (i * 7 + 13) % 250;
        }
        
        int iters = 10;
        
        auto start = std::chrono::high_resolution_clock::now();
        for (int iter = 0; iter < iters; iter++) {
            for (int i = 0; i < n; i++) {
                int val = values[i];
                uchar8 b = bounds[i];
                int pass = 1;
                if (val >= b.a) pass = 0;
                else if (val >= b.b) pass = 0;
                else if (val >= b.c) pass = 0;
                else if (val >= b.d) pass = 0;
                else if (val >= b.e) pass = 0;
                else if (val >= b.f) pass = 0;
                else if (val >= b.g) pass = 0;
                else if (val >= b.h) pass = 0;
                results[i] = pass;
            }
        }
        auto end = std::chrono::high_resolution_clock::now();
        double ms = std::chrono::duration<double, std::milli>(end - start).count();
        
        double constr_per_sec = (double)n * 8 * iters / (ms / 1000.0);
        int pass_count = 0;
        for (int i = 0; i < n; i++) if (results[i]) pass_count++;
        
        printf("n=%10d | %15.0f constr/s | %7.2f ms/iter | pass: %d/%d (%.1f%%)\n",
               n, constr_per_sec, ms/iters, pass_count, n, 100.0*pass_count/n);
        
        delete[] bounds; delete[] values; delete[] results;
    }
    
    // SIMD hint
    printf("\nNote: This is scalar C++. AVX-2 would give ~4-8x, AVX-512 ~8-16x.\n");
    printf("CPU power: ~15-65W depending on load.\n");
    printf("GPU RTX 4050: 89.5B constr/s sustained at ~20-35W\n");
    
    return 0;
}
