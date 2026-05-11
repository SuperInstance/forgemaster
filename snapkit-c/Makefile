#
# SnapKit Makefile
#
# Targets:
#   make              Build static library (libsnapkit.a)
#   make shared       Build shared library (libsnapkit.so)
#   make test         Build and run tests
#   make benchmark    Build and run benchmarks
#   make examples     Build example programs
#   make all          Build library + tests + examples
#   make doxygen      Generate Doxygen docs
#   make install      Install to PREFIX (/usr/local)
#   make clean        Remove build artifacts
#   make valgrind     Run tests under valgrind
#
# Cross-compilation:
#   make CROSS_COMPILE=arm-none-eabi- CC=arm-none-eabi-gcc AR=arm-none-eabi-ar
#
# Header-only mode:
#   #define SNAPKIT_HEADER_ONLY 1 before including snapkit.h
#

# ========== Configuration ==========

CC       ?= gcc
AR       ?= ar
CFLAGS   ?= -O3 -march=native -mtune=native
CFLAGS   += -std=c11 -Wall -Wextra -Wpedantic -Werror -fPIC
CFLAGS   += -Iinclude -Isrc
LDFLAGS  ?=
LDLIBS   ?= -lm

# Installation prefix
PREFIX   ?= /usr/local
LIBDIR   ?= $(PREFIX)/lib
INCDIR   ?= $(PREFIX)/include

# Cross-compilation prefix (set via env, e.g., CROSS_COMPILE=arm-none-eabi-)
ifdef CROSS_COMPILE
    CC := $(CROSS_COMPILE)gcc
    AR := $(CROSS_COMPILE)ar
    CFLAGS += --specs=nano.specs
endif

# Debug build
ifdef DEBUG
    CFLAGS := -O0 -g -ggdb3 -fsanitize=address -fno-omit-frame-pointer \
              $(filter-out -O3 -march=native -mtune=native, $(CFLAGS))
    CFLAGS += -DSNAPKIT_DEBUG
endif

# Profiling build
ifdef PROFILE
    CFLAGS += -pg -g
    LDFLAGS += -pg
endif

# ========== Sources ==========

SRCDIR := src
BUILDDIR := build

SRC_CORE := \
    $(SRCDIR)/core_ade.c \
    $(SRCDIR)/core_eisenstein.c \
    $(SRCDIR)/core_snap.c \
    $(SRCDIR)/core_delta.c

OBJS := $(patsubst $(SRCDIR)/%.c, $(BUILDDIR)/%.o, $(SRC_CORE))

LIB_STATIC := $(BUILDDIR)/libsnapkit.a
LIB_SHARED := $(BUILDDIR)/libsnapkit.so

TESTDIR := tests
TEST_SRC := $(TESTDIR)/test_snapkit.c
TEST_BIN := $(BUILDDIR)/test_snapkit

BENCH_SRC := $(TESTDIR)/bench_snapkit.c
BENCH_BIN := $(BUILDDIR)/bench_snapkit

EXAMPLES := $(BUILDDIR)/example_eisenstein $(BUILDDIR)/example_delta

# ========== Targets ==========

.PHONY: all static shared test benchmark examples doxygen install uninstall clean valgrind

all: static shared test examples

static: $(LIB_STATIC)
shared: $(LIB_SHARED)

# Build rules

$(BUILDDIR):
	mkdir -p $(BUILDDIR)

$(BUILDDIR)/%.o: $(SRCDIR)/%.c include/snapkit/snapkit.h include/snapkit/snapkit_internal.h | $(BUILDDIR)
	$(CC) $(CFLAGS) -c -o $@ $<

$(LIB_STATIC): $(OBJS)
	$(AR) rcs $@ $^
	@echo "Built: $(LIB_STATIC)"

$(LIB_SHARED): $(OBJS)
	$(CC) -shared -o $@ $^ $(LDFLAGS) $(LDLIBS)
	@echo "Built: $(LIB_SHARED)"

# Tests

test: $(TEST_BIN)
	@echo ""
	@echo "=== SnapKit Test Suite ==="
	@echo ""
	$(TEST_BIN)
	@echo ""
	@echo "=== All tests passed ==="

$(TEST_BIN): $(TEST_SRC) $(LIB_STATIC) | $(BUILDDIR)
	$(CC) $(CFLAGS) -o $@ $< -L$(BUILDDIR) -lsnapkit $(LDFLAGS) $(LDLIBS)
	@echo "Built: $(TEST_BIN)"

# Benchmarks

benchmark: $(BENCH_BIN)
	@echo ""
	@echo "=== SnapKit Benchmark ==="
	@echo ""
	$(BENCH_BIN)

$(BENCH_BIN): $(BENCH_SRC) $(LIB_STATIC) | $(BUILDDIR)
	$(CC) $(CFLAGS) -o $@ $< -L$(BUILDDIR) -lsnapkit $(LDFLAGS) $(LDLIBS)
	@echo "Built: $(BENCH_BIN)"

