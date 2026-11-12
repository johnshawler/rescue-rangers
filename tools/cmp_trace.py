#!/usr/bin/env python3
"""cmp_trace.py <trace.bin> - first tick where the Amiga's per-tick checksums (tools/debug_run.sh) differ from
the host test's (out/host_test N -t, built from port.conf's HOST_TEST)."""
import struct, subprocess, sys
d = open(sys.argv[1], 'rb').read(); a = struct.unpack('>%dI' % (len(d) // 4), d)
h = subprocess.run(['out/host_test', str(len(a)), '-t'], capture_output=True, text=True).stdout.split('\n')
h = [int(l.split()[1], 16) for l in h if l and l[0].isdigit() and len(l.split()) == 2]
for i, (x, y) in enumerate(zip(a, h)):
    if x != y: print('first difference at tick %d: amiga %08x host %08x' % (i + 1, x, y)); sys.exit(1)
print('equal for %d ticks' % min(len(a), len(h)))
