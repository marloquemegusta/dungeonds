# Catálogo de assets

Registro único de **todos los assets del juego**: de dónde sale cada uno, qué script lo convierte, qué usa la ROM y dónde se guarda. Cómo entra, cambia y sale un asset: §0 «Ciclo de vida». Las reglas de proceso que lo rodean (worktrees, rescate de assets al cerrar): `AGENTS.md`. Parámetros de render (resoluciones, clips, velocidades): `assets/sprites/characters/characters.json` y `TECHNICAL.md` §3; aquí no se duplican.

**Almacén:** `LFS` (en git, contenido guardado aparte por Git LFS; lo decide `.gitattributes`), `git` (normal), `derivado` (no se versiona; se regenera con el script) o `local` (solo en este disco; es una anomalía y debe resolverse).

Estado a 2026-11-19.

## 0. Ciclo de vida

Todo asset que use el juego está en este catálogo y versionado. Lo que no está aquí no existe para el proyecto.

**Dónde se guarda cada cosa:**
- **Originales** (modelos 3D de Tripo o Mixamo con sus texturas, vídeos finales): git con **Git LFS**. `.gitattributes` decide qué va a LFS (`*.fbx`, `*.glb`, `*.obj`, `*.blend`, `*.mp4` y las texturas de `assets/models/` y de las losas); basta con `git add` y `git push`. Detalle técnico: `TECHNICAL.md`, «Assets pesados: Git LFS».
- **Derivados** (FBX animados, GLB intermedios, renders del lab que se rehacen con un comando): no se versionan; los ignora `.gitignore` y se regeneran con el script que indica este catálogo.
- **Lo que lee la ROM** (`source/*.c` generados, `nitrofiles/`, paquetes de sprites, paletas): git normal, para compilar sin regenerar.
- **Lo que entra en LFS ocupa cupo para siempre** (10 GiB en la cuenta gratuita de GitHub), aunque se borre después. Por eso solo se adopta lo final.

**Etapas:**
1. **Entrada.** Todo lo descargado (zips de Tripo, packs, audio en bruto) cae en `assets/inbox/`, que git ignora. Ningún script lee de `inbox/`.
2. **Evaluación.** Las alternativas se comparan desde `inbox/` o el scratchpad (renders, rondas A/B/C). Nada de esto se versiona; la comparación queda en el walkthrough de la sesión.
3. **Adopción.** Solo cuando el usuario elige la versión que va al juego: se extrae a `assets/models/<tipo>/<pieza>/source/` (nombre de pieza y UUID de Tripo), se añade su fila a este catálogo y se commitea. Personajes y animaciones van separados: en `source/`, solo el modelo con esqueleto (accesorios en subcarpetas); en `assets/models/animations/<grupo>/<clip>.fbx`, solo esqueleto y movimiento, sin malla (de Mixamo se baja «sin piel»). El `build_<personaje>.py` los junta. El zip pasa a `assets/inbox/processed/`.
4. **Derivados.** Se generan con el script de este catálogo. Un retoque a mano de un derivado (por ejemplo, un banco roto editado en Blender) lo convierte en original: se guarda en `source/` y se registra. Así no vuelve a perderse.
5. **Sustitución.** Cuando una versión nueva sustituye a otra, la vieja se borra de la carpeta activa (sigue en el historial de git) y se apunta en §5 «Descartado» con su UUID. No se guardan variantes «por si acaso».
6. **Retirada.** Lo que sale del juego se borra y se apunta en este catálogo (qué era y su UUID). No hay carpeta de archivo: lo borrado se recupera del historial de git o de la copia completa del repo que se guarda antes de cada reescritura del historial.
7. **Limpieza del inbox.** Al cerrar la sesión que adoptó algo, y después del `git push`, se borran sus zips de `inbox/processed/`. Lo que quede suelto en `inbox/` se lista al usuario, que decide qué se borra.

**Al cerrar una sesión que toca assets:** este catálogo está al día, `git lfs ls-files` incluye los originales nuevos, `git push` sube también los datos de LFS y no quedan originales en uso solo en la carpeta principal (regla de rescate de `AGENTS.md`, «Protocolo de Sesiones»).

## 1. Mapa general

