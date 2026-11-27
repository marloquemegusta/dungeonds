# STATUS-ARCHIVE.md - Historial de Sesiones hasta 2026-11-20

Registro histórico congelado. No se actualiza: las entregas nuevas van en `STATUS.md`. Muchas de estas sesiones describen sistemas ya eliminados (pipeline Blender, antorcha, niebla de guerra, mapas WH40K/FBX anteriores); el estado vigente está en `STATUS.md` y `TECHNICAL.md`. Los números de sesión se repiten en algunos tramos porque se escribieron desde ramas distintas.

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

## Sesión 11: Streaming del Fondo, Stutter y Alineación de Pilares/Arcos
- [x] Sustitución del repintado de 32x25 tiles por un ring map hardware BG1 de 64x32; actualiza sólo filas/columnas expuestas dentro de VBlank.
- [x] Corrección del layout físico de BG 512x256: dos screenblocks de 32x32, scroll circular sincronizado con el origen de cámara y el fine scroll.
- [x] Particionamiento VRAM_C: tileset de 448 tiles (28 KB), mapa de 4 KB en offset 0x7000 y framebuffer de 96 KB desde 0x8000.
- [x] Corrección de telemetría: incluye el streaming del fondo en los ticks de CPU y usa el presupuesto de 560,190 ciclos por frame.
- [x] Benchmark DeSmuME de 240 frames: **240/240 a 60 FPS**, carga CPU media **48.95%**, máxima **53%**, streaming de suelo **26.8 µs/frame**.
- [x] Escenarios dual-screen (6 capturas), colisión con pilares (5 capturas) y unión muro/arco (4 capturas): todos PASS; capturas revisadas sin gaps, tiles negros ni seams.
- **Evidencia:** `walkthroughs/11-perf-bg-scroll-and-rendering/walkthrough.md` y sus assets de validación. Sin validación en consola física.

## Sesión 12: Prototipo de Combate con Lanza Ósea
- [x] Horneado del proyectil en ocho direcciones con el look e30 compartido y exportación a BGR555.
- [x] A mantenido autoapunta al enemigo activo más cercano; lápiz mantenido dispara en la dirección de la pantalla inferior y prevalece sobre A.
- [x] Implementados daño provisional (30), vida (Esqueleto 40 / Charger 90), cadencia de 16 frames, proyectil rápido perforante y destello breve al impacto.
- [x] Contrato host de sprites/números y escenarios DeSmuME para A, lápiz y fuego sostenido: todos PASS; el escenario de 120 frames elimina varios enemigos.
- [x] Compilación BlocksDS limpia. Sin validación en consola física.
- **Evidencia:** [walkthroughs/12-bone-lance-prototype/walkthrough.md](walkthroughs/12-bone-lance-prototype/walkthrough.md).

## Sesión 13: Salva de Perdigones de Hueso
- [x] Reducción del asta del proyectil a aproximadamente 0,90 m y sprite opaco máximo de 12×12 px en las ocho direcciones.
- [x] A y lápiz disparan cinco astillas rápidas en abanico; 10 de daño por astilla y 16 frames entre salvas.
- [x] Balance de prueba: esqueleto 40 PV y cargador 90 PV; hasta 50 de daño si impactan los cinco perdigones.
- [x] Tres contratos host, compilación BlocksDS y escenarios DeSmuME para botón, táctil y fuego sostenido: PASS. Sin validación en consola física.
- **Evidencia:** [walkthroughs/13-bone-shotgun-pellets/walkthrough.md](walkthroughs/13-bone-shotgun-pellets/walkthrough.md).

## Sesión 14: Lanza Ósea Procedural
- [x] Sustitución del spritesheet por astillas estrechas de 8–11 px dibujadas en runtime, con variación por semilla y sin outline.
- [x] Añadido pool de 32 motas espectrales con movimiento fijo, tonos/tamaños variables y vida de 4–7 frames.
- [x] Build BlocksDS, contratos host y escenarios DeSmuME para A, lápiz y fuego sostenido: PASS.
- [x] GIF de 28 capturas de DeSmuME registrado en walkthrough; ampliado nearest-neighbor para revisión visual. Sin validación en consola física.
- **Evidencia:** [walkthroughs/14-bone-particle-lance/walkthrough.md](walkthroughs/14-bone-particle-lance/walkthrough.md).

## Sesión 15: Lanza Rápida y Fragmentación de Enemigos
- [x] Duplicada la velocidad de los proyectiles de 4 a 8 px/frame, manteniendo el abanico y el daño.
- [x] Eliminado el cian de la lanza y las motas; paleta de hueso y marfil.
- [x] Al morir, el enemigo se rompe en seis parches 4×4 de su sprite; preservan los colores originales, salen con impulso del disparo, describen un arco corto y se ordenan por profundidad.
- [x] Build BlocksDS y 3 contratos host: PASS. Escenarios DeSmuME para movimiento, botón, táctil, combate y muerte: PASS; GIFs de movimiento y fragmentación guardados. Sin validación en consola física.
- **Inspiración TowerDS:** extracción de parches de píxeles originales y física breve de fragmentos; adaptado al framebuffer BGR555 y al presupuesto de DungeonDS.
- **Evidencia:** [walkthroughs/15-bone-projectile-revision/walkthrough.md](walkthroughs/15-bone-projectile-revision/walkthrough.md).

## Sesión 16: DS Shader Lab Interactivo y Pipeline FBX Abierto
- [x] Desarrollo de DS Shader Lab (`tools/lab/shader_lab_server.py` y `tools/lab/shader_lab_ui.html` en puerto `8088`).
- [x] Corrección de centrado vertical de cámara isométrica en Blender Cycles (`target_z = height * 0.50`), eliminando el corte superior a escalas de 1.4x–2.2x.
- [x] Soporte para selección abierta de cualquier FBX del repositorio y subida vía web con previsualización inmediata.
- [x] Acoplamiento cinemático automático de zancada 3D a velocidad fija de Nintendo DS (formato 8.8) para evitar foot-sliding.
- [x] La resolución de salida se selecciona en píxeles; la cámara ortográfica se ajusta desde los vértices animados y Blender renderiza directamente a ese tamaño. Tres FBX quedaron dentro de ±1 px del objetivo de 32 px.
- [x] Comparados los sprites compilados de ROM con el laboratorio: tamaño visible máximo actual del héroe 18×23 px, cargador 32×36 px y esqueleto 19×22 px; el selector ahora admite 22–60 px en pasos de 1 para reproducirlos.
- [x] Corregido el enlazado de mapas PBR FBX por nombre (base color, metallic, roughness y normal) y el entorno de reflexión neutro; el mago encapuchado ya no se interpreta como metal negro.
- [x] El periodo en ticks controla también la duración real de cada frame de la previsualización; la inclinación se reaplica tras evaluar cada pose y detecta el eje lateral de Neck/Head (X o Z local) para evitar torsiones horizontales entre rigs.
- [x] Cada render del laboratorio guarda salidas con ID único; el historial conserva los parámetros usados y los restaura al volver a una miniatura, evitando que renders distintos se sobrescriban por una clave incompleta.
- [x] Pasada final Impeccable: vacío inicial y mensajes de error útiles, controles avanzados etiquetados y accesibles, historial con teclado, collage ampliado y legible a 22 px; verificación en escritorio/móvil, cero overflow horizontal y cero errores de consola.
- [x] Render real a 22×22 px (8 muestras) con dos ajustes de luz ambiente; IDs/GIFs distintos y restauración del ajuste al seleccionar la primera miniatura. Evidencia de UI y sprite en el walkthrough.
- [x] Validación completa de renderizado de 8 direcciones en Blender Cycles y exportación de GIF collage.
- **Evidencia:** [walkthroughs/16-shader-lab-interactive/walkthrough.md](walkthroughs/16-shader-lab-interactive/walkthrough.md).

## Sesión 17: Shader Lab importa FBX sin buscar sidecars .fbm
- [x] Desactivada la búsqueda recursiva global de imágenes FBX en el inspector de acciones y el worker de render.
- [x] El Shader Lab no inspecciona carpetas .fbm; utiliza los mapas empacados en el FBX.
- [x] Mario importa en **0,85 s** y renderiza desde una carpeta sin sidecar .fbm (48×48, 16 muestras) en **7,7 s**.
- **Evidencia:** [walkthroughs/17-shader-fbx-image-search/walkthrough.md](walkthroughs/17-shader-fbx-image-search/walkthrough.md).

## Sesión 18: Perfil real de carga y render de Mario frente al héroe
- [x] Confirmado que el servidor de puerto 8088 seguía con la versión anterior y buscaba imágenes recursivamente al listar acciones; reiniciado con el código actual.
- [x] Endpoints UI a 48×48 px y 16 muestras: Mario **2,51 s** para acciones + **4,95 s** para render; héroe **2,54 s** + **4,54 s**.
- [x] Mario tiene 2,77× los polígonos y 76 % más huesos; perfil detallado en [walkthroughs/18-profile-mario-vs-hero/walkthrough.md](walkthroughs/18-profile-mario-vs-hero/walkthrough.md).

## Sesión 19: Pipeline 2.5D Estilo Diablo para Mazmorras 3D Completas (FBX)
- [x] Implementación de la arquitectura de renderizado pre-renderizado estilo *Diablo / Fallout* para el modelo 3D FBX (`tripo_convert_b14b0e1b...fbx`).
- [x] Eliminación definitiva del cuello de botella de los 448 tiles de hardware 2D: la mazmorra se hornea como un mapa continuo de 512×512 en 16 bits RGB555 (512 KB), preservando la fidelidad total de Blender Cycles sin pérdida de compresión.
- [x] Blitting directo de la ventana de cámara visible (256×192) en el framebuffer a 60 FPS con menos de 0.4 ms de CPU por frame.
- [x] Cámara suave que sigue al héroe en tiempo real en coordenadas de píxel de mundo continuo.
- [x] Matriz de colisión automática de 128×128 (4 px / ~14 cm por celda) extraída mediante raycasting BVH vertical de la malla 3D, con deslizamiento por paredes (`wall sliding`).
- [x] Escala natural y espaciosa: pasillos amplios de 70+ px de ancho donde el héroe cabe holgadamente.
- [x] Validación completa en DeSmuME headless a 60 FPS con GIF animado.
- **Evidencia:** [walkthroughs/19-modular-3d-scifi-dungeon/walkthrough.md](walkthroughs/19-modular-3d-scifi-dungeon/walkthrough.md).


## Features Abiertas y Ramas Activas (En Pausa / Backlog)

- **`feat/skeleton-collapse-fbx` — Colapso del Esqueleto a Pila de Huesos:**
  - **Estado:** Pausado / Prototipo resguardado en rama (`d537db3`).
  - **Objetivo:** Reemplazar la fragmentación aleatoria por una animación determinista donde el esqueleto colapsa y deja una pila de huesos estática en el suelo al morir.
  - **Pendiente para reanudar:** Pulido visual del render/spritesheet (el montón de huesos resultante requiere mayor claridad visual en baja resolución) y posterior mecánica de reanimación nigromántica de la pila.
  - **Evidencia guardada:** `walkthroughs/skeleton-death-fbx/walkthrough.md` (preservada en la rama).

## Próximas Líneas de Trabajo
- Invocación de esbirros esqueletos y mecánicas de nigromancia activa.
- Expansión de mazmorra procedural manteniendo el contrato dimétrico y presupuestos de 60 FPS.



## Sesión 20: Navegación de la mazmorra FBX (validación parcial)
- [x] Compilación BlocksDS y contratos host de navegación/telemetría: PASS.
- [x] La aserción DeSmuME confirma entrada RIGHT consumida, desplazamiento del jugador y cambio de cámara.
- [ ] La ejecución final de colisión aún falla al capturar la detención: el tramo de 50 frames seguía avanzando; el escenario se amplió a 120 frames, pendiente de re-ejecución.
- [ ] Oclusión sprites/entorno y coincidencia de iluminación quedan pendientes; cámara, escala y grading necesitan revisión.
- Sin validación en Nintendo DS física. No se afirma soporte general de FBX.
- **Evidencia:** walkthroughs/fbx-navigation-repair/walkthrough.md.

## Sesión 21: Experimento de Oclusión FBX (no aceptado)
- [x] Compositor experimental de spans y contadores de llamadas, runs, píxeles copiados y ticks.
- [x] Host contract sintético: orden delante/detrás de pared y payload de runs comprobados.
- [ ] Falla la aserción de alineación de piso: el spawn conocido (174,238) se clasifica como upper en la máscara generada.
- [ ] Falla el presupuesto: 15–20 FPS, 243–332% de CPU y ~8.000 runs/frame; no cumple 60 FPS dual-screen con diez actores.
- [ ] El escenario aún no pasa movimiento, detención y release en una misma ejecución; iluminación pendiente.
- Sin validación física DS ni afirmación de compatibilidad general FBX.
- **Evidencia:** walkthroughs/fbx-occlusion-experiment/walkthrough.md.

## Sesión 22: Corrección de colisión FBX (validación parcial)
- [x] El generador produce una cuadrícula 128×128: 1.808 celdas transitables, 150 obstáculos y 14.426 vacíos; spawn seleccionado (270,290) con 3×3 de despeje.
- [x] Host tests: navegación 5/5; contrato de oclusión/máscara 3/3. La prueba de máscara verifica carga y límites del payload, no alineación visual de suelo.
- [x] Escenario DeSmuME con estado real: movimiento DOWN 2,83 px; 24 frames bloqueados ante obstáculo; posición/cámara estables durante espera; input liberado.
- [ ] Puerta y conectividad entre habitaciones no verificadas. Sin prueba en hardware DS.
- [ ] Oclusión experimental sigue por debajo del objetivo (15–20 FPS, 243–332% CPU observados); iluminación/color del jugador pendiente. No se afirma 60 FPS ni soporte FBX general.
- **Evidencia:** walkthroughs/fbx-collision-fix/walkthrough.md.


## Sesión 23: Puntos de colisión FBX y recorte de spans
- [x] Se descarta el cruce vertical impar que queda por debajo de los pies; altura 0,05 m y tolerancia 0,015 m.
- [x] Regresión de los nueve sondeos del jugador para (128,249), (238,309) y (250,314): footprint libre en la malla generada.
- [x] Recorrido de spans limitado al viewport con margen medido de 34 px; benchmark DeSmuME mejora de 62,4 ms a 51,9 ms de CPU media por frame (−16,9%).
- [x] ROM v4 subida y verificada en `ftp://192.168.1.151:5000/roms/nds/dungeonds.nds` (SHA-256 `E8BD107A3F649A3AD04D286EE23DB29CFB5FA6F13DB2BC3C4251B55DA390FA05`).
- [ ] Pendiente: reproducir en DeSmuME/hardware las rutas BFS a los puntos; prueba física DS y objetivo 60 FPS aún sin validar/alcanzar.
- **Evidencia:** [walkthroughs/fbx-collision-perf-followup/walkthrough.md](walkthroughs/fbx-collision-perf-followup/walkthrough.md).
## Sesión 24: Diagnóstico A/B de rendimiento FBX frente al renderer modular
- [x] Benchmark comparable de 240 frames: modular 8.36 ms CPU medio y 240/240 a 60 FPS; FBX baja de 51.53 ms a 45.84 ms tras el fast path de spans cortos; objetivo 60 FPS aún no alcanzado (13/240).
- [x] El fast path evita memcpy para spans de 1–4 píxeles (90.7% de los spans generados) y conserva los mismos píxeles/profundidad; objetos/oclusiones bajan de 39.32 ms a 34.05 ms.
- [x] Copia software del fondo sigue en ~10.5 ms/frame; sin cambios de física o gameplay.
- [x] Build BlocksDS, 27 pruebas host y benchmark DeSmuME PASS. Sin validación en DS física.
- **Evidencia:** [walkthroughs/full3d-performance-gap/walkthrough.md](walkthroughs/full3d-performance-gap/walkthrough.md).


### Cierre de la optimizaci?n FBX (2026-10-10)

- [x] Tabla de profundidad precalculada reemplaza el replay CPU de 16,908 spans; conserva el mismo depth test.
- [x] DMA halfword para las filas de fondo.
- [x] Benchmark DeSmuME 240 frames: 239/240 a 60 FPS; CPU medio 8.60 ms, objetos 1.45 ms, suelo 5.84 ms.
- [x] Capturas alineadas por estado: cero diferencias de p?xel en reposo y movimiento. Build, host tests y escenario FBX pasan.
- [ ] Pendiente medir en consola DS f?sica; hubo un frame lento en el benchmark.
- **Evidencia:** [walkthroughs/full3d-performance-gap/walkthrough.md](walkthroughs/full3d-performance-gap/walkthrough.md).


## Sesi?n 25: Contador de FPS en HUD superior

- [x] A?adido indicador persistente `FPS:NN` en la esquina superior izquierda de la pantalla superior, con el valor existente de `g_perf.fps` y estilo pixelado verde sobre panel oscuro inspirado en TowerDS.
- [x] Build BlocksDS y pruebas host PASS. Escenario DeSmuME: `fps=60` en reposo y tras caminar; captura revisada.
- [x] ROM cargada por FTP y entrada remota verificada.
- **Evidencia:** [walkthroughs/fps-hud/walkthrough.md](walkthroughs/fps-hud/walkthrough.md).


### Seguimiento de rendimiento físico (2026-10-10)

- Usuario informa `FPS:20 C:40 P:10` en Nintendo DSi, en reposo y al moverse. La medición previa de DeSmuME no predice la consola.
- `C` mide lógica+render y `P` incluye espera de VBlank+copia de presentación. La nueva segunda línea muestra `F/S/B/L`: suelo, sombras, blits y lógica.
- TowerDS dibuja el framebuffer inferior directamente en buffer de VRAM con flip; esta rama compone dos buffers en RAM y copia 192 KB por frame. Es una diferencia arquitectónica observada, aún no prueba de la causa.
- Rejilla conservadora 8×8 evita el depth test por píxel cuando no puede existir oclusión. Contrato de 20.000 regiones aleatorias PASS; capturas DeSmuME pre/post con 0 píxeles distintos; blit emulado −7%.
- HUD ampliado: build BlocksDS, contrato de HUD y escenario DeSmuME PASS; captura `FPS:60 C:10 P:06 / F:06 S:00 B:01 L:00`.
- Commit `086d05c`; build diagnóstica `F/S/B/L` CRC `3C31A321` subida y verificada por FTP. Usuario midió `F:38`, `S/B/L:0`; la copia del fondo es el cuello de botella físico.
- El BG1 tileado proviene del mapa modular y su streaming está sin uso; no sustituye el fondo FBX. TowerDS cambia directamente el framebuffer inferior en VRAM, pero ese patrón no elimina el recorte/copiado del bitmap FBX por cámara y pantalla.
- Ensayo: sustituir 384 llamadas DMA por línea/frame con ráfagas ARM9 de 8 palabras (alineado) y pares halfword seguros (desalineado). Build y escenarios pasan; recorrido da las mismas coordenadas inicial/final.
- En el DeSmuME headless (modo intérprete), el candidato cae de 60 a 30 FPS y `F` mide 7 ms quieto / hasta 15 ms andando. Resultado físico aún no medido.
- Commit `749d44f`; ROM CRC `4A0B2288`, SHA-256 `269BFC72206230499B6D3DCC77EE4784160B88C65E12DD66FE29EF55B9868F4E`. FTP `192.168.1.151:5000` agotó el tiempo de conexión a los 10 s; transferencia no confirmada, sin reintentos.


## Sesión 26: Perfilado de rutas de render del suelo FBX

- [x] El atlas BG 8bpp admite hasta 65.535 tiles porque `0xFFFF` es el ID inválido reservado. La residencia VRAM queda limitada al viewport; la metadata `slot_for_tile` crece 4 bytes por tile único entre las dos pantallas.
- [x] Bitmap 8bpp experimental: 240 frames DeSmuME, CPU medio 4.99 ms, `F=1.53 ms`, 240/240 a 60 FPS; el bitmap 512×512 ocupa 256 KiB y deja la pantalla superior sin BG.
- [x] Prototipo FBX tileado con ring map: DeSmuME intérprete 240 frames, CPU medio 4.89 ms, `F=1.49 ms`, 239/240 a 60 FPS; escenario de paseo PASS.
- [x] Refresco de pantalla superior a 30 Hz: CPU medio 5.48 ms y `F=2.91 ms`, peor que ring map; 240/240 a 60 FPS.
- [x] La pantalla superior muestra el suelo tileado siguiendo la misma cámara; mantiene el render de actores/sombras/HUD completo abajo.
- [x] Refinamiento genérico del ring: conserva BG 512×256 y actualiza solo la ventana visible de 33×25 tiles (máximo 825 residentes); elimina la dependencia de densidad de tiles fuera de pantalla.
- [x] Build limpia, contrato host y escenario de paseo PASS para la primera versión del ring; ROM CRC `9CA76D62`, SHA-256 `99A42DF4891390462F4F5B0C45BEB5AED68827DE46F8D1E105471CE6140A7173`.
- [x] Perfil DeSmuME final 240/240 a 60 FPS; CPU medio 4,919 ms, `F=1,508 ms`. Prácticamente igual al ring anterior: no demuestra la mejora en DSi.
- [x] Prueba de estrés del generador con bake 768×768 y 9.217 tiles únicos (atlas 589.888 B + mapa 18.432 B); genera correctamente IDs por encima del número de tiles residentes en VRAM.
- [x] ROM con ring genérico subida y listada por FTP (CRC `9CA76D62`); el byte a byte remoto no pudo verificarse por timeout.
- [x] Corrección de sincronización: escrituras de BG/scroll después de entrar en VBlank; build y escenario PASS. Perfil 240/240 a 60 FPS, CPU medio 4,913 ms.
- [x] ROM corregida CRC `65BC36B1` y SHA-256 `0970E9163B8FF432DAB09F8AD3B4AF6DE78D90F1D8A364103639859D2411F5F4` subida y verificada por readback. Usuario confirma que la DSi va perfecta; no se recibió lectura numérica del HUD.
- **Evidencia:** [walkthroughs/fbx-floor-render-options/walkthrough.md](walkthroughs/fbx-floor-render-options/walkthrough.md).


## Sesión 27: Pruebas de límites del generador FBX

- [x] Prueba de integración con fixture 768×768 y 9.216 tiles únicos; valida mapas mayores que los slots residentes de VRAM.
- [x] Escenario DeSmuME con scroll X/Y y releases PASS (5 capturas, 16 eventos; cámara X 122→76, Y 170→150).
- [x] Corregida la paleta escasa de Pillow; el fixture de 65.536 tiles prueba el rechazo del ID centinela; suite de 20 pruebas host PASS.
- [x] Regeneración del atlas actual idéntica por SHA-256 al C versionado (1.007 tiles, mapa 64×64).
- [x] Walkthrough actualiza el límite real de RAM y la validación DSi; skill `ds-game-dev` añade el protocolo de medición física.
- **Evidencia:** [walkthroughs/fbx-background-generator-tests/walkthrough.md](walkthroughs/fbx-background-generator-tests/walkthrough.md).

## Sesión 28: Flujo reutilizable de optimización DS
- [x] Skill local y copia de proyecto consolidadas con baseline físico, perfil por etapa, A/B de una ruta, invariantes de gameplay y estrés de escalabilidad/VBlank.
- [x] Walkthrough recoge la diferencia de coste DeSmuME/DSi y los límites de la evidencia física recibida.
- **Evidencia:** [walkthroughs/ds-game-dev-performance-workflow/walkthrough.md](walkthroughs/ds-game-dev-performance-workflow/walkthrough.md).

---

