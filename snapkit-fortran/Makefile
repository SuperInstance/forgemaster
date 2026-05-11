CC       = gfortran
CFLAGS   = -std=f2008 -Wall -Wextra -ffree-line-length-none -fcheck=all -g -O2
AR       = ar
ARFLAGS  = rcs

SRC       = src/snapkit.f90 src/eisenstein.f90 src/snap.f90 \
            src/delta.f90 src/attention.f90 src/topology.f90 \
            src/scripts.f90 src/learning.f90 src/visualization.f90
OBJ       = $(SRC:.f90=.o)

APP_SRC   = app/demo_poker.f90 app/demo_learning.f90 app/benchmark.f90
APP       = app/demo_poker app/demo_learning app/benchmark

TEST_OBJ  = test/test_eisenstein.o test/test_snap.o test/test_delta.o \
            test/test_attention.o test/test_topology.o test/run_all.o

.PHONY: all clean check

all: libsnapkit.a $(APP) test/test_runner

# Build order respects module dependencies
src/snapkit.o: src/snapkit.f90
	$(CC) $(CFLAGS) -c $< -o $@

src/eisenstein.o: src/eisenstein.f90 src/snapkit.o
	$(CC) $(CFLAGS) -c $< -o $@

src/snap.o: src/snap.f90 src/snapkit.o src/eisenstein.o
	$(CC) $(CFLAGS) -c $< -o $@

src/delta.o: src/delta.f90 src/snapkit.o src/snap.o
	$(CC) $(CFLAGS) -c $< -o $@

src/attention.o: src/attention.f90 src/snapkit.o
	$(CC) $(CFLAGS) -c $< -o $@

src/topology.o: src/topology.f90 src/snapkit.o
	$(CC) $(CFLAGS) -c $< -o $@

src/scripts.o: src/scripts.f90 src/snapkit.o
	$(CC) $(CFLAGS) -c $< -o $@

src/learning.o: src/learning.f90 src/snapkit.o
	$(CC) $(CFLAGS) -c $< -o $@

src/visualization.o: src/visualization.f90 src/snapkit.o src/snap.o \
                     src/delta.o src/attention.o
	$(CC) $(CFLAGS) -c $< -o $@

libsnapkit.a: $(OBJ)
	$(AR) $(ARFLAGS) $@ $^

app/demo_poker: app/demo_poker.o libsnapkit.a
	$(CC) $(CFLAGS) app/demo_poker.o -L. -lsnapkit -o $@

app/demo_learning: app/demo_learning.o libsnapkit.a
	$(CC) $(CFLAGS) app/demo_learning.o -L. -lsnapkit -o $@

app/benchmark: app/benchmark.o libsnapkit.a
	$(CC) $(CFLAGS) app/benchmark.o -L. -lsnapkit -o $@

test/test_runner: $(TEST_OBJ) libsnapkit.a
	$(CC) $(CFLAGS) $(TEST_OBJ) -L. -lsnapkit -o $@

%.o: %.f90
	$(CC) $(CFLAGS) -c $< -o $@

check: all test/test_runner
	./test/test_runner

clean:
	rm -f $(OBJ) $(APP_OBJ) $(TEST_OBJ) libsnapkit.a *.mod
	rm -f src/*.o app/*.o test/*.o
	rm -f app/demo_poker app/demo_learning app/benchmark test/test_runner
