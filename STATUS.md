# STATUS.md - Historial de Entregas y Estado del Proyecto DungeonDS

Este documento registra el historial cronolÃ³gico de sesiones de desarrollo verificadas mediante compilaciÃ³n BlocksDS, escenarios deterministas en DeSmuME y validaciÃ³n en Nintendo DS fÃ­sica.

---

## SesiÃ³n 01: Prototipo Jugable y Pipeline de Renderizado
- [x] Repositorio inicializado, toolchain offline con Docker BlocksDS y DeSmuME headless.
- [x] ProyecciÃ³n dimÃ©trica: tiles de suelo en rombo 32Ã—`FLOOR_TILE_H` con ordenaciÃ³n por profundidad `(col+row)`.
- [x] Pipeline de Blender para pre-renderizado de ruinas y personaje en 8 direcciones.
- [x] Contrato de anclaje de suelo Ãºnico: origen en el centro de la celda.
- [x] CachÃ© de suelo del mundo en EWRAM (`s_floor_cache`) con mÃ¡scaras de sombra proyectada (Cycles Shadow Catcher).
- **Evidencia:** `walkthroughs/02-isometric-renderer/walkthrough.md`.

---

## SesiÃ³n 02: AtmÃ³sfera GÃ³tica Chiaroscuro y Outline de Legibilidad
- [x] IluminaciÃ³n gÃ³tica en `tools/ds_look.py`: antorcha Ã¡mbar viva, relleno frÃ­o tenue (`0.50`), ambiente (`0.18`), fondo negro abisal y sombras al 63%.
- [x] Outline de legibilidad de 1 px exterior para silueta del personaje sobre fondos oscuros.
- [x] SincronizaciÃ³n fÃ­sica de paso con zancada 3D (`PLAYER_SPEED = 181`, `ANIM_PERIOD = 3`, sin foot-sliding).
- [x] ColisiÃ³n sub-tile fÃ­sica circular en pilares de la cripta (radio de 0.65 m).
- [x] Linternas de alma frontales con llama azul espectral potenciada.
- [x] Banner NDS oficial: `DungeonDS: Necromancer Crypt`.
- **Evidencia:** `walkthroughs/03-dungeon-atmosphere-and-outline/walkthrough.md`.

---

## SesiÃ³n 03: Enemigo Cargador (Run.fbx) y Swap DinÃ¡mico de Personaje
- [x] GeneraciÃ³n de spritesheets del enemigo cargador: `charger_e30.png` y `charger_e30_shadow.png` (8 dirs x 8 frames).
- [x] SincronizaciÃ³n cinemÃ¡tica de carga: zancada de 2.00 m, `CHARGER_SPEED = 362` (1.41 px/frame, ~2x velocidad del hÃ©roe) y `ANIM_PERIOD = 2`.
- [x] OptimizaciÃ³n de memoria EWRAM: recorte de lienzo a 48Ã—40 centrado en pie, ahorrando >540 KB de RAM para encajar holgadamente en el lÃ­mite de 4 MB de la consola.
- [x] Cambio de personaje interactivo en tiempo real con botones (`X`, `Y`, `A` o `SELECT`).
- **Evidencia:** `walkthroughs/04-enemy-charger-and-character-swap/walkthrough.md`.

---

## SesiÃ³n 04: Arquitectura de Rendimiento 60 FPS y CorrecciÃ³n de Alineamiento ARM9
- [x] Benchmarking de frames determinista con timers hardware ARM9 (`cpuStartTiming`/`cpuGetTiming`) y script `tools/measure_perf.py`.
- [x] ReducciÃ³n de tiempo de render por frame de **86.59 ms (~10-11 FPS)** a **10.62 ms (80% bloqueado a 60 FPS)**.
- [x] Pre-baking de sombras estÃ¡ticas en la cachÃ© de suelo durante startup (`draw_shadow_mask_to_cache`), eliminando el 99% del coste de sombras en tiempo de ejecuciÃ³n.
- [x] EliminaciÃ³n de divisiones enteras software en shaders de sombras con desplazamientos de bits.
- [x] Double-buffering directo en VRAM con zero-copy (`MODE_FB0`/`MODE_FB1` escribiendo en `VRAM_A`/`VRAM_B`).
- [x] Interleaving de la pantalla superior durante scroll continuo (30 Hz top / 60 Hz bot).
- [x] **CorrecciÃ³n de alineamiento ARM946E-S en blitting**: reemplazo de accesos desalineados de 32 bits (`*(uint32_t*)`) por lecturas y escrituras halfword limpias de 16 bits (`uint16_t`), eliminando la rotaciÃ³n de 16 bits del hardware y la deslocalizaciÃ³n visual en muros y columnas.
- [x] ValidaciÃ³n visual determinista contra la verdad canÃ³nica: **0 pÃ­xeles de diferencia** frente a `00_spawn_center.png`.
- [x] Despliegue verificado en Nintendo DS fÃ­sica por FTP.
- **Evidencia:** `walkthroughs/05-arm9-alignment-and-60fps/walkthrough.md`.

---

## SesiÃ³n 06: CorrecciÃ³n de ColisiÃ³n y Orden de Profundidad (Depth Sorting) en Pilares
- [x] DiagnÃ³stico de desfase vertical de 8 pÃ­xeles de pantalla entre el collider y la base proyectada de los pilares.
- [x] CorrecciÃ³n del origen de colisiÃ³n de pilares en `position_is_free()` pasando de `(c + 0.5, r + 0.5)` a `(c, r)` para coincidir exactamente con el anclaje del sprite.
- [x] CorrecciÃ³n de la clave de profundidad de objetos en `render_screen()` a `(col + row) << 8`.
- [x] CorrecciÃ³n del spawn inicial del jugador en `player_init()` para centrado perfecto en la celda inicial.
- [x] GeneraciÃ³n de suite de test de colisiÃ³n de pilares (`scenarios/pillar_collision_test.json`) y evidencia visual side-by-side x4.
- [x] ValidaciÃ³n de no regresiÃ³n en todos los escenarios automÃ¡ticos con DeSmuME headless y compilaciÃ³n limpia con Docker BlocksDS.
- **Evidencia:** `walkthroughs/06-pillar-collision-and-depth-alignment/walkthrough.md`.

---