## Sesión 29: Visor FBX web offline con look DungeonDS
- [x] Visor autónomo guardado en tools/lab/FBX-Web-Renderer-offline.html y copiado a Descargas; scripts, bibliotecas y estilos están embebidos.
- [x] Presets DungeonDS/neutro/antorcha, controles de intensidad/color, sombras de key, escala visible aproximada en píxeles y encuadre con todas las poses exportadas.
- [x] Root/Hips in-place por defecto, manteniendo Y; casilla para restaurar el movimiento original.
- [x] Scripts parseados con Node; prueba sintética Root/Hips pasa.
- [ ] Prueba visual/headless pendiente: el navegador disponible bloquea la automatización de file://; no se afirma validación visual.
- **Evidencia:** walkthroughs/web-shader-lab-parity/walkthrough.md.

## Sesión 30: Corrección de animación in-place del visor web
- [x] El bloqueo horizontal reconoce nodos de raíz FBX como RootNodeL además de Root/Hips.
- [x] También fija pistas de posición escalares X/Z y conserva la componente vertical; desactivar la casilla restaura los valores originales.
- [x] Node valida la sintaxis del HTML y pruebas sintéticas cubren RootNodeL, Hips, canales por componente y restauración.
- [ ] Revisión visual del ciclo dentro del navegador pendiente; no se afirma validación del FBX real porque la automatización de file:// está bloqueada.
- **Evidencia:** walkthroughs/web-inplace-fix/walkthrough.md.

## Sesión 31: In-place según la orientación de la armadura FBX

- [x] Reproducido el fallo con mario_camisa_blanca.fbx: armadura Z-up girada −90° X; el avance está en Y local y fijar X/Z local no lo elimina.
- [x] Bloqueo horizontal en los ejes de escena mediante la matriz del padre, conservando la oscilación vertical.
- [x] Verificación headless con el lector/mixer del HTML: 101 muestras × 8 direcciones en Mario, Walking, Skeleton y Run; deriva horizontal <1e−5, altura conservada y restauración exacta.
- [x] Corregida la explicación previa sobre RootNodeL y el estado de la casilla desactivada.
- [ ] No se capturó salida WebGL; las pruebas validan transformaciones reales del FBX.
- **Evidencia:** walkthroughs/web-inplace-axis-fix/walkthrough.md.

## Sesión 32: Paridad de iluminación del visor FBX web con Blender

- [x] Preset DungeonDS alineado con Blender: key 4.5, fill 0.85, rim 0, world 0.35; colores sRGB equivalentes a los RGB lineales del worker.
- [x] World uniforme, AgX, grading de contraste/saturación y fuerza de normal maps 0.35.
- [x] Compensación de intensidades Three.js y adaptación de la orientación al sistema de cámara del visor.
- [x] Headless Chromium cargó `mario_camisa_blanca.fbx` y renderizó ocho direcciones sin errores JavaScript.
- **Evidencia:** walkthroughs/web-blender-light-parity/walkthrough.md.

---

## Sesión 33: Showcase del sector urbano WH40K (prueba física pendiente)

- [x] Escenario de 512×512 con colisión dual jugador/proyectil, oclusión de estructuras altas y personajes armonizados.
- [x] Build BlocksDS y contratos host PASS; escenario `scenarios/wh40k_showcase.json` PASS (4 capturas, 18 eventos, 3 cambios de pantalla comprobados).
- [x] ROM de 2.702.848 bytes, CRC DeSmuME `3F2A656E`, SHA-256 `B7C9599209DCF50520FF46AA6CD4EEAA0BB50878A5769F839AA42328E81991C5`; FTP cargado y nombre remoto verificado en `192.168.1.151:5000/roms/nds/dungeonds.nds`.
- [x] Primera prueba física del usuario: el escenario funciona en general; reportó bloqueo cerca del centro y parpadeo de líneas del Charger.
- **Evidencia:** `walkthroughs/wh40k-floor-preview/walkthrough.md`.

## Sesión 34: Cámara centrada, continuidad dual-screen y diagnóstico del Charger

- [x] Escenario `wh40k_camera_collision.json`: prueba el bloqueo contra el edificio, rodeo por el sur y avance hasta el borde este; el seguimiento de cámara continúa y se limita al llegar al límite del mapa.
- [x] Restaurados 6.056 píxeles opacos de contorno del Charger que la armonización había convertido en transparentes.
- [x] Build BlocksDS, contratos host, showcase y escenarios de colisión/animación PASS; ROM 2.702.848 bytes, CRC DeSmuME `0ABEE539`, SHA-256 `90154A808F77FBAF3948B184DEF37EB6233327E1AB68254A7D7F1F874462FE8D`.
- [x] Primer intento FTP agotó el tiempo; tras la petición del usuario, la segunda transferencia finalizó PASS a `192.168.1.151:5000/roms/nds/dungeonds.nds`.
- [ ] Repetir la prueba en DS con esta ROM y confirmar navegación y Charger. Mantener rama y worktree abiertos hasta esa validación.
- [x] Corrección del encuadre dual: la pantalla superior usa `cam_y - 192`, así que muestra los 192 px inmediatamente anteriores a la pantalla inferior; fuera de la huella del mundo el fondo es negro. La explicación anterior de que ambas mostraban el mismo suelo era errónea.
- [x] El generador dibuja la huella del suelo con esquinas diagonales a resolución de píxel; el exterior es transparente/negro y la misma huella bloquea movimiento y proyectiles. Escenario `wh40k_world_edge_panorama.json` PASS (4 capturas, borde norte y esquina noroeste).
- [x] Cámara centrada también al pasar sobre el vacío: en el borde norte la escena registra `cam_y=-77` y movimiento bloqueado en el límite real del suelo. Build BlocksDS, suite host (9 casos) y escenario DeSmuME (4 capturas, 20 eventos) PASS; ROM SHA-256 `6CD25AA05666395AC6DEBE8A6E17CF93F33888E0884EBD372D5BCD10C2E99D52`. Validación en DS pendiente.
- [x] Se descartó la revisión que repetía una muestra de baldosa en todo el fondo conectado: convertía el lienzo 512×512 en suelo rectangular y hacía caminables las esquinas exteriores.
- [x] El generador mantiene transparente el fondo alrededor de la losa cuadrada proyectada como rombo; render y colisión usan el mismo atlas/máscara. Escenarios norte y sur PASS con movimiento bloqueado en el vacío.
- [x] Build BlocksDS, suite host y escenarios DeSmuME norte/sur PASS; ROM CRC DeSmuME `69A83C37`. Tearing de actores ya confirmado resuelto físicamente en la DS en la prueba anterior.
- [ ] Subir y validar físicamente la revisión previa del perímetro en DS.
- **Evidencia:** `walkthroughs/wh40k-floor-preview/walkthrough.md`.

## Sesión 35: Bake del perímetro completo WH40K

- [x] La foto física reveló que la franja negra vertical venía del recorte de render: `ORTHO_SCALE=30` no encuadraba la losa de 50×50 m.
- [x] La primera revisión subió `ORTHO_SCALE` a 72 y quitó el recorte, pero redujo demasiado el tamaño aparente de las baldosas; el usuario detectó correctamente esa regresión.
- [x] Build BlocksDS PASS; 7 contratos focalizados PASS; escenarios norte y sur PASS (6 capturas en total). ROM 2.378.240 bytes, CRC `8348AD98`, SHA-256 `113355E91D490A9799F59781E77B8E517EC57E187D507E1D888D028D8D6E4DD6`.
- [x] ROM enviada por FTP a `192.168.1.151:5000/roms/nds/dungeonds.nds`; su escala visual se corrigió en la sesión 32.
- **Evidencia:** `walkthroughs/wh40k-floor-preview/walkthrough.md`.

## Sesión 36: Escala original WH40K y lienzo completo

- [x] Lienzo 1280×768 con `ORTHO_SCALE=75` conserva los mismos 17,07 px/m que 512×512 con escala 30, ahora sin recortar la losa.
- [x] Colisión 320×192 a 4 px/celda y mapa BG 160×96 mantienen el borde diagonal y el vacío negro a la escala original.
- [x] Se quitó la copia RGB555 completa del mundo: el sombreado lee el color de suelo del atlas BG; la profundidad usa celdas conservadoras de 2×2 para respetar los 4 MB de EWRAM.
- [x] Build BlocksDS PASS; contratos del proyecto (11 casos), oclusión (3) y streaming del suelo (1) PASS. Escenarios DeSmuME de entrada, showcase, borde norte y borde sur PASS.
- [x] ROM 2.488.832 bytes, CRC DeSmuME `6F146AA8`, SHA-256 `817D998A7EE766902838C549563914FB5A8629366E691865EB4C77A902ABF7E5`.
- [x] Tras el timeout inicial, la ROM se subió por FTP a `192.168.1.151:5000/roms/nds/dungeonds.nds` a petición del usuario.
- [ ] La prueba física de esta revisión queda pendiente; DeSmuME confirma geometría y movimiento, no la validación en hardware.
- **Evidencia:** `walkthroughs/wh40k-floor-preview/walkthrough.md`.

## Sesión 37: Recorrido WH40K de cuatro sectores

- [x] Se concatenaron cuatro sectores contiguos de 50 m en el eje norte-sur, manteniendo 17,07 px/m; la proyección ocupa 3200×1920 px.
- [x] La oclusión se prepara por ventana visible y la colisión se empaqueta a 2 bits por celda para caber en la RAM de la DS.
- [x] Build BlocksDS PASS; contratos configurados (11) y rejilla de oclusión (3) PASS. DeSmuME `wh40k_four_sector_walk.json`: 1100 frames, movimiento 534 px, cámara −529 px, `blocked_moves=0`.
- [x] ROM 3.456.512 bytes, CRC DeSmuME `21C12934`, SHA-256 `47A5BD64CA7EB25FE7D2AFB87F6607164969B0EADF4E55491AAC1CF4685E92E7`.
- [x] ROM de prueba subida por FTP a `192.168.1.151:5000/roms/nds/dungeonds.nds` (3.456.512 bytes transferidos); prueba física pendiente.
- **Evidencia:** captura `walkthroughs/wh40k-floor-preview/assets/18_four_sector_walk.png` y escenario `scenarios/wh40k_four_sector_walk.json`.


## Sesión 38: Colisión de edificios en sectores WH40K repetidos

- [x] Causa: el BVH tomaba los vértices locales de cada copia y omitía `matrix_world`; los sectores repetidos quedaban con edificios visuales sin colisión y colisiones fantasma en la coordenada fuente.
- [x] BVH separado para movimiento/proyectiles: transforma los vértices nuevos con `p.matrix_world`; mapa de colisión de 800×480 y flags a 2 bits.
- [x] Contrato host verifica celdas bloqueadas en las cuatro bandas del mundo; los 13 contratos host configurados pasan.
- [x] Build BlocksDS PASS; escenarios `wh40k_four_sector_walk.json` y `wh40k_camera_collision.json` PASS. Contacto de edificio: `blocked_moves=811`, `moving=0`.
- [x] ROM 3.456.512 bytes, CRC DeSmuME `8BB17AC6`, SHA-256 `CE8EECDF3C64287B4639D21A6518BC3AA5E4B0C0420B5E1D7A08BAD0395ABB3C`.
- [x] ROM subida por FTP a `192.168.1.151:5000/roms/nds/dungeonds.nds` (3.456.512 bytes); falta probarla físicamente en la DS.
- **Evidencia:** `walkthroughs/wh40k-floor-preview/assets/19_four_sector_building_collision.png` y `scenarios/wh40k_four_sector_walk.json`.

## Sesión 39: rasterización volumétrica de colisiones WH40K

- [x] El bake de movimiento sustituye dos consultas a alturas fijas por cuatro rayos verticales por celda 4×4, cubriendo toda la altura del cuerpo del personaje.
- [x] La máscara de proyectiles sigue usando su altura independiente.
- [x] Build BlocksDS PASS; 13 contratos host PASS. `wh40k_building_collision_contact.json`: el jugador permanece bloqueado 40 frames y luego rodea el edificio (6 capturas, 25 eventos); `wh40k_four_sector_walk.json`: `blocked_moves=807`, `moving=0`.
- [x] ROM 3.456.512 bytes, CRC DeSmuME `6239B895`, SHA-256 `7F44D40CCE0A56E360FD24CEF5C9944C9F9F39DBB6A24288941EDD8374EA2B05`.
- [x] La revisión 35 se envió a la DS; la prueba física confirmó que aún se atraviesan algunas partes de edificios. La revisión 36 amplía la cobertura de la máscara.
- **Evidencia:** `walkthroughs/wh40k-floor-preview/assets/20_vertical_column_building_contact.png`, `assets/21_vertical_column_sector_contact.png`, `scenarios/wh40k_building_collision_contact.json` y `scenarios/wh40k_four_sector_walk.json`.

## Sesión 40: Cobertura completa de celdas de colisión WH40K

- [x] La comparación confirmó que la rasterización anterior solo comprobaba cuatro puntos interiores de cada celda 4×4; ahora examina los 16 píxeles y mantiene el mismo formato y presupuesto de memoria.
- [x] El bake marca 802 celdas de movimiento y 12.603 celdas sólidas.
- [x] Build BlocksDS PASS; 13 contratos host PASS; escenario de contacto/rodeo PASS (6 capturas, 25 eventos).
- [x] ROM 3.456.512 bytes, CRC DeSmuME `47A5826E`, SHA-256 `32B18E3BDBBF5AE3067F4C0DBBDB7FD79A8E088CEC8232CE526F29B01393A500`.
- [ ] Subir esta revisión y comprobar en la DS que no atraviesa partes de edificios.
- **Evidencia:** `walkthroughs/wh40k-floor-preview/assets/22_dense_building_contact.png`, `assets/23_dense_building_detour.png`, `scenarios/wh40k_building_collision_contact.json`.

## Sesión 41: alineación del pie visible del Charger

- [x] Los frames del Charger llegan hasta la fila 33 del canvas, 5 px debajo de `PLAYER_ANCHOR_Y=28`; los del héroe, hasta 2 px debajo. Esto explica por qué el pie podía verse bajo un muro aunque el cuerpo quedase ocluido.
- [x] `draw_player()` y `draw_enemy()` alinean el píxel opaco inferior de cada frame con el ancla de suelo que comparten movimiento y profundidad.
- [x] Build BlocksDS PASS; 15 contratos host PASS; escenario `wh40k_charger_building_contact.json` PASS: la ruta queda bloqueada 40 frames y rodea el muro.
- [x] ROM 3.456.512 bytes, CRC DeSmuME `5ACE388F`, SHA-256 `9A5DD510B0B4A15B9A367151E0C06074EA886116934DB61FCD075248F67007A0`.
- [ ] Probar en la DS y recorrer otros tramos reportados; la captura actual confirma solo un contacto emulado. ROM aún no subida.
- **Evidencia:** `walkthroughs/wh40k-floor-preview/assets/24_charger_ground_anchor_idle.png`, `assets/25_charger_ground_anchor_contact.png`, `scenarios/wh40k_charger_building_contact.json`, `tests/test_sprite_ground_anchor.py`.

## Sesión 42: Arena sintética para aislar colisión y oclusión WH40K

- [x] Se creó una arena temporal de 1280×768 px sobre el suelo WH40K, con escala original de 17,07 px/m y ocho cajas 3D programáticas de varias orientaciones y alturas.
- [x] El proyecto temporal usa el código actual del motor, la cámara y el pipeline Blender/BG/colisión/oclusión; reemplaza solo los props FBX y conserva intacto el mapa normal.
- [x] Input preflight y escenarios de DeSmuME para UP/RIGHT/DOWN/LEFT PASS. UP se detiene ante la caja de 1,2 m; las cajas altas de RIGHT/DOWN/LEFT no generan flags WALK y el jugador las atraviesa.
- [x] Causa offline confirmada para las cajas cerradas: el rayo WALK empieza a +1,20 m y solo recorre 1,19 m; queda dentro de cajas altas y no alcanza su cara inferior. La caja de 1,2 m sí deja celdas caminables.
- [x] Build BlocksDS PASS. ROM de test 2.187.776 bytes, CRC DeSmuME `2C0163BA`, SHA-256 `32460815AAF6204C421B32E09571659B21C766608B6C49567AE179D6BA94EF3F`.
- [x] ROM de test subida por FTP el 2026-10-13 a `ftp://192.168.1.151:5000/roms/nds/dungeonds.nds` (`FTP_UPLOAD_RESULT=PASS`). Pendiente prueba física del usuario; las capturas de esta sesión son de DeSmuME.
- **Evidencia:** `walkthroughs/wh40k-collision-arena-test/walkthrough.md`.

## Sesión 43: Optimización de Oclusión a 60 FPS y Calibración de Silueta Exacta

- [x] **Causa de la caída a 30 FPS:** `build_occlusion_depth_map` tardaba 18 ms en CPU por culpa de un bitmask redundante (`s_occlusion_upper_mask`) que ejecutaba lecturas/escrituras no alineadas de 8 bits en EWRAM por cada píxel de tramo visible.
- [x] **Optimización de renderizado en ARM9:**
  - Eliminado el buffer de 48 KB `s_occlusion_upper_mask`; descarte de sombras resuelto sobre `s_occlusion_depth >= 0`.
  - Reemplazada la iteración lineal de 4.419 tramos por búsqueda binaria `find_first_occlusion_run()` ($O(\log N)$, ~12 ciclos).
  - Compilación forzada en ARM nativo 32-bit (`__attribute__((target("arm"), optimize("O3"), noinline))`).
  - Reducción del tiempo de lógica de 18 ms a 6 ms; tiempo de CPU a 9 ms; **60 FPS locked recuperados**.
- [x] **Eliminación del padding artificial:** `OCCLUSION_DEPTH_PAD_CELLS = 0` elimina los recortes en el aire al pasar junto a muros y arcos góticos.
- [x] **Calibración de escenarios de test:** Documentadas en `AGENTS.md` las reglas que impiden crear tests con nombres o precondiciones falsas en suelo abierto.
- [x] **Verificación:** Tests de host PASS, escenario `wh40k_cathedral_occlusion_exact.json` PASS (2 capturas, 17 eventos deterministas).
- [x] **Subida por FTP a hardware:** ROM final de 3,32 MB subida exitosamente a `ftp://192.168.1.151:5000/roms/nds/dungeonds.nds` (`FTP_UPLOAD_RESULT=PASS`).
- **Evidencia:** `captures/exact_occ_final/01_charger_behind_arch_wall.png`, `walkthroughs/wh40k-floor-preview/walkthrough.md`.

## Sesión 44: Transparencia de Oclusión por Frames Alternados (Flicker / Temporal Dithering)

- [x] **Visibilidad del personaje tras muros:** Se implementó entrelazado temporal en la rutina de blit de sprites (lit_stride) para que el personaje principal sea visible cuando pasa por detrás de paredes ocluyentes.
- [x] **Renderizado por alternancia:** En los frames impares (s_frame_index & 1), los píxeles ocluidos del jugador se dibujan normalmente; en los frames pares, se omiten para dejar ver la pared. En una pantalla física a 60 FPS esto produce un 50% de semitransparencia óptica fluida.
- [x] **Presupuesto de CPU (60 FPS Locked):** Telemetría en HUD confirma FPS:60 C:10 P:06 (~10% de uso de CPU).
- [x] **Verificación:** 21 contratos de host PASS, compilación BlocksDS limpia y escenario de emulación en DeSmuME validado con capturas de frames consecutivos y GIFs animados.
- **Evidencia:** walkthroughs/13-feat-occlusion-transparency/walkthrough.md, walkthroughs/13-feat-occlusion-transparency/assets/zoom_character.gif, walkthroughs/13-feat-occlusion-transparency/assets/charger_occlusion.gif.

## Sesión 45: Mazmorra Completa FBX con Despeje de Puertas, Oclusión y 60 FPS Locked

- [x] **Diagnóstico y causa raíz de bloqueos en puertas:** El raycasting vertical anterior se proyectaba ciegamente desde el cielo, bloqueando cualquier dintel o arco superior a 2.3 m de altura.
- [x] **Despeje por volumen de torso:** Se implementó raycast de torso en el rango físico $Z \in [0.3\text{m}, 1.4\text{m}]$. Como los dinteles y arcos del modelo FBX se sitúan en $Z \ge 1.71\text{m}$ (media $2.28\text{m}$), todas las puertas quedan 100% transitables y conectadas.
- [x] **Pipeline de horneado 2.5D dimétrico:** Malla de colisión 2-bit de $192 \times 128$ (5.253 celdas caminables), 2.389 tiles de hardware VRAM y 2.379 tramos RLE ordenados para oclusión exacta en arcos y pilares.
- [x] **Presupuesto 60 FPS Locked:** HUD de telemetría confirma `FPS:60 C:11 P:04` (CPU 11 ms, 0 frames perdidos).
- [x] **Verificación:** Suite de pruebas unitarias de host PASS (36/36 tests ejecutados), compilación limpia de ROM BlocksDS y escenario `scifi_dungeon_walk.json` ejecutado en DeSmuME con héroe visible y verificado a 60 FPS en pantalla inferior (GIF animado de 126 frames).
- **Evidencia:** `walkthroughs/scifi-dungeon-tripo/walkthrough.md`, `walkthroughs/scifi-dungeon-tripo/assets/scifi_dungeon_walk.gif`, `walkthroughs/scifi-dungeon-tripo/assets/scifi_collision_overlay.png`.

## Sesión 46: Sistema de Niebla de Guerra (Fog of War), Línea de Visión y 60 FPS Locked

- [x] **Arquitectura de visibilidad y memoria:** Rejillas de bits en EWRAM de 768 bytes cada una (`g_fog_explored` y `g_fog_visible`) para mapear el mundo de $96 \times 64$ tiles de $8 \times 8$ px.
- [x] **Raycaster Bresenham sin división:** 64 rayos en radio de 24 celdas (~5 metros) con interpolación de error Bresenham pura (0 llamadas a división por software en ARM9, coste < 0.05 ms).
- [x] **Ocultación en hardware BG:** Zonas inexploradas forzadas a `tile_id = 0` (negro abisal de VRAM) en `update_screen_hardware_bg` con 0 ms de CPU.
- [x] **Ocultación estricta de enemigos:** Los enemigos situados detrás de esquinas, puertas cerradas o fuera del cono de visión no se dibujan ni generan sombras dinámicas. Al entrar en el haz de visión, despiertan y persiguen al jugador.
- [x] **Trama de penumbra por palabras de 32 bits:** Zonas exploradas pero fuera de la visión activa reciben una trama checkerboard del 50% (`draw_fog_penumbra`) a alta velocidad (0.19 ms).
- [x] **Presupuesto 60 FPS Locked:** HUD de telemetría confirma `FPS:60 C:11 P:04` (CPU 11 ms, 4 ms de espera VBlank, 0 frames caídos).
- [x] **Verificación:** 41/41 tests unitarios de host PASS (incluyendo 5 contratos en `tests/test_fog_of_war.py`), compilación limpia BlocksDS y escenario `scifi_dungeon_walk.json` en DeSmuME con GIF animado de 126 frames (`fog_dungeon_walk.gif`).
- **Evidencia:** `walkthroughs/fog-and-visibility/walkthrough.md`, `walkthroughs/fog-and-visibility/assets/fog_dungeon_walk.gif`, `walkthroughs/fog-and-visibility/assets/00_spawn.png`.

## Sesión 47: Iluminación de Antorcha 3D Suave, Oscurecimiento Continuo y 60 FPS Locked

- [x] **Diagnóstico y causa de artefactos en bloques:** La binarización visible/no visible sobre tiles hardware 8x8 creaba escalonados cuadrados bruscos. Requería oscurecimiento proporcional continuo (merge con negro) y oclusiones 3D reales.
- [x] **Horneado 3D BVH completo (`tools/bake_full_smooth_lightgrid.py`):** Precomputación offline con Blender 5.2 sobre la malla FBX de 50.000 polígonos. Rejillas de luz $21 \times 21$ empaquetadas a 4 bits por nodo para las 1.614 posiciones caminables (356 KB en ROM). Rayos a $Z=1.2\text{m}$ pasan orgánicamente bajo arcos y son ocluidos por muros altos estilo *Doom*.
- [x] **Renderizado Bilineal ARM9 sin FPU (`source/smooth_lightmap.c`):** Sombreado proporcional de 16 niveles directamente en el búfer bitmap de 16bpp (`s_bot_screen_buf`).
- [x] **Optimización a 60 FPS Locked:**
  - Salto de celdas 8x8 negras completas en 1 ciclo (`(l00 | l10 | l01 | l11) == 0`).
  - Vía rápida de copia directa para celdas uniformes (`l00 == l10 && l00 == l01 && l00 == l11`).
  - Interpolación DDA incremental sin multiplicaciones en el bucle interior de pixels.
  - Tabla de sombreado directo en RAM `s_shaded_palette[16][256]` (8 KiB) sin cálculo RGB en caliente.
  - Reducción del coste de suelo de 34 ms iniciales a 7..8 ms, bloqueando 60 FPS sólidos.
- [x] **Subida a Nintendo DS física:** ROM `dungeonds.nds` (2.28 MB) transferida y verificada con éxito por FTP a `192.168.1.151:5000/roms/nds/dungeonds.nds`.
- **Evidencia:** `walkthroughs/fog-and-visibility/walkthrough.md`, `walkthroughs/fog-and-visibility/assets/fog_dungeon_walk.gif`.

---

## Sesión 48: Sombreado Atmosférico de Antorcha Continuo, Paleta Ámbar Perceptiva y 60 FPS Locked

- [x] **Diagnóstico del Efecto Binario:**
  1. *Desfase de escala geométrica:* `tools/bake_full_smooth_lightgrid.py` usaba `ortho_scale = 32.5` en vez de `38.0`, provocando que el raycast BVH impactara muros a destiempo e inyectara ceros en mitad de celdas transitables.
  2. *Curva de atenuación empinada:* La fórmula cuadrática inversa $1/(1+(d/2.6)^2)$ colapsaba a menos del 20% a sólo 3 celdas (24 px) y truncaba en el nivel 4 (30% de luz) en la frontera de 10 celdas, generando un corte visual seco.
  3. *Aplastamiento de negros en pantalla LCD DS:* La escala lineal $(c \times l)/16$ mapeaba niveles 1 a 5 a componentes RGB 0..3 (sobre 31), absolutamente indistinguibles de negro en la DS.
- [x] **Falloff Hermite Smoothstep en Blender 5.2:**
  - `ortho_scale` fijado a `38.0`.
  - Falloff smoothstep $u = d/10.0, t = 1-u, \text{smooth} = t^2(3-2t)$, repartiendo de forma perfectamente homogénea los 15 niveles a lo largo de un radio de 80 píxeles ($\sim 5.3$ px por nivel de luz).
- [x] **Paleta Perceptiva DTCM con Calidez Ámbar:**
  - Precomputación en DTCM con corrección gamma $(l/15)^{0.7}$, canal R al 105%, G al 95%, B al 75%.
  - Nivel 1 emite penumbra visible (`RGB15(2, 1, 1)`), eliminando el corte binario.
  - Bounding box ampliado a `if (val > 0)` y corte a `if (left_L == 0 && right_L == 0)`.
- [x] **Presupuesto 60 FPS Locked:**
  - Medido en HUD de telemetría de DeSmuME: `FPS:60 C:12 P:04` (CPU 12 ms, Floor lighting 8-9 ms, Present 4 ms, > 4.6 ms de holgura VBlank).
- [x] **Evidencia Visual:** `walkthroughs/19-smooth-torch-shading/walkthrough.md`, `walkthroughs/19-smooth-torch-shading/assets/smooth_spawn_v1_vs_v2.png`, `walkthroughs/19-smooth-torch-shading/assets/smooth_shading_v1_vs_v2_comparison.png`, `walkthroughs/19-smooth-torch-shading/assets/nds_smooth_torch_shading_v2.gif`.

## Sesion 49: Lab 3JS con exportacion de atlas y paquete de sprites

- [x] El visor autonomo conserva frames RGBA y exporta spritesheet transparente, PNG por frame, GIFs direccionales, collage y ZIP con ajustes.
- [x] Se anaden controles del flujo Shader Lab para rig, cuello, displacement, shader oseo, zancada, ticks, brillo, relieve y sombras WebGL.
- [x] Regla permanente: las validaciones de navegador del proyecto deben ejecutarse solo en modo headless.
- [x] Run.fbx carga y renderiza ocho direcciones con Chromium headless; PNG 384x384 RGBA transparente; paquete ZIP de 86 entradas; cero errores de consola.
- **Limite:** Three.js WebGL no reproduce Cycles ni promete igualdad pixel a pixel con Blender.
- **Evidencia:** `walkthroughs/js-lab-sprite-parity/walkthrough.md`.

---

## Sesion 50: Un solo control de tamaño para el lab 3JS

- [x] El control `Tamaño del sprite` define la celda de salida (48 × 48 px por defecto); se eliminó el slider separado de tamaño visible.
- [x] La cámara mantiene el FOV y calcula la distancia para un llenado objetivo fijo del 96%, con escala común entre frames y direcciones.
- [x] Chromium headless confirma que la interfaz muestra un único control de tamaño y carga sin errores de consola.
- **Límite:** falta revisar la ocupación real de un FBX en los frames renderizados.
- **Evidencia:** `walkthroughs/js-lab-single-size-control/walkthrough.md`.

---

## Sesion 51: Resultados de sprites por encima del visor 3D

- [x] El orden de la página coloca los GIFs y la descarga antes del visor 3D animado.
- [x] El visor 3D queda al final y reducido a 280 px de alto (240–320 px).
- [x] Chromium headless carga la página sin errores de consola; se revisó la estructura y la captura de página completa.
- **Límite:** la captura de esta sesión no carga un FBX ni muestra la cuadrícula ya renderizada.
- **Evidencia:** `walkthroughs/js-lab-results-above-preview/walkthrough.md`.

---

## Sesion 52: Eliminacion del slider Escala modelo del lab 3JS

- [x] Se elimino el control de escala visual y sus referencias del HTML generado y el codigo de carga.
- [x] El modelo conserva su normalizacion automatica; `Tamaño del sprite` sigue presente y el encuadre se actualiza con el modelo.
- [x] Chromium headless confirmo que la pagina carga sin el control de escala y conserva el tamaño del sprite.
- **Evidencia:** `walkthroughs/remove-model-scale-control/walkthrough.md`.

---

## Sesion 53: Comparacion visual del lab 3JS y Blender

- [x] Se renderizo `Run.fbx` con el clip `mixamo.com` en ambos laboratorios: 48×48 px, 8 direcciones × 8 frames, cámara a 35° y valores de luz/color alineados.
- [x] El GIF lado a lado confirma que Blender muestra una silueta más grande y luminosa; cobertura alfa media 28,6% frente a 11,0% en 3JS.
- [x] Se documentan las diferencias entre el encuadre ortográfico de Blender y el autoencuadre de 3JS, además de las diferencias entre Cycles y WebGL.
- **Evidencia:** `walkthroughs/lab3js-vs-blender/walkthrough.md`.

---

## Sesion 54: Ajuste real del tamaño visible del sprite en 3JS

- [x] El encuadre mide la malla deformada por la animación y aplica azimut 45°, como el lab Blender.
- [x] El margen deriva del tamaño de celda: 2 px con outline y 0 px sin outline.
- [x] Chromium headless renderizó 64 frames de Run.fbx: media 36.1×36.2 px a 48×48; el control 32×32 produjo 24.2×24.4 px.
- [x] La ocupación queda próxima a Blender (34×36 px de media en la comparación anterior), frente a 21.1×21.3 px antes del arreglo.
- **Límite:** WebGL conserva proyección perspectiva; Blender usa cámara ortográfica y Cycles.
- **Evidencia:** `walkthroughs/lab3js-sprite-size-fit/walkthrough.md`.

## Sesion 55: Comparativa Blender visible en el walkthrough del ajuste 3JS

- [x] Se añadió una imagen conjunta de 3JS corregido y Blender, con las ocho direcciones en celdas de 48×48 px.
- [x] El walkthrough indica FBX, clip, resolución y normalización de la escala de pantalla.
- **Evidencia:** `walkthroughs/lab3js-sprite-size-fit/walkthrough.md`.

---

## Sesion 56: Paridad Fidedigna 3JS vs Blender (FBX a Sprite)

- [x] **Cámara Ortográfica y Encuadre Canónico:** Sustitución de `PerspectiveCamera` por `OrthographicCamera` azimut 45°, encuadre unificado sobre las 8 direcciones con vértices deformados y re-anclaje de pies al suelo por frame.
- [x] **Orientación 1:1 en las 8 Direcciones:** Corrección del desfase de 45° en el yaw del rig (`135° - d * 45°`), logrando correspondencia perfecta con Blender (`best_blender_dir = [0, 1, 2, 3, 4, 5, 6, 7]`).
- [x] **Iluminación Calibrada y Vectores de Luz:** Escalado de intensidades de luz por $\pi$ (equivalencia BRDF Lambertiana vs $W/m^2$ de Blender), colores exactos y transformación matemática de ejes Blender (Z-up) a Three (Y-up), corrigiendo inversión en Z.
- [x] **Materiales PBR Equivalentes a Principled BSDF:** Conversión automática de materiales del FBX a `MeshStandardMaterial` blanco puro con diffuse `sRGB`, normal map 0.35, roughness 0.5, metalness 0.0 y emisión en `sRGB`.
- [x] **Filtrado y Reducción Blackman-Harris 4×:** Implementación de supersampling con filtro Cycles Blackman-Harris (1.5 px) y control en UI (`labSupersample`).
- [x] **Harness Automatizado de Comparación:** Script `tools/lab/compare_labs.py` con Playwright headless y backend de Blender, validando métricas objetivas (IoU de silueta sube de 0.275 a **0.809**, centroides alineados a < 0.04 px y luminancia alineada a 66.6 vs 60.3 de Blender).
- **Evidencia:** `walkthroughs/lab3js-blender-parity/walkthrough.md`.

---

## Sesion 57: Laboratorio Web Offline de Ensamblaje de Armas, Retargeting e IK a `.FBX` Binario

- [x] Construcción de `tools/lab/FBX-Weapon-Anim-Lab-offline.html` (3.21 MB, 100% Web Offline autónomo) junto a sus módulos fuente (`fbx_binary_splicer.js`, `retarget_and_ik_engine.js`, `glb_loader_minimal.js`, `seed_catalog_data.js`, `weapon_anim_lab_app.js`, `build_weapon_anim_lab.py`).
- [x] Parser y Splicer binario **Kaydara FBX Binary 7400** sin pérdida: conserva mallas, `Deformer` (pesos de skinning) y texturas originales del personaje, inyecta el arma (`Geometry`, `Model`, `Material`, `Texture`/`Video`) emparentada al nodo `Model` del hueso de la mano, e inyecta las curvas de animación horneadas (`AnimationStack`, `AnimationLayer`, `AnimationCurveNode`, `AnimationCurve`).
- [x] Auto-alineación geométrica de armas (`.glb` y `.fbx`) mediante PCA 3x3 (Jacobi) + heurística de polaridad cañón/culata y mira/cargador + base anatómica palmar de `RightHand`, con botones de inversión rápida 90°/180°, sliders y gizmo interactivo en viewport (`[G]`, `[R]`, `[F]`).
- [x] Retargeting universal entre esqueletos heterogéneos (Mixamo 65 huesos, Tripo3D 37-52 huesos, Meshy) con bloqueo In-Place X/Z, plantado de pies sobre el suelo (`Y=0`), cierre procedural de dedos y **solver IK analítico de 2 huesos** (`LeftArm -> LeftForeArm -> LeftHand`) hacia el guardamanos del rifle.
- [x] Catálogo semilla pre-empaquetado con 5 armas (`AK-47`, `M4 Carbine`, `Battle Rifle`, `Tactical SMG`, `Gothic Broadsword`) y 10 animaciones, extensible con importación por lotes de `.fbx` Mixamo y persistencia en `IndexedDB`.
- [x] Verificación E2E headless en Chromium (Playwright) con cero errores de consola: exportación de `spacemarine_ak47_rifle_run.fbx` (22.63 MB) y renderizado exitoso de las 8 direcciones en `tools/lab/FBX-Web-Renderer-offline.html`.
- **Evidencia:** `walkthroughs/fbx-weapon-anim-lab/walkthrough.md`.

---

## Sesion 58: Corrección del Centrado Multimodelo (Mario, Henar, Wizard, Necron) en Three.js

- [x] **Diagnóstico de Causa Raíz:** Detección de que el loader `Lf` usaba `Box3.setFromObject(e)` sin evaluar el skinning/huesos, lo que en mallas Tripo/Mixamo calculaba un desfase espurio de bind-pose (`Z ≈ -50` cm) e inyectaba `+50` cm a `model.position.z`, provocando que el rig describiera una órbita circular de 15 px de radio (`cx` entre 8.6 y 38.4 px) a lo largo de las 8 direcciones.
- [x] **Guarda en `setFromObject`:** Añadida guarda `if (!object) return this;` en el interceptor `hr.prototype.setFromObject` de `FBX-Web-Renderer-parity.js` para blindar contra llamadas con objetos no inicializados durante cargas asíncronas.
- [x] **Reemplazo Canónico de `Lf` y Hook `Ap`:** Para modelos con armadura/huesos, el pivote horizontal se fija estrictamente en el origen del rig `(0, 0)` (igual que Blender `CameraRig`), apoyando el vértice posado más bajo en `Y=0`. Para modelos estáticos sin huesos se centra horizontalmente en base a los vértices reales.
- [x] **Alineación Geométrica de Cámara en `Qf`:** Eliminación del desplazamiento hardcodeado empírico `- 1.48 * pixelWorld` en `center.upAxis`, adoptando el punto medio exacto `(minV + maxV) / 2` equivalente a `((_min_y + _max_y) * 0.5)` de Cycles.
- [x] **Validación Multimodelo con Blender (IoU):**
  - Mario: IoU de silueta sube de **12.5%** a **94.21%**, con coincidencia 100% en las 8 direcciones (`best_dir = [0,1,2,3,4,5,6,7]`) y centroides alineados a < 0.1 px.
  - Henar: IoU alcanza **95.58%**, centroide horizontal `cx` en 23.5 ± 0.7 px.
  - Wizard: IoU alcanza **94.91%**, centroide horizontal `cx` en 23.5 ± 0.5 px.
  - Necron: Centrado perfecto en 23.5 ± 0.4 px en las 8 direcciones (antes oscilaba entre 8.6 y 38.4 px).
  - Charger: IoU sube de **80.87%** a **84.68%**.
- **Evidencia:** `walkthroughs/lab3js-centering-fix/walkthrough.md`.

---

## Sesión 59: Correcciones de Animación, Retargeting e IK de Armas

- [x] Corregida la discontinuidad de `rifle_idle`: salto máximo de cabeza de 0.9439588 a 0.0001027575 alturas de personaje en 186 muestras.
- [x] Motor verificado: alineación semántica en cuatro armas, 60 contactos de palma alcanzables (error máximo 4.59677e-8 alturas) y mezcla híbrida en cuatro fases (error local máximo 4.22e-8 rad; cadera sin error).
- [x] Extracción compatible con proxies Mesh planos animados en `skeleton_death.fbx`, con prioridad estricta para Bones humanoides reales.
- [x] Tests unitarios del motor (5 secciones), splicer (2 materiales) y chequeo de sintaxis PASS.
- [x] Regenerados catálogo (2.33 MB) y HTML autónomo (3.28 MB) con `rifle_walk_ready` («Caminar en ristre») y `rifle_run_ready` («Correr en ristre»); 11 clips compartidos únicos (9 fuentes base + 2 híbridos), además de clips propios de personajes cuando se cargan; E2E exportó FBX de 22.72 MB y el visor lo cargó.
- [x] Dedupe probado: `Slash.fbx` y `JumpHit.fbx` tienen 59 muestras, las mismas 23 pistas canónicas y valores idénticos; `melee_jump_hit` se quita del catálogo. Regresión compara ambas fuentes; walk/run/crouch y los dos modos ready siguen separados.
- [x] Matriz headless: 5 personajes × 4 armas; ambos modos `rifle_walk_ready`/`rifle_run_ready` probados con shotgun y sniper. `Death Fall` aparece en Combat, se selecciona y prepara retarget (1.233 s). Contacto máximo 1.61e-8 alturas, orientación dot ≈1, sin errores JavaScript.
- [x] FBM: shotgun 14 mapas / 4,424,669 bytes / 14 grupos; sniper 13 / 6,641,310 bytes / 13 grupos.
- [x] Ambos híbridos se exportaron/reimportaron en shotgun y sniper. Se conservan 14 materiales/mapas del arma de shotgun y los 13 slots, grupos y mapas del sniper; FBXLoader reimporta los nodos de geometría/materiales. Los FBX contienen 19 Texture + 19 Video + 15 Material (shotgun) y 18 Texture + 18 Video + 14 Material (sniper), incluidos materiales del personaje. Evidencia: 10 capturas y `walkthroughs/weapon-anim-lab-fixes/assets/headless-summary.json`.
- **Alcance:** worktree de `fix/weapon-anim-diagnosis`; `main` intacta. Sin afirmaciones de FPS ni validación en Nintendo DS.
- **Evidencia:** `walkthroughs/weapon-anim-lab-fixes/walkthrough.md`.

---

## Sesión 60: Reorganización Integral de Assets 3D, Spritesheets y Render de Mazmorra Consistente

- [x] **Reorganización Integral del Catálogo 3D:** Modelos clasificados bajo `assets/models/`: `characters/` (monster, charger, skeleton, necron, spacemarine, custom), `environment/` (scifi_dungeon, dreadhollow), `weapons/` (shotgun, sniper, sword) y `animations/` (combat, rifle).
- [x] **Directorio Canónico de Spritesheets:** `assets/sprites/` estructurado con `characters/` (preparado con `README.md` explicativo para recepción directa de paquetes exportados desde el Shader Lab) y `dungeon/`.
- [x] **Almacén Histórico Preservado:** Todo el contenido descartado (runs de laboratorio `lab_runs`, renders intermedios `render_runs`, spritesheets heredados `dungeon_e30`/`e60`, previews y demos anteriores de Mario) migrado a `archive/`.
- [x] **Render de Mazmorra Consistente con Three.js:** Pre-renderizado de la mazmorra 3D de test con preset de antorcha cálida ámbar `(1.0, 0.76, 0.46)`, relleno frío `(0.45, 0.55, 0.75)` y contraste `1.50`, produciendo `test_dungeon_warm_torch_c15.png` y mallas de colisión y oclusión sincronizadas.
- [x] **Verificación de Compilación y Suites:** Build BlocksDS (`DS_BUILD=PASS`) y 16 contratos de tests unitarios de host aprobados al 100%.
- **Evidencia:** `walkthroughs/asset-reorganization/walkthrough.md`.

---

## Sesión 61: Rediseño Integral FBX-to-Sprite Lab, Renderizador 3D de Mapas y Simulador Nintendo DS

- [x] **Layout 100vh Zero-Scroll Estricto:** Reestructuración completa de la UI (`FBX-Web-Renderer-parity.js` y `FBX-Web-Renderer-offline.html`). Sidebar izquierdo modular de 360px con pestañas compactas (`Escala y Archivos`, `Luz y Cámara`, `Shader y Post`) y barra de acciones fija inferior.
- [x] **Tira de 8 Direcciones en Tiempo Real:** 8 tarjetas (`0_S` a `7_SE`, 155px de alto) con canvases pixelados interactivos. Sincronización bidireccional inmediata con el simulador al hacer click sobre cualquier orientación.
- [x] **Split 50/50 Inferior (Visor 3D + Simulador NDS):**
  - **Visor 3D:** Three.js OrbitControls, cuadrícula táctica métrica, métricas de malla (vértices, caras, tamaño en metros) y conmutador `Personaje / Mapa / Ambos`.
  - **Simulador Nintendo DS:** Canvas nativo 256×192 y modo Dual-Screen 256×384, zoom dinámico (1x, 2x, 3x, Fit), badge de métricas (`world_x/y`, celda de grid, FPS, facing), movimiento interactivo con WASD / flechas y dragging con puntero.
- [x] **Renderizador de Mapas 3D (.FBX y .GLB) y Corrección de Escala Métrica:**
  - Soporte integrado de `.fbx` (vía `cf` FBXLoader) y `.glb` (vía `MinimalGLBLoader` + synthetic `THREE_ENV`).
  - Auto-leveling de suelo a `minZ = 0`, auto-escalado horizontal a span métrico (`targetSpanMeters / rawSpan`, defecto 24.0 m) evitando modelos desmedidos de 2400 m, y cálculo automático de densidad de píxeles (`px/m`).
  - Sincronización asíncrona de texturas (`waitForModelTextures`) esperando a la carga de Blob URLs para garantizar render no negro con texturas completas en el simulador.
  - Encuadre isométrico 3D automático en `(16, 14, 16)` con plano lejano ampliado a 1000.
  - Renderizado dimétrico ortográfico a 45° de acimut y elevación compartida sin contornos de silueta.
  - Exportador a ZIP del mapa: `<name>_world.png` + `<name>_map_settings.json`.
- [x] **Pipeline Reactivo en Tiempo Real:** Sliders con previsualización inmediata (`ss=1`) en `input` vía `requestAnimationFrame` y render de máxima fidelidad (Blackman-Harris 4x) en `change`.
- [x] **Compilador Offline Actualizado:** `tools/lab/build_offline_renderer.py` inyecta automáticamente `glb_loader_minimal.js` y `FBX-Web-Renderer-parity.js` de forma atómica.
- **Evidencia:** `walkthroughs/fbx-sprite-map-lab/walkthrough.md`.

---

## Sesión 62: Refinamiento de Arquitectura a 3 Columnas, Soporte Multi-Material FBX/GLB, Auto-Framing Ortográfico, Nivelación por Histograma y Anclaje 3D

- [x] **Arquitectura de 3 Columnas Zero-Scroll (100vh):**
  - Col 1 (330px): Sidebar con 3 pestañas (`Escala y Archivos`, `Luz y Cámara`, `Shader y Post`) y barra de acciones inferior fijada.
  - Col 2 (430px): Panel vertical dedicado `#labCenterPanel` con cuadrícula de 2 cols × 4 filas para los 8 sprites/GIFs direccionales (`width: auto`, `height: calc(100% - 24px)`, aspect-ratio 1:1, rendering pixelado).
  - Col 3 (1fr): Stage principal (>600px) con selector por pestañas entre *🎮 Pantalla Nintendo DS (256×192)* y *🧊 Visor 3D Interactivo*.
- [x] **Soporte Multi-Material y Colores Base en .GLB y .FBX:**
  - `glb_loader_minimal.js` actualizado para procesar `meshData.groups` y `meshData.materials`, instanciando array de materiales con factores difusos y emisivos.
  - `FBX-Web-Renderer-parity.js` preserva colores base (`mat.color`, `mat.emissive`) cuando no hay texturas difusas.
  - Modelo `assets/models/environment/blockout/blockout_scene.py` y exports FBX/GLB actualizados sin el plano gigante de 200×200m.
- [x] **Auto-Encuadre Ortográfico Dimétrico y Control `#mapPixelSize`:**
  - Eliminados sliders confusos (`#mapResolution`, `#mapMeshScale`, `#mapOrthoScale`, `#rigScale`).
  - Auto-framing matemático proyectando los 8 vértices de la bounding box sobre los ejes `right` y `up` de la cámara ortográfica.
  - Control `#mapPixelSize` de resolución unificada (256 a 1536 px).
- [x] **Auto-Nivelación por Histograma Ponderado de Áreas de Suelo:**
  - Algoritmo de detección de caras horizontales (`|norm.y| > 0.8`), cálculo de área de triángulos y binning en cubos de 5 cm. El bucket con mayor superficie acumulada se traslada exactamente a `Y = 0`.
- [x] **Anclaje de Pies 3D a Y=0 y Sincronización Métrica:**
  - `groundCharacterIn3D()` compensa la traslación de la raíz `$.modelRoot.position.y -= minY` para que los pies reposen sobre el plano de suelo (error < 0.05m).
  - `sync3DRelativeScale()` escala el mapa en 3D para guardar estricta coincidencia proporcional con el sprite 2D del simulador DS.
- [x] **Cero Ghosting en Simulador DS y Desbloqueo de Iluminación:**
  - Borrado explícito a `#000000` en `drawDsSimulator()`, garantizando márgenes exteriores a negro sólido sin estelas.
  - Eliminados clamps hardcodeados de luz, permitiendo iluminación compartida fidedigna.
- [x] **Verificación Automatizada Headless con Playwright:**
  - Suite determinista `tools/lab/verify_lab_refinements.py` aprobada al 100% (zero-scroll 100vh, proporciones 330/430/1fr, Run.fbx, blockout FBX multi-material, reactividad de luz/elevación, cero ghosting, anclaje pies Y=0, blockout GLB y Sci-Fi Dungeon).
- **Evidencia:** `walkthroughs/fbx-sprite-map-lab/walkthrough.md`.

---

## Sesión 63: Grid 2D de Walkability y Motor de Colisiones Físicas para Mapas 3D en el Simulador Nintendo DS

- [x] **Extracción de Grid 2D de Walkability desde Geometría 3D (`buildMapCollisionGrid`):**
  - Rasterización de triángulos de suelo (`|norm.y| > 0.70`, `midY ≈ 0`) marcando bit `1` (FLOOR) en celda métrica de 4 px.
  - Rasterización del footprint en el plano XZ de obstáculos, muros y coberturas bajas (`maxY > 0.30`, `minY < 1.0` o caras superiores horizontales de cobertura) marcando bit `2` (BLOCKED).
  - Manejo robusto de triángulos degenerados/verticales (`denom < 1e-5`), eliminando falsos bloqueos rectangulares en pasillos estrechos.
- [x] **Proyecciones Bidireccionales 2D/3D Matemáticas:**
  - `worldXZToMapPixel(x, z)`: Proyecta coordenadas de mundo sobre la cámara ortográfica dimétrica dim_u / dim_v.
  - `mapPixelToWorldXZ(mx, my)`: Inversión 2×2 exacta para trasladar la posición de pies del sprite 2D a coordenadas 3D del mundo.
- [x] **Garantía de Spawn en Suelo Transitable (`ensureCharacterOnWalkableFloor`):**
  - Verificación de margen de seguridad y clearance alrededor del personaje.
  - Posicionamiento automático en pasillo despejado (evitando bloques de cobertura centrales como `cover_mid`) y búsqueda radial + escaneo exhaustivo más cercano al centro.
  - Recentrado de cámara DS (`dsPanX`, `dsPanY`) sincronizado con el spawn.
- [x] **Motor de Movimiento y Bloqueo de Colisiones en Tiempo Real (`tryMoveCharacter`):**
  - Soporte de movimiento interactivo con WASD / cursores y arrastre de ratón.
  - Bloqueo estricto de entrada a celdas con bit `2` o fuera de suelo transitable (`isMapPixelWalkable`).
  - Deslizamiento sobre ejes (sliding X / Y) y bisección suave en la frontera de impacto sin penetración geométrica.
  - Sincronización continua en el visor 3D interactivo (`syncCharacter3DPositionFrom2D`).
- [x] **Verificación Headless con Playwright al 100%:**
  - Suite `tools/lab/verify_lab_refinements.py` aprobada con validación de spawn transitable, colisión y bloqueo contra obstáculos centrales en Blockout FBX, Blockout GLB y Sci-Fi Dungeon FBX.
  - Evidencia visual regenerada y sincronizada en artefactos y walkthrough.
- **Evidencia:** `walkthroughs/fbx-sprite-map-lab/walkthrough.md`.




---

## 2026-10-18 - Entrega Completa del Sistema de Gameplay y Combate Doom-Style (Fases 0 a F)

### Objetivo y Resumen
Diseño e implementación de extremo a extremo de la IA de enemigos (Charger y Tirador necrón), sistema de armas con apuntado táctil, pickups, oleadas por sala, y progresión de mazmorra, asegurando 60 FPS fijos en Nintendo DS.

### Componentes Entregados
1. **Purga de Fog of War & Módulo de Visión Pura (`source/los.c`, `include/los.h`):**
   - Eliminados ~2.200 líneas de código legacy (`baked_visibility.c`, `fog_of_war.c`).
   - Algoritmo de línea de visión directa (Bresenham) ultra-eficiente sobre `g_dungeon_collision`.
2. **Sistema de Combate y Daño (`source/gameplay.c`, `include/gameplay.h`):**
   - 100 HP + armadura con absorción fraccional entera.
   - Pool de pickups en suelo (vida, armadura y munición por tipo).
   - Tablas `const` de parámetros marcadas `/* TUNABLE-PLACEHOLDER */` en punto fijo `8.8` (cero flotantes).
3. **IA de Enemigos (`source/enemy_ai.c`, `include/enemy_ai.h`):**
   - **Charger:** FSM estilo Pinky (`IDLE` -> `ALERT` -> `CHASE` -> `ATTACK` -> `SEARCH`), persecución rápida sin telegraph, mordisco melee y pérdida de objetivo tras 3s sin LOS.
   - **Tirador necrón:** FSM de control de espacio (`IDLE` -> `ALERT` -> `POSITION` -> `AIM` -> `BURST(3)` -> `COOLDOWN`), strafe lateral, mantenimiento de banda de distancia y predicción lineal de disparo (*lead*).
   - Amortización de evaluación de LOS alternando frames para garantizar presupuesto.
4. **Pool de Proyectiles (`source/projectiles.c`, `include/projectiles.h`):**
   - Soporte desacoplado para proyectiles físicos lentos y hitscan.
   - Colisión con geometría sólida (`bullet_position_is_free`) y daño al jugador.
5. **Arsenal del Jugador y Controles Táctiles (`source/weapons.c`, `include/weapons.h`):**
   - **Pistola:** Munición infinita, trazador lineal preciso.
   - **Escopeta:** Cono de 5 perdigones con dispersión angular y retroceso.
   - **Gatling:** Cadencia ultra-rápida con penalización del 50% a la velocidad al disparar.
   - **Pesada (Lanzacohetes):** Proyectil de alto calibre con explosión radial en área.
   - Cambio de arma en tiempo real con botones `L`/`R`.
   - Apuntado y disparo vectorial con stylus/touchscreen en pantalla inferior.
   - HUD ampliado de 4 líneas con estado de HP, armadura, arma seleccionada y munición.
6. **Gestor de Oleadas y Progresión (`source/encounters.c`, `include/encounters.h`):**
   - Estados de sala `IDLE` -> `ACTIVE` -> `CLEARED`.
   - Reaparición de oleadas mixtas en coordenadas transitables garantizadas.
   - Drops garantizados de recompensas al limpiar la sala y apertura del portal de salida al siguiente piso.

### Verificación y Rendimiento
- **Tests Host:** 9 suites completas pasando (`DS_HOST_TESTS=PASS`).
- **Toolchain BlocksDS:** Compilación limpia y enlace sin advertencias (`DS_BUILD=PASS`, ROM `dungeonds.nds`).
- **Validación Headless DeSmuME:**
  - `scenarios/weapons_switching_and_touch.json`: PASS (ciclo de armas, apuntado táctil y explosiones).
  - `scenarios/room_encounter_test.json`: PASS (oleada, combate, aniquilación de enemigos, apertura de portal).
  - Rendimiento verificado: **60 FPS fijos** (`cpu_ticks <= 33514`, tiempo lógico CPU < 1 ms).




---

## 2026-10-20 - Sesión 62: Sincronización Automática de Zancada (Stride Preview) y Eliminación de Foot Sliding en Simulador NDS

### Objetivo y Resumen
Eliminación integral del patinaje sobre hielo (*foot sliding*) en el simulador interactivo de Nintendo DS de `FBX-Web-Renderer`. Extracción automática de la zancada 3D del modelo mediante tres estrategias (root motion, muestreo de huesos de pies o fallback antropomórfico invariante), cálculo de la zancada efectiva en píxeles sobre la pantalla DS, sincronización de frames acumulativa y acoplamiento con la velocidad fija (`speedFixed8_8`) exportada en `settings.json`.

### Componentes Entregados
1. **Extracción Automática de Zancada 3D (`stride3D`) y Ratio Invariante (`FBX-Web-Renderer-parity.js`):**
   - Detección de desplazamiento del hueso raíz horizontal ($\Delta X, \Delta Z$) antes de fijar in-place.
   - Muestreo a 16 puntos de animación de separación máxima de huesos de pies (`LeftFoot`/`RightFoot`, `LeftToeBase`/`RightToeBase`, Mixamo/rig) para clips in-place ($D_{3D} = 2 \times \max_t \text{dist}_{XZ}(t)$).
   - Fallback invariante seguro $\text{strideRatio} = 0.833$ ($1.50$ m para $1.8$ m).
2. **Cálculo de Zancada Efectiva en Canvas DS (`getEffectiveStridePx`):**
   - Proyección 1:1 sobre la altura visual real del sprite en la pantalla DS (`spriteVisibleHeightPx * strideRatio`).
3. **Sincronización Acumulativa de Movimiento en Simulador NDS:**
   - Acumulador `state.charWalkDistAccum` en arrastre con ratón (`isDraggingChar`) y teclado (WASD/flechas).
   - Avance estricto de frames: `while (charWalkDistAccum >= pxPerFrame) { charAnimFrame = (charAnimFrame + 1) % frameCount; }`.
   - Eliminado el hardcoded `% 16` y el avance incondicional por evento de ratón.
4. **UI de Laboratorio y Exportador de Sprites:**
   - Control interactivo `#stride3d` con auto-detección y override manual.
   - Badges de métricas en barra lateral y HUD del simulador DS (`Zancada: 1.42m (38px, r=0.83)`).
   - Exportación de `stride3dMeters`, `strideRatio`, `ticksPerFrame`, `stridePixels` y `speedFixed8_8` en `settings.json`.
5. **Autonomía Offline:**
   - Regenerado `FBX-Web-Renderer-offline.html` con paridad integrada.

### Verificación Automatizada
- **Test Headless Playwright (`tools/lab/test_stride_preview_headless.cjs`):**
  - Carga de laboratorio autónomo con cero errores de consola (`errors.length === 0`).
  - Arrastre de 30 micro-eventos sumando 1 zancada: exactamente 7-8 transiciones de frame (1 ciclo completo de 8 frames), validando la eliminación del patinaje sobre hielo.
  - Micro-arrastre de 1 frame: exactamente 1 transición de frame.
  - Input `#stride3d`: verificación de recálculo dinámico de ratio y píxeles en canvas.
  - Modelo real FBX (`spacemarine.fbx`): verificación de métricas y renderizado de sprite en simulador.
- **Evidencia Visual:** `walkthroughs/fix-lab-stride-preview/walkthrough.md`.

---

## Sesión 63: Exportación Completa de Sombras, Anchor y Datos de Mapa (Colisión/Oclusión)
- [x] **Cálculo y Exportación Automática del Anchor:** Proyección 3D $\rightarrow$ 2D del contacto de suelo `(0, 0, 0)` bajo cámara ortográfica y escaneo de los píxeles opacos de los frames renderizados para obtener `dirGroundAnchors[8]`, `dirBounds[8]` y el anclaje global `anchor: [anchorX, anchorY]`.
- [x] **Alineación Milimétrica en Simulador DS:** Sustituido el offset hardcodeado por `screenX - anchorX`, `screenY - dirGroundAnchorY`, eliminando flotabilidad o hundimiento y sincronizando los pies del sprite con el centro de la sombra.
- [x] **Generación de Sombras Proyectadas (`generateCharacterShadows`):** Proyección planar 3D de los vértices/triángulos del personaje sobre $Y=0$ siguiendo el vector de luz principal (Key light). Generación de atlas de sombras NDS de `768x96` px (8 direcciones de `96x96` px centradas en `(48, 48)`).
- [x] **Máscaras NDS de 4 Bits y Bounds:** Empaquetado de nibbles `(hi << 4) | lo` con niveles 0..15 ($96 \times 96 / 2 = 4608$ bytes por dirección) y bounding boxes de sombra (`shadowBounds`).
- [x] **Exportación Completa de Personaje (`exportPackage`):** Inclusión de `${name}_shadow.png`, carpeta `shadows/` con 8 sombras individuales, archivo C auto-generado `${name}_nds_shadow_anchor.h` y metadatos en `settings.json`.
- [x] **Exportación Completa de Mapa (`exportMapPackage`):** Inclusión de `${name}_world.png`, `${name}_map_settings.json`, `${name}_collision.json` (grilla celda a celda $4 \times 4$), `${name}_collision.png` (b/w) y `${name}_occlusion.png` (máscara de oclusión de geometría con altura $3D > 0.65$ m).
- [x] **Sincronización Offline:** `build_offline_renderer.py` integró la capa de paridad en `FBX-Web-Renderer-offline.html`.
- [x] **Verificación Headless:** Test Playwright `tools/lab/test_shadow_anchor_export_headless.cjs` con cero errores fatales de consola y aserciones de exportación y métricas superadas al 100%.
- **Evidencia Visual:** `walkthroughs/feat-lab-shadow-anchor-export/walkthrough.md`.

---

## Sesión 64: Cálculo Automático de Ticks/Frame (AnimTicks) y Persistencia del Botón de Descarga ZIP
- [x] **Persistencia Garantizada de `#downloadPackageBtn`:** Eliminada la manipulación oculta en `Np(e)` que ejecutaba `op.style.display = 'none'`, soporte unificado de IDs `#downloadPackageBtn` y `#renderBtn` con alias para `#btnExportZip` y `#btnRender`, regla inyectada `display: inline-flex !important;` y centinela `MutationObserver` para mantener el botón siempre visible y operativo antes, durante y después del renderizado completo.
- [x] **Cálculo Cinemático Automático de `animTicks` a 60 Hz:** Deducción de `state.autoAnimTicks = Math.max(1, Math.min(30, Math.round((clipDuration * 60) / frameCount)))` a partir de `clip.duration` y `getExportFrameCount()`. Actualización automática del input `#animTicks`.
- [x] **Gestión de Override de Usuario (`dataset.userEdited`):** Flag `userEdited` cuando el usuario ingresa un valor manual, protegiéndolo de sobreescrituras automáticas, y reseteo inmediato al cambiar de modelo, alternar animación o vaciar el campo.
- [x] **Telemetría y Badge UI (`#strideMetricsHint`):** Inclusión de indicador interactivo mostrando ticks y velocidad de motor en punto fijo 8.8 (`3t/f @60Hz -> speed8.8=181`), reflejado en la barra lateral, en `updateDsMetricsBadge()` y durante la navegación por teclado (`WASD`/flechas) en el simulador DS.
- [x] **Sincronización Offline:** Actualizado `FBX-Web-Renderer-offline.html` mediante `build_offline_renderer.py`.
- [x] **Verificación Automatizada Headless:** Test Playwright `tools/lab/test_autoticks_and_zip_btn_headless.cjs` superado al 100% con cero errores de consola y capturas antes/después del renderizado.
- **Evidencia Visual:** `walkthroughs/fix-lab-autoticks-and-zip-btn/walkthrough.md`.

---

## Sesión 65: Nombres Cortos de Exportación ZIP (Anti MAX_PATH) y Reactividad de Inclinación de Cuello / Cabeza
- [x] **Nombres Cortos de Exportación en UI (`#exportCharName` y `#exportMapName`):** Añadidos campos limpios de texto editables junto a los botones de exportación, con valores por defecto cortos (`hero`, `dungeon`, o deducidos del archivo), sanitización automática a `a-z0-9_` y límite estricto de 20 caracteres.
- [x] **Estructura Interna de ZIP Inmune a `MAX_PATH` de Windows:** Rediseñadas las rutas internas en `exportPackage()` y `exportMapPackage()` eliminando carpetas redundantes y prefijos concatenados kilométricos. Cada ruta interna mide $\le 19$ caracteres (estrictamente $< 35$ caracteres): `spritesheet.png`, `shadow.png`, `collage.gif`, `dirs/0_S.gif`, `frames/0_S/0.png`, `shadows/0_S.png`, `nds_shadow_anchor.h`, `settings.json`, `README.md` (y para mapas: `world.png`, `collision.png`, `collision.json`, `occlusion.png`, `map_settings.json`). El archivo descargado se nombra `${name}.zip`.
- [x] **Neutralización de Handlers Antiguos:** Garantizado que `#downloadPackageBtn` / `#btnExportZip` y `#btnDownloadAll` ejecuten exclusivamente el exportador limpio de `FBX-Web-Renderer-parity.js`.
- [x] **Detección Automática de Huesos de Cuello y Cabeza:** Búsqueda flexible e insensible a mayúsculas/minúsculas para rigs Mixamo (`mixamorig:Neck`, `mixamorig:Head`), Blender (`Neck`, `Head`), Bip01 y detección geométrica del cubo superior de cabeza en el modelo demo procedimental.
- [x] **Cálculo Anatómico del Eje de Inclinación (Pitch) en Three.js:** Determinación dinámica del eje local del hueso más alineado con el eje lateral del modelo en espacio raíz $(1, 0, 0)$ y corrección de signo para cabeceo coherente con Blender / Cycles.
- [x] **Hook en `Three.js AnimationMixer` (`update` y `setTime`):** Inyección del offset de inclinación inmediatamente después de evaluar cada pose de animación, impidiendo que el mixer sobreescriba la inclinación de la cabeza.
- [x] **Sincronización Bidireccional de Controles (`#neckPitch` y `#neckTilt`):** Integración de slider continuo y campo numérico sincronizados con indicador angular en vivo (`0°`), reflejando cambios al instante en la vista 3D, los 8 paneles direccionales y el canvas del simulador Nintendo DS.
- [x] **Sincronización Offline:** `build_offline_renderer.py` integró la capa de paridad en `FBX-Web-Renderer-offline.html`.
- [x] **Verificación Automatizada Headless:** Test Playwright `tools/lab/test_zip_names_and_neck_tilt_headless.cjs` superado al 100% con 0 errores de consola, comprobación estricta de rutas de ZIP $< 35$ caracteres, delta de rotación de mundo tras `mixer.update` y divergencia de píxeles renderizados.
- **Evidencia Visual:** `walkthroughs/fix-lab-zip-names-and-neck-tilt/walkthrough.md`.

---

## Sesión 66: Corrección Anatómica del Eje de Inclinación de Cuello y Sincronización Total del Input Numérico
- [x] **Diagnóstico y Corrección de Input Numérico Ignorado (`#neckTilt`):**
  - Identificada la causa raíz: un interceptor erróneo en `document.getElementById('neckTilt')` y `document.querySelector('#neckTilt')` forzaba el retorno del slider `#neckPitch`, privando al `<input type="number">` de cualquier listener de eventos.
  - Eliminado el alias incorrecto del DOM.
  - Sincronización bidireccional completa en `syncNeckTilt()` respondiendo a eventos `input`, `change` y `blur`, actualizando instantáneamente `#neckPitch`, `#neckPitchValue`, `state.neckPitch`, la vista previa 3D y el simulador DS sin requerir arrastrar el slider.
- [x] **Cálculo Anatómico del Eje de Inclinación de Cabeza / Cuello (Pitch Sagital):**
  - Eliminado el algoritmo anterior de aproximación a ejes cardinales locales (`(1,0,0)`, `(0,0,1)`), el cual introducía torsión lateral (roll) hacia los hombros en modelos Mixamo/FBX con orientación ósea no estándar (`spacemarine.fbx` presentaba un error lateral $\Delta X = 0.0374$).
  - Extraído el eje lateral universal que une ambos hombros en tiempo real ($\vec{u}_{\text{lateral}} = \text{normalize}(\mathbf{p}_{\text{LeftShoulder}} - \mathbf{p}_{\text{RightShoulder}})$ con proyección horizontal $Y=0$), con fallback a caderas/piernas y eje lateral del modelo en espacio mundo.
  - Proyección del eje al espacio padre del hueso en la pose actual y premultiplicación del cuaternión (`bone.quaternion.premultiply(qPitch)`).
  - Verificación matemática de idempotencia y reversibilidad absoluta (error de reversibilidad $1.56 \times 10^{-17}$), neutralizando acumulaciones en ticks sucesivos del mixer.
  - **Error lateral $\Delta X$ reducido a $0.000000$ (0 roll)** en `spacemarine.fbx` con desplazamiento sagital puro ($\Delta Y = 0.0373$, $\Delta Z = 0.0560$). En `skeleton.fbx`, $\Delta X = 0.000048$ y $\Delta Y = 0.0954$.
- [x] **Sincronización Offline:** `build_offline_renderer.py` integró la capa de paridad en `FBX-Web-Renderer-offline.html`.
- [x] **Verificación Automatizada Headless:** Test Playwright `tools/lab/test_neck_pitch_axis_and_input_headless.cjs` superado al 100% con 0 errores de consola, comprobación estricta de separación DOM, reactividad de entrada por teclado, cero roll lateral y cabeceo visual en spacemarine, skeleton y demo.
- **Evidencia Visual:** `walkthroughs/fix-neck-pitch-axis-and-input/walkthrough.md`.


---

## 2026-10-21 - Integración de Sprites Definitivos (Marine, Charger y Necrón) y Limpieza de Assets

### Objetivo y Resumen
Integración completa de los nuevos modelos y spritesheets en 8 direcciones provenientes del Shader Lab (`assets/inbox/`), sustitución y purga de personajes legacy (esqueletos), conversión a arrays BGR555 optimizados para NDS, y guardado de los archivos fuente de mapa `isometric_shooter_bl`.

### Componentes Actualizados
1. **Modelos 3D FBX Canónicos (`assets/models/characters/`):**
   - Incorporado `assets/models/characters/spacemarine/spacemarine_running.fbx` (Space Marine con arma).
   - Incorporado `assets/models/characters/necron/necron_running_rifle.fbx` (Tirador Necrón con rifle).
   - Mantenido `assets/models/characters/charger/Run.fbx` (Charger knocker).
   - Purgados modelos viejos de esqueleto (`skeleton.fbx`, `skeleton_death.fbx`).
2. **Spritesheets 2D 48×48 en 8 Direcciones (`assets/sprites/characters/`):**
   - `assets/sprites/characters/marine/`: Spritesheet, máscaras de sombra de 96×96 y cabeceras de anclaje.
   - `assets/sprites/characters/charger/`: Spritesheet, máscaras de sombra y anclajes.
   - `assets/sprites/characters/necron/`: Spritesheet, máscaras de sombra y anclajes.
3. **Conversión a Memoria NDS (`source/player_sprite.c`, `include/player_sprite.h`):**
   - Generados arrays BGR555 nativos para las 3 clases (`g_player_frames`, `g_charger_frames`, `g_necron_frames`).
   - Dimensiones de celda actualizadas a 48×48 manteniendo compatibilidad de anclaje y colisión.
   - Enumeración actualizada con alias retrocompatible `CHAR_NECRON = 2` y `CHAR_SKELETON = CHAR_NECRON`.
4. **Archivos Fuente del Mapa (`assets/sprites/dungeon/isometric_shooter_bl/`):**
   - Extraídos e incorporados los archivos `world.png`, `collision.png`, `occlusion.png`, `collision.json` y `map_settings.json` listos para el pipeline de horneado a tiles hardware.

### Verificación y Rendimiento
- **Tests Host:** 9 suites completas pasando (`DS_HOST_TESTS=PASS`, 35 tests OK).
- **Toolchain BlocksDS:** Compilación limpia sin advertencias (`DS_BUILD=PASS`, ROM `dungeonds.nds`).
- **Validación Headless DeSmuME:** `scenarios/weapons_switching_and_touch.json` verificado con captura del nuevo Marine en combate (`captures_headless/new_sprites_test`).


---

## 2026-10-21 - Horneado e Integración del Mapa Real `isometric_shooter_bl` en la ROM

### Resumen
Se ha completado el horneado integral del mapa `isometric_shooter_bl` desde sus fuentes PNG/JSON a los subsistemas de hardware de Nintendo DS:
- **Atlas de tiles y Tilemap:** Cuantización y empaquetado a 3.808 tiles 8bpp de hardware en `dungeon_bg_tiles.c` / `.h` con dimensiones de mundo `1536 × 864`.
- **Malla de colisión 2-bit:** `384 × 216` celdas a escala 4px (20.736 bytes empaquetados) en `diablo_dungeon.c` / `.h`.
- **Oclusión RLE:** 5.402 tramos calculados de muros y columnas en `dungeon_occlusion.c` / `.h`.
- **Punto de spawn:** Actualizado a `(754, 466)` en el centro del área transitable del blockout.
- **Validación:** 35/35 host tests pasando, build BlocksDS limpia (`dungeonds.nds`), y escenario DeSmuME verificado con el nuevo Marine en la nueva mazmorra a 60 FPS estables.

---

## 2026-10-21 - Corrección de Fondo en Pantalla Inferior y Purga de Código Legacy

### Resumen
Se solucionó el problema por el cual la pantalla táctil inferior se mostraba negra sobre el fondo de la mazmorra:
- **Causa raíz:** `smooth_lightmap.c` intentaba indexar una tabla de antorcha dimensionada para el mapa viejo de 768×512. Al exceder los límites, ejecutaba un volcado de negro opaco (`RGB15(0, 0, 0) | BIT(15)`) en la capa bitmap frontal (BG2), ocultando las baldosas del fondo hardware (BG1).
- **Corrección:** Se eliminó la llamada a `render_smooth_torch_lighting()` y se sustituyó por una inicialización transparente (`0x0000`, bit 15 desactivado) mediante BIOS `swiFastCopy` (`COPY_MODE_FILL`). Esto deja ver nítidamente las baldosas y muros de `isometric_shooter_bl` en ambas pantallas simultáneamente.
- **Purga de assets y código legacy:** Se eliminaron `source/smooth_lightmap.c` e `include/smooth_lightmap.h` (-2.011 líneas), reduciendo la ROM de 2,66 MB a 2,20 MB.
- **Validación:**
  - 35/35 host tests pasando (`DS_HOST_TESTS=PASS`).
  - Escenario DeSmuME `weapons_switching_and_touch.json` verificado: 673 colores únicos en la pantalla inferior (baldosas, paredes, sombras proyectadas y HUD a 60 FPS fijos).
  - ROM `dungeonds.nds` lista en la raíz para despliegue por FTP.

---

## Sesiones del 2026-11-02 al 2026-11-16 (movidas desde STATUS.md el 2026-11-19)

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

---

## 2026-11-14 - Sombras por Hardware y Horda Doble a 60 FPS

- Fase 1 de rendimiento (A–F) en `perf/hw-shadows`: sombras por hardware, IA más barata, blit por tramos, limpieza en ráfaga, ITCM y picos troceados. DeSmuME: 34,1 → ~15,5 ms en el banco A/B.
- DS física (`stress-perf`, 48 enemigos): 14,3–15,1 ms de media, peor frame 17–18,5 ms; versión normal jugada sin caídas.
- Arreglado el log de `PERF_PROFILE` (ruta `fat:/` explícita por NitroFS).
- Detalle: [`walkthroughs/hw-shadows/`](walkthroughs/hw-shadows/walkthrough.md).

## 2026-11-14 - Legibilidad C2, estatuas y flujo único de reconstrucción (`feat/legibilidad-lab`)

- **Legibilidad C2 en personajes y props:** tono neutro, curva S suave, enfoque suave, bordes al 30 % y redondeo BGR555 en `generate_player_sprites_c.py` y `prerender_props.py`, con paleta de props recalculada automáticamente (`extract_palette.py`: 144 tonos únicos, 156/256 compartidos). Comparativas A/B en [`walkthroughs/legibilidad-lab/`](walkthroughs/legibilidad-lab/walkthrough.md); decisión en `DESIGN.md` §6.9.1b.
- **Estatuas y velas:** integradas dos estatuas `santo` simétricas en los tramos abiertos/relicario (`strip_kit.h`, `strip.c`, `bake_cathedral_kit.py`: 896/1024 tiles, peor ventana 389/<440) y limpiados los trozos sueltos de alambre en `vela` con `prep_props.py`.
- **Flujo único en 1 comando:** creado el manifiesto `assets/sprites/characters/characters.json` y el orquestador `tools/rebuild_all.py` (conectado a `tools/rebuild-assets.ps1`) para re-renderizar, extraer paleta, hornear, pasar los 15 tests de contrato y compilar `dungeonds.nds` sin warnings. Validado en la Nintendo DS física por el usuario.

## 2026-11-14 - Ojo del Tribunal: mirada colimada y llamarada espectral (`feat/ojo-tribunal`)

- Se descarta el cono de suelo con cuenta compartida y se vuelve al ritmo del francotirador anterior: seguir (40 f), fijar con parpadeo (20 f) y disparar desde la boca. El disparo es una llamarada espectral en hielo de 31 f (golpe, llamarada y disipación) que daña durante 23 f.
- Sprites re-renderizados con C2 (entradas en `characters.json`), VFX desaturados, oclusión por profundidad con los personajes (pintado intercalado) y merge de `main` en la rama.
- 0 warnings, host 16/16, escenarios del Ojo 9/9. ROM `perf` jugada en la DS por el usuario y dada por buena; no se descargó el registro de rendimiento. Detalle y GIFs: [`walkthroughs/ojo-tribunal/`](walkthroughs/ojo-tribunal/walkthrough.md).

## 2026-11-14 - Exvoto en la catedral (`feat/exvoto`)
- **Hecho:** sustitución del esqueleto por el Exvoto (rezo frente a estatuas/velas/relicarios, despertar en cadena, transición `stand_up` y muerte derritiéndose en charco de cera irregular), más scripts de animación `tools/characters/build_exvoto.py`.
- **Verificado:** 0 warnings, `hostTests` + `test_strip.py` OK, escenario `exvoto_reza_despierta_derrite` PASS y probado en Nintendo DS física. Detalle: [`walkthroughs/exvoto-anim/`](walkthroughs/exvoto-anim/walkthrough.md).

## 2026-11-14 - Códice / Bestiario minimalista en 8 direcciones (`feat/bestiario`)
- **Hecho:** visor de 4 fichas (Corazón Abierto, Exvoto, Cireneo y Ojo del Tribunal con giro de linterna al 50 % de velocidad de paso, 16 frames/dir) en maquetación B minimalista (retratos 160×160 en 8 direcciones desde NitroFS arriba, ficha en español sin etiquetas de rol abajo, conectado al botón `CODICE` del menú inicial y de pausa). Corregidos los puntos blancos de borde en DS física (cuantización `1..255` sin colisión con índice 0 transparente y apagado de capas hardware durante el códice).
- **Verificado:** 0 warnings (`default` y `bestiary`), tests host 21/21, escenario `bestiary_tour` PASS y validado en Nintendo DS física. Detalle: [`walkthroughs/bestiario/`](walkthroughs/bestiario/walkthrough.md).

## 2026-11-15 - Exvotos rezan siempre de rodillas (`feat/exvoto-rodillas`, integrado en `main`)
- **Hecho:** `EXVOTO_KNEEL_PERCENT` pasa de 50 a 100: todos los Exvotos que nacen rezando delante de una pieza devota lo hacen de rodillas y se levantan (`stand_up`) al despertar; el resto de la masa sigue llegando andando. Decisión en `DESIGN.md` §6.10 («Postura»). El rezo de pie queda en la ROM sin uso en la horda.
- **Verificado:** compilación sin warnings; ROM subida a la DS para probar (sin medición de rendimiento: es una constante).

## 2026-11-16 - Biblia del lore y lote 01 de vídeos de redes (`docs/lore-biblia`)
- **Hecho:** `LORE.md`; 10 guiones con nombres cruzados y frase final con voz propia; generador `render_guiones.py` (voces de personaje, parejas, planos por frase, trayectos con zancada medida del exvoto); sprites `corazon_walk` y `exvoto_walk_b`; skill actualizada con lo aprendido publicando (sin negro al inicio, frase fuerte primero, subtítulos fuera de la zona de botones, puesta en escena por vídeo).
- **Verificado:** vídeos 01 y 03 publicados y medidos en TikTok e Instagram (01: de 3,8 s a 7,2 s de visionado medio al quitar el negro y adelantar la frase fuerte); guiones 02 y 04–10 generados sin voz sin errores. Detalle: [`walkthroughs/lore-lote-01/`](walkthroughs/lore-lote-01/walkthrough.md).

## 2026-11-16 - Vídeo de lore 08: La Catedral que no termina (`docs/lore-video-08`, integrado)

- **Hecho:** guion 08 reescrito contra `LORE.md` (la Marcha y la guerra contra el propio pueblo); estilo visual de los vídeos decidido (negro sin suelo, props a escala real, skill `codice-lore-video`); generador con props, plano continuo, altar, multitud, `alejar`, `(pausa N)` y estilo por vídeo; props re-renderizados para vídeo, animaciones de rezar de Elías y Abanderado solo; guiones y voces movidos a `assets/videos/`.
- **Verificado:** vídeo con voz de 67,9 s aprobado por el usuario tras tres rondas (A/B/C y dos de ajustes). Sin tests de juego: no toca la ROM. [`walkthrough`](walkthroughs/lore-video-08/walkthrough.md).

---

## Entregas recientes antiguas (movidas desde STATUS.md el 2026-11-19)

- **Sombras por hardware y horda doble (`perf/hw-shadows`, 2026-11-14, `walkthroughs/hw-shadows/`):** sombras oscurecidas por la consola (ventana OBJ) en vez del procesador, IA con rejilla y LOD, blit por tramos opacos, limpieza más rápida, camino caliente en ITCM y picos de rebase/láseres/muertes troceados. Medido en la DS con 48 enemigos: **14,3–15,1 ms** de media (antes 34–36 ms, 20 FPS), casi siempre a 60 FPS; la versión normal (24) va sobrada. La separación entre enemigos se conserva. Siguiente cuello: el blit (~6 ms con horda llena). Variantes `stress` y `stress-perf` y banco A/B `perf_stress_bench` (`TECHNICAL.md` §3.6).
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

---

## Movido desde TECHNICAL.md el 2026-11-19

Texto técnico histórico o de variantes retirado de `TECHNICAL.md`, sin reescribir (salvo el título de cada bloque). Las cifras de tiles y rutas de aquí son las de su época.

### Arenas: datos → lab → baker → runtime (v0.2, ROM descartada)
> **Solo variantes de pruebas (sandbox, bestiario).** La ROM por defecto no usa `arenas.json`; usa el kit de catedral de `strip.c`. Siguen en `hostTests`.

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

### Godrays (antiguo §3.5)
> **No están en la ROM por defecto** (solo se compilan con `GODRAYS_PROTO=1`); las anclas descritas abajo son las de la catedral infinita de 512 px y no se han adaptado a las salas de 256 px.
- **Estado:** integrados con la catedral v2 en su día (`walkthroughs/catedral-v2-salon/`, medidos en DS: peor frame al 72 % y 26 % de media); hoy solo viven en la variante de compilación `godrays` (`GODRAYS_PROTO=1`, `.ds-game-dev/project.json`).
- **Cómo:** `source/godrays.c` y `source/godrays_gfx.c` (cabeceras `include/godrays*.h`) dibujan rayos con OBJ semitransparentes anclados cada 256 px absolutos de la franja, alternando paredes, compensando los rebases con `strip_shift_total_px()`. Sprites en `assets/sprites/godrays/` y notas en `tools/godrays/README.md`.
- **Límites conocidos:** con la línea de marea visible se ocultan todos los rayos (la semitransparencia OBJ se vuelve opaca en la ventana de la marea); los rayos usan sprites placeholder y ámbar/vitral sin decisión de arte en `DESIGN.md`.
- **Desajuste de origen:** la variante de rosetón también se coloca en los anclajes periódicos de los muros laterales. El layout de catedral reserva el rosetón para el arco frontal del crucero; separar ese emisor es trabajo de la Sesión 3 (`DESIGN.md` §6.9.1b).
- **Prioridad en crucero:** la Sesión 3 debe suspender los haces laterales durante la pantalla del rosetón; `BLDALPHA` comparte la intensidad por pantalla y dos haces solapados no se suman (`walkthroughs/v032-escenario/BIBLIA.md` §7).
- **Pendiente:** certificar 60 FPS en la DS con `PERF_PROFILE` antes de activarlo en la build por defecto (regla 6) y escribir la decisión de arte (regla 9).
- **Incompatibles con las sombras hardware (§3.6):** ambos usan los bancos OBJ, así que con `GODRAYS_PROTO=1` se fuerza `HW_SHADOWS 0` (camino software).

### Horda y stress (antiguo §3.6, parte no vigente)
- **Variantes:** `stress` (`STRESS_TEST=1`: horda a 48, pool 64, enemigos de 1 PS, héroe invulnerable, L+R+A alterna sombras HW/SW) y `stress-perf` (además `PERF_PROFILE=1`). El log de `PERF_PROFILE` usa ruta explícita `fat:/` (o `sd:/`), porque NitroFS deja el directorio en `nitro:/`.
- **Banco A/B en DeSmuME:** `scenarios/perf_stress_bench.json` (+ `_sw_shadows`, `perf_stress_climb`) y `python tools/perf_bench_summary.py <salida> [<base>]`. Solo comparativo (regla 6).
- **Medido en la DS (`stress-perf`, horda llena ~48):** CPU 14,3–15,1 ms de media por ventana de 1 s y peor frame 17–18,5 ms; 0–5 frames perdidos por segundo en los peores tramos (parte, la escritura del log). Antes: 34–36 ms (20 FPS) con sombras y 17–21 ms sin ellas. Con el pool normal de 24, 8–12 ms. Lo que más pesa ahora es el blit (~6 ms con horda llena).

### Vídeos verticales (antiguo §3.7)
- **Carpeta de salida centralizada:** `assets/videos/` contiene los vídeos verticales en formato MP4 (1080×1920, 9:16) producidos para redes sociales (TikTok, Reels, Shorts). Cada archivo se nombra de forma canónica (p. ej. `codice_03_cireneo.mp4`, `codice_04_ojo.mp4`).
- **Pipeline:** skill `.agents/skills/codice-lore-video` basada en ElevenLabs CLI (`eleven_multilingual_v2`, voz Carmelo a bloques cortos con pausas de 0,5–0,85 s), FFmpeg y Pillow.
- **Automatización:** el script `render_codice_video.py` compila subtítulos Palatino Linotype en formato `.ass` (`MarginV = 240`) y copia automáticamente el archivo generado a `assets/videos/`.

### Bloque «Requisitos técnicos de la v0.3: horda y franja vertical» (antiguo §4.7)
### 4.7. Requisitos técnicos de la v0.3: horda y franja vertical (2026-11-06; histórico)
> **Histórico.** La ROM por defecto ya no tiene horda continua ni franja infinita (`DESIGN.md` §6.13.6); el criterio de 48 enemigos activos no se persigue. Se conserva por las mediciones de rendimiento y por si vuelve una horda en otra variante. Diseño original en `DESIGN-ARCHIVE.md`.

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
- **Bordes laterales duros:** el carril tiene 64 columnas de tiles; `source/strip.c` reserva seis tiles (48 px) a cada lado, los marca sólidos para cuerpos y proyectiles y limita las estampas a las 52 columnas centrales (416 px). La sesión 2 añade el arte de pared a esas columnas exteriores; la colisión de borde ya está resuelta.
- **Composición reproducible pendiente:** el runtime elige estampas por hash en bandas de 128 px y `main.c` arranca con una semilla de hora/timing; no hay secuencia determinista de familias lógicas de 192 px ni el runner de escenarios acepta una semilla de franja. Para validar en ROM el layout de `DESIGN.md` §6.9.1b, hará falta un fixture de composición fijo o el generador final con semilla reproducible; cambiar solo la semilla no garantiza las pantallas de la propuesta.
- **Mapa visual del primer pase de catedral:** BG1 usa un único tilemap opaco; el baker compone suelo, paños laterales, lancetas y un umbral con rosetón en una tabla de 64×128 tiles (1.024 px de ciclo arquitectónico). La alternancia de lancetas se repite cada 512 px; el umbral del crucero alarga el ciclo completo a 1.024 px. La tabla ocupa 16 KiB, +14 KiB frente al mapa de suelo de 64×16 tiles; `s_map` conserva sus 64×256 tiles (32 KiB). `StripKit`/`generate_band()` mantienen períodos independientes: `map_h_tiles=128` para arte y `floor_h_tiles=16` para colisión de 128 px. El kit usa 1.024 tiles en total y la ventana de 33×25 usa 224. Los paños actuales son pixel art de primer pase basado en la forma geminada; el modelo Blender está en `assets/models/environment/cathedral/lancet_pair.blend` y `lancet_pair.glb`, pendiente de ajustar al encuadre del lab antes de sustituir ese arte. Los muros son planos decorativos en los bordes ya sólidos; no añaden spans de oclusión ni colisión. La ROM/capturas de revisión están en `walkthroughs/muros-catedral/`.
- **Contrato de props de la franja: validado (2026-11-10).** Color, huella y profundidad comparten encuadre. La profundidad va en píxeles del sprite (§3.3), y con eso la peor ventana bajó de 14.838 a 4.117 runs de oclusión. El usuario lo probó en la DS y lo dio por bueno, sin desglosar prop por prop. En DeSmuME están cubiertos la columna y el banco roto, por los dos lados. Santo, relicario, vela y banco volcado no tienen escenario propio. Escenarios y capturas: `walkthroughs/props-depth-units/`.
- **Deuda del kit de catedral:** usa 1.024 de 1.024 tiles, así que no cabe ninguna pieza nueva. Las lápidas planas conservan su `depth.png` en unidades del render fuente; no lo usan, pero hay que regenerarlo antes de dar oclusión a una lápida.
- **Navegación:** `navfield` de 48×128 nodos de 16 px. En el rebase se desplaza el campo (`nav_shift_down`) en vez de rehacerlo.
- **Horda** (`source/horde.c`) sobre el pool de 24 (`MAX_GAMEPLAY_ENEMIES`), con reciclaje sin recompensa. La IA de siempre, con un flag de modo franja.
- **Marea** (`source/tide.c`): WIN0 con fundido a negro por hardware (`REG_BLDCNT` modo 3, `BLDY`), sin coste de CPU por píxel.
- **Medido en la DS:** CPU media de 219.000 ticks (39 %) y máxima de 489.882 (87 %). Picos de `en` 115.000 y `proj` 106.000. Sin frames perdidos salvo la escritura del log. Aún no aplica nada de los "cambios previstos" de arriba (pool de 48, IA por niveles de detalle, rejilla, 8 bpp).
- **Escenarios:** `strip_climb_smoke` y `strip_horde_tide` leen `g_strip_debug[4]` = {altura en px, rebase acumulado, enemigos vivos, vida}.

**Franja vertical (pendiente):**
- Los tramos hechos a mano de la 0.6 sustituirán a las bandas procedurales; la ventana con rebase se mantiene.
- El baker ya cumple el presupuesto de tiles por ventana (§3.3), que no depende del tamaño total. Los tramos repetidos comparten tiles. ROM orientativa: la mazmorra de 768×768 ocupa unos 83 KB; una franja de 384×6000 px debería quedarse en pocos cientos de KB.
- **Timestep (§4.5):** con horda, una caída a 30 FPS pone el juego a media velocidad. Conviene resolverlo antes del tuning.

### Viñetas «Resuelto» y notas retiradas de §3 y §4
- Resuelto (ver `STATUS.md`): la pantalla superior ya dibuja actores, sombras, proyectiles y FX con el mismo compositor que la inferior (`render_screen` se ejecuta una vez por pantalla, §3.3).
- Resuelto: actores detrás de una superficie oclusora quedan ocultos por profundidad, sin parpadeo temporal ni línea negra auxiliar; decisión en `DESIGN.md` §3.
- Resuelto (ver `STATUS.md`): movimiento/colisión isotrópicos en suelo (`GROUND_DY2`, elipse 6×3), ancla única exportada, oclusión exacta por consulta directa de tramos (sin mapa 4×4 ni reconstrucción por cámara).
- Resuelto (ver `STATUS.md`, v0.1): lead del tirador, i-frames, pickups, navegación BFS (`navfield.c`), mordisco a través de muros.
- Los escenarios atados al mapa viejo (`dungeon_walk_tour`, `fbx_bg_ring_scroll`, `integration_showcase_walk`, `wall_junction_closeup`, `map_occlusion_collision_coherence`) se eliminaron con él. `assets/sprites/dungeon/isometric_shooter_bl/` y `assets/models/environment/blockout/` quedan solo como referencia histórica; ningún build los usa.
- (§3.1, L58) El blit ampliado salta consultas de oclusión si no hay tramos en las filas; su coste por frame requiere medición en DS antes de integrar la rama.
- (§3.3, L81) Presupuesto de tiles de las arenas v0.2: el baker fusionaba con pérdida (umbral medio de color 1,0: 3804 → 1123 tiles, peor ventana 576 → 252). Con las sombras suaves y diagonales subió a 999 tiles únicos (peor ventana 237 de 440).
- (§4.4, L193 de §4.7) Cita retirada: `assets/models/environment/cathedral/lancet_pair.blend` ya no existe. (§Arenas) `labRender` en `tools/lab/map_settings.json` tampoco existe.

---

## Movido desde STATUS.md el 2026-11-19

Entregas del 2026-11-14 al 2026-11-18, notas de estado técnico y ramas aparcadas, con el texto íntegro de `STATUS.md` (varias tienen también su sección propia más arriba, escrita en su día; aquí va el resumen que había en `STATUS.md`).

### Entregas 2026-11-18 y anteriores (más nueva primero)

- **Coberturas bajas: el héroe se agacha tras bancos y sacos (`feat/coberturas-bajas`, 2026-11-18, integrado en `main`):** sin botón, se agacha solo al pegarse a un banco o unos sacos, anda agachado a la mitad de velocidad y se levanta al tocar el stylus para disparar; agachado, el haz del Ojo no le da si cruza la cobertura antes (cuerpo a cuerpo, cargas y marea le dan igual). Arte final del andar agachado: variante A2 (cadera 15 u más baja, torso inclinado; 20,8 px de alto frente a 32,3 de pie); el agachado quieto es el fotograma 4 de ese andar. Colisión nueva «cobertura baja» (valor 2: bloquea cuerpos, no balas) en bancos y rects de sacos. Build 0 avisos, tests y escenarios PASS (escenario `cobertura_baja_agachado`, variante `cathedral-sandbox`). No se midió de nuevo en DS: A2 no cambia el render ni el presupuesto y el agachado ya midió ~3 % del frame en la DS (60 FPS). Tiles del kit 948/1024; EWRAM 3,38 de 3,5 MiB. [`walkthrough`](walkthroughs/coberturas-bajas/walkthrough.md).
- **Encuentros tácticos, solo diseño (`docs/encuentros-tacticos`, 2026-11-18, integrado en `main`):** `DESIGN.md` §6.13.9 corrige §6.13.6 porque en las salas lo óptimo seguía siendo quedarse abajo esperando: Ojo con más alcance que el rayo y en su puesto arriba (en todas las salas del acto I menos el atrio), Exvotos que se reúnen y flanquean (rodean la cobertura), Cireneo guardián, cuatro reglas de sala y catálogo v3 de 7 plantas (`walkthroughs/encuentros-tacticos/catalogo-salas-v3.html`). **Sin código en la ROM:** siguen las salas v2. Siguiente: revisar el catálogo v3 contra las reglas y programar alcance del Ojo, flanqueo y Cireneo guardián.
- **Buffer de carga del láser y cancelación reactiva (`fix/laser-charge-buffer`, 2026-11-18, integrado en `main`):** resuelta la pérdida de pulsación tras disparar el francotirador; ahora al volver a pulsar la pantalla el arma arranca la carga del láser inmediatamente desde cero (progreso 0) sin esperar el enfriamiento post-disparo de 40 frames ni quedar atrapado en la recuperación. Al soltar el lápiz (`!touch_down`), se corta de inmediato el clip encorvado regresando al reposo/andar normal. Combinado con los sprites de escala unificada normalizados a 48 px de `main`. Build 0 avisos, escenarios headless PASS y validado en Nintendo DS física por el usuario. [`walkthrough`](walkthroughs/fix-laser-charge-buffer/walkthrough.md).
- **Remate: embestida previa, cámara pegada al héroe y sandbox que parece el juego (`feat/remate-tuning`, 2026-11-18, integrado en `main`):** al pulsar `L` el héroe corre hasta el punto de inicio del remate y la cámara sigue sus pies; el sandbox de remates (`REMATE_SANDBOX`) ya no muestra el HUD de depuración. Probado a mano por el usuario con buena pinta, **pero falta un testeo más a fondo** (balance de alcance, tambaleo, feedback y recarga siguen pendientes de tunear; sin pasada de escenarios ni medición `perf` en DS).
- **Ejecuciones (remates) del Exvoto y Cireneo (`feat/remate`, 2026-11-18, integrado en `main`):** implementada la mecánica de remate por botón `L` tras impacto no letal (estado `WOBBLE` de 60 frames con pulso de luz cálido, sin parpadeo neón). Héroe invulnerable durante la ejecución, muerte instantánea del enemigo y rayo recargado inmediatamente al terminar. Animaciones Sonnet opción A integradas para ambos: Exvoto (agarre y partición vertical en 64×64 con mitades de cera en el suelo) y Cireneo (arrancado de cruz y empalamiento en el suelo en 80×80). Optimización de EWRAM (máscaras de sombra compartidas cada 2 fotogramas y fotogramas finales de reposo reutilizados) para encajar en el límite estricto de 3,5 MB de la DS. Build 0 avisos, subida por FTP y validada en hardware por el usuario. **Pendiente: tunear la mecánica en sí** (alcance de activación, duración de tambaleo, feedback táctil y balance de recarga instantánea). [`walkthrough`](walkthroughs/remate-exvoto/walkthrough.md).
- **Piezas 3D de las salas, rastrillo OBJ y lápidas (`feat/props-catedral-v2`, 2026-11-17, integrado en `main`):** sustituidos los provisionales del Acto I por piezas 3D (sacos con remate, alambre 32×24 con colisión exacta de 128 px, columna rota, banco roto 1 de cada 4 grupos, relicario nuevo, estatuas orientadas al centro `santo`/`santo_der`). Rastrillo delantero y trasero dibujados con sprites hardware (OBJ, 128 tiles reservados): al limpiar sube despacio (~0,9 s) recortado por arriba y abre paso; al entrar baja la reja trasera ocluyendo al héroe dentro. Recuperadas las 4 variantes de lápidas en el kit (**948 / 1024 tiles**, peor ventana 279/<440) y simetría izquierda/derecha por cuerpo. Build 0 avisos, tests y escenarios `props_*` PASS; validado en DS física. [`walkthrough`](walkthroughs/props-catedral-v2/walkthrough.md).
- **Catálogo y versionado de assets (`docs/assets-manifiesto`, 2026-11-17, `walkthroughs/assets-manifiesto/`):** los originales 3D, sus texturas y los vídeos van por **Git LFS** (`.gitattributes`). `assets/MANIFEST.md` es el catálogo de todos los assets, con su fuente, su script y su almacén. La política de entrada, adopción, retirada y limpieza está en `AGENTS.md`, «Ciclo de vida de los assets». Personajes y animaciones van separados (`characters/<p>/source/` frente a `animations/`). Todos los sprites de personajes se han regenerado a **escala fija por personaje**: con `scaleRef`, las animaciones heredan del andar el reescalado del modelo y la escala de cámara, así que el personaje mide lo mismo en todas sus animaciones. El disparo del héroe usa un recuadro propio de 48 px para que quepa la cruz sin encogerlo. El monaguillo ya se regenera desde archivos versionados. La tabla sprite → modelo → animación → script y los pasos para regenerar están en `MANIFEST.md` §2. Probado en la DS por el usuario: va bien. Se borraron el legado y los modelos sin uso. Pendiente: reescribir el historial de git para quitar el legado (ensayada: de 922 a ~574 MB; con copia previa), decidir los `.h` del bestiario y borrar la prueba de DVC en Google Drive.
- **Modo jefe integrado en la ROM principal (`feat/integrar-jefe`, 2026-11-17, integrado en `main`):** `dungeonds.nds` arranca ya por defecto con el escenario por encuentros, la nueva IA de enemigos y el modo jefe (`boss.c`, `DESIGN.md` §6.13.7: intro con zoom y voz, barra de vida en pantalla inferior, fases con invulnerabilidad, escolta y victoria con reliquia). Partida estructurada en 14 stages (Vía Crucis): **primer jefe (El Abanderado) en el stage 5**, y **jefe repetido (El Abanderado) en los stages 10 y 14** hasta añadir los otros dos jefes. Build 0 avisos, tests de host y escenario `integracion_jefe_stage5` PASS. [`walkthrough`](walkthroughs/integrar-jefe/walkthrough.md).
- **Acto I por encuentros, prototipo v2 (`feat/encuentros-acto1`, 2026-11-17, integrado como versión de prueba):** variante de build `encuentros` (la ROM normal no cambia de comportamiento). Catedral de 256 de ancho, 6 salas hechas a mano con 3 poblaciones cada una (ligera, media y dura por tercios), pasillo con relicario lateral (Don o corazón), barrera que se abre al limpiar y el Abanderado con escolta al final. Todos los enemigos están en la sala desde el principio y despiertan a la vez; el Exvoto esquiva el rayo, el Cireneo persigue y embiste (aturdido al chocar), el rayo sigue solo con el daño sobrante. Diseño en `DESIGN.md` §6.13.6; catálogo de salas en `walkthroughs/encuentros-acto1/catalogo-salas.html` (generado por `tools/encuentros/catalogo_v2.py`, que también genera los datos). Bot de pruebas dentro de la ROM (variante `encuentros-bot`). Build 0 avisos, tests de host del kit, strip, navegación y normas PASS. Jugado en la DS por el usuario; **sin registro de rendimiento**. [`walkthrough`](walkthroughs/encuentros-acto1/walkthrough.md).
  - **Problemas abiertos (prueba del usuario en la DS, 2026-11-17):**
    - ~~Sale una oferta de mejora nada más arrancar, sin causa conocida.~~ *(Resuelto 2026-11-17: desactivada la tecla de depuración `X` en encuentros y limpiados los flags de depuración al reiniciar).*
    - ~~Muchas salas no son simétricas y quedan feas: las columnas y las estatuas deberían ir en pares simétricos.~~ *(Resuelto 2026-11-17: fase espejo de `santo` horneada en el kit y ajuste por pares simétricos en el catálogo).*
    - ~~No hay lápidas en las salas.~~ *(Resuelto 2026-11-17: 1–2 lápidas aleatorias por sala respetando el damero y sin solapar piezas).*
    - Los muros del ancho 256 pueden ser más finos.
    - ~~La IA del Exvoto se siente lista pero hace alguna cosa rara; falta explicar con claridad qué hace (esquiva de la línea de apuntado y zigzag al andar) y revisarla.~~ *(Explicada y corregida 2026-11-17: cancela la esquiva al soltar el apuntado en vez de congelarse y atenúa el zigzag de 96 a 32 px).*
    - ~~En muchas salas la estrategia óptima es quedarse quieto o recular y matar lo que viene: estudiarlo.~~ *(Resuelto 2026-11-17: al entrar 36 px en la sala se cierra también la barrera trasera hasta limpiarla, y los enemigos siguen siendo intocables desde el pasillo).*
    - Una partida completa se queda corta: solo hay un acto y un jefe *(stages 10 y 14 cubiertos con El Abanderado repetido; faltan los otros 2 jefes).*
  - **Para siguientes sesiones:**
    - Consolidar la lista de assets que faltan para hacerlos en 3D (sacos, alambre de espino, barrera o verja, muro fino de 256, relicario dorado y lo que salga del inventario).
    - Los otros dos jefes (Campanero y El Paso) y los actos II y III.
    - El escenario cambia tras cada jefe (cada acto más profanado: bancos rotos, sacos, etc.); sin implementar.
    - ~~Medir rendimiento en la DS con `PERF_PROFILE`~~ *(Medido por el usuario en DS: va bien, no hace falta medir más).*
    - Retirar los ganchos de prueba cuando la variante pase a ser el juego (`g_enc_debug`, bot).

- **Estructura de la partida, la Subida (`docs/estructura-partida`, 2026-11-16, integrado):** decidida en `DESIGN.md` §6.13, sin código. Partida de 15–18 min como un Vía Crucis de 14 estaciones en tres actos, con jefes en las estaciones V (Abanderado), X (Campanero) y XIV (El Paso) que luego vuelven como élites; encuentros en el pasillo con intro y pantalla bloqueada; al ganar se sigue en las criptas; reliquias en el nivel 5 y al vencer a cada jefe. Sustituye a la catedral infinita y concreta la 0.6. Siguiente: escenario por actos, Campanero y escoltas. [`walkthrough`](walkthroughs/estructura-partida/walkthrough.md).
- **Lore y vídeos de redes (`docs/lore-biblia`, 2026-11-16, integrado):** `LORE.md` es la biblia del mundo (eje LGBT y anticlerical, cronología llana, lo abierto en §9) y toda la escritura de lore va contra ella. Los vídeos se generan por lotes con `render_guiones.py` desde `assets/videos/guiones/lote-01.md`: un plano por frase con puesta en escena, voces de personaje y paso natural. Publicados el 01 y el 03; después el 08 (La Catedral que no termina, escenografía de props a escala, `walkthroughs/lore-video-08/`). El 02 (Remedios) es el primero con cierre de pregunta moral para pedir comentarios (`> Pregunta:` en el guion) y está listo para publicar (`walkthroughs/lore-video-02/`); las cifras de comentarios se apuntan en «Publicado» de `lote-01.md`. El calendario de los próximos días está al final de `lote-01.md`; los guiones que no están cerrados son preliminares y se reescriben el día que tocan, y el guion contiene todo lo necesario para rehacer el vídeo. Reglas de retención y voces en la skill `codice-lore-video`. TikTok se sube a mano, no por Metricool. [`walkthrough`](walkthroughs/lore-lote-01/walkthrough.md).
- **Sistema de mejoras v0.4, primera versión (`docs/mejoras-diseno`, 2026-11-16, SIN fusionar):** gemas y experiencia, subida de nivel con 3 cartas en paralelo estilo Códice (arte capturado de la ROM), 7 Dones y 10 Reliquias, rayo que se para en el primer superviviente, estado Quemado con tinte por capas, requisitos de oferta y ronda A/B/C de efectos (elecciones en `DESIGN.md` §6.12.11-13). Diseño en §6.12. Compila sin avisos, normas de color OK, jugado en DeSmuME y subido a la DS (variante `perf`). **Pendiente:** validar si es divertido con el plan de pruebas (`walkthroughs/mejoras-v04/plan_pruebas.md`) y seguir la entrevista de ajustes; arreglar los problemas básicos que el usuario va detectando; sonidos (§6.12.14); medir rendimiento en la DS; limpiar variantes y ganchos de prueba (tecla `X`, `g_abc_debug`, `g_upg_debug`). Fusionado en `main` el 2026-11-16 a petición del usuario como versión de prueba. Cierre: build 0 avisos (default, perf, sandbox), host 17/18 (el que falla, `test_bestiary_assets_contract`, ya fallaba en `main` por un archivo de otra sesión), `upgrade_requisitos` PASS; en el tag `ojo-tribunal`, `enemy_ojo_esquiva_saliendo_de_la_linea` pasa a fallar por 0,5 px (un frame de desfase; el héroe esquiva igual), y otros 5 escenarios ya fallaban en `main`. [`walkthrough`](walkthroughs/mejoras-v04/walkthrough.md).
- **Vídeo de Lore: El Abanderado (`feat/video-lore-abanderado`, 2026-11-15):** generado el vídeo vertical 9:16 (1080×1920, 01:22) para redes sociales con la skill estandarizada `codice-lore-video`. Locución con Carmelo (ElevenLabs CLI frase a frase con pausas dramáticas y redacción aspiracional/mitológica sobre el pacto y dogma de la no retirada), sprite animado caminando en diagonal izquierda (1_SW) revelando en perspectiva el cortejo de los dos monaguillos de cera marchando tras él, ficha auténtica de Nintendo DS y cierre en mosaico 2×2 `PRÓXIMAMENTE en tu Nintendo DS`. [`walkthrough`](walkthroughs/codice-abanderado/walkthrough.md).
- **Vídeo de Lore: El Ojo del Tribunal (`feat/video-lore-ojo`, 2026-11-14):** generado el vídeo vertical 9:16 (1080×1920, 01:10) para redes sociales con la skill estandarizada `codice-lore-video`. Locución con Carmelo (ElevenLabs CLI frase a frase con pausas dramáticas y regla reforzada en la skill de redacción aspiracional/mitológica sin descripciones visuales obvias), sprite animado con barrido de linterna sobre fondo negro, ficha auténtica de Nintendo DS limpia y cierre en mosaico 2×2 `PRÓXIMAMENTE en tu Nintendo DS`. [`walkthrough`](walkthroughs/codice-ojo/walkthrough.md).
- **Tarjetas de introducción (`feat/intro-tarjetas`, 2026-11-15, integrado en `main`):** `NUEVA PARTIDA` abre 4 tarjetas (catedral, moverse y apuntar, marea, vida) con bucles de vídeo sin pérdida de la pantalla inferior real arriba (828 KB en NitroFS, ROM 6,03 MB) y `Saltar`/`START` para empezar al instante; navegación con lápiz, cruceta, `A`/`B` y `L`/`R`. Build 0 warnings, host 21/21, escenario PASS y validado en DS física, sin registro de rendimiento. [`walkthrough`](walkthroughs/intro-tarjetas/walkthrough.md).
- **Ficha de El Abanderado en el Códice (`feat/abanderado-codice`, 2026-11-14):** añadida la 5ª ficha al Códice (El Abanderado, jefe invocador) con retrato 160×160 en 8 direcciones bajo demanda desde NitroFS (`nitrofiles/bestiary/abanderado.bin`, 434 KB) con preset de legibilidad C2 y rotación con cruceta, texto inferior maquetado en español (126 px de alto), paginación 1/5 a 5/5 y fallback 2× nearest en caso de ausencia de NitroFS. Compilación limpia (0 warnings) en `default` y `bestiary`, tests de host 22/22 PASS y escenario headless `bestiary_tour.json` PASS. [`walkthrough`](walkthroughs/abanderado-codice/walkthrough.md).
- **Códice / Bestiario (`feat/bestiario`, 2026-11-14, integrado en `main`):** visor de 4 fichas (Corazón Abierto, Exvoto, Cireneo, Ojo del Tribunal con barrido de linterna a mitad de velocidad del paso) en maquetación B minimalista (fondo negro, borde gris 1 px, retratos 160×160 en 8 direcciones bajo demanda desde NitroFS arriba, ficha en español sin etiquetas de rol abajo con fuente bitmap propia de ~2,4 KB). Conectado al botón `CODICE` del menú inicial/pausa, además de `L + R + SELECT` y variante `bestiary`. Resuelto el punteado blanco de bordes en hardware (mapeo directo `1..255` en cuantización de paleta y limpieza de capas hardware en transición). Build limpia (0 warnings), host 22/22, escenarios PASS y validado en Nintendo DS física. [`walkthrough`](walkthroughs/bestiario/walkthrough.md).
- **Vídeo de Lore de El Cireneo (2026-11-14):** vídeo vertical 9:16 (1080×1920, 64,2 s) de lore de El Cireneo (`CÓDICE · III`) generado con la skill `codice-lore-video`. Locución con Carmelo (`eleven_multilingual_v2`), pausas dramáticas de silencio, música atenuada (`cathedral_battle_loop.wav`), animación de paso en escorzo diagonal Sureste (`7_SE`, 160×160 px), ficha dual de Nintendo DS limpia y cierre estándar de Códice con mosaico animado 2×2. [`walkthrough`](walkthroughs/codice-cireneo/walkthrough.md).
- **Limpieza de tests (`docs/tests-limpieza`, 2026-11-14, integrado):** nuevas reglas de cierre en `AGENTS.md` (reglas 4 y 4b): escenarios de la feature siempre, tests de host solo si el cambio toca su área, batería completa solo en hitos; prohibidos los contratos de texto. 22 tests borrados, normas globales en `tests/test_guardrails.py`, 21 escenarios fuera de la batería. [`walkthrough`](walkthroughs/tests-limpieza/walkthrough.md).
- **El Abanderado, jefe versión mínima (`feat/abanderado-jefe`, 2026-11-14, integrado):** arte C2 del Abanderado (`60×60`, andar + apuntar) y Exvoto monaguillo (`40×40`), aparición cada 2:00 tras morir el anterior, patrulla en la banda visible de la cámara, charco color crema a medio camino cada ~3 s con 2 monaguillos emergentes invulnerables (~0,5 s, tope 8), barra de vida flotante y Sagrado Corazón al morir. Compilación limpia (0 warnings), tests de contrato OK, escenario `abanderado_jefe_ciclo.json` PASS en DeSmuME y validado en DS física. [`walkthrough`](walkthroughs/abanderado-jefe/walkthrough.md).
- **Demo para un colega (`feat/demo-colega`, 2026-11-14, `walkthroughs/demo-colega/`):** HUD de vida con 5 Sagrados Corazones (`14×18` px, pre-renderizados en el lab con `--legibility c2`) en la pantalla inferior, láser como arma única en la ROM principal (`L` desactivado; `SELECT` e `Y` activos para comparar VFX). Compilación sin warnings (`default` y `playground`), tests de host y escenarios headless PASS; validado en DS física.
- **Menú inicial y menú de pausa (`feat/menu-inicial`, 2026-11-14, integrado):** pantalla inicial (`NUEVA PARTIDA`, `BESTIARIO`, `CONTROLES`) y pausa con `START` (`CONTINUAR`, `REINICIAR`, `BESTIARIO`, `CONTROLES`) con catedral de fondo arriba y catedral oscurecida + cajas semitransparentes abajo (`DESIGN.md` §6.3). Navegación por lápiz y cruceta+A/B; congela simulación y pausa BGM (`sfx_set_bgm_paused`). Compilación 0 warnings, host 17/17, escenario `menu_inicial_pausa` PASS; jugado en DS por el usuario (variante `perf`), sin registro de rendimiento descargado. [`walkthrough`](walkthroughs/menu-inicial/walkthrough.md).
- **Ojo del Tribunal (`feat/ojo-tribunal`, 2026-11-14, integrado):** cuerpo bajo y gordo al 140 % en C2, cabeza abierta en la mano. Mecánica «Mirada colimada» (DESIGN §6.10): sin efectos al buscar; mirada verde desde el farol que sigue y se estrecha (40 f), se fija y parpadea (20 f) y la boca suelta una llamarada espectral en hielo (31 f, daña 23 f). Verde = te apuntan, hielo = te disparan. Oclusión real con personajes por profundidad. Regla de VFX desaturados reforzada en `AGENTS.md`. Host 16/16, escenarios del Ojo 9/9; jugado en DS por el usuario, **sin registro de rendimiento descargado**. [`walkthrough`](walkthroughs/ojo-tribunal/walkthrough.md).
- **Cámara con adelanto vertical (`feat/camera-lookahead`, 2026-11-14, `walkthroughs/camera-lookahead/`):** encuadre *look-ahead* en la pantalla inferior (`CAM_ANCHOR_UP = 132` al subir, `CAM_ANCHOR_DOWN = 64` al bajar, retardo de 22 frames y *freeze* al parar o *kitear* apuntando hacia delante). Compilación sin warnings, contratos host OK (14/14) y validada en la DS física.

### Entrada suelta (2026-11-17)

## 2026-11-17 - Vídeo de lore 02: Remedios, la cerera (`docs/lore-video-02`)

- **Hecho:** guion 02 reescrito con cierre de pregunta moral («¿Remedios robó a Dios… o hizo lo que Dios no hacía?»), dicha por el narrador, escrita arriba hasta el final y seguida de «Deja tu veredicto en los comentarios»; generador con `> Pregunta:`; animaciones `exvoto_rezar` y `exvoto_levantarse`; textos de los posts en `lote-01.md`.
- **Verificado:** prueba sin voz revisada plano a plano y render con voz de 75,2 s sin errores. Sin tests de juego: no toca la ROM. [`walkthrough`](walkthroughs/lore-video-02/walkthrough.md).

### Notas de estado técnico (a 2026-11-19; el punto 69, «Sin existir en código: iluminación dinámica, niebla de guerra», se borró por no aportar)

- **Arenas:** datos en `assets/arenas/arenas.json`; generador de modelos, export con el lab y baker (`tools/make_arena_glb.py`, `tools/export_arenas.py`, `tools/bake_arena.py`) descritos en `TECHNICAL.md` §3. El mapa grande `isometric_shooter_bl` ya no se usa.
- **Render:** actores dibujados directamente en la página trasera del framebuffer de VRAM, limpieza por spans sucios y oclusión exacta al píxel por consulta de tramos (`TECHNICAL.md` §3.3). Medido en DS: CPU 1,58 ms de media y 12 de 2520 frames con más de un vblank.
- **Personajes:** héroe (`CHAR_HERO`: Corazón Abierto; el space marine queda sin uso), charger (`CHAR_CHARGER`: Cireneo v2 a 60×60 con clips de carga agachado y telegrafía), necron (`CHAR_NECRON`) y esqueleto (`CHAR_SKELETON`), exportados por el lab a `assets/sprites/characters/<nombre>/`. El lab puede tomar el `muzzle` de un hueso (`--muzzleBone`).
- **Herramientas de diagnóstico en DS:** `PERF_PROFILE` (`include/perfprof.h`, log `fat:/dungeonds_perf.log`) y `crashlog` (`CRASHLOG_ENABLED`, logs `/dungeonds_crash.log` y `/dungeonds_live.log`). Ambas apagadas por defecto; se leen con `fetch-device-log.ps1` de la skill.

### Rama aparcada `feat/v03-mazmorra` (texto íntegro)

- **`feat/v03-mazmorra`** (commit `1e4973d`; la rama local se borró en la limpieza del 2026-11-19 y solo queda `origin/feat/v03-mazmorra`). Trabajo de la sesión del 2026-11-04/05 (mazmorra de 1280×1280 y luz oscura), guardado como WIP. Nunca se probó en la DS ni se revisó, y la dirección cambió a la v0.3 survivors. **No es una base: como mucho, una cantera.**
  - **Quizá útil en el paso 3 (franja vertical):** `navfield` a 80×80 con distancias `uint16`, sin `/` ni `%` por nodo y con límite de profundidad (`NAV_MAX_DEPTH`); `BG_MAX_TILES` 4096; `solve_frame` analítico y `normalize_blocks` (bloques sin costuras) en `tools/make_arena_glb.py`; `export_arenas.py`, que aclara los píxeles negros del suelo para que el baker no los tome por vacío; y `tools/gen_dungeon_layout.py` como idea para el generador de tramos (está pensado para salas, no para tramos). Hay que revisar y medir todo antes de traerlo.
  - **No rescatar:** el mapa de 1280 y sus manadas; los sprites re-renderizados, cuya luz no se aprobó (el brillo de contorno parecía escarcha); y su `DESIGN.md` §6, que contradice el vigente. El lab y la luz se están rehaciendo en otro worktree, así que no se toman de aquí.
  - **Caducidad:** borrar la rama remota (con permiso del usuario) en cuanto el paso 3 rehaga esas piezas por otro lado o, en todo caso, si el **2026-12-06** no se ha usado nada de ella.

