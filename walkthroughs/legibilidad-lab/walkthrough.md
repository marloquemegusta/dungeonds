# Legibilidad del pre-render de personajes (2026-11-14)

Revisión del pipeline de personajes del lab (render → reducción → grading → colores DS) buscando mejoras del tipo del supersampling, sin contorno. Decisión en `DESIGN.md` §6.9.1b («Legibilidad del pre-render de personajes»).

Todas las imágenes son **render real del lab** con una **simulación** de la conversión a DS, sobre una baldosa de suelo recortada de una captura de la ROM, a 4x NEAREST. No son capturas de ROM.

## Tanda 1

- `assets/cmp_corazon_rom.png`, `assets/cmp_abanderado_rom.png`. A actual · B supersampling ×4 + bordes 50 % · C B + tono neutro + curva S · D/E C + brillo de borde (suave/fuerte).
- La contraluz direccional colocada detrás no se ve a este tamaño (prueba mínima con solo esa luz: ilumina un filo de 1–2 px).
- Elegida: **C**.

## Tanda 2 (sobre C, abanderado a ~3 m)

- `assets/ab2_corazon.png`, `assets/ab2_abanderado.png`: C · C1 bordes 30 % · C2 C1 + enfoque suave · C3 C1 + enfoque medio.
- `assets/ab2_escala.png`: Corazón (1,80 m, 31–33 px) y Abanderado (~3 m, 54 px) juntos.
- Bajar el relieve de materiales no cambia ningún píxel (Corazón no tiene mapa de relieve; en el abanderado no se nota).
- Elegida: **C2**.

## Cómo se generó

`tools/ab_render.cjs` fuerza las variantes en el lab offline headless sin modificarlo (supersampling, tono, contraluz, brillo de borde, relieve, resolución, zoom). `tools/compose.py` y `tools/compose2.py` aplican curva S, enfoque y la conversión a DS, y componen las hojas. Abanderado: `assets/models/characters/abanderado/source/` de la rama `feat/ojo-tribunal` (pose estática, sin estandarte).

## Preset en el lab

`tools/lab/FBX-Web-Renderer-parity.js` añade el selector «Legibilidad: Anterior / C2» (por defecto Anterior, idéntico a antes). En exportación headless: `node tools/lab/export_character_headless.cjs <fbx> <out> ... --legibility c2`, que anota `"legibility"` y `"toneMapping"` en `settings.json`. Comparativa: `assets/lab_preset_anterior_vs_c2.png`.

## Pendiente

- Bordes al 30 % y redondeo en `tools/generate_player_sprites_c.py`.
- Re-exportar los personajes de la ROM con C2 y botón para alternar sets en la consola; validar en la DS.
- Escenario: solo cuando se recuperen los modelos de columna y banco.

## Cierre e integración en la ROM (2026-11-14)

- **Conversión DS y automatización (`tools/rebuild_all.py`):** implementado `characters.json`, soporte `--legibility c2` en `generate_player_sprites_c.py`, `export_character_headless.cjs`, `export_map_package_headless.cjs` y `prerender_props.py`, además de recálculo automático de paleta (`extract_palette.py`, 144 tonos de props) antes de `bake_cathedral_kit.py`.
- **Props y estatuas:** recuperados los 5 `.fbx` activos desde `inbox/` a `.glb` con `prep_props.py` (eliminando los 3.763 vértices sueltos de alambre en `vela`), añadidas dos estatuas `santo` simétricas en los tramos abiertos/relicario (`strip.c`, `bake_cathedral_kit.py`: 896/1024 tiles, peor ventana 389/<440).
- **Verificación:** `15/15` suites de tests de contrato PASS, compilación limpia sin warnings (`dungeonds.nds`, 1.441.792 bytes) y subida a la Nintendo DS física.
