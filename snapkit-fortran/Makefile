CC      = gfortran
CFLAGS   = -std=f2008 -Wall -Wextra -Wno-maybe-uninitialized -fcheck=all -g -O2
AR       = ar
ARFLAGS  = rcs

SRC      = $(wildcard src/*.f90)
APP_SRC  = $(wildcard app/*.f90)
TEST_SRC = $(wildcard test/*.f90)

OBJ       = $(SRC:.f90=.o)
APP       = $(APP_SRC:.f90=)
TEST_BINS = $(TEST_SRC:.f90=)

MODULES  = snapkit.mod snap.f90.o delta.f90.o attention.f90.o \
           eisenstein.f90.o topology.f90.o scripts.f90.o \
           learning.f90.o visualization.f90.o

.PHONY: all clean check

all: libsnapkit.a $(APP) $(TEST_BINS)

libsnapkit.a: $(OBJ)
	$(AR) $(ARFLAGS) $@ $^

%.o: %.f90
	$(CC) $(CFLAGS) -c $< -o $@

demo_poker: app/demo_poker.f90 libsnapkit.a
	$(CC) $(CFLAGS) $< -L. -lsnapkit -o $@

demo_learning: app/demo_learning.f90 libsnapkit.a
	$(CC) $(CFLAGS) $< -L. -lsnapkit -o $@

benchmark: app/benchmark.f90 libsnapkit.a
	$(CC) $(CFLAGS) $< -L. -lsnapkit -o $@

test_snapkit: test/run_all.f90 libsnapkit.a
	$(CC) $(CFLAGS) $< -L. -lsnapkit -o $@

check: all test_snapkit
	./test_snapkit

clean:
	rm -f $(OBJ) $(APP) $(TEST_BINS) libsnapkit.a *.mod
	rm -f app/*.o test/*.o
