# Makefile for snapkit-cuda — GPU tolerance-compressed attention allocation
# Targets: sm_86 (Ada/RTX 40xx), sm_75 fallback (Turing/RTX 20xx)
# Requires CUDA 11.5+

CUDA_HOME ?= /usr/local/cuda
NVCC := $(CUDA_HOME)/bin/nvcc

CUDA_MINIMUM_VERSION := 11.5
CUDA_VERSION := $(shell $(NVCC) --version | grep -oP 'release \K[0-9]+\.[0-9]+' || echo "0.0")

# Architecture targets
SM_TARGETS := -gencode arch=compute_86,code=sm_86 -gencode arch=compute_89,code=sm_89
SM_TARGETS += -gencode arch=compute_75,code=sm_75

# Compiler flags
NVCC_FLAGS := $(SM_TARGETS) -O3 -std=c++17 -Xcompiler -O3,-march=native,-fPIC
NVCC_FLAGS += --use_fast_math -maxrregcount=128
NVCC_FLAGS += -DNDEBUG -DCUDA_CHECK

# Debug flags (not used in release)
DEBUG_FLAGS := -G -DDEBUG -DCUDA_CHECK

# Includes
INCLUDES := -Iinclude -I$(CUDA_HOME)/include

# Libraries
LIBRARIES := -L$(CUDA_HOME)/lib64 -lcudart -lcuda

# Sources (explicit order for proper linking)
SRC := \
	src/eisenstein_snap.cu \
	src/batch_snap.cu \
	src/delta_detect.cu \
	src/attention.cu \
	src/topology.cu \
	src/reduce.cu \
	src/snapkit_cuda.cu
OBJ := $(SRC:.cu=.o)

# Library targets
STATIC_LIB := libsnapkit_cuda.a
SHARED_LIB := libsnapkit_cuda.so

# PTX extraction
PTX_DIR := ptx
PTX_SRC := kernels/eisenstein_snap_kernel.cuh kernels/delta_threshold_kernel.cuh
PTX_SRC += kernels/attention_weight_kernel.cuh kernels/topology_snap_kernel.cuh

