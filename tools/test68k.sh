#!/bin/bash
# Usage: tools/test68k.sh <ticks> - the Amiga's 68k translation, run on the host: the host test (src/host_test.c)
# built with the Amiga compiler around src/gen68k.s instead of the C translation, run under vamos (amitools'
# AmigaOS emulator: pip install amitools machine68k greenlet). No hardware is touched, so no emulator is needed.
# Compares the checksum after every tick with the C translation (out/host_test) and prints the first difference.
# TEST_CFLAGS=-DBENCH_PLAY uses the scripted-play input (src/bench_play.h) on both sides.
# Seconds instead of minutes, and a crash shows up with vamos -I (instruction trace).
cd "$(dirname "$0")/.."
. ./port.conf
N="${1:-3000}"
CFLAGS="-Isrc $TEST_CFLAGS" tools/build.sh "dist/${NAME}68t" src/host_test.c src/host_render.c src/logic.c src/nes.c src/run68k.c src/coro.s src/gen68k.s 2>&1 | grep -i "error" && exit 1
mkdir -p out
cc -O1 -w $HOST_CFLAGS $TEST_CFLAGS $HOST_TEST -o out/host_test || exit 1
vamos -q -C 68020 -m 8192 -s 64 -- "dist/${NAME}68t" "$N" -t > out/t68.txt; echo "vamos exit code $?"
./out/host_test "$N" -t > out/tc.txt
python3 - <<'PY'
a = [l.split() for l in open('out/t68.txt') if l[:1].isdigit()]
c = [l.split() for l in open('out/tc.txt') if l[:1].isdigit()]
for x, y in zip(a, c):
    if x != y: print('first difference at tick %s: 68k %s, C %s' % (x[0], x[1], y[1])); break
else: print('68k equal to C for %d ticks (C ran %d)' % (len(a), len(c)))
PY
