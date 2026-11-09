# Prompt para continuar la 0.3.2 (catedral) en otra sesión

Copia todo lo que hay debajo de la línea en una sesión nueva.

---

**MODO AHORRO DE TOKENS (prioridad sobre todo lo demás).** Me quedan pocos tokens:
- Delega casi todo en agentes externos con la skill `delegate-agents` (DeepSeek, Luna, Flash): su consumo no cuenta en esta sesión. Usa Haiku solo si no queda otra; nada de Sonnet ni de Opus.
- No leas archivos enteros, logs crudos, transcripciones de agentes ni JSONL de progreso. Usa `tail -n 5`, `grep` concreto o `--status`. Pide a cada agente una respuesta de 10 líneas como mucho.
- No leas los documentos de la lista de abajo salvo la sección exacta que necesites (con `grep -n`). El contexto de este prompt basta.
- Ninguna imagen se mira a tamaño completo: un recorte o miniatura de ≤ 800 px, y solo las hojas finales. Las comprobaciones intermedias las hace el agente.
- Build y escenarios: imprime solo la línea `DS_BUILD=` / `DSM_SCENARIO_RESULT=`.
- Sin relevo ni seguimiento en vivo: lanza en segundo plano y espera el aviso.
- Respuestas cortas. Si algo no cabe, hazlo a medias, dilo y para.

Seguimos con el escenario de la catedral de dungeonds (DS), versión 0.3.2. Trabaja en el worktree `C:\codexlocal\dungeonds\.worktrees\v032-escenario` (rama `feat/v032-escenario`). Hay mucho trabajo sin commitear de esta y otras sesiones: añade siempre por ruta, nunca `git add -A`. **Commit solo cuando yo lo apruebe.**

## Lee primero
- `AGENTS.md` (reglas: worktree, sin float, 0 warnings, escenarios con geometría verídica, DS a 60 FPS, subagentes con modelo asignado).
- `DESIGN.md` §6.9.1b: decisiones vigentes de la catedral, entre ellas la luz única neutra, los sprites sin contorno (en prueba), el suelo de damero en rombos con lápidas y las sombras de las piezas.
- `walkthroughs/v032-escenario/BIBLIA.md`: método. La Fase A de concepts está cancelada; la paleta sale de los prerenders.
- `assets/environment/cathedral/prompts.md`: prompts de Tripo de los lotes 1, 2 y 3.
- Registro de agentes de esta sesión: `C:\codexlocal\skills\delegate-agents\feedback\2026-11-08-dungeonds-catedral-props.md`. Ahí están los aciertos, los fallos y los bugs encontrados.

## Qué está hecho (verificado)
- **Piezas del lote 1** (banco_roto, banco_volcado, columna, relicario, santo, vela):
  - Pipeline FBX de Tripo → `tools/props/prep_props.py` (Blender headless; `yaw`, `pitch`, `loose_filter`, `align_slab`, `top_only`, `slab_turn`) → `tools/props/prerender_props.py` (lab, cámara de 30°, luz `tools/props/props_render_settings.json`, preset neutral) → `assets/environment/cathedral/props/render/<pieza>/` (color, footprint, depth, shadow y meta).
  - Hoja con el marine: `walkthroughs/v032-escenario/assets/props_lote1_escala.png`.
- **Bug del lab arreglado:** las texturas de los GLB salían volteadas (`texture.flipY = false` en `tools/lab/glb_loader_minimal.js` y en `FBX-Web-Renderer-offline.html`). Todo lo renderizado antes de ese arreglo estaba mal.
- **Paleta neutra:** `assets/environment/cathedral/palette/` (130 colores de piezas).
- **Personajes con luz neutra y sin contorno:** `assets/sprites/characters_neutral/` (la ROM aún usa los de `characters/`). Comparativa: `personajes_neutra_vs_actual.png`. `tools/generate_player_sprites_c.py --src` genera desde la carpeta neutra.
- **Kit de la catedral en la ROM:**
  - `tools/bake_cathedral_kit.py --floor assets/environment/cathedral/floor/rombos --phases 4` → `source/strip_kit.c`.
  - Muros de 48 px (arte provisional, casi negro), piezas por fases, oclusión de la columna y el santo, sombras horneadas alineadas con la del marine (`tools/props/prop_shadows.py`), lápidas de 1 fase.
  - Último horneado: 880/1024 tiles, peor ventana 208/440.
  - Corregidos dos bugs del baker: la expansión del periodo del suelo y el muestreo del suelo bajo las piezas.
  - Último build: PASS con 0 warnings. Escenarios `strip_cathedral_look`, `strip_climb_smoke` y `strip_horde_tide`: PASS.
  - Capturas: `rom_catedral_rombos.png`. Las sombras y las lápidas aún no están compiladas en la ROM.
