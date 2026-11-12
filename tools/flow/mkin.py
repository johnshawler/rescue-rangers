import random, sys
# mkin.py mode frames seed: mode 1p | watch
mode, n, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); r = random.Random(seed)
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
