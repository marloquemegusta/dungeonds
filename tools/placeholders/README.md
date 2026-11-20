# Placeholders (temporales)

Sprites de marcador para el prototipo ARPG, hechos con cajas de color. Son provisionales:
se sustituyen por los modelos reales de Tripo cuando lleguen, con el mismo nombre de sprite
y los mismos tamaños (`PH_<NAME>_W` / `_H` en `include/placeholders_gfx.h`).

| Sprite | Qué es | Tamaño | Color |
| :--- | :--- | :--- | :--- |
| `runa_xp` | Runa de experiencia que sueltan los enemigos (losa alta y fina) | 12x12 | ámbar apagado |
| `orbe_vida` | Orbe de vida en el suelo (cubo) | 12x12 | rojo sangre seca |
| `orbe_mana` | Orbe de maná en el suelo (cubo) | 12x12 | azul pizarra |
| `maldicion` | Proyectil de maldición lanzado (cubo girado 45° en dos ejes) | 12x12 | violeta ceniza |
| `aliado_marca` | Marca sobre enemigos resucitados (placa plana) | 8x8 | verde hueso grisáceo |

## Regenerar

Desde la raíz del worktree (Blender en `C:/Program Files/Blender Foundation/Blender 5.2/blender.exe`):

```
"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P tools/placeholders/make_boxes.py
python tools/placeholders/prerender_placeholders.py
python tools/placeholders/bake_placeholders.py
```

Salidas: `assets/models/placeholders/*.glb` -> `assets/sprites/placeholders/source/*.png` ->
`assets/sprites/placeholders/*.png`, `include/placeholders_gfx.h`, `source/placeholders_gfx.c`.
Hoja de contacto (4x): `tools/placeholders/contact_sheet.py` -> `walkthroughs/arpg-predemo/assets/placeholders_4x.png`.

El render usa el motor del lab (Node + Playwright, Chromium headless) con la cámara y la luz de
los props (`tools/props/props_render_settings.json`), con brillo 0.6 y saturación 1.8 para que el
color no salga lavado.
