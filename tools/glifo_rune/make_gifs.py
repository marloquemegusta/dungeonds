#!/usr/bin/env python3
"""Compone los GIFs de evidencia del Glifo a partir de las capturas de los escenarios glifo_* (ultima ejecucion de cada uno):
recorte de la pantalla inferior alrededor de la runa, 4x NEAREST, 50 ms por fotograma (una captura cada 3 frames = 20 fps
reales), y una hoja de contacto por GIF. Escribe en walkthroughs/glifo-diseno/assets/rom/."""
import glob
import json
import os
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "walkthroughs", "glifo-diseno", "assets", "rom")
NAMES = ["glifo_sello", "glifo_sello_redil", "glifo_sello_zarza", "glifo_sello_redil_zarza"]
CROP = (64, 192, 192, 288)      # pantalla inferior: x 64..192, y 0..96 (la runa esta en (128, 48))


def main():
    os.makedirs(OUT, exist_ok=True)
    for n in NAMES:
        d = sorted(glob.glob(os.path.join(ROOT, "artifacts", "scenarios", n + "-*")))[-1]
        for line in open(os.path.join(d, "events.jsonl"), encoding="utf-8"):
            e = json.loads(line)
            if e.get("action") == "state_capture":
                st = e["state"]
                print(n, e["name"], [(st["e%dx" % i] // 256, st["e%dy" % i] // 256, st["e%dhp" % i], st["e%dburn" % i]) for i in range(4)])
        fr = [Image.open(f).convert("RGB").crop(CROP).resize((512, 384), Image.NEAREST)
              for f in sorted(glob.glob(os.path.join(d, n + "_0*.png")))]
        fr[0].save(os.path.join(OUT, n + ".gif"), save_all=True, append_images=fr[1:], duration=50, loop=0)
        sel = fr[::6][:12]
        sheet = Image.new("RGB", (4 * 256, 3 * 192))
        for k, im in enumerate(sel):
            sheet.paste(im.resize((256, 192), Image.NEAREST), ((k % 4) * 256, (k // 4) * 192))
        sheet.save(os.path.join(OUT, n + "_hoja.png"))
        print(n, len(fr), "frames")


if __name__ == "__main__":
    main()
