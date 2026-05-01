set -e

python gen.py
# python pulsetrain.py

if false
then
  for F in example-neopixel2  example-neopixel example-LHL example-H3L2 example-LHL7HL example-neopixel
  do
    npx wavedrom -i $F.json | npx @resvg/resvg-js-cli - images/$F.png
  done
  # qiv images/example-neopixel2.png
fi

python -m py_compile example.py

ROOT=/media/jamesb/CIRCUITPY/
rm -rf image
mkdir image image/lib/
cp example.py image/code.py
cp pulsetrain.py  pt1.py image/
# cp adafruit_pioasm.mpy image/lib/
rsync -rv --checksum image/ $ROOT/
sync
