/* bench_play.h - a second scripted input for tests (built with -DBENCH_PLAY): start a 1-player game, get
 * through the story screens, then play with pseudo-random buttons. The attract demo (the normal bench) presses
 * nothing, so this one covers the controller code and the paths a player reaches. Shared by src/logic.c and
 * tools/nesref/verify.c. Bits: 1 Right, 2 Left, 4 Down, 8 Up, 16 A, 32 B, 64 Start, 128 Select. */
#ifdef BENCH_PLAY
static unsigned short bench_play(unsigned int t)
{
    static const unsigned short pick[12] = { 1, 1 | 16, 1, 32, 2, 8, 4, 4 | 32, 16, 1 | 32, 2 | 16, 0 };
    unsigned int r;
    if (t >= 320 && t <= 325) return 64;
    if (t >= 450 && t <= 455) return 64;
    if (t >= 500 && t < 900) return (t % 20) < 3 ? 16 : 0;
    if (t < 950) return 0;
    r = (t / 24) * 1103515245u + 12345u;        /* a new choice every 24 ticks */
    return pick[(r >> 16) % 12];
}
#endif
