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

### Arenas: datos → lab → baker → runtime
- **Fuente única:** `assets/arenas/arenas.json` (geometría en píxeles de la imagen final, alturas en metros, inicio del jugador y enemigos con su `pack`). Desde v0.2 contiene una sola mazmorra de 768×768 con zonas de color, puertas y decoración (`zones`, `doors`, `kind` por bloque); la imagen y el recorte son por arena. La paleta de color la ajusta `tools/calibrate_arena_palette.py` (resultado en `tools/arena_palette.json`).
- **Modelos:** `python tools/make_arena_glb.py` escribe `assets/models/environment/arenas/arena_0N.glb` con un escritor GLB propio (cajas con color plano; no hace falta Blender). La sala se gira 45° para que sus muros salgan alineados con la pantalla.
- **Export:** `python tools/export_arenas.py [arena_0N]` (unos 25 s las cuatro) construye los GLB y llama a `tools/lab/export_map_package_headless.cjs`. El lab encuadra el modelo por su caja envolvente en ejes del mundo, que para una sala girada es mucho mayor que 384×384; por eso renderiza a 896×541 con 40,42 px/m y recorta 384×384 en (256,68) (`labRender` en `map_settings.json`). Paquete por arena en `assets/sprites/arenas/arena_0N/`: `world.png`, `collision.png/json`, `occlusion.png`, `occlusion_depth.png`.
- **Bake:** `python tools/bake_arena.py --spec assets/arenas/arenas.json` escribe `source/arena_0N.c` (paleta de 255 colores, tiles y tilemap con el presupuesto de tiles de §3.3, colisión de 2 bits por celda de 4 px, runs de oclusión con índice por fila, inicio y enemigos) y `source/arenas.c` (orden de juego). Comprueba que el inicio y los spawns están sobre suelo caminable.
- **Runtime:** `include/arena.h` define `Arena`; `g_arena` apunta a la activa y toda la colisión, visión, oclusión, fondo, navegación y cámara leen de ella. `arena_enter()` (main.c) cambia paleta, vacía las cachés de tiles, reconstruye el campo de navegación y reinicia el encuentro. El paso entre arenas es un fundido a negro (8 frames), carga con la pantalla negra y fundido de vuelta.
- **Iluminación del mapa (excepción):** `arenas.json` puede llevar `lighting` {key, fill, world}; la mazmorra usa 1,5/1,2/0,3 en vez de la luz de los personajes porque con la original todo salía marrón y claro. Rompe la regla de §2 de DESIGN.md (misma luz para mapa y personajes); si los personajes desentonan, revisar aquí.
- **Sombras e iluminación (v0.2):** las sombras son las del lab, con la misma luz key que los personajes. El shadow camera de la luz key mide ±5 m por defecto y solo cubría el centro de un modelo de 768×768; `"shadows": true` en `arenas.json` hace que `tools/lab/export_map_package_headless.cjs` lo ensanche a ±45 m con mapa de 4096. Luz: key 1,7 / fill 1,0 / world 0,4, con `tools/calibrate_arena_palette.py` recalibrado. `"baked_glow": true` añade dos bandas planas de brillo del color de acento delante de cada muro horizontal (`bake_light` en `tools/export_arenas.py`); `"baked_shadows"` dibuja sombras desde la spec y queda como alternativa. Las sombras suaves y diagonales suben a 999 tiles únicos (peor ventana 237 de 440) y `BG_MAX_TILES` pasa a 1024.
- **Manadas y modificadores (v0.2):** `ArenaEnemy.pack` agrupa enemigos; `encounters.c` los crea `DORMANT` (sin IA) y despierta la manada completa por cercanía (220 px de suelo) o daño; `modifiers.c` guarda los efectos en `g_mods` que leen `weapons.c`, `gameplay.c` y `main.c`. `MAX_GAMEPLAY_ENEMIES` 24 y `NAV_MAX_W/H` 48 (mazmorra 768×768 = 48×48 nodos de 16 px).
- **Cámara:** sigue al jugador sin salir de la imagen en horizontal; en vertical el jugador se mantiene en la pantalla táctil y la superior muestra la franja de encima (como mucho media pantalla de vacío fuera de la arena).
- **Verificación:** `tests/test_arena_export.py` (geometría del export contra la especificación), `tests/test_map_export_coherence.py` (paquete del lab, baker y runtime coherentes por arena), `tests/test_arena_data.py` (inicio y spawns libres para el cuerpo, composición del diseño) y `tests/test_navfield.py` (colisión y navegación compiladas en el host sobre cada arena).

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
- **Arquitectura de Profundidad Continua vs Capas Hardware:** Con estructuras altas continuas (muros, contrafuertes góticos) las capas de fondo fijas de hardware son insuficientes: el personaje debe ocluirse al norte del muro y mostrarse por delante al pisar el sur de su base. El motor dibuja actores directamente en la página trasera del framebuffer de VRAM (sin framebuffer en EWRAM ni DMA de pantalla completa) y limpia solo los spans sucios (`DirtySpan`, `dirty_row`/`dirty_rect` en `game.h`; `clear_dirty_spans` en `main.c`; el modo `DIRTY_VERIFY` comprueba fugas en `dirty_leaks`). La oclusión se consulta directamente sobre `g_arena->occlusion_runs` por fila (`find_hiding_run`, `occlusion_blocks_pixel`), exacta al píxel y sin mapa intermedio.
- **Las dos pantallas usan el mismo compositor.** `render_screen(buffer, spans, cam_x, cam_y)` se llama una vez por pantalla; la superior usa la cámara de la inferior desplazada `SCREEN_H` hacia arriba. El estado "jugador tras una pared" (`update_player_see_through`) se calcula una vez por frame a partir del jugador y vale para ambas.
  - **Inferior (motor principal):** suelo en BG1 (banco D, 1024 slots de tile) y páginas 16 bpp de actores en BG2 (bancos A y B), con doble búfer.
  - **Superior (motor secundario, banco C de 128 KiB):** tiles 0–28 KiB (448 slots, `TOP_TILE_CACHE_CAPACITY`), mapa del suelo en 28–32 KiB y una única página 16 bpp de actores en 32–128 KiB. No hay hueco para una segunda página, así que se dibuja justo después de la lógica, dentro del VBlank, y puede parpadear si el frame se alarga.
  - **Presupuesto de tiles:** cualquier ventana de pantalla (33×25 tiles) debe necesitar menos de 440 tiles distintos. El baker (`tools/bake_arena.py`) fusiona con pérdida los tiles casi idénticos hasta cumplirlo (umbral medio de color 1,0: 3804 → 1123 tiles, peor ventana 576 → 252). Lo comprueba `tests/test_upper_screen_contract.py`.
