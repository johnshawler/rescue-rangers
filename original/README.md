# The game to port

**Chip 'n Dale: Rescue Rangers** (Capcom, 1990) for the NES, **European (PAL) release**. The ROM is
`original/rr.nes`; it is not in the repository (copyrighted; `.gitignore` keeps it and everything made from it
out).

- To build, put the iNES file here as `original/rr.nes` (`Chip 'n Dale - Rescue Rangers (Europe).nes`,
  262,160 bytes, SHA-1 `82595a9e5f20270783c78e7e6ec3449691f57945`), then run `tools/make_assets.sh`.
- Mapper, sizes: MMC1 (mapper 1), 128 KB PRG + 128 KB CHR, CHR in 4 KB banks, vertical mirroring, no PRG RAM.
  iNES 2.0 header with byte 12 = 1: a **PAL** game, 50 frames a second (1,662,607 Hz CPU, 312 lines). One NES
  frame is one Amiga frame: no 6-in-5 tick pattern. `tools/nesref` reads the header and runs PAL timing.
- Program structure: a cooperative task scheduler (Capcom's engine). Four task slots at `$80 + 4n` (status,
  sleep count, saved S or start address). A task yields with `JSR $FF04`/`$FEFD`, which saves S and jumps to the
  scheduler at `$FE8D`; the NMI counts sleeping tasks down; the idle loop `$FE90-$FEA3` is the frame wait. Each
  task has its own part of the stack page and is resumed by `TXS; PLA; TAY; PLA; TAX; RTS`. See
  `tools/games/rr.py`.
- Display: no sprite-0 split and no scroll split; the status bar (faces, hearts, flower boxes) is made of
  sprites. Background tile banks change only between levels; sprite tile banks change rarely.
- Sound: two pulses, triangle and noise. No DMC samples (only the reset writes `$4010` = 0).
- Self-playing mode for the bench: the attract demo. With no input, from tick ~950 Chip and Dale play level 1 by
  themselves for minutes, scrolling right and up past the mechanical dogs, apples and crates. Up to 59 of the 64
  NES sprites are on screen (ticks ~1270-1330).
- Controls on the NES: pad, A (jump), B (pick up / throw), Start (title, pause). Start on the title screen, Start
  again to choose Chip or Dale, A to page through the story.
- Load (6502 instructions per frame outside the scheduler's idle loop, reference NES, PAL): title 1,300-2,300;
  attract-demo gameplay 4,700-7,500; level loading up to 11,000 (with the screen off).
- Running it without a window: `tools/nesref/nesref.c` runs the ROM headless with scripted input and dumps
  frames:

      cc -O2 tools/nesref/nesref.c -o nesref
      ./nesref original/rr.nes 3000 -d 1000,2000 -o /tmp
      WAITPCS=fe90,fe92,fe94,fe96,fe98,fe9a,fe9c,fe9d,fe9e,fe9f,fea0,fea1,fea3 ./nesref original/rr.nes 3000 -s

The previous port's description is in history/llb/original-README.md.
