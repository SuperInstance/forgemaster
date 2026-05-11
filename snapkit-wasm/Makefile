# snapkit-wasm Makefile
# Builds snapkit_glue.c → snapkit.wasm using clang with wasm32 target
# No Emscripten needed — pure math, no libc/syscalls

CC = clang
TARGET = wasm32
WASM_LD = wasm-ld

# Flags for WASM compilation
CFLAGS = --target=$(TARGET) -O3 -nostdlib \
         -fno-builtin -fvisibility=hidden \
         -Wall -Wextra -Wno-unused-parameter

# Exported functions
EXPORTS = eisenstein_snap \
          eisenstein_snap_voronoi \
          eisenstein_snap_batch \
          covering_radius \
          beat_grid_snap \
          beat_grid_snap_batch \
          wasm_alloc

# Build the export flags
EXPORT_FLAGS = $(foreach fn,$(EXPORTS),-Wl,--export=$(fn))

# Maximum memory: 16 pages (1MB)
MEMORY_FLAGS = -Wl,--max-memory=1048576

SRC = src/snapkit_glue.c
OUT = snapkit.wasm

.PHONY: all clean check

all: $(OUT)

# Try wasm-ld first (lld), fall back to direct clang linking
$(OUT): $(SRC)
	$(CC) $(CFLAGS) $(EXPORT_FLAGS) $(MEMORY_FLAGS) \
	      -Wl,--no-entry -Wl,--allow-undefined \
	      -o $@ $< -lm

clean:
	rm -f $(OUT)

check: $(OUT)
	@echo "Checking WASM exports..."
	@wasm-objdump -x $(OUT) 2>/dev/null || \
	 wasm2wat $(OUT) 2>/dev/null | grep '(export' || \
	 echo "Install wabt (wasm-objdump/wasm2wat) to inspect exports"

# Alternative build using wasm-ld directly (if clang can't do it in one step)
$(OUT).alt: $(SRC)
	$(CC) $(CFLAGS) -c -o snapkit_glue.o $<
	$(WASM_LD) --no-entry --allow-undefined \
	            $(EXPORT_FLAGS) \
	            -o $(OUT) snapkit_glue.o
	rm -f snapkit_glue.o
