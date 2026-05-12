FC      = gfortran
FFLAGS  = -O2 -Wall -Wextra -std=f2008 -fcheck=all
AR      = ar
ARFLAGS = rcs

SRCDIR  = src
TSTDIR  = tests
LIBDIR  = lib
BINDIR  = bin

SRCS    = $(SRCDIR)/eisenstein.f90 $(SRCDIR)/voronoi.f90 \
          $(SRCDIR)/spectral.f90 $(SRCDIR)/temporal.f90
LIB     = $(LIBDIR)/libsnapkit.a

TESTS   = $(BINDIR)/test_eisenstein $(BINDIR)/test_spectral

.PHONY: all clean test

all: $(LIB) $(TESTS)

$(LIBDIR):
	mkdir -p $(LIBDIR)

$(BINDIR):
	mkdir -p $(BINDIR)

# Build library from source modules
$(LIB): $(SRCS) | $(LIBDIR)
	$(FC) $(FFLAGS) -c $^ -J$(LIBDIR)
	$(AR) $(ARFLAGS) $@ *.o
	rm -f *.o

# Build test executables
$(BINDIR)/test_eisenstein: $(TSTDIR)/test_eisenstein.f90 $(LIB) | $(BINDIR)
	$(FC) $(FFLAGS) -I$(LIBDIR) $< -L$(LIBDIR) -lsnapkit -o $@

$(BINDIR)/test_spectral: $(TSTDIR)/test_spectral.f90 $(LIB) | $(BINDIR)
	$(FC) $(FFLAGS) -I$(LIBDIR) $< -L$(LIBDIR) -lsnapkit -o $@

test: $(TESTS)
	@echo "=== Running test_eisenstein ==="
	$(BINDIR)/test_eisenstein
	@echo "=== Running test_spectral ==="
	$(BINDIR)/test_spectral
	@echo "=== All tests passed ==="

clean:
	rm -rf $(LIBDIR) $(BINDIR) *.o *.mod
