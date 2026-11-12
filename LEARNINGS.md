# Learnings from porting Chip 'n Dale: Rescue Rangers (NES, PAL) to the A1200

The second NES port with this template (the first: history/llb/LEARNINGS.md). What was new, what it cost, and the
numbers. The general part is folded into `PLAYBOOK-NES.md`; the brief's gaps are in `NOTES.md`; the result is in
`REPORT.txt`.

## 1. The game, measured before any code

- MMC1, 128 KB PRG + 128 KB CHR: the board the tools already supported, so the first day went into the frame
  model, not a mapper.
- **PAL.** The European ROM has an iNES 2.0 header with byte 12 = 1. The reference NES ran NTSC timing only; with
  PAL timing (312 lines, 106.5 CPU cycles a line, 70 lines of vertical blank) the game runs at 50 frames a
  second, so one NES frame is one Amiga frame. That alone gives each tick 17% more time than an NTSC game's.
- Load (6502 instructions a frame outside the idle loop): title 1,300-2,300, attract-demo gameplay 4,700-7,500,
  level loading up to 11,000 with the screen off. The verdict written before code: stock no (50k-100k of logic
  against a 57k gate), 4 MB fast RAM borderline. It ended at 36.3 fps stock and 49.1 fps on 4 MB.
- The attract demo is a good bench: from tick ~950 both chipmunks play level 1 for minutes with no input,
  scrolling both ways, with up to 59 of the 64 NES sprites on screen.

## 2. A task scheduler instead of a main loop

- Capcom's engine: four task slots at `$80`, each task with its own part of the stack page. A task yields with
  `JSR $FF04` (save X, Y and S, `JMP $FE8D`); the scheduler resets S, scans the slots, and resumes a ready task
  with `TXS; PLA; TAY; PLA; TAX; RTS`. The NMI counts sleeping tasks down.
- The idle loop (`$FE90-$FEA3`) is the frame wait, but it writes `$90` on every pass and closes with a `JMP`, so
  the static detection rejected it. `WAITS` in the game file names it; all three implementations (C back end,
  68k back end, the interpreter in `verify.c`) accept a wait closed by a `JMP`.
- A resumed task returns into code whose native (C or 68k) caller frame belongs to another task or is gone. The
  translation already handled that (return upward, dispatch at the top level), but only for addresses that are
  entries. `SCHEDULER` makes the return point of every call that can reach the scheduler an entry (66 yielding
  functions, 55 return points). A pushed-address call (`PHA PHA JMP ($0000)` at bank 6 `$8016`) loses frames the
  same way: `INDIRECT_BREAKS_CHAIN` (now 191 return points). Then C = interpreter for 20,000 ticks.
- Not done: a native coroutine per task. Each task switch unwinds to the top level and goes through the hashed
  dispatch; it shows as 1-2% in the profile.

## 3. Bugs the first port never hit

All three were in shared code (`src/nes68k.s`, `tools/back68k.py`), latent since Little League Baseball:

| Symptom | Cause | Found with |
| --- | --- | --- |
| Amiga build hangs at tick 5 | `_io_wr_d2` (STY to an I/O address) fell through into `_set_prg` and returned with the registers it had pushed still on the stack | vamos instruction trace (`vamos -I -r`) |
| Checksum differs at tick 958 | `CMP (zp),y` through a helper: `move.b d0,d4; sub.b d4,d4` compared the operand with itself | RAM diff at that tick, gdb watchpoint on the host, then reading the 68k |
| Bank switch to bank 0 at tick 2980 | `abs,y` / `(zp),y` past `$FFFF` did not wrap: the address became $10069, and a write meant for the zero page went to the MMC1 shift register | `IO_LOG` build: the last tick's I/O writes on both sides, diffed |

**The new tool that made these quick: `tools/test68k.sh`.** It builds the host test with the Amiga compiler around
`src/gen68k.s` (no hardware is touched) and runs it under vamos (amitools' AmigaOS emulator) on the host: 20,000
ticks in about a minute, the 68k checksum after every tick compared with the C translation, plus state the
checksum does not cover (scroll, CHR banks, APU triggers). An FS-UAE run is 2-3 minutes and shows nothing when it
hangs.

## 4. What bought speed (colour clocks; logic per tick, display per frame; attract demo gameplay)

| Change | Stock fps | 4 MB fps | Effect measured |
| --- | --- | --- | --- |
| First correct build | 25.1 | 41.5 | logic 49.6k stock / 29.3k fast, display ~59k / 32k |
| Sprite cache keyed on the CHR banks (a bug fix); segments already in place not copied | | | display 32k -> 26.6k (fast) |
| `(zp),y` ROM fast path inline; APU writes in assembly; OAM hide `$C21E` by hand | 29.8 | 46.5 | logic 29.4k -> 27.1k |
| MMC1 routines `$FF53/$FF1F/$FF39` and the controller `$C162` by hand | | | logic 27.1k -> 23.2k |
| Linked-list sprite grouping, shape pool, cheaper signature, dead-carry peephole | 31.1 | 48.2 | display 26.6k -> 21-22k |
| Metasprite emission loop (bank 5 `$8193`, split off with `SPLIT`) by hand | | | logic in the busiest passage 29.0k -> 24.5k |
| Grouping in registers; row/edge checks only when the scroll moved | 36.3 | 49.1 | display in the busiest passage 27k -> 24.4k |
| PPU register writes in assembly | 36.4 | 49.1 | |
| Longer traces (more entries; same logic) | 36.3 | 49.1 | final referee run (`tools/port.sh`, `tools/port.sh fast`) |

- Again the I/O plumbing paid first: bank switches (30 serial mapper writes a tick), the controller, OAM and APU
  writes. Then one game loop that runs once per NES sprite.
- On the stock machine every change helped about twice as much in colour clocks as on fast RAM: instruction
  fetch from chip RAM is the cost.

## 5. The display

- The first port's display worked unchanged for this game (vertical mirroring, 4 KB CHR banks, no split).
- **Sprite reuse** was the big display win, in three levels: the same segment in the same slot of the same
  (double-buffered) list as two frames ago is not touched at all (about three quarters of all segments over the bench); one drawn
  last frame is copied from the other list; one drawn recently comes from a 48 KB shape pool (a third of the
  rest). Signatures must include the CHR banks: the status bar's faces changed by bank switch with the same OAM.
- Grouping costs as much as drawing now (6-7k each in the busiest passage on 4 MB). It is C over 64 OAM entries
  every frame; assembly is the next step.
- Catch-up spirals: the late frames in gameplay come in runs. One frame slips, the next pass runs two ticks and
  slips again, until a light tick. Cutting the peak that starts a run removed whole runs at once.
- The NES picture is 256 pixels in a 320-pixel view; columns that leave the NES picture keep their content in the
  border. Left border shows a little more of the level; sprites never appear there.

## 6. Measuring

- `tools/prof.py` reads the 1 kHz profile. Lesson: `nm` gives offsets per hunk, so only symbols of the hunk whose
  base is known may be mixed; the first version mapped C samples onto translated functions and pointed at the
  wrong routines.
- `VP_LO`/`VP_HI` move the display timers onto the busiest passage (ticks 1270-1335 here); a whole-run average
  hides it.
- `callgrind` on the host display harness (`tools/vhost.c`) finds the hot lines of `video.c` quickly; x86 counts
  are only a guide for the 68k.

## 7. What I would do next

See `PIPELINE.md` part B: grouping and signatures in assembly, drawing only the used width of new shapes, a
native coroutine per task, then the next hand-written game routines from the busiest-passage profile.
