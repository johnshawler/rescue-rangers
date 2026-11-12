# Development pipeline, reprioritised

What this port taught (see `LEARNINGS.md`) changes the order of work. Part A replaces the milestone order of
BRIEF.md Step 4 for ports of translated binaries (NES/6502 and similar); the gates and the referee
(`tools/port.sh`) are unchanged. Part B is the prioritised backlog for this port.

## Why the order changes

- The deciding number came last in the brief's order: how busy the original CPU is. It is measurable on day one
  with a reference emulator, and it alone decided that 50 Hz on a stock machine was out of reach.
- Correctness tooling paid for itself many times over: every translator bug was found in minutes by "first tick
  that differs, then a RAM dump". Built late, every bug would have been a guess.
- The cheapest large wins were I/O plumbing (OAM DMA, controller, mapper, PPU writes), found only with an
  unbiased profiler. Static cost estimates pointed the wrong way several times.
- Display bugs were found on the host harness, not in the emulator.

## Part A: milestone order for a translated-binary port

| # | Milestone | Gate | Was |
| --- | --- | --- | --- |
| 1 | Reference emulator of the original machine, headless, scripted input, frame dumps | Frames match the real game's screens | new |
| 2 | **Load measurement**: original CPU instructions per frame by scene (exclude wait loops) | Number per scene, written into the feasibility note | new |
| 3 | Feasibility note with the load: instructions/frame × 10–13 colour clocks (stock, chip RAM) or ×5–6 (fast RAM) + the display budget of Step 2, against 57k (80%) | Honest verdict per machine *before* code is written | 1 |
| 4 | Kit skeleton builds and benches | `late=0` | 2 |
| 5 | Traces → static translation to C; frame model (waits, NMI, coroutine) | Translated C equals an instruction interpreter tick by tick for ≥ 20,000 ticks | 3 |
| 6 | Asset script (ROM split, translation) with no manual step | `tools/make_assets.sh` from the ROM alone | 4 |
| 7 | 68k back end (registers in registers, 6502 flags in 68k flags, liveness) | Amiga checksum = host checksum for every tick of the bench | 8 (moved up) |
| 8 | Debug tooling on the Amiga: per-tick checksum and RAM dump, per-tick time, **1 kHz CIA profiler**, per-frame (vblank, tick) log | Profile of the busiest scene names its top routines | new |
| 9 | I/O fast paths and hand-written hot routines, chosen by the profiler, each guarded and proven by the checksum | Logic per tick in the busiest scene within its share of the budget | new |
| 10 | Host display harness (fake kit calls → PPM) | Screens match the reference emulator's | new |
| 11 | Background, scrolling, splits | Harness screenshots, then emulator screenshots, match | 5, 6 |
| 12 | Sprites (hardware first, multiplexed if needed) | No dropped clusters on the harness over the bench | 7 |
| 13 | Display cost: profile the display in the busiest scene, cut instruction count (not memory traffic) | Display + logic under 80% in the busiest scene | new |
| 14 | Sound | Still the same `late` | 9 |
| 15 | Final bench on stock and fast RAM | The brief's gates; report | 10 |

Rules that come with it:
- Measure before optimising, and only in the busiest scene. Re-measure after every change; keep the checksum
  equal after every change.
- If milestone 3 says the stock machine cannot hold 50 Hz, say so in the report early and target the cheapest
  upgrade explicitly. Don't spend days on the stock machine.

## Part B: backlog for this port (Rescue Rangers)

Status: see REPORT.txt. Busiest passages of the attract demo on 4 MB fast RAM: logic ~24k colour clocks a tick,
display ~24k a frame (sprite grouping ~6.6k, drawing new shapes ~6.4k), 71k available. The late frames left are
level-start screen builds (the picture is off) and short catch-up runs in the busiest passages.

| Priority | Item | Expected gain | Effort | How to know it worked |
| --- | --- | --- | --- | --- |
| 1 | Sprite grouping, channel assignment and signatures in assembly (`build_groups`, `assign`, `group_sig`) | -4k per frame | medium | `video.txt` grouping figure (`-DVP_LO=1270 -DVP_HI=1335`); `tools/vhost.c` pictures identical |
| 2 | Draw only the used width of a new sprite shape (most groups are 16-32 px wide, the lists are 64) | -2-3k per frame when shapes change | medium | `video.txt` drawing figure |
| 3 | A native coroutine per 6502 task (switch C stacks at TXS on a saved task S): no unwinding to the top level and no hashed dispatch at every task switch | -1-2k per tick | medium | `_dispatch`/`_unwind` share in `tools/prof.py` |
| 4 | Hand-written collision helper `F7_eb3b` and the object loop `F5_802f` head; then re-profile | -1k per tick each | medium | `ticktime.bin` in the busy window; `tools/test68k.sh` both inputs |
| 5 | Screen builds: keep the last picture (or black) and build the new screen over several frames without counting them late (needs a kit-side notion of "picture off") | the start-up and level-start late frames | small, kit question | `late` in `bench.txt` |
| 6 | Measure a 68030 accelerator (FS-UAE accelerator options) and report it | the honest "cheapest upgrade" number | small | a third bench line in REPORT.txt |
| 7 | Show sprites in the 32-pixel borders / narrow the display window | cosmetic | needs kit support | screenshot |
| 8 | Listen to the sound on the emulator with audio; play-test with a person | quality | small | by ear; a written note |
