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

CH32V003_FLASH_BASE = 0x08000000
CH32V003_FLASH_SIZE = 16 * 1024
CH32V003_FLASH_PAGE_SIZE = 1024
CH32V003_SRAM_TOP = 0x20000800
CSR_DPC = 0x7B1

FLASH_BASE = 0x40022000
FLASH_KEYR = FLASH_BASE + 0x04
FLASH_STATR = FLASH_BASE + 0x0C
FLASH_CTLR = FLASH_BASE + 0x10
FLASH_ADDR = FLASH_BASE + 0x14

FLASH_KEY1 = 0x45670123
FLASH_KEY2 = 0xCDEF89AB

FLASH_STATR_BSY = 1 << 0
FLASH_STATR_WRPRTERR = 1 << 4
FLASH_STATR_EOP = 1 << 5

FLASH_CTLR_PG = 1 << 0
FLASH_CTLR_PER = 1 << 1
FLASH_CTLR_STRT = 1 << 6
FLASH_CTLR_LOCK = 1 << 7

CH32V003_R_32BIT = (
    0x7b251073,
    0x7b359073,
    0xe0000537,
    0x0f852583,
    0x2a23418c,
    0x25730eb5,
    0x25f37b20,
    0x90027b30,
)

CH32V003_W_32BIT = (
    0x7b251073,
    0x7b359073,
    0xe0000537,
    0x0f852583,
    0x0f452503,
    0x2573c188,
    0x25f37b20,
    0x90027b30,
)

CH32V003_W_16BIT = (
    0x7b251073,
    0x7b359073,
    0xe0000537,
    0x0f852583,
    0x0f452503,
    0x00a59023,
    0x7b202573,
    0x7b3025f3,
)


