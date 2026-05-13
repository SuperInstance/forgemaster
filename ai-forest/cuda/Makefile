# Penrose CUDA — Build System
#
# Targets:
#   make        — build the CUDA binary (for RTX 4050: sm_89)
#   make ptx   — generate PTX assembly for inspection
#   make run   — run with default 5 iterations
#   make run7  — run with 7 iterations (6100 triangles)
#   make profile — profile with nvprof
#   make clean — remove build artifacts

NVCC = nvcc
ARCH = -arch=sm_89
OPT = -O3
SRC = penrose_cuda.cu
BIN = penrose_cuda
PTX_OUT = penrose.ptx

all: $(BIN)

$(BIN): $(SRC)
	$(NVCC) $(OPT) $(ARCH) -o $@ $^
	@echo "Built: $@"

ptx: $(SRC)
	$(NVCC) $(OPT) $(ARCH) -ptx $^ -o $(PTX_OUT)
	@echo "PTX generated: $(PTX_OUT)"

run: $(BIN)
	./$(BIN) 5

run7: $(BIN)
	./$(BIN) 7

run_verify: $(BIN)
	./$(BIN) 5 --verify

profile: $(BIN)
	nvprof ./$(BIN) 7

clean:
	rm -f $(BIN) $(PTX_OUT) *.o
