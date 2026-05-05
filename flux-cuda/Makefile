# Makefile for FLUX CUDA library
# Targets: Jetson Xavier (sm_72) + Ampere (sm_86)

NVCC      ?= nvcc
NVCC_FLAGS = -std=c++17 -O2 -lineinfo -Xcompiler -fPIC
ARCH_FLAGS = -gencode arch=compute_72,code=sm_72 \
             -gencode arch=compute_72,code=compute_72 \
             -gencode arch=compute_86,code=sm_86 \
             -gencode arch=compute_86,code=compute_86

INCLUDES  = -Iinclude
LIBS      = -lcudart

SRCDIR    = src
TESTDIR   = test
BUILDDIR  = build

SRCS      = $(SRCDIR)/flux_vm_kernel.cu \
            $(SRCDIR)/csp_solver_kernel.cu \
            $(SRCDIR)/sonar_physics_kernel.cu \
            $(SRCDIR)/host_interface.cu

OBJS      = $(patsubst $(SRCDIR)/%.cu,$(BUILDDIR)/%.o,$(SRCS))

TARGET_LIB  = libflux_cuda.a
TARGET_SO   = libflux_cuda.so
TARGET_TEST = test_flux_cuda

.PHONY: all static shared test clean info

all: static shared

# ── Static library ──────────────────────────────────────────
static: $(TARGET_LIB)

$(TARGET_LIB): $(OBJS)
	ar rcs $@ $^

# ── Shared library ──────────────────────────────────────────
shared: $(TARGET_SO)

$(TARGET_SO): $(OBJS)
	$(NVCC) -shared -o $@ $^ $(LIBS) $(NVCC_FLAGS) $(ARCH_FLAGS)

# ── Object files ────────────────────────────────────────────
$(BUILDDIR)/%.o: $(SRCDIR)/%.cu | $(BUILDDIR)
	$(NVCC) $(NVCC_FLAGS) $(ARCH_FLAGS) $(INCLUDES) -c $< -o $@

$(BUILDDIR):
	mkdir -p $(BUILDDIR)

# ── Tests ───────────────────────────────────────────────────
test: $(TARGET_TEST)
	./$(TARGET_TEST)

$(TARGET_TEST): $(TESTDIR)/test_cuda.cu $(TARGET_LIB)
	$(NVCC) $(NVCC_FLAGS) $(ARCH_FLAGS) $(INCLUDES) -o $@ $< -L. -lflux_cuda $(LIBS)

# ── Clean ───────────────────────────────────────────────────
clean:
	rm -rf $(BUILDDIR) $(TARGET_LIB) $(TARGET_SO) $(TARGET_TEST)

# ── Info ────────────────────────────────────────────────────
info:
	@echo "NVCC: $(NVCC)"
	@echo "Flags: $(NVCC_FLAGS)"
	@echo "Arch: $(ARCH_FLAGS)"
	@echo "Sources: $(SRCS)"
	@echo "Objects: $(OBJS)"