- **Regla Crítica de EWRAM (Prohibición de loops bit a bit):** La memoria principal EWRAM (4 MB) en Nintendo DS tiene bus estrecho y latencia de acceso con wait states. Prohibido terminantemente ejecutar bucles horizontales que realicen operaciones bit a bit no alineadas (`|= (1u << (index & 7))`) por píxel individual: un bitmask de pantalla completa bajo este patrón consume 12–15 ms por frame. Toda máscara debe procesarse por palabras alineadas (32 bits) o resolverse por consulta de tramos.
- **Compilación Obligatoria en Modo ARM 32-bit:** Por defecto BlocksDS compila código ARM9 en Thumb-1 (16-bit). Las funciones críticas de manipulación de memoria y rasterizado (`find_first_occlusion_run_in_row`, `blit_stride`, `draw_shadow_mask`) deben declararse explícitamente con `__attribute__((target("arm"), optimize("O3"), noinline))` para aprovechar instrucciones nativas de 32 bits (`LDRH`/`STRH`, `STMIA`) y evitar el estrangulamiento de registros.
- **Índice por Fila y Búsqueda Binaria en X:** Los tramos (`g_arena->occlusion_runs`) se ordenan por (y, x) y `g_arena->occlusion_row_start` delimita los de cada fila. `find_first_occlusion_run_in_row()` busca en binario el primer tramo que alcanza la X consultada; recorrer todos los tramos de la fila es demasiado caro.
- **Prohibición de Paddings Fantasma:** Prohibido aplicar márgenes de celda arbitrarios a las máscaras. Todo padding artificial crea volúmenes invisibles que recortan al personaje en el aire antes de tocar las siluetas arquitectónicas reales.
- **Contrato de Datos del Mapa (lab → baker → runtime):** `world.png`, `collision.png` y `occlusion_depth.png` se exportan del mismo modelo y la misma cámara (`tools/lab/export_map_package_headless.cjs`). `occlusion_depth.png` guarda por píxel la Y de mapa del punto de suelo bajo la superficie visible (R,G big endian) y B=255 si la superficie supera 0,25 m; el runtime oculta un píxel de actor si esa Y es mayor que la Y de sus pies. La colisión es la huella sobre el suelo de la geometría en la franja 0,30–1,20 m y es la única fuente de "suelo caminable". Verificación: `python tests/test_map_export_coherence.py`.

