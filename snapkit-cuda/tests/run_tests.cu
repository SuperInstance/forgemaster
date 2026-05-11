/*
 * run_tests.cu — Test runner for all snapkit-cuda tests
 *
 * Runs all test suites and reports pass/fail.
 * Each test returns 0 on success, non-zero on failure.
 *
 * Usage: ./run_tests [--quick]
 */

#include <cstdio>
#include <cstdlib>
#include <ctime>

/* Test function signatures */
int test_eisenstein();
int test_batch();
int test_delta();
int test_correctness();

int main(int argc, char** argv) {
    int quick = (argc > 1 && strcmp(argv[1], "--quick") == 0);

    printf("\n");
    printf("╔══════════════════════════════════════════════╗\n");
    printf("║        snapkit-cuda TEST SUITE              ║\n");
    printf("║  GPU tolerance-compressed attention alloc   ║\n");
    printf("╚══════════════════════════════════════════════╝\n");
    printf("\n");

    /* Print CUDA device info */
    int device_id = 0;
    cudaDeviceProp prop;
    if (cudaGetDeviceProperties(&prop, device_id) == cudaSuccess) {
        printf("Device: %s (sm_%d%d)\n", prop.name, prop.major, prop.minor);
        printf("SMs: %d, Warp: %d, Mem: %.1f GB\n",
               prop.multiProcessorCount, prop.warpSize,
               (double)prop.totalGlobalMem / (1024*1024*1024));
        printf("\n");
    }

    int total_failures = 0;
    int total_tests = 0;
    int passed = 0, failed = 0;

    /* Test suites */
    struct {
        const char* name;
        int (*func)();
    } test_suites[] = {
        {"Eisenstein Snap",    test_eisenstein},
        {"Batch Snap",         test_batch},
        {"Delta Detection",    test_delta},
        {"Correctness (CPU vs GPU)", test_correctness},
    };

    int num_suites = sizeof(test_suites) / sizeof(test_suites[0]);

    for (int i = 0; i < num_suites; i++) {
        if (quick && i > 1) break;  /* Skip CPU vs GPU in quick mode */

        printf("─── Test Suite: %s ───\n", test_suites[i].name);
        int result = test_suites[i].func();
        total_failures += result;

        if (result == 0) {
            passed++;
        } else {
            failed++;
        }
        total_tests++;
        printf("\n");
    }

    printf("╔══════════════════════════════════════════════╗\n");
    printf("║  RESULTS: %d/%d suites passed, %d failures    ║\n",
           passed, total_tests, total_failures);
    printf("╚══════════════════════════════════════════════╝\n");
    printf("\n");

    return total_failures > 0 ? 1 : 0;
}
