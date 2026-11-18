# Catálogo de assets

Registro único de **todos los assets del juego**: de dónde sale cada uno, qué script lo convierte, qué usa la ROM y dónde se guarda. Cómo entra, cambia y sale un asset: `AGENTS.md`, «Ciclo de vida de los assets». Parámetros de render (resoluciones, clips, velocidades): `assets/sprites/characters/characters.json` y `TECHNICAL.md` §3; aquí no se duplican.

**Almacén:** `LFS` (en git, contenido guardado aparte por Git LFS; lo decide `.gitattributes`), `git` (normal), `derivado` (no se versiona; se regenera con el script) o `local` (solo en este disco; es una anomalía y debe resolverse).

Estado a 2026-11-17.

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
| Arenas (mazmorra) | `assets/arenas/arenas.json` | `tools/export_arenas.py` → `bake_arena.py` | `source/arena_0N.c` | git |
| HUD | corazón sagrado 3D `assets/models/hud/sacred_heart/` | `tools/hud/prerender_hud_heart.py` → `tools/generate_hud_icons_c.py` | `source/hud_icons_gfx.c` | LFS (PNG: git) |
| Rayos de luz | pintados a mano, `assets/sprites/godrays/` | `source/godrays_gfx.c` (notas en `tools/godrays/README.md`) | `source/godrays_gfx.c` | git |
| Cartas de mejora | escenas reales de la ROM (`cathedral-sandbox`) | `tools/levelup_cards/capture_cards.py` | `nitrofiles/levelup/*.bin` | derivado (capturas intermedias en `assets/sprites/levelup/`, ignoradas) |
| Clips de la intro | partida real en DeSmuME | `tools/gen_intro_clips.py` | `nitrofiles/intro/*.bin` | derivado |
| Efectos de sonido | ElevenLabs → `assets/sfx/raw/` | recorte a mano → `assets/sfx/baked/` → `tools/bake_sfx.py` | arrays en C (`source/sfx.c`) | git |
| Música | `assets/music/*.wav` | conversión a `nitrofiles/bgm.raw` | `nitrofiles/bgm.raw` | git |
| Icono de la ROM | `assets/icon.png` | toolchain | banner de la ROM | git |
| Vídeos de redes | skill `codice-lore-video` | `render_guiones.py` | no van en la ROM | LFS (`assets/videos/*.mp4`) |

## 2. Personajes: de qué sale cada sprite

Esta tabla es la única fuente de verdad de qué modelo y qué animación producen cada sprite del juego. Las rutas de modelos son relativas a `assets/models/characters/`, las de animaciones a `assets/models/animations/` y los scripts están en `tools/characters/`. La celda es el tamaño en píxeles del recuadro (`resolution`). Los parámetros de render están en `assets/sprites/characters/characters.json`.

| Sprite del juego | Entrada de `characters.json` (celda) | Modelo (UUID Tripo) | Animación | Script |
| :--- | :--- | :--- | :--- | :--- |
| `CHAR_HERO`: andar | `corazon` (40) | `corazon/source/corazon.fbx` (`f25681c0`) | `corazon/walk.fbx` | `build_corazon.py` |
| `CHAR_HERO`: cargar y disparar | `corazon_disparo` (40) | el mismo | `corazon/disparo.fbx` | `build_corazon.py` |
| `CHAR_HERO_CROUCH_WALK`: andar agachado y, en un fotograma fijo (7), agachado quieto | `corazon_agachado_andar` (48) | el mismo | `corazon/agachado_andar.fbx` (Mixamo «Crouched Walking», avance de raíz anulado en `build_corazon.py`) | `build_corazon.py` |
| `CHAR_CHARGER`: andar | `cireneo` (60) | `cireneo/source/…cd715dbe` + cruz `source/cruz/…ed8f6d13` | `walk/walk_normal.fbx` y `cireneo/v1_clips.fbx` | `build_cireneo_v2.py` |
| `CHAR_CHARGER`: carga | `cireneo_charge` (60) | el mismo | `cireneo/v1_clips.fbx` | `build_cireneo_v2.py` |
| `CHAR_CHARGER`: telegrafía | `cireneo_telegraph` (60) | el mismo | pose generada en el script | `build_cireneo_v2.py` |
| `CHAR_OJO`: andar | `ojo` (56) | cuerpo `ojo/source/…ed4d249d`, cabeza `ojo/source/cabeza/…5f17753f` | `walk/walk_normal.fbx` | `build_ojo.py` |
| `CHAR_OJO`: mirar y sentenciar | `ojo_look`, `ojo_sentence` (56) | el mismo | poses generadas en el script | `build_ojo.py` |
| `CHAR_EXVOTO`: andar | `exvoto` (40) | `exvoto/source/…45adc30a` | `walk/walk_normal.fbx` | `build_exvoto.py` |
| `CHAR_EXVOTO_PRAY_STAND` | `exvoto_pray_stand` (40) | el mismo | `pray/pray_standing.fbx` | `build_exvoto.py` |
| `CHAR_EXVOTO_PRAY_KNEEL` | `exvoto_pray_kneel` (40) | el mismo | `pray/pray_kneeling.fbx` | `build_exvoto.py` |
| `CHAR_EXVOTO_STAND_UP` | `exvoto_stand_up` (48) | el mismo | `pray/pray_kneel_to_stand.fbx` | `build_exvoto.py` |
| `CHAR_ABANDERADO`: andar | `abanderado` (60) | cuerpo `abanderado/source/…6e3a96b5`, estandarte `source/estandarte/…989b9291` | `walk/sad_walk.fbx` | `build_abanderado.py` |
| `CHAR_ABANDERADO`: señalar | `abanderado_point` (60) | el mismo | pose generada en el script | `build_abanderado.py` |
| `CHAR_MONAGUILLO` | `monaguillo` (40) | `monaguillo/source/…9a55a12b` | `monaguillo/walk_pray.fbx` (andar rezando, extraído del esqueleto retirado) | `build_monaguillo.py` |
| Retratos del bestiario (rezo) | no aplica (160 px) | Corazón y Exvoto | `pray/*` | `build_corazon_pray.py`, `build_exvoto_pray.py` |
| Campanero | sin integrar | campana `campanero/source/campana/…af5a0caa`, cuerpo `campanero/source/…0865ecc9` | — | sin script (solo en `LORE.md`) |

