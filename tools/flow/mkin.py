import random, sys
# mkin.py mode frames seed: mode 1p | watch
mode, n, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); r = random.Random(seed)
if mode == 'rrplay':    # the same buttons as src/bench_play.h (BENCH_PLAY), for tools/nesref traces
    names = {1: 'RIGHT', 2: 'LEFT', 4: 'DOWN', 8: 'UP', 16: 'B', 32: 'A', 64: 'START', 128: 'SELECT'}
    pick = [1, 1 | 32, 1, 16, 2, 8, 4, 4 | 16, 32, 1 | 16, 2 | 32, 0]
    def bp(t):
        if 320 <= t <= 325 or 450 <= t <= 455: return 64
        if 500 <= t < 900: return 32 if t % 20 < 3 else 0
        if t < 950: return 0
        r = ((t // 24) * 1103515245 + 12345) & 0xffffffff
        return pick[(r >> 16) % 12]
    out, t = [], 0
    while t < n:
        b, u = bp(t), t
        while u + 1 < n and bp(u + 1) == b: u += 1
        if b: out.append('%d %d %s' % (t, u, ' '.join(v for k, v in sorted(names.items()) if b & k)))
        t = u + 1
    print('\n'.join(out)); sys.exit(0)
if mode == 'rr':        # Rescue Rangers: start a 1-player game, then mostly run right and jump, some throws
    out, f = ['320 325 START', '450 455 START'] + ['%d %d %s' % (k, k + 3, 'A') for k in range(500, 900, 20)], 950
    while f < n:
        if False: out.append('%d %d START' % (f, f + 4)); f += 20; continue
        d = r.randint(5, 60)
        b = r.choice(['RIGHT', 'RIGHT A', 'RIGHT', 'B', 'LEFT', 'UP', 'DOWN', 'DOWN B', 'A', 'RIGHT B', 'LEFT A', ''])
        if b: out.append('%d %d %s' % (f, f + d, b))
        f += d + r.randint(1, 10)
    print('\n'.join(out)); sys.exit(0)
out = ['100 105 START', '200 205 DOWN', '250 255 A']
if mode == 'watch': out += ['330 335 DOWN', '360 365 DOWN', '400 405 A']
else: out += ['400 405 A']
f = 500
while f < n:
    if mode == 'watch':
        if r.random() < 0.2: out.append('%d %d A' % (f, f + 4))
        f += r.randint(40, 120); continue
    d = r.randint(3, 40)
    b = r.choice(['A', 'B', 'A', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'A LEFT', 'A RIGHT', 'B UP', 'START', 'SELECT', '', '', ''])
    if b: out.append('%d %d %s' % (f, f + d, b))
    f += d + r.randint(1, 30)
print('\n'.join(out))
