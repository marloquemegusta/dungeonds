"""GIFs de evidencia ARANA: columnas andar B vigente | arana a 4x NEAREST sobre gris medio, 8 ticks/frame (~133 ms) + hoja 8x8.
Uso: python tools/characters/arana_gifs.py <salida_dir>"""
import sys
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
ar = Image.open(ROOT / "assets/staging/super_monja_arana/bake/exvoto_super_monja/spritesheet.png").convert("RGBA")
bb = Image.open(ROOT / "assets/staging/super_monja_anim/B/exvoto_super_monja/spritesheet.png").convert("RGBA")
C, Z, G = 56, 4, (128, 128, 128, 255)
names = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
def cell(im, d, f): return im.crop((f * C, d * C, f * C + C, d * C + C)).resize((C * Z, C * Z), Image.NEAREST)
for d in (0, 7, 6):
    fr = []
    for f in range(8):
        im = Image.new("RGBA", (C * Z * 2, C * Z), G)
        im.alpha_composite(cell(bb, d, f)); im.alpha_composite(cell(ar, d, f), (C * Z, 0))
        fr.append(im.convert("RGB"))
    fr[0].save(out / f"arana_andar_{names[d]}.gif", save_all=True, append_images=fr[1:], duration=133, loop=0, disposal=2)
hoja = Image.new("RGBA", (C * Z * 8, C * Z * 8), G)
for d in range(8):
    for f in range(8):
        hoja.alpha_composite(cell(ar, d, f), (f * C * Z, d * C * Z))
hoja.save(out / "arana_hoja.png")