### 3.4. Efectos de armas, pase de suelo/luz y sandbox (2026-11-06, rama `proto/weapon-previews`)

- **Dos pases de suelo y luz:** `weapons_render_floor` se pinta antes de sombras y sprites (elipses 2:1 de `groundfx`, mitad trasera del aura que debe tapar el cuerpo) y `weapons_render_light` tras los sprites (columna de luz de la granada C). `weapons_render` pinta lo que tiene volumen encima. Se llaman una vez por pantalla con su cámara.
- **`groundfx`:** `gfx_ground_ring/arc/disc` y `gfx_light_column` trabajan en coordenadas de mundo con la métrica del suelo (dist² = dx² + 4·dy²). Oclusión por muros con `world_span_hidden` (por filas) y `world_pixel_hidden` solo si el tramo está parcialmente oculto; ese fue el arreglo que devolvió la granada C a 60 frames en el emulador.
- **Aura del francotirador:** pools de tamaño fijo (rayos K/C, chispas V), PRNG congruencial propio, seno y coseno por tabla de enteros, todo bucle de líneas con tope de pasos (un bucle sin tope en Bresenham congeló el juego una vez). Los rayos se regeneran cada 2-3 frames.
- **Sandbox:** buzón `g_sandbox` en RAM (offsets fijados por contrato en `include/sandbox.h` y `tests/test_sandbox_contract.py`), variantes de build `sandbox`, `playground` y `playground-perf` en `.ds-game-dev/project.json`. Un escenario escribe el buzón (`poke` por nombre de campo), espera el `ack` y captura. Patrón genérico en la skill `ds-game-dev` (`references/sandbox-pattern.md`).
- **Volumen de impacto del rayo del francotirador** (`include/hitvolume.h`, rama `fix/sniper-hit-side`): el rayo vuela a la altura del cañón y el puntero se lee en pantalla, así que el test es en espacio de pantalla con una elipse de cuerpo (centro 14 px sobre los pies, semiejes 15×18, enteros). La elipse de suelo `ENEMY_HIT_RADIUS` (11×5,5 px) cubría solo el 22-39 % de los píxeles del sprite y queda para perdigones. Deuda: los perdigones de la escopeta siguen con la elipse de suelo (misma limitación, abanico de perdigones lo compensa); la granada es de área en suelo y no se ve afectada. `g_enemies` (antes `s_enemies`) es global para que los escenarios lo lean por símbolo.
- **Selectores de depuración:** `SELECT` (estilo A/B/C) e `Y` (aura K/C/V). Se retiran cuando se elijan las variantes definitivas.


## 4. Deuda Técnica Pendiente (auditoría 2026-11-02)