| Familia | Original (fuente) | Cómo se genera | Lo que usa la ROM | Almacén del original |
| :--- | :--- | :--- | :--- | :--- |
| Personajes | modelos 3D en `assets/models/characters/` (§2) | `tools/characters/build_*.py` (Blender) → lab con `characters.json` → `tools/generate_player_sprites_c.py` (paso `characters` y `bake` de `tools/rebuild_all.py`) | `source/player_sprite.c` | LFS (paquetes del lab en `assets/sprites/characters/`: git) |
| Retratos del bestiario | animaciones exportadas en `assets/sprites/bestiary/<anim>/` | `tools/gen_bestiary_portraits.py` | `nitrofiles/bestiary/*.bin` | git (ver §7, deuda de los `.h`) |
| Props de la catedral | `assets/models/environment/cathedral/props/` (§3) | `tools/props/prep_props.py` → `prerender_props.py` → `bake_cathedral_kit.py` | `source/strip_kit.c` | LFS (renders en `assets/environment/cathedral/props/render/`: git) |
| Suelo de la catedral | cinco losas en `assets/environment/cathedral/floor_tiles/` (§4) | `tools/floor/rombos_tripo.py` | `floor/rombos_tripo/` → `strip_kit.c` | LFS |
| Lápidas | lápidas Tripo en `props/` (§3) | `tools/catedral_editor/gen/*` (cadena en su `README.md`) | `assets/environment/cathedral/lapidas/` → `strip_kit.c` | LFS |
| Muro izquierdo | arco gótico `f450c095` en `props/` | `tools/catedral_editor/gen/wall_row_glb.py` | `muros/muro_izq_128.png` → `strip_kit.c` | LFS |
| Paleta de la catedral | renders actuales | `tools/palette/extract_palette.py` | `assets/environment/cathedral/palette/palette.json` | git (derivado versionado) |
| Arenas (mazmorra) | `assets/arenas/arenas.json` | `tools/export_arenas.py` → `bake_arena.py` | `source/arena_dungeon_01.c` | git |
| HUD | corazón sagrado 3D `assets/models/hud/sacred_heart/` | `tools/hud/prerender_hud_heart.py` → `tools/generate_hud_icons_c.py` | `source/hud_icons_gfx.c` | LFS (PNG: git) |
| Reliquias y tomos del inventario | modelos 3D en `assets/models/items/` (§6) y `assets/models/hud/sacred_heart/` | export GLB (Blender) → lab (C2) → `tools/generate_item_icons_c.py`; giros 56×56 con `tools/render_item_spin.py` | `include/inv_item_art.h` + `nitrofiles/items/*.bin` | LFS (bins en git) |
| Rayos de luz | pintados a mano, `assets/sprites/godrays/` | `source/godrays_gfx.c` (notas en `tools/godrays/README.md`) | `source/godrays_gfx.c` | git |
| Cartas de mejora | escenas reales de la ROM (`cathedral-sandbox`) | `tools/levelup_cards/capture_cards.py` | `nitrofiles/levelup/*.bin` | derivado (capturas intermedias en `assets/sprites/levelup/`, ignoradas) |
| Clips de la intro | partida real en DeSmuME | `tools/gen_intro_clips.py` | `nitrofiles/intro/*.bin` | derivado |
| Remates (ejecuciones) | clips Mixamo del inbox (patada y muerte) + modelos de los personajes | `tools/characters/ds_remate_ojo.py` (escena + GLB horneados) → `tools/lab/fast/export_scene_fast.cjs` (lab rápido) → `tools/generate_remate_sprites.py` | `nitrofiles/remate/<tipo>_d<dir>.bin` + `source/remate_sprites.c` | derivado (los FBX del inbox son dato de pose; los GLB del lab no se versionan) |
| Efectos de sonido | ElevenLabs → `assets/sfx/raw/` | recorte a mano → `assets/sfx/baked/` → `tools/bake_sfx.py` | arrays en C (`source/sfx.c`) | git |
| Música | `assets/music/*.wav` | conversión a `nitrofiles/bgm.raw` | `nitrofiles/bgm.raw` | git |
| Icono de la ROM | `assets/icon.png` | toolchain | banner de la ROM | git |
| Vídeos de redes | skill `codice-lore-video` | `render_guiones.py` | no van en la ROM | LFS (`assets/videos/*.mp4`) |
| Sonidos y citas grabadas de los vídeos | ElevenLabs (efectos y tomas elegidas por el usuario) | a mano; ver la skill | no van en la ROM | git normal (`assets/videos/sfx/`, `assets/videos/voces/`) |

## 2. Personajes: de qué sale cada sprite

