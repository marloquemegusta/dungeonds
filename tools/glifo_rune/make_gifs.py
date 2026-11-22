#!/usr/bin/env python3
"""Compone los GIFs de evidencia del Glifo a partir de las capturas de los escenarios glifo_* (ultima ejecucion de cada uno):
(glifo_reza.gif sale de glifo_reza_andando: el heroe baja rezando) recorte de la pantalla inferior alrededor de la runa, 4x NEAREST, 50 ms por fotograma (una captura cada 3 frames = 20 fps
reales), y una hoja de contacto por GIF. Escribe en walkthroughs/glifo-pulido/assets/."""
import glob
import json
import os
import sys
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(ROOT, "walkthroughs", "glifo-pulido", "assets")
NAMES = ["glifo_sello", "glifo_sello_redil_zarza", "glifo_sello_radio", "glifo_sello_radio_redil_zarza"]
WALK = "glifo_reza_andando"
CROP = (64, 192, 192, 288)      # pantalla inferior: x 64..192, y 0..96 (la runa esta en (128, 48))
CROP_BIG = (28, 192, 228, 292)  # radio grande: la runa llega a +-80 px
CROP_WALK = (72, 222, 184, 352)  # heroe rezando mientras baja hacia la camara (x 128, y 118 y bajando)


def main():
    os.makedirs(OUT, exist_ok=True)
    for n in ([] if "--walk-only" in sys.argv else NAMES):
        d = sorted(glob.glob(os.path.join(ROOT, "artifacts", "scenarios", n + "-*")))[-1]
        for line in open(os.path.join(d, "events.jsonl"), encoding="utf-8"):
            e = json.loads(line)
            if e.get("action") == "state_capture":
                st = e["state"]
                print(n, e["name"], [(st["e%dx" % i] // 256, st["e%dy" % i] // 256, st["e%dhp" % i], st["e%dburn" % i]) for i in range(4)])
        crop = CROP_BIG if "radio" in n else CROP
        files = sorted(glob.glob(os.path.join(d, n + "_0*.png")))
        fr = [Image.open(f).convert("RGB").crop(crop) for f in files]
        fr = [im.resize((im.width * 4, im.height * 4), Image.NEAREST) for im in fr]
        fr[0].save(os.path.join(OUT, n + ".gif"), save_all=True, append_images=fr[1:], duration=50, loop=0)
        sel = fr[::6][:12]
        tw, th = fr[0].width // 2, fr[0].height // 2
        sheet = Image.new("RGB", (4 * tw, 3 * th))
        for k, im in enumerate(sel):
            sheet.paste(im.resize((tw, th), Image.NEAREST), ((k % 4) * tw, (k // 4) * th))
        sheet.save(os.path.join(OUT, n + "_hoja.png"))
        print(n, len(fr), "frames")
    # Reza andando: una captura por frame, una de cada 3 al GIF (20 fps reales), 4x NEAREST.
    d = sorted(glob.glob(os.path.join(ROOT, "artifacts", "scenarios", WALK + "-*")))[-1]
    files = sorted(glob.glob(os.path.join(d, WALK + "_0*.png")))[::3]
    pr = [Image.open(f).convert("RGB").crop(CROP_WALK) for f in files]
    pr = [im.resize((im.width * 4, im.height * 4), Image.NEAREST) for im in pr]
    pr[0].save(os.path.join(OUT, "glifo_reza.gif"), save_all=True, append_images=pr[1:], duration=50, loop=0)
    print(WALK, len(pr), "frames")


if __name__ == "__main__":
    main()
