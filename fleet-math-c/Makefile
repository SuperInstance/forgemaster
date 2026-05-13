CC = gcc
CFLAGS = -O3 -march=native -Wall -Wextra -std=c11
LDFLAGS = -lm

all: bridge_bench

bridge_bench: bridge_bench.c eisenstein_bridge.c eisenstein_bridge.h
	$(CC) $(CFLAGS) -o $@ bridge_bench.c eisenstein_bridge.c $(LDFLAGS)

run: bridge_bench
	./bridge_bench

clean:
	rm -f bridge_bench

.PHONY: all run clean