### Entregas 2026-11-19 y 2026-11-20 (movidas de `STATUS.md` el 2026-11-22)

- **Vídeo de lore 07 Lope y feedback consolidado (`feat/video-lope` + `docs/feedback-lope`, 2026-11-19/20, integrado en `main`):** vídeo `assets/videos/lore01_07_lope.mp4` (88,3 s, con voz, sin publicar) con la animación nueva `abanderado_derrota` (Mixamo «Plant A Plant» espejado: el asta cae, Íñigo golpea el suelo y la recoge), el Ojo como el Tribunal y la Columna de monaguillos solo en su plano; fichas nuevas `medio` y capitán en `multitud` y velocidad de voz por personaje en `render_guiones.py`. El feedback del usuario (narrativa clara, sin cortejo por defecto, props con alfa, ritmo lento, citas lentas, no recortar) está en las reglas 7-9 de la skill `codice-lore-video`; textos de los posts en `lote-01.md`. [`walkthrough`](walkthroughs/lore-lote-01/walkthrough.md).
- **Purga de código y términos obsoletos (`fix/purga-obsoletos`, 2026-11-19, integrado en `main`):** eliminados del runtime, tests y escenarios la marea (`tide.*`, `test_tide_contract.py` y el split VCOUNT en `hwshadow.c`), las gemas de experiencia (`gems.*`), la escopeta, la granada (`grenade.*`) y el selector de armas (`TEST_WEAPON_CYCLE`), dejando el rayo del Corazón Abierto como única arma y conservando las curas en el suelo (`pickups.*`, corazones). Retirados los escenarios obsoletos de escopeta/granada/marea/marine/necron y limpiados `test_guardrails.py` y `tools/props/contact_sheet.py`. Anotado en `DESIGN-ARCHIVE.md` el commit **`7aa3b5f`** para rescatar granada o selector de armas en el futuro. Builds (`default`, `perf`, `cathedral-sandbox`, `godrays`, `stress`) con 0 avisos; tests de host PASS (salvo los 2 previos de `main`: `test_bestiary_assets_contract` y `test_character_muzzle`). [`walkthrough`](walkthroughs/purga-obsoletos/walkthrough.md).
- **Relicarios en pasillos, relicario dorado en jefes y Altar final (`feat/relicarios-boss`, 2026-11-19, integrado en `main`):** 15 stages (jefes en 5, 10 y 15 con El Abanderado), 14 pasillos con relicario normal (Dones), relicario dorado en la sala de cada jefe al vencerlo (Reliquias; retirado `ENC_GOLDEN_AFTER`) y Altar en el pasillo tras el stage 15 («Fin de la demo»). Variantes visuales provisionales para el relicario dorado y el Altar en `include/enc_relic_gfx.h`. Build 0 avisos; `test_guardrails` PASS. [`walkthrough`](walkthroughs/relicarios-boss/walkthrough.md).
- **Limpieza de documentación (`docs/limpieza-docs`, 2026-11-19):** `DESIGN.md` refleja el juego actual (relicarios: 13 pasillos, 12 Dones y 1 Reliquia dorada; Cireneo 4 y Abanderado ~37 disparos; sin marea, horda, gemas ni XP), `STATUS.md` y `TECHNICAL.md` recortados con lo histórico en `STATUS-ARCHIVE.md`, `LORE.md` sin la Marea y regla nueva en `AGENTS.md`: al cerrar cada sesión se revisan los MDs. Borrados legacy (sprites `marine`/`necron`/`charger`, briefs de encuentros, `scenarios_legacy`, test de golpes con armas antiguas). Solo docs; sin build. [`walkthrough`](walkthroughs/limpieza-docs/walkthrough.md).
- **Intro: seis tarjetas con clips grabados en escenas montadas (`feat/intro-tarjetas`, 2026-11-19, integrado en `main`):** la intro tras NUEVA PARTIDA enseña La catedral, Moverse y apuntar, Coberturas, Rematar, Relicarios y Vida, con textos que aclaran las invulnerabilidades del remate y del golpe. Los clips se graban en escenas exactas del sandbox (`tools/clip_scene.py`) y de la ROM `encuentros` (relicario), con fundido de 3 imágenes al cerrar el bucle. Las ROM de captura sandbox ya no llevan «Nv.» ni barra; el Makefile ya no activa `ENCOUNTERS_PROTO` en ellas. Los relicarios ya no curan. **Pendiente:** ver «Fallos y deuda conocidos». [`walkthrough`](walkthroughs/intro-tarjetas/walkthrough.md).
- **Ojo táctico, guarnición y Ojo en todas las salas (`feat/ojo-alcance`, 2026-11-19, integrado en `main`):** primera vuelta del método sala a sala (`DESIGN.md` §6.13.10), jugada en la DS con el usuario. **Cambia:** el Ojo no tiene alcance (solo le corta la vista una columna o estatua); un Ojo en todas las salas del acto I (7 Ojos nuevos en ligeras y medias); guarnición arriba (Exvotos y Cireneos que esperan junto al Ojo y se sueltan al acercarte, al dañarlos o al morir su Ojo); el Ojo es un tirador táctico en las salas de encuentros: cubierto tras banco o saco espera sin disparar y, al salir, arranca el ciclo normal de apuntado; tras columnas y estatuas te sigue y se recoloca (correa que crece hasta toda la sala). **No cambia:** las salas siguen siendo las plantas v2 (el catálogo v3 es solo diseño); el flanqueo coordinado de los Exvotos no está programado; el Ojo anda a un tercio de tu velocidad y mantiene la línea solo ~57 % del tiempo con el héroe moviéndose (palancas pendientes: velocidad de persecución y tiempo parado al apuntar); el comportamiento de la horda no se toca. **Sin hacer:** medición `perf` en la DS (rayo largo y búsqueda cada 8 frames por Ojo; el usuario no notó tirones); la última versión, con ciclo completo al salir de cobertura, no se jugó en la DS. Build 0 avisos; escenarios del Ojo y de cobertura baja PASS tras actualizar dos a propósito (`enemy_ojo_andar_mirar_sentenciar`, `cobertura_baja_agachado`); `test_guardrails` PASS. **Deuda heredada:** los 4 escenarios `enemy_ojo_*` que fallan, en «Fallos y deuda conocidos». [`walkthrough`](walkthroughs/ojo-tactico/walkthrough.md), registro en [`plan_pruebas.md`](walkthroughs/sala-atrio/plan_pruebas.md).
- **Tipografía: Palatino nítida en todo el texto del juego (`feat/tipografia`, 2026-11-19, integrado en `main`):** la poca legibilidad venía de dibujar Georgia suave y recortarla a blanco y negro; ahora se usa el trazado nítido de la fuente. Palatino 11 sustituye a Georgia en el Códice y a la fuente 5×7 en mayúsculas del menú, la pausa, los controles y el HUD de partida (con tildes y minúsculas); los nombres de pedestales llevan tilde y la fila VIDA/VELOC./AMENAZA cabe con marcas más juntas. El contador de FPS queda fuera. Además la ROM jugable vuelve a abrir en el menú de título (el salto venía de la variante de encuentros; ahora solo `SKIP_TITLE` en variantes de pruebas). Decisión en `DESIGN.md` §6.11.2. Build 0 avisos; subida a la DS; sin medir rendimiento por decisión del usuario. [`walkthrough`](walkthroughs/tipografia/walkthrough.md).
- **Códice con datos de juego (`docs/codice-datos`, 2026-11-19, integrado en `main`):** las fichas de Exvoto, Cireneo, Ojo y Abanderado enseñan `VIDA`, `VELOC.` y `AMENAZA` (1-5, el Exvoto es el mínimo de las tres), `HACE` y `TRUCO`. Decisión en `DESIGN.md` §6.11.1; textos acortados para caber. Pendiente: ficha del Monaguillo cuando exista su lore. [Walkthrough](walkthroughs/codice-datos/walkthrough.md).

### Entregas movidas de `STATUS.md` el 2026-11-23

- **Ejecución del Ojo del Tribunal, re-render con el lab rápido e integración en la ROM (`feat/remate-ojo`, 2026-11-21):** el gesto aprobado (el héroe le arranca el farol del hombro, lo tira y lo patea; el cuerpo descabezado se incorpora a su postura encorvada y cae de espaldas, soltando la cabeza que lleva en la mano) se ha **vuelto a renderizar con el lab rápido** (nuevo `tools/lab/fast/export_scene_fast.cjs`, secuencias GLB de escena, 8 direcciones × 39 fotogramas en ≈15 s) y **está en la ROM**: nuevo `REMATE_KIND_OJO` (celda 96×96, 38 fotogramas, 4 ticks = ~2,5 s, restos = el cadáver). Mismas reglas que el resto: el Ojo tambalea al 50 % de vida, `L` a ≤96 px, invulnerable durante la ejecución, muerte limpia, rayo recargado y restos. Los bins se leen de NitroFS **fotograma a fotograma** (buffers de 23,5 KB; EWRAM 3,32/3,5 MiB, heap 181 KB — el bin entero habría roto la intro). Escenarios de transición del remate PASS. [`walkthrough`](walkthroughs/remate-ojo/walkthrough.md).
- **Huella exacta de las barricadas de sacos (`fix/sacos-hitbox`, 2026-11-21):** la colisión de los sacos es ahora la franja de apoyo de 4 px del arte 3D, no el rectángulo del placeholder: el héroe se pega a la base por delante y por detrás. [`walkthrough`](walkthroughs/sacos-hitbox/walkthrough.md).
- **Vídeo de lore 04 El Liebre (`feat/video-liebre`, 2026-11-20):** `assets/videos/lore01_04_el_liebre.mp4` (74,1 s, con voz, sin publicar; textos de los posts en `lote-01.md`). Tras 9 pruebas con poses a medida que salían mal, se rehízo con 6 animaciones ya probadas, Inés, Bartolomé ya en la cruz y el martillo de Tadeo sobre negro. Nueva regla de producción simple (máximo unas 5 animaciones, como mucho 1 nueva y de Mixamo tal cual, sin poses montadas a mano) en la regla 10 de la skill `codice-lore-video`; fichas `negro` y `sfx … fin` en el generador; `--dirs` en el exportador del lab. [`walkthrough`](walkthroughs/lore-lote-01/walkthrough.md).

### Entregas ARPG (movidas de `STATUS-ARPG.md`)

- **Ojo del Tribunal: sentencia escrita en el suelo (`feat/ojo-sentencia`, 2026-11-23, en `proto/arpg` y `main`):** grieta verde con ojos desde sus pies que te sigue, se fija hasta el muro, cuenta atrás y estalla toda a la vez; la cabeza solo abre la boca; daño = franja de suelo. Variante `arpg-ojo` (sala de prueba con un Ojo). Builds 0 avisos, guardrails PASS. **Pendiente:** `perf` en la DS y probar `arpg-ojo` en la DS; escenarios `ojo-tribunal` ya fallaban antes por aserciones desfasadas. [`walkthrough`](walkthroughs/ojo-sentencia/walkthrough.md)
- **Zona 1 jugable (`claude/arpg-zona1-jugable-d58ff4`, 2026-11-23, en `proto/arpg`):** mapa de 16 salas con Claustro y Hospital (~1 h), plantel de la parte 1 sin élites, Capilla del párroco (monjas rezando que curan; suelta la llave), Misa y monjaraña, reja de llave ante el cofre legendario, premios garantizados, viaje entre altares, XP por amenaza (Cripta a nivel 6 simulado) y tarjeta de fin de la demo; guardado v6. Builds 0 avisos; escenarios de evidencia PASS. **Falta:** partida completa del usuario con feedback y `perf` en la DS. [`walkthrough`](walkthroughs/arpg-zona1-jugable/walkthrough.md).
- **ROM de prueba de sonidos (`claude/arpg-prueba-sonidos-723ae1`, 2026-11-23, en `proto/arpg`):** variante `prueba-sonidos`: 7 escenas elegibles desde el menú (SELECT) que disparan cada grupo de sonidos en su contexto (remates, Rayo y Glifo, Ojos, Cireneos, Monja, Monaguillos, Campanero) y catálogo con cada `SND_*`, su archivo y su origen (banco gratuito o IA) más los 31 `lab_*`. Escuchada en la DS por el usuario; la lista de lo que chirría está en «Pendiente», punto 5. Build 0 avisos; no se sustituyó ningún sonido. [`walkthrough`](walkthroughs/arpg-prueba-sonidos/walkthrough.md).
- **Campamento nocturno cerrado (`claude/arpg-campamento-19aed8`, 2026-11-23, sobre `proto/arpg`):** muros del campamento = muros de la catedral con grietas e hiedra; la mesa es el Crisol de desguace (bolsa sin engarces; el arcón queda sin Crisol); los objetos utilizables respiran un halo cálido y el portón brilla en el umbral. **Alijo del arcón:** 16 huecos para reliquias, guardado en la partida (v6; los v5 se leen). Build 0 avisos; escenarios `camp_foco_crisol` y `camp_alijo` (evidencia). **Sin hacer:** medir `perf` en la DS; pociones/gasto de cera (decidido: solo desguace). [`walkthrough`](walkthroughs/arpg-campamento/walkthrough.md).
- **Exvotos de escalón 3 (`claude/arpg-exvoto-ramas-a622a1`, 2026-11-23, en `proto/arpg`):** Súper Monja araña emboscada (embestida que persigue, esquiva el Glifo) con aura de posesión sobre Monja de cera y Monaguillo (se levantan al quedar tambaleantes); Párroco inmune al Rayo (destello, chispas, «0»); guardaespaldas más rápidos que no protegen al Bebé; remates de la Súper Monja (18 fotogramas) y del Párroco; variantes `arpg-exvotos` y `arpg-remates`. Escenarios PASS en emulador y jugado en la DS, sin log `perf`. **Falta:** `perf` con muchos poseídos, balance y dónde salen en el acto I. [`walkthrough`](../walkthroughs/arpg-exvoto-ramas/walkthrough.md).
- **Remate de la Súper Monja araña (`claude/remate-smonja-27d615`, 2026-11-23, sobre `claude/arpg-exvoto-ramas-a622a1`):** `L` sobre la Súper Monja tambaleante: el héroe le arranca la cabeza de un tirón amplio y el cuerpo araña cae espatarrado (variante B elegida por el usuario frente a un tirón más corto). Build `arpg-lab` 0 avisos; escenarios `remate_transicion_smonja` (oeste) y `_sur` PASS con GIF de la ROM. **Sin hacer:** `perf` en la DS y comprobar que el remate del Ojo sigue bien. [`walkthrough`](walkthroughs/remate-smonja/walkthrough.md).
- **Remate del Párroco «derretirlo» (`claude/remate-parroco-f8ecfc`, 2026-11-23, sobre `arpg-exvoto-ramas`):** de pie y frío, el héroe le atraviesa el pecho con la mano; brillo cálido y el Párroco se derrite de abajo arriba hasta un charco (40 fotogramas, ~2,7 s). Aprobado por el usuario en GIF de la ROM; 5 escenarios de remate PASS; falta `perf` en la DS. [`walkthrough`](walkthroughs/remate-parroco/walkthrough.md).
- **Familias y roles de los Exvotos (`claude/arpg-exvoto-ramas-a622a1`, 2026-11-22, solo diseño):** cuatro familias con escalones (Exvoto chico: Bebé → Monaguillo → Párroco; Exvoto chica: Bebé → Monja → Súper Monja; Ojo; Cireneo) y el Abanderado de jefe. El Monaguillo protege a la Monja poniéndose delante del Rayo, la Monja cura fuerte, el Párroco es un Monaguillo más rápido que carga y la Súper Monja cura y acelera. Falta reordenar el código, que usa esos nombres para otros roles. [`walkthrough`](walkthroughs/arpg-exvoto-ramas/walkthrough.md).
- **Icono de la reliquia del Glifo (`feat/arpg-icono-hostia`, 2026-11-23, en `proto/arpg`):** las reliquias del Glifo son una hostia consagrada con el anillo y el crismón hendidos (antes, un rombo de color), modelada por geometría en Blender (`tools/make_relic_hostia.py`) y renderizada como las demás: bolsa, engarces, giro en la ficha y suelo con halo y sombra. Builds 0 avisos; `arpg_icono_hostia` PASS (capturas); sin verla en la DS. [`walkthrough`](walkthroughs/arpg-icono-hostia/walkthrough.md)
- **El Campanero de Ánimas (`feat/arpg-campanero`, 2026-11-23, en `proto/arpg`):** jefe con arte propio (campana por el yugo, sin atravesar el cuerpo), intro propia, toque verde cortado en seco por columnas y estatuas con el corte marcado (la zona segura no se pinta) y tañido como línea gris. En la DS, ~96 % de fotogramas a tiempo en combate (ondas por píxel recortadas, sonidos escalonados, animación en RAM en `perf`). Builds 0 avisos; `arpg_campanero_sombra_columna` PASS. **Sin equilibrar el encuentro:** las coberturas quedan fuera del alcance del Rayo; pendiente de sesión de balance. [`walkthrough`](walkthroughs/arpg-campanero/walkthrough.md)
- **Cartas y Códice comprimidos (`perf/arpg-rom-compresion`, 2026-11-23, en `proto/arpg`):** port de la compresión de `main`; mismos píxeles. ROM 15,1 → 12,7 MB. Build 0 avisos y `bestiary_tour` PASS. [`walkthrough`](walkthroughs/arpg-rom-compresion/walkthrough.md).
- **Reliquias en el suelo con su icono (`fix/arpg-icono-suelo`, 2026-11-22, en `proto/arpg`):** las reliquias y tomos caídos muestran su icono a 24 px con más contraste, halo semitransparente del color de rareza y sombra proyectada (antes, un rombo de color). Builds sin avisos, capturas de la ROM y visto en la DS (variante `reliquias-suelo`); sin log `perf`. [`arpg-icono-suelo/`](walkthroughs/arpg-icono-suelo/walkthrough.md)
- **Menús y arranque del ARPG (`claude/arpg-menus-inicio-f647ad`, 2026-11-22, sobre `proto/arpg`):** la intro del roguelike (6 tarjetas) pasa a 3 tarjetas del ARPG con vídeo de la ROM (Pelear, El lápiz, El campamento); avisos de primera vez (rematar, primera reliquia, Glifo, dormir) guardados en la partida; tarjeta «Reliquias» la primera vez que se abre el inventario; Controles en dos bloques (con SELECT Mapa); pausa de la catedral por encima del HUD; arreglada la franja negra de la pantalla de arriba del campamento. Build 0 avisos; escenarios `arpg_menus_inicio_final`, `arpg_avisos` y `arpg_menus_pulido` PASS. Visto en la DS por el usuario. **Sin hacer:** leer el log `perf` del campamento y del inventario; avisos de rematar, reliquia y Glifo no vistos en el emulador. [`walkthrough`](walkthroughs/arpg-menus-inicio/walkthrough.md).
- **Mapa fijo de la zona 1 (`feat/arpg-mapa-zona1`, 2026-11-22, en `proto/arpg`):** 12 salas fijas (variante D: 4 naves de 6 pantallas, galerías, capillas y Cripta) con nivel y grupos tipo por sala, escalón 2 de Ojo y Cireneo, fundido al cruzar, llegada junto al hueco opuesto, persistencia (guardado v5) y reaparición al dormir. La sala flota en el vacío: muro del fondo de arcos con la puerta abierta, huecos laterales de dos módulos con oclusión y muros a la mitad de grosor. SELECT abre un mapa isométrico superpuesto. Builds 0 avisos nuevos; escenarios de capturas PASS; jugado y medido en la DS sin más caídas que antes. [`walkthrough`](walkthroughs/arpg-mapa/walkthrough.md).
- **Glifo pulido (`feat/glifo-pulido`, 2026-11-22, sobre `proto/arpg`):** sin proyectil, el héroe reza (y puede andar mientras apunta y reza); alcance infinito solo sobre suelo, con la runa recortada en los muros; previsualización tenue con el lápiz apoyado; runa al radio real; SFX del banco (`lab_creak`, `lab_mining0`); Crisol con confirmación; L pega al pulsar y abre el radial si se mantiene. Builds 0 avisos nuevos y escenarios PASS; probado en la DS. [`walkthrough`](walkthroughs/glifo-pulido/walkthrough.md).
- **Limpiezas del ARPG (`fix/arpg-limpiezas`, 2026-11-22, en `proto/arpg`):** fuera el árbol de habilidades (el Glifo depende solo de su tomo), la Resurrección desenganchada y las runas de experiencia; `DESIGN-ARPG.md` §1–2 describen el juego actual y el escalón intermedio es el Párroco (los modelos de Súper Monaguillo y Súper Monja no están en el repo). Build 0 avisos; `glifo_equipar` PASS. [`walkthrough`](walkthroughs/arpg-limpiezas/walkthrough.md).
- **Sala de boxeo y puñetazo sin cortes (`feat/boxeo-lab`, 2026-11-22, sobre `feat/arpg-lab` + `fix/punch-pies-puños`):** nueva variante `arpg-boxeo` con un solo enemigo de vida infinita delante del héroe para probar el puñetazo, y página «Puñetazo» en el menú del lab para ajustarlo en vivo. El golpe encadenado ya no corta la animación antes del impacto (cola de hasta 2 pulsaciones), el empuje y el *hit-stun* se aplican de verdad y los toques cortos ya no se pierden. Builds `arpg-boxeo`, `arpg-lab` y `default` 0 avisos nuevos; escenario `arpg_boxeo` PASS; sin medición `perf` en la DS. [`walkthrough`](walkthroughs/sala-boxeo/walkthrough.md).
- **Puñetazo andando en el ARPG (`fix/punch-pies-puños`, 2026-11-22, sobre `proto/arpg`):** el combo ya no clava al héroe: se puede andar al 65 % mientras pega. Composición en runtime del tren superior del golpe y las piernas del andar en la dirección real, con la cadencia del paseo escalada al 65 % (0,414 px/frame con período 6 ≈ 19,9 px/ciclo, frente a 0,637 px/frame y período 4 ≈ 20,4 px/ciclo): sin deslizamiento. Parado, clip entero con los pies plantados. Andando, el golpe va en la dirección de movimiento y alcanza un cono frontal de ±45° (a menos de 4 px entra siempre); parado, autoapuntado al enemigo más cercano. Build 0 avisos y escenario `punch_andando` PASS; sin medición `perf` en la DS. [`walkthrough`](walkthroughs/punch-andando/walkthrough.md).
- **Pulido de reliquias, stats en combate real, bloqueo por nivel y dirección de escalones (`fix/arpg-relic-stats`, 2026-11-22, en `proto/arpg`):** alcance ajustado a la protodemo (2 auras Rayo, 1 Ejecución, 2 Pecho y 3 Legendarias; pestañas *Glifo* y *Levantar* selladas con «Letanía sellada»); unidades explícitas (`%`, `pts`, `pts/s`), `Carga`/`Alcance` en `%` (alcance de Ejecución conectado a puñetazo y remate) y `mech_val` conectado al daño real de cada aura, con `Vida máx.`, `Maná máx.` y *Llaga Abierta* reversibles en vivo; escalado Nivel vs. Rareza donde el nivel manda en stats brutos con bloqueo `Req. Nv. X` (Opción A) y drops fijos por ala/escalón; optimización VBlank en comparativa (`EQUIPADA` vs `REQ. NV.10` sin cortes). Documentadas en `DESIGN-ARPG.md` §5 y `diseno_juego_final.md` las etapas de corrupción biológica y la elección de SFX definitivos como pendiente. Builds `default` y `arpg-todo` con 0 avisos; tests y escenarios PASS. [`walkthrough`](walkthroughs/arpg-relic-stats/walkthrough.md).
- **Glifo en la ROM y revisión del inventario (`feat/glifo`, 2026-11-22, en `proto/arpg`):** el Glifo sustituye a la Maldición: ciclo apertura/espera/detonación de 80, hasta 3 a la vez, runa A horneada por script y auras **componibles** (Redil retuerce la runa y arrastra al centro; Zarza añade llamas y Quemado). Reliquias con líneas Daño/Radio/Espera/Coste y legendaria Ampolla del Santo Óleo. Inventario: pestaña Glifo con engarces, tomos visibles, desengarzar (X, toque doble, arrastre) y 9 fallos más; guardado v4. Radial con `L` en 5 frames. Builds 0 avisos; `glifo_equipar`, `inventario` y `test_guardrails` PASS. **Pendiente:** `perf` en la DS con 3 glifos, enemigos apilados en el Redil, runa fija a radio 40, Vial y SFX. [`walkthrough`](walkthroughs/glifo-diseno/walkthrough.md).
- **Pulido de reliquias, ventana 3D giratoria y auras ARPG (`fix/arpg-relic-ui`, 2026-11-22, en `proto/arpg`):** corregido el oscurecimiento de Nudillera y Corazón en la bolsa; pantalla superior dividida con ventana de objeto 3D 56×56 girando en 24 fotogramas desde NitroFS (`tools/render_item_spin.py`, lectura sin búfer `open`/`read` para no consumir heap); cambio automático de pestaña al seleccionar reliquia; descripciones ARPG (sin corazones) con cifra propia (`mech_val`) en ficha y comparativa lado a lado; Rayo limitado a sus 2 auras (*Lanza* y *Llama Votiva*); **Cilicio** activo de forma continua al caminar. Builds `default` y `arpg-todo` con 0 avisos; `test_guardrails` y escenario `arpg_inv_ui_check` PASS. [`walkthrough`](walkthroughs/arpg-relic-ui/walkthrough.md).
- **Reliquias y libros 3D en el inventario ARPG (`feat/reliquias-libros-3d`, 2026-11-22, en `proto/arpg`):** 6 modelos 3D del inbox pre-renderizados en sprites 24×24 RGB15 con el pipeline de legibilidad C2: Punta de Lanza (Rayo), Nudillera (Ejecución), Cráneo Votivo (Levantar), Tomo del Glifo (verde), Tomo de Levantar (negro) y Tomo del Rayo (amarillo con cruz). Integrados en `source/inventory.c` reemplazando los glifos geométricos provisionales (rombos y anillos) por los sprites 3D en engarces, bolsa, arrastre y tarjetas de comparación. Bolsa inicial (`arpg_inv_new_game`) ampliada a 14 objetos sumando el Tomo verde, el Tomo negro y el Cráneo votivo, dejando 2 huecos libres. Textos diegéticos en tooltips e inspección. Builds `default` y `arpg-todo` con 0 avisos; escenario `arpg_menus` PASS. [`walkthrough`](walkthroughs/reliquias-libros-3d/walkthrough.md).
- **Campamento nocturno (`proto/arpg`, 2026-11-21, no integrado en `main`):** patio exterior de noche iluminado solo por la hoguera, con la luz horneada: suelo de tierra y piedra con 7 bandas de brillo y parpadeo por paleta, fuego animado nuevo, props y héroe re-renderizados con luz de fuego (el héroe en 8 variantes según su posición respecto al fuego), sin rótulos, y un marco de muros hecho con un kit de 3 imágenes del usuario (norte con portón central; laterales con contrafuertes cada 5 paneles). **Pendiente por decisión del usuario: revisar la perspectiva de los muros laterales** (se ven como texturas pegadas en escorzo; el frontal sí queda bien). **Sin hacer:** medición `perf` en la DS (marco ~40k píxeles/frame y lectura por frame del héroe desde NitroFS), mesa como Crisol, señal diegética de foco. [`walkthrough`](walkthroughs/campamento-nocturno/walkthrough.md)
- **Protodemo ARPG v1 (`proto/arpg`, 2026-11-20, prototipo, no integrado en `main`):** combo de puñetazos, tambaleo por vida baja, Glifo, HUD de vasos y números de daño, salas con puerta, hueco lateral, cofres y altares, población por grupos con curva de inicio, tiers de Exvoto (Bebé, Párroco, Monja) y campamento andable. Build sin avisos; subida a la DS sin medir rendimiento. [`walkthrough`](walkthroughs/arpg-predemo/walkthrough.md).
- **Vídeo de lore 09 Los monaguillos (`feat/video-monaguillos`, 2026-11-21):** `assets/videos/lore01_09_los_monaguillos.mp4` (57,8 s, con voz, sin publicar; textos de los posts en `lote-01.md`). Con pregunta moral «¿Habrías hablado tú, sabiendo el castigo?», dos animaciones y la Columna marchando de espaldas y luego de frente. Decisión: no se hace Gaspar humano para el 05 (los condenados recrean su pasado). [`walkthrough`](walkthroughs/lore-lote-01/walkthrough.md).
- **Render rápido de personajes (`perf/render-rapido`, 2026-11-21):** exportador sin navegador (`tools/lab/fast/`, Node + rasterizador por software) por defecto en `rebuild_all.py`: 16 personajes 113 s → 29 s con 4 en paralelo (≈2–4 s cada uno solo). Validado a ojo por el usuario. Detalle en [`walkthroughs/render-rapido/`](walkthroughs/render-rapido/walkthrough.md). Regla en `AGENTS.md` (12).
- **Huella exacta de las barricadas de sacos (`fix/sacos-hitbox`, 2026-11-21):** la colisión de los sacos es ahora la franja de apoyo de 4 px del arte 3D, no el rectángulo del placeholder: el héroe se pega a la base por delante y por detrás. [`walkthrough`](walkthroughs/sacos-hitbox/walkthrough.md).
- **Depósito de sala: reparto RAM / cartucho (`perf/ram-por-sala`, 2026-11-23, en `proto/arpg`):** los enemigos salen de la RAM fija y se cargan por sala en la pantalla de carga (depósito de 1,70 MB; la sala más cara, la del Campanero, 1,63 MB); sombras a 1 bpp en todos los personajes (Campanero 1,57 → 1,12 MB); Párroco, Súper Monja y Campanero ya no leen del cartucho en combate salvo respaldo. Regla para todo contenido nuevo en `TECHNICAL.md` §3.3.1. Builds 0 avisos nuevos, barrido de 12 salas sin cargas imprevistas, escenarios y tests PASS; **sin medir en la DS**. [`walkthrough`](walkthroughs/ram-por-sala/walkthrough.md).
- **Vídeo de lore 10 No es mi corazón (`docs/video-corazon`, 2026-11-22):** `assets/videos/lore01_10_no_es_mi_corazon.mp4` (66,1 s, con voz, sin publicar; textos de los posts en `lote-01.md`). Pregunta moral «¿Quién está más vivo: el que murió o el que lo lleva?», arranque con el corazón de un soldado muerto, Inés como pista final y la cita de Martín sobre el corazón. [`walkthrough`](walkthroughs/lore-lote-01/walkthrough.md).
- **Título e inventario (`claude/arpg-acabado-0baf54`, 2026-11-23, sobre `proto/arpg`):** pantalla de título con el nombre provisional EXVOTION y una vela que parpadea, las dos pantallas sobre el mismo fondo oscuro; el inventario pasa a Palatino 10 (fuente propia; el resto sigue en 11). Builds 0 avisos; `arpg_titulo` y `arpg_menus_inicio_final` PASS (capturas). Sonidos aplazados a una ROM de prueba. [`walkthrough`](walkthroughs/arpg-acabado/walkthrough.md)
- **ROM más ligera: cartas y Códice comprimidos (`perf/rom-compresion`, 2026-11-23):** el arte de las 17 cartas de mejora y los retratos del Códice va comprimido (formato de la BIOS) y se descomprime al cargarlo; mismos píxeles. ROM 10,4 → 9,6 MB. Build 0 avisos, `bestiary_tour` PASS y cartas vistas en la ROM; sin mirar en la DS. Siguientes candidatos (remates, sprites a paleta, sombras a 1 bit) en el [`walkthrough`](walkthroughs/rom-compresion/walkthrough.md).
- **Campamento nocturno cerrado (`claude/arpg-campamento-19aed8`, 2026-11-23, sobre `proto/arpg`):** muros del campamento = muros de la catedral con grietas e hiedra; la mesa es el Crisol de desguace (bolsa sin engarces; el arcón queda sin Crisol); los objetos utilizables respiran un halo cálido y el portón brilla en el umbral. **Alijo del arcón:** 16 huecos para reliquias, guardado en la partida (v6; los v5 se leen). Build 0 avisos; escenarios `camp_foco_crisol` y `camp_alijo` (evidencia). **Sin hacer:** medir `perf` en la DS; pociones/gasto de cera (decidido: solo desguace). [`walkthrough`](walkthroughs/arpg-campamento/walkthrough.md).

