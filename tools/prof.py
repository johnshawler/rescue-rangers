#!/usr/bin/env python3
"""prof.py <debug dir> [first_tick last_tick] - read the 1 kHz profile of a tools/debug_run.sh run.

prof.bin holds the run-time address of the reset function (translated code hunk) and of game_tick (C code hunk),
then one program counter per millisecond. Symbols come from m68k-amigaos-nm of the debug binary (in Docker);
each hunk is placed by the one symbol whose run-time address is known. frames.bin ((vblank, tick) per drawn
frame) selects the samples of a tick range: sample k was taken about k / 20 vertical blanks after the start.
"""
import struct, subprocess, sys, os, bisect, collections
d = sys.argv[1]
lo, hi = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 1 << 30)
exe = [f for f in os.listdir(d) if f.endswith('_dbg')][0]
raw = open(os.path.join(d, 'prof.bin'), 'rb').read()
base, cbase = struct.unpack('>II', raw[:8]); pcs = struct.unpack('>%dI' % ((len(raw) - 8) // 4), raw[8:])
fr = open(os.path.join(d, 'frames.bin'), 'rb').read(); fr = struct.unpack('>%dI' % (len(fr) // 4), fr)
vb, tk = fr[0::2], fr[1::2]
v0 = vb[0] if vb else 0
nm = subprocess.run(['docker', 'run', '--rm', '-v', os.path.abspath(d) + ':/w', 'amigadev/crosstools:m68k-amigaos',
                     'm68k-amigaos-nm', '-n', '/w/' + exe], capture_output=True, text=True).stdout.split('\n')
syms = []
for l in nm:
    p = l.split()
    if len(p) == 3 and p[1] in 'tT': syms.append((int(p[0], 16), p[2]))
off = {n: a for a, n in syms}
reset_name = [n for n in off if n.startswith('F7_')]
# the translated code: F* and helper symbols, in the hunk of the reset function
gen = sorted((a, n) for a, n in syms if n.startswith(('F', 'D_', '_')) and not n.startswith('__'))
def lookup(table, x):
    i = bisect.bisect_right([a for a, _ in table], x) - 1
    return table[i][1] if i >= 0 else '?'
# find the reset function's offset: the F7 symbol named in prof.bin is the one at 'base'; use _reset_fn's target
rf = subprocess.run(['grep', '-o', r'_reset_fn: dc.l F7_[0-9a-f]*', 'src/gen68k.s'], capture_output=True, text=True).stdout.split()[-1]
gofs = base - off[rf]; cofs = cbase - off['_game_tick']
import re
helpers = set(re.findall(r'^(_[A-Za-z0-9_]+):', open('src/nes68k.s').read(), re.M))    # in the same hunk
ingen = lambda n: n.startswith('F') or n.startswith('D_') or n in helpers
gsyms = sorted((a + gofs, n) for a, n in syms if ingen(n))
csyms = sorted((a + cofs, n) for a, n in syms if not ingen(n))
gk = [a for a, _ in gsyms]; ck = [a for a, _ in csyms]
cnt = collections.Counter(); total = 0
for k, pc in enumerate(pcs):
    v = v0 + k // 20
    i = bisect.bisect_right(vb, v) - 1
    t = tk[i] if i >= 0 else 0
    if not (lo <= t < hi): continue
    total += 1
    gi = bisect.bisect_right(gk, pc) - 1; ci = bisect.bisect_right(ck, pc) - 1
    ga = gk[gi] if gi >= 0 else -1; ca = ck[ci] if ci >= 0 else -1      # whichever symbol is closer below pc
    cnt[(gsyms[gi][1] if ga >= ca else csyms[ci][1]) if max(ga, ca) >= 0 else '?'] += 1
print('samples %d (ticks %d..%d)' % (total, lo, hi))
for n, c in cnt.most_common(40): print('%6.2f%%  %s' % (100.0 * c / max(total, 1), n))
