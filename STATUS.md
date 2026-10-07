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

## Sesión 06: Corrección de Colisión y Orden de Profundidad (Depth Sorting) en Pilares
- [x] Diagnóstico de desfase vertical de 8 píxeles de pantalla entre el collider y la base proyectada de los pilares.
- [x] Corrección del origen de colisión de pilares en `position_is_free()` pasando de `(c + 0.5, r + 0.5)` a `(c, r)` para coincidir exactamente con el anclaje del sprite.
- [x] Corrección de la clave de profundidad de objetos en `render_screen()` a `(col + row) << 8`.
- [x] Corrección del spawn inicial del jugador en `player_init()` para centrado perfecto en la celda inicial.
- [x] Generación de suite de test de colisión de pilares (`scenarios/pillar_collision_test.json`) y evidencia visual side-by-side x4.
- [x] Validación de no regresión en todos los escenarios automáticos con DeSmuME headless y compilación limpia con Docker BlocksDS.
- **Evidencia:** `walkthroughs/06-pillar-collision-and-depth-alignment/walkthrough.md`.

---

## Sesión 07: Integración del Enemigo Skeleton y Reorganización Canónica de Assets
- [x] Limpieza del repositorio raíz: reubicación de capturas sueltas de tests y comparativas en `assets/tests_and_previews/` y scripts utilitarios en `tools/` y `tools/lab/`.
- [x] Clasificación canónica de modelos 3D bajo `assets/characters/<nombre>/` (`monster`, `charger`, `skeleton`).
- [x] Integración de `skeleton.fbx` en el pipeline de horneado (`tools/bake_player.py`): soporte de material de hueso gótico (`BoneGothic`), normalización de escala a estándar NDS ($1.39\text{ m}$) y fijación de root motion en caderas.
- [x] Ajuste de contraste para sombras óseas esbeltas en `tools/shadow_masks.py` (percentil 0.1%), superando el contrato formal de tests unitarios (`tests/test_shadow_masks.py`).
- [x] Corrección del bug de outline gap: dilatación y solidificación del sprite contra el contorno para eliminar vacíos transparentes en cuernos y huesos finos.
- [x] Engrosamiento de malla ósea del esqueleto (Displacement 0.12) y sombreado chiaroscuro dramático en Cycles con oclusión ambiental de cavidades y rampa de profundidad.
- [x] Consolidación definitiva del Charger Opción A+ Pulida (1.35x, cuello elevado +20°, colores vivos 2K y outline anti-erosión contiguo).
- [x] Expansión del conversor a C (`tools/convert_iso_to_c.py`) para soportar 3 personajes simultáneos (`CHAR_HERO`, `CHAR_CHARGER`, `CHAR_SKELETON`) con arrays BGR555 y máscaras de 4 bits empaquetadas.
- [x] Verificación de compilación en Docker BlocksDS y ejecución headless en DeSmuME (`scenarios/character_switch_test.json`), demostrando conmutación cíclica entre los tres personajes con físicas y sprites impecables.
- **Evidencia:** `walkthroughs/07-skeleton-enemy-and-asset-cleanup/walkthrough.md`.

## Sesión 08: Estandarización del Pipeline de Shaders, Normales y Contraste de Personajes
- [x] Diagnóstico y auditoría de tratamientos ad-hoc en modelos 3D (`monster`, `charger`, `skeleton`).
- [x] Formalización del manifiesto declarativo de perfiles de horneado en `tools/character_profiles.json` (desacoplado de bifurcaciones de código).
- [x] Documentación formal de arquitectura en `TECHNICAL.md` (Sección 3.1: regla de atenuación de normal maps al 30-40% en NDS, engrosamiento Displace de 0.12 para huesos, Ambient Occlusion de cavidades con ColorRamp y grading 2D en PIL).
- [x] Generación de collages animados en 8 direcciones sincronizados (GIFs con 8 facings simultáneos) para cada configuración y modelo bajo `walkthroughs/08-standardize-character-shaders/assets/` mediante `tools/generate_all_8dir_collages.py`:
  - **Héroe (Monster):** Conf 1 (In-place crudo), Conf 2 (Outline clásico), Conf 3 (Anti-erosión e30 actual).
  - **Cargador (Maw):** Conf 1 (Base 1.0x), Conf 2 (1.35x + cuello +20°), Conf 3 (Contraste limpio), Conf 4 (Horns glow), Conf 5 (Opción A+ pulida).
  - **Esqueleto (Skeleton):** Conf 1 (Blanco plano original), Conf 2 (Engrosado marfil), Conf 3 (Chiaroscuro dramático actual).
