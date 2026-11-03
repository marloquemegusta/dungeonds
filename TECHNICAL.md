# TECHNICAL.md - Especificación Técnica y Arquitectura

## 1. Plataforma y Toolchain NDS
- **Consola:** Nintendo DS (ARM946E-S @ 67 MHz para lógica/render, ARM7TDMI @ 33 MHz para audio/input).
- **Aritmética:** Sin FPU hardware. Todo cálculo físico o posicional se realiza en punto fijo entero (`int32_t`, 8.8 o 12.12).
- **Toolchain:** BlocksDS (`skylyrac/blocksds:slim-latest`) vía Docker (skill `ds-game-dev`: `C:\codexlocal\skills\agentic-ds-dev\scripts\build-project.ps1`).
- **Emulación determinista:** DeSmuME headless sobre WSL2 (skill: `C:\codexlocal\skills\agentic-ds-dev\scripts\run-scenario.ps1`). Sirve para comportamiento y comparaciones A/B, no para certificar FPS (ver `AGENTS.md` regla 6).
- **Dependencias de host:** Python 3.13 de Windows (`python.exe`) con `numpy` y Pillow para tests y bakers; Node con Playwright/Chromium para el export headless del lab. Los tests se ejecutan con `python.exe tests/<test>.py`.

## 2. Presupuestos Hardware de Nintendo DS
- **RAM Principal:** 4 MB.
- **Hardware 2D (OAM):** 128 entradas máximas de sprites por hardware.
- **Resolución nativa:** 256×192 píxeles por pantalla.

## 3. Pipeline de Assets
- **Fuente de verdad visual:** el Shader Lab de Three.js (`tools/lab/FBX-Web-Renderer-offline.html`, generado desde `tools/lab/FBX-Web-Renderer-parity.js`) renderiza mapa y personajes con la misma cámara y la misma iluminación. Blender y `tools/ds_look.py` no forman parte del flujo activo.
- **Legado:** `tools/ds_look.py`, `tools/bake_player.py`, `tools/bake_dungeon_*.py`, `tools/convert_*_to_c.py` y `tools/character_profiles.json` pertenecen al pipeline Blender anterior y no generan el mapa ni los sprites de personaje vigentes. Único rastro en el runtime: un comentario en `source/main.c` que cita `ds_look.py` como origen de `FLOOR_TILE_H`.
- **Runtime NDS:** fondo en capas BG de tiles, oclusión por profundidad y actores en OAM. Blender no forma parte del runtime.

### Mapa: lab → baker → runtime
- **Entrada:** modelo FBX/GLB de la mazmorra y `assets/sprites/dungeon/isometric_shooter_bl/map_settings.json` (1536×857 px, 40,42 px/m, ortho 38 m, elevación 30°, preset de luz cálido).
- **Export:** `node tools/lab/export_map_package_headless.cjs <modelo> <map_settings.json> <salida>` abre el lab en Chromium headless (SwiftShader), aplica los ajustes y escribe `world.png`, `collision.png` + `collision.json`, `occlusion.png` (vista binaria) y `occlusion_depth.png` (profundidad), todos de 1536×857 y de la misma cámara.
- **Bake:** `python tools/bake_isometric_shooter_bl.py` rellena a 1536×864 (múltiplo de 8) y genera:
  - `include/dungeon_bg_tiles.h` y `source/dungeon_bg_tiles.c`: fondo cuantizado a 255 colores en tiles de 8×8 y tilemap.
  - `include/diablo_dungeon.h` y `source/diablo_dungeon.c`: colisión de 2 bits por celda de 4 px (384×216).
  - `include/dungeon_occlusion.h` y `source/dungeon_occlusion.c`: runs de oclusión ordenados por (y, x), con `g_dungeon_occlusion_row_start`. La profundidad sale de `occlusion_depth.png`.
- **Runtime:** `source/main.c` dibuja el fondo, consulta la oclusión directamente sobre los tramos y dibuja los actores en el framebuffer de VRAM (§3.3). La rejilla de colisión es la única fuente de suelo caminable.
- **Contrato de datos:** ver §3.3.
- **Verificación:** `python tests/test_map_export_coherence.py` y el escenario `scenarios/map_occlusion_collision_coherence.json` con `run-scenario.ps1`.

