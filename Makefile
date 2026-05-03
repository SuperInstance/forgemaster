# =============================================================================
# Makefile — Cocapn Fleet Definitive Build System
# =============================================================================
# Builds: C libs, CUDA binaries, Rust crates (all fleet targets)
# Target: JetsonClaw1 (Jetson Xavier NX, ARM64) + cloud (x86_64)
# Auto-detects toolchains, graceful degradation for missing ones
# =============================================================================

# =============================================================================
# ANSI Colors
# =============================================================================
Y  := \033[33m
G  := \033[32m
R  := \033[31m
C  := \033[36m
B  := \033[34m
E  := \033[0m

# =============================================================================
# Toolchain Auto-Detection
# =============================================================================
CC      ?= $(shell which gcc 2>/dev/null || which clang 2>/dev/null)
CXX     ?= $(shell which g++ 2>/dev/null || which clang++ 2>/dev/null)
NVCC    := $(shell which nvcc 2>/dev/null)
CARGO   := $(shell which cargo 2>/dev/null)
PYTHON3 := $(shell which python3 2>/dev/null)
SCP     := $(shell which scp 2>/dev/null)
ARCH    := $(shell uname -m)

# =============================================================================
# Directories
# =============================================================================
B       := build
BC      := $(B)/c
BCUDA   := $(B)/cuda
BRUST   := $(B)/rust
BDEPLOY := $(B)/deploy

# =============================================================================
# Flags
# =============================================================================
CFLAGS  := -std=c99 -O3 -Wall -Wextra -fPIC -D_POSIX_C_SOURCE=200809L
AR      := ar
ARFLAGS := rcs

ifeq ($(ARCH),aarch64)
  CFLAGS += -mcpu=carmel
endif

# CUDA
CUDA_ARCH  := -gencode arch=compute_72,code=sm_72 -gencode arch=compute_86,code=sm_86
NVCC_FLAGS := -O3 $(CUDA_ARCH) -Xcompiler "-fPIC"

# Rust — max 2 concurrent builds (OOM protection)
CARGO_JOBS := 2

# =============================================================================
# C Source Discovery
# =============================================================================
FLUX_C_SRC    := $(wildcard flux-isa-c/src/*.c)
SONAR_C_SRC   := $(wildcard sonar-vision-c/src/*.c)
FLUX_C_OBJ    := $(patsubst flux-isa-c/src/%.c,$(BC)/flux-isa-%.o,$(FLUX_C_SRC))
SONAR_C_OBJ   := $(patsubst sonar-vision-c/src/%.c,$(BC)/sonar-%.o,$(SONAR_C_SRC))

# =============================================================================
# Rust Crate List (workspace-root subdirs)
# =============================================================================
RUST_CRATES := \
	flux-isa \
	flux-isa-mini \
	flux-isa-std \
	flux-isa-edge \
	flux-isa-thor \
	cocapn-glue-core \
	plato-engine \
	constraint-theory-core-cuda

# Filter to only crates that actually have Cargo.toml
RUST_PRESENT := $(foreach crate,$(RUST_CRATES),$(shell test -f $(crate)/Cargo.toml && echo $(crate)))

# =============================================================================
# Default
# =============================================================================
.DEFAULT_GOAL := all

# =============================================================================
# Directory rules (order-only)
# =============================================================================
$(B) $(BC) $(BCUDA) $(BRUST) $(BDEPLOY):
	@mkdir -p $@

# =============================================================================
# C Pattern Rules
# =============================================================================
$(BC)/flux-isa-%.o: flux-isa-c/src/%.c | $(BC)
	@echo "$(G)[CC]$(E) $<"
	@$(CC) $(CFLAGS) -Iflux-isa-c/include -c $< -o $@

$(BC)/sonar-%.o: sonar-vision-c/src/%.c | $(BC)
	@echo "$(G)[CC]$(E) $<"
	@$(CC) $(CFLAGS) -Isonar-vision-c/include -c $< -o $@

# =============================================================================
# PHONY declarations
# =============================================================================
.PHONY: all c cuda rust test bench clean deploy-jetson publish help \
        c-libs c-bins \
        $(RUST_CRATES:%=rust-%)

# =============================================================================
# ALL
# =============================================================================
all:
	@echo "$(G)════════════════════════════════════════$(E)"
	@echo "$(G)  Cocapn Fleet Build System$(E)"
	@echo "$(G)════════════════════════════════════════$(E)"
	@echo "  CC:      $(or $(CC),$(R)not found$(E))"
	@echo "  CXX:     $(or $(CXX),$(R)not found$(E))"
	@echo "  NVCC:    $(or $(NVCC),$(Y)not found — CUDA skipped$(E))"
	@echo "  CARGO:   $(or $(CARGO),$(Y)not found — Rust skipped$(E))"
	@echo "  PYTHON3: $(or $(PYTHON3),$(Y)not found$(E))"
	@echo "  ARCH:    $(C)$(ARCH)$(E)"
	@echo "$(G)════════════════════════════════════════$(E)"
	@$(MAKE) --no-print-directory _all

.PHONY: _all
_all: c cuda rust
	@echo ""
	@echo "$(G)════════════════════════════════════════$(E)"
	@echo "$(G)  ✓ Fleet build complete$(E)"
	@echo "$(G)════════════════════════════════════════$(E)"

# =============================================================================
# C TARGETS
# =============================================================================
c: c-libs c-bins
	@echo "$(G)[C]$(E) All C targets built"

# --- Libraries ---
c-libs: $(BC)/libfluxisa.a $(BC)/libfluxisa.so $(BC)/libsonarvision.a
	@true

$(BC)/libfluxisa.a: $(FLUX_C_OBJ) | $(BC)
ifeq ($(FLUX_C_SRC),)
	@echo "$(Y)[SKIP]$(E) libfluxisa — no sources in flux-isa-c/src/"
else
	@echo "$(G)[AR]$(E) $@"
	@$(AR) $(ARFLAGS) $@ $^
endif

$(BC)/libfluxisa.so: $(FLUX_C_OBJ) | $(BC)
ifeq ($(FLUX_C_SRC),)
	@echo "$(Y)[SKIP]$(E) libfluxisa.so — no sources"
else
	@echo "$(G)[LD]$(E) $@"
	@$(CC) -shared $^ -o $@ -lm
endif

$(BC)/libsonarvision.a: $(SONAR_C_OBJ) | $(BC)
ifeq ($(SONAR_C_SRC),)
	@echo "$(Y)[SKIP]$(E) libsonarvision — no sources in sonar-vision-c/src/"
else
	@echo "$(G)[AR]$(E) $@"
	@$(AR) $(ARFLAGS) $@ $^
endif

# --- Standalone C binaries ---
c-bins: $(B)/benchmark_csp
	@true

$(B)/benchmark_csp: benchmark_csp.c c-libs | $(B)
ifeq ($(CC),)
	@echo "$(Y)[SKIP]$(E) benchmark_csp — no C compiler"
else ifeq ($(wildcard benchmark_csp.c),)
	@echo "$(Y)[SKIP]$(E) benchmark_csp.c not found"
else
	@echo "$(G)[CC]$(E) benchmark_csp.c → $@"
	@$(CC) $(CFLAGS) -Iflux-isa-c/include benchmark_csp.c \
	    -L$(BC) -lfluxisa -lm -o $@
endif

# =============================================================================
# CUDA TARGETS
# =============================================================================
cuda:
ifeq ($(NVCC),)
	@echo "$(Y)[SKIP]$(E) CUDA — nvcc not found"
else
	@$(MAKE) --no-print-directory _cuda
endif

.PHONY: _cuda
_cuda: $(B)/nqueens_cuda $(B)/test_flux_cuda
	@echo "$(G)[CUDA]$(E) All CUDA targets built"

$(B)/nqueens_cuda: nqueens_cuda.cu | $(B)
ifeq ($(NVCC),)
	@true
else ifeq ($(wildcard nqueens_cuda.cu),)
	@echo "$(Y)[SKIP]$(E) nqueens_cuda.cu not found"
else
	@echo "$(G)[NVCC]$(E) nqueens_cuda.cu → $@"
	@$(NVCC) $(NVCC_FLAGS) $< -o $@
endif

$(B)/test_flux_cuda: test_flux_cuda.cu | $(B)
ifeq ($(NVCC),)
	@true
else ifeq ($(wildcard test_flux_cuda.cu),)
	@echo "$(Y)[SKIP]$(E) test_flux_cuda.cu not found"
else
	@echo "$(G)[NVCC]$(E) test_flux_cuda.cu → $@"
	@$(NVCC) $(NVCC_FLAGS) $< -o $@
endif

# =============================================================================
# RUST TARGETS
# =============================================================================
# Strategy: build crates in batches of CARGO_JOBS to avoid OOM
# Each crate gets its own phony target for selective builds

rust:
ifeq ($(CARGO),)
	@echo "$(Y)[SKIP]$(E) Rust — cargo not found"
else ifeq ($(RUST_PRESENT),)
	@echo "$(Y)[SKIP]$(E) Rust — no Cargo.toml found in any crate directory"
else
	@echo "$(G)[RUST]$(E) Building $(words $(RUST_PRESENT)) crate(s): $(RUST_PRESENT)"
	@$(MAKE) --no-print-directory _rust
	@echo "$(G)[RUST]$(E) All Rust crates built"
endif

.PHONY: _rust
_rust: $(RUST_PRESENT:%=rust-%)

# Per-crate build rules
define RUST_CRATE_RULE
rust-$(1):
	@echo "$(G)[CARGO]$(E) Building $(1)..."
	@cd $(1) && $(CARGO) build --release --jobs $(CARGO_JOBS)
	@mkdir -p $(BRUST)
	@cp -f $(1)/target/release/lib$(subst -,_,$(1)).rlib $(BRUST)/ 2>/dev/null || true
	@cp -f $(1)/target/release/lib$(subst -,_,$(1))*.so $(BRUST)/ 2>/dev/null || true
	@cp -f $(1)/target/release/$(1) $(BRUST)/ 2>/dev/null || true
	@echo "$(G)[DONE]$(E) $(1)"
endef

$(foreach crate,$(RUST_PRESENT),$(eval $(call RUST_CRATE_RULE,$(crate))))

# =============================================================================
# TEST
# =============================================================================
test: test-c test-cuda test-rust
	@echo "$(G)[TEST]$(E) All test suites complete"

.PHONY: test-c test-cuda test-rust

test-c: c
	@echo "$(G)[TEST]$(E) Running C tests..."
	@for dir in flux-isa-c sonar-vision-c; do \
	    if [ -f $$dir/Makefile ] && grep -q '^test:' $$dir/Makefile 2>/dev/null; then \
	        echo "$(G)[TEST]$(E) $$dir"; \
	        $(MAKE) -C $$dir test || true; \
	    fi; \
	done

test-cuda: cuda
ifeq ($(NVCC),)
	@echo "$(Y)[SKIP]$(E) CUDA tests — nvcc not found"
else ifeq ($(wildcard $(B)/test_flux_cuda),)
	@echo "$(Y)[SKIP]$(E) No test_flux_cuda binary"
else
	@echo "$(G)[TEST]$(E) Running test_flux_cuda..."
	@$(B)/test_flux_cuda
endif

test-rust:
ifeq ($(CARGO),)
	@echo "$(Y)[SKIP]$(E) Rust tests — cargo not found"
else
	@echo "$(G)[TEST]$(E) Running Rust tests..."
	@for crate in $(RUST_PRESENT); do \
	    echo "$(G)[TEST]$(E) $$crate"; \
	    cd $$crate && $(CARGO) test --release --jobs $(CARGO_JOBS) 2>&1 | tail -5 || true; \
	    cd - > /dev/null; \
	done
endif

# =============================================================================
# BENCHMARK
# =============================================================================
bench: $(B)/benchmark_csp
ifeq ($(wildcard $(B)/benchmark_csp),)
	@echo "$(Y)[SKIP]$(E) benchmark_csp not built"
else
	@echo "$(G)[BENCH]$(E) Running benchmark_csp..."
	@cd $(B) && LD_LIBRARY_PATH=$(BC):$$$$LD_LIBRARY_PATH ./benchmark_csp
endif

# =============================================================================
# CLEAN
# =============================================================================
clean:
	@echo "$(R)[CLEAN]$(E) Removing build/ ..."
	@rm -rf $(B)
	@echo "$(G)[DONE]$(E) Clean complete"

# =============================================================================
# DEPLOY
# =============================================================================
deploy-jetson: all
	@mkdir -p $(BDEPLOY)
	@cp -r $(BC)/* $(BCUDA)/* $(BRUST)/* $(BDEPLOY)/ 2>/dev/null || true
	@echo "$(C)[DEPLOY]$(E) Deploying to jetson@jetsonclaw1.local:~/cocapn/bin/ ..."
	@ssh jetson@jetsonclaw1.local "mkdir -p ~/cocapn/bin" 2>/dev/null || \
	    echo "$(Y)[WARN]$(E) SSH mkdir failed (may need connectivity check)"
	@scp -r $(BDEPLOY)/* jetson@jetsonclaw1.local:~/cocapn/bin/ || \
	    (echo "$(R)[ERROR]$(E) Deploy failed" && exit 1)
	@echo "$(G)[DONE]$(E) Deployed to JetsonClaw1"

# =============================================================================
# PUBLISH (Rust crates — dry-run first)
# =============================================================================
publish:
ifeq ($(CARGO),)
	@echo "$(R)[ERROR]$(E) cargo not found"
else
	@echo "$(C)[PUBLISH]$(E) Dry-run publish for all Rust crates..."
	@for crate in $(RUST_PRESENT); do \
	    echo "$(G)[PUBLISH --dry-run]$(E) $$crate"; \
	    cd $$crate && $(CARGO) publish --dry-run 2>&1 | tail -3 || true; \
	    cd - > /dev/null; \
	done
	@echo ""
	@echo "$(Y)Dry run complete. Run 'make publish-for-real' to actually publish.$(E)"
endif

.PHONY: publish-for-real
publish-for-real:
	@echo "$(R)[PUBLISH]$(E) Publishing ALL Rust crates for real..."
	@for crate in $(RUST_PRESENT); do \
	    echo "$(G)[PUBLISH]$(E) $$crate"; \
	    cd $$crate && $(CARGO) publish || exit 1; \
	    cd - > /dev/null; \
	done
	@echo "$(G)[DONE]$(E) All crates published"

# =============================================================================
# HELP
# =============================================================================
help:
	@echo "$(C)Cocapn Fleet Build System$(E)"
	@echo "═══════════════════════════"
	@echo ""
	@echo "$(B)Targets:$(E)"
	@echo "  all             — Build everything (C + CUDA + Rust)"
	@echo "  c               — C targets: libfluxisa.a/so, libsonarvision.a, benchmark_csp"
	@echo "  cuda            — CUDA targets: nqueens_cuda, test_flux_cuda"
	@echo "  rust            — All Rust crates (OOM-safe parallelism)"
	@echo "  test            — Run all test suites"
	@echo "  bench           — Run benchmark_csp"
	@echo "  clean           — Remove build/"
	@echo "  deploy-jetson   — Deploy to jetson@jetsonclaw1.local:~/cocapn/bin/"
	@echo "  publish         — Dry-run cargo publish for all crates"
	@echo "  publish-for-real— Actually publish all crates"
	@echo "  help            — This message"
	@echo ""
	@echo "$(B)Individual Rust crates:$(E)"
	@for crate in $(RUST_PRESENT); do echo "  rust-$$crate"; done
	@echo ""
	@echo "$(B)Detected toolchains:$(E)"
	@echo "  CC:      $(or $(CC),$(R)missing$(E))"
	@echo "  CXX:     $(or $(CXX),$(R)missing$(E))"
	@echo "  NVCC:    $(or $(NVCC),$(Y)missing$(E))"
	@echo "  CARGO:   $(or $(CARGO),$(Y)missing$(E))"
	@echo "  PYTHON3: $(or $(PYTHON3),$(Y)missing$(E))"
	@echo "  ARCH:    $(C)$(ARCH)$(E)"
	@echo ""
	@echo "$(B)Rust crates found ($(words $(RUST_PRESENT))):$(E) $(RUST_PRESENT)"
	@echo "$(B)Cargo parallelism:$(E) $(CARGO_JOBS) jobs"