Origen: `walkthroughs/audit-saneamiento-2d3d/`. Lo ya resuelto (colisión/oclusión coherentes con el render) está en `walkthroughs/map-export-coherence/`. Se referencian funciones, no líneas, porque se desplazan. Al cerrar un punto, borrarlo de aquí y registrarlo en `STATUS.md`.

### 4.1. Proyección y render 2.5D
- **Escala personaje/mapa (decidido 2026-11-07, `DESIGN.md` §6.9.1b).** Hasta la 0.3.1 el mapa estaba a 40,42 px/m con sprites de ~30 px, es decir, un personaje de ~0,75 m. Decisión: el marine mide 2 m (31 px de alto), así que **el mapa pasa a ~17,9 px/m** y los sprites no cambian de tamaño; la escena se renderiza con ese factor al construir el suelo. Hay que adaptar los exportadores del lab (que fijan la escala por la caja del modelo, no por los ajustes: medir y re-renderizar hasta clavar el px/m) y el kit de la franja.
- Resuelto (ver `STATUS.md`): la pantalla superior ya dibuja actores, sombras, proyectiles y FX con el mismo compositor que la inferior (`render_screen` se ejecuta una vez por pantalla, §3.3).
- **Transparencias tras paredes:** diseño sin decidir; ver §4.6.
- Resuelto (ver `STATUS.md`): movimiento/colisión isotrópicos en suelo (`GROUND_DY2`, elipse 6×3), ancla única exportada, oclusión exacta por consulta directa de tramos (sin mapa 4×4 ni reconstrucción por cámara).

### 4.2. Gameplay
- Fallback de spawn de `encounters_spawn_wave` con coordenadas del mapa antiguo (380,227) y centinela `anchor == (0,0)`; el generador de oleadas por "plantas" se sustituye por arenas en la Fase D.
- `los.c` bloquea la visión con `flags == 3`, las balas con el bit `0x02` y los cuerpos con el `0x01`. Para decidir si un enemigo puede disparar o morder usa `bullet_line_is_free` y `line_is_walkable` (`collision.c`), no solo la visión.
- Resuelto (ver `STATUS.md`, v0.1): lead del tirador, i-frames, pickups, navegación BFS (`navfield.c`), mordisco a través de muros.

### 4.3. Código muerto y acoplamiento
- `tools/convert_iso_to_c.py` (invocado por `tools/build-view.ps1`) todavía emite `dungeon_data`; ejecutarlo volvería a meter ~737 KB en la ROM. Separar su salida de `player_sprite`.

### 4.4. Tests, escenarios, docs y repo
- Los escenarios atados al mapa viejo (`dungeon_walk_tour`, `fbx_bg_ring_scroll`, `integration_showcase_walk`, `wall_junction_closeup`, `map_occlusion_collision_coherence`) se eliminaron con él. `assets/sprites/dungeon/isometric_shooter_bl/` y `assets/models/environment/blockout/` quedan solo como referencia histórica; ningún build los usa.
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

### 4.7. Requisitos técnicos de la v0.3: horda y franja vertical (2026-11-06)
Diseño en `DESIGN.md` §6. Esto es lo que el motor actual no cubre y cómo se mide.

**Cómo manejaba los enemigos la v0.2 (revisado 2026-11-06):**
- **Total:** array fijo de `MAX_GAMEPLAY_ENEMIES` = 24 (`gameplay.h`). En la v0.2 todos existen desde el principio y los `DORMANT` no ejecutan IA.
- **Lógica:** `enemy_ai_update` ejecuta IA, movimiento y colisión de todos los despiertos, estén o no en pantalla. `apply_separation` compara cada enemigo con todos (O(n²)). El cargador comprueba la línea de visión (`los_has_line_of_sight` y `line_is_walkable`) cada frame.
- **Dibujo:** `render_screen` solo añade los enemigos visibles en esa pantalla. Cada uno es un blit 40×40 a 16 bpp con sombra y oclusión por píxel.
- **Navegación:** `navfield` cubría 48×48 nodos de 16 px (mapa de 768×768 como máximo). En la 0.3 mínima pasó a 48×128 (abajo).
- **Coste medido en la DS (v0.2, unos 8–12 despiertos):** `en` 55–60 k ticks y `blit` 63–74 k ticks por frame, con el frame total en 300–411 k de 560190 (`walkthroughs/v0.2/`). Extrapolado a lo bruto, unos 35 enemigos se pasan del presupuesto con el motor tal cual.

