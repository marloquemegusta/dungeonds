# STATUS.md - Estado Actual e Historial Reciente de DungeonDS

Primero el estado necesario para retomar el trabajo sin depender del chat; después, las entregas recientes verificadas (más nueva al final). El historial hasta 2026-10-21 está en `STATUS-ARCHIVE.md`.

## Estado actual (2026-11-13)

- **Profiling de estrés de enemigos (`perf/stress-enemies`, `walkthroughs/stress-enemies-profiling/`):** medido en Nintendo DS física con `PERF_PROFILE=1`. Con sombras suaves actuales, 48–72 enemigos caen a **20 FPS** (`34,3–36,5 ms`, de los cuales **15,8 ms** son solo sombras por lectura píxel a píxel del suelo). Sin sombras: **30–38 FPS** (`17,3–21,1 ms`). Con sombras negras alternadas (30 Hz): techo de **60 FPS** en **18–20 enemigos** (`8,8–11,7 ms` de media, pico `13,9 ms`), aunque el parpadeo de las sombras a 30 Hz se nota en pantalla real. Queda pendiente una sesión específica de rendimiento (sombras, picos de rebase/proyectiles y logger `PERF_PROFILE` con NitroFS).

- **Fix de parpadeo en pantalla superior (`fix/top-flicker`, `walkthroughs/top-flicker-fix/`):** reordenado el bucle principal en `source/main.c` para renderizar la pantalla inferior (doble búfer) antes de `swiWaitForVBlank()` y pintar `s_top_page` (búfer único) nada más empezar el VBlank. Validado en tests de host (`5/5` + `58/58`) y en Nintendo DS física por el usuario.

- **Recorte de sprites y sombras (`perf/crop-sprites-shadows`, `walkthroughs/crop-sprites-shadows/`):** `tools/generate_player_sprites_c.py` recorta sprites BGR555 y máscaras de sombra 4 bpp a su bounding box con tablas de offsets/bounds; `dungeonds.nds` baja de **2,74 MiB a 1,00 MiB (-63,5 %)** sin pérdida visual. Validado en tests de host (41/41), DeSmuME y Nintendo DS física.

