# TECHNICAL.md - Especificación Técnica y Arquitectura

## 1. Plataforma y Toolchain NDS
- **Consola:** Nintendo DS (ARM946E-S @ 67 MHz para lógica/render, ARM7TDMI @ 33 MHz para audio/input).
- **Aritmética:** Sin FPU hardware. Todo cálculo físico o posicional se realiza en punto fijo entero (`int32_t`, 8.8 o 12.12).
- **Toolchain:** BlocksDS (`skylyrac/blocksds:slim-latest`) vía Docker (`scripts/build-project.ps1`).
- **Emulación determinista:** DeSmuME headless sobre WSL2 (`scripts/run-scenario.ps1`).

## 2. Presupuestos Hardware de Nintendo DS
- **RAM Principal:** 4 MB.
- **Hardware 2D (OAM):** 128 entradas máximas de sprites por hardware.
- **Resolución nativa:** 256×192 píxeles por pantalla.

## 3. Pipeline de Assets
- **Fuente de verdad visual:** `tools/ds_look.py` define elevación, escala de píxel, cámaras y anclas compartidas por entorno y personaje.
- **Horneado:** `tools/bake_dungeon_iso.py` crea suelo y objetos en cuatro rotaciones; `tools/bake_player.py` crea animaciones en ocho direcciones. Blender es sólo tiempo de edición: no forma parte del runtime.
- **Orientación:** cada segmento de pared/arco/columna usa el sprite horneado para su dirección de mundo. Se hornean las cuatro rotaciones explícitamente.
- **Ancla:** el origen de suelo `(0,0,0)` se proyecta al centro de la celda del canvas. El personaje comparte el ancla de suelo; se planta midiendo la geometría evaluada, no suponiendo que el origen FBX coincide con la suela.
- **Sombras horneadas:** cada orientación de objeto tiene un pase Cycles Shadow Catcher de 128×128; el conversor toma el recorte central 96×96. El jugador tiene una celda 96×96 por dirección, muestreada desde una pose plantada de referencia. El pase se guarda como RGB de luminancia: alfa no codifica cobertura.
- **Máscara:** `tools/shadow_masks.py` estima el nivel iluminado a partir de las esquinas y convierte la reducción de luminancia a cobertura. El conversor debe rechazar pases sin contraste/fondo identificables.
- **Runtime NDS:** cobertura cuantizada a 4 bits (dos píxeles por byte) con límites `[x,y,w,h]`; se oscurece sólo el suelo subyacente válido, nunca `VOID_COLOR`. Orden por frame: suelo → sombras → sprites. No sintetizar elipses/siluetas de sombra por código.
- **Presupuesto:** no guardar máscaras como bytes completos ni usar las dimensiones de horneado completas en C: el primer intento excedía EWRAM. El recorte y empaquetado son parte del contrato de memoria.
- **Verificación:** `python tests/test_shadow_masks.py -v`, conversión del preset, compilación con `scripts/build-project.ps1` y escenario/capturas con `scripts/run-scenario.ps1`. La prueba actual cubre máscaras `e30`; no implica que `e60` se haya regenerado o validado.

### 3.1. Estandarización de Shaders y Modelos 3D para Sprites NDS
- **Manifiesto de perfiles:** `tools/character_profiles.json` define de forma declarativa y desacoplada las características de horneado para cada modelo.
- **Normal Maps en NDS (Atenuación obligatoria):** A resolución nativa de $256\times 192$, relieves normales al 100% generan micro-ruido y parpadeo (*shimmering*). El estándar exige atenuar su influencia al 30%-40% (`normal_strength: 0.3 - 0.4`).
- **Fattening / Displace Modifier:** Mallas anatómicas finas (costillas, extremidades esqueléticas < 2 px de proyección) sufren desconexión de vóxeles y píxeles huérfanos. Se compensan paramétricamente con `DISPLACE` (`strength: 0.12`).
- **Ambient Occlusion con ColorRamp de Cavidad:** Modelos sin mapas de textura PBR emplean sombreado procedural anatómico complementado con Cycles AO agresivo (ramp con parada negra en 0.30) para sumergir cavidades y órbitas en penumbra gótica.
- **Grading 2D unificado (PIL):** Los sprites horneados de personaje y entorno pasan por el post-proceso central de `tools/ds_look.py` (Contraste 1.24, Brillo 0.98, Saturación 1.24, y outline de 1 px solidificado sin halos de transparencia sub-umbral).