Esta tabla es la única fuente de verdad de qué modelo y qué animación producen cada sprite del juego. Las rutas de modelos son relativas a `assets/models/characters/`, las de animaciones a `assets/models/animations/` y los scripts están en `tools/characters/`. La celda es el tamaño en píxeles del recuadro (`resolution`). Los parámetros de render están en `assets/sprites/characters/characters.json`.

| Sprite del juego | Entrada de `characters.json` (celda) | Modelo (UUID Tripo) | Animación | Script |
| :--- | :--- | :--- | :--- | :--- |
| `CHAR_HERO`: andar | `corazon` (40) | `corazon/source/corazon.fbx` (`f25681c0`) | `corazon/walk.fbx` | `build_corazon.py` |
| `CHAR_HERO`: cargar y disparar | `corazon_disparo` (48) | el mismo | `corazon/disparo.fbx` | `build_corazon.py` |
| `CHAR_HERO_CROUCH_WALK`: andar agachado y, en un fotograma fijo (4), agachado quieto | `corazon_agachado_andar` (40) | el mismo | `corazon/agachado_andar.fbx` (Mixamo «Crouched Walking», avance de raíz anulado y retoque procedural A2 en `build_corazon.py`: pelvis 15 u más baja, torso inclinado, 20,8 px de alto frente a 32,3 de pie) | `build_corazon.py` |
| `CHAR_CHARGER`: andar | `cireneo` (60) | `cireneo/source/…cd715dbe` + cruz `source/cruz/…ed8f6d13` | `walk/walk_normal.fbx` y `cireneo/v1_clips.fbx` | `build_cireneo_v2.py` |
| `CHAR_CHARGER`: carga | `cireneo_charge` (60) | el mismo | `cireneo/v1_clips.fbx` | `build_cireneo_v2.py` |
| `CHAR_CHARGER`: telegrafía | `cireneo_telegraph` (60) | el mismo | pose generada en el script | `build_cireneo_v2.py` |
| `CHAR_OJO`: andar | `ojo` (56) | cuerpo `ojo/source/…ed4d249d`, cabeza `ojo/source/cabeza/…5f17753f` | `walk/walk_normal.fbx` | `build_ojo.py` |
| `CHAR_OJO`: mirar y sentenciar | `ojo_look`, `ojo_sentence` (56) | el mismo | poses generadas en el script | `build_ojo.py` |
| `CHAR_EXVOTO`: andar | `exvoto` (40) | `exvoto/source/…45adc30a` | `walk/walk_normal.fbx` | `build_exvoto.py` |
| `CHAR_EXVOTO_PRAY_STAND` | `exvoto_pray_stand` (40) | el mismo | `pray/pray_standing.fbx` | `build_exvoto.py` |
| `CHAR_EXVOTO_PRAY_KNEEL` | `exvoto_pray_kneel` (40) | el mismo | `pray/pray_kneeling.fbx` | `build_exvoto.py` |
| `CHAR_EXVOTO_STAND_UP` | `exvoto_stand_up` (40) | el mismo | `pray/pray_kneel_to_stand.fbx` | `build_exvoto.py` |
| Tiers de Exvoto (rama ARPG): `exvoto_bebe`, `exvoto_parroco`, `exvoto_monja` y sus `_pray_stand`, `_pray_kneel`, `_stand_up` (40; `exvoto_parroco_stand_up` 48) | ídem | `exvoto_bebe/source/…79cc0a74`, `exvoto_parroco/source/…6fbad9bb`, `exvoto_monja/source/…269f9186` | las del Exvoto | `build_exvoto_tier.py` (brazos por dirección + giro de palma; la cabeza del Párroco sale girada, pendiente) |
| Héroe, combo de puñetazos (rama ARPG): `corazon_punch_a`, `corazon_punch_b`, `corazon_gancho` (48) | ídem | `corazon/source/corazon.fbx` | `corazon/{punch_a,punch_b,gancho}.fbx` (Mixamo «Punching», «Punching (1)», «Hook Punch»; recorte `TRIM` en `build_corazon.py`) | `build_corazon.py`; a NitroFS con `tools/generate_punch_sprites.py` |
| `CHAR_ABANDERADO`: andar | `abanderado` (60) | cuerpo `abanderado/source/…6e3a96b5`, estandarte `source/estandarte/…989b9291` | `walk/sad_walk.fbx` | `build_abanderado.py` |
| `CHAR_ABANDERADO`: señalar | `abanderado_point` (60) | el mismo | pose generada en el script | `build_abanderado.py` |
| Vídeo de lore 07 (Lope): `abanderado_derrota` (sprite 320, `assets/sprites/bestiary/abanderado_derrota/`) | el mismo cuerpo y estandarte | `animations/derrota/plant_a_plant.fbx` (Mixamo «Plant A Plant», espejado; golpes procedurales) | `build_abanderado_derrota.py` |
| Vídeo de lore 04 (Liebre): `cireneo_sincruz_triste` y `cireneo_sincruz_run` (160, `assets/sprites/bestiary/`) | Cireneo sin cruz (`cireneo/source/…cd715dbe`) | `idle/sad_idle.fbx` y `walk/fast_run.fbx` (Mixamo tal cual) | `build_cireneo_clips.py` |
| `CHAR_MONAGUILLO` | `monaguillo` (40) | `monaguillo/source/…9a55a12b` | `monaguillo/walk_pray.fbx` (andar rezando, extraído del esqueleto retirado) | `build_monaguillo.py` |
| Retratos del bestiario (rezo) | no aplica (160 px) | Corazón y Exvoto | `pray/*` | `build_corazon_pray.py`, `build_exvoto_pray.py` |
| Campanero | sin integrar (el modelo con barba está en disco; la versión sin barba `b142ae4c`, sin rig, se descartó) | campana `campanero/source/campana/…af5a0caa`, cuerpo `campanero/source/…0865ecc9` | — | sin script (solo en `LORE.md`) |