### Personajes: lab → generador → runtime
- **Export:** en el lab, renderizar 8 direcciones y pulsar "Exportar paquete completo". El paquete va a `assets/sprites/characters/<nombre>/` con `spritesheet.png` (8×8 celdas de 40×40: 8 direcciones × 8 frames), `shadow.png`, `settings.json` (direcciones, ancla, bounds por dirección) y `nds_shadow_anchor.h`. Modelos fuente en `assets/models/characters/`.
- **Generación:** `python tools/generate_player_sprites_c.py` convierte cada spritesheet a BGR555 y cada máscara de sombra a 4 bits, y escribe `source/player_sprite.c`. Personajes: héroe (space marine), charger y necron (`NUM_CHARACTERS 3` en `include/player_sprite.h`).
- **Sombra:** la máscara `shadow.png` se convierte a cobertura de 4 bits (dos píxeles por byte). El runtime la aplica con límites `[x,y,w,h]` y sólo oscurece el suelo subyacente válido, nunca `VOID_COLOR`. Orden por frame: suelo → sombras → sprites. No sintetizar elipses ni siluetas de sombra por código.
- **Presupuesto:** no guardar máscaras como bytes completos ni usar dimensiones de horneado completas en C. El recorte y empaquetado son parte del contrato de memoria.
- **Verificación:** compilación con `C:\codexlocal\skills\agentic-ds-dev\scripts\build-project.ps1` y escenario con capturas vía `run-scenario.ps1`.

### 3.1. Render de Sprites de Personaje (Shader Lab)
- **Perfil de render:** los ajustes de cada personaje viven en su `settings.json`. Referencia de contraste del lab: 1,50 (`assets/sprites/characters/README.md`).
- **Relieves y grading:** las directrices del pipeline Blender (normal maps atenuados al 30–40%, `DISPLACE` para mallas finas, ramp de cavidad en AO y grading PIL de `ds_look.py`) no están implementadas en el lab. No aplicarlas sin validar el resultado en el lab y en Nintendo DS.
- **Normal maps en NDS:** a resolución nativa de 256×192, relieves al 100% producen parpadeo (*shimmering*). Mantener el criterio de atenuación al validar cualquier sprite nuevo.

### 3.2. Efectos Procedurales en Runtime
- La lanza ósea no usa spritesheets ni outlines: rasteriza una astilla de píxeles estrecha y puntiaguda, orientada por su velocidad fija.
- Las motas del proyectil salen de un pool de 32 partículas; cada una usa posición y deriva 8.8, semilla por proyectil, tonos de hueso y 4–7 frames de vida. La velocidad de la salva es 8 px/frame en punto fijo y conserva el abanico anterior.
- Al morir un enemigo, seis parches de 4×4 copian sus colores BGR555 reales a un pool de 48 fragmentos. Posición/velocidad planar y altura usan 8.8; la gravedad frena el arco y cada parche conserva su color durante 28–35 frames.
- Los fragmentos entran en el orden de profundidad del render y dibujan una sombra puntual en el suelo. El dibujado escribe directamente en BGR555; no instancia modelos 3D ni consume entradas OAM.

### 3.3. Pipeline de Oclusión 2.5D y Presupuesto de Rendimiento en ARM9
- **Arquitectura de Profundidad Continua vs Capas Hardware:** Con estructuras altas continuas (muros, contrafuertes góticos) las capas de fondo fijas de hardware son insuficientes: el personaje debe ocluirse al norte del muro y mostrarse por delante al pisar el sur de su base. El motor dibuja actores directamente en la página trasera del framebuffer de VRAM (sin framebuffer en EWRAM ni DMA de pantalla completa) y limpia solo los spans sucios (`DirtySpan`, `dirty_row`/`dirty_rect` en `game.h`; `clear_dirty_spans` en `main.c`; el modo `DIRTY_VERIFY` comprueba fugas en `dirty_leaks`). La oclusión se consulta directamente sobre `g_dungeon_occlusion_runs` por fila (`find_hiding_run`, `occlusion_blocks_pixel`), exacta al píxel y sin mapa intermedio.
- **Regla Crítica de EWRAM (Prohibición de loops bit a bit):** La memoria principal EWRAM (4 MB) en Nintendo DS tiene bus estrecho y latencia de acceso con wait states. Prohibido terminantemente ejecutar bucles horizontales que realicen operaciones bit a bit no alineadas (`|= (1u << (index & 7))`) por píxel individual: un bitmask de pantalla completa bajo este patrón consume 12–15 ms por frame. Toda máscara debe procesarse por palabras alineadas (32 bits) o resolverse por consulta de tramos.
- **Compilación Obligatoria en Modo ARM 32-bit:** Por defecto BlocksDS compila código ARM9 en Thumb-1 (16-bit). Las funciones críticas de manipulación de memoria y rasterizado (`find_first_occlusion_run_in_row`, `blit_stride`, `draw_shadow_mask`) deben declararse explícitamente con `__attribute__((target("arm"), optimize("O3"), noinline))` para aprovechar instrucciones nativas de 32 bits (`LDRH`/`STRH`, `STMIA`) y evitar el estrangulamiento de registros.
- **Índice por Fila y Búsqueda Binaria en X:** Los tramos (`g_dungeon_occlusion_runs`) se ordenan por (y, x) y `g_dungeon_occlusion_row_start[WORLD_H + 1]` delimita los de cada fila. `find_first_occlusion_run_in_row()` busca en binario el primer tramo que alcanza la X consultada; recorrer todos los tramos de la fila es demasiado caro.
- **Prohibición de Paddings Fantasma:** Prohibido aplicar márgenes de celda arbitrarios a las máscaras. Todo padding artificial crea volúmenes invisibles que recortan al personaje en el aire antes de tocar las siluetas arquitectónicas reales.
- **Contrato de Datos del Mapa (lab → baker → runtime):** `world.png`, `collision.png` y `occlusion_depth.png` se exportan del mismo modelo y la misma cámara (`tools/lab/export_map_package_headless.cjs`). `occlusion_depth.png` guarda por píxel la Y de mapa del punto de suelo bajo la superficie visible (R,G big endian) y B=255 si la superficie supera 0,25 m; el runtime oculta un píxel de actor si esa Y es mayor que la Y de sus pies. La colisión es la huella sobre el suelo de la geometría en la franja 0,30–1,20 m y es la única fuente de "suelo caminable". Verificación: `python tests/test_map_export_coherence.py`.

