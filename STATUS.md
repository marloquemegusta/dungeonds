# STATUS.md - Estado Actual e Historial Reciente de DungeonDS

Primero el estado necesario para retomar el trabajo sin depender del chat; después, las entregas recientes verificadas (más nueva al final). El historial hasta 2026-10-21 está en `STATUS-ARCHIVE.md`.

## Estado actual (2026-11-04)

- **Rama base:** `main`, con v0.1 (`walkthroughs/v0.1/`) y v0.2 (`walkthroughs/v0.2/`) integradas. La v0.2 se integró con la deuda de rendimiento anotada abajo.
- **Juego (v0.2, integrada en `main`):** una mazmorra de 768×768 con 6 manadas dormidas (22 enemigos), 8 modificadores estilo Isaac con coste, curación de 1 golpe por manada, HUD de run, reinicio total al morir (`DESIGN.md` §5). Pendiente: probar en la DS (sensación, rendimiento con hasta 24 enemigos y dos pantallas).
- **Juego (v0.1, base de la v0.2; sustituida por la mazmorra):** prueba de diversión en 4 arenas cerradas de 384×384 px encadenadas (`DESIGN.md` §4): escopeta + francotirador, cargador (con navegación BFS) + tirador (telegraph y ráfagas de 3). Pendiente la Fase E: tuning y 60 FPS certificados en la DS.
- **Arenas:** datos en `assets/arenas/arenas.json`; generador de modelos, export con el lab y baker (`tools/make_arena_glb.py`, `tools/export_arenas.py`, `tools/bake_arena.py`) descritos en `TECHNICAL.md` §3. El mapa grande `isometric_shooter_bl` ya no se usa.
- **Render:** actores dibujados directamente en la página trasera del framebuffer de VRAM, limpieza por spans sucios y oclusión exacta al píxel por consulta de tramos (`TECHNICAL.md` §3.3). Medido en DS: CPU 1,58 ms de media y 12 de 2520 frames con más de un vblank.
- **Personajes:** héroe (space marine), charger y necron, exportados por el lab a `assets/sprites/characters/<nombre>/`.
- **Sin existir en código:** iluminación dinámica, niebla de guerra.
- **Herramientas de diagnóstico en DS:** `PERF_PROFILE` (`include/perfprof.h`, log `/dungeonds_perf.log`) y `crashlog` (`CRASHLOG_ENABLED`, logs `/dungeonds_crash.log` y `/dungeonds_live.log`). Ambas apagadas por defecto; se leen con `fetch-device-log.ps1` de la skill.

### Siguientes pasos
1. **Sesión de diseño de transparencias** (lectura tras paredes): preguntas en `TECHNICAL.md` §4.6; la decisión va a `DESIGN.md` §3 antes de tocar código.
2. **Deuda del motor** (`TECHNICAL.md` §4.5): timestep, assets (paleta/compresión/NitroFS), pipeline de assets, acoplamiento.
3. **Render 2.5D** (`TECHNICAL.md` §4.1): escala personaje/mapa.
4. **Data abort** intermitente en hardware sin causa conocida (`TECHNICAL.md` §4.4).
5. **v0.2, cierre de la prueba (orden propuesto):**
   1. **Rendimiento (deuda abierta, regla 6):** bajar el coste de enemigos (`en`) y sprites (`blit`) con varias manadas despiertas (tramos de 300–411 k ticks) y explicar los picos aislados; volver a medir con `PERF_PROFILE` y certificar 60 FPS en la DS.
   2. **Sesión de tuning:** daño de las armas, daño de los enemigos al jugador y stats generales (`DESIGN.md` §5, Feedback).
   3. **Modificadores y UI:** que se entienda qué hace cada uno (icono, descripción de efecto y coste) y rediseñar pedestales y HUD, hoy provisionales.
   4. **Mazmorra v0.3:** más grande, salas más diferenciadas, posiblemente con puertas; decisión de diseño primero.
   5. Después: tercer tipo de enemigo, jefes, sonido, transparencias (`DESIGN.md` §3 y §5).

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