- **Marea elástica (`feat/tide-spring`, integrada en `main`, SIN PROBAR):** velocidad adaptativa según la distancia al jugador (`DESIGN.md` §6.4: frena cerca, acelera lejos y reduce la velocidad del jugador un 25 % dentro de ella). Compilación pendiente de verificar en DeSmuME y en la Nintendo DS física.
- **Telegrafía sobria del Cireneo (`feat/cireneo-telegraph`, integrada en `main`):** retirado el parpadeo en `ENEMY_STATE_TELEGRAPH`; agachado progresivo en 3 fases con keyframe `cireneo_telegraph` (`60×60`), pulso único de brasa tras la cruz y temblor de 1 px. Validado en DeSmuME y tests de host (`walkthroughs/cireneo-telegraph/`); pendiente de probar en la DS.
- **BSO de combate en streaming (`feat/bgm-loop`, 2026-11-13, `walkthroughs/bgm-loop/`):** música tecno/gregoriana (`cathedral_battle_loop`, 21,6 s @ 11.025 Hz) en streaming por NitroFS (`nitro:/bgm.raw`) + Maxmod (`mmStreamOpen`, buffer 2 KB), y los 5 SFX migrados a `soundbank.bin` en NitroFS. Validado en DS por el usuario. Reservado `assets/music/boss_climax_loop.wav` (28,8 s) para jefes.
- **SFX base del Corazón Abierto (2026-11-13, `walkthroughs/sfx-core/`):** 5 sonidos base (carga, fuego sagrado, hit enemigo con jitter ±12%, muerte por combustión y daño al jugador con quejido) vía Maxmod + NitroFS con panning por cámara y cooldowns anti-spam. Validado en DS por el usuario. Pendiente: granada, telegrafías enemigas (láser/embestida), muro y pickups.
- **VFX del Corazón Abierto (2026-11-13, `walkthroughs/corazon-vfx-paleta/`):** paleta `FX_SH_*` desaturada y cálida (marfil, oro antiguo, ámbar, terracota, carmesí, sangre seca y ceniza cálida) + bordes tramados/atenuados en láser de carga/disparo, chispas y las cuatro auras (`L`, `G`, `E`, `H`), junto con anillos de suelo discontinuos. Validado en DS por el usuario. Pendiente: elegir aura definitiva y quitar el selector `Y`.
- **El Corazón Abierto, héroe (2026-11-12, en `main`):** sustituye al marine. Andar de Mixamo, carga/disparo con brazos en cruz, rayo desde el pecho, haz «fuego» y cuatro auras de carga en comparación (`Y`: llamas, resplandor, espinas, ceniza). Jugado en la DS por el usuario con la catedral v2: va bien (sin log de `PERF_PROFILE`). Pendiente: elegir aura y quitar el selector `Y`. Detalle: `walkthroughs/corazon-abierto/`; diseño en `DESIGN.md` §6.10.
- **v0.3.1 cerrada (2026-11-07, `walkthroughs/v031-tuning/`):** tres tiers de enemigos (esqueleto, cargador que carga, tirador láser), escala de cifras 100 = 1,0 y pulido de suelo y marea. Jugada en la DS: rendimiento bien y el juego se siente mucho mejor. Pool de 24; el techo 32/48 y el log de `PERF_PROFILE` no se hicieron (`DESIGN.md` §6.9.1, "Valores de la 0.3.1").
- **Props: oclusión y colisión resueltas (2026-11-10).** La profundidad de los props estaba en píxeles del render fuente, no en píxeles de mundo. Además, los bancos toman ahora como huella toda su planta. El usuario lo probó en la DS y lo dio por bueno. Detalle: `walkthroughs/props-depth-units/`.
- **Catedral 0.3.2 v2 (2026-11-12, `walkthroughs/catedral-v2-salon/`):** planta de salón con el muro 3D del usuario, lápidas v5 encajadas en el damero, compositor por pantalla (columnas con velas, bancadas o relicario, lápidas) y godrays desde la cara del muro (retirados el parpadeo y la línea negra tras muros). Rebase preparado por trozos: medido en la DS, peor frame al 72 % y sin parpadeo. Herramienta de diseño: `tools/catedral_editor/editor.html`. Pendientes: escala de piezas, caballero más legible y variedad de tramos. `walkthroughs/distribucion-catedral/BRIEFING-SIGUIENTE.md` queda sustituido.
- **v0.3 mínima jugable (2026-11-06, `walkthroughs/v03-minima/`):** la ROM principal arranca en la franja vertical infinita con horda desde arriba, marea, curas y HUD de altura (`DESIGN.md` §6.0). 60 FPS en la DS con el pool de 24. **Cerrada.** El resto de §6 (gemas, mejoras, élites, jefes) sigue sin código y está repartido por versiones en `DESIGN.md` §6.9.
- **Dirección vigente (v0.3, decidida 2026-11-06):** survivors de frente vertical con apuntado manual. Un nivel de ~8 min en una franja vertical que se sube mientras una marea avanza desde abajo, horda continua, gemas → nivel → elegir 1 de 3 mejoras, élites, minijefe y jefe, y **cada personaje tiene su única arma** (no hay múltiples armas por personaje; los cambios de arma con `L`, estilo con `SELECT`, aura con `Y` o cambios de animación en la ROM actual son **solo para depuración**). Diseño en `DESIGN.md` §6; requisitos técnicos en `TECHNICAL.md` §4.7. Sesión: `walkthroughs/survivors-direction/`.
- **Rama base:** `main`, con v0.1 (`walkthroughs/v0.1/`) y v0.2 (`walkthroughs/v0.2/`) integradas. La v0.2 se integró con la deuda de rendimiento anotada abajo.
- **Juego (v0.2, en `main`, sustituida en diseño por la v0.3):** una mazmorra de 768×768 con 6 manadas dormidas (22 enemigos), 8 modificadores estilo Isaac con coste, curación de 1 golpe por manada, HUD de run, reinicio total al morir (`DESIGN.md` §5). Jugada en la DS: más divertida que la v0.1 pero se agota en un par de minutos. El código sigue en `main`, pero la ROM principal ya no la arranca.
- **Juego (v0.1, base de la v0.2; sustituida por la mazmorra):** prueba de diversión en 4 arenas cerradas de 384×384 px encadenadas (`DESIGN.md` §4): escopeta + francotirador, cargador (con navegación BFS) + tirador (telegraph y ráfagas de 3). Pendiente la Fase E: tuning y 60 FPS certificados en la DS.
- **Arenas:** datos en `assets/arenas/arenas.json`; generador de modelos, export con el lab y baker (`tools/make_arena_glb.py`, `tools/export_arenas.py`, `tools/bake_arena.py`) descritos en `TECHNICAL.md` §3. El mapa grande `isometric_shooter_bl` ya no se usa.
- **Render:** actores dibujados directamente en la página trasera del framebuffer de VRAM, limpieza por spans sucios y oclusión exacta al píxel por consulta de tramos (`TECHNICAL.md` §3.3). Medido en DS: CPU 1,58 ms de media y 12 de 2520 frames con más de un vblank.
- **Personajes:** héroe (`CHAR_HERO`: Corazón Abierto; el space marine queda sin uso), charger (`CHAR_CHARGER`: Cireneo v2 a 60×60 con clips de carga agachado y telegrafía), necron (`CHAR_NECRON`) y esqueleto (`CHAR_SKELETON`), exportados por el lab a `assets/sprites/characters/<nombre>/`. El lab puede tomar el `muzzle` de un hueso (`--muzzleBone`).
- **Sin existir en código:** iluminación dinámica, niebla de guerra.
- **Herramientas de diagnóstico en DS:** `PERF_PROFILE` (`include/perfprof.h`, log `/dungeonds_perf.log`) y `crashlog` (`CRASHLOG_ENABLED`, logs `/dungeonds_crash.log` y `/dungeonds_live.log`). Ambas apagadas por defecto; se leen con `fetch-device-log.ps1` de la skill.

### Siguientes pasos
Hoja de ruta por versiones en `DESIGN.md` §6.9; cada versión es una sesión y una rama.
1. **0.3.1, tuning y pulido:** cerrada (arriba). Quedan pendientes, anotados en `DESIGN.md` §6.9.1: techo de la horda 32/48, marca visual del aturdimiento, cruz de cura, vida en el HUD de la franja y láser tras muros altos.
   - **0.3.2, escenario del primer nivel** y **0.3.3, personajes** (`DESIGN.md` §6.9.1b), antes de la 0.4.