## SesiÃ³n 07: IntegraciÃ³n del Enemigo Skeleton y ReorganizaciÃ³n CanÃ³nica de Assets
- [x] Limpieza del repositorio raÃ­z: reubicaciÃ³n de capturas sueltas de tests y comparativas en `assets/tests_and_previews/` y scripts utilitarios en `tools/` y `tools/lab/`.
- [x] ClasificaciÃ³n canÃ³nica de modelos 3D bajo `assets/characters/<nombre>/` (`monster`, `charger`, `skeleton`).
- [x] IntegraciÃ³n de `skeleton.fbx` en el pipeline de horneado (`tools/bake_player.py`): soporte de material de hueso gÃ³tico (`BoneGothic`), normalizaciÃ³n de escala a estÃ¡ndar NDS ($1.39\text{ m}$) y fijaciÃ³n de root motion en caderas.
- [x] Ajuste de contraste para sombras Ã³seas esbeltas en `tools/shadow_masks.py` (percentil 0.1%), superando el contrato formal de tests unitarios (`tests/test_shadow_masks.py`).
- [x] CorrecciÃ³n del bug de outline gap: dilataciÃ³n y solidificaciÃ³n del sprite contra el contorno para eliminar vacÃ­os transparentes en cuernos y huesos finos.
- [x] Engrosamiento de malla Ã³sea del esqueleto (Displacement 0.12) y sombreado chiaroscuro dramÃ¡tico en Cycles con oclusiÃ³n ambiental de cavidades y rampa de profundidad.
- [x] ConsolidaciÃ³n definitiva del Charger OpciÃ³n A+ Pulida (1.35x, cuello elevado +20Â°, colores vivos 2K y outline anti-erosiÃ³n contiguo).
- [x] ExpansiÃ³n del conversor a C (`tools/convert_iso_to_c.py`) para soportar 3 personajes simultÃ¡neos (`CHAR_HERO`, `CHAR_CHARGER`, `CHAR_SKELETON`) con arrays BGR555 y mÃ¡scaras de 4 bits empaquetadas.
- [x] VerificaciÃ³n de compilaciÃ³n en Docker BlocksDS y ejecuciÃ³n headless en DeSmuME (`scenarios/character_switch_test.json`), demostrando conmutaciÃ³n cÃ­clica entre los tres personajes con fÃ­sicas y sprites impecables.
- **Evidencia:** `walkthroughs/07-skeleton-enemy-and-asset-cleanup/walkthrough.md`.

## SesiÃ³n 08: EstandarizaciÃ³n del Pipeline de Shaders, Normales y Contraste de Personajes
- [x] DiagnÃ³stico y auditorÃ­a de tratamientos ad-hoc en modelos 3D (`monster`, `charger`, `skeleton`).
- [x] FormalizaciÃ³n del manifiesto declarativo de perfiles de horneado en `tools/character_profiles.json` (desacoplado de bifurcaciones de cÃ³digo).
- [x] DocumentaciÃ³n formal de arquitectura en `TECHNICAL.md` (SecciÃ³n 3.1: regla de atenuaciÃ³n de normal maps al 30-40% en NDS, engrosamiento Displace de 0.12 para huesos, Ambient Occlusion de cavidades con ColorRamp y grading 2D en PIL).
- [x] GeneraciÃ³n de collages animados en 8 direcciones sincronizados (GIFs con 8 facings simultÃ¡neos) para cada configuraciÃ³n y modelo bajo `walkthroughs/08-standardize-character-shaders/assets/` mediante `tools/generate_all_8dir_collages.py`:
  - **HÃ©roe (Monster):** Conf 1 (In-place crudo), Conf 2 (Outline clÃ¡sico), Conf 3 (Anti-erosiÃ³n e30 actual).
  - **Cargador (Maw):** Conf 1 (Base 1.0x), Conf 2 (1.35x + cuello +20Â°), Conf 3 (Contraste limpio), Conf 4 (Horns glow), Conf 5 (OpciÃ³n A+ pulida).
  - **Esqueleto (Skeleton):** Conf 1 (Blanco plano original), Conf 2 (Engrosado marfil), Conf 3 (Chiaroscuro dramÃ¡tico actual).
- [x] Registro y catÃ¡logo visual auditable en `walkthroughs/08-standardize-character-shaders/walkthrough.md`.
- **Evidencia:** `walkthroughs/08-standardize-character-shaders/walkthrough.md`.

---

## SesiÃ³n 09: Rendimiento 60 FPS Dual-Screen, CorrecciÃ³n Diagonal y Multi-Entidad (10 Enemigos)
- [x] DiagnÃ³stico matemÃ¡tico y de temporizaciÃ³n del judder/tirones en diagonal del Charger:
  - EliminaciÃ³n del truncamiento de punto fijo 5-bit prematuro (`dcol`/`drow`), conservando resoluciÃ³n completa de subpÃ­xel de 8 bits.
  - SupresiÃ³n del enganche de fase cÃ­clico de pÃ©rdida de VBlank con el perÃ­odo de animaciÃ³n del Charger (`anim_period = 2`).
- [x] Overhaul del renderizador Dual-Screen a 60 FPS bloqueado:
  - EliminaciÃ³n de `s_top_backbuffer` en EWRAM (ahorro de 96 KB).
  - Renderizado directo en `VRAM_C` sin copias ni DMA bloqueante (`dmaCopyWords`).
  - Refresco a 60 Hz completo en ambas pantallas simultÃ¡neamente.
  - ImplementaciÃ³n de copias rÃ¡faga hardware ARM de 32 bits (`ldmia`/`stmia` con registros r3-r10) reduciendo el tiempo de floor copy a 6.5 ms (antes 11.5 ms).
  - VCount mÃ¡ximo de finalizaciÃ³n de renderizado en lÃ­nea 173 / 262 (19 scanlines antes del inicio del VBlank).
- [x] Sistema Multi-Entidad en tiempo real (10 enemigos activos):
  - IntegraciÃ³n de 10 enemigos autÃ³nomos (5 Chargers y 5 Esqueletos) deambulando y colisionando de forma independiente en la cripta.
  - OptimizaciÃ³n de bounding boxes dinÃ¡micas por frame (`s_char_frame_bounds`), reduciendo el Ã¡rea rasterizada en mÃ¡s de un 40%.
  - Sombreado dinÃ¡mico acelerado (`apply_shadow_fast`) con mÃ¡scara de bits a 1 ciclo de reloj (0.9 ms de sombras con 11 entidades simultÃ¡neas).
  - Despacho optimizado en ensamblador ARM para blitting y sorting en `render_screen()`.
- [x] VerificaciÃ³n de escenarios y captura de evidencia visual:
  - Suite de benchmarks deterministas de 240 frames en DeSmuME headless (`tools/measure_perf.py`).
  - GeneraciÃ³n de capturas y walkthrough en `walkthroughs/09-dual-screen-60fps-and-multi-entity/walkthrough.md`.
- **Evidencia:** `walkthroughs/09-dual-screen-60fps-and-multi-entity/walkthrough.md`.

---

## SesiÃ³n 10: Hardware Background Scrolling a 60 FPS en Dual-Screen
- [x] EliminaciÃ³n completa de la copia por software de ventana de suelo (`Floor Window Copy`) en ambas pantallas:
  - Descenso de tiempo de suelo de **7,232.1 Âµs** a **554.1 Âµs** (**-92.3%**).
  - SupresiÃ³n del array `s_floor_cache` en EWRAM, liberando **1.34 MB de RAM principal**.
