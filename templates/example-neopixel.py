import board
import pulsetrain
import random
import time
        
pin = board.GP0
pt = pulsetrain.PulseTrain(pin, freq=2_500_000)

if 0:
    bits = ["HLL", "HHL"]
    reset = "H L 150 H"
    print(f"{reset=}")
    pt.drive("H")
    while 1:
        pt.drive(reset + "".join([random.choice(bits) for i in range(24 * 10)]) + "H")
else:
    bits = [pt.compile(p) for p in ["HLL", "HHL"]]
    reset = pt.compile("H L 150 H")
    def rgb(cc):
        # incoming RGB, neopixels use GRB
        cc = ((cc & 0xff0000) >> 8) | ((cc & 0x00ff00) << 8) | (cc & 0x0000ff)
        return pt.join([bits[1 & (cc >> (23 - i))] for i in range(24)])
    colors = [rgb(0xffffff), rgb(0xff0000), rgb(0x00ff00), rgb(0x0000ff), rgb(0xff8000)]
    while 1:
        t0 = time.monotonic()
        pt.drive(pt.join([random.choice(colors) for i in range(60)] + [reset]))
        t1 = time.monotonic()
        print(round(t1 - t0, 4))