## 4. Deuda Técnica Pendiente (auditoría 2026-11-02)

Origen: `walkthroughs/audit-saneamiento-2d3d/`. Lo ya resuelto (colisión/oclusión coherentes con el render) está en `walkthroughs/map-export-coherence/`. Se referencian funciones, no líneas, porque se desplazan. Al cerrar un punto, borrarlo de aquí y registrarlo en `STATUS.md`.

### 4.1. Proyección y render 2.5D
- **Escala personaje/mapa.** El mapa está a 40,42 px/m (`map_settings.json`) y los sprites miden ~30 px: el personaje equivale a ~0,75 m y queda oculto tras obstáculos de 1 m. Requiere re-renderizar los tres personajes (8 dir × 8 frames) a ~2× y ampliar el canvas de 40×40, con impacto en RAM/ROM; fijar entonces una única escala px/m con test.
- **Pantalla superior sin actores.** Sólo la inferior dibuja actores; enemigos por encima de la cámara no se ven. Exige un segundo pase de render por frame (vigilar el presupuesto de 60 FPS).
- **Transparencias tras paredes:** diseño sin decidir; ver §4.6.
- Resuelto (ver `STATUS.md`): movimiento/colisión isotrópicos en suelo (`GROUND_DY2`, elipse 6×3), ancla única exportada, oclusión exacta por consulta directa de tramos (sin mapa 4×4 ni reconstrucción por cámara).

### 4.2. Gameplay (preliminar, diferido)
- Lead del tirador anulado: `(player_vx * travel_frames) >> 8` en `enemy_ai.c` divide la predicción entre 256 (quitar el `>> 8`).
- Fallback de spawn de `encounters_spawn_wave` con coordenadas del mapa antiguo (380,227) y centinela `anchor == (0,0)`.
- `invuln_timer` se decrementa pero nunca se asigna ni se consulta en `player_apply_damage`: sin i-frames.
- Pool de pickups (`MAX_PICKUPS` 16) sin expiración; `pickup_spawn` devuelve NULL en silencio y se pierden drops.
- LOS (`los.c`) bloquea con `flags == 3` y las balas con bit `0x02`; el melee del charger no comprueba muros.
- Diseño no implementado: navegación BFS/campo de distancias (los enemigos se atascan en esquinas) y detección por ruido.

### 4.3. Código muerto y acoplamiento
- `tools/convert_iso_to_c.py` (invocado por `tools/build-view.ps1`) todavía emite `dungeon_data`; ejecutarlo volvería a meter ~737 KB en la ROM. Separar su salida de `player_sprite`.

