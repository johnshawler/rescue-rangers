"""rr.py - what the translator needs to know about Chip 'n Dale: Rescue Rangers (Capcom 1990, NES, Europe/PAL,
MMC1) that it cannot find out by itself. Loaded by tools/recomp.py (--game rr). See tools/games/llb.py for a
filled-in example and PLAYBOOK-NES.md sections 3-5 for how to find each entry.

The game is a cooperative task scheduler (Capcom's engine): four task slots at $80 + 4n (status, sleep count,
saved S / start address). Tasks yield with JSR $FEFD (sleep X frames), which saves S and jumps to the scheduler at
$FE8D; the NMI ($C0A1) counts sleeping tasks down and marks them ready (status 4). The scheduler resumes a task by
TXS + PLA/TAY/PLA/TAX/RTS, i.e. by switching to that task's part of the stack page.
"""
NORETURN = set()        # subroutines that pop their own return address (jump-table dispatchers)
HLE = {                 # (bank, address): hand-written 68k text, exact, proven by the checksum
    # $C21E: hide the OAM entries from $97 on: LDX $97 / (X = 4: $0200 = $F8) / STA $0200,X += 4 until X wraps.
    # Leaves A = $F8, X = 0, N = 0, Z = 1, C and V as they were. X not a multiple of 4 never ends: .orig.
    (7, 0xc21e): """
    moveq #0,d1
    move.b $97-$80(a5),d1
    move.b d1,d4
    and.b #3,d4
    bne .orig
    cmp.b #4,d1
    bne.s .h1
    move.b #$f8,$200-$80(a5)
.h1 lea $200-$80(a5,d1.w),a0
    lea $300-$80(a5),a1
    move.b #$f8,d0
.h2 move.b d0,(a0)
    addq.l #4,a0
    cmpa.l a1,a0
    bcs.s .h2
    moveq #0,d1
""",
}
HLE_FALLBACK = {(7, 0xc21e)}    # entries of HLE whose text may branch to .orig

# Wait loops the static detection cannot accept. The scheduler's idle loop $FE90-$FEA3 scans the four task
# slots for status >= 4 and writes $90 = 0 on every pass (so it is not "write-free"); it closes with JMP $FE90.
# On the NES only the NMI can end it. (bank, address of the jump back): (kind, loop start)
WAITS = {(7, 0xfea3): ('RAM', 0xfe90)}
SCHEDULER = 0xfe8d     # tasks yield by jumping here (from $FF04 and $FEED); see recomp.py
INDIRECT_BREAKS_CHAIN = True   # PHA PHA JMP ($00) at bank 6 $8016: pushed-address returns

# The game's MMC1 routines: "STA store; (INC $F5;) five times STA reg / LSR (four LSRs); then LDA #0; STA flag".
# Done in one step when the shift register is idle and A has no reset bit; else the translation (.orig).
# Effects: the register gets A & $1F, the carry is bit 3 of A, A ends 0 (N = 0, Z = 1), X Y V unchanged.
def _mmc(store, setreg, tail):
    return '\n'.join(['    btst #7,d0', '    bne .orig', '    cmp.b #$10,_mmc_shift', '    bne .orig'] + tail[0] +
                     ['    move.b d0,$%x-$80(a5)' % s for s in store] +
                     ['    moveq #$1f,d4', '    and.b d0,d4'] + setreg + ['    lsr.b #4,d0'] + tail[1] + ['    moveq #0,d0'])
# $FF53: PRG bank. STA $F1 / STA $F4 / INC $F5 / five writes / LDA #0 / STA $F5 / LDA $F6 / BNE (a sound call
# the NMI deferred: never pending here, .orig if it is) / RTS: A = $F6 = 0.
HLE[(7, 0xff53)] = _mmc((0xf1, 0xf4), ['    bsr _set_prg'],
                        (['    tst.b $f6-$80(a5)', '    bne .orig'], ['    clr.b $f5-$80(a5)']))
# $FF1F / $FF39: tile sets 0 and 1. STA $F2 (or $F3) / five writes / LDA #0 / STA $1A (or $1B) / RTS.
HLE[(7, 0xff1f)] = _mmc((0xf2,), ['    move.b d4,_mmc_chr0', '    move.b #$10,_mmc_shift'], ([], ['    clr.b $1a-$80(a5)']))
HLE[(7, 0xff39)] = _mmc((0xf3,), ['    move.b d4,_mmc_chr1', '    move.b #$10,_mmc_shift'], ([], ['    clr.b $1b-$80(a5)']))
HLE_FALLBACK |= {(7, 0xff53), (7, 0xff1f), (7, 0xff39)}

# $C162: read both controllers (strobe, 8 x $4016 and $4017, LSR/ROL into $14 $00 / $15 $01), new presses in
# $14/$15 and held buttons in $16/$17, then clear up+down and left+right pairs in $14-$17. Port 2 reads 0 here.
# Ends with X = $FF (N = 1, Z = 0), Y = the buttons held, A and the carry from the last pair test on $14.
HLE[(7, 0xc162)] = """
    moveq #0,d4
    move.b _nes_pad,d4
    move.b (_revtab,d4.w),d4
    move.b #$ff,_pad_shift
    clr.b _pad_strobe
    clr.b $00-$80(a5)
    clr.b $01-$80(a5)
    clr.b $15-$80(a5)
    clr.b $17-$80(a5)
    moveq #0,d2
    move.b d4,d2
    move.b $16-$80(a5),d7
    eor.b d4,d7
    and.b d4,d7
    moveq #$0c,d6
    and.b d4,d6
    cmp.b #$0c,d6
    beq.s .c1
    moveq #3,d6
    and.b d4,d6
    cmp.b #3,d6
    bne.s .c2
.c1 and.b #$f0,d4
.c2 move.b d4,$16-$80(a5)
    move.b d7,$14-$80(a5)
    moveq #$0c,d0
    and.b d7,d0
    cmp.b #$0c,d0
    beq.s .c3
    moveq #3,d0
    and.b d7,d0
    cmp.b #3,d0
    beq.s .c3
    andi.b #$ef,ccr
    bra.s .c4
.c3 move.b d7,d0
    and.b #$f0,d0
    move.b d0,$14-$80(a5)
    ori.b #$10,ccr
.c4 moveq #0,d1
    move.b #$ff,d1
"""
