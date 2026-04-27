# code.py - CircuitPython on RP2040
# Minimal CH32V003 SWIO debug-register dump using PIO.
#
# Wire RP2040 GP0 to CH32 SWIO/PD1 and share ground. Use 3.3 V only.

import array
import time

import board
from adafruit_pioasm import Program
from rp2pio import StateMachine


SWIO_PIN = board.GP0
PIO_FREQUENCY = 1_000_000

src0 = """
.program pt

main:
    pull block
    set pins, 0
    set pins, 1
    jmp main
public set0:
public set1:
"""


next = """
    pull block
    mov pc, osr
"""
src1 = f"""
.program pt
.origin 0

main:
{next}

public set0:
    set pins, 0
{next}

public set1:
    set pins, 1
{next}
"""

src = src1

print(src)
pt = Program(src)
l = pt.public_labels

rlabels = {o:nm for (nm, o) in l.items()}
for (i,opcode) in enumerate(pt.assembled):
    bb = f"{opcode:016b}"
    insn    = 0x07 & (opcode >> 13)
    delay   = 0x1f & (opcode >> 8)
    f1      = 0x07 & (opcode >> 5)
    f2      = 0x1f & (opcode >> 0)

    if insn == 0:
        cond = ['', '!x', 'x--', '!y', 'y--', 'x!=y', 'pin', '!osre'][f1]
        dis = f"jmp {cond} {f2}"
    elif insn == 5:
        dst = ['pins', 'x', 'y', '?', 'exec', 'pc', 'isr', 'osr'][f1]
        src = ['pins', 'x', 'y', 'NULL', '?', 'status', 'isr', 'osr'][f2 & 7]
        dis = f"mov {dst} {src}"
    else:
        dis = ['jmp', 'wait', 'in', 'out', 'pushpull', 'mov', 'irq', 'set'][insn]
    if i in rlabels:
        print(rlabels[i] + ":")
    print(f"{i:2d} {insn:03b}_{delay:05b}_{f1:03b}_{f2:05b}    {dis}")
print()

sm = StateMachine(
    pt.assembled,
    frequency=PIO_FREQUENCY,
    first_set_pin=SWIO_PIN,
    set_pin_count=1,
    fifo_type="tx",
    **pt.pio_kwargs
)

delay_words = array.array("I", [l['set0'], l['set1']] * 100)
print(f"{delay_words=}")

while True:
    sm.write(delay_words)