**Cambios previstos para la horda:**
- **Pool:** unas 48 plazas que se reciclan. Los enemigos nacen fuera de la vista y se liberan al morir, al quedar muy atrás o al tragárselos la marea. El total de la run no ocupa memoria.
- **IA por niveles de detalle:** los enemigos lejanos o fuera de pantalla se actualizan cada 2–4 frames, sin comprobar la línea de visión y bajando por el campo de distancias.
- **Separación con rejilla espacial:** cada enemigo solo mira a sus vecinos de celda.
- **Blit más barato:** sprites con paleta de 8 bpp en lugar de 16 bpp, y oclusión saltada cuando el sprite no toca ningún tramo de oclusión (en la franja, casi siempre).
- **Gemas y pickups en OAM:** sprites hardware de 8×8 o 16×16, sin coste de CPU. Hay 128 entradas y el HUD también usa algunas.

**Criterio de la prueba de horda (se mide en la 0.3.1 y se cumple en la 0.5, `DESIGN.md` §6.9):** 60 FPS certificados en la DS (`AGENTS.md` regla 6) con **32 enemigos visibles entre las dos pantallas y 48 activos**, disparando sin parar y con los efectos de armas activos, durante al menos 2 minutos de log. Si no se llega optimizando el compositor actual, se evalúa dibujar el enjambre con OAM o con el motor 3D (quads con textura y orden de profundidad por hardware) antes de seguir.

**Lo que implementó la 0.3 mínima (2026-11-06, `walkthroughs/v03-minima/`):**
- **Franja en ventana:** `g_arena` es una ventana en RAM de 512×2048 px de una franja infinita (`source/strip.c`). Las bandas de 128 px salen de un hash de (semilla, banda) con el kit horneado de `source/strip_kit.c`. Cuando el jugador pasa de y=768, la ventana baja 512 px (rebase) y `strip_shift_world_y` desplaza toda Y viva: jugador, enemigos, proyectiles, armas, granada, horda, marea, curas y navegación.
- **Navegación:** `navfield` de 48×128 nodos de 16 px. En el rebase se desplaza el campo (`nav_shift_down`) en vez de rehacerlo.
- **Horda** (`source/horde.c`) sobre el pool de 24 (`MAX_GAMEPLAY_ENEMIES`), con reciclaje sin recompensa. La IA de siempre, con un flag de modo franja.
- **Marea** (`source/tide.c`): WIN0 con fundido a negro por hardware (`REG_BLDCNT` modo 3, `BLDY`), sin coste de CPU por píxel.
- **Medido en la DS:** CPU media de 219.000 ticks (39 %) y máxima de 489.882 (87 %). Picos de `en` 115.000 y `proj` 106.000. Sin frames perdidos salvo la escritura del log. Aún no aplica nada de los "cambios previstos" de arriba (pool de 48, IA por niveles de detalle, rejilla, 8 bpp).
- **Escenarios:** `strip_climb_smoke` y `strip_horde_tide` leen `g_strip_debug[4]` = {altura en px, rebase acumulado, enemigos vivos, vida}.

**Franja vertical (pendiente):**
- Los tramos hechos a mano de la 0.6 sustituirán a las bandas procedurales; la ventana con rebase se mantiene.
- El baker ya cumple el presupuesto de tiles por ventana (§3.3), que no depende del tamaño total. Los tramos repetidos comparten tiles. ROM orientativa: la mazmorra de 768×768 ocupa unos 83 KB; una franja de 384×6000 px debería quedarse en pocos cientos de KB.
- **Timestep (§4.5):** con horda, una caída a 30 FPS pone el juego a media velocidad. Conviene resolverlo antes del tuning.
