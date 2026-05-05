import array
import board
from rp2pio import StateMachine

import pt1

def _compile(model, s):
    r = []
    sym = model.PUBLIC_LABELS
    i = 0
    while i < len(s):
        c = s[i]
        if c in "HLzi":
            r.append(sym[c])
            i += 1
        elif c.isdigit():
            j = i + 1
            while j < len(s) and s[j].isdigit():
                j += 1
            n = int(s[i:j])
            if n == 0:
                raise ValueError("delay must be greater than zero")
            r.append(sym['Delay'])
            r.append(3 * (n - 1))
            i = j
        elif c.isspace():
            i += 1
        else:
            raise ValueError(f"unexpected character {c!r} at offset {i}")
    return array.array('I', r)

class PulseTrain:
    def __init__(self, pin, freq, read_little_endian = True):
        self.sm = StateMachine(
            pt1.PROGRAM,
            frequency=3 * freq,
            first_in_pin=pin,
            in_pin_count=1,
            first_set_pin=pin,
            set_pin_count=1,
            fifo_type="txrx",
            auto_pull=True,
            pull_threshold=5,
            out_shift_right=True,
            auto_push=True,
            push_threshold=8,
            in_shift_right=read_little_endian,
            **pt1.PIO_KWARGS
        )
        self.model = pt1

    def compile(self, s):
        return _compile(self.model, s)

    def join(self, ss):
        total = sum([len(x) for x in ss])
        out = array.array('I', [0]) * total
        i = 0
        for arr in ss:
            n = len(arr)
            out[i:i+n] = arr
            i += n
        return out

    def source_or_binary(self, x):
        if isinstance(x, str):
            return self.compile(x)
        else:
            return x

    def loop(self, s):
        bb = self.source_or_binary(s) * 100
        self.sm.background_write(loop = bb)

    def drive(self, s):
        self.sm.write(self.source_or_binary(s))

    def read(self, n):
        input_bytes = bytearray(n)
        self.sm.readinto(input_bytes)
        return input_bytes
