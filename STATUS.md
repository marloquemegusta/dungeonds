# STATUS.md - Estado del Proyecto DungeonDS

## Hito 0: Setup de Proyecto y Pipeline Gráfico (Completado)
- [x] Repositorio Git inicializado y estructura de directorios (`source/`, `include/`, `scripts/`, `tools/`, `assets/`, `docs/`).
- [x] Skill `ds-game-dev` y scripts de toolchain automatizados (`scripts/*.ps1`) configurados.
- [x] Documentos de arquitectura y proceso (`AGENTS.md`, `DESIGN.md`, `TECHNICAL.md`, `STATUS.md`).
- [x] Pipeline de pre-renderizado de modelos 3D a spritesheets 8-direccionales con soporte in-place.

## Hito 1: Primera Demo Jugable de Mazmorra (Completado)
- [x] Biblioteca de tiles de ruinas góticas horneados desde Dreadhollow 3D.
- [x] Motor de juego en C con movimiento 8-direccional en punto fijo 8.8 y colisiones.
- [x] Compilación limpia de la ROM con Docker BlocksDS.

## Hito 2: Motor de Renderizado Dimétrico (Completado)
- [x] Proyección dimétrica real: tiles de suelo en rombo 32×`FLOOR_TILE_H` con filas escalonadas y orden de pintado por profundidad `(col+row)`.
- [x] Assets re-horneados con cámara ortográfica correcta (azimut 45°): suelos en rombo, muros/pilares/arcos con alfa y cara superior legible. Se corrigieron los muros negros de la demo anterior.
- [x] `tools/ds_look.py` como fuente única del look (elevación, rig de luces key/fill/rim, ambiente, corrección de color y escala de píxeles); entorno y personaje comparten exactamente la misma iluminación.
- [x] Contrato de anclaje único: el origen de suelo de cada sprite cae en su centro, de modo que suelo, muros, pilares y personaje se alinean con una sola regla.
- [x] Caché de suelo del tamaño del mundo; sombras de entorno y personaje pre-renderizadas desde Cycles Shadow Catcher y compuestas sobre el suelo con máscaras empaquetadas a 4 bits.
- [x] Personaje re-horneado a la escala real del mundo (modelo 1,83 m frente a muros de 2,40 m): humano, no gigante.
- [x] Dos presets de vista horneables y comparables: `e30` (2:1 clásico) y `e60` (más cenital).
- [x] ROMs limpias `dungeonds_e30.nds` y `dungeonds_e60.nds`; escenario headless en DeSmuME (`scenarios/dual_screen_ruins_test.json`) al 100% de éxito.
- [x] Walkthrough con evidencia: `walkthroughs/02-isometric-renderer/walkthrough.md`.

### Validación de sombras horneadas (e30)
- [x] 40 máscaras de objetos (10 tipos × 4 orientaciones) y 8 máscaras del personaje verificadas por `tests/test_shadow_masks.py`.
- [x] ROM `e30` compilada con BlocksDS y escenario `scenarios/integration_showcase_walk.json` ejecutado en DeSmuME headless; capturas y logs en `artifacts/baked_shadows_final/`.

## Hito 2.5: Atmósfera Gótica, Outline, Colisiones y Sincronización (Completado)
- [x] Rama `feat/dungeon-lighting-and-outline` creada y consolidada.
- [x] Iluminación gótica chiaroscuro en `tools/ds_look.py`: luz de antorcha cálida ámbar, relleno de cripta azul pizarra tenue, rim espectral y ambiente de mundo oscuro (`0.18`).
- [x] Fondo negro abisal (`VOID_COLOR = RGB15(0,0,0)`) y oscurecimiento de sombras al 63%.
- [x] Outline de legibilidad de 1 px exterior para el personaje (`#101018`) por celda de 64×64.
- [x] Sincronización exacta de zancada (1.502 m = 16.99 px): `PLAYER_SPEED = 181` y `ANIM_PERIOD = 3` (cero efecto cinta transportadora).
- [x] Colisión sub-tile física circular en pilares (0.65 m de base en vez de bloquear 3.5 m).
- [x] Orientación frontal de linternas de alma (rotaciones 180° y 90°) y llama azul espectral potenciada con shader de emisión saturada.
- [x] Banner NDS corregido a `DungeonDS: Necromancer Crypt` y limpieza de ROMs obsoletas en la SD de la consola.
- [x] Verificado en DeSmuME headless (100% PASS, 74 frames de tour) y subido por FTP a la Nintendo DS física (`dungeonds.nds`).
- [x] Walkthrough documentado en `walkthroughs/03-dungeon-atmosphere-and-outline/walkthrough.md`.

## Siguiente Hito (Hito 3): Mecánicas de Nigromancia
- [ ] Spawneo de cadáveres o invocación de esbirros esqueletos.
- [ ] Expansión de mapa procedural manteniendo el contrato de proyección/anclaje.

