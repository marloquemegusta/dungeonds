# STATUS.md - Historial de Entregas y Estado del Proyecto DungeonDS

Este documento registra el historial cronológico de sesiones de desarrollo verificadas mediante compilación BlocksDS, escenarios deterministas en DeSmuME y validación en Nintendo DS física.

---

## Sesión 01: Prototipo Jugable y Pipeline de Renderizado
- [x] Repositorio inicializado, toolchain offline con Docker BlocksDS y DeSmuME headless.
- [x] Proyección dimétrica: tiles de suelo en rombo 32×`FLOOR_TILE_H` con ordenación por profundidad `(col+row)`.
- [x] Pipeline de Blender para pre-renderizado de ruinas y personaje en 8 direcciones.
- [x] Contrato de anclaje de suelo único: origen en el centro de la celda.
- [x] Caché de suelo del mundo en EWRAM (`s_floor_cache`) con máscaras de sombra proyectada (Cycles Shadow Catcher).
- **Evidencia:** `walkthroughs/02-isometric-renderer/walkthrough.md`.

---

## Sesión 02: Atmósfera Gótica Chiaroscuro y Outline de Legibilidad
- [x] Iluminación gótica en `tools/ds_look.py`: antorcha ámbar viva, relleno frío tenue (`0.50`), ambiente (`0.18`), fondo negro abisal y sombras al 63%.
- [x] Outline de legibilidad de 1 px exterior para silueta del personaje sobre fondos oscuros.
- [x] Sincronización física de paso con zancada 3D (`PLAYER_SPEED = 181`, `ANIM_PERIOD = 3`, sin foot-sliding).
- [x] Colisión sub-tile física circular en pilares de la cripta (radio de 0.65 m).
- [x] Linternas de alma frontales con llama azul espectral potenciada.
- [x] Banner NDS oficial: `DungeonDS: Necromancer Crypt`.
- **Evidencia:** `walkthroughs/03-dungeon-atmosphere-and-outline/walkthrough.md`.

---

## Sesión 03: Enemigo Cargador (Run.fbx) y Swap Dinámico de Personaje
- [x] Generación de spritesheets del enemigo cargador: `charger_e30.png` y `charger_e30_shadow.png` (8 dirs x 8 frames).
- [x] Sincronización cinemática de carga: zancada de 2.00 m, `CHARGER_SPEED = 362` (1.41 px/frame, ~2x velocidad del héroe) y `ANIM_PERIOD = 2`.
- [x] Optimización de memoria EWRAM: recorte de lienzo a 48×40 centrado en pie, ahorrando >540 KB de RAM para encajar holgadamente en el límite de 4 MB de la consola.
- [x] Cambio de personaje interactivo en tiempo real con botones (`X`, `Y`, `A` o `SELECT`).
- **Evidencia:** `walkthroughs/04-enemy-charger-and-character-swap/walkthrough.md`.

---

## Sesión 04: Arquitectura de Rendimiento 60 FPS y Corrección de Alineamiento ARM9
- [x] Benchmarking de frames determinista con timers hardware ARM9 (`cpuStartTiming`/`cpuGetTiming`) y script `tools/measure_perf.py`.
- [x] Reducción de tiempo de render por frame de **86.59 ms (~10-11 FPS)** a **10.62 ms (80% bloqueado a 60 FPS)**.
- [x] Pre-baking de sombras estáticas en la caché de suelo durante startup (`draw_shadow_mask_to_cache`), eliminando el 99% del coste de sombras en tiempo de ejecución.
- [x] Eliminación de divisiones enteras software en shaders de sombras con desplazamientos de bits.
- [x] Double-buffering directo en VRAM con zero-copy (`MODE_FB0`/`MODE_FB1` escribiendo en `VRAM_A`/`VRAM_B`).
- [x] Interleaving de la pantalla superior durante scroll continuo (30 Hz top / 60 Hz bot).
- [x] **Corrección de alineamiento ARM946E-S en blitting**: reemplazo de accesos desalineados de 32 bits (`*(uint32_t*)`) por lecturas y escrituras halfword limpias de 16 bits (`uint16_t`), eliminando la rotación de 16 bits del hardware y la deslocalización visual en muros y columnas.
- [x] Validación visual determinista contra la verdad canónica: **0 píxeles de diferencia** frente a `00_spawn_center.png`.
- [x] Despliegue verificado en Nintendo DS física por FTP.
- **Evidencia:** `walkthroughs/05-arm9-alignment-and-60fps/walkthrough.md`.

---

## Próximas Líneas de Trabajo
- Invocación de esbirros esqueletos y mecánicas de nigromancia activa.
- Expansión de mazmorra procedural manteniendo el contrato dimétrico y presupuestos de 60 FPS.