- [x] Registro y catálogo visual auditable en `walkthroughs/08-standardize-character-shaders/walkthrough.md`.
- **Evidencia:** `walkthroughs/08-standardize-character-shaders/walkthrough.md`.

---

## Sesión 09: Rendimiento 60 FPS Dual-Screen, Corrección Diagonal y Multi-Entidad (10 Enemigos)
- [x] Diagnóstico matemático y de temporización del judder/tirones en diagonal del Charger:
  - Eliminación del truncamiento de punto fijo 5-bit prematuro (`dcol`/`drow`), conservando resolución completa de subpíxel de 8 bits.
  - Supresión del enganche de fase cíclico de pérdida de VBlank con el período de animación del Charger (`anim_period = 2`).
- [x] Overhaul del renderizador Dual-Screen a 60 FPS bloqueado:
  - Eliminación de `s_top_backbuffer` en EWRAM (ahorro de 96 KB).
  - Renderizado directo en `VRAM_C` sin copias ni DMA bloqueante (`dmaCopyWords`).
  - Refresco a 60 Hz completo en ambas pantallas simultáneamente.
  - Implementación de copias ráfaga hardware ARM de 32 bits (`ldmia`/`stmia` con registros r3-r10) reduciendo el tiempo de floor copy a 6.5 ms (antes 11.5 ms).
  - VCount máximo de finalización de renderizado en línea 173 / 262 (19 scanlines antes del inicio del VBlank).
- [x] Sistema Multi-Entidad en tiempo real (10 enemigos activos):
  - Integración de 10 enemigos autónomos (5 Chargers y 5 Esqueletos) deambulando y colisionando de forma independiente en la cripta.
  - Optimización de bounding boxes dinámicas por frame (`s_char_frame_bounds`), reduciendo el área rasterizada en más de un 40%.
  - Sombreado dinámico acelerado (`apply_shadow_fast`) con máscara de bits a 1 ciclo de reloj (0.9 ms de sombras con 11 entidades simultáneas).
  - Despacho optimizado en ensamblador ARM para blitting y sorting en `render_screen()`.
- [x] Verificación de escenarios y captura de evidencia visual:
  - Suite de benchmarks deterministas de 240 frames en DeSmuME headless (`tools/measure_perf.py`).
  - Generación de capturas y walkthrough en `walkthroughs/09-dual-screen-60fps-and-multi-entity/walkthrough.md`.
- **Evidencia:** `walkthroughs/09-dual-screen-60fps-and-multi-entity/walkthrough.md`.

---

## Sesión 10: Hardware Background Scrolling a 60 FPS en Dual-Screen
- [x] Eliminación completa de la copia por software de ventana de suelo (`Floor Window Copy`) en ambas pantallas:
  - Descenso de tiempo de suelo de **7,232.1 µs** a **554.1 µs** (**-92.3%**).
  - Supresión del array `s_floor_cache` en EWRAM, liberando **1.34 MB de RAM principal**.
- [x] Integración de fondo tileado hardware (`BgType_Text8bpp`) en Modo 5 2D:
  - Uso de capa `BG1` tanto en motor principal (pantalla inferior) como secundario (pantalla superior).
  - Streaming eficiente del tilemap 32x25 en memoria de fondo hardware y ajuste directo de subpíxel en registros `REG_BG1HOFS`/`REG_BG1VOFS`.
- [x] Empaquetado y particionamiento milimétrico de VRAM:
  - Motor secundario: compresión perceptual sin pérdida perceptible a **480 tiles únicos** (30 KB), encajando en los 128 KB de `VRAM_C` junto al tilemap (2 KB) y el framebuffer Bmp16 de entidades (96 KB).
  - Motor principal: `VRAM_A`/`VRAM_B` en double-buffering para `BG2` Bmp16 y `VRAM_D` (slot 6) para `BG1` Text8bpp.
- [x] Resultados de rendimiento comprobados:
  - **239 / 240 frames a 60 FPS exactos (99.6% locked 60 FPS)** en benchmark determinista.
  - Finalización de renderizado en scanline raster promedio 117 / 262 (41 líneas antes del VBlank).
- **Evidencia:** `walkthroughs/10-hardware-bg-scroll-60fps/walkthrough.md`.

---

## Próximas Líneas de Trabajo
- Invocación de esbirros esqueletos y mecánicas de nigromancia activa.
- Expansión de mazmorra procedural manteniendo el contrato dimétrico y presupuestos de 60 FPS.

