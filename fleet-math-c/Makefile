CC       = gcc
CFLAGS   = -O3 -march=native -Wall -Wextra -pedantic
LDFLAGS  = -lm

TEST_SRC = test/test_fleet_math.c
TEST_BIN = test_fleet_math

.PHONY: all test clean

all: $(TEST_BIN)

$(TEST_BIN): $(TEST_SRC) include/fleet_math.h
	$(CC) $(CFLAGS) -Iinclude $(TEST_SRC) -o $(TEST_BIN) $(LDFLAGS)

test: $(TEST_BIN)
	./$(TEST_BIN)

# Also compile a standalone example
example: example.c include/fleet_math.h
	$(CC) $(CFLAGS) example.c -o example $(LDFLAGS)

clean:
	rm -f $(TEST_BIN) example *.o
