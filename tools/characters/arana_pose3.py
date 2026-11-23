"""Hoja de comprobacion de apoyos: perfil, frente y arriba con linea de suelo z=0, zoom a manos y pies y la foto de referencia.
Uso: python tools/characters/arana_pose3.py <prefijo_diag> <salida.png>"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[2]
pre = sys.argv[1]; S = 384
pj = json.load(open(pre + '_proj.json'))
sh = Image.new('RGB', (S * 4, S * 3), (128, 128, 128)); dr = ImageDraw.Draw(sh)
ref = Image.open(ROOT / 'walkthroughs/arpg-exvoto-ramas/assets/arana/referencia_puente.jpg').convert('RGB'); ref.thumbnail((S, S)); sh.paste(ref, (0, 0))
imgs = {}
for v in ('perfil', 'frente0', 'arriba', 'SE'):
    im = Image.open(f'{pre}_{v}.png').convert('RGB'); d = ImageDraw.Draw(im)
    if v in ('perfil', 'frente0'):
        y = pj[v]['suelo'][1]; d.line((0, y, 512, y), fill=(255, 0, 0), width=1)
    imgs[v] = im
for i, v in enumerate(('perfil', 'frente0', 'arriba')):
    sh.paste(imgs[v].resize((S, S), Image.LANCZOS), ((i + 1) * S, 0)); dr.text(((i + 1) * S + 4, 4), v + ' (rojo = suelo z=0)', fill=(255, 255, 0))
sh.paste(imgs['SE'].resize((S, S), Image.LANCZOS), (0, S)); dr.text((4, S + 4), 'SE', fill=(255, 255, 0))
def crop(v, key, x, y, lab, r=64):
    cx, cy = pj[v][key]; box = (int(cx - r), int(cy - r), int(cx + r), int(cy + r))
    sh.paste(imgs[v].crop(box).resize((S, S), Image.LANCZOS), (x * S, y * S)); dr.text((x * S + 4, y * S + 4), lab, fill=(255, 255, 0))
crop('perfil', 'manoI', 1, 1, 'manos perfil'); crop('perfil', 'pieD', 2, 1, 'pies perfil'); crop('frente0', 'manoI', 3, 1, 'mano frente')
crop('frente0', 'pieI', 1, 2, 'pie frente'); crop('frente0', 'manoD', 2, 2, 'mano D frente'); crop('frente0', 'pieD', 3, 2, 'pie D frente')
sh.save(sys.argv[2])