2. **0.4, progresión (tras la 0.3.3):** gemas, nivel, 1 de 3 mejoras y clases. Antes, una sesión de diseño de mejoras.
3. **0.5:** enjambre, élites, cofres y emboscadas, con pool de 48 (`TECHNICAL.md` §4.7).
4. **0.6:** tramos a mano, biomas, minijefe y jefe. Cierra la prueba de §6.1.

Siguen abiertos, sin prioridad frente a la hoja de ruta:
- Timestep y deuda del motor (`TECHNICAL.md` §4.5). El timestep se adelanta si la 0.3.1 mide caídas a 30 FPS.
- Escala personaje/mapa (§4.1).
- Data abort intermitente (§4.4).
- Transparencias (§4.6), fuera de la v0.3.

Los pasos de cierre de la v0.2 (modificadores, pedestales, mazmorra más grande) se descartan.

### Ramas aparcadas (se borran si caducan)
- **`feat/v03-mazmorra`** (commit `1e4973d`, sin worktree). Trabajo de la sesión del 2026-11-04/05 (mazmorra de 1280×1280 y luz oscura), guardado como WIP. Nunca se probó en la DS ni se revisó, y la dirección cambió a la v0.3 survivors. **No es una base: como mucho, una cantera.**
  - **Quizá útil en el paso 3 (franja vertical):** `navfield` a 80×80 con distancias `uint16`, sin `/` ni `%` por nodo y con límite de profundidad (`NAV_MAX_DEPTH`); `BG_MAX_TILES` 4096; `solve_frame` analítico y `normalize_blocks` (bloques sin costuras) en `tools/make_arena_glb.py`; `export_arenas.py`, que aclara los píxeles negros del suelo para que el baker no los tome por vacío; y `tools/gen_dungeon_layout.py` como idea para el generador de tramos (está pensado para salas, no para tramos). Hay que revisar y medir todo antes de traerlo.
  - **No rescatar:** el mapa de 1280 y sus manadas; los sprites re-renderizados, cuya luz no se aprobó (el brillo de contorno parecía escarcha); y su `DESIGN.md` §6, que contradice el vigente. El lab y la luz se están rehaciendo en otro worktree, así que no se toman de aquí.
  - **Caducidad:** borrar la rama (`git branch -D feat/v03-mazmorra`) en cuanto el paso 3 rehaga esas piezas por otro lado o, en todo caso, si el **2026-12-06** no se ha usado nada de ella.

---

## 2026-11-02 - Colisión y Oclusión Coherentes con el Render del Mapa

### Resumen
- Auditoría completa del juego en `walkthroughs/audit-saneamiento-2d3d/`: el 65 % de la oclusión caía sobre vacío y la colisión creaba muros invisibles tras las coberturas.
- El lab exporta `occlusion_depth.png` (Y de contacto con el suelo por píxel, mismo pase que `world.png`) y una colisión por huella en la franja corporal 0,30–1,20 m.
- Baker con profundidad exacta e índice de runs por fila; runtime recorre sólo runs visibles (sin caídas a 30 FPS) y usa la rejilla como única fuente de suelo.
- **Validación:** build limpia; escenario `map_occlusion_collision_coherence.json` PASS; `test_map_export_coherence.py` OK. Detalle: `walkthroughs/map-export-coherence/walkthrough.md`.

---

## 2026-11-02 - Saneamiento 2D/3D (suelo isotrópico, código muerto, repo)

- Movimiento y colisión en suelo 2:1, ancla de suelo única, oclusión 4×4 sin histéresis (2×2 descartada por FPS); parpadeo del jugador ocluido intacto por diseño.
- Eliminados `dungeon_data` (-722 KB de ROM), lanzas óseas legacy, hitscan/campos sin uso; `enemy_hit` y colisión movidos a `gameplay.c`; `sweep_position` sin int64.
- 22 escenarios y 9 generadores obsoletos fuera; docs y tests del lab actualizados.
- **Validación:** build limpia; escenarios PASS (coherencia recalibrada, fire_*, room_encounter, weapons, dismemberment); rendimiento sin regresión relativa. Detalle: `walkthroughs/saneamiento-2d3d/`.
- Pendiente: escala personaje/mapa, actores en pantalla superior, §4.2 gameplay (diferido).

- Pendiente: un data abort intermitente en hardware sin causa identificada y otras anomalías por revisar; herramienta de diagnóstico `crashlog` disponible (desactivada por defecto, ver `TECHNICAL.md` §4.4).

---

## Sesión: Fix de oclusión de actores (2026-11-03)
- [x] Máscara de oclusión exacta al píxel (`s_occlusion_cover`), sin bloques de suelo en siluetas.
- [x] La transparencia del jugador tras una pared también muestra a los enemigos ocluidos.
- [x] Sombra y borde de huella de colisión visibles mientras dura la transparencia.
- [ ] Pendiente: escenario con enemigo tras la pared y medida de frame en hardware.
- **Evidencia:** `walkthroughs/fix-oclusion-siluetas/walkthrough.md`.

---