# Test source
TEST_SRC := $(wildcard tests/*.cu)
TEST_BINS := $(TEST_SRC:.cu=)

# Example source
EXAMPLE_SRC := $(wildcard examples/*.cu)
EXAMPLE_BINS := $(EXAMPLE_SRC:.cu=)

# Bench source
BENCH_SRC := $(wildcard benches/*.cu)
BENCH_BINS := $(BENCH_SRC:.cu=)

# Default target
.PHONY: all
all: $(STATIC_LIB) $(SHARED_LIB)

# Object files
src/%.o: src/%.cu include/snapkit_cuda/snapkit_cuda.h
	$(NVCC) $(NVCC_FLAGS) $(INCLUDES) -c $< -o $@

# Static library
$(STATIC_LIB): $(OBJ)
	ar rcs $@ $^

# Shared library
$(SHARED_LIB): $(OBJ)
	$(NVCC) $(NVCC_FLAGS) $(INCLUDES) --shared -o $@ $^ $(LIBRARIES)

# PTX extraction
$(PTX_DIR)/%.ptx: kernels/%.cuh
	mkdir -p $(PTX_DIR)
	$(NVCC) -ptx $(SM_TARGETS) --use_fast_math -std=c++17 $(INCLUDES) \
		--device-c $< -o $@ 2>/dev/null || \
		echo "Warning: Could not compile PTX for $< (may need device-linkable wrapper)"

.PHONY: ptx
ptx: $(PTX_SRC:kernels/%=$(PTX_DIR)/%)

# Build tests
tests/test_eisenstein: tests/test_eisenstein.cu $(STATIC_LIB)
	$(NVCC) $(NVCC_FLAGS) $(INCLUDES) -o $@ $< $(STATIC_LIB) $(LIBRARIES)

tests/test_batch: tests/test_batch.cu $(STATIC_LIB)
	$(NVCC) $(NVCC_FLAGS) $(INCLUDES) -o $@ $< $(STATIC_LIB) $(LIBRARIES)

tests/test_delta: tests/test_delta.cu $(STATIC_LIB)
	$(NVCC) $(NVCC_FLAGS) $(INCLUDES) -o $@ $< $(STATIC_LIB) $(LIBRARIES)

tests/test_correctness: tests/test_correctness.cu $(STATIC_LIB)
	$(NVCC) $(NVCC_FLAGS) $(INCLUDES) -o $@ $< $(STATIC_LIB) $(LIBRARIES)

tests/run_tests: tests/run_tests.cu $(STATIC_LIB)
	$(NVCC) $(NVCC_FLAGS) $(INCLUDES) -o $@ $< $(STATIC_LIB) $(LIBRARIES)

.PHONY: test
test: tests/test_eisenstein tests/test_batch tests/test_delta tests/test_correctness tests/run_tests
	@echo "Running all tests..."
	@tests/run_tests --quick || (echo "Some tests failed!" && exit 1)
	@echo "All tests passed!"

# Build examples
examples/batch_eisenstein: examples/batch_eisenstein.cu $(STATIC_LIB)
	$(NVCC) $(NVCC_FLAGS) $(INCLUDES) -o $@ $< $(STATIC_LIB) $(LIBRARIES)

examples/stream_monitor: examples/stream_monitor.cu $(STATIC_LIB)
	$(NVCC) $(NVCC_FLAGS) $(INCLUDES) -o $@ $< $(STATIC_LIB) $(LIBRARIES)

examples/topology_compare: examples/topology_compare.cu $(STATIC_LIB)
	$(NVCC) $(NVCC_FLAGS) $(INCLUDES) -o $@ $< $(STATIC_LIB) $(LIBRARIES)

examples/multi_stream: examples/multi_stream.cu $(STATIC_LIB)
	$(NVCC) $(NVCC_FLAGS) $(INCLUDES) -o $@ $< $(STATIC_LIB) $(LIBRARIES)

.PHONY: examples
examples: $(EXAMPLE_BINS)

# Build benchmarks
benches/bench_snap: benches/bench_snap.cu $(STATIC_LIB)
	$(NVCC) $(NVCC_FLAGS) $(INCLUDES) -o $@ $< $(STATIC_LIB) $(LIBRARIES)

benches/bench_comparison: benches/bench_comparison.cu $(STATIC_LIB)
	$(NVCC) $(NVCC_FLAGS) $(INCLUDES) -o $@ $< $(STATIC_LIB) $(LIBRARIES)

.PHONY: bench
bench: $(BENCH_BINS)
	@echo "Running all benchmarks..."
	@for b in $(BENCH_BINS); do \
		echo "  Benchmark: $$b"; \
		$$b || exit 1; \
	done

# Check CUDA version
.PHONY: check-cuda
check-cuda:
	@echo "CUDA version: $(CUDA_VERSION)"
	@if [ "$$(printf '%s\n' '$(CUDA_MINIMUM_VERSION)' '$(CUDA_VERSION)' | sort -V | head -n1)" != '$(CUDA_MINIMUM_VERSION)' ]; then \
		echo "ERROR: CUDA $(CUDA_MINIMUM_VERSION)+ required (found $(CUDA_VERSION))"; \
		exit 1; \
	fi
	@echo "CUDA version OK"

# Clean
.PHONY: clean
clean:
	rm -f $(OBJ) $(STATIC_LIB) $(SHARED_LIB)
	rm -f $(TEST_BINS) $(EXAMPLE_BINS) $(BENCH_BINS)
	rm -f $(PTX_DIR)/*.ptx
	rm -rf __pycache__

# Debug build
.PHONY: debug
debug: NVCC_FLAGS = $(SM_TARGETS) -G -std=c++17 -Xcompiler -O0,-fPIC -DCUDA_CHECK
debug: clean all

# Quick test (skips correctness verification)
.PHONY: test-quick
test-quick: tests/test_eisenstein tests/test_batch tests/test_delta
	@echo "Running quick tests..."
	@tests/test_eisenstein && tests/test_batch && tests/test_delta && echo "Quick tests passed!"

# Full test (includes CPU vs GPU correctness)
.PHONY: test-full
test-full: test

# Install
.PHONY: install
install: all
	@echo "Install not configured. Files are at:"
	@echo "  include/snapkit_cuda/"
	@echo "  $(STATIC_LIB)"
	@echo "  $(SHARED_LIB)"

# Help
.PHONY: help
help:
	@echo "snapkit-cuda Makefile targets:"
	@echo "  all       — Build static and shared libraries (default)"
	@echo "  test      — Build and run all tests"
	@echo "  bench     — Build and run all benchmarks"
	@echo "  examples  — Build all examples"
	@echo "  ptx       — Extract PTX for manual inspection"
	@echo "  debug     — Debug build (-G flag)"
	@echo "  clean     — Remove all build artifacts"
	@echo "  check-cuda — Verify CUDA version"
	@echo ""
	@echo "Requirements: CUDA $(CUDA_MINIMUM_VERSION)+, nvcc compatible"
	@echo "Targets: sm_86 (Ada), sm_89 (Ada refresh), sm_75 (Turing)"

.DEFAULT_GOAL := all
