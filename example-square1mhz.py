import board
import pulsetrain
import random
import time
        
pin = board.GP15
pt = pulsetrain.PulseTrain(pin, freq=2_000_000)
# pt.loop("H999L999")
pt.loop("H1L1")
while 1:
    pass