## Sesión: Auditoría del motor 2D/3D y prototipo A (2026-11-03)
- [x] Perfilado en DS real (`PERF_PROFILE`): coste concentrado en limpiar/copiar 96 KB y reconstruir el mapa de oclusión por movimiento de cámara.
- [x] Prototipo A (`proto/compositor-a`): dibujo directo en VRAM + spans sucios + oclusión por consulta directa de tramos; CPU 12,03 → 1,58 ms de media, frame 18,93 → 16,54 ms, frames con >1 vblank 226/1500 → 12/2520.
- [x] Regla 5 de `AGENTS.md` corregida (umbral 560190 ticks / vblanks, no 33514).
- [ ] Pendiente: rediseño de transparencias (parpadeo temporal), timestep, assets, pipeline y acoplamiento (`TECHNICAL.md` §4.5); validación visual en la DS por el usuario.
- **Evidencia:** `walkthroughs/audit-motor-2d3d/walkthrough.md`.

---

## Sesión: Diseño de gameplay mínimo (2026-11-03)
- [x] Entrevista de diseño: `DESIGN.md` §1 y §4 reescritos como prueba de diversión mínima (2 armas, 2 enemigos, 3–4 arenas cerradas, sin loot/munición/pickups/generador).
- [ ] Pendiente: forma de los mapas de arena y sonido (`DESIGN.md` §3); implementación por fases (§4.8).
- **Evidencia:** `walkthroughs/diseno-gameplay-minimo/walkthrough.md`.

---

## Sesión: v0.1 prueba de diversión mínima (2026-11-03)
- [x] Fase A: escopeta y francotirador, disparo desde la boca del arma (exportada por el lab), salud en golpes, i-frames, hitstop, temblor, FX procedurales y pantalla superior igual que la inferior (sin regresión de FPS en la DS: 0,57 % de frames de más de un vblank).
- [x] Fase B: cargador con campo de distancias BFS incremental, activación total al empezar.
- [x] Fase C: tirador necrón con banda de distancia, telegraph y ráfaga de 3 desde la boca.
- [x] Fase D: 4 arenas (modelos generados, lab, baker), runtime multi-arena, encuentros por arena y fundido.
- [ ] Fase E: tuning en la DS y certificación de 60 FPS; medir `nav_update` y el segundo pase de render con `PERF_PROFILE`.
- **Evidencia:** `walkthroughs/v0.1/walkthrough.md`.

## 2026-11-06 - Granada, variantes de armas y aura de carga (rama `proto/weapon-previews`, sin mergear)

Granada como tercera arma (`L`), variantes de efectos A/B/C de escopeta, francotirador y granada (`SELECT`), aura de carga del francotirador K/C/V (`Y`), regla de perspectiva del suelo 2:1 (`groundfx`), sandbox con ROM `playground` para comparar en la consola. Decisiones en `DESIGN.md` §4.9. Validado en DeSmuME y tests de host; rendimiento probado en la DS con `playground-perf` (el usuario reporta que va bien). Detalle y GIFs: [walkthrough](walkthroughs/weapon-previews/walkthrough.md).

## 2026-11-06 - Colimado del láser del francotirador (rama `feat/sniper-collimation`, sin mergear)

El láser de apuntado se colima durante la carga (ancho, difuso y rojo a 1 px verde estable) en los estilos A/B/C; decisión en `DESIGN.md` §4.9. Tests de host y escenarios del sandbox OK, 0 warnings; **pendiente certificar 60 FPS en la DS** con `playground-perf`. Detalle y GIFs: [walkthrough](walkthroughs/sniper-collimation/walkthrough.md).

## 2026-11-04 - v0.2: Mazmorra de Manadas con Modificadores

### Resumen
- Tras jugar la v0.1 en la DS ("se juega bien pero no es divertido, y es fácil") se decidió la dirección en `DESIGN.md` §5: mazmorra grande de manadas dormidas estilo Diablo, modificadores con compromiso estilo Isaac, reinicio total al morir.
- Mapa de 768×768 con seis salas generado por el pipeline lab → baker (999 tiles únicos, máximo 237 por ventana de 33×25, 3133 runs de oclusión, unos 115 KB en ROM; sombras del lab con la misma luz que los personajes).
- Manadas `DORMANT` que despiertan juntas, 8 modificadores con coste, HUD siempre visible, curación por manada y banner de mazmorra completada.
- Arreglos incluidos: los proyectiles enemigos se ocultan tras muros y los enemigos miran hacia donde caminan.
- **Validación:** build limpia, todos los tests de `tests/`, escenarios `dungeon_pack_wakes_near_player` y `dungeon_pack_reward_pedestals` y los de v0.1 que siguen vigentes. Pendiente la DS. Detalle: `walkthroughs/v0.2/walkthrough.md`.
- **Feedback tras jugarla en la DS:** más divertida que la v0.1; gráficos bien. Pendiente tuning de daños y stats, claridad de los modificadores, pedestales y UI provisionales, y una mazmorra más grande con salas diferenciadas (`DESIGN.md` §5).
- **Deuda abierta:** 60 FPS sin certificar (0,89 % de frames con más de un vblank, tramos de hasta ~410 k ticks con varias manadas). Integrada a `main` por decisión del usuario; primer paso de la siguiente sesión.
- **Sin uso en el repo:** `assets/sprites/dungeon/isometric_shooter_bl` y `blockout` (mapa viejo, se dejan como referencia por decisión del usuario).
- **No leído:** el log de rendimiento de la última ROM (luz nueva) no se pudo descargar al estar cerrado `ftpd.nds`.

---

## 2026-11-05 - Lab: carga y cambios de ajustes sin cuelgues