- **Suelos generados:**
  - `assets/environment/cathedral/floor/{rombos, rombos_b, rombos_h, rombos_h_b}`: damero en 3D a 30°; `rombos` es el favorito.
  - Descartados por ser dibujo plano: `losas_cuadricula*` y `tiles_sueltos*`.
  - Losas rectangulares en 3D: `losas_3d*`.
  - Comparativa: `rombos_4_variantes.png`.

## Pendiente (en este orden)
1. **Lápidas (urgente, las rompí al final):**
   - Las 8 entradas `lapida_{cruz,caballero,cruz2,caballero2}_{h,v}` de `tools/props/props.json` usan `exact_px` y `canvas_px`, que las **aplastan**: el usuario lo rechazó.
   - Quita `exact_px` (no estirar) y conserva la proporción natural. Lo que le gustaba es la hoja `walkthroughs/v032-escenario/assets/lapidas_legibilidad.png`, columnas «4 m», salvo el giro del caballero v2.
   - Son **suelo**, a ras: `top_only` (sin cantos) está bien.
   - El caballero v2 necesita `align_slab` para quedar recto y comprobar el giro (`slab_turn`).
   - Comprueba en el render grande (`--raw`) que se ve la cara grabada.
   - Todas a unos 4 m de largo, en horizontal y en vertical, alineadas a la rejilla de 8 px (lienzo múltiplo de 8 sin deformar).
   - Hoja nueva sobre el suelo de rombos con el marine.
2. **Damero con las losas de Tripo** del usuario:
   - Están en `assets/environment/cathedral/floor_tiles/`: losa_a, losa_cera, losa_grieta, losa_rota y losa_sangre. No hay losa_b.
   - Flash se pausó a los 27 min sin hitos y sin salida. Brief: `C:\Users\malfonso\AppData\Local\Temp\claude\39ccd0e360023ad3\2d4996c8-ed50-4c7a-ada4-8ab8e81ae3cb\scratchpad\briefs\flash_rombos_tripo.md` (si ya no existe, rehazlo).
   - La segunda piedra del damero se saca **recoloreando en Blender** la losa_a, con poco contraste.
   - Se puede reanudar con `delegate.py --resume 20261108T175438-76e1` o rehacer.
   - Salida: `floor/rombos_tripo*`.
3. **Hornear y compilar** con sombras y las 8 lápidas. Vigila el tope de 1024 tiles: si se pasa, quita fases o lápidas y dilo. Después, build y los 3 escenarios.
4. **Variante con los sprites sin contorno:** compila una ROM alternativa con `tools/generate_player_sprites_c.py --src assets/sprites/characters_neutral` y saca las mismas capturas. Revisa la sombra y el ancla, que el ancla sube 1 px.
5. **Walkthrough tipo «catálogo visual»** en `walkthroughs/v032-escenario/walkthrough.md`, con imágenes en `assets/`. Debe enseñar **todas las opciones** de cada cosa para que el usuario elija sin leer técnica:
   - suelos (todas las carpetas de `floor/`, con la misma escena del marine y las piezas);
   - lápidas (8, en horizontal y en vertical);
   - piezas con y sin sombra;
   - personajes con y sin contorno;
   - capturas de la ROM real de cada combinación principal.

   Cada opción con letra o número y una línea en lenguaje llano. Añade una fila en `walkthroughs/README.md` y la entrada en `STATUS.md`.
6. **Reordenar los assets 2D sin perder nada:** separar fuentes (FBX, GLB, zips) y resultados 2D, y actualizar las rutas de los scripts. Enseña el árbol antes de mover nada.
7. **Corregir la biblia:** la §6 todavía describe texturas planas.

## Delegación
- Usa la skill `delegate-agents` (versión en `C:\codexlocal\skills\delegate-agents`, actualizada; ahora incluye **DeepSeek**, consulta `delegate.py --list`).
- Modelos: Haiku para el arte iterado con imagen en Blender (ha rendido muy bien), Flash para el arte 3D, Luna para C/baker (cara en tokens y sobreafirma lo visual) y DeepSeek para probarlo.
- Indica el modelo de cada uno.
- El clasificador de permisos bloquea `--allow-toolchain`: compila y pasa los escenarios tú con `C:\codexlocal\skills\agentic-ds-dev\scripts\build-project.ps1 -ProjectPath <wt>` y `run-scenario.ps1 -ProjectPath <wt> -ScenarioPath <wt>\scenarios\<x>.json`.
- **Mira tú la hoja final** (en miniatura) antes de dar algo por bueno: los agentes han dado por buenas vistas previas rotas. Pide al agente que te diga en una línea qué debes comprobar en ella.
- Anota el feedback de cada agente en el archivo de feedback.

## Limpieza que el usuario debe hacer a mano
El clasificador no dejó borrar 7 duplicados exactos del inbox. El comando está en la conversación anterior y en el walkthrough, si lo añades. Además, las lápidas v2 y las losas de Tripo siguen en `C:\codexlocal\dungeonds\assets\inbox`: muévelas a `assets/models/environment/cathedral/tripo/` (está en `.gitignore`).

Las elecciones que me pidas, en lenguaje llano y en pasos cortos.
