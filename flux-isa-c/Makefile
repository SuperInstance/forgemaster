CC      ?= gcc
CFLAGS  := -std=c99 -O2 -Wall -Wextra -Werror -fPIC -Iinclude
LDFLAGS := -lm

SRCDIR  := src
OBJDIR  := obj
SRCS    := $(SRCDIR)/vm.c $(SRCDIR)/bytecode.c $(SRCDIR)/disassemble.c
OBJS    := $(patsubst $(SRCDIR)/%.c,$(OBJDIR)/%.o,$(SRCS))

.PHONY: all clean test

all: libflux.a libflux.so

$(OBJDIR)/%.o: $(SRCDIR)/%.c | $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(OBJDIR):
	mkdir -p $(OBJDIR)

libflux.a: $(OBJS)
	ar rcs $@ $^

libflux.so: $(OBJS)
	$(CC) -shared -o $@ $^ $(LDFLAGS)

test: libflux.a
	$(CC) -std=c99 -Wall -Wextra -Werror -Iinclude -o test_runner test/test_vm.c -L. -lflux $(LDFLAGS)
	./test_runner

clean:
	rm -rf $(OBJDIR) libflux.a libflux.so test_runner