- Desde `f2af500` el lab regeneraba el atlas de sombras 8×8 al cargar y en cada cambio de la interfaz, con un `closePath()` por triángulo en una sola ruta de canvas: ~325 s al cargar el marine y la ventana colgada al cambiar un preset.
- `generateCharacterShadows` cierra los triángulos con `lineTo` (extremos redondeados) y `renderLiveFrame` solo regenera las sombras si cambia la geometría, pose o cámara (no la luz ni el grading).
- **Validación:** carga del marine en 5,6 s con GPU headless; atlas de sombras del cargador igual al anterior salvo 619 de 39.048 píxeles de borde.

## 2026-11-06 - Francotirador: volumen de impacto del rayo (`fix/sniper-hit-side`)

- El rayo acertaba solo en 22-39 % del sprite (elipse de suelo sin altura); ahora usa una elipse de cuerpo en pantalla (88-98 %, `include/hitvolume.h`). Escenarios `sniper_hit_sweep_west/east` fallan con la fórmula vieja y pasan con la nueva. Escopeta con la misma limitación, anotada en `TECHNICAL.md` §3.4. Pendiente validar en la DS. Detalle: [`walkthroughs/sniper-hit-side/`](walkthroughs/sniper-hit-side/walkthrough.md).

---

## 2026-11-06 - Dirección v0.3: survivors de frente vertical (`docs/survivors-direction`)
- Sesión de diseño, sin código. La v0.2 divertía un par de minutos pero no tenía un "y luego qué". Se eligió un survivors con apuntado manual adaptado a la DS: franja vertical, marea que sube desde abajo, pantalla superior como vanguardia a la que se dispara, clase = arma y economía de gemas → nivel → 1 de 3 mejoras.
- `DESIGN.md` §1, §3 y §6 nuevos (v0.1 y v0.2 marcadas como historia); `TECHNICAL.md` §4.7 con cómo maneja hoy el motor los enemigos y el criterio de la prueba de horda.
- Detalle y opciones descartadas: `walkthroughs/survivors-direction/walkthrough.md`.

---

## 2026-11-06 - v0.3 mínima: franja vertical infinita (`feat/v03-minima`)
- La ROM principal arranca en modo franja (`DESIGN.md` §6.0): mapa infinito de 512 px de ancho generado por bandas con el kit cian de la mazmorra, horda que baja desde arriba, marea de oscuridad por hardware, curas y HUD de altura y tiempo. Sandbox y playground siguen con sus arenas.
- Validación: build sin warnings, 154 tests de host, escenarios `strip_climb_smoke` y `strip_horde_tide` PASS. En la DS, CPU media del 39 % y máxima del 87 %, sin frames perdidos salvo la escritura del log. El usuario la juega y "se siente como un juego real".
- Detalle: [`walkthroughs/v03-minima/`](walkthroughs/v03-minima/walkthrough.md).

---

## 2026-11-07 - Hoja de ruta por versiones: 0.3.1 → 0.6 (`docs/roadmap-v031`)
- La 0.3 mínima se da por cerrada. `DESIGN.md` §6.9 sustituye el plan por pasos por versiones jugables:
  - **0.3.1:** tuning y pulido;
  - **0.4:** gemas, nivel, mejoras y clases;
  - **0.5:** enjambre, élites, cofres y pool de 48;
  - **0.6:** tramos, biomas y jefes.
- Cada versión con diseño previo empieza por su sesión de diseño (regla 9). Alcance detallado de la 0.3.1 en §6.9.1.
- `TECHNICAL.md` §4.7 recoge lo que ya implementó la 0.3 mínima (franja en ventana con rebase, navegación de 48×128, pool de 24 medido). El ancho de la franja se fija en 512 px (`DESIGN.md` §6.2).
- Detalle: [`walkthroughs/roadmap-v031/`](walkthroughs/roadmap-v031/walkthrough.md).

---

## 2026-11-07 - v0.3.1: tres tiers de enemigos, escala de cifras y pulido (rama `feat/v031-tuning`, fusionada en `main`)

### Resumen
- Vida y daño en centésimas (100 = 1,0); armas ×5. Tres tiers: esqueleto (100 de vida, velocidad 130, 60 % de la horda, modelo nuevo desde el FBX del inbox), cargador con telegrafía, carga recta y aturdimiento (por choque, escopeta o granada) y tirador con láser verde (carga, fijado, disparo). Decisión en `DESIGN.md` §6.9.1.
- Pulido: luz neutra del kit de la franja (suelo ya no marrón) y borde de la marea de 3 px fuera del fundido. Los `dungeon_pack_*` se movieron a `scenarios_legacy/dungeon_v02/` (no se borraron).
- **Validación:** build 0 warnings, 172 tests de host y escenarios `strip_*` y `enemy_*` en PASS. **Subida a la DS y jugada por el usuario:** rendimiento bien, sensación mucho mejor. **Sin hacer:** log de `PERF_PROFILE`, techo de la horda 32/48, cruz de cura, vida en el HUD y marca visual del aturdimiento (anotados en `DESIGN.md` §6.9.1). Siguen 0.3.2 (escenario) y 0.3.3 (sprites), estilo Trench Crusade / Warhammer 40k sombrío (§6.9.1b). Detalle: `walkthroughs/v031-tuning/walkthrough.md`.