**Rigs de los originales:** todos los cuerpos van con rig de Mixamo (Tripo → Mixamo). Sin rig, como piezas sueltas: estandarte del Abanderado, campana del Campanero y cabeza del Ojo. El Monaguillo es una variante del Exvoto (monje zombi) que invoca el Abanderado. Los zips de Tripo están en `assets/inbox/processed/` del repo principal. Los FBX conservan el nombre de Tripo porque las texturas `.fbm` se buscan por él.

**Plantillas de render:** `assets/sprites/characters/skeleton/settings.json` no es un personaje del juego: lo usan como plantilla (`template`) varias entradas de `characters.json`; no se borra.

**Convención:**
- En `characters/<personaje>/source/` va solo el modelo con esqueleto, con los accesorios en subcarpetas.
- En `animations/<grupo>/<clip>.fbx` va solo esqueleto y movimiento, sin malla; de Mixamo se descarga «sin piel».
- El script `build_<personaje>.py` los junta y exporta un FBX animado por clip, `characters/<personaje>/<entrada>.fbx`. Son derivados: no se versionan.

**Escala fija por personaje (2026-11-17):**
- Cada personaje se renderiza a la escala de su animación de referencia, la de andar. El resto de sus animaciones llevan `"scaleRef": "<referencia>"` en `characters.json` y heredan dos cosas de ella:
  - El reescalado del modelo (`normScale`). El render normaliza cada FBX según la postura con que empieza la animación; sin heredarlo, una animación que empieza de rodillas sale más grande.
  - Los píxeles por metro de la cámara (`fitExtent` y `fitZoom`).
- Así el personaje mide lo mismo en todas sus animaciones y las alturas en píxeles siguen a las del modelo 3D. No se compensa nada con `fitZoom` por animación.
- El tamaño del personaje en pantalla se ajusta solo con el `fitZoom` de la referencia.
- Si una pose no cabe en la celda, el render avisa con `CROPPED`. La salida es dar a esa animación una celda mayor (`resolution`), que mantiene la escala. Así está `corazon_disparo`, a 48 px. No se encoge el personaje. El motor toma el tamaño de cada celda de su `settings.json`; el disparo del héroe tiene además su propia fila de pies (`HERO_SHOT_SPRITE_W/H` y `g_player_shot_ground_anchors` en `player_sprite.h`). Por encima de 60 px se recortaría la sombra, que en el motor mide 80×80.

### Cómo regenerar los sprites de personajes

1. **FBX animados** (solo si cambia un modelo o una animación, o faltan):
   ```
   "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b -P tools/characters/build_<personaje>.py -- <raíz del repo>
   ```
2. **Sprites y código C:** `python tools/rebuild_all.py --only characters,bake --char <entradas>`. Si la referencia no entra en la lista, se lee su escala de su `settings.json`. Sin `--char` se renderizan todos.
3. **ROM:** `python tools/rebuild_all.py --only rom`, o `build-project.ps1`.

Todo de una vez: `python tools/rebuild_all.py`. Pasos y opciones: `TECHNICAL.md` §3.

## 3. Props de la catedral (originales 3D)

