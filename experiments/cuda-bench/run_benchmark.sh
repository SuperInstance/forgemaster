#!/bin/bash
#
# run_benchmark.sh — Build and benchmark CUDA constraint checking kernels
#
# Checks for CUDA GPU via nvidia-smi. If found, runs full GPU benchmark.
# If not found, runs CPU reference tests only.
#
# Usage: ./run_benchmark.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RESULTS_FILE="results.txt"
BUILD_LOG="build.log"

echo "==============================================================" | tee "$RESULTS_FILE"
echo "  CUDA Constraint Kernel Benchmark" | tee -a "$RESULTS_FILE"
echo "  Date: $(date)" | tee -a "$RESULTS_FILE"
echo "  Host: $(hostname)" | tee -a "$RESULTS_FILE"
echo "==============================================================" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

# --- Check for nvcc ---
if command -v nvcc &> /dev/null; then
    NVCC_VERSION=$(nvcc --version | grep "release" | awk '{print $6}')
    echo "nvcc found: $NVCC_VERSION" | tee -a "$RESULTS_FILE"
else
    echo "ERROR: nvcc not found. Install CUDA toolkit." | tee -a "$RESULTS_FILE"
    exit 1
fi

echo "" | tee -a "$RESULTS_FILE"

# --- Build fat binary for multiple architectures ---
echo "Building fat binary (sm_70, sm_75, sm_80, sm_86)..." | tee -a "$RESULTS_FILE"
echo "Build log: $BUILD_LOG" | tee -a "$RESULTS_FILE"

nvcc -O3 \
    -gencode arch=compute_70,code=sm_70 \
    -gencode arch=compute_75,code=sm_75 \
    -gencode arch=compute_80,code=sm_80 \
    -gencode arch=compute_86,code=sm_86 \
    -std=c++14 \
    constraint_cuda.cu reference.cpp \
    -o constraint_cuda \
    2>&1 | tee "$BUILD_LOG"

BUILD_STATUS=${PIPESTATUS[0]}
if [ $BUILD_STATUS -ne 0 ]; then
    echo "BUILD FAILED (exit code $BUILD_STATUS)" | tee -a "$RESULTS_FILE"
    echo "See build.log for details." | tee -a "$RESULTS_FILE"
    exit $BUILD_STATUS
fi

echo "Build OK" | tee -a "$RESULTS_FILE"

# Also build single-architecture version for this machine
echo "" | tee -a "$RESULTS_FILE"
echo "Building sm_86-only binary..." | tee -a "$RESULTS_FILE"
nvcc -O3 -arch=sm_86 -std=c++14 constraint_cuda.cu reference.cpp -o constraint_cuda_sm86 \
    2>&1 | tee -a "$BUILD_LOG"

echo "" | tee -a "$RESULTS_FILE"

# --- Check for CUDA GPU ---
echo "--- GPU Check ---" | tee -a "$RESULTS_FILE"
if command -v nvidia-smi &> /dev/null; then
    if nvidia-smi &> /dev/null; then
        echo "GPU found:" | tee -a "$RESULTS_FILE"
        nvidia-smi --query-gpu=name,compute_cap,memory.total --format=csv,noheader 2>&1 | tee -a "$RESULTS_FILE"
        echo "" | tee -a "$RESULTS_FILE"
        
        echo "--- Running GPU Benchmark ---" | tee -a "$RESULTS_FILE"
        ./constraint_cuda --bench 2>&1 | tee -a "$RESULTS_FILE"
    else
        echo "nvidia-smi found but no GPU accessible" | tee -a "$RESULTS_FILE"
        echo "Running CPU reference tests only..." | tee -a "$RESULTS_FILE"
        echo "" | tee -a "$RESULTS_FILE"
        echo "NO_GPU: CPU reference tests only" | tee -a "$RESULTS_FILE"
        ./constraint_cuda 2>&1 | tee -a "$RESULTS_FILE"
    fi
else
    echo "nvidia-smi not found — no CUDA GPU available on this host" | tee -a "$RESULTS_FILE"
    echo "Running CPU reference tests only..." | tee -a "$RESULTS_FILE"
    echo "" | tee -a "$RESULTS_FILE"
    echo "NO_GPU: CPU reference tests only" | tee -a "$RESULTS_FILE"
    ./constraint_cuda 2>&1 | tee -a "$RESULTS_FILE"
fi

echo "" | tee -a "$RESULTS_FILE"
echo "--- Benchmark Complete ---" | tee -a "$RESULTS_FILE"
echo "Results saved to: $RESULTS_FILE"
echo "Build log saved to: $BUILD_LOG"

# Show binary info
echo "" | tee -a "$RESULTS_FILE"
echo "Binary info:" | tee -a "$RESULTS_FILE"
file constraint_cuda 2>&1 | tee -a "$RESULTS_FILE"
file constraint_cuda_sm86 2>&1 | tee -a "$RESULTS_FILE"