- [x] IntegraciÃ³n de fondo tileado hardware (`BgType_Text8bpp`) en Modo 5 2D:
  - Uso de capa `BG1` tanto en motor principal (pantalla inferior) como secundario (pantalla superior).
  - Streaming eficiente del tilemap 32x25 en memoria de fondo hardware y ajuste directo de subpÃ­xel en registros `REG_BG1HOFS`/`REG_BG1VOFS`.
- [x] Empaquetado y particionamiento milimÃ©trico de VRAM:
  - Motor secundario: compresiÃ³n perceptual sin pÃ©rdida perceptible a **480 tiles Ãºnicos** (30 KB), encajando en los 128 KB de `VRAM_C` junto al tilemap (2 KB) y el framebuffer Bmp16 de entidades (96 KB).
  - Motor principal: `VRAM_A`/`VRAM_B` en double-buffering para `BG2` Bmp16 y `VRAM_D` (slot 6) para `BG1` Text8bpp.
- [x] Resultados de rendimiento comprobados:
  - **239 / 240 frames a 60 FPS exactos (99.6% locked 60 FPS)** en benchmark determinista.
  - FinalizaciÃ³n de renderizado en scanline raster promedio 117 / 262 (41 lÃ­neas antes del VBlank).
- **Evidencia:** `walkthroughs/10-hardware-bg-scroll-60fps/walkthrough.md`.

---

## SesiÃ³n 11: Streaming del Fondo, Stutter y AlineaciÃ³n de Pilares/Arcos
- [x] SustituciÃ³n del repintado de 32x25 tiles por un ring map hardware BG1 de 64x32; actualiza sÃ³lo filas/columnas expuestas dentro de VBlank.
- [x] CorrecciÃ³n del layout fÃ­sico de BG 512x256: dos screenblocks de 32x32, scroll circular sincronizado con el origen de cÃ¡mara y el fine scroll.
- [x] Particionamiento VRAM_C: tileset de 448 tiles (28 KB), mapa de 4 KB en offset 0x7000 y framebuffer de 96 KB desde 0x8000.
- [x] CorrecciÃ³n de telemetrÃ­a: incluye el streaming del fondo en los ticks de CPU y usa el presupuesto de 560,190 ciclos por frame.
- [x] Benchmark DeSmuME de 240 frames: **240/240 a 60 FPS**, carga CPU media **48.95%**, mÃ¡xima **53%**, streaming de suelo **26.8 Âµs/frame**.
- [x] Escenarios dual-screen (6 capturas), colisiÃ³n con pilares (5 capturas) y uniÃ³n muro/arco (4 capturas): todos PASS; capturas revisadas sin gaps, tiles negros ni seams.
- **Evidencia:** `walkthroughs/11-perf-bg-scroll-and-rendering/walkthrough.md` y sus assets de validaciÃ³n. Sin validaciÃ³n en consola fÃ­sica.

## SesiÃ³n 12: Prototipo de Combate con Lanza Ã“sea
- [x] Horneado del proyectil en ocho direcciones con el look e30 compartido y exportaciÃ³n a BGR555.
- [x] A mantenido autoapunta al enemigo activo mÃ¡s cercano; lÃ¡piz mantenido dispara en la direcciÃ³n de la pantalla inferior y prevalece sobre A.
- [x] Implementados daÃ±o provisional (30), vida (Esqueleto 40 / Charger 90), cadencia de 16 frames, proyectil rÃ¡pido perforante y destello breve al impacto.
- [x] Contrato host de sprites/nÃºmeros y escenarios DeSmuME para A, lÃ¡piz y fuego sostenido: todos PASS; el escenario de 120 frames elimina varios enemigos.
- [x] CompilaciÃ³n BlocksDS limpia. Sin validaciÃ³n en consola fÃ­sica.
- **Evidencia:** [walkthroughs/12-bone-lance-prototype/walkthrough.md](walkthroughs/12-bone-lance-prototype/walkthrough.md).

## SesiÃ³n 13: Salva de Perdigones de Hueso
- [x] ReducciÃ³n del asta del proyectil a aproximadamente 0,90 m y sprite opaco mÃ¡ximo de 12Ã—12 px en las ocho direcciones.
- [x] A y lÃ¡piz disparan cinco astillas rÃ¡pidas en abanico; 10 de daÃ±o por astilla y 16 frames entre salvas.
- [x] Balance de prueba: esqueleto 40 PV y cargador 90 PV; hasta 50 de daÃ±o si impactan los cinco perdigones.
- [x] Tres contratos host, compilaciÃ³n BlocksDS y escenarios DeSmuME para botÃ³n, tÃ¡ctil y fuego sostenido: PASS. Sin validaciÃ³n en consola fÃ­sica.
- **Evidencia:** [walkthroughs/13-bone-shotgun-pellets/walkthrough.md](walkthroughs/13-bone-shotgun-pellets/walkthrough.md).

## SesiÃ³n 14: Lanza Ã“sea Procedural
- [x] SustituciÃ³n del spritesheet por astillas estrechas de 8â€“11 px dibujadas en runtime, con variaciÃ³n por semilla y sin outline.
- [x] AÃ±adido pool de 32 motas espectrales con movimiento fijo, tonos/tamaÃ±os variables y vida de 4â€“7 frames.
- [x] Build BlocksDS, contratos host y escenarios DeSmuME para A, lÃ¡piz y fuego sostenido: PASS.
- [x] GIF de 28 capturas de DeSmuME registrado en walkthrough; ampliado nearest-neighbor para revisiÃ³n visual. Sin validaciÃ³n en consola fÃ­sica.
- **Evidencia:** [walkthroughs/14-bone-particle-lance/walkthrough.md](walkthroughs/14-bone-particle-lance/walkthrough.md).

## SesiÃ³n 15: Lanza RÃ¡pida y FragmentaciÃ³n de Enemigos
- [x] Duplicada la velocidad de los proyectiles de 4 a 8 px/frame, manteniendo el abanico y el daÃ±o.
- [x] Eliminado el cian de la lanza y las motas; paleta de hueso y marfil.
- [x] Al morir, el enemigo se rompe en seis parches 4Ã—4 de su sprite; preservan los colores originales, salen con impulso del disparo, describen un arco corto y se ordenan por profundidad.
- [x] Build BlocksDS y 3 contratos host: PASS. Escenarios DeSmuME para movimiento, botÃ³n, tÃ¡ctil, combate y muerte: PASS; GIFs de movimiento y fragmentaciÃ³n guardados. Sin validaciÃ³n en consola fÃ­sica.
- **InspiraciÃ³n TowerDS:** extracciÃ³n de parches de pÃ­xeles originales y fÃ­sica breve de fragmentos; adaptado al framebuffer BGR555 y al presupuesto de DungeonDS.
- **Evidencia:** [walkthroughs/15-bone-projectile-revision/walkthrough.md](walkthroughs/15-bone-projectile-revision/walkthrough.md).

## SesiÃ³n 16: DS Shader Lab Interactivo y Pipeline FBX Abierto
- [x] Desarrollo de DS Shader Lab (`tools/lab/shader_lab_server.py` y `tools/lab/shader_lab_ui.html` en puerto `8088`).
- [x] CorrecciÃ³n de centrado vertical de cÃ¡mara isomÃ©trica en Blender Cycles (`target_z = height * 0.50`), eliminando el corte superior a escalas de 1.4xâ€“2.2x.
- [x] Soporte para selecciÃ³n abierta de cualquier FBX del repositorio y subida vÃ­a web con previsualizaciÃ³n inmediata.
- [x] Acoplamiento cinemÃ¡tico automÃ¡tico de zancada 3D a velocidad fija de Nintendo DS (formato 8.8) para evitar foot-sliding.
- [x] La resoluciÃ³n de salida se selecciona en pÃ­xeles; la cÃ¡mara ortogrÃ¡fica se ajusta desde los vÃ©rtices animados y Blender renderiza directamente a ese tamaÃ±o. Tres FBX quedaron dentro de Â±1 px del objetivo de 32 px.
- [x] Comparados los sprites compilados de ROM con el laboratorio: tamaÃ±o visible mÃ¡ximo actual del hÃ©roe 18Ã—23 px, cargador 32Ã—36 px y esqueleto 19Ã—22 px; el selector ahora admite 22â€“60 px en pasos de 1 para reproducirlos.
- [x] Corregido el enlazado de mapas PBR FBX por nombre (base color, metallic, roughness y normal) y el entorno de reflexiÃ³n neutro; el mago encapuchado ya no se interpreta como metal negro.
- [x] El periodo en ticks controla tambiÃ©n la duraciÃ³n real de cada frame de la previsualizaciÃ³n; la inclinaciÃ³n se reaplica tras evaluar cada pose y detecta el eje lateral de Neck/Head (X o Z local) para evitar torsiones horizontales entre rigs.
- [x] Cada render del laboratorio guarda salidas con ID Ãºnico; el historial conserva los parÃ¡metros usados y los restaura al volver a una miniatura, evitando que renders distintos se sobrescriban por una clave incompleta.
- [x] Pasada final Impeccable: vacÃ­o inicial y mensajes de error Ãºtiles, controles avanzados etiquetados y accesibles, historial con teclado, collage ampliado y legible a 22 px; verificaciÃ³n en escritorio/mÃ³vil, cero overflow horizontal y cero errores de consola.
- [x] Render real a 22Ã—22 px (8 muestras) con dos ajustes de luz ambiente; IDs/GIFs distintos y restauraciÃ³n del ajuste al seleccionar la primera miniatura. Evidencia de UI y sprite en el walkthrough.
- [x] ValidaciÃ³n completa de renderizado de 8 direcciones en Blender Cycles y exportaciÃ³n de GIF collage.
- **Evidencia:** [walkthroughs/16-shader-lab-interactive/walkthrough.md](walkthroughs/16-shader-lab-interactive/walkthrough.md).

## SesiÃ³n 17: Shader Lab importa FBX sin buscar sidecars .fbm
- [x] Desactivada la bÃºsqueda recursiva global de imÃ¡genes FBX en el inspector de acciones y el worker de render.
- [x] El Shader Lab no inspecciona carpetas .fbm; utiliza los mapas empacados en el FBX.
- [x] Mario importa en **0,85 s** y renderiza desde una carpeta sin sidecar .fbm (48Ã—48, 16 muestras) en **7,7 s**.
- **Evidencia:** [walkthroughs/17-shader-fbx-image-search/walkthrough.md](walkthroughs/17-shader-fbx-image-search/walkthrough.md).

## SesiÃ³n 18: Perfil real de carga y render de Mario frente al hÃ©roe
- [x] Confirmado que el servidor de puerto 8088 seguÃ­a con la versiÃ³n anterior y buscaba imÃ¡genes recursivamente al listar acciones; reiniciado con el cÃ³digo actual.
- [x] Endpoints UI a 48Ã—48 px y 16 muestras: Mario **2,51 s** para acciones + **4,95 s** para render; hÃ©roe **2,54 s** + **4,54 s**.
- [x] Mario tiene 2,77Ã— los polÃ­gonos y 76 % mÃ¡s huesos; perfil detallado en [walkthroughs/18-profile-mario-vs-hero/walkthrough.md](walkthroughs/18-profile-mario-vs-hero/walkthrough.md).

## SesiÃ³n 19: Pipeline 2.5D Estilo Diablo para Mazmorras 3D Completas (FBX)
- [x] ImplementaciÃ³n de la arquitectura de renderizado pre-renderizado estilo *Diablo / Fallout* para el modelo 3D FBX (`tripo_convert_b14b0e1b...fbx`).
- [x] EliminaciÃ³n definitiva del cuello de botella de los 448 tiles de hardware 2D: la mazmorra se hornea como un mapa continuo de 512Ã—512 en 16 bits RGB555 (512 KB), preservando la fidelidad total de Blender Cycles sin pÃ©rdida de compresiÃ³n.
- [x] Blitting directo de la ventana de cÃ¡mara visible (256Ã—192) en el framebuffer a 60 FPS con menos de 0.4 ms de CPU por frame.
- [x] CÃ¡mara suave que sigue al hÃ©roe en tiempo real en coordenadas de pÃ­xel de mundo continuo.
- [x] Matriz de colisiÃ³n automÃ¡tica de 128Ã—128 (4 px / ~14 cm por celda) extraÃ­da mediante raycasting BVH vertical de la malla 3D, con deslizamiento por paredes (`wall sliding`).
- [x] Escala natural y espaciosa: pasillos amplios de 70+ px de ancho donde el hÃ©roe cabe holgadamente.
- [x] ValidaciÃ³n completa en DeSmuME headless a 60 FPS con GIF animado.
- **Evidencia:** [walkthroughs/19-modular-3d-scifi-dungeon/walkthrough.md](walkthroughs/19-modular-3d-scifi-dungeon/walkthrough.md).


## Features Abiertas y Ramas Activas (En Pausa / Backlog)

- **`feat/skeleton-collapse-fbx` â€” Colapso del Esqueleto a Pila de Huesos:**
  - **Estado:** Pausado / Prototipo resguardado en rama (`d537db3`).
  - **Objetivo:** Reemplazar la fragmentaciÃ³n aleatoria por una animaciÃ³n determinista donde el esqueleto colapsa y deja una pila de huesos estÃ¡tica en el suelo al morir.
  - **Pendiente para reanudar:** Pulido visual del render/spritesheet (el montÃ³n de huesos resultante requiere mayor claridad visual en baja resoluciÃ³n) y posterior mecÃ¡nica de reanimaciÃ³n nigromÃ¡ntica de la pila.
  - **Evidencia guardada:** `walkthroughs/skeleton-death-fbx/walkthrough.md` (preservada en la rama).

## PrÃ³ximas LÃ­neas de Trabajo
- InvocaciÃ³n de esbirros esqueletos y mecÃ¡nicas de nigromancia activa.
- ExpansiÃ³n de mazmorra procedural manteniendo el contrato dimÃ©trico y presupuestos de 60 FPS.



## SesiÃ³n 20: NavegaciÃ³n de la mazmorra FBX (validaciÃ³n parcial)
- [x] CompilaciÃ³n BlocksDS y contratos host de navegaciÃ³n/telemetrÃ­a: PASS.
- [x] La aserciÃ³n DeSmuME confirma entrada RIGHT consumida, desplazamiento del jugador y cambio de cÃ¡mara.
- [ ] La ejecuciÃ³n final de colisiÃ³n aÃºn falla al capturar la detenciÃ³n: el tramo de 50 frames seguÃ­a avanzando; el escenario se ampliÃ³ a 120 frames, pendiente de re-ejecuciÃ³n.
- [ ] OclusiÃ³n sprites/entorno y coincidencia de iluminaciÃ³n quedan pendientes; cÃ¡mara, escala y grading necesitan revisiÃ³n.
- Sin validaciÃ³n en Nintendo DS fÃ­sica. No se afirma soporte general de FBX.
- **Evidencia:** walkthroughs/fbx-navigation-repair/walkthrough.md.

## SesiÃ³n 21: Experimento de OclusiÃ³n FBX (no aceptado)
- [x] Compositor experimental de spans y contadores de llamadas, runs, pÃ­xeles copiados y ticks.
- [x] Host contract sintÃ©tico: orden delante/detrÃ¡s de pared y payload de runs comprobados.
- [ ] Falla la aserciÃ³n de alineaciÃ³n de piso: el spawn conocido (174,238) se clasifica como upper en la mÃ¡scara generada.
- [ ] Falla el presupuesto: 15â€“20 FPS, 243â€“332% de CPU y ~8.000 runs/frame; no cumple 60 FPS dual-screen con diez actores.
- [ ] El escenario aÃºn no pasa movimiento, detenciÃ³n y release en una misma ejecuciÃ³n; iluminaciÃ³n pendiente.
- Sin validaciÃ³n fÃ­sica DS ni afirmaciÃ³n de compatibilidad general FBX.
- **Evidencia:** walkthroughs/fbx-occlusion-experiment/walkthrough.md.

## SesiÃ³n 22: CorrecciÃ³n de colisiÃ³n FBX (validaciÃ³n parcial)
- [x] El generador produce una cuadrÃ­cula 128Ã—128: 1.808 celdas transitables, 150 obstÃ¡culos y 14.426 vacÃ­os; spawn seleccionado (270,290) con 3Ã—3 de despeje.
- [x] Host tests: navegaciÃ³n 5/5; contrato de oclusiÃ³n/mÃ¡scara 3/3. La prueba de mÃ¡scara verifica carga y lÃ­mites del payload, no alineaciÃ³n visual de suelo.
- [x] Escenario DeSmuME con estado real: movimiento DOWN 2,83 px; 24 frames bloqueados ante obstÃ¡culo; posiciÃ³n/cÃ¡mara estables durante espera; input liberado.
- [ ] Puerta y conectividad entre habitaciones no verificadas. Sin prueba en hardware DS.
- [ ] OclusiÃ³n experimental sigue por debajo del objetivo (15â€“20 FPS, 243â€“332% CPU observados); iluminaciÃ³n/color del jugador pendiente. No se afirma 60 FPS ni soporte FBX general.
- **Evidencia:** walkthroughs/fbx-collision-fix/walkthrough.md.


## SesiÃ³n 23: Puntos de colisiÃ³n FBX y recorte de spans
- [x] Se descarta el cruce vertical impar que queda por debajo de los pies; altura 0,05 m y tolerancia 0,015 m.
- [x] RegresiÃ³n de los nueve sondeos del jugador para (128,249), (238,309) y (250,314): footprint libre en la malla generada.
- [x] Recorrido de spans limitado al viewport con margen medido de 34 px; benchmark DeSmuME mejora de 62,4 ms a 51,9 ms de CPU media por frame (âˆ’16,9%).
- [x] ROM v4 subida y verificada en `ftp://192.168.1.151:5000/roms/nds/dungeonds.nds` (SHA-256 `E8BD107A3F649A3AD04D286EE23DB29CFB5FA6F13DB2BC3C4251B55DA390FA05`).
- [ ] Pendiente: reproducir en DeSmuME/hardware las rutas BFS a los puntos; prueba fÃ­sica DS y objetivo 60 FPS aÃºn sin validar/alcanzar.
- **Evidencia:** [walkthroughs/fbx-collision-perf-followup/walkthrough.md](walkthroughs/fbx-collision-perf-followup/walkthrough.md).
## SesiÃ³n 24: DiagnÃ³stico A/B de rendimiento FBX frente al renderer modular
- [x] Benchmark comparable de 240 frames: modular 8.36 ms CPU medio y 240/240 a 60 FPS; FBX baja de 51.53 ms a 45.84 ms tras el fast path de spans cortos; objetivo 60 FPS aÃºn no alcanzado (13/240).
- [x] El fast path evita memcpy para spans de 1â€“4 pÃ­xeles (90.7% de los spans generados) y conserva los mismos pÃ­xeles/profundidad; objetos/oclusiones bajan de 39.32 ms a 34.05 ms.
- [x] Copia software del fondo sigue en ~10.5 ms/frame; sin cambios de fÃ­sica o gameplay.
- [x] Build BlocksDS, 27 pruebas host y benchmark DeSmuME PASS. Sin validaciÃ³n en DS fÃ­sica.
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


### Seguimiento de rendimiento fÃ­sico (2026-10-10)

- Usuario informa `FPS:20 C:40 P:10` en Nintendo DSi, en reposo y al moverse. La mediciÃ³n previa de DeSmuME no predice la consola.
- `C` mide lÃ³gica+render y `P` incluye espera de VBlank+copia de presentaciÃ³n. La nueva segunda lÃ­nea muestra `F/S/B/L`: suelo, sombras, blits y lÃ³gica.
- TowerDS dibuja el framebuffer inferior directamente en buffer de VRAM con flip; esta rama compone dos buffers en RAM y copia 192 KB por frame. Es una diferencia arquitectÃ³nica observada, aÃºn no prueba de la causa.
- Rejilla conservadora 8Ã—8 evita el depth test por pÃ­xel cuando no puede existir oclusiÃ³n. Contrato de 20.000 regiones aleatorias PASS; capturas DeSmuME pre/post con 0 pÃ­xeles distintos; blit emulado âˆ’7%.
- HUD ampliado: build BlocksDS, contrato de HUD y escenario DeSmuME PASS; captura `FPS:60 C:10 P:06 / F:06 S:00 B:01 L:00`.
- Commit `086d05c`; build diagnÃ³stica `F/S/B/L` CRC `3C31A321` subida y verificada por FTP. Usuario midiÃ³ `F:38`, `S/B/L:0`; la copia del fondo es el cuello de botella fÃ­sico.
- El BG1 tileado proviene del mapa modular y su streaming estÃ¡ sin uso; no sustituye el fondo FBX. TowerDS cambia directamente el framebuffer inferior en VRAM, pero ese patrÃ³n no elimina el recorte/copiado del bitmap FBX por cÃ¡mara y pantalla.
- Ensayo: sustituir 384 llamadas DMA por lÃ­nea/frame con rÃ¡fagas ARM9 de 8 palabras (alineado) y pares halfword seguros (desalineado). Build y escenarios pasan; recorrido da las mismas coordenadas inicial/final.
- En el DeSmuME headless (modo intÃ©rprete), el candidato cae de 60 a 30 FPS y `F` mide 7 ms quieto / hasta 15 ms andando. Resultado fÃ­sico aÃºn no medido.
- Commit `749d44f`; ROM CRC `4A0B2288`, SHA-256 `269BFC72206230499B6D3DCC77EE4784160B88C65E12DD66FE29EF55B9868F4E`. FTP `192.168.1.151:5000` agotÃ³ el tiempo de conexiÃ³n a los 10 s; transferencia no confirmada, sin reintentos.


## SesiÃ³n 26: Perfilado de rutas de render del suelo FBX

- [x] El atlas BG 8bpp admite hasta 65.535 tiles porque `0xFFFF` es el ID invÃ¡lido reservado. La residencia VRAM queda limitada al viewport; la metadata `slot_for_tile` crece 4 bytes por tile Ãºnico entre las dos pantallas.
- [x] Bitmap 8bpp experimental: 240 frames DeSmuME, CPU medio 4.99 ms, `F=1.53 ms`, 240/240 a 60 FPS; el bitmap 512Ã—512 ocupa 256 KiB y deja la pantalla superior sin BG.
- [x] Prototipo FBX tileado con ring map: DeSmuME intÃ©rprete 240 frames, CPU medio 4.89 ms, `F=1.49 ms`, 239/240 a 60 FPS; escenario de paseo PASS.
- [x] Refresco de pantalla superior a 30 Hz: CPU medio 5.48 ms y `F=2.91 ms`, peor que ring map; 240/240 a 60 FPS.
- [x] La pantalla superior muestra el suelo tileado siguiendo la misma cÃ¡mara; mantiene el render de actores/sombras/HUD completo abajo.
- [x] Refinamiento genÃ©rico del ring: conserva BG 512Ã—256 y actualiza solo la ventana visible de 33Ã—25 tiles (mÃ¡ximo 825 residentes); elimina la dependencia de densidad de tiles fuera de pantalla.
- [x] Build limpia, contrato host y escenario de paseo PASS para la primera versiÃ³n del ring; ROM CRC `9CA76D62`, SHA-256 `99A42DF4891390462F4F5B0C45BEB5AED68827DE46F8D1E105471CE6140A7173`.
- [x] Perfil DeSmuME final 240/240 a 60 FPS; CPU medio 4,919 ms, `F=1,508 ms`. PrÃ¡cticamente igual al ring anterior: no demuestra la mejora en DSi.
- [x] Prueba de estrÃ©s del generador con bake 768Ã—768 y 9.217 tiles Ãºnicos (atlas 589.888 B + mapa 18.432 B); genera correctamente IDs por encima del nÃºmero de tiles residentes en VRAM.
- [x] ROM con ring genÃ©rico subida y listada por FTP (CRC `9CA76D62`); el byte a byte remoto no pudo verificarse por timeout.
- [x] CorrecciÃ³n de sincronizaciÃ³n: escrituras de BG/scroll despuÃ©s de entrar en VBlank; build y escenario PASS. Perfil 240/240 a 60 FPS, CPU medio 4,913 ms.
- [x] ROM corregida CRC `65BC36B1` y SHA-256 `0970E9163B8FF432DAB09F8AD3B4AF6DE78D90F1D8A364103639859D2411F5F4` subida y verificada por readback. Usuario confirma que la DSi va perfecta; no se recibiÃ³ lectura numÃ©rica del HUD.
- **Evidencia:** [walkthroughs/fbx-floor-render-options/walkthrough.md](walkthroughs/fbx-floor-render-options/walkthrough.md).


## SesiÃ³n 27: Pruebas de lÃ­mites del generador FBX

- [x] Prueba de integraciÃ³n con fixture 768Ã—768 y 9.216 tiles Ãºnicos; valida mapas mayores que los slots residentes de VRAM.
- [x] Escenario DeSmuME con scroll X/Y y releases PASS (5 capturas, 16 eventos; cÃ¡mara X 122â†’76, Y 170â†’150).
- [x] Corregida la paleta escasa de Pillow; el fixture de 65.536 tiles prueba el rechazo del ID centinela; suite de 20 pruebas host PASS.
- [x] RegeneraciÃ³n del atlas actual idÃ©ntica por SHA-256 al C versionado (1.007 tiles, mapa 64Ã—64).
- [x] Walkthrough actualiza el lÃ­mite real de RAM y la validaciÃ³n DSi; skill `ds-game-dev` aÃ±ade el protocolo de mediciÃ³n fÃ­sica.
- **Evidencia:** [walkthroughs/fbx-background-generator-tests/walkthrough.md](walkthroughs/fbx-background-generator-tests/walkthrough.md).

## SesiÃ³n 28: Flujo reutilizable de optimizaciÃ³n DS
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

- [x] Escenario de 512Ã—512 con colisiÃ³n dual jugador/proyectil, oclusiÃ³n de estructuras altas y personajes armonizados.
- [x] Build BlocksDS y contratos host PASS; escenario `scenarios/wh40k_showcase.json` PASS (4 capturas, 18 eventos, 3 cambios de pantalla comprobados).
- [x] ROM de 2.702.848 bytes, CRC DeSmuME `3F2A656E`, SHA-256 `B7C9599209DCF50520FF46AA6CD4EEAA0BB50878A5769F839AA42328E81991C5`; FTP cargado y nombre remoto verificado en `192.168.1.151:5000/roms/nds/dungeonds.nds`.
- [x] Primera prueba fÃ­sica del usuario: el escenario funciona en general; reportÃ³ bloqueo cerca del centro y parpadeo de lÃ­neas del Charger.
- **Evidencia:** `walkthroughs/wh40k-floor-preview/walkthrough.md`.

## Sesión 34: Cámara centrada, continuidad dual-screen y diagnóstico del Charger

- [x] Escenario `wh40k_camera_collision.json`: prueba el bloqueo contra el edificio, rodeo por el sur y avance hasta el borde este; el seguimiento de cÃ¡mara continÃºa y se limita al llegar al lÃ­mite del mapa.
- [x] Restaurados 6.056 pÃ­xeles opacos de contorno del Charger que la armonizaciÃ³n habÃ­a convertido en transparentes.
- [x] Build BlocksDS, contratos host, showcase y escenarios de colisiÃ³n/animaciÃ³n PASS; ROM 2.702.848 bytes, CRC DeSmuME `0ABEE539`, SHA-256 `90154A808F77FBAF3948B184DEF37EB6233327E1AB68254A7D7F1F874462FE8D`.
- [x] Primer intento FTP agotÃ³ el tiempo; tras la peticiÃ³n del usuario, la segunda transferencia finalizÃ³ PASS a `192.168.1.151:5000/roms/nds/dungeonds.nds`.
- [ ] Repetir la prueba en DS con esta ROM y confirmar navegaciÃ³n y Charger. Mantener rama y worktree abiertos hasta esa validaciÃ³n.
- [x] CorrecciÃ³n del encuadre dual: la pantalla superior usa `cam_y - 192`, asÃ­ que muestra los 192 px inmediatamente anteriores a la pantalla inferior; fuera de la huella del mundo el fondo es negro. La explicaciÃ³n anterior de que ambas mostraban el mismo suelo era errÃ³nea.
- [x] El generador dibuja la huella del suelo con esquinas diagonales a resoluciÃ³n de pÃ­xel; el exterior es transparente/negro y la misma huella bloquea movimiento y proyectiles. Escenario `wh40k_world_edge_panorama.json` PASS (4 capturas, borde norte y esquina noroeste).
- [x] CÃ¡mara centrada tambiÃ©n al pasar sobre el vacÃ­o: en el borde norte la escena registra `cam_y=-77` y movimiento bloqueado en el lÃ­mite real del suelo. Build BlocksDS, suite host (9 casos) y escenario DeSmuME (4 capturas, 20 eventos) PASS; ROM SHA-256 `6CD25AA05666395AC6DEBE8A6E17CF93F33888E0884EBD372D5BCD10C2E99D52`. ValidaciÃ³n en DS pendiente.
- [x] Se descartÃ³ la revisiÃ³n que repetÃ­a una muestra de baldosa en todo el fondo conectado: convertÃ­a el lienzo 512Ã—512 en suelo rectangular y hacÃ­a caminables las esquinas exteriores.
- [x] El generador mantiene transparente el fondo alrededor de la losa cuadrada proyectada como rombo; render y colisiÃ³n usan el mismo atlas/mÃ¡scara. Escenarios norte y sur PASS con movimiento bloqueado en el vacÃ­o.
- [x] Build BlocksDS, suite host y escenarios DeSmuME norte/sur PASS; ROM CRC DeSmuME `69A83C37`. Tearing de actores ya confirmado resuelto fÃ­sicamente en la DS en la prueba anterior.
- [ ] Subir y validar fÃ­sicamente la revisiÃ³n previa del perÃ­metro en DS.
- **Evidencia:** `walkthroughs/wh40k-floor-preview/walkthrough.md`.

## Sesión 35: Bake del perÃ­metro completo WH40K

- [x] La foto fÃ­sica revelÃ³ que la franja negra vertical venÃ­a del recorte de render: `ORTHO_SCALE=30` no encuadraba la losa de 50Ã—50 m.
- [x] La primera revisiÃ³n subiÃ³ `ORTHO_SCALE` a 72 y quitÃ³ el recorte, pero redujo demasiado el tamaÃ±o aparente de las baldosas; el usuario detectÃ³ correctamente esa regresiÃ³n.
- [x] Build BlocksDS PASS; 7 contratos focalizados PASS; escenarios norte y sur PASS (6 capturas en total). ROM 2.378.240 bytes, CRC `8348AD98`, SHA-256 `113355E91D490A9799F59781E77B8E517EC57E187D507E1D888D028D8D6E4DD6`.
- [x] ROM enviada por FTP a `192.168.1.151:5000/roms/nds/dungeonds.nds`; su escala visual se corrigiÃ³ en la sesiÃ³n 32.
- **Evidencia:** `walkthroughs/wh40k-floor-preview/walkthrough.md`.

## Sesión 36: Escala original WH40K y lienzo completo

- [x] Lienzo 1280Ã—768 con `ORTHO_SCALE=75` conserva los mismos 17,07 px/m que 512Ã—512 con escala 30, ahora sin recortar la losa.
- [x] ColisiÃ³n 320Ã—192 a 4 px/celda y mapa BG 160Ã—96 mantienen el borde diagonal y el vacÃ­o negro a la escala original.
- [x] Se quitÃ³ la copia RGB555 completa del mundo: el sombreado lee el color de suelo del atlas BG; la profundidad usa celdas conservadoras de 2Ã—2 para respetar los 4 MB de EWRAM.
- [x] Build BlocksDS PASS; contratos del proyecto (11 casos), oclusiÃ³n (3) y streaming del suelo (1) PASS. Escenarios DeSmuME de entrada, showcase, borde norte y borde sur PASS.
- [x] ROM 2.488.832 bytes, CRC DeSmuME `6F146AA8`, SHA-256 `817D998A7EE766902838C549563914FB5A8629366E691865EB4C77A902ABF7E5`.
- [x] Tras el timeout inicial, la ROM se subiÃ³ por FTP a `192.168.1.151:5000/roms/nds/dungeonds.nds` a peticiÃ³n del usuario.
- [ ] La prueba fÃ­sica de esta revisiÃ³n queda pendiente; DeSmuME confirma geometrÃ­a y movimiento, no la validaciÃ³n en hardware.
- **Evidencia:** `walkthroughs/wh40k-floor-preview/walkthrough.md`.

## Sesión 37: Recorrido WH40K de cuatro sectores

- [x] Se concatenaron cuatro sectores contiguos de 50 m en el eje norte-sur, manteniendo 17,07 px/m; la proyecciÃ³n ocupa 3200Ã—1920 px.
- [x] La oclusiÃ³n se prepara por ventana visible y la colisiÃ³n se empaqueta a 2 bits por celda para caber en la RAM de la DS.
- [x] Build BlocksDS PASS; contratos configurados (11) y rejilla de oclusiÃ³n (3) PASS. DeSmuME `wh40k_four_sector_walk.json`: 1100 frames, movimiento 534 px, cÃ¡mara âˆ’529 px, `blocked_moves=0`.
- [x] ROM 3.456.512 bytes, CRC DeSmuME `21C12934`, SHA-256 `47A5BD64CA7EB25FE7D2AFB87F6607164969B0EADF4E55491AAC1CF4685E92E7`.
- [x] ROM de prueba subida por FTP a `192.168.1.151:5000/roms/nds/dungeonds.nds` (3.456.512 bytes transferidos); prueba fÃ­sica pendiente.
- **Evidencia:** captura `walkthroughs/wh40k-floor-preview/assets/18_four_sector_walk.png` y escenario `scenarios/wh40k_four_sector_walk.json`.


