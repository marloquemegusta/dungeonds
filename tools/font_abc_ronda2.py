#!/usr/bin/env python3
"""Ronda 2 de tipografia: HTML con capturas reales (antes/despues) de menu, HUD, controles y codice.
Uso: font_abc_ronda2.py <dir_antes> <dir_despues> <salida.html>"""
import sys, os, io, base64
from PIL import Image

A, D, OUT = sys.argv[1:4]

def crop(p):
    return Image.open(p).convert('RGB').crop((0, 192, 256, 384)).resize((1024, 768), Image.NEAREST)

def b64(im):
    b = io.BytesIO(); im.save(b, 'PNG'); return base64.b64encode(b.getvalue()).decode()

items = [
 ('Pausa: botones y textos del HUD',
  'Los botones pasan de MAYÚSCULAS en 5×7 a Palatino con tilde.',
  [('Hoy', os.path.join(A, 'menu_inicial_pausa', '04_pausa.png')),
   ('Palatino', os.path.join(D, 'menu_inicial_pausa', '04_pausa.png'))]),
 ('HUD en partida',
  'Altura y tiempo abajo, Enc. 1 de 14 arriba. Fíjate en cómo se lee de reojo sobre el suelo con textura.',
  [('Hoy', os.path.join(A, 'demo_hud_hearts', '01_after_3s_alive.png')),
   ('Palatino', os.path.join(D, 'demo_hud_hearts', '01_after_3s_alive.png'))]),
 ('Controles (solo Palatino)', 'Ahora con tildes y minúsculas.',
  [('', os.path.join(D, 'extra', '14_controles.png'))]),
 ('Ficha del Códice (solo Palatino)', 'Con la fuente elegida en la ronda 1.',
  [('', os.path.join(D, 'extra', '15_codice.png'))]),
]
h = ['<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Tipografía ronda 2</title>'
     '<style>body{background:#0b0b0b;color:#ddd;font:15px Georgia,serif;max-width:760px;margin:auto;padding:16px}'
     'h1{font-size:20px}h2{font-size:16px;margin:26px 0 4px;color:#e8dcc0}p{color:#aaa;font-size:14px;margin:2px 0 8px}'
     'img{width:100%;image-rendering:pixelated;border:1px solid #333;display:block;margin-bottom:10px}b{color:#e8dcc0}</style>'
     '<h1>Tipografía: ronda 2, menú y HUD</h1><p>Capturas reales de la ROM (pantalla inferior, 4×).</p>']
for t, d, ps in items:
    h.append(f'<h2>{t}</h2><p>{d}</p>')
    for lab, p in ps:
        if lab: h.append(f'<p><b>{lab}</b></p>')
        h.append('<img src="data:image/png;base64,' + b64(crop(p)) + '">')
open(OUT, 'w', encoding='utf-8').write('\n'.join(h))
print('ok')
