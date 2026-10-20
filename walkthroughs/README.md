# Walkthroughs por Sesión

Resúmenes acumulativos y auditables de cada entrega y avance de desarrollo en `dungeonds`.

## Convención

- Una carpeta por hito o sesión atómica: `walkthroughs/<nombre-sesion>/`.
- Dentro, el resumen `walkthrough.md` y sus evidencias visuales (GIFs, capturas) en `walkthroughs/<nombre-sesion>/assets/`.
- Los assets se enlazan con rutas relativas al propio `.md` (por ejemplo `assets/foo.png` o `assets/foo.gif`).
- Estos archivos se versionan en Git para mantener el historial vivo de evolución del proyecto.

## Índice de sesiones

| # | Hito / Sesión | Carpeta | Estado |
| :---: | :--- | :--- | :--- |
| 0 | Setup de proyecto, pipeline 3D a 2D y catálogo de ruinas | [`00-project-setup-pipeline/`](00-project-setup-pipeline/walkthrough.md) | Completado |
| 1 | Primera demo interactiva: Ruinas y movimiento 8-dir en NDS | [`01-playable-ruins-prototype/`](01-playable-ruins-prototype/walkthrough.md) | En progreso |
| 2 | Motor de renderizado dimétrico, look compartido y presets e30/e60 | [`02-isometric-renderer/`](02-isometric-renderer/walkthrough.md) | Completado |
| 3 | Iluminación de mazmorra gótica y outline de legibilidad | [`03-dungeon-atmosphere-and-outline/`](03-dungeon-atmosphere-and-outline/walkthrough.md) | Completado |
| 4 | Enemigo cargador (Run.fbx) y cambio dinámico de personaje | [`04-enemy-charger-and-character-swap/`](04-enemy-charger-and-character-swap/walkthrough.md) | Completado |
| 5 | Arquitectura de rendimiento a 60 FPS y corrección de alineamiento ARM9 | [`05-arm9-alignment-and-60fps/`](05-arm9-alignment-and-60fps/walkthrough.md) | Completado |
| 6 | Corrección de colisión y profundidad (depth sorting) en pilares | [`06-pillar-collision-and-depth-alignment/`](06-pillar-collision-and-depth-alignment/walkthrough.md) | Completado |
| 7 | Integración de enemigo esqueleto (skeleton.fbx) y reorganización de assets | [`07-skeleton-enemy-and-asset-cleanup/`](07-skeleton-enemy-and-asset-cleanup/walkthrough.md) | Completado |
| 8 | Estandarización del pipeline de shaders, normales y contraste de personajes | [`08-standardize-character-shaders/`](08-standardize-character-shaders/walkthrough.md) | Completado |
| 9 | Rendimiento 60 FPS Dual-Screen, Corrección Diagonal y Multi-Entidad (10 Enemigos) | [`09-dual-screen-60fps-and-multi-entity/`](09-dual-screen-60fps-and-multi-entity/walkthrough.md) | Completado |
| 10 | Hardware Background Scrolling a 60 FPS en Dual-Screen | [`10-hardware-bg-scroll-60fps/`](10-hardware-bg-scroll-60fps/walkthrough.md) | Completado |
| 11 | Mejora de Rendimiento y Pipeline: Background Scroll Streaming, Stutter y Alineación de Pilares | [`11-perf-bg-scroll-and-rendering/`](11-perf-bg-scroll-and-rendering/walkthrough.md) | Completado |
| 12 | Prototipo de combate: Lanza ósea (A y lápiz táctil) | [12-bone-lance-prototype](12-bone-lance-prototype/walkthrough.md) | Validado en emulador |
| 13 | Escopeta de perdigones de hueso (5 astillas, <1 m) | [13-bone-shotgun-pellets](13-bone-shotgun-pellets/walkthrough.md) | Validado en emulador |
| 14 | Lanza ósea procedural (astillas sin outline y motas espectrales) | [14-bone-particle-lance](14-bone-particle-lance/walkthrough.md) | Prototipo GIF validado en emulador |
| 15 | Lanza más rápida sin azul y fragmentación al morir | [15-bone-projectile-revision](15-bone-projectile-revision/walkthrough.md) | Validado en DeSmuME |
| 16 | DS Shader Lab interactivo, selector de FBX y tamaño de sprite en píxeles | [`16-shader-lab-interactive/`](16-shader-lab-interactive/walkthrough.md) | Completado |
| 17 | Shader Lab importa FBX sin buscar sidecars .fbm | [`17-shader-fbx-image-search/`](17-shader-fbx-image-search/walkthrough.md) | Verificado con Blender |
| 18 | Diagnóstico de la carga y render lento de Mario en Shader Lab | [`18-profile-mario-vs-hero/`](18-profile-mario-vs-hero/walkthrough.md) | Medido en servidor y Blender |
| 19 | Integración Modular del Dungeon 3D (FBX) en el Motor Nintendo DS | [`19-modular-3d-scifi-dungeon/`](19-modular-3d-scifi-dungeon/walkthrough.md) | Validado en DeSmuME (GIF) |
| 23 | Reparación de puntos de colisión FBX y recorte de spans de oclusión | [`fbx-collision-perf-followup/`](fbx-collision-perf-followup/walkthrough.md) | ROM subida; validación física pendiente |
| 24 | Diagnóstico A/B de la regresión de rendimiento FBX | [`full3d-performance-gap/`](full3d-performance-gap/walkthrough.md) | Medido en DeSmuME; optimización arquitectónica pendiente |
| 25 | HUD FPS y diagnóstico de rendimiento en Nintendo DSi | [`fps-hud/`](fps-hud/walkthrough.md) | Fix ARM9 comprometido; carga FTP fallida; prueba DSi pendiente |
| 26 | Perfilado de tres rutas para el suelo FBX | [`fbx-floor-render-options/`](fbx-floor-render-options/walkthrough.md) | Ring genérico + sync VBlank; DSi confirmada cualitativamente |
| 27 | Pruebas de límites y robustez del generador FBX | [`fbx-background-generator-tests/`](fbx-background-generator-tests/walkthrough.md) | 20 pruebas host + scroll X/Y PASS; límites 768² y 2048² |
| 28 | Flujo reutilizable de optimización DS | [`ds-game-dev-performance-workflow/`](ds-game-dev-performance-workflow/walkthrough.md) | Skills local y del repositorio actualizadas; límites físicos documentados |
| 29 | Visor FBX web offline con look DungeonDS | [`web-shader-lab-parity/`](web-shader-lab-parity/walkthrough.md) | HTML autónomo; verificación sintética y estática; prueba visual pendiente |
| 30 | Corrección de animación in-place del visor web | [`web-inplace-fix/`](web-inplace-fix/walkthrough.md) | Corrección sintética verificada; prueba visual pendiente |
| 31 | In-place según la orientación de armadura FBX | [`web-inplace-axis-fix/`](web-inplace-axis-fix/walkthrough.md) | Mario y otros tres FBX: 808 poses por archivo verificadas con el mixer real |
| 32 | Paridad de iluminación del visor FBX web con Blender | [`web-blender-light-parity/`](web-blender-light-parity/walkthrough.md) | Mario: carga y render headless de ocho direcciones; cero errores JavaScript |
| 33 | Showcase del sector urbano WH40K | [`wh40k-floor-preview/`](wh40k-floor-preview/walkthrough.md) | Probado en DS; seguimiento de navegación y contorno Charger en revisión |
| 34 | Cámara centrada, continuidad dual-screen y perímetro WH40K | [`wh40k-floor-preview/`](wh40k-floor-preview/walkthrough.md) | Revisión previa del perímetro; la foto física detectó un recorte del bake |
| 35 | Bake WH40K de la losa completa 50×50 m | [`wh40k-floor-preview/`](wh40k-floor-preview/walkthrough.md) | La revisión redujo por error la escala visual; corregido en la sesión 32 |
| 36 | Escala original WH40K y lienzo completo | [`wh40k-floor-preview/`](wh40k-floor-preview/walkthrough.md) | ROM subida por FTP; prueba física pendiente |
| 37 | Recorrido WH40K de cuatro sectores | [`wh40k-floor-preview/`](wh40k-floor-preview/walkthrough.md) | El retest detectó colisiones ausentes en los edificios repetidos |
| 38 | Colisión de edificios en sectores WH40K repetidos | [`wh40k-floor-preview/`](wh40k-floor-preview/walkthrough.md) | Build, contratos host y escenario de contacto PASS; ROM subida, prueba física pendiente |
| 39 | Rasterización volumétrica de colisiones WH40K | [`wh40k-floor-preview/`](wh40k-floor-preview/walkthrough.md) | Build, contratos host y contacto/rodeo PASS; ROM nueva sin subir, prueba física pendiente |
| 40 | Cobertura completa de celdas de colisión WH40K | [`wh40k-floor-preview/`](wh40k-floor-preview/walkthrough.md) | Build, contratos host y contacto/rodeo PASS; ROM sin subir, prueba física pendiente |
| 41 | Alineación de pies del Charger con el ancla de colisión | [`wh40k-floor-preview/`](wh40k-floor-preview/walkthrough.md) | Build, 15 contratos host y contacto Charger PASS; comprobar otros tramos y DS física |
| 42 | Arena sintética para aislar colisión y oclusión WH40K | [`wh40k-collision-arena-test/`](wh40k-collision-arena-test/walkthrough.md) | Build y cuatro probes DeSmuME PASS; bake offline no asigna WALK a muros altos; ROM sin subir |
| 43 | Oclusión exacta de catedral y 60 FPS bloqueados | [`wh40k-floor-preview/`](wh40k-floor-preview/walkthrough.md) | Validado en NDS física; 60 FPS locked, optimización ARM9 (9 ms CPU), oclusión exacta sin sangrado |
| 44 | Mazmorra Completa FBX: Despeje de Puertas, Oclusión y 60 FPS | [`scifi-dungeon-tripo/`](scifi-dungeon-tripo/walkthrough.md) | Completado (60 FPS Locked, 36 tests PASS, cruce de arcos verificado en DeSmuME) |
| 45 | Iluminación de Antorcha 3D Dinámica Suave, Merge Continuo y 60 FPS Locked | [`fog-and-visibility/`](fog-and-visibility/walkthrough.md) | Completado (60 FPS Locked en los 5 hitos, oscurecimiento proporcional continuo en DTCM, oclusiones 3D BVH estilo Doom, cero bloques 8x8 en DeSmuME) |
| 46 | Sombreado Atmosférico de Antorcha Continuo, Paleta Ámbar Perceptiva y 60 FPS Locked | [`19-smooth-torch-shading/`](19-smooth-torch-shading/walkthrough.md) | Completado (60 FPS Locked, 80px smoothstep falloff, paleta DTCM perceptual ámbar, eliminación del efecto binario) |
| 47 | Lab 3JS: paridad funcional de sprites | [`js-lab-sprite-parity/`](js-lab-sprite-parity/walkthrough.md) | Ocho direcciones y paquete de sprites verificados en Chromium headless; Cycles no replicado |
| 48 | Un solo control de tamaño para el lab 3JS | [`js-lab-single-size-control/`](js-lab-single-size-control/walkthrough.md) | UI revisada en Chromium headless; ajuste con FBX pendiente |
| 49 | Resultados de sprites por encima del visor 3D | [`js-lab-results-above-preview/`](js-lab-results-above-preview/walkthrough.md) | Orden y altura del visor revisados en Chromium headless |
| 50 | Eliminar el slider «Escala modelo» del lab 3JS | [`remove-model-scale-control/`](remove-model-scale-control/walkthrough.md) | Control eliminado; normalización y tamaño del sprite verificados en Chromium headless |
| 51 | Comparación visual del lab 3JS y Blender | [`lab3js-vs-blender/`](lab3js-vs-blender/walkthrough.md) | GIFs del mismo FBX y clip; Blender llena más la celda y resulta más legible |
| 52 | Tamaño visible del sprite alineado con Blender en 3JS | [`lab3js-sprite-size-fit/`](lab3js-sprite-size-fit/walkthrough.md) | Run.fbx a 48×48: caja alfa media 36×36, frente a 21×21 antes; escala proporcional validada a 32×32 |
| 53 | Comparativa Blender visible en el walkthrough del ajuste 3JS | [`lab3js-sprite-size-fit/`](lab3js-sprite-size-fit/walkthrough.md) | Comparativa visual 3JS/Blender añadida junto a la evidencia del arreglo de encuadre |
| 54 | Paridad fidedigna 3JS vs Blender (cámara ortográfica, PBR, luces PI y Blackman-Harris 4x) | [`lab3js-blender-parity/`](lab3js-blender-parity/walkthrough.md) | IoU de silueta pasa de 27.5% a 80.9%, direcciones 100% coincidentes, luminancia y PBR alineados con Cycles |
| 55 | Laboratorio Web Offline de Ensamblaje de Armas, Retargeting e IK a `.FBX` Binario | [`fbx-weapon-anim-lab/`](fbx-weapon-anim-lab/walkthrough.md) | Completado (Splicer FBX 7400 lossless, Auto-PCA + IK 2 manos, 10 anims + 5 armas, verificado en Chromium headless y FBX-Web-Renderer) |
| 56 | Corrección de centrado multimodelo en Three.js (Mario, Henar, Wizard, Necron) | [`lab3js-centering-fix/`](lab3js-centering-fix/walkthrough.md) | Completado (IoU Mario sube de 12.5% a 94.2%, Wizard 94.9%, Henar 95.6%, Necron centrado en 23.5px, órbita de 15px eliminada) |
| 57 | Correcciones de animación, retargeting e IK de armas | [`weapon-anim-lab-fixes/`](weapon-anim-lab-fixes/walkthrough.md) | 11 clips únicos; duplicado Slash/JumpHit eliminado; ambos híbridos exportados/reimportados con shotgun y sniper; 13 mapas del sniper preservados |
| 58 | Reorganización integral de assets 3D, sprites y render de mazmorra Three.js | [`asset-reorganization/`](asset-reorganization/walkthrough.md) | Catálogo limpio en assets/models/ y assets/sprites/; archive/ para históricos; bake de mazmorra con antorcha cálida y contraste 1.50 |
| 59 | Rediseño Integral FBX-to-Sprite Lab, Renderizador 3D de Mapas y Simulador NDS | [`fbx-sprite-map-lab/`](fbx-sprite-map-lab/walkthrough.md) | Completado (100vh zero-scroll, 8 dirs strip, visor 3D, simulador dual-screen, exportador de mapa/sprite y paridad Blender) |
| 60 | Refinamiento a 3 Columnas, Soporte Multi-Material FBX/GLB, Auto-Framing y Grounding | [`fbx-sprite-map-lab/`](fbx-sprite-map-lab/walkthrough.md) | Completado (Layout 3 columnas 330/430/1fr, GLB loader multi-material, auto-framing mapa, nivelación por histograma de suelo, anclaje Y=0, paridad de luz, cero ghosting, verificado en Playwright headless) |
| 61 | Grid 2D de Walkability y Motor de Colisiones Físicas para Mapas 3D en Simulador NDS | [`fbx-sprite-map-lab/`](fbx-sprite-map-lab/walkthrough.md) | Completado (Extracción de grid 2D desde mallas 3D, proyecciones exactas 2D/3D, auto-spawn en suelo transitable sin muros, colisión y sliding en tiempo real con WASD/drag, verificado en Playwright headless) |
| 62 | Sincronización Automática de Zancada (Stride Preview) y Eliminación de Foot Sliding en Simulador NDS | [`fix-lab-stride-preview/`](fix-lab-stride-preview/walkthrough.md) | Completado (Extracción de zancada 3D vía root motion / foot bones / fallback invariante, sincronización milimétrica drag/teclado en NDS canvas, override #stride3d, test Playwright headless) |
| 63 | Exportación Completa de Sombras, Anchor y Datos de Mapa (Colisión/Oclusión) | [`feat-lab-shadow-anchor-export/`](feat-lab-shadow-anchor-export/walkthrough.md) | Completado (Anchor global y dirGroundAnchors/dirBounds 8 dirs, atlas de sombras 768x96 y máscaras NDS 4-bit 4608 bytes, header C NDS, colisión/oclusión >0.65m en exportMapPackage, verificado en Playwright headless) |



- [Reparación de navegación de la mazmorra FBX](fbx-navigation-repair/walkthrough.md) — conversión y colisión para la escena FBX; incluye escenarios con estado real y límites de validación.
- [Experimento de oclusión para la mazmorra FBX](fbx-occlusion-experiment/walkthrough.md) — prototipo de spans de profundidad; la verificación de máscara y el presupuesto de rendimiento siguen fallando.

- [FBX collision grid and wall-stop check](fbx-collision-fix/walkthrough.md) — host tests and state-backed DeSmuME wall-stop scenario pass; doorway connectivity remains unverified.
