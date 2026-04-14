#include <stdio.h>
#include <math.h>

__device__ int count_matches(int c1, int c2, int c3, int c4, int c5) {
    int matches = 0;
    if (c1 == c2) matches++;
    if (c1 == c3) matches++;
    if (c1 == c4) matches++;
    if (c1 == c5) matches++;
    if (c2 == c3) matches++;
    if (c2 == c4) matches++;
    if (c2 == c5) matches++;
    if (c3 == c4) matches++;
    if (c3 == c5) matches++;
    if (c4 == c5) matches++;
    return matches;
}

__global__ void test_convergence_constants() {
    int total_matches = 0;
    for (int c1 = 1; c1 <= 5; c1++) {
        for (int c2 = 1; c2 <= 5; c2++) {
            for (int c3 = 1; c3 <= 5; c3++) {
                for (int c4 = 1; c4 <= 5; c4++) {
                    for (int c5 = 1; c5 <= 5; c5++) {
                        total_matches += count_matches(c1, c2, c3, c4, c5);
                    }
                }
            }
        }
    }
    printf("Total matches: %d\n", total_matches);
    printf("SUMMARY: Total matches found: %d\n", total_matches);
}

int main() {
    test_convergence_constants<<<1, 1>>> ();
    cudaDeviceSynchronize();
    return 0;
}