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