## 2026-11-09 - v0.3.2: escenario de la catedral (rama `feat/v032-escenario`, fusionada en `main`)
- **Decidido:** personajes sin contorno; suelo Tripo A (`rombos_tripo`, 92 tiles); luz key 55°/30° con sombras de piezas y marine alineadas; lápidas de suelo sustituyen losas, rombos enteros, sin sombra sobre el suelo ni contorno pintado. Kit horneado con `tools/bake_cathedral_kit.py` (suelo + 5 lápidas = 882/1024 tiles; tope real 1024; compactación y remapeo de paleta corregidos). Catálogo en `tools/catalogo/`. `BIBLIA.md` §6 corregida.
- **Probado, sin decidir:** lápida hundida vs a ras (la 3D hundida de 192 tiles no quedó bien; en la ROM va cluster + junta de 1 px), ahorros de tiles, reorden de `assets/` (`REORDEN_ASSETS.md`).
- **Sin hacer:** medición en la DS (`PERF_PROFILE`), limpieza manual del inbox, soporte de `lapida3d_*` en el baker.
- Detalle: [`walkthroughs/v032-escenario/`](walkthroughs/v032-escenario/walkthrough.md).

---

## 2026-11-09 - v0.3.2 (continuación): Solución Unificada de Lápidas en Shader Lab
- **Diseño geométrico resuelto:** la lápida **es** la losa. Se eliminaron los stickers 2D y los cajeados oscuros con corte booleano. La pieza sustituye exactamente un bloque de teselas completas con la junta de mortero estándar de la catedral (`JOINT = 0.026 m`).
- **Pipeline 100% unificado en Three.js Shader Lab (`tools/lab/export_map_package_headless.cjs`)**: todo el renderizado visual pasa por la misma cámara (30° elevación, 45° azimuth) y la misma luz neutra que los personajes y el suelo. Blender actúa exclusivamente como ensamblador geométrico exportando a GLB (`tools/floor/build_lapidas_lab_blender.py`).
- **Modelos Tripo v2 con relieve escultórico realzado (12 cm)**: tanto el caballero yacente como la cruz con espada empotrada mantienen su volumen tridimensional completo sin aplastamiento, proyectando sombras de contacto y brillos marmóreos bajo la luz canónica.
- **Color nativo BGR555**: preserva los 15 bits de precisión de hardware de la Nintendo DS sin comprimir los tonos en la paleta oscura del suelo.
- **Lámina comparativa maestra:** [`cat_lapidas_lab_unified.png`](walkthroughs/v032-escenario/assets/cat_lapidas_lab_unified.png) comparando Vía A (3×2 teselas = 80×40 px) y Vía B (3×3 teselas = 96×48 px) con macro 4x y mapas de costura.
- **Siguiente paso para otra sesión:** hornear las variantes definitivas en `tools/bake_cathedral_kit.py`, actualizar el strip kit y validar 60 FPS en la Nintendo DS física con `PERF_PROFILE`.

## 2026-11-09 - 0.3.2: composición espacial y layout de la catedral (`docs/layout-catedral`)
- **Propuesta:** recorrido, altura lógica, familias de composición y reglas de distribución, en `DESIGN.md` §6.9.1b.
- **Walkthrough:** [`walkthroughs/layout-catedral/walkthrough.md`](walkthroughs/layout-catedral/walkthrough.md) muestra 12 pantallas, ocho con posiciones concretas y las cuentas de pasillos/huella.
- **Estado:** el usuario dio paso a la sesión 2 con este layout como base; la validación visual en ROM se hará con el kit integrado.
- **Siguiente:** sesión 2, muros laterales, arcadas y vanos de vidrieras/rosetones.

## 2026-11-09 - 0.3.2: muros laterales, arcadas y vanos de la catedral (`docs/layout-catedral`)
- **Propuesta técnica:** bandas laterales de 48 px cerradas, pilastras moduladas, lancetas alternas alineadas con los rayos ya existentes y rosetón frontal en el arco del crucero.
- **Compatibilidad:** el origen de cada lanceta se expresa en las coordenadas actuales de `source/godrays.c`; la sesión 3 debe dejar de colocar la variante de rosetón en una pared lateral y anclarla al arco frontal.
- **Pendiente del usuario:** escoger referencias de tracería y color del vidrio, generar modelos de lanceta/rosetón/contrafuerte y aprobar los prerenders.
- **Detalle y briefs:** [`walkthroughs/muros-catedral/walkthrough.md`](walkthroughs/muros-catedral/walkthrough.md).

## 2026-11-10 - 0.3.2: cierre de revisión de la primera ROM de catedral (`feat/muros-catedral`)
- **Conseguido:** primera pasada del escenario compilada y jugada; rendimiento y estética general aceptables para el usuario. Godrays integrados en las variantes de catedral. Retiradas las ayudas de lectura a través del muro; ROM `cathedral-playground-perf` subida como `dungeonds.nds`.
- **Abierto:** el usuario no aprueba la distribución de bancos y estatuas. Las colisiones y oclusiones de los props siguen fallando. El escenario de ocho direcciones creado durante el diagnóstico no demostró contacto con la estatua, se retiró y no cuenta como evidencia.
- **Siguiente:** rehacer composición y fuente común de geometría/dibujo/huella/profundidad; validar cada coordenada y contacto antes de interpretar capturas. Certificar rendimiento después de resolverlo. Detalle: [`walkthroughs/catedral-cierre/`](walkthroughs/catedral-cierre/walkthrough.md).