**Convención:**
- En `characters/<personaje>/source/` va solo el modelo con esqueleto, con los accesorios en subcarpetas.
- En `animations/<grupo>/<clip>.fbx` va solo esqueleto y movimiento, sin malla; de Mixamo se descarga «sin piel».
- El script `build_<personaje>.py` los junta y exporta un FBX animado por clip, `characters/<personaje>/<entrada>.fbx`. Son derivados: no se versionan.

**Escala fija por personaje (2026-11-17):**
- Cada personaje se renderiza a unos píxeles por metro fijos, los de su animación de referencia (la de andar). El resto de sus animaciones llevan `"scaleRef": "<referencia>"` en `characters.json` y heredan esa escala, así que el personaje no cambia de tamaño al cambiar de animación.
- No se compensa con `fitZoom` por animación.
- Si una pose no cabe en la celda, esa animación lleva una celda mayor (`resolution`) y mantiene la escala; así está `exvoto_stand_up`, a 48 px. Cuando una pose se sale, el render avisa con `CROPPED`. La celda puede llegar hasta 60 px: por encima, la sombra (de 80×80 en el motor) se recortaría.

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

## 4. Suelo de la catedral

El suelo del juego (`assets/environment/cathedral/floor/rombos_tripo/`) sale de `python tools/floor/rombos_tripo.py` con **las cinco losas** de `floor_tiles/`: `losa_a` (lisa), `losa_grieta`, `losa_rota`, `losa_cera` y `losa_sangre`. Zips de origen: `d9f88a50`, `ea230fcd`, `3f00608c`, `799f9815`, `d2e57143`. Las lápidas se encastran en ese suelo con el mismo damero.

## 5. Descartado, archivado y borrado

**Descartado** (2026-11-16, solo se guardan finales y usadas; quedan en el historial de git o en su zip): Ojo cuerpo `d54eb2c5`, cabeza `140d65e3`, `source_capucha` y `source_delgado`; Campanero sin barba; Cireneo encapuchado `b85b520c`; Cireneo v1 (`cireneo/source/`, zips `172f5fef` y `aa6eb455`; sus clips viven en `animations/cireneo/v1_clips.fbx`, verificados con diferencias < 3e-5); esqueleto zombi `9b09f817`; encapuchado blanco `f8f4ac05`; columna B `6c5015e8`; banco B `fcc73c36`. **Descartado** (2026-11-17): Mixamo «Male Crouch Pose» como pose de agachado quieto (brazos abiertos en cruz en el clip original; el quieto usa ahora un fotograma fijo del andar agachado), `animations/corazon/agachado.fbx`.

**Borrado del legado** (2026-11-17, decisión del usuario): necrón, marine espacial, cargador antiguo, esqueleto sin textura, animaciones y armas del lab (`assets/models/archive/legacy/`), el blockout del shooter isométrico, el par de ventanas ojivales (`lancet_pair`) y el monstruo (solo local). La geometría de arenas (`assets/models/environment/arenas/`) deja de versionarse: la regeneran `make_arena_glb.py` y `export_arenas.py`. Todo lo que estaba en git sigue en el historial hasta su reescritura (pendiente); el monstruo se pierde.

**Borrado sin copia en git** (2026-11-17, decisión del usuario): maquetas A/B/C de las cartas de mejora y su `bake_cards.py`, y los corazones girando de `hud/pickup/`. Ninguno lo usaba el juego. También los restos del legado que quedaban en el disco de la carpeta principal; esos siguen en el historial.

**Borrado** (2026-11-16): `environment/dreadhollow/GLB` y `Previews` (306 MB; pack «Dreadhollow — The Cursed Kingdom» de Kareel Games, se vuelve a bajar del proveedor); `animations/rifle/aim.fbx`, `walk/walk_renqueante.fbx`, `weapons/sword/sword.glb` (sin referencias); `environment/scifi_dungeon` (68 MB, pipeline legado; los scripts `bake_scifi_dungeon.py` y afines ya no se pueden ejecutar). Todo sigue en el historial de git salvo dreadhollow.

## 6. Sin registrar

En Descargas, fuera del repo: `tripo_convert_8c5b4a72` (esqueleto soldado) y `tripo_convert_f65595e4` (esqueleto con máscara antigás), del 2026-11-07. Probables conceptos del esqueleto anterior; decidir si se borran.

## 7. Anomalías abiertas

- **`.h` del bestiario versionados:** `assets/sprites/bestiary/*/nds_shadow_anchor.h` ocupan ~270 MB en git y son derivados (`TECHNICAL.md` §4.4).
- **Sin versionar, solo en la carpeta principal:** vídeos `assets/videos/lore01_{04..10}*.mp4`, `lore01_02_…_sinvoz.mp4` y avatares `avatar_{corazon,ojo}.png`. Si son finales, se adoptan en LFS.
- **Modelos de prueba del usuario** (`archive/legacy/custom/` en la carpeta principal: mago, esqueleto muriendo y dos personajes): sin decidir; no se versionan.
- **Originales perdidos:** `columna` (base rota), `banco_roto`, `banco_volcado` (ver §3).
