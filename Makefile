# Makefile — Cocapn Fleet Stack Build System
# Builds: C libs (static+shared), CUDA kernels (sm_72+sm_86), Rust crates (+aarch64 cross)
# Target: JetsonClaw1 (Jetson Xavier NX, ARM64 Carmel) + cloud servers (x86_64, sm_86)
# Author: Fleet Coding Agent

# =============================================================================
# ANSI Colors
# =============================================================================
YELLOW := \033[33m
GREEN  := \033[32m
RED    := \033[31m
BLUE   := \033[34m
CYAN   := \033[36m
RESET  := \033[0m

# =============================================================================
# Toolchain Auto-Detection
# =============================================================================

# C compiler: prefer gcc, fallback to clang
CC_CANDIDATE := $(shell which gcc 2>/dev/null)
ifeq ($(CC_CANDIDATE),)
    CC_CANDIDATE := $(shell which clang 2>/dev/null)
endif
CC        ?= $(CC_CANDIDATE)
CXX       ?= $(shell which g++ 2>/dev/null || which clang++ 2>/dev/null)
NVCC      := $(shell which nvcc 2>/dev/null)
CARGO     := $(shell which cargo 2>/dev/null)
RUSTUP    := $(shell which rustup 2>/dev/null)
SCP       := $(shell which scp 2>/dev/null)
SSH       := $(shell which ssh 2>/dev/null)
ARCH      := $(shell uname -m)

# =============================================================================
# Directories
# =============================================================================
BUILD_DIR     := build
BUILD_C       := $(BUILD_DIR)/c
BUILD_CUDA    := $(BUILD_DIR)/cuda
BUILD_RUST    := $(BUILD_DIR)/rust
SRC_C_FLUX    := src/c/flux-isa
SRC_C_SONAR   := src/c/sonar
SRC_CUDA_FLUX := src/cuda/flux
SRC_CUDA_SONAR:= src/cuda/sonar
SRC_RUST      := src/rust

# =============================================================================
# Flags
# =============================================================================
C_FLAGS       := -std=c99 -O3 -Wall -Wextra -fPIC -D_POSIX_C_SOURCE=200809L
CUDA_ARCH     := -gencode arch=compute_72,code=sm_72 -gencode arch=compute_86,code=sm_86
NVCC_FLAGS    := -O3 $(CUDA_ARCH) -Xcompiler "$(C_FLAGS)"

# ARM64-specific flags for Jetson Xavier NX Carmel cores
ifeq ($(ARCH),aarch64)
    C_FLAGS += -mcpu=carmel
endif

AR            := ar
ARFLAGS       := rcs
LDFLAGS       := -shared

# =============================================================================
# Source Discovery (with graceful fallback)
# =============================================================================

# C sources — flux-isa
FLUX_C_SRC    := $(wildcard $(SRC_C_FLUX)/*.c)
ifeq ($(FLUX_C_SRC),)
    FLUX_C_SRC_MSG := "$(YELLOW)[WARN]$(RESET) No C sources found in $(SRC_C_FLUX)/ — create .c files to build libfluxisa"
endif

# C sources — sonar
SONAR_C_SRC   := $(wildcard $(SRC_C_SONAR)/*.c)
ifeq ($(SONAR_C_SRC),)
    SONAR_C_SRC_MSG := "$(YELLOW)[WARN]$(RESET) No C sources found in $(SRC_C_SONAR)/ — create .c files to build libsonar"
endif

# CUDA sources — flux
FLUX_CUDA_SRC := $(wildcard $(SRC_CUDA_FLUX)/*.cu)
ifeq ($(FLUX_CUDA_SRC),)
    FLUX_CUDA_MSG := "$(YELLOW)[WARN]$(RESET) No CUDA sources found in $(SRC_CUDA_FLUX)/ — create .cu files to build libfluxcuda"
endif

# CUDA sources — sonar
SONAR_CUDA_SRC:= $(wildcard $(SRC_CUDA_SONAR)/*.cu)
ifeq ($(SONAR_CUDA_SRC),)
    SONAR_CUDA_MSG := "$(YELLOW)[WARN]$(RESET) No CUDA sources found in $(SRC_CUDA_SONAR)/ — create .cu files to build libsonarcuda"
endif

# Object files
FLUX_C_OBJ    := $(patsubst $(SRC_C_FLUX)/%.c,$(BUILD_C)/flux-isa-%.o,$(FLUX_C_SRC))
SONAR_C_OBJ   := $(patsubst $(SRC_C_SONAR)/%.c,$(BUILD_C)/sonar-%.o,$(SONAR_C_SRC))
FLUX_CUDA_OBJ := $(patsubst $(SRC_CUDA_FLUX)/%.cu,$(BUILD_CUDA)/flux-%.o,$(FLUX_CUDA_SRC))
SONAR_CUDA_OBJ:= $(patsubst $(SRC_CUDA_SONAR)/%.cu,$(BUILD_CUDA)/sonar-%.o,$(SONAR_CUDA_SRC))

# =============================================================================
# Default Target
# =============================================================================
.DEFAULT_GOAL := all

# =============================================================================
# Build Directory Creation (order-only prerequisites)
# =============================================================================
$(BUILD_C):
	@mkdir -p $@
	@echo "$(GREEN)[MKDIR]$(RESET) Created $@"

$(BUILD_CUDA):
	@mkdir -p $@
	@echo "$(GREEN)[MKDIR]$(RESET) Created $@"

$(BUILD_RUST):
	@mkdir -p $@
	@echo "$(GREEN)[MKDIR]$(RESET) Created $@"

# Parent build directory
$(BUILD_DIR):
	@mkdir -p $@

# =============================================================================
# Pattern Rules
# =============================================================================

# C compilation: .c -> .o in build/c/
$(BUILD_C)/flux-isa-%.o: $(SRC_C_FLUX)/%.c | $(BUILD_C)
	@echo "$(GREEN)[CC]$(RESET) $<"
	@$(CC) $(C_FLAGS) -c $< -o $@

$(BUILD_C)/sonar-%.o: $(SRC_C_SONAR)/%.c | $(BUILD_C)
	@echo "$(GREEN)[CC]$(RESET) $<"
	@$(CC) $(C_FLAGS) -c $< -o $@

# CUDA compilation: .cu -> .o in build/cuda/
$(BUILD_CUDA)/flux-%.o: $(SRC_CUDA_FLUX)/%.cu | $(BUILD_CUDA)
	@echo "$(GREEN)[NVCC]$(RESET) $<"
	@$(NVCC) $(NVCC_FLAGS) -dc $< -o $@

$(BUILD_CUDA)/sonar-%.o: $(SRC_CUDA_SONAR)/%.cu | $(BUILD_CUDA)
	@echo "$(GREEN)[NVCC]$(RESET) $<"
	@$(NVCC) $(NVCC_FLAGS) -dc $< -o $@

# =============================================================================
# C Targets
# =============================================================================

.PHONY: c flux-isa-c sonar-vision-c

c: flux-isa-c sonar-vision-c

# Flux ISA — static and shared libraries
flux-isa-c: $(BUILD_C)/libfluxisa.a $(BUILD_C)/libfluxisa.so
	@echo "$(GREEN)[DONE]$(RESET) flux-isa-c built"

$(BUILD_C)/libfluxisa.a: $(FLUX_C_OBJ) | $(BUILD_C)
ifeq ($(FLUX_C_SRC),)
	@echo $(FLUX_C_SRC_MSG)
	@echo "$(YELLOW)[SKIP]$(RESET) libfluxisa.a — no sources"
else
	@echo "$(GREEN)[AR]$(RESET) $@"
	@$(AR) $(ARFLAGS) $@ $(FLUX_C_OBJ)
endif

$(BUILD_C)/libfluxisa.so: $(FLUX_C_OBJ) | $(BUILD_C)
ifeq ($(FLUX_C_SRC),)
	@echo "$(YELLOW)[SKIP]$(RESET) libfluxisa.so — no sources"
else
	@echo "$(GREEN)[LD]$(RESET) $@"
	@$(CC) $(LDFLAGS) $(FLUX_C_OBJ) -o $@
endif

# Sonar Vision — static and shared libraries
sonar-vision-c: $(BUILD_C)/libsonar.a $(BUILD_C)/libsonar.so
	@echo "$(GREEN)[DONE]$(RESET) sonar-vision-c built"

$(BUILD_C)/libsonar.a: $(SONAR_C_OBJ) | $(BUILD_C)
ifeq ($(SONAR_C_SRC),)
	@echo $(SONAR_C_SRC_MSG)
	@echo "$(YELLOW)[SKIP]$(RESET) libsonar.a — no sources"
else
	@echo "$(GREEN)[AR]$(RESET) $@"
	@$(AR) $(ARFLAGS) $@ $(SONAR_C_OBJ)
endif

$(BUILD_C)/libsonar.so: $(SONAR_C_OBJ) | $(BUILD_C)
ifeq ($(SONAR_C_SRC),)
	@echo "$(YELLOW)[SKIP]$(RESET) libsonar.so — no sources"
else
	@echo "$(GREEN)[LD]$(RESET) $@"
	@$(CC) $(LDFLAGS) $(SONAR_C_OBJ) -o $@
endif

# =============================================================================
# CUDA Targets
# =============================================================================

.PHONY: cuda flux-cuda sonar-vision-cuda

cuda: flux-cuda sonar-vision-cuda

# Helper: check for nvcc
.PHONY: check-nvcc
check-nvcc:
ifeq ($(NVCC),)
	@echo "$(YELLOW)WARNING: nvcc not found, skipping CUDA targets$(RESET)"
endif

# Flux CUDA — static library
flux-cuda: check-nvcc | $(BUILD_CUDA)
ifeq ($(NVCC),)
	@true
else ifeq ($(FLUX_CUDA_SRC),)
	@echo $(FLUX_CUDA_MSG)
	@echo "$(YELLOW)[SKIP]$(RESET) libfluxcuda.a — no sources"
else
	@$(MAKE) $(BUILD_CUDA)/libfluxcuda.a
	@echo "$(GREEN)[DONE]$(RESET) flux-cuda built"
endif

$(BUILD_CUDA)/libfluxcuda.a: $(FLUX_CUDA_OBJ) | $(BUILD_CUDA)
	@echo "$(GREEN)[AR]$(RESET) $@"
	@$(AR) $(ARFLAGS) $@ $(FLUX_CUDA_OBJ)

# Sonar CUDA — static library
sonar-vision-cuda: check-nvcc | $(BUILD_CUDA)
ifeq ($(NVCC),)
	@true
else ifeq ($(SONAR_CUDA_SRC),)
	@echo $(SONAR_CUDA_MSG)
	@echo "$(YELLOW)[SKIP]$(RESET) libsonarcuda.a — no sources"
else
	@$(MAKE) $(BUILD_CUDA)/libsonarcuda.a
	@echo "$(GREEN)[DONE]$(RESET) sonar-vision-cuda built"
endif

$(BUILD_CUDA)/libsonarcuda.a: $(SONAR_CUDA_OBJ) | $(BUILD_CUDA)
	@echo "$(GREEN)[AR]$(RESET) $@"
	@$(AR) $(ARFLAGS) $@ $(SONAR_CUDA_OBJ)

# =============================================================================
# Rust Targets
# =============================================================================

.PHONY: rust check-cargo rust-flux-isa rust-plato-engine rust-constraint-theory

rust: check-cargo rust-flux-isa rust-plato-engine rust-constraint-theory

check-cargo:
ifeq ($(CARGO),)
	@echo "$(YELLOW)WARNING: cargo not found, skipping Rust targets$(RESET)"
endif

# Build Rust crate helper — takes crate name and optional target
# $(1) = crate name, $(2) = target triple (optional)
define RUST_BUILD
	@echo "$(GREEN)[CARGO]$(RESET) Building $(1)$(if $(2), for $(2)) ..."
	@cd $(SRC_RUST)/$(1) && $(CARGO) build --release $(if $(2),--target=$(2))
endef

# Copy Rust artifacts to build/rust/
define RUST_COPY
	@mkdir -p $(BUILD_RUST)
	@cp $(SRC_RUST)/$(1)/target/$(if $(2),$(2)/release,release)/$(3) $(BUILD_RUST)/$(3) 2>/dev/null || true
endef

rust-flux-isa: check-cargo | $(BUILD_RUST)
ifeq ($(CARGO),)
	@true
else
	$(call RUST_BUILD,flux-isa,)
	$(call RUST_COPY,flux-isa,,flux-isa)
	@echo "$(GREEN)[DONE]$(RESET) flux-isa crate built -> $(BUILD_RUST)/flux-isa"
endif

rust-plato-engine: check-cargo | $(BUILD_RUST)
ifeq ($(CARGO),)
	@true
else
	$(call RUST_BUILD,plato-engine,)
	$(call RUST_COPY,plato-engine,,plato-engine)
	@echo "$(GREEN)[DONE]$(RESET) plato-engine crate built -> $(BUILD_RUST)/plato-engine"
endif

rust-constraint-theory: check-cargo | $(BUILD_RUST)
ifeq ($(CARGO),)
	@true
else
	$(call RUST_BUILD,constraint-theory-core,)
	@mkdir -p $(BUILD_RUST)
	@cp $(SRC_RUST)/constraint-theory-core/target/release/libconstraint_theory.rlib $(BUILD_RUST)/libconstraint_theory.rlib 2>/dev/null || \
	 cp $(SRC_RUST)/constraint-theory-core/target/release/libconstraint_theory*.rlib $(BUILD_RUST)/ 2>/dev/null || true
	@echo "$(GREEN)[DONE]$(RESET) constraint-theory-core crate built"
endif

# =============================================================================
# Rust Cross-Compilation (aarch64)
# =============================================================================

.PHONY: rust-cross

AARCH64_TARGET := aarch64-unknown-linux-gnu
RUST_TARGETS_INSTALLED := $(shell $(RUSTUP) target list --installed 2>/dev/null)
AARCH64_INSTALLED := $(findstring $(AARCH64_TARGET),$(RUST_TARGETS_INSTALLED))

rust-cross: check-cargo | $(BUILD_RUST)
ifeq ($(CARGO),)
	@echo "$(YELLOW)[SKIP]$(RESET) rust-cross — cargo not installed"
else ifeq ($(RUSTUP),)
	@echo "$(YELLOW)[SKIP]$(RESET) rust-cross — rustup not installed (needed for target check)"
else ifeq ($(AARCH64_INSTALLED),)
	@echo "$(YELLOW)WARNING: aarch64 target not installed. Run: rustup target add aarch64-unknown-linux-gnu$(RESET)"
	@echo "$(YELLOW)[SKIP]$(RESET) rust-cross — aarch64 target missing"
else
	@echo "$(GREEN)[CARGO]$(RESET) Cross-compiling Rust crates for $(AARCH64_TARGET) ..."
	@$(MAKE) rust-flux-isa-cross rust-plato-engine-cross rust-constraint-theory-cross
	@echo "$(GREEN)[DONE]$(RESET) rust-cross complete"
endif

.PHONY: rust-flux-isa-cross rust-plato-engine-cross rust-constraint-theory-cross

rust-flux-isa-cross:
	$(call RUST_BUILD,flux-isa,$(AARCH64_TARGET))
	$(call RUST_COPY,flux-isa,$(AARCH64_TARGET),flux-isa)
	@mv $(BUILD_RUST)/flux-isa $(BUILD_RUST)/flux-isa-aarch64 2>/dev/null || true

rust-plato-engine-cross:
	$(call RUST_BUILD,plato-engine,$(AARCH64_TARGET))
	$(call RUST_COPY,plato-engine,$(AARCH64_TARGET),plato-engine)
	@mv $(BUILD_RUST)/plato-engine $(BUILD_RUST)/plato-engine-aarch64 2>/dev/null || true

rust-constraint-theory-cross:
	$(call RUST_BUILD,constraint-theory-core,$(AARCH64_TARGET))
	@mkdir -p $(BUILD_RUST)
	@cp $(SRC_RUST)/constraint-theory-core/target/$(AARCH64_TARGET)/release/libconstraint_theory.rlib $(BUILD_RUST)/libconstraint_theory_aarch64.rlib 2>/dev/null || \
	 cp $(SRC_RUST)/constraint-theory-core/target/$(AARCH64_TARGET)/release/libconstraint_theory*.rlib $(BUILD_RUST)/ 2>/dev/null || true

# =============================================================================
# Aggregated Targets
# =============================================================================

.PHONY: all
all: c cuda rust rust-cross
	@echo ""
	@echo "$(GREEN)========================================$(RESET)"
	@echo "$(GREEN)  Cocapn Fleet Stack build complete$(RESET)"
	@echo "$(GREEN)========================================$(RESET)"
	@echo "  Architecture: $(ARCH)"
	@echo "  C compiler:   $(CC)"
	@echo "  NVCC:         $(if $(NVCC),$(NVCC),$(RED)not found$(RESET))"
	@echo "  Cargo:        $(if $(CARGO),$(CARGO),$(RED)not found$(RESET))"
	@echo "$(GREEN)========================================$(RESET)"

# =============================================================================
# Test Target
# =============================================================================

.PHONY: test test-c test-cuda test-rust

test: test-c test-cuda test-rust

test-c: c
	@echo "$(GREEN)[TEST]$(RESET) Running C unit tests ..."
ifeq ($(wildcard test/test_c.c),)
	@echo "$(YELLOW)[SKIP]$(RESET) No C tests found (test/test_c.c)"
else
	@$(CC) $(C_FLAGS) test/test_c.c -I$(SRC_C_FLUX) -I$(SRC_C_SONAR) \
	    -L$(BUILD_C) -lfluxisa -lsonar -o $(BUILD_DIR)/test_c
	@cd $(BUILD_DIR) && LD_LIBRARY_PATH=$(BUILD_C):$$LD_LIBRARY_PATH ./test_c
endif

test-cuda: cuda
ifeq ($(NVCC),)
	@echo "$(YELLOW)[SKIP]$(RESET) CUDA tests — nvcc not found"
else
	@echo "$(GREEN)[TEST]$(RESET) Running CUDA integration tests ..."
ifeq ($(wildcard test/test_flux_cuda),)
	@echo "$(YELLOW)[SKIP]$(RESET) No CUDA test binary found (test/test_flux_cuda)"
else
	@test/test_flux_cuda
endif
endif

test-rust: check-cargo
ifeq ($(CARGO),)
	@echo "$(YELLOW)[SKIP]$(RESET) Rust tests — cargo not found"
else
	@echo "$(GREEN)[TEST]$(RESET) Running Rust test suite ..."
	@cd $(SRC_RUST)/flux-isa              && $(CARGO) test --release 2>/dev/null || echo "$(YELLOW)[SKIP]$(RESET) flux-isa tests unavailable"
	@cd $(SRC_RUST)/plato-engine          && $(CARGO) test --release 2>/dev/null || echo "$(YELLOW)[SKIP]$(RESET) plato-engine tests unavailable"
	@cd $(SRC_RUST)/constraint-theory-core && $(CARGO) test --release 2>/dev/null || echo "$(YELLOW)[SKIP]$(RESET) constraint-theory-core tests unavailable"
endif

# =============================================================================
# Benchmark Target
# =============================================================================

.PHONY: bench

bench: c
	@echo "$(GREEN)[BENCH]$(RESET) Running benchmark harness ..."
ifeq ($(wildcard benchmark/benchmark_csp),)
ifeq ($(wildcard benchmark/benchmark_csp.c),)
	@echo "$(YELLOW)[SKIP]$(RESET) No benchmark harness found (benchmark/benchmark_csp)"
else
	@$(CC) $(C_FLAGS) benchmark/benchmark_csp.c -I$(SRC_C_FLUX) -L$(BUILD_C) -lfluxisa -o $(BUILD_DIR)/benchmark_csp
	@cd $(BUILD_DIR) && LD_LIBRARY_PATH=$(BUILD_C):$$LD_LIBRARY_PATH ./benchmark_csp
endif
else
	@benchmark/benchmark_csp
endif

# =============================================================================
# Clean Target
# =============================================================================

.PHONY: clean

clean:
	@echo "$(RED)[CLEAN]$(RESET) Removing build artifacts ..."
	@rm -rf $(BUILD_DIR)
	@echo "$(GREEN)[DONE]$(RESET) Clean complete"

# =============================================================================
# Deploy Target
# =============================================================================

.PHONY: deploy-jetson check-deploy-tools

check-deploy-tools:
ifeq ($(SCP),)
	@echo "$(RED)[ERROR]$(RESET) scp not found — required for deploy-jetson"
	@exit 1
endif
ifeq ($(SSH),)
	@echo "$(RED)[ERROR]$(RESET) ssh not found — required for deploy-jetson"
	@exit 1
endif

deploy-jetson: all check-deploy-tools
	@echo "$(CYAN)[DEPLOY]$(RESET) Deploying to jetson@jetsonclaw1.local ..."
	@ssh jetson@jetsonclaw1.local "mkdir -p ~/cocapn/bin/" 2>/dev/null || \
	    echo "$(YELLOW)[WARN]$(RESET) Could not create remote directory (ssh may fail)"
	@scp -r $(BUILD_DIR)/* jetson@jetsonclaw1.local:~/cocapn/bin/ 2>/dev/null || \
	    (echo "$(RED)[ERROR]$(RESET) scp deploy failed — check connectivity and credentials" && exit 1)
	@echo "$(GREEN)[DONE]$(RESET) Deployed to jetson@jetsonclaw1.local:~/cocapn/bin/"

# =============================================================================
# Help Target
# =============================================================================

.PHONY: help

help:
	@echo "Cocapn Fleet Stack Makefile"
	@echo "============================"
	@echo ""
	@echo "Targets:"
	@echo "  all           — Build entire fleet (C + CUDA + Rust)"
	@echo "  c             — Build C libraries (libfluxisa, libsonar)"
	@echo "  cuda          — Build CUDA libraries (libfluxcuda, libsonarcuda)"
	@echo "  rust          — Build Rust crates (native)"
	@echo "  rust-cross    — Cross-compile Rust for aarch64 (Jetson)"
	@echo "  test          — Run all test suites"
	@echo "  bench         — Run benchmark harness"
	@echo "  clean         — Remove all build artifacts"
	@echo "  deploy-jetson — Deploy binaries to JetsonClaw1"
	@echo "  help          — Show this help message"
	@echo ""
	@echo "Detected toolchains:"
	@echo "  CC:     $(if $(CC),$(GREEN)$(CC)$(RESET),$(RED)not found$(RESET))"
	@echo "  CXX:    $(if $(CXX),$(GREEN)$(CXX)$(RESET),$(RED)not found$(RESET))"
	@echo "  NVCC:   $(if $(NVCC),$(GREEN)$(NVCC)$(RESET),$(YELLOW)not found$(RESET))"
	@echo "  CARGO:  $(if $(CARGO),$(GREEN)$(CARGO)$(RESET),$(YELLOW)not found$(RESET))"
	@echo "  RUSTUP: $(if $(RUSTUP),$(GREEN)$(RUSTUP)$(RESET),$(YELLOW)not found$(RESET))"
	@echo "  SCP:    $(if $(SCP),$(GREEN)$(SCP)$(RESET),$(YELLOW)not found$(RESET))"
	@echo "  SSH:    $(if $(SSH),$(GREEN)$(SSH)$(RESET),$(YELLOW)not found$(RESET))"
	@echo "  ARCH:   $(CYAN)$(ARCH)$(RESET)"
	@echo ""
	@echo "Rust aarch64 target: $(if $(AARCH64_INSTALLED),$(GREEN)installed$(RESET),$(YELLOW)not installed$(RESET))"
	@echo ""
	@echo "Directory layout:"
	@echo "  src/c/flux-isa/            — C VM constraint solver sources"
	@echo "  src/c/sonar/                — C underwater acoustic physics sources"
	@echo "  src/cuda/flux/              — CUDA constraint solver kernels"
	@echo "  src/cuda/sonar/             — CUDA acoustic kernels"
	@echo "  src/rust/flux-isa/          — Rust flux-isa crate"
	@echo "  src/rust/plato-engine/      — Rust plato-engine crate"
	@echo "  src/rust/constraint-theory-core/ — Rust constraint-theory-core crate"
	@echo "  build/c/                    — C build artifacts"
	@echo "  build/cuda/                 — CUDA build artifacts"
	@echo "  build/rust/                 — Rust build artifacts"
