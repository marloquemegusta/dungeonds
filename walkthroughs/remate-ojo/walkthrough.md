# Walkthrough — Ejecución del Ojo del Tribunal: re-render con el lab rápido e integración en el juego (`feat/remate-ojo`)

**Fecha:** 2026-11-21
**Rama:** `feat/remate-ojo` (worktree `.worktrees/remate-ojo`)
**Diseño:** `DESIGN.md` §6.13.8 (ejecuciones / glory kills)

## Qué se ha pedido

El gesto ya estaba aprobado, pero se renderizó con **Blender**. La entrega hace dos cosas:

1. **Re-renderizarlo con el lab rápido** (`tools/lab/fast/`), el pipeline de sprites que usa el resto del juego.
2. **Integrarlo en la ROM** con las mismas reglas que las ejecuciones del Exvoto y el Cireneo: el Ojo tambaleante se
   puede rematar con `L`, el héroe es invulnerable durante la ejecución, el enemigo muere sin su efecto estándar, el
   rayo queda cargado y quedan restos en el suelo.

## 1. Re-render con el lab rápido

El pipeline es el de los remates (Blender hornea la escena, el lab hace los sprites), pero con el lab rápido en lugar
del web:

1. `tools/characters/ds_remate_ojo.py` con `REMATE_GLB_DIR` escribe **39 GLB** (38 fotogramas + el de restos) con las
   mallas ya horneadas y sin armadura, en metros de mundo, con el Ojo en el origen (el ancla del lab) y el héroe a −X.
   Los actores ocultos de cada fotograma se exportan encogidos a 1e-5 para que todos los fotogramas compartan
   **la misma topología** (es lo que permite al rasterizador compartir una sola malla por actor).
2. **`tools/lab/fast/export_scene_fast.cjs`** (nuevo, Node sin navegador) lee la secuencia de GLB con
   `glb_loader_minimal.js`, decodifica sus texturas PNG una sola vez (deducidas por hash), encuadra la escena con
   cámara ortográfica fija y rasteriza las **8 direcciones × 39 fotogramas** con el mismo `raster.cjs`/`post.cjs` de
   los personajes. Escribe el paquete del lab (`frames/<dir>/<i>.png` 1x, `shadow.png`, `settings.json`, GIFs).
   - Celda **96×96**, **38 px/m** (`fitExtent = 96/38 = 2,5263 m`, la escala que asume el packer del remate).
   - Legibilidad **C2** (supersample 4, tono neutral), la misma de los sprites de personaje.
   - **14,7 s** en total (lectura 1,1 s, texturas 0,3 s, raster 4,5 s, post 6,6 s, escritura 1,8 s). El lab web tardó
     **32 min solo en cargar los 39 GLB** y además no puede descartar las chispas aparcadas: mide un encuadre de
     6,72 m y saca los fotogramas vacíos, así que **no hay referencia válida del lab web** para comparar.
3. `tools/generate_remate_sprites.py` empaqueta el paquete en `nitrofiles/remate/ojo_d0..d7.bin` y regenera
   `source/remate_sprites.c` / `include/remate_sprites.h`.

La animación (guion, poses, clips del inbox, correcciones de las vueltas anteriores) **no cambia**: cambia el
renderizador. El aspecto final es el del lab (el mismo de todos los personajes y del resto de remates): iluminación
del lab, bordes duros, sombra horneada aparte.

### Sombras de la celda

La proyección de sombra del lab lleva cada vértice al suelo desplazándolo según su altura (~1,7 m de sombra por cada
metro de altura), así que **las chispas y el vidrio de la escena dejaban su sombra a un metro largo de los actores**:
la máscara de sombra del juego admite 64 px, el recorte se movía fotograma a fotograma y la sombra se veía rota (el
lab rápido acepta `--shadow-skip-materials` y la escena del Ojo excluye `brasa,brasa2,vidrio`). Con eso la sombra de
la animación entra siempre en los 64 px; solo los 4 fotogramas finales (el cadáver ya tendido, cuya sombra mide 75 px)
se recortan en estático al lienzo de 64, sin saltos.

## 2. Integración en el juego

- **Nuevo tipo de remate** `REMATE_KIND_OJO` (celda 96×96, **38 fotogramas**, **4 ticks** por fotograma = 152 frames
  de juego ≈ 2,5 s, el ritmo del GIF aprobado; restos = el fotograma 38, el cadáver sin el héroe).
  `RemateKindInfo` gana `frames` y `ticks`: cada tipo decide su duración (Exvoto/Cireneo siguen 12×6 = 72 frames).