## 2026-11-10 - 0.3.2: oclusión de props y huella de los bancos (`feat/muros-catedral`)
- **Causa:** el prerender de props reducía la imagen del lab pero no los valores de profundidad, que seguían en píxeles del render fuente (7–23× más grandes). Los props no tapaban al actor que tenían detrás y a veces tapaban al de delante.
- **Arreglo:**
  - profundidad en píxeles del sprite, con el baker rechazando datos fuera de rango;
  - huella de los bancos a partir de su planta, con envolvente convexa (decisión en `DESIGN.md` §6.9.1b);
  - escenario nuevo `cathedral_bench_collision`;
  - la peor ventana de oclusión baja de 14.838 a 4.117 runs.
- **Verificación:** build sin warnings, 9 tests de host y 3 escenarios de catedral PASS. ROM `cathedral-playground-perf` subida y dada por buena por el usuario en la DS. Log `PERF_PROFILE` de unos 11 minutos: CPU con media de 116.277 ticks y máximo de 396.970, de un presupuesto de 560.190. Los únicos frames de más de un vblank los causa la escritura del propio log en la SD.
- **Detalle:** [`walkthroughs/props-depth-units/`](walkthroughs/props-depth-units/walkthrough.md). Siguientes pasos y briefs: [`walkthroughs/catedral-siguientes-pasos/`](walkthroughs/catedral-siguientes-pasos/walkthrough.md).

## 2026-11-11 - Concepto de personaje, enemigos, élites y jefe de la demo (`main`, solo documentación)
- **Decidido:** el rayo del personaje es un milagro que le quema el cuerpo; se continúa con El Corazón Abierto (El Lector y La Custodia en reserva). Enemigos base con aspecto nuevo y misma FSM, élites Portaestandarte y Exorcista hueco, jefe paso procesional (`DESIGN.md` §6.10).
- **Detalle y prompts de Gemini:** [`walkthroughs/concepto-demo-personajes/`](walkthroughs/concepto-demo-personajes/walkthrough.md).

## 2026-11-12 - Animaciones del Cireneo con la cruz (`feat/anim-cireneo`)
- **Hecho:** script de Blender `tools/characters/build_cireneo.py` que pega la cruz al hueso `Spine2`, fija los brazos sobre el travesaño y genera andar, carga, telegrafía y atascado a partir del modelo de Tripo. Los FBX resultantes no se versionan (se regeneran en ~5 s).
- **Verificación:** hojas de contacto en Blender y export del lab en las 8 direcciones a 40 px, con luz `neutral`; la cruz se lee bien. Sin integrar en el juego ni medir en DS.
- **Detalle:** [`walkthroughs/anim-cireneo/`](walkthroughs/anim-cireneo/walkthrough.md).

### Catedral 0.3.2: compositor de la nave (2026-11-11)

- **Qué:** el reparto aleatorio de piezas se sustituye por un compositor determinista (tramo de 256 px, ciclo de 4 tramos, columnata junto a los muros, bancadas en grupos de 4–6 bancos pegados y centrados, barricada de sacos y crucero). Piezas nuevas: `banco_entero`, `sacos` y `columna_entera`. Se retira el rosetón pintado en el suelo y se arregla la sombra cortada de la columna entera. Reglas en `DESIGN.md` §6.9.1b.
- **Verificación:** kit 851/1.024 tiles, ventana 351, oclusión 15.624 (antes 4.117); build sin warnings; paridad C == Python; 5 escenarios de catedral PASS; el único test de host que falla (`test_strip_kit`) ya fallaba en `main`. **No medido en la DS:** la oclusión sube 3,8 veces y hay que certificar los 60 FPS antes de merge (`AGENTS.md`, regla 6).
- **Detalle y pendientes:** [`walkthroughs/distribucion-catedral/`](walkthroughs/distribucion-catedral/walkthrough.md) y [`BRIEFING-SIGUIENTE.md`](walkthroughs/distribucion-catedral/BRIEFING-SIGUIENTE.md).

### Catedral 0.3.2 v2: planta de salón y rebase sin tirones (2026-11-12)

- **Qué:**
  - Planta de salón con el muro 3D `gothic_arch` del usuario y luz que entra desde la cara del muro.
  - Lápidas v5: la piedra sustituye bloques de 3×2 o 2×1 losas, a ras del suelo, con los surcos oscurecidos y dos estampas por color del damero.
  - Compositor v2 por pantalla, en bloques de 2 pantallas: columnas con velas, bancadas en grupos de 4 o relicario, y lápidas sueltas o en escalera.
  - Editor de planta `tools/catedral_editor/`.
  - Rebase de 768 px preparado por trozos, sin `qsort` y sin vaciar la caché de tiles.
  - Limpieza de 372 assets viejos.
  - Reglas en `DESIGN.md` §6.9.1b.
- **Verificación:**
  - 13 tests de host, incluida la equivalencia bit a bit del rebase.
  - 4 variantes compiladas sin warnings.
  - 8 escenarios PASS.
  - Kit de 857 de 1.024 tiles y peor ventana de 379.
  - **DS:** peor frame 406.000 de 560.190 ticks (72 %) y media del 26 %. Ningún frame perdido por el juego: los perdidos coinciden con la escritura del log en la SD. El usuario confirma que no parpadea.
- **Detalle:** [`walkthroughs/catedral-v2-salon/`](walkthroughs/catedral-v2-salon/walkthrough.md).

