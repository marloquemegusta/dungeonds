# Brief para continuar: props 3D en las salas (ronda 3)

Copia este archivo como primer mensaje del chat nuevo.

## Dónde está el trabajo
- **Worktree:** `C:\codexlocal\dungeonds\.worktrees\props-catedral-v2`, rama `feat/props-catedral-v2`, **sin commits** (unos 38 archivos modificados más los nuevos). Base: `main` 99aacec. No mergeado.
- **Diseño decidido:** `DESIGN.md` §6.13.6, bloque «Piezas 3D de las salas (decidido 2026-11-17…)».
- **Evidencia:** `walkthroughs/props-catedral-v2/props_v2.html` (revisión de piezas) y `salas_integradas.html` (las 5 salas en la ROM). Escenarios de captura `scenarios/props_{embudo,alambrada,balcon,procesion,barrera}.json` (`suite:false`, `evidence_only`).
- **Piezas renderizadas** (`assets/environment/cathedral/props/render/`): `verja` (rastrillo 104x56), `sacos`, `sacos_b`, `sacos_remate`, `sacos_remate_der`, `alambre` (64x48), `columna` (rota), `relicario` (nuevo), `banco_roto`. Las FBX fuente están en `assets/environment/cathedral/props/*.fbx` del worktree (ignoradas por git; los zips siguen en `assets/inbox/`).
- **Herramientas nuevas en `tools/props/`:** `clip_x`, `repeat_x`, `scale_x`, `mirror_x` (prep en Blender), `tone` por pieza (prerender), `shadow_wrap` true/`"clip"` (sombras de piezas modulares).
- **Pipeline:** Blender `"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P tools/props/prep_props.py -- <worktree> <piezas>` → `python tools/props/prerender_props.py <piezas>` → `python tools/props/prop_shadows.py <piezas>` → paleta y kit con los comandos de `step_bake` en `tools/rebuild_all.py` → `build-project.ps1`. Python: `C:/Users/malfonso/AppData/Local/Microsoft/WindowsApps/python` (el del PATH no tiene Pillow).
- **Delegación:** el usuario quiere subagentes **DeepSeek flash** (`delegate-agents`, alias `deepseek`), no Sonnet, para no gastar cuota de Claude. Con briefs largos se corta por `max_turns`: reanudar con `--resume <run_id> --brief <archivo>`.

## Estado de lo integrado
- Rastrillo en el borde de arriba de cada sala y de los jefes 5 y 10, con la base sobre la línea de la barrera (el jefe final no tiene pasillo encima y conserva la franja roja).
- Embudo con sacos y remate; alambrada con 2 líneas de alambre; balcón con columna entera y rota; 1 de cada 4 grupos de bancos con banco roto.
- La colisión de sacos, alambre y rastrillo sigue siendo el rectángulo de cada sala; las piezas nuevas se hornean con huella 0.
- Kit derivado de lo que usan las salas: **1015/1024 tiles**, peor ventana 264/<440. Build 0 avisos; tests de host del kit, strip, paridad y normas PASS.

## Lo que hay que hacer (pedido del usuario, 2026-11-17)

### 1. El rastrillo sube y baja
Hoy no desaparece al limpiar la sala: el strip se genera entero al arrancar (ventana de 2048 px) y no hay forma de redibujar un bloque. **Propuesta a evaluar primero:** dibujar el rastrillo con **sprites de hardware** en vez de en el fondo (por ejemplo 4 sprites de 64x64 para 208x56). Así sube y baja con una animación trivial y además **libera las ~182 tiles** que hoy cuestan sus dos fases en el kit. Revisar: VRAM de sprites, prioridad y oclusión con los actores que pasan detrás o delante, y paleta. La alternativa es una API para redibujar un bloque del strip; comparar coste y riesgo. **Hace falta decisión de diseño antes de código** (regla 9: cómo sube, cuánto tarda, si baja al entrar como la barrera trasera).

### 2. Análisis de tiles: qué podemos quitar
Las **lápidas del suelo están fuera del kit** (con ellas, 1103 > 1024; `LAPIDAS_EN_KIT=False` en el baker y `enc_place_lapidas()` no coloca ninguna). Hacer una tabla de coste en tiles por pieza y fase (suelo, muro, cada prop) y proponer qué recortar. Opciones ya vistas:
- Rastrillo como sprites (ver punto 1): unas 182 tiles.
- Fusionar tiles casi idénticas en el baker de la catedral, como ya hace `tools/bake_arena.py` (umbral de color). Solo cambia la herramienta.
- Alambre más pequeño (punto 4): menos tiles por tramo.
Objetivo: recuperar las lápidas con margen.

### 3. Simetría izquierda/derecha
Las piezas emparejadas no quedan simétricas respecto al eje de la nave (x = 256):
- **Bancos:** `procesion`/`pinza` en x 4 y 132 con lienzo de 72 px (cuerpo 64 + 8 de sombra a la izquierda) → cuerpos a 12 px de la pared izquierda y a 4 px de la derecha.
- **Columnas:** en el balcón, 32 y 136, con anchos distintos (entera 35 px, rota 56); en el resto, la que esté emparejada.
- Revisar también los santos (0/168, 40/128) y cualquier pareja.
Causas: las posiciones del JSON se dan por el lienzo y no por el cuerpo, y `enc_place_piece` encaja cada pieza en la **fase horneada más cercana**, que puede moverla hasta media fase. Regla a aplicar: colocar por el cuerpo del arte, con pares espejo (x_der = 208 − x_izq − ancho_cuerpo) y hornear las fases de cada par para que caigan exactas (DESIGN.md ya usa esa regla con los santos: «x + x' = 59»). Comprobar con capturas y con una impresión numérica de las posiciones finales (`g_enc_last_place` existe con `STRIP_LAYOUT_DUMP`).

### 4. Alambre más bajo
Los tramos se ven enormes. Bajarlos a **casi la mitad de alto**, escalando el tramo entero (por ejemplo 32x24 en vez de 64x48), y **poner el doble de tramos** para que cada línea siga cerrando la misma longitud. Cambiar `target_width` en `tools/props/props.json`, re-renderizar (prep + prerender + shadows), ajustar las posiciones en `tools/encuentros/acto1_v2.json` y regenerar las tablas. Revisar que la base del arte sigue sobre la colisión del rectángulo.

## Cierre (cuando el usuario apruebe)
AGENTS.md regla 4, fase 2: build sin avisos, escenarios `props_*`, tests de host de kit/strip/navegación y **medición en la DS con `PERF_PROFILE`** (regla 6) porque cambia el render. `walkthroughs/props-catedral-v2/walkthrough.md`, fila en `walkthroughs/README.md`, entrada en `STATUS.md`. Antes de borrar el worktree, rescatar las FBX y `.fbm` no versionadas de `assets/environment/cathedral/props/` (y comprobar que la sesión del manifiesto de assets, rama `docs/assets-manifiesto`, no choca: está moviendo los originales 3D a Git LFS en `assets/models/environment/cathedral/props/<objeto>_<uuid>/`).