Ajustes de render por pieza: `tools/props/props.json`. Cada original está extraído en `assets/models/environment/cathedral/props/<objeto>_<uuid>/` (~30 MB cada uno).

| Carpeta | Pieza del juego | Nota |
| :--- | :--- | :--- |
| `relicario_7db9333c` | `relicario` | |
| `estatua_caballero_c83faa86` | `santo` | |
| `vela_derretida_cb025b38` | `vela` | |
| `sacos_barrera_fa59a3ab` | `sacos` | |
| `columna_antigua_7b241e8d` | `columna_entera` | `columna` (base rota) salió de otro modelo Tripo del 8-nov cuyo original se perdió; queda su render. |
| `banco_gotico_c2b65edd` | `banco_entero` | `banco_roto` y `banco_volcado`: originales perdidos, quedan los renders. El volcado se hará por código; el roto, si hace falta, se regenera en Tripo con `assets/environment/cathedral/prompts.md`. |
| `arco_gotico_f450c095` | muro izquierdo (`gothic_arch`, 5 módulos) | |
| `lapida_tumba_abc4677e` (cruz), `lapida_medieval_ceaaedd5` (caballero) | cuatro estampas de lápida | Los `.glb` v2 se regeneran con `tomb_glb.py` + `lapida_ao.py`. |
| `puerta_f4a93d19`, `cofre_cerrado_efcc7983`, `cofre_abierto_dcd534cc`, `altar_cfd253e4` | `puerta`, `cofre_cerrado`, `cofre_abierto`, `altar` (rama ARPG, horneados en el kit) | Prototipo ARPG, 2026-11-20. |
| `camp_mesa_49adda99`, `camp_jergon_8cc28e31`, `camp_atril_b2e93f3e`, `camp_hoguera_701a10ac` | props del campamento (rama ARPG) | No van al kit: `tools/camp/generate_camp_gfx.py` los dibuja por software (`source/camp_props_gfx.c`), con la paleta de props y su sombra. |
| Kit de muros del campamento (`assets/environment/camp/muros_src/`: `panel_liso`, `panel_porton`, `contrafuerte`) | imágenes generadas por el usuario (2026-11-21), prompts en `assets/environment/camp/prompts_muros.md` | `python tools/camp/marco_build.py` → `nitrofiles/camp/marco_{norte,izq,der}.bin` | sprites RGB15 en NitroFS; laterales por revisar |
| Héroe con luz de hoguera, fuego, suelo y props nocturnos del campamento | lab rápido (`--light camp-fire`), lab de props, scripts propios | `tools/camp/bake_camp_hero.py`, `fuego_frames.py`, `bake_camp_arena.py`, `tools/props/props_camp_night.py` + `generate_camp_gfx.py` | `nitrofiles/camp/{hero_a0..7,hoguera_fuego,floor_tiles,*}.bin` |

## 4. Suelo de la catedral

El suelo del juego (`assets/environment/cathedral/floor/rombos_tripo/`) sale de `python tools/floor/rombos_tripo.py` con **las cinco losas** de `floor_tiles/`: `losa_a` (lisa), `losa_grieta`, `losa_rota`, `losa_cera` y `losa_sangre`. Zips de origen: `d9f88a50`, `ea230fcd`, `3f00608c`, `799f9815`, `d2e57143`. Las lápidas se encastran en ese suelo con el mismo damero.

## 5. Descartado, archivado y borrado

**Descartado** (2026-11-16, solo se guardan finales y usadas; quedan en el historial de git o en su zip): Ojo cuerpo `d54eb2c5`, cabeza `140d65e3`, `source_capucha` y `source_delgado`; Campanero sin barba; Cireneo encapuchado `b85b520c`; Cireneo v1 (`cireneo/source/`, zips `172f5fef` y `aa6eb455`; sus clips viven en `animations/cireneo/v1_clips.fbx`, verificados con diferencias < 3e-5); esqueleto zombi `9b09f817`; encapuchado blanco `f8f4ac05`; columna B `6c5015e8`; banco B `fcc73c36`. **Descartado** (2026-11-17): Mixamo «Male Crouch Pose» como pose de agachado quieto (brazos abiertos en cruz en el clip original; el quieto usa ahora un fotograma fijo del andar agachado), `animations/corazon/agachado.fbx`. **Descartado** (2026-11-18): variantes del andar agachado `a1` (torso del clip) y `a3` (más inclinado), la ronda anterior `a` y el andar sin retocar (85 % de la altura de pie, no se leía agachado); se eligió A2.

