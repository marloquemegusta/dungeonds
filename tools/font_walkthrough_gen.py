#!/usr/bin/env python3
"""Genera walkthroughs/tipografia/walkthrough.md y assets/tipografia_antes_despues.html
a partir de assets/comparativa/NN_<nombre>_{antes,despues}.png. Uso: font_walkthrough_gen.py <dir tipografia>"""
import sys, os, io, base64
from PIL import Image

ROOT = sys.argv[1]
CMP = os.path.join(ROOT, 'assets', 'comparativa')

# (id, titulo, que cambia / observacion para el usuario)
PAIRS = [
 ('01_titulo', 'Menú de título', 'Vuelve a aparecer al arrancar (antes la ROM entraba directa en partida). Botones en Palatino, con minúscula inicial. La pantalla superior no lleva logo en ninguna de las dos versiones.'),
 ('02_pausa', 'Pausa', 'Los cuatro botones caben y quedan centrados. El gris de los botones inactivos pierde algo de contraste con la letra fina.'),
 ('03_controles', 'Controles', 'El mayor salto: tildes y minúsculas ("Lápiz - apuntar y cargar", "subir de nivel (prueba)").'),
 ('04_codice_corazon_abierto', 'Códice: El Corazón Abierto', 'Misma ficha; las letras se leen más limpias y la "a", la "e" y la "m" ya no se pegan.'),
 ('05_codice_exvoto', 'Códice: El Exvoto (con datos)', 'La fila VIDA, VELOC. y AMENAZA cabe en el marco con las marcas más juntas. Queda en un gris algo más tenue que el resto.'),
 ('06_codice_abanderado', 'Códice: El Abanderado (la más cargada)', 'Cabe entera sin tocar los botones de abajo.'),
 ('07_intro_catedral', 'Introducción 1/4: La catedral', 'Sin cortes.'),
 ('08_intro_apuntar', 'Introducción 2/4: Moverse y apuntar', 'Sin cortes.'),
 ('09_intro_marea', 'Introducción 3/4: La marea', 'Sin cortes.'),
 ('10_intro_vida', 'Introducción 4/4: Vida', 'Sin cortes; el texto se reparte distinto entre líneas. El HUD de la pantalla superior va horneado en el vídeo y sigue con la letra antigua.'),
 ('11_hud_partida', 'HUD en partida', 'La parte más discutible: "Enc. 1 de 14", "Altura 0 m" y "Tiempo 0:00" salen más finos y se leen con menos fuerza sobre el suelo con textura. Mejora la ortografía, pierde contundencia.'),
 ('12_dones_nivel', 'Subida de nivel: dones', 'Ya usaba la fuente del Códice, ahora en Palatino. Las cartas ofrecidas cambian por azar. El texto "Jefe 5 de 14" queda en parte tapado por la carta seleccionada.'),
 ('13_reliquia', 'Subida de nivel: reliquia', 'Texto del efecto correcto. La reja de la sala se dibuja encima de las cartas en las dos versiones, así que no se puede comprobar si los nombres largos caben en dos líneas.'),
 ('14_jefe_intro', 'Jefe: introducción', 'Nombre, capitán y cita con Palatino; el título es más fino y claro.'),
 ('15_jefe_victoria', 'Jefe: victoria', 'Sin cortes.'),
 ('16_jefe_hud_combate', 'Jefe: HUD en combate', 'La reja tapa parte de "Altura" y "Tiempo" en ambas versiones; no es de la tipografía.'),
]

def img(p, scale):
    im = Image.open(p).convert('RGB')
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)

def b64(im):
    b = io.BytesIO(); im.save(b, 'PNG', optimize=True); return base64.b64encode(b.getvalue()).decode()