### 4.4. Tests, escenarios, docs y repo
- Los escenarios `dungeon_walk_tour`, `fbx_bg_ring_scroll`, `integration_showcase_walk` y `wall_junction_closeup` no están validados contra el mapa actual (regla 5 de `AGENTS.md`).
- `tools/gen_exact_scenario.py` y `tools/character_profiles.json` aún referencian `wh40k` y `skeleton`.
- ROMs viejas `dungeonds_e30.nds`/`dungeonds_e60.nds` en la raíz del repo principal (ignoradas por git): borrar a mano.
- **Data abort en hardware, sin causa conocida.** Tras unos minutos jugando (dar vueltas y matar enemigos) la DS mostró una pantalla roja "data abort" con la ROM de esta sesión; no se reproduce en DeSmuME (soak de 23.000 frames) ni se pudo atribuir a un cambio concreto. Con la ROM de depuración no volvió a aparecer, y se detectan "cosas raras" por revisar. Herramienta: `include/crashlog.h` + `source/crashlog.c` (poner `CRASHLOG_ENABLED 1`): migas en un anillo, log vivo `/dungeonds_live.log` cada segundo, informe en ambas pantallas y `/dungeonds_crash.log` con registros; L+R+START muestra el informe, L+R+SELECT provoca una excepción real. El handler real no se pudo validar en DeSmuME. Resolver el PC contra `.ds-game-dev/build/build/game-blocksds.map`.

### 4.5. Motor 2D/3D (auditoría 2026-11-03)
Origen: `walkthroughs/audit-motor-2d3d/`. Resueltos en el prototipo A (compositor directo en VRAM, spans sucios, oclusión por consulta, HUD con START, logs bajo `DEBUG`); lo siguiente sigue pendiente.
- **Métricas.** `cpu_percent` excluye DMA y anillo BG; comentario obsoleto de presupuesto (280095) en `game.h`. Presupuesto real: 560190 ticks/frame. El rendimiento solo se valida en DS con `PERF_PROFILE` (`/dungeonds_perf.log`), no en DeSmuME. El Makefile no define `DEBUG` y `encounters.c` conserva 3 `nocashMessage`.
- **Timestep por frame presentado.** A 30 FPS el juego va a media velocidad; usar delta de tiempo o paso fijo con acumulador.
- **Transparencias:** ver §4.6.
- **Anillo de BG:** reescanea 2048 celdas por pantalla en cada cambio de tile (~0,1 ms de media, picos ~2 ms). Baja prioridad.
- **Assets:** sprites BGR555 crudos (614 KB) y máscaras de sombra 4 bpp 80×80 (614 KB) sin paleta ni compresión ni NitroFS; ~2,0 MiB de 3,5 MiB de EWRAM; ITCM/DTCM sin uso.
- **Pipeline:** `tools/rebuild-assets.ps1` llama a `tools/build_assets.py` inexistente; `generate_player_sprites_c.py` copia texto del `.h` del lab en vez de convertir `shadow.png`; tamaño del mundo duplicado en 4 sitios; `SPAWN` hardcodeado en el baker; `.c` generados sin hash de origen; ~40 scripts muertos en `tools/`.
- **Acoplamiento:** coordenadas de mundo = píxeles de pantalla; impactos con círculo en pantalla frente a movimiento con métrica de suelo; estado global en `main.c`; `on_enemy_death` copia píxeles.
- **Escenarios:** sensibles a frames perdidos del emulador; deberían basarse en frames de lógica, no en vblanks.

### 4.6. Transparencias y lectura tras paredes: DISEÑO POR DECIDIR
No hay decisión de diseño tomada sobre cómo mostrar lo que queda detrás de una pared. Lo que hay en el código es provisional y no debe tomarse como referencia ni ampliarse:
- **Personaje:** parpadeo temporal (`blit_stride`, `s_frame_index & 1`): los píxeles ocluidos se pintan en frames alternos. Solo se lee como transparencia a 60 FPS estables.
- **Enemigos:** usan el mismo parpadeo solo mientras el jugador está ocluido (`s_player_see_through`); si no, quedan ocultos del todo.
- **Pie de la pared / suelo oculto:** mientras el jugador está ocluido se dibuja su sombra sobre la pared y una línea del borde de la huella de colisión (`draw_hidden_wall_base`) en una caja de 64×48 px. Esa línea no coincide con la base visible de la pared y en hardware no funciona bien.

Preguntas abiertas a resolver en una sesión de diseño (`DESIGN.md`) antes de tocar código:
1. ¿Qué se ve del personaje tras una pared (parpadeo, trama espacial fija, silueta de color, contorno, alfa por hardware)?
2. ¿Qué se ve de los enemigos y bajo qué condición (nunca, solo cuando el jugador también está detrás, siempre como silueta)?
3. ¿Cómo se comunica dónde está el suelo caminable y la base de la pared en la zona oculta (ocultación ambiental en el render del mapa, recorte/transparencia de la pared cerca del jugador, otra técnica)?
4. ¿Encaja con el compositor por software actual o pide OAM/motor 3D (alfa por hardware, ventanas de OBJ, Z-buffer)?