### 3.2. Efectos Procedurales en Runtime
- La lanza ósea no usa spritesheets ni outlines: rasteriza una astilla de píxeles estrecha y puntiaguda, orientada por su velocidad fija.
- Las motas del proyectil salen de un pool de 32 partículas; cada una usa posición y deriva 8.8, semilla por proyectil, tonos de hueso y 4–7 frames de vida. La velocidad de la salva es 8 px/frame en punto fijo y conserva el abanico anterior.
- Al morir un enemigo, seis parches de 4×4 copian sus colores BGR555 reales a un pool de 48 fragmentos. Posición/velocidad planar y altura usan 8.8; la gravedad frena el arco y cada parche conserva su color durante 28–35 frames.
- Los fragmentos entran en el orden de profundidad del render y dibujan una sombra puntual en el suelo. El dibujado escribe directamente en BGR555; no instancia modelos 3D ni consume entradas OAM.

### 3.3. Pipeline de Oclusión 2.5D y Presupuesto de Rendimiento en ARM9
- **Arquitectura de Profundidad Continua vs Capas Hardware:** En perspectiva dimétrica/isométrica con estructuras altas continuas (muros, contrafuertes góticos), las capas de fondo fijas de hardware (BG0/BG1) son insuficientes: el personaje debe ocluirse al norte del muro pero mostrarse por delante al pisar el sur de su base. El motor utiliza un búfer de profundidad horizontal por tramos (`s_occlusion_depth`, resolución 128×96 celdas, 16 bits con signo).
- **Regla Crítica de EWRAM (Prohibición de loops bit a bit):** La memoria principal EWRAM (4 MB) en Nintendo DS tiene bus estrecho y latencia de acceso con wait states. Prohibido terminantemente ejecutar bucles horizontales que realicen operaciones bit a bit no alineadas (`|= (1u << (index & 7))`) por píxel individual: un bitmask de pantalla completa bajo este patrón consume 12–15 ms por frame. Toda máscara debe procesarse por palabras alineadas (32 bits) o inferirse directamente del mapa de profundidad (`s_occlusion_depth >= 0`).
- **Compilación Obligatoria en Modo ARM 32-bit:** Por defecto BlocksDS compila código ARM9 en Thumb-1 (16-bit). Las funciones críticas de manipulación de memoria y rasterizado (`build_occlusion_depth_map`, `blit_stride`, `draw_shadow_mask`) deben declararse explícitamente con `__attribute__((target("arm"), optimize("O3"), noinline))` para aprovechar instrucciones nativas de 32 bits (`LDRH`/`STRH`, `STMIA`) y evitar el estrangulamiento de registros.
- **Acceso Biseccional por Tramos Ordenados:** Las tablas de tramos de oclusión horneados (`g_dungeon_occlusion_runs`) se ordenan monótonamente por coordenada Y. El arranque de escaneo de cada segmento visible se resuelve mediante búsqueda binaria (`find_first_occlusion_run()`), reduciendo el coste de búsqueda de $O(N)$ (~4.400 comparaciones lineales) a $O(\log N)$ (máximo 12 comparaciones).
- **Prohibición de Paddings Fantasma:** Queda terminantemente prohibido aplicar márgenes de celda arbitrarios a las máscaras (`OCCLUSION_DEPTH_PAD_CELLS = 0`). Todo padding artificial crea volúmenes invisibles que recortan al personaje en el aire antes de tocar las siluetas arquitectónicas reales.
