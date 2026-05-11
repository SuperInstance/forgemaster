CC      ?= gcc
CFLAGS  ?= -std=c99 -Wall -Wextra -O2 -fPIC
AR      ?= ar
PREFIX  ?= /usr/local

SRC     = src/snapkit.c
HDR     = include/snapkit.h
LIB_STATIC = libsnapkit.a
LIB_SHARED = libsnapkit.so

TEST_BINS = test_eisenstein test_temporal test_spectral

.PHONY: all static shared clean test

all: static shared

static: $(LIB_STATIC)

shared: $(LIB_SHARED)

$(LIB_STATIC): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -Iinclude -c $(SRC) -o snapkit.o
	$(AR) rcs $@ snapkit.o

$(LIB_SHARED): $(SRC) $(HDR)
	$(CC) $(CFLAGS) -Iinclude -shared $(SRC) -o $@ -lm

# Tests
test_eisenstein: tests/test_eisenstein.c $(HDR) $(LIB_STATIC)
	$(CC) $(CFLAGS) -Iinclude tests/test_eisenstein.c -L. -lsnapkit -lm -o $@

test_temporal: tests/test_temporal.c $(HDR) $(LIB_STATIC)
	$(CC) $(CFLAGS) -Iinclude tests/test_temporal.c -L. -lsnapkit -lm -o $@

test_spectral: tests/test_spectral.c $(HDR) $(LIB_STATIC)
	$(CC) $(CFLAGS) -Iinclude tests/test_spectral.c -L. -lsnapkit -lm -o $@

test: test_eisenstein test_temporal test_spectral
	@echo "=== test_eisenstein ===" && LD_LIBRARY_PATH=. ./test_eisenstein
	@echo "=== test_temporal ===" && LD_LIBRARY_PATH=. ./test_temporal
	@echo "=== test_spectral ===" && LD_LIBRARY_PATH=. ./test_spectral
	@echo "All tests passed."

clean:
	rm -f snapkit.o $(LIB_STATIC) $(LIB_SHARED) $(TEST_BINS)

install: all
	install -d $(PREFIX)/lib $(PREFIX)/include
	install -m 644 $(HDR) $(PREFIX)/include/
	install -m 644 $(LIB_STATIC) $(PREFIX)/lib/
	install -m 755 $(LIB_SHARED) $(PREFIX)/lib/
