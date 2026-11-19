# abanderado_derrota

Spritesheet PNG: 56 columnas (frames), 8 filas (direcciones), 320x320px por celda, RGBA transparente.

Incluye atlas de sombras NDS (768x96 px), mascaras 4-bit, bounds de sombra por direccion, codigo C listo para Nintendo DS (nds_shadow_anchor.h), GIF por direccion, collage GIF, PNG por frame y settings.json. Orden: S, SW, W, NW, N, NE, E, SE.

El Abanderado solo, 320x320 por celda, 56 fotogramas por direccion: suelta el estandarte (cae al suelo), se derrumba de rodillas, golpea el suelo con el puño izquierdo 4 veces y recoge el asta (~7 s, se usa con `una vez`). Se regenera con `tools/characters/build_abanderado_derrota.py` y `node tools/lab/export_character_headless.cjs assets/models/characters/abanderado/abanderado_derrota.fbx assets/sprites/bestiary/abanderado_derrota --template tools/characters/abanderado_lab_template.json --anim abanderado_derrota --resolution 320 --fitZoom 0.88 --legibility c2 --frames 56 --noCHeader`.
