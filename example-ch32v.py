import array
import time
import struct

import board
import pulsetrain

DEG_Abst_DATA0     = 0x04
DEG_Abst_DATA1     = 0x05

DEG_Module_CTRL    = 0x10
DEG_Module_STA     = 0x11
DEG_Hart_INFO      = 0x12

DEG_Abst_STA       = 0x16
DEG_Abst_CMD       = 0x17
DEG_Abst_CMDAUTO   = 0x18

DEG_Prog_BUF0      = 0x20
DEG_Prog_BUF1      = 0x21
DEG_Prog_BUF2      = 0x22
DEG_Prog_BUF3      = 0x23
DEG_Prog_BUF4      = 0x24
DEG_Prog_BUF5      = 0x25
DEG_Prog_BUF6      = 0x26
DEG_Prog_BUF7      = 0x27

DEG_Hart_SUM0      = 0x40

ONLINE_CAPR_STA    = 0x7C
ONLINE_CFGR_MASK   = 0x7D
ONLINE_CFGR_SHAD   = 0x7E

class CH32VDebug:
    def __init__(self, pin=board.GP0):
        self.pt = pulsetrain.PulseTrain(pin, freq=4_000_000, read_little_endian = False)
        self.seq = array.array("I")

        # Source-to-target bits:
        #   0: 750 ns low, 250 ns high.
        #   1: 250 ns low, 250 ns high.
        # Target-to-source bit:
        #   pull low 250ns, wait, sample, then let the
        #   target release the line before the next bit.

        self.bit0 = pulsetrain.compile(self.pt.model, "L 2 H")
        self.bit1 = pulsetrain.compile(self.pt.model, "L H")

        self.readbit = pulsetrain.compile(self.pt.model, "L z i 2")

        # 2 us is 8 ticks
        self.packet_gap = pulsetrain.compile(self.pt.model, "H 8")

        self.reset()
        self.swio_write_reg(0x7E, 0x5AA50400)
        self.swio_write_reg(0x7D, 0x5AA50400)
        self.swio_write_reg(0x10, 0x80000001)

    def reset(self):
        # How low for 2 milliseconds (8000 ticks @ 4 MHz)
        self.pt.drive("L 8000 H")

    #
    # packet construction
    #

    def clear(self):
        self.seq = array.array("I")

    def append(self, seq):
        self.seq.extend(seq)

    def drive(self):
        self.pt.drive(self.seq)

    def _bits_msb_first(self, value, width):
        for bit in range(width - 1, -1, -1):
            yield (value >> bit) & 1

    def _send_nbit(self, x, n):
        for bit in self._bits_msb_first(x, n):
            self.append(self.bit1 if bit else self.bit0)

    def swio_write_reg(self, address, value):
        print(f"Write {address:x} {value:x}")
        self.clear()
        self.append(self.bit1)  # start bit
        self._send_nbit(address, 7)
        self.append(self.bit1)  # write
        self._send_nbit(value, 32)
        self.append(self.packet_gap)
        self.drive()

    def swio_read_reg(self, address):
        self.clear()
        self.append(self.bit1)  # start bit
        self._send_nbit(address, 7)
        self.append(self.bit0)  # read
        for _ in range(32):
            self.append(self.readbit)
        self.append(self.packet_gap)
        self.drive()

        rx = self.pt.read(4)
        return struct.unpack(">I", rx)[0]

debug = CH32VDebug()

for r in (0x10, 0x7e, 0x7d, 0x10):
    print("%02x: %08x" % (r, debug.swio_read_reg(r)))

debug.swio_write_reg(DEG_Abst_DATA0, 0x94700947)
for i in range(5):
    print("%02x: %08x" % (DEG_Abst_DATA0, debug.swio_read_reg(DEG_Abst_DATA0)))
while True:
    time.sleep(1)