- **Vídeo de lore 05 Sor Leonor, A/B clásico frente a Remotion (2026-11-23, en `main`):** `assets/videos/lore01_05_sor_leonor.mp4` (62,1 s) y `lore01_05_sor_leonor_remotion.mp4` (mismo audio y planos; subtítulo palabra a palabra, zoom por plano y golpes; composición `Lore05` en `C:\codexlocal\devlog`). El Ojo hace de Tribunal y Leonor sale como monja de cera; pregunta «¿Mintió Leonor… o mintió el farol?». Se publican las dos como A/B; resultado pendiente en `lote-01.md`. [`walkthrough`](walkthroughs/lore-lote-01/walkthrough.md).

- **Cámara hacia el grupo (`feat/camara-grupo`, 2026-11-23, en `main` y `proto/arpg`):** en combate el encuadre vertical apunta entre el héroe y el centro del grupo de enemigos (los cercanos pesan más), con suavizado y el héroe entre el 25 % y el 75 % de la pantalla táctil; kitear hacia atrás ya no quita el frente. Sin enemigos sigue el adelanto por marcha. Probado y aprobado por el usuario en la DS (`perf`: CPU media ~12 %, dos picos breves). [`walkthrough`](walkthroughs/camara-grupo/walkthrough.md).

- **Del ARPG al roguelike: números de daño y depósito de sala (`feat/migra-arpg`, 2026-11-23):** cifras flotantes sobre el enemigo golpeado (daño y quemado; sin cifra sobre el héroe, `DESIGN.md` §6.11.3) y enemigos fuera de la RAM fija: se cargan del cartucho al empezar el acto, sombras a 1 bpp (`TECHNICAL.md` §3.3.1). Heap libre +290 KB, ROM 9,57 → 9,11 MB. Build 0 avisos, tests de guardarraíles y escenarios de enemigos y remates PASS, `pool_misses` 0; **sin medir en la DS** (mergeado así por decisión del usuario). Falta pasar a carga por encuentro antes de traer Súper Monja, Párroco y Campanero. [`walkthrough`](walkthroughs/migra-arpg/walkthrough.md).

## Entrega archivada desde STATUS-ARPG.md

- **Zona 1 jugable (`claude/arpg-zona1-jugable-d58ff4`, 2026-11-23, en `proto/arpg`):** mapa de 16 salas con Claustro y Hospital (~1 h), plantel de la parte 1 sin élites, Capilla del párroco (monjas rezando que curan; suelta la llave), Misa y monjaraña, reja de llave ante el cofre legendario, premios garantizados, viaje entre altares, XP por amenaza (Cripta a nivel 6 simulado) y tarjeta de fin de la demo; guardado v6. Builds 0 avisos; escenarios de evidencia PASS. **Falta:** partida completa del usuario con feedback y `perf` en la DS. [`walkthrough`](walkthroughs/arpg-zona1-jugable/walkthrough.md).

- **Sonidos definitivos (`claude/arpg-prueba-sonidos-723ae1`, 2026-11-24, en `proto/arpg`):** elegidos por el usuario en la DS con la variante `prueba-sonidos`: Glifo (`glifo_grieta`, `glifo_detonacion`), orbe, Monaguillo y golpe grave del Cireneo (ElevenLabs). Cada remate tiene su sonido sincronizado, con varias pistas (Súper Monja, Ojo, Párroco); se retira `remate_exec`. Mezcla: tambaleo con retraso tras el puñetazo, el Rayo ya no suena como impacto, la campana del Campanero suena al alzarse. Builds `prueba-sonidos`, `arpg-lab` y por defecto 0 avisos; el audio se validó en la DS. Falta el sonido de premio de la reliquia. [`walkthrough`](walkthroughs/arpg-prueba-sonidos/walkthrough.md).

- **Remate que cura y balance (`claude/awesome-bohr-b761e7`, 2026-11-24, en `proto/arpg`):** el remate restaura vida y maná al instante (60 % +20 vida, 75 % +25 maná) con destello y `+N`, sin orbes en el suelo ni sonido propio (solo suena el remate, sin el de muerte genérica); balance de `DESIGN-ARPG.md` §10 con `tools/arpg_balance.py` y perillas `BAL`; bot con guion; atasco del Cireneo traído (carga fuera de la ITCM para que quepa). Builds 0 avisos; `arpg_remate_cura` y `cireneo_atasco_gif` PASS; probado en la DS por el usuario. **Pendiente:** subir la cura (+20 es poco frente a 420 de vida a nivel 5); `perf` en la DS; a veces suena una «ruleta» al rematar un Exvoto (sospecha: recoger una reliquia que cae donde termina el remate, sonido de orbe agudo; sin confirmar); el escenario `enemy_ojo_sentencia_alcanza_al_heroe_quieto` falla porque espera corazones del roguelike (5→4) y en el ARPG la vida va 100→70; bot: Capilla con llave y táctica de jefe. [`walkthrough`](walkthroughs/arpg-remate-cura/walkthrough.md).

## Entrega archivada desde STATUS.md (2026-11-26)

- **Ojo del Tribunal: sentencia escrita en el suelo (`feat/ojo-sentencia`, 2026-11-23, en `main` y `proto/arpg`):** el Ojo ya no apunta con banda verde ni dispara un haz: escribe en el suelo una grieta con ojos que te sigue, se fija hasta el muro, cuenta atrás con sus ojos y estalla toda a la vez en llamas verdes; la cabeza solo abre la boca. El daño es esa franja desde sus pies. Builds por defecto y `perf` sin avisos, guardrails PASS, captura de la ROM. **Pendiente:** medir `perf` en la DS (rendimiento sin certificar); los escenarios `ojo-tribunal` ya fallaban antes por aserciones desfasadas. [`walkthrough`](walkthroughs/ojo-sentencia/walkthrough.md)

## Entrega archivada desde STATUS-ARPG.md (2026-11-26)

- **Arcón: alijo sin pisar la filigrana (`fix/arpg-inv-alijo`, 2026-11-24, en `proto/arpg`):** maquetación B «Respiro» elegida en ronda A/B/C: alijo y bolsa 4x4 de 26 px alineadas, margen de 5 px, títulos «Alijo» y «Bolsa», fila inferior con ayuda y cera; las espadas caben en sus casillas; pestañas repartidas con hueco igual y centradas en todos los modos. La cabecera de la pantalla superior muestra el icono del viril de la escuela (Pecho sigue con rombo). Verificado: builds 0 avisos y escenario `arpg_inv_alijo`; no probado en la DS (menú); sin revisar a ojo las pestañas en pausa y Crisol. [Walkthrough](walkthroughs/arpg-inv-alijo/walkthrough.md).

## Entrega archivada desde STATUS-ARPG.md (2026-11-26, 2)

- **Póster del mapa ARPG, versión preliminar (`docs/poster-arpg`, 2026-11-24, en `proto/arpg`):** póster de las 16 salas con la composición de props de cada una (cada sala cuenta lo que fue), sombras bajo luz de techo, flechas a la sala real y visor con zoom (teselas HD). Es solo documentación y herramientas (`tools/poster/`); el juego no cambia. Verificado visualmente en el póster. **Falta:** luces definitivas por sala y enemigos; el cofre fijo choca con un enemigo en las salas 5, 7 y 12. [`walkthrough`](walkthroughs/poster-mapa/walkthrough.md).

## Entrega archivada desde STATUS-ARPG.md (2026-11-26, 3)

- **Escala de props del mapa (`proto/props-escala`, 2026-11-25, en `proto/arpg`):** los props de los enemigos pasan a escala creíble (reclinatorio 28 px recoloreado, catre 48, palangana 24, cepo 32; osario: calaveras 21, huesos 34, estante 40) y los exvotos (40 px) se cuelgan de la pared del fondo; paleta compartida 171 → 175 colores. Verificado: test_guardrails, test_strip_kit y test_cathedral_kit_contract PASS; ROM sin avisos nuevos; sin DS. **Falta:** el altar sigue a 16 px (a 28 rompe el horneado del kit); `osario_lado` sin revisar; `place()` del póster descarta en silencio piezas solapadas; `test_cathedral_kit` falla en 2 casos previos (IDs de puerta y de pieza); imagen `salas/15_cripta.png` sin actualizar. [`walkthrough`](walkthroughs/props-escala/walkthrough.md).

- **Puñetazo: objetivo igual andando que parado (`fix/punch-target`, 2026-11-25, en `proto/arpg`):** el golpe elige el enemigo más cercano dentro del alcance en cualquier dirección, sin el cono de ±45° al andar; arregla los fallos con enemigos en diagonal. Probado en la DS («se siente perfecto»). Nueva variante `arpg-boxeo-mele` (12 monaguillos que persiguen y reaparecen) para probar el cuerpo a cuerpo. Builds 0 avisos; `punch_diagonal`, `arpg_boxeo` y `punch_andando` PASS; sin `perf`. [Walkthrough](walkthroughs/punch-target/walkthrough.md).

- **Encuentros de la zona 1, diseño (`feat/arpg-encuentros`, 2026-11-25, en `proto/arpg`):** las 16 salas tienen grupos de enemigos colocados a mano (formaciones, reposo, emboscadas, progresión por naves), decididos en `DESIGN-ARPG.md` §12 y revisados en el póster (herramienta, la ROM no cambia). Pendiente: llevar posiciones y reposos a la ROM (vaivén, monja rezando, barrido del Ojo, Cireneo paseando, escondidos con pista, patrulla, despertar del grupo), regenerar los props `osario_lado` y `sarcofago_lado` (la Cripta es provisional), emboscadas del Osario a ~80 px del camino, radio de aviso en galerías de un tramo y el Párroco tapa algo el altar. Detalle: [`arpg-encuentros/`](walkthroughs/arpg-encuentros/walkthrough.md).

- **Salas, reposos, luz por sala, Monja curandera y primera partida en la ROM (`feat/arpg-integra`, 2026-11-26, en `proto/arpg`):** las 16 salas de la zona 1 salen en la ROM con sus piezas (`.rmk`) y su luz principal (12 luces, cargadas en la pantalla de carga), los grupos aparecen por proximidad y reposan por papel hasta que el héroe se acerca, y la Monja de cera cura a su grupo en combate. **En ROM, falta medir en la DS** (FPS y tiempo de carga de sala; margen de montón ~12-16 KB con la luz cargada, `TECHNICAL.md` §3.3.1). Escenarios de la entrega PASS salvo `monja_curandera_gif` (evidencia sin suite; la Monja no cura al arrancar en sala, pendiente de diagnosticar). Detalle: [`arpg-salas-rom/`](walkthroughs/arpg-salas-rom/walkthrough.md). Luces de las salas 9, 12, 14 y 15 oscurecidas (merge `feat/arpg-luz-oscura` y `-b`). Cofre cerrado, cofre abierto y altar con la luz y la sombra de su sala (`_fix.bin`, `feat/arpg-fix-luz`; +2.816 B de montón).

- **Generador de sprites sin romper la luz por sala (`fix/sprite-gen-luz-sala`, 2026-11-26, en `arpg`):** regenerar `source/player_sprite.c` deshacía las ediciones de la luz por sala (fddb9938) y ahora `generate_player_sprites_c.py` encadena `tools/room_light_slots.py`; se ajusta el recuadro de sombra del Abanderado (pendiente desde 061d66a2; cuerpo y sombra idénticos, ~400 B menos por clip). Verificado: build sin avisos nuevos, `arpg_luz_sala`, `test_sprite_ground_anchor`, `test_blit_runs_contract`, `test_guardrails` PASS. Pendiente aparte: `cripta.bin` sale distinto al rehornearlo. Detalle: [`walkthroughs/fix-sprite-gen-luz-sala/`](walkthroughs/fix-sprite-gen-luz-sala/walkthrough.md).
- **Cepo legible (`feat/cepo-abc`, 2026-11-26, en `arpg`):** el cepo de las salas 4, 5 y 12 se ve en vista 3/4 y con la madera oscura y el metal marcado, así que se leen los agujeros (antes salía naranja y plano). Build -Clean PASS sin avisos nuevos y capturas de la ROM en las salas 4 y 12; `galerias` 743/1024 y `prisionero` 658/1024 tiles. No medido en la DS (prop fijo de decorado). Detalle en [`walkthroughs/cepo-abc/`](walkthroughs/cepo-abc/walkthrough.md).

- **Sombras largas en cripta y monjaraña (`fix/rehorneo-cripta-monjarana`, 2026-11-26, en `arpg`):** en la galería de la monjaraña (sala 14) y la cripta (sala 15) todas las piezas sueltas (capullos, calaveras, huesos, sarcófagos, braseros, lápidas) llevan ya sombra larga coherente con su luz; antes se descartaba en silencio la que no cabía en 8 px. Estatuas y columnas (kit) siguen con margen de 8 px (con sombra larga la monjaraña pasaba de 440 tiles por ventana). Monjaraña 941/1024 (ventana 229+143=372/440), cripta 706/1024; gana un capullo. ROM compilada y capturas 4x antes del merge; tras el merge con `arpg` se regeneró la colocación y los `.rmk` (sin recompilar ni recapturar). Sin probar en la DS. Detalle: [`fix-rehorneo-cripta/`](walkthroughs/fix-rehorneo-cripta/walkthrough.md).

- **Ficha de la escuela en el inventario (`feat/inventario-ficha`, 2026-11-26, en `arpg`):** la pantalla superior muestra por defecto la ficha de la escuela (estadísticas «base -> total» y nombres de sus auras por rareza; Pecho es una pestaña más); textos de aura sin cifra, con la cifra en línea propia; el inventario aplica las reliquias al abrirse (cifras correctas en el arcón recién arrancado). Compila (default y arpg-todo), `arpg_inv_ficha` PASS y probado en la DS; sin medición de rendimiento (no toca combate). [Walkthrough](walkthroughs/arpg-inventario-ficha/walkthrough.md).

- **ROM parcial por contrato (`feat/rom-parcial`, 2026-11-26, en `arpg`):** se puede compilar una ROM con solo lo que pide un contrato de conceptos (`rodaje`, `boxeo-monaguillo`, ...), traducido a archivos por `.ds-game-dev/partial/catalogo.json`; falla si un archivo de `nitrofiles/` no está catalogado o si, al correr los escenarios, el juego intenta abrir algo ausente. Verificado: contrato `rodaje` (8 escenarios `rodaje_boxeo_*`) PASS con 8,7 MB frente a 56 MB, sin párroco/monja FAIL nombrando lo que falta, y probado en la DS; el contrato `boxeo-monaguillo` no se ha compilado. [Walkthrough](walkthroughs/rom-parcial/walkthrough.md).