md = ['# Tipografía: Palatino nítida en todo el juego (2026-11-19)', '',
 'Sesión `feat/tipografia`. Se estudió la legibilidad de las fuentes, se eligió Palatino con trazado nítido y se llevó a todo el texto del juego salvo el contador de rendimiento. Además se arregló el menú de título, que la ROM jugable se saltaba.', '',
 '## Qué se hizo', '',
 '- **Causa de la mala lectura:** la fuente del Códice era Georgia a 11 px dibujada suave y recortada a blanco y negro, lo que rompe los trazos finos. Se usa ahora el trazado con hinting de la propia fuente.',
 '- **Elegida:** Palatino 11 px nítida (misma altura y hueco que antes). Georgia nítida se lee bien pero es más ancha y desborda las fichas con datos. Rondas A/B/C: `assets/tipografia_ronda1.html` y `assets/tipografia_ronda2.html`.',
 '- **Fila VIDA, VELOC., AMENAZA:** marcas de 3 px con paso 5 para que quepa con la fuente nueva.',
 '- **Menú, pausa, controles y HUD de partida:** dejan la fuente de 5×7 solo en mayúsculas y pasan a Palatino con tildes y minúsculas.',
 '- **Pedestales antiguos (`modifiers.c`):** nombres con tildes ("Cañón largo", "Recámara doble").',
 '- **Título:** el salto del menú venía de la variante de encuentros. Ahora solo las variantes de pruebas (`SKIP_TITLE`) arrancan directas; la ROM jugable muestra el título.',
 '- **Fuera de alcance:** contador de FPS y datos de rendimiento (siguen en 5×7).', '',
 '## Antes y después', '',
 'Cada pareja: izquierda ANTES (`d65c39d` con solo el arreglo del título), derecha DESPUÉS. Capturas reales de la pantalla inferior de la ROM, 256×192.', '']
for pid, title, note in PAIRS:
    md += [f'### {title}', '', f'| Antes | Después |', '| :---: | :---: |',
           f'| ![antes](assets/comparativa/{pid}_antes.png) | ![después](assets/comparativa/{pid}_despues.png) |', '', note, '']
md += ['## Pendiente', '',
 '- Escribir la decisión en `DESIGN.md` (Palatino en todo el texto, HUD incluido).',
 '- Subir el contraste de los botones inactivos y de la fila de datos del Códice.',
 '- Medir rendimiento en la DS con la variante `perf` (el cambio toca el dibujado de texto por frame en el HUD).',
 '- Sin cubrir: pedestal con nombre y pantalla "Mazmorra completada" (el HUD de pedestales solo existe en la rama no-encuentros), reja que tapa nombres de reliquias, y `Jefe 5 de 14` tapado por la carta seleccionada.',
 '- Validación en la DS física: ROM subida el 2026-11-19 (sin el cambio de los nombres de pedestales).', '']
open(os.path.join(ROOT, 'walkthrough.md'), 'w', encoding='utf-8', newline='\n').write('\n'.join(md))

h = ['<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Tipografía antes y después</title>'
     '<style>body{background:#0b0b0b;color:#ddd;font:15px Georgia,serif;max-width:900px;margin:auto;padding:16px}h1{font-size:20px}'
     'h2{font-size:16px;margin:26px 0 4px;color:#e8dcc0}p{color:#aaa;font-size:14px;margin:2px 0 8px}'
     '.r{display:grid;grid-template-columns:1fr 1fr;gap:8px}@media(max-width:600px){.r{grid-template-columns:1fr}}'
     'img{width:100%;image-rendering:pixelated;border:1px solid #333;display:block}b{color:#e8dcc0;font-size:13px}</style>'
     '<h1>Tipografía: antes y después</h1><p>Capturas reales de la ROM (pantalla inferior, 3×). Izquierda: antes. Derecha: después (Palatino).</p>']
for pid, title, note in PAIRS:
    a = b64(img(os.path.join(CMP, pid + '_antes.png'), 3)); d = b64(img(os.path.join(CMP, pid + '_despues.png'), 3))
    h.append(f'<h2>{title}</h2><p>{note}</p><div class=r><div><b>Antes</b><img src="data:image/png;base64,{a}"></div>'
             f'<div><b>Después</b><img src="data:image/png;base64,{d}"></div></div>')
out = os.path.join(ROOT, 'assets', 'tipografia_antes_despues.html')
open(out, 'w', encoding='utf-8').write('\n'.join(h))
print(os.path.getsize(out) // 1024, 'KB')