class CH32VDebug:
    def __init__(self, pin=board.GP0):
        self.pt = pulsetrain.PulseTrain(pin, freq=4_000_000, read_little_endian = False)
        self.seq = array.array("I")
        self.prog_buf = None

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
        self.enter_pause_mode()

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
        # print(f"Write {address:x} {value:x}")
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

    def check_module_status(self, mask, value):
        for _ in range(200):
            status = self.swio_read_reg(DEG_Module_STA)
            if status != 0xFFFFFFFF and (status & mask) == value:
                return status
            time.sleep(0.003)

        raise RuntimeError("module status timed out: %08x" % status)

    def enter_pause_mode(self):
        self.swio_write_reg(DEG_Module_CTRL, 0x80000001)
        self.swio_write_reg(DEG_Module_CTRL, 0x80000001)
        self.check_module_status(3 << 8, 3 << 8)
        self.swio_write_reg(DEG_Module_CTRL, 0x00000001)

    #
    # abstract command helpers
    #

    def check_abstract_status(self):
        for _ in range(200):
            status = self.swio_read_reg(DEG_Abst_STA)
            if status & (1 << 12):
                time.sleep(0.001)
                continue

            error = (status >> 8) & 0x7
            if error:
                self.swio_write_reg(DEG_Abst_STA, 0xFFFFFFFF)
                raise RuntimeError("abstract command failed: %08x" % status)
            return status

        raise RuntimeError("abstract command timed out")

    def load_program_buffer(self, words):
        if self.prog_buf != words:
            for offset, word in enumerate(words):
                self.swio_write_reg(DEG_Prog_BUF0 + offset, word)
            self.prog_buf = words

    def exec_program_buffer(self):
        self.swio_write_reg(DEG_Abst_CMD, 1 << 18)
        self.check_abstract_status()

    def read_u32(self, address):
        self.swio_write_reg(DEG_Abst_DATA1, address)
        self.load_program_buffer(CH32V003_R_32BIT)
        self.exec_program_buffer()
        return self.swio_read_reg(DEG_Abst_DATA0)

    def write_u32(self, address, value):
        self.swio_write_reg(DEG_Abst_DATA0, value)
        self.swio_write_reg(DEG_Abst_DATA1, address)
        self.load_program_buffer(CH32V003_W_32BIT)
        self.exec_program_buffer()

    def write_u16(self, address, value):
        self.swio_write_reg(DEG_Abst_DATA0, value & 0xFFFF)
        self.swio_write_reg(DEG_Abst_DATA1, address)
        self.load_program_buffer(CH32V003_W_16BIT)
        self.exec_program_buffer()

    def write_u16_with_loaded_program(self, address, value):
        self.swio_write_reg(DEG_Abst_DATA0, value & 0xFFFF)
        self.swio_write_reg(DEG_Abst_DATA1, address)
        self.exec_program_buffer()

    def write_gpr(self, register, value):
        self.swio_write_reg(DEG_Abst_DATA0, value)
        self.swio_write_reg(DEG_Abst_CMD, 0x00231000 | register)
        self.check_abstract_status()

    def write_csr(self, register, value):
        self.swio_write_reg(DEG_Abst_DATA0, value)
        self.swio_write_reg(DEG_Abst_CMD, 0x00230000 | register)
        self.check_abstract_status()

    #
    # flash loader
    #

    def wait_flash(self):
        for _ in range(1000):
            status = self.read_u32(FLASH_STATR)
            if status & FLASH_STATR_BSY:
                time.sleep(0.001)
                continue

            if status & FLASH_STATR_WRPRTERR:
                raise RuntimeError("flash write-protect error: %08x" % status)

            if status & FLASH_STATR_EOP:
                self.write_u32(FLASH_STATR, FLASH_STATR_EOP)
            return status

        raise RuntimeError("flash operation timed out")

    def unlock_flash(self):
        if self.read_u32(FLASH_CTLR) & FLASH_CTLR_LOCK:
            self.write_u32(FLASH_KEYR, FLASH_KEY1)
            self.write_u32(FLASH_KEYR, FLASH_KEY2)

        control = self.read_u32(FLASH_CTLR)
        if control & FLASH_CTLR_LOCK:
            raise RuntimeError("flash controller is still locked: %08x" % control)

    def erase_flash_page(self, address):
        print("erase %08x" % address)
        self.wait_flash()
        self.write_u32(FLASH_CTLR, FLASH_CTLR_PER)
        self.write_u32(FLASH_ADDR, address)
        self.write_u32(FLASH_CTLR, FLASH_CTLR_PER | FLASH_CTLR_STRT)
        self.wait_flash()
        self.write_u32(FLASH_CTLR, 0)

    def program_flash(self, address, data):
        print("program %d bytes at %08x" % (len(data), address))
        self.wait_flash()
        self.write_u32(FLASH_CTLR, FLASH_CTLR_PG)
        self.load_program_buffer(CH32V003_W_16BIT)

        if len(data) & 1:
            data += b"\xff"

        for offset in range(0, len(data), 2):
            if offset and offset % 256 == 0:
                print("programmed %04x/%04x" % (offset, len(data)))
            halfword = data[offset] | (data[offset + 1] << 8)
            self.write_u16_with_loaded_program(address + offset, halfword)

        self.wait_flash()
        self.write_u32(FLASH_CTLR, 0)

    def verify_flash(self, address, data):
        if len(data) & 3:
            data += b"\xff" * (4 - (len(data) & 3))

        for offset in range(0, len(data), 4):
            expected = struct.unpack_from("<I", data, offset)[0]
            actual = self.read_u32(address + offset)
            if actual != expected:
                raise RuntimeError(
                    "verify failed at %08x: got %08x expected %08x"
                    % (address + offset, actual, expected)
                )
        print("verify ok")

    def load_flash_image(self, path, address=CH32V003_FLASH_BASE):
        with open(path, "rb") as f:
            data = f.read()

        self.unlock_flash()

        erase_size = ((len(data) + CH32V003_FLASH_PAGE_SIZE - 1) // CH32V003_FLASH_PAGE_SIZE) * CH32V003_FLASH_PAGE_SIZE
        for offset in range(0, erase_size, CH32V003_FLASH_PAGE_SIZE):
            self.erase_flash_page(address + offset)

        self.program_flash(address, data)
        self.verify_flash(address, data)

    def reset_core(self):
        self.swio_write_reg(DEG_Module_CTRL, 0x00000003)
        self.check_module_status(3 << 18, 3 << 18)
        self.swio_write_reg(DEG_Module_CTRL, 0x00000001)
        self.swio_write_reg(DEG_Module_CTRL, 0x10000001)
        self.check_module_status(3 << 18, 0)

    def exit_pause_mode(self):
        self.swio_write_reg(DEG_Module_CTRL, 0x80000001)
        self.swio_write_reg(DEG_Module_CTRL, 0x80000001)
        self.swio_write_reg(DEG_Module_CTRL, 0x00000001)
        self.swio_write_reg(DEG_Module_CTRL, 0x40000001)
        self.check_module_status(3 << 10, 3 << 10)

    def run(self, entry=0, stack=CH32V003_SRAM_TOP):
        print("run entry=%08x stack=%08x" % (entry, stack))
        self.write_gpr(2, stack)
        self.write_csr(CSR_DPC, entry)
        self.exit_pause_mode()

    def dump_flash_hex(self, base=CH32V003_FLASH_BASE, size=CH32V003_FLASH_SIZE):
        for offset in range(0, size, 16):
            words = []
            for word_offset in range(0, min(16, size - offset), 4):
                words.append(self.read_u32(base + offset + word_offset))

            data = bytearray()
            for word in words:
                data.extend(struct.pack("<I", word))

            hex_bytes = " ".join("%02x" % b for b in data)
            print("%08x: %s" % (base + offset, hex_bytes))


debug = CH32VDebug()
debug.load_flash_image("blink-small.bin")
debug.run()

while True:
    time.sleep(1)