- **Mismas reglas que el resto** (`remate_start`): el Ojo entra en `ENEMY_STATE_WOBBLE` al 50 % de vida (antes los
  tiradores no tambaleaban; `gameplay.c`), `L` a ≤96 px, embestida previa, invulnerabilidad durante embestida y
  celda, muerte limpia (`remate_killing`), rayo recargado al instante, invulnerabilidad de 1 s después y restos
  parpadeando 1 s. El Ojo mira al héroe durante la celda (`e->dir = (s_dir + 4) & 7`), como el Exvoto.
- **El FSM del Ojo aprende a tambalearse** (`enemy_ai.c`): un caso `ENEMY_STATE_WOBBLE` corta el ciclo de apuntado
  (no sigue, no fija, no sentencia) mientras dura el aturdimiento; desde ahí `L` abre el remate.
- **Formato de datos por tipo, no global.** Antes `REMATE_NUM_FRAMES = 12` estaba compilado en el header y en los
  bins. Ahora la cabecera del bin es variable (cada tipo lleva sus arrays) y el header declara `REMATE_MAX_FRAMES`.
  Los bins y tablas del Exvoto y el Cireneo quedaron **congelados** en `tools/remate_legacy.json` (sus paquetes del
  lab nunca se versionaron) y no se reescriben.
- **Streaming desde NitroFS.** Cargar el bin del Ojo entero (206 KB) dejaba la EWRAM a 4 KB del límite: el vídeo de
  la intro pide ~98 KB de heap al arrancar y habría fallado. Ahora `remate.c` abre el bin al empezar la celda y lee
  **solo el fotograma que toca** (píxeles + runs + máscara) a buffers estáticos de 23,5 KB; al terminar deja cargado
  el fotograma de restos y cierra el fichero. EWRAM: **3,32 de 3,5 MiB** (antes de la sesión, 3,38) y **181 KB de
  heap**.
- **Regresión de los otros remates**: los tres escenarios de transición existentes (Exvoto cerca, Exvoto oeste,
  Cireneo norte) **pasan** con el nuevo cargador.

## Secuencia (38 fotogramas, 4 ticks por fotograma ≈ 2,5 s)

| Fotogramas | Qué pasa |
| :--- | :--- |
| 0–1 | El héroe entra. El Ojo está **agachado** a propósito: es la única forma de que el farol del hombro le llegue al héroe, que es un 40 % más bajo. |
| 2 | **Agarre:** las dos manos del héroe cierran sobre la jaula del farol. |
| 3–4 | **Tirón y arranque:** el farol se desprende del cuello (borde dentado y sección en rojo oscuro). Chispas y vidrio. |
| 4–11 | El cuerpo **se incorpora** a su postura natural, algo encorvada, sin llegar nunca a estar de pie perfecto. |
| 5–8 | El héroe voltea el farol y lo tira: vuela, cae a sus pies en el 8 y se queda a ras. |
| 11–17 | El Ojo, ya **incorporado y descabezado**, se tambalea; el héroe sube la pierna. |
| **17** | **Contacto:** el pie del héroe toca el cuerpo del Ojo **y ese mismo fotograma arranca el desplome**. |
| 17–29 | **Desplome:** clip `Falling Back Death` desde su fotograma 7 (el de la reacción). Se vuelca, abre los brazos y cae de espaldas; el 37 es el cadáver tendido. |
| **21** | **Se le cae la cabeza de la mano:** cae al suelo entre los dos y rueda hasta pararse junto al cuerpo. |
| 30–37 | El cuerpo queda muerto en el suelo, con la cabeza suelta a su lado y el farol arrancado delante. El héroe **recupera la pose** (la patada se mezcla de vuelta a su reposo). |
| 38 | **Restos** (fotograma extra del bin, sin héroe): el cadáver que queda ~1 s parpadeando. |

## Evidencia

- **La ejecución en la ROM real** (captura de DeSmuME del escenario, pantalla de juego, 4x):
  [`assets/ojo_remate_rom_4x.gif`](assets/ojo_remate_rom_4x.gif).
- **Las 8 direcciones para revisar** (GIF 4x por dirección, ya con el lab rápido):
  [`assets/ojo_remate_8dirs.html`](assets/ojo_remate_8dirs.html).
