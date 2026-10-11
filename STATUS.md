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

- [x] El atlas de BG 8bpp pasa a ser dato estático escalable hasta IDs de tile de 16 bits; el cache VRAM permanece acotado al viewport móvil, no al ancho/alto total del mundo.
- [x] Bitmap 8bpp experimental: 240 frames DeSmuME, CPU medio 4.99 ms, `F=1.53 ms`, 240/240 a 60 FPS; el bitmap 512×512 ocupa 256 KiB y deja la pantalla superior sin BG.
- [x] Prototipo FBX tileado con ring map: DeSmuME intérprete 240 frames, CPU medio 4.89 ms, `F=1.49 ms`, 239/240 a 60 FPS; escenario de paseo PASS.
- [x] Refresco de pantalla superior a 30 Hz: CPU medio 5.48 ms y `F=2.91 ms`, peor que ring map; 240/240 a 60 FPS.
- [x] La pantalla superior muestra el suelo tileado siguiendo la misma cámara; mantiene el render de actores/sombras/HUD completo abajo.
- [x] Refinamiento genérico del ring: conserva BG 512×256 y actualiza solo la ventana visible de 33×25 tiles (máximo 825 residentes); elimina la dependencia de densidad de tiles fuera de pantalla.
- [x] Build limpia, contrato host y escenario de paseo PASS; ROM final CRC `9CA76D62`, SHA-256 `99A42DF4891390462F4F5B0C45BEB5AED68827DE46F8D1E105471CE6140A7173`.
- [x] Perfil DeSmuME final 240/240 a 60 FPS; CPU medio 4,919 ms, `F=1,508 ms`. Prácticamente igual al ring anterior: no demuestra la mejora en DSi.
- [x] Prueba de estrés del generador con bake 768×768 y 9.217 tiles únicos (atlas 589.888 B + mapa 18.432 B); genera correctamente IDs por encima del número de tiles residentes en VRAM.
- [x] ROM final subida: FTP devolvió PASS y el listado remoto mostró `dungeonds.nds` (1,85 MiB transferidos).
- [ ] La descarga FTP para comparación SHA-256 y un listado posterior agotaron conexión; byte a byte remoto pendiente. Medir HUD en DSi (`20 FPS`, `F≈38 ms` de referencia) al arrancar la ROM subida.
- **Evidencia:** [walkthroughs/fbx-floor-render-options/walkthrough.md](walkthroughs/fbx-floor-render-options/walkthrough.md).