## Sesión 38: ColisiÃ³n de edificios en sectores WH40K repetidos

- [x] Causa: el BVH tomaba los vÃ©rtices locales de cada copia y omitÃ­a `matrix_world`; los sectores repetidos quedaban con edificios visuales sin colisiÃ³n y colisiones fantasma en la coordenada fuente.
- [x] BVH separado para movimiento/proyectiles: transforma los vÃ©rtices nuevos con `p.matrix_world`; mapa de colisiÃ³n de 800Ã—480 y flags a 2 bits.
- [x] Contrato host verifica celdas bloqueadas en las cuatro bandas del mundo; los 13 contratos host configurados pasan.
- [x] Build BlocksDS PASS; escenarios `wh40k_four_sector_walk.json` y `wh40k_camera_collision.json` PASS. Contacto de edificio: `blocked_moves=811`, `moving=0`.
- [x] ROM 3.456.512 bytes, CRC DeSmuME `8BB17AC6`, SHA-256 `CE8EECDF3C64287B4639D21A6518BC3AA5E4B0C0420B5E1D7A08BAD0395ABB3C`.
- [x] ROM subida por FTP a `192.168.1.151:5000/roms/nds/dungeonds.nds` (3.456.512 bytes); falta probarla fÃ­sicamente en la DS.
- **Evidencia:** `walkthroughs/wh40k-floor-preview/assets/19_four_sector_building_collision.png` y `scenarios/wh40k_four_sector_walk.json`.

## Sesión 39: rasterizaciÃ³n volumÃ©trica de colisiones WH40K

- [x] El bake de movimiento sustituye dos consultas a alturas fijas por cuatro rayos verticales por celda 4Ã—4, cubriendo toda la altura del cuerpo del personaje.
- [x] La mÃ¡scara de proyectiles sigue usando su altura independiente.
- [x] Build BlocksDS PASS; 13 contratos host PASS. `wh40k_building_collision_contact.json`: el jugador permanece bloqueado 40 frames y luego rodea el edificio (6 capturas, 25 eventos); `wh40k_four_sector_walk.json`: `blocked_moves=807`, `moving=0`.
- [x] ROM 3.456.512 bytes, CRC DeSmuME `6239B895`, SHA-256 `7F44D40CCE0A56E360FD24CEF5C9944C9F9F39DBB6A24288941EDD8374EA2B05`.
- [x] La revisiÃ³n 35 se enviÃ³ a la DS; la prueba fÃ­sica confirmÃ³ que aÃºn se atraviesan algunas partes de edificios. La revisiÃ³n 36 amplÃ­a la cobertura de la mÃ¡scara.
- **Evidencia:** `walkthroughs/wh40k-floor-preview/assets/20_vertical_column_building_contact.png`, `assets/21_vertical_column_sector_contact.png`, `scenarios/wh40k_building_collision_contact.json` y `scenarios/wh40k_four_sector_walk.json`.

## Sesión 40: Cobertura completa de celdas de colisiÃ³n WH40K

- [x] La comparaciÃ³n confirmÃ³ que la rasterizaciÃ³n anterior solo comprobaba cuatro puntos interiores de cada celda 4Ã—4; ahora examina los 16 pÃ­xeles y mantiene el mismo formato y presupuesto de memoria.
- [x] El bake marca 802 celdas de movimiento y 12.603 celdas sÃ³lidas.
- [x] Build BlocksDS PASS; 13 contratos host PASS; escenario de contacto/rodeo PASS (6 capturas, 25 eventos).
- [x] ROM 3.456.512 bytes, CRC DeSmuME `47A5826E`, SHA-256 `32B18E3BDBBF5AE3067F4C0DBBDB7FD79A8E088CEC8232CE526F29B01393A500`.
- [ ] Subir esta revisiÃ³n y comprobar en la DS que no atraviesa partes de edificios.
- **Evidencia:** `walkthroughs/wh40k-floor-preview/assets/22_dense_building_contact.png`, `assets/23_dense_building_detour.png`, `scenarios/wh40k_building_collision_contact.json`.

## Sesión 41: alineaciÃ³n del pie visible del Charger

- [x] Los frames del Charger llegan hasta la fila 33 del canvas, 5 px debajo de `PLAYER_ANCHOR_Y=28`; los del hÃ©roe, hasta 2 px debajo. Esto explica por quÃ© el pie podÃ­a verse bajo un muro aunque el cuerpo quedase ocluido.
- [x] `draw_player()` y `draw_enemy()` alinean el pÃ­xel opaco inferior de cada frame con el ancla de suelo que comparten movimiento y profundidad.
- [x] Build BlocksDS PASS; 15 contratos host PASS; escenario `wh40k_charger_building_contact.json` PASS: la ruta queda bloqueada 40 frames y rodea el muro.
- [x] ROM 3.456.512 bytes, CRC DeSmuME `5ACE388F`, SHA-256 `9A5DD510B0B4A15B9A367151E0C06074EA886116934DB61FCD075248F67007A0`.
- [ ] Probar en la DS y recorrer otros tramos reportados; la captura actual confirma solo un contacto emulado. ROM aÃºn no subida.
- **Evidencia:** `walkthroughs/wh40k-floor-preview/assets/24_charger_ground_anchor_idle.png`, `assets/25_charger_ground_anchor_contact.png`, `scenarios/wh40k_charger_building_contact.json`, `tests/test_sprite_ground_anchor.py`.

## Sesión 42: Arena sintÃ©tica para aislar colisiÃ³n y oclusiÃ³n WH40K

- [x] Se creÃ³ una arena temporal de 1280Ã—768 px sobre el suelo WH40K, con escala original de 17,07 px/m y ocho cajas 3D programÃ¡ticas de varias orientaciones y alturas.
- [x] El proyecto temporal usa el cÃ³digo actual del motor, la cÃ¡mara y el pipeline Blender/BG/colisiÃ³n/oclusiÃ³n; reemplaza solo los props FBX y conserva intacto el mapa normal.
- [x] Input preflight y escenarios de DeSmuME para UP/RIGHT/DOWN/LEFT PASS. UP se detiene ante la caja de 1,2 m; las cajas altas de RIGHT/DOWN/LEFT no generan flags WALK y el jugador las atraviesa.
- [x] Causa offline confirmada para las cajas cerradas: el rayo WALK empieza a +1,20 m y solo recorre 1,19 m; queda dentro de cajas altas y no alcanza su cara inferior. La caja de 1,2 m sÃ­ deja celdas caminables.
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