## 2026-11-12 - El Corazón Abierto como héroe (`feat/corazon-abierto`)
- **Entrega:** héroe nuevo con andar de Mixamo adaptado (cadera en el sitio), clip de disparo que al revés hace de carga, `muzzle` en el pecho desde el hueso `Spine2`, haz «fuego» del francotirador y cuatro auras de carga para comparar (`Y`). Rama al día con `main` (catedral v2 y Cireneo).
- **Verificación:** 4 variantes sin warnings; 222 tests de Python y 10 de host; 14 escenarios PASS (héroe y catedral). ROM (commit `13a4b18`) jugada en la DS por el usuario: va bien; no hay log de `PERF_PROFILE`.
- **Pendiente:** elección de aura, chispa de impacto propia del rayo y, si se ven caídas, log de `PERF_PROFILE`.
- **Detalle:** [`walkthroughs/corazon-abierto/`](walkthroughs/corazon-abierto/walkthrough.md).

## 2026-11-12 - Cireneo v2 con acentos negro y rojo (`feat/cireneo-v2`)
- **Decidido:** todos los personajes llevan acentos negros y rojos (`DESIGN.md` §6.10).
- **Hecho:** el nuevo Cireneo y su cruz carbonizada reutilizan las animaciones de la v1, transfiriendo rotaciones en espacio de mundo (`tools/characters/build_cireneo_v2.py`). Hojas de contacto y lab a 40 px revisadas. Sin integrar en el juego.
- **Detalle:** [`walkthroughs/cireneo-v2/`](walkthroughs/cireneo-v2/walkthrough.md).

## 2026-11-13 - Cireneo v2 integrado en ROM (`feat/cireneo-rom`)
- **Entrega:** Cireneo v2 integrado como `CHAR_CHARGER` a `60×60` px (sombra recortada a `80×80`, `CharacterConfig` con dimensiones por personaje y hit volume de francotirador escalado 1,5×), poste inferior de la cruz alargado (`CRUZ_LOWER_K = 0.70`), ritmo de pasos ajustado en `CHASE` (`anim_period = 8`) y clip dedicado de carga agachado (~77,4°, 4 frames a 4 ticks/frame en `CHARGE`). Limpieza de `assets/inbox/`.
- **Detalle:** [`walkthroughs/cireneo-rom/`](walkthroughs/cireneo-rom/walkthrough.md).

## 2026-11-13 - SFX base del Corazón Abierto (`feat/sfx-core`)
- **Entrega:** 5 SFX generados vía `@elevenlabs/cli`, horneados con `tools/bake_sfx.py` (`assets/sfx/raw/` → `assets/sfx/baked/` → `source/sfx_bank.c`, 23,1 KB en 8-bit) e integrados en `source/sfx.c` (`libnds` hardware, panning por X, cooldowns 2–3 frames y jitter ±12% en hit). Reglas de CLI añadidas a `AGENTS.md` y diseño a `DESIGN.md`.
- **Verificación:** `build-project.ps1` (`0 warnings`), tests de host (`9` + `58` OK) y prueba en DS real aprobada por el usuario.
- **Detalle:** [`walkthroughs/sfx-core/`](walkthroughs/sfx-core/walkthrough.md).

## 2026-11-13 - Telegrafía sobria del Cireneo (`feat/cireneo-telegraph`, fusionada en `main`)
- **Entrega:** retirado el parpadeo arcade de `ENEMY_STATE_TELEGRAPH`; integrado keyframe `cireneo_telegraph` (`60×60`, 56,25 KiB) en secuencia progresiva de 3 fases (`walk[0] → telegraph → charge[0]`), pulso único de brasa tras la cruz (`draw_telegraph_pulse`) y temblor de tensión de 1 px en los últimos 10 frames.
- **Verificación:** `build-project.ps1` (`default` y `sandbox`, `0 warnings`), `test_charger_contract.py` (`16` tests OK) y 3 escenarios `enemy_charger_*` PASS. Pendiente de probar en DS física.
- **Detalle:** [`walkthroughs/cireneo-telegraph/`](walkthroughs/cireneo-telegraph/walkthrough.md).

## 2026-11-13 - Marea elástica (`feat/tide-spring`, fusionada en `main`, SIN PROBAR)
- **Entrega:** velocidad de la marea adaptativa según la distancia al jugador (`DESIGN.md` §6.4, `include/tide.h`, `source/tide.c`, `source/main.c`) y reducción del 25 % de velocidad del jugador dentro de la marea.
- **Detalle:** [`walkthroughs/tide-spring/`](walkthroughs/tide-spring/walkthrough.md).

## 2026-11-13 - BSO de combate por NitroFS + Maxmod (`feat/bgm-loop`)
- **Entrega:** `cathedral_battle_loop.wav` (21,6 s) en streaming vía `nitro:/bgm.raw` + `mmStreamOpen` (2 KB RAM) y 5 SFX en `soundbank.bin` vía NitroFS (`AUDIODIRS := audio`, `NITROFSDIR := nitrofiles`), liberando los 23,1 KB estáticos anteriores. Guardado `assets/music/boss_climax_loop.wav` (28,8 s) para futuros jefes.
- **Verificación:** `build-project.ps1` (`0 warnings`), tests de host (`9` + `58` OK) y prueba en DS real aprobada por el usuario.
- **Detalle:** [`walkthroughs/bgm-loop/`](walkthroughs/bgm-loop/walkthrough.md).
- **Verificación:** test de contrato `tests/test_tide_contract.py` OK. **Sin probar en DeSmuME ni en Nintendo DS física; sin walkthrough propio todavía.**
