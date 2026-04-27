set -e

python -m py_compile main.py

ROOT=/media/jamesb/CIRCUITPY/
rm -rf image
mkdir image image/lib/
cp main.py image/code.py
cp adafruit_pioasm.mpy image/lib/
rsync -rv --checksum image/ $ROOT/
sync
