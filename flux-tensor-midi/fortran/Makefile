# FLUX-Tensor-MIDI Fortran Makefile
# Usage: make       (build all)
#        make test  (build and run tests)
#        make clean

FC = gfortran
FFLAGS = -std=f2008 -Wall -Wextra -O2
SRCDIR = src
TESTDIR = tests
OBJDIR = obj

# Module sources (order matters for Fortran dependencies)
MOD_SRCS = \
  $(SRCDIR)/flux_midi_flux.f90 \
  $(SRCDIR)/flux_midi_clock.f90 \
  $(SRCDIR)/flux_midi_snap.f90 \
  $(SRCDIR)/flux_midi_room.f90 \
  $(SRCDIR)/flux_midi_harmony.f90 \
  $(SRCDIR)/flux_midi_spectrum.f90 \
  $(SRCDIR)/flux_midi_batch.f90

MOD_OBJS = $(MOD_SRCS:$(SRCDIR)/%.f90=$(OBJDIR)/%.o)
MOD_MODS = $(MOD_SRCS:$(SRCDIR)/%.f90=$(OBJDIR)/%.mod)

# Library
LIB = $(OBJDIR)/libflux_midi.a

.PHONY: all test clean

all: $(LIB) test_flux test_clock test_snap test_spectrum

# Build modules
$(OBJDIR)/%.o: $(SRCDIR)/%.f90 | $(OBJDIR)
	$(FC) $(FFLAGS) -J$(OBJDIR) -c $< -o $@

$(OBJDIR):
	mkdir -p $(OBJDIR)

# Static library
$(LIB): $(MOD_OBJS)
	ar rcs $@ $^

# Test programs
test_flux: $(TESTDIR)/test_flux.f90 $(LIB)
	$(FC) $(FFLAGS) -I$(OBJDIR) $< -L$(OBJDIR) -lflux_midi -o $@

test_clock: $(TESTDIR)/test_clock.f90 $(LIB)
	$(FC) $(FFLAGS) -I$(OBJDIR) $< -L$(OBJDIR) -lflux_midi -o $@

test_snap: $(TESTDIR)/test_snap.f90 $(LIB)
	$(FC) $(FFLAGS) -I$(OBJDIR) $< -L$(OBJDIR) -lflux_midi -o $@

test_spectrum: $(TESTDIR)/test_spectrum.f90 $(LIB)
	$(FC) $(FFLAGS) -I$(OBJDIR) $< -L$(OBJDIR) -lflux_midi -o $@

test: all
	@echo "=== Running FLUX-Tensor-MIDI Fortran tests ==="
	./test_flux
	@echo ""
	./test_clock
	@echo ""
	./test_snap
	@echo ""
	./test_spectrum
	@echo ""
	@echo "=== All tests complete ==="

clean:
	rm -rf $(OBJDIR) test_flux test_clock test_snap test_spectrum *.mod
