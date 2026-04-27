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

swio_tx = Program(
    """
.program swio_tx

main:
    pull block; 
    mov x, osr
delay:
    jmp x-- delay
    set pins, 0
    set pins, 1
    jmp main
"""
)
for (i,opcode) in enumerate(swio_tx.assembled):
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
    print(f"{i:2d} {insn:03b}_{delay:05b}_{f1:03b}_{f2:05b}    {dis}")

sm = StateMachine(
    swio_tx.assembled,
    frequency=PIO_FREQUENCY,
    first_set_pin=SWIO_PIN,
    set_pin_count=1,
    fifo_type="tx",
)

delay_words = array.array("I", [0] * 100)

while True:
    sm.write(delay_words)