**Borrado del legado** (2026-11-17, decisión del usuario): necrón, marine espacial, cargador antiguo (también sus sprites renderizados en `assets/sprites/characters/{marine,necron,charger}`, borrados 2026-11-19), esqueleto sin textura, animaciones y armas del lab (`assets/models/archive/legacy/`), el blockout del shooter isométrico, el par de ventanas ojivales (`lancet_pair`) y el monstruo (solo local). La geometría de arenas (`assets/models/environment/arenas/`) deja de versionarse: la regeneran `make_arena_glb.py` y `export_arenas.py`. Todo lo que estaba en git sigue en el historial hasta su reescritura (pendiente); el monstruo se pierde.

**Borrado sin copia en git** (2026-11-17, decisión del usuario): maquetas A/B/C de las cartas de mejora y su `bake_cards.py`, y los corazones girando de `hud/pickup/`. Ninguno lo usaba el juego. También los restos del legado que quedaban en el disco de la carpeta principal; esos siguen en el historial.

**Borrado** (2026-11-16): `environment/dreadhollow/GLB` y `Previews` (306 MB; pack «Dreadhollow — The Cursed Kingdom» de Kareel Games, se vuelve a bajar del proveedor; en la carpeta quedan `README.md`, `ASSET_INDEX.txt`, `LICENSE.txt` y `Textures/`); `animations/rifle/aim.fbx`, `walk/walk_renqueante.fbx`, `weapons/sword/sword.glb` (sin referencias); `environment/scifi_dungeon` (68 MB, pipeline legado; los scripts `bake_scifi_dungeon.py` y afines ya no se pueden ejecutar). Todo sigue en el historial de git salvo dreadhollow.

## 6. Reliquias y Tomos (ARPG)

Modelos 3D descargados de Tripo y adoptados para el inventario ARPG (2026-11-22). Sus fuentes viven en `assets/models/items/<item>/` (LFS) y se hornean en sprites de 24×24 RGB15 con legibilidad C2 para la ROM (`include/inv_item_art.h`).

| Pieza | UUID de Tripo | Escuela / Uso | Render 24×24 | Estado |
| :--- | :--- | :--- | :--- | :--- |
| `relic_lanza` | `0d52d8fc-15de-4d38-96f4-428d929ce548` | Rayo (Reliquia base / Punta de lanza) | `s_relic_lanza_24` | Integrado en ROM |
| `relic_nudillera` | `bbb28601-f245-42a7-93b7-c5cc8f5208a7` | Ejecución (Reliquia base / Nudillera) | `s_relic_nudillera_24` | Integrado en ROM |
| `relic_calavera` | `c1f10f3e-f623-4806-9d9f-e33bd68769f8` | Levantar (Reliquia base / Cráneo votivo) | `s_relic_calavera_24` | Integrado en ROM |
| `tome_glifo` | `d5266d16-afb4-4b41-b70f-4489e4284835` | Glifo (Tomo verde) | `s_tome_glifo_24` | Integrado en ROM |
| `tome_levantar` | `6d103588-8b90-49d8-a6a3-c08fe9093cd3` | Levantar (Tomo negro) | `s_tome_levantar_24` | Integrado en ROM |
| `tome_rayo` | `3c8af05f-e6d7-48a1-bb2f-018926b464f0` | Rayo (Tomo amarillo con cruz) | `s_tome_rayo_24` | Horneado; sin uso inicial (el héroe empieza con Rayo) |

## 7. Sin registrar

En Descargas, fuera del repo: `tripo_convert_8c5b4a72` (esqueleto soldado) y `tripo_convert_f65595e4` (esqueleto con máscara antigás), del 2026-11-07. Probables conceptos del esqueleto anterior; decidir si se borran.

## 7. Anomalías abiertas

- **`.h` del bestiario versionados:** `assets/sprites/bestiary/*/nds_shadow_anchor.h` ocupan ~270 MB en git y son derivados (`TECHNICAL.md` §4.4).
- **Sin versionar, solo en la carpeta principal:** vídeos `assets/videos/lore01_{05,06,09,10}*.mp4` (el 04 final ya está en LFS), `lore01_02_…_sinvoz.mp4` y avatares `avatar_{corazon,ojo}.png`. Si son finales, se adoptan en LFS.
- **Modelos de prueba del usuario** (`archive/legacy/custom/` en la carpeta principal: mago, esqueleto muriendo y dos personajes): sin decidir; no se versionan.
- **Originales perdidos:** `columna` (base rota), `banco_roto`, `banco_volcado` (ver §3).