# Examples

examples: $(EXAMPLES)

$(BUILDDIR)/example_eisenstein: examples/example_eisenstein.c $(LIB_STATIC) | $(BUILDDIR)
	$(CC) $(CFLAGS) -o $@ $< -L$(BUILDDIR) -lsnapkit $(LDFLAGS) $(LDLIBS)
	@echo "Built: $@"

$(BUILDDIR)/example_delta: examples/example_delta.c $(LIB_STATIC) | $(BUILDDIR)
	$(CC) $(CFLAGS) -o $@ $< -L$(BUILDDIR) -lsnapkit $(LDFLAGS) $(LDLIBS)
	@echo "Built: $@"

# Doxygen

DOXYFILE := Doxyfile
DOXYDIR := docs/doxygen

doxygen: $(DOXYFILE)
	@mkdir -p $(DOXYDIR)
	doxygen $(DOXYFILE)
	@echo "Doxygen docs generated in $(DOXYDIR)/"

$(DOXYFILE):
	@echo "Generating Doxyfile..."
	@doxygen -g $(DOXYFILE) > /dev/null 2>&1 || true
	@sed -i 's|^PROJECT_NAME[ ]*=.*|PROJECT_NAME           = "SnapKit"|' $(DOXYFILE)
	@sed -i 's|^PROJECT_NUMBER[ ]*=.*|PROJECT_NUMBER        = $(SNAPKIT_VERSION)|' $(DOXYFILE)
	@sed -i 's|^INPUT[ ]*=.*|INPUT                  = include/snapkit/ src/'|' $(DOXYFILE)
	@sed -i 's|^OUTPUT_DIRECTORY[ ]*=.*|OUTPUT_DIRECTORY      = docs/doxygen|' $(DOXYFILE)
	@sed -i 's|^RECURSIVE[ ]*=.*|RECURSIVE             = YES|' $(DOXYFILE)
	@sed -i 's|^EXTRACT_ALL[ ]*=.*|EXTRACT_ALL          = YES|' $(DOXYFILE)
	@sed -i 's|^GENERATE_LATEX[ ]*=.*|GENERATE_LATEX        = NO|' $(DOXYFILE)

# Install

install: static shared
	install -d $(LIBDIR)
	install -d $(INCDIR)/snapkit
	install -d $(LIBDIR)/pkgconfig
	install -d $(LIBDIR)/cmake/snapkit
	install -m 644 $(LIB_STATIC) $(LIBDIR)/
	install -m 755 $(LIB_SHARED) $(LIBDIR)/
	install -m 644 include/snapkit/*.h $(INCDIR)/snapkit/
	# pkg-config
	sed 's|@PREFIX@|$(PREFIX)|g' snapkit.pc.in > $(LIBDIR)/pkgconfig/snapkit.pc
	# CMake
	sed -e 's|@PACKAGE_INIT@|set(PACKAGE_INCLUDE_DIR "$(INCDIR)")|g' \
	    -e 's|@PACKAGE_INCLUDE_DIR@|$(INCDIR)|g' \
	    -e 's|@PACKAGE_LIBRARY_DIR@|$(LIBDIR)|g' \
	    snapkit-config.cmake.in > $(LIBDIR)/cmake/snapkit/snapkit-config.cmake
	ldconfig || true
	@echo "Installed SnapKit to $(PREFIX) (lib -> $(LIBDIR), headers -> $(INCDIR)/snapkit/)"

uninstall:
	rm -f $(LIBDIR)/libsnapkit.a
	rm -f $(LIBDIR)/libsnapkit.so
	rm -rf $(INCDIR)/snapkit
	@echo "Uninstalled SnapKit from $(PREFIX)"

# Clean

clean:
	rm -rf $(BUILDDIR) docs/doxygen
	@echo "Cleaned."

# Valgrind

valgrind: $(TEST_BIN)
	valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes \
	         --error-exitcode=1 $(TEST_BIN)
	@echo "Valgrind: no memory errors or leaks"

# Dependency tracking

-include $(OBJS:.o=.d)

%.d: %.c
	@$(CC) -MM -MT $(@:.d=.o) $(CFLAGS) $< > $@

# Help

help:
	@echo "SnapKit Build System"
	@echo ""
	@echo "make           Build static library"
	@echo "make shared    Build shared library"
	@echo "make test      Build and run tests"
	@echo "make benchmark Build and run benchmarks"
	@echo "make examples  Build example programs"
	@echo "make all       Build everything"
	@echo "make doxygen   Generate documentation"
	@echo "make install   Install to $(PREFIX)"
	@echo "make clean     Remove build artifacts"
	@echo "make valgrind  Run tests under valgrind"
	@echo ""
	@echo "Options:"
	@echo "  DEBUG=1       Enable debug build (ASan, -O0)"
	@echo "  PROFILE=1     Enable profiling (-pg)"
	@echo "  CROSS_COMPILE=arm-none-eabi-  Cross-compile for ARM"
