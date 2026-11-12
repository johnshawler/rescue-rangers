# NES → A1200 porting playbook

The accumulated know-how for porting NES games to the Amiga 1200 with this template. **Read it before starting
a NES port, and add to it before finishing one** (section 9). The details of the first port are in
`LEARNINGS.md`; the order of work is in `PIPELINE.md`.

Ports get better only through this file and the tools next to it: a new session remembers nothing else.
To start a new port, see `KICKOFF.md` (with a ready first message). In short: make the new repository from this one ("Use this template" once it is marked as a template,
or a copy) and run `tools/new_port.sh <game> <rom.nes>`: it archives the previous port under `history/`,
resets the per-game files and keeps everything reusable. The Claude skill in `skills/amiga-nes-port/SKILL.md`
(install it in Claude) makes any session start by reading this playbook and end by adding to it.

## 1. What is reusable, what is per game

| Kind | Files | For a new game |
| --- | --- | --- |
| Generic 6502 | `tools/op6502.py`, `tools/dis.py`, `tools/recomp.py`, `tools/back68k.py`, `tools/nesref/verify.c`, `src/coro*.{s,c,h}`, `src/run*.{c,h}`, `src/nes68k.s` (helpers), `src/logic.c` frame model | use as is |
| NES machine | `tools/nesref/nesref.c` (reference NES), `src/nes.{c,h}` (PPU/APU/pad state), `src/video.{c,h}` + `src/video68k.s` (PPU → AGA), `src/sound.{c,h}` (APU → Paula), `tools/vhost.c`, `tools/shost.c` | use; extend for what the game uses |
| Mapper | MMC1 in `nesref.c`, `nes.c`, and the fast paths in `nes68k.s` (`_set_prg`, `_io_wr`) | add the new mapper in all three |
| Per game | `tools/games/<game>.py` (NORETURN, WAITS, SCHEDULER, INDIRECT_BREAKS_CHAIN, SPLIT, hand-written routines), `game_bench_input` in `src/logic.c`, `src/bench_play.h` (a scripted-play test input), the flow traces in `tools/flow/` (`mkin.py` has a mode per game), `tools/make_assets.sh` (ROM check), `NES_PAL` in `port.conf` CFLAGS, `original/README.md` | write new |
| Starting a port | `tools/new_port.sh`, `skills/amiga-nes-port/SKILL.md` | run once / install once |
| Debugging | `tools/test68k.sh` (the Amiga's 68k code on the host under vamos, tick by tick, seconds), `tools/debug_run.sh`, `tools/cmp_trace.py`, `tools/prof.py` (reads the 1 kHz profile), `tools/shot_at.sh`, `src/prof68k.s`, `LOGIC_TRACE`/`LOGIC_NOSUM`/`LOGIC_DUMP`/`HOLD_AT`/`IO_LOG`/`VP_LO`+`VP_HI`/`BENCH_PLAY` builds | use as is |

## 2. Start of a port: the first day

1. `tools/new_port.sh <game> <rom.nes>`, `tools/setup.sh`; check mapper, PRG/CHR sizes, mirroring, 50/60 Hz
   (`tools/make_assets.sh` refuses what the tools do not support yet: section 8). **PAL or NTSC**: European ROMs
   are usually PAL (iNES 2.0 byte 7 bits 2-3 = 2 and byte 12 = 1). `tools/nesref` then runs PAL timing by itself;
   set `TICKS_PER_SECOND` 50 in `src/main.c` and add `-DNES_PAL` to port.conf's CFLAGS (sound clock). A PAL game
   runs one tick per Amiga frame instead of 1.2: 17% more time per tick than an NTSC one.
2. Run the ROM in `tools/nesref` headless; dump frames; find a **self-playing mode** (attract, "watch game",
   demo) for the bench and for coverage. Write the input scripts (`tools/flow/mkin.py`).
3. **Measure the load before anything else**: `WAITPCS=<wait loop addresses> nesref -s` gives 6502 instructions
   per frame outside wait loops. Do it per scene. Then the verdict (section 6). Write it in the feasibility note.
4. Trace (`nesref -c`) attract, self-play and random input; `tools/recomp.py --game <game>` → C and 68k.
5. `tools/nesref/verify.c` against the host test, tick by tick (NES RAM). Then **`tools/test68k.sh`**: the 68k
   translation against the C one, tick by tick, on the host (vamos: `pip install amitools machine68k greenlet`),
   for the attract bench and for `TEST_CFLAGS=-DBENCH_PLAY` (the attract demo never presses a button). Seconds per
   run, and a crash shows with `vamos -I -r`. FS-UAE (`tools/debug_run.sh`) only for timing and pictures.

## 3. NES behaviour the frame model must get right

- **One tick = NMI + main thread until it waits.** Wait loops: no writes, fixed addresses, registers
  redefined each pass (RAM poll → `nes_wait`; `$2002` bit 7 → vblank wait; `$2002` bit 6 → sprite-0 wait).
- **The vblank race**: games poll `$2002` while the NMI also reads it. Model it deterministically: NMI first,
  then the vblank flag set for the poller.
- **Sprite-0 splits**: a toggling hit flag ends the wait in two reads and records the split; what the NMI
  changes after it belongs to the lower part of the picture.
- **Stack tricks** (jump tables after JSR, `PLA PLA RTS`, pushed-address RTS): the 6502 stack stays in RAM,
  RTS compares with the caller's expectation and unwinds. Jump-table dispatchers go in `NORETURN`.
- **Lag**: check with the reference whether the original finishes its logic within each frame in the busy
  scenes. If it doesn't, game time on the NES is slower there and the frame model would need cycle budgets
  (not needed for Little League Baseball).
- **Task schedulers** (Capcom and others): several tasks, each with its own part of the stack page, switched by
  saving S and `TXS`; the scheduler's idle loop is the frame wait but usually writes RAM (`STX $90`), so name it
  in `WAITS` (a loop closed by a `JMP` is supported). A resumed task returns into code whose native caller frame
  is gone: `SCHEDULER = <address>` makes the return point of every call that can reach the scheduler an entry,
  so the top level can dispatch it. Same for `PHA PHA JMP (zp)` pushed-address calls: `INDIRECT_BREAKS_CHAIN`.
- The checksum covers all 2 KB of RAM including the stack page: anything that changes RAM must be exact. It does
  **not** cover the scroll registers, CHR banks or APU state: `host_test -t` prints those too, and
  `tools/test68k.sh` compares them.

## 4. Idioms worth looking for first (the cheap big wins)

Found in the first port; look for them in every game with the profiler (`src/prof68k.s`, busiest scene only):

| Idiom | Signature | What to do |
| --- | --- | --- |
| OAM DMA | `STA $4014` with a RAM page (usually 2) | already a `memcpy` in `nes.c` |
| Controller read | 8× `LDA $4016,x / LSR / ROL` loop, often read twice until equal, edge and hold counters after | hand-write the whole routine (`tools/games/llb.py` $CEBD as template) |
| Mapper serial writes | 5× `STA $8000-$FFFF / LSR` (MMC1) | hand-write: one step when the shift register is idle (template: `_mmc_hle`) |
| PPU data port | `STA $2007` loops in the NMI | nametable fast path in `nes68k.s` (`_io_wr`) |
| Jump table | `ASL A; TAY; PLA; STA; PLA; STA; ... JMP (zp)` after JSR | `NORETURN`; hashed dispatch handles the jumps |
| Shift-and-add multiply | 8 or 16 iterations of `ASL/ROL/ADC` | `mulu` + replay only what decides the stack bytes (template: $C378) |
| Metasprite builder | `LDA (ptr),y` streams into `$0200,x` | hand-write with one pointer (templates: llb $E2DE; rr bank 5 $8193, split off the object routine with `SPLIT`) |
| OAM hide loop | `LDA #$F8; STA $0200,x; INX x4; BNE` | a few lines with a guard for X not a multiple of 4 (rr $C21E) |
| Bank-switch subroutine | `STA save; 5 x (STA $E000-$FFFF; LSR)` | one `_set_prg` call; the same for CHR banks (rr $FF53, $FF1F, $FF39) |
| PPU and APU register writes | `STA $2000/$2001/$2005`, `STA $4000-$4015` | done in `_io_wr` in assembly now (were C calls) |

Hand-written routines: guard them (fall back to `.orig`), reproduce registers, all four flags, RAM and the
return addresses left on the stack page, and prove them with the per-tick checksum.

## 5. Translator rules of thumb

- 68k back end, not C, on the Amiga (C costs 3× more: registers through globals at every call).
- 6502 N/Z in 68k N/Z, C in 68k X; protect only live flags. Use address registers for addresses (no flags).
- RAM indexed tables: the index never crosses $07FF in practice; check with the interpreter and use direct
  addressing. `(zp),y` reads are almost always ROM.
- Any I/O done through C costs ~60–80 instructions; anything done per frame dozens of times belongs in assembly.
- `(zp),y` reads are inlined with a ROM fast path: the pointer sign-extended (`movea.w`) makes $8000-$FFFF
  negative, so one test separates ROM from RAM/I/O and a carry past $FFFF wraps to the zero page by itself.
- 6502 address arithmetic wraps at 16 bits; 68k helpers must too (abs,y and (zp),y past $FFFF land in the zero
  page). Found because a wrapped write reached the MMC1 shift register.
- A peephole drops `SEC`/`CLC` whose X flag is overwritten before it is read (`CLC; ADC` -> `add.b`): ~490 sites.
- Hand-written code for a loop in the middle of a function: `SPLIT = {(bank, address)}` makes it a function of
  its own (falling or branching into it becomes a tail call), then `HLE` it.
- After every translator change: regenerate, then `tools/test68k.sh` on both inputs; C against the interpreter
  (`tools/nesref/verify.c`, also with `-DBENCH_PLAY`) when the C side changed.

## 6. The verdict, before writing code

Translated 6502 code on a 14 MHz 68020 costs about **10–13 colour clocks per 6502 instruction from chip RAM**
(stock A1200) and **about half that from fast RAM**. A frame is 71,051 colour clocks, 57k at the 80% gate, and
a 60 Hz NES game runs 1.2 ticks per 50 Hz frame. So, for the busiest scene:

| 6502 instructions per NES frame | Stock A1200 (logic per frame) | 4 MB fast RAM (logic per frame) |
| --- | --- | --- |
| 2,000 | ~30k: 50 Hz possible | ~15k |
| 5,000 | ~70k: no | ~35k: possible with a cheap display |
| 10,000 | ~140k: no | ~60–70k: only with many hand-written routines |

Add the display (Little League Baseball, 4 MB, field play: 25–35k per frame with ~40 sprites and scrolling;
Rescue Rangers, 4 MB, after the display work: 20–25k per frame with up to 59 sprites).
Say the verdict in the report from the start; name the upgrade.

Measured after the work on the second port (Rescue Rangers, PAL, 5,000–7,500 6502 instructions a frame in play):
about 4 colour clocks per 6502 instruction on 4 MB fast RAM and about 7 on the stock machine. With PAL's one tick
a frame that was 49.1 fps on 4 MB and 36.3 on stock; the table above is the pessimistic first estimate.

## 7. Display and sound recipes

- Background: 4 planes = 16 NES colours (attribute bits as planes 2–3), hardware scroll over an unwrapped world,
  stream tile columns, each tile row at y and y+240 drawing only the shown copy, border columns blank, honour
  PPUMASK's hidden left column. Tile-set-only splits: draw rows with the right tile set.
- Sprites: cluster ≤ 64 px, 64-pixel attached pairs (15 colours), reuse channels down the screen. Three levels of
  reuse, cheapest first: a segment identical to what that slot of that (double-buffered) sprite list held two
  frames ago is left alone; one drawn last frame is copied from the other list; one drawn in the last few dozen
  draws is copied from a shape pool (48 KB, fast RAM when present). Key the shapes on the CHR banks too (a bank
  switch animates sprites without touching OAM). Sprite-behind-background priority is not done yet.
- Per-frame bookkeeping that walks every row or column (row copies for the vertical wrap, border columns) only
  when the scroll or the drawn column range changed.
- Catch-up spirals: when one frame slips, the next pass runs two ticks and slips again until a light tick. The
  late frames come in runs; cut the peak that starts them, not the average.
- Sound: APU model (length, envelope, sweep, linear counter, 240 Hz sequencer) → Paula periods and volumes with
  looped one-period waveforms. `-DNES_PAL` switches the CPU clock and noise table for PAL games. DMC not done
  yet (check first: Rescue Rangers never uses it).
- Develop both on the host harnesses (`tools/vhost.c`, `tools/shost.c`), then confirm on the emulator.

## 8. Not done yet (do it when a game needs it)

Other mappers (UxROM, CNROM, MMC3 with its scanline IRQ); scroll changes at a split; sprite-behind-background;
DMC samples; 8×16 sprites in `video.c` (the reference handles them); lag (cycle budgets); a 68030 bench; a
native coroutine per 6502 task for scheduler games (now every task switch unwinds to the top level and
dispatches); screen builds with the picture off still count as late frames (several per level start).

## 9. Lessons log (append one entry per port, newest last)

Each entry: game, mapper, verdict numbers, what was new, what to do differently next time. Then update the
sections above if a lesson is general.

### 1. Little League Baseball: Championship Series (SNK 1990), MMC1, 2026-11

- Load: 2,000 (batting) to 11,000 (fielding) 6502 instructions per frame; the NES is 95–100% busy fielding.
- Result: 37.2 fps stock, 44.6 fps with 4 or 8 MB fast RAM; 50 Hz in menus and batting on fast RAM; checksum equal.
- New: the whole toolchain (reference NES, two-back-end translator, frame model, display, sound, profiler).
- Biggest wins were I/O plumbing found by the profiler (OAM DMA, controller, MMC1, PPU writes), not game logic.
- Next time: measure the load on day one (it decided the outcome); build the 1 kHz profiler before optimising
  anything; don't trust static cost estimates; write the display on the host harness first.
