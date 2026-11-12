"""rr.py - what the translator needs to know about Chip 'n Dale: Rescue Rangers (Capcom 1990, NES, Europe/PAL,
MMC1) that it cannot find out by itself. Loaded by tools/recomp.py (--game rr). See tools/games/llb.py for a
filled-in example and PLAYBOOK-NES.md sections 3-5 for how to find each entry.

The game is a cooperative task scheduler (Capcom's engine): four task slots at $80 + 4n (status, sleep count,
saved S / start address). Tasks yield with JSR $FEFD (sleep X frames), which saves S and jumps to the scheduler at
$FE8D; the NMI ($C0A1) counts sleeping tasks down and marks them ready (status 4). The scheduler resumes a task by
TXS + PLA/TAY/PLA/TAX/RTS, i.e. by switching to that task's part of the stack page.
"""
NORETURN = set()        # subroutines that pop their own return address (jump-table dispatchers)
HLE = {}                # (bank, address): hand-written 68k text, exact, proven by the checksum
HLE_FALLBACK = set()    # entries of HLE whose text may branch to .orig

# Wait loops the static detection cannot accept. The scheduler's idle loop $FE90-$FEA3 scans the four task
# slots for status >= 4 and writes $90 = 0 on every pass (so it is not "write-free"); it closes with JMP $FE90.
# On the NES only the NMI can end it. (bank, address of the jump back): (kind, loop start)
WAITS = {(7, 0xfea3): ('RAM', 0xfe90)}
SCHEDULER = 0xfe8d     # tasks yield by jumping here (from $FF04 and $FEED); see recomp.py
INDIRECT_BREAKS_CHAIN = True   # PHA PHA JMP ($00) at bank 6 $8016: pushed-address returns