- GIF por dirección: [`assets/ojo_remate_d0_4x.gif`](assets/ojo_remate_d0_4x.gif) … `assets/ojo_remate_d7_4x.gif`.
- Hoja del fotograma de contacto (17) en las 8:
  [`assets/ojo_remate_contacto_8dirs.png`](assets/ojo_remate_contacto_8dirs.png).
- Tira del desplome (fotogramas 16–31, 4x): [`assets/ojo_remate_desplome_4x.png`](assets/ojo_remate_desplome_4x.png).
- Paquete del lab rápido (fotogramas 1x, sombras y settings) en `assets/lab_out/` (derivado, no versionado).

## Verificación

- **ROM**: `DS_BUILD=PASS` (0 warnings) en la variante de producción y en `remate-sandbox`.
- **Escenario nuevo** `scenarios/remate_transicion_ojo_cerca.json` (variante `remate-sandbox`, ROM real): el Ojo se
  fuerza a tambaleo, se pulsa `L` y se capturan 189 frames; **PASS** (`en_state` 18 al empezar, `en_active` 0 al
  terminar: el remate lo mata). Sin congelaciones (los fotogramas de la celda cambian uno a uno).
- **Regresión**: `remate_transicion_exvoto_cerca`, `remate_transicion_exvoto_oeste` y
  `remate_transicion_cireneo_norte` **PASS** con el cargador en streaming. (El de Cireneo destapó un fallo real del
  streaming en el fotograma de restos —lectura fuera de rango— que está corregido en esta entrega.)
- **Tests de host**: `test_guardrails`, `test_sprite_ground_anchor`, `test_blit_runs_contract` y el resto de la
  batería **PASS**; fallan `test_bestiary_assets_contract` y `test_character_muzzle` porque el worktree no tiene los
  paquetes de sprites sin versionar (`assets/sprites/characters/charger/settings.json`), un fallo de entorno que no
  toca esta entrega.
- **Memoria**: EWRAM 3,32/3,5 MiB, heap 181 KB (el bin del Ojo entero habría dejado 4 KB y roto la intro).
- **Assets**: `nitrofiles/remate/ojo_d0..d7.bin` (1,2 MB los 8; el mayor, 206 KB) + `source/remate_sprites.c` y
  `include/remate_sprites.h` regenerados con el generador.

## Pendiente / decisiones abiertas

- **Duración**: 38×4 = 152 frames (~2,5 s) son el ritmo del GIF aprobado, pero es el doble de los ~1,2 s del
  Exvoto/Cireneo. Es un número por tipo (`ticks` en `RemateKindInfo`): si en la DS se hace largo, bajar a 3 ticks.
- **Balance**: el Ojo ahora tambalea y se puede rematar. Falta verlo en una sala real con el Cireneo guardándolo
  (§6.13.9) y decidir si el tambaleo del tirador es demasiado generoso.
- **Paridad lab rápido ↔ lab web** en secuencias GLB: no se pudo medir porque el lab web no descarta las chispas
  aparcadas de los GLB (encuadre de 6,72 m → sprites vacíos). La referencia visual es la captura de la ROM.
- El fotograma 0 del lab web sigue siendo defectuoso para Exvoto/Cireneo (se usa el 1 repetido); el lab rápido no
  tiene ese problema y el Ojo usa su fotograma 0.

## Notas

- Scripts: `tools/characters/ds_remate_ojo.py` (escena + export GLB con `REMATE_GLB_DIR`),
  `tools/lab/fast/export_scene_fast.cjs` (render de la secuencia GLB),
  `tools/generate_remate_sprites.py` (empaquetado y C generado), `tools/remate_legacy.json` (datos congelados de
  Exvoto/Cireneo).
- Los GLB de la escena y el paquete del lab son **derivados** (no se versionan): se regeneran con los comandos de
  arriba. Los dos clips del inbox **no se han movido, copiado ni borrado** (el usuario pidió no retirarlos).
- Documentos actualizados: `DESIGN.md` §6.13.8 (ejecución del Ojo integrada y sus reglas), `TECHNICAL.md` §3 (lab
  rápido con secuencias GLB y bins de remate en streaming, EWRAM 3,32), `assets/MANIFEST.md` (familia de remates),
  `STATUS.md` y este walkthrough.
