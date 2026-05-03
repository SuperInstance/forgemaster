# Makefile — SonarVision: Real-time underwater acoustic physics engine
# C99 + CUDA, targeting Jetson Xavier (sm_72)
#
# Targets:
#   make              — build static library + shared library
#   make test         — build and run validation tests
#   make clean        — remove build artifacts
#   make cuda         — build CUDA components (requires nvcc)
#   make all          — build everything including CUDA

CC      = gcc
NVCC    = nvcc
AR      = ar
ARFLAGS = rcs

# C flags: C99, optimized, fast-math, native arch
CFLAGS   = -std=c99 -O2 -ffast-math -march=native -Wall -Wextra -fPIC
CFLAGS  += -Iinclude

# CUDA flags: sm_72 = Jetson Xavier NX / AGX
NVCCFLAGS = -arch=sm_72 -O2 -Xcompiler -fPIC --std=c++14
NVCCFLAGS += -Iinclude

# Library name
LIBNAME = sonarvision

# Source files (CPU only)
C_SRCS = src/mackenzie.c src/francois_garrison.c src/ray_trace.c \
         src/sonar_equation.c src/reverberation.c src/version.c

# CUDA source files
CU_SRCS = cuda/sonar_cuda.cu cuda/host_api.cu

# Object directories
BUILD_DIR = build
C_OBJDIR  = $(BUILD_DIR)/cpu
CU_OBJDIR = $(BUILD_DIR)/cuda

C_OBJS  = $(patsubst src/%.c,$(C_OBJDIR)/%.o,$(C_SRCS))
CU_OBJS = $(patsubst cuda/%.cu,$(CU_OBJDIR)/%.o,$(CU_SRCS))

# Output
STATIC_LIB  = $(BUILD_DIR)/lib$(LIBNAME).a
SHARED_LIB  = $(BUILD_DIR)/lib$(LIBNAME).so
CUDA_LIB    = $(BUILD_DIR)/lib$(LIBNAME)_cuda.a
TEST_BIN    = $(BUILD_DIR)/test_physics

# Linker flags
LDFLAGS  = -lm
CULDFLAGS = -lcudart

# ── Default: CPU-only libraries ────────────────────────────────────

.PHONY: all cpu cuda test clean

all: cpu cuda

cpu: $(STATIC_LIB) $(SHARED_LIB)

cuda: $(CUDA_LIB) $(STATIC_LIB)

# ── Build directories ──────────────────────────────────────────────

$(C_OBJDIR):
	@mkdir -p $(C_OBJDIR)

$(CU_OBJDIR):
	@mkdir -p $(CU_OBJDIR)

$(BUILD_DIR):
	@mkdir -p $(BUILD_DIR)

# ── Compile C sources ──────────────────────────────────────────────

$(C_OBJDIR)/%.o: src/%.c | $(C_OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@

# ── Compile CUDA sources ───────────────────────────────────────────

$(CU_OBJDIR)/%.o: cuda/%.cu | $(CU_OBJDIR)
	$(NVCC) $(NVCCFLAGS) -c $< -o $@

# ── Static library (CPU only) ──────────────────────────────────────

$(STATIC_LIB): $(C_OBJS) | $(BUILD_DIR)
	$(AR) $(ARFLAGS) $@ $^

# ── Shared library (CPU only) ──────────────────────────────────────

$(SHARED_LIB): $(C_OBJS) | $(BUILD_DIR)
	$(CC) -shared -o $@ $^ $(LDFLAGS)

# ── CUDA static library ────────────────────────────────────────────

$(CUDA_LIB): $(CU_OBJS) | $(BUILD_DIR)
	$(AR) $(ARFLAGS) $@ $^

# ── Test binary (CPU only, no CUDA dependency) ─────────────────────

$(TEST_BIN): test/test_physics.c $(STATIC_LIB) | $(BUILD_DIR)
	$(CC) $(CFLAGS) -o $@ $< -L$(BUILD_DIR) -l$(LIBNAME) $(LDFLAGS)

test: $(TEST_BIN)
	@echo "Running SonarVision physics validation..."
	@LD_LIBRARY_PATH=$(BUILD_DIR) ./$(TEST_BIN)

# ── Clean ───────────────────────────────────────────────────────────

clean:
	rm -rf $(BUILD_DIR)

# ── Dependencies (explicit, no auto-dep for simplicity) ────────────

$(C_OBJDIR)/mackenzie.o: include/sonar_vision.h
$(C_OBJDIR)/francois_garrison.o: include/sonar_vision.h
$(C_OBJDIR)/ray_trace.o: include/sonar_vision.h
$(C_OBJDIR)/sonar_equation.o: include/sonar_vision.h
$(C_OBJDIR)/reverberation.o: include/sonar_vision.h
$(C_OBJDIR)/version.o: include/sonar_vision.h
