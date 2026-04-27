# rp2040-circuitpython-pulsetrain

This is an experimental CircuitPython module for simpler generation 1-pin pulse trains.

This implementation uses RP2040's PIO, so only runs on RP2040.

```
import pulsetrain as pt

pt = pt.PulseTrain(1_000_000) # 1 Mhz

# A single high 1us pulse
pt.drive("L H L")

# 8 pulses with a 3:2 duty cycle, 5 us cycle time
pt.drive("H 3 L 2" * 8)

# a low-to-high-to-low pulse, then float for 30 us, then sample input. Repeat for 8 bits
pt.drive("L H L _ 30 i" * 8)
```
