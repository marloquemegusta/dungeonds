# AGENTS.md - Reglas de Operación y Roles de Agente

## Taxonomía Documental

El repositorio cuenta con fuentes de verdad canónicas sin duplicación:

| Documento | Ámbito | Contenido |
| :--- | :--- | :--- |
| `DESIGN.md` | Producto y Arte | Visión de juego, controles, mecánicas, dirección visual y decisiones abiertas. |
| `LORE.md` | Lore | Biblia del mundo: eje temático, nombres, lugares, cronología y reglas de escritura. Todo texto de lore (Códice, vídeos) se escribe contra ella. |
| `DESIGN-ARCHIVE.md` | Historia del diseño | Texto retirado de `DESIGN.md` (v0.1, v0.2, franja infinita, marea, gemas). No es fuente de verdad; se consulta solo por el porqué de una decisión pasada. |
| `TECHNICAL.md` | Arquitectura C / NDS | Toolchain, presupuestos, pipeline de assets y render, dependencias de host y deuda técnica. |
| `AGENTS.md` | Proceso y Reglas | Protocolo de trabajo, workflow de desarrollo para Nintendo DS y verificación de cambios. |
| `STATUS.md` | Estado y Registro | Estado actual para retomar el trabajo y entregas recientes verificadas. Lo anterior a 2026-11-17 está en `STATUS-ARCHIVE.md`. |
| `assets/MANIFEST.md` | Catálogo de assets | Qué asset alimenta qué parte del juego, con qué script se genera y dónde se guarda. Ciclo de vida de los assets: su §0. |
| `walkthroughs/` | Documentación por sesión | Un `walkthrough.md` por entrega, con su evidencia en `assets/`. Índice en `walkthroughs/README.md`. |
| `LEAN-CTX.md` | Herramienta | Reglas de la herramienta lean-ctx; no es documentación del juego. |
| `BENCHMARK.md` y `bench/` | Proyecto de delegación | Banco de pruebas de modelos delegados; no es documentación del juego (el usuario decidirá si se archiva). |
| Skill compartida `ds-game-dev` | `C:\codexlocal\skills\agentic-ds-dev` | Flujo genérico del toolchain NDS (Docker + DeSmuME + FTP). Vive fuera del repo y no se debe copiar aquí. |

Si una regla o cifra aparece en dos documentos, uno de ellos sobra: dejarla en su fuente canónica y referenciarla desde el otro.

---

## Reglas del Toolchain y Ejecución

1. **Sin comandos interactivos del toolchain al usuario**: compilación, tests, emulación headless y subida a la DS se ejecutan con los scripts de la skill (`build-project.ps1`, `check-toolchain.ps1`, `run-scenario.ps1`, `run-scenarios.ps1`, `run-host-tests.ps1`, `upload-rom.ps1`, `fetch-device-log.ps1`), invocados desde `C:\codexlocal\skills\agentic-ds-dev\scripts\` con `powershell -NonInteractive -ExecutionPolicy Bypass -File ...` y `-ProjectPath <ruta del worktree>` (así ningún parámetro faltante deja el proceso colgado esperando teclado). Si Docker Desktop no está arrancado, arrancarlo y esperar con una condición (no con `sleep` fijo). Los arreglos genéricos del toolchain se hacen en el repo de la skill, en su propia rama, nunca parcheados aquí.
2. **Nintendo DS es plataforma sin FPU**: prohibido `float` o `double` en código de simulación o juego en tiempo de ejecución (lo vigila `tests/test_guardrails.py`). Física y movimiento en punto fijo (`int32_t` con 8.8 o 12.12); la ARM9 tiene divisor y raíz por hardware (`div32`, `sqrt32`): evitar `/` y `%` de C en bucles calientes.
3. **Presupuesto estricto de memoria** (OAM de 128 entradas, 4 MB de RAM): cifras de uso y arquitectura de render vigente en `TECHNICAL.md` §3.3 y §4.5.
4. **Verificación en dos fases (primera versión rápida vs cierre)**:
   - **Fase 1 — Primera versión e iteración:** prioridad absoluta a entregar algo compilado y visible/jugable cuanto antes. **Prohibido** ejecutar `pytest` o `run-scenario.ps1` en bucle tras cada micro-cambio o como "línea base" antes de editar (salvo petición expresa del usuario o depuración de lógica pura). Evitar subagentes si la tarea se resuelve leyendo 2-3 archivos directamente con `rg`. Ciclo rápido: leer lo mínimo → editar → compilar ROM (`build-project.ps1`, sin warnings nuevos) → enseñar captura/GIF o preparar subida a la DS.
   - **Fase 2 — Cierre (solo cuando el usuario apruebe la versión para mergear a `main`), una sola pasada:** compilar sin warnings nuevos; los escenarios de la feature (`run-scenarios.ps1 -Tag <feature>` o `-Filter`); `run-host-tests.ps1` (una vez, con `-Filter` si basta) **solo si el cambio toca lo que vigilan**: pipeline de assets y bakers, kit/compositor de la catedral, navegación y marea, blitter, volumen de impacto, tabla de armas o vida de enemigos, o si añade `float` o colores de efectos; la batería completa de escenarios **solo en los hitos de versión** (`DESIGN.md` §6.9) o cuando el usuario la pida; evidencia visual en `walkthroughs/`, `STATUS.md` y rendimiento en DS si aplica (regla 6). Si algo falla, se arregla y se repite solo lo que falló. En `STATUS.md` basta «tests y escenarios PASS»; no se apuntan recuentos.
4a. **Navegador solo headless:** toda validación con navegador usa Chromium/Playwright en modo headless explícito.
4b. **Qué tests se escriben** (detalle en la skill `ds-game-dev`, `references/verification-levels.md` y `host-tests.md`):
   - Un test nuevo solo si detecta un fallo real que ni un escenario ni la vista detectarían: lógica pura (compilando el C en el host), presupuestos (tiles, VRAM, ROM), datos generados por el pipeline o paridad Python/C.
   - **Prohibidos los contratos de texto:** tests que abren `source/*.c` y buscan nombres, `#define`, llamadas o cifras copiadas. Se rompen con un renombrado y no detectan que el juego falle. Las normas globales (sin `float`/`double`, paletas de efectos desaturadas) viven solo en `tests/test_guardrails.py`; se amplía ese archivo en vez de crear otro.
   - Un escenario de la batería debe comprobar estado (`state_changes`). Los que solo generan capturas o comparan variantes de arte llevan `"suite": false` (y `"evidence_only": true` si no tienen aserciones); los de rendimiento en DeSmuME, también `"suite": false` (regla 6).
   - Todo test de `tests/` está declarado en `hostTests` de `.ds-game-dev/project.json` y pasa en `main`; si deja de tener sentido, se borra.
5. **Escenarios de prueba headless**:
   - **Precondición geométrica obligatoria:** al escribir o modificar un escenario (`scenarios/*.json`), verificar que las coordenadas del actor crucen de verdad la entidad o volumen a probar (muro, oclusión, proyectil). Nunca probar oclusión o colisión en suelo abierto.
   - **Nomenclatura verídica:** prohibido nombrar eventos o capturas como `behind_wall_occluded` o similar si la geometría en esas coordenadas no produce lo que el nombre dice.
6. **Rendimiento: 60 FPS se certifican en la DS, no en el emulador.**
   - **Presupuesto único:** un frame son 560190 ticks de `cpuGetTiming()` (bus a 33,514 MHz, 16,7 ms). 33514 ticks es 1 ms, no el presupuesto. No usar otras cifras.
   - **Emulador:** DeSmuME solo sirve para comparar A/B el mismo escenario antes y después de un cambio. Un frame "barato" en DeSmuME puede pasarse del presupuesto en la DS (ya pasó: ~190.000 ticks en el emulador y caídas a 30 FPS en la consola).
   - **Hardware:** todo cambio que toque render, oclusión, actores o bucles por frame se valida en la DS antes de mergear, **en la catedral normal** con la variante `perf` de `.ds-game-dev/project.json` (`build-project.ps1 -Variant perf`; el juego tal cual con `PERF_PROFILE`). El `playground` está descartado (decisión del usuario, 2026-11-18). Ciclo: compilar `perf` → `upload-rom.ps1` → el usuario juega la situación → `fetch-device-log.ps1 -RemoteFile /dungeonds_perf.log` → leer media, máximos y frames con más de un vblank (detalle en la skill `ds-game-dev`).
   - Si la feature se ve bien pero la DS baja de 60 FPS, la tarea está bloqueada hasta optimizar.
7. **Subida a la DS (FTP)**:
   - Solo con confirmación explícita del usuario, que vale para esa subida.
   - Ejecutar siempre en modo no interactivo: `powershell -NonInteractive -ExecutionPolicy Bypass -File C:\codexlocal\skills\agentic-ds-dev\scripts\upload-rom.ps1 -ProjectPath <worktree> -ConfirmUpload` (el script lee `rom` y `romUploadName` de `.ds-game-dev/project.json`; no pasar `-RemoteName` salvo que el usuario lo pida).
   - Subir la ROM del worktree en el que se ha trabajado y recién compilada. Tras subir, decir al usuario rama, commit, nombre remoto y tamaño verificado, y qué debe mirar en la consola para reconocer la versión nueva.
   - Si el FTP no responde, la DS no tiene `ftpd.nds` abierto: pedir al usuario que lo abra; no reintentar a ciegas.
8. **Evidencia visual en el chat**: las imágenes que se quieran mostrar al usuario van en `walkthroughs/<sesión>/assets/` (o en el scratchpad mientras se trabaja), se enlazan con rutas relativas verificadas (comprobar que el archivo existe) y nunca se usan mockups fuera de la ROM como evidencia de juego. Para GIFs de animación:
   - Probar y aprobar primero en **1 unidad** antes de componer multitudes o escenas completas.
   - Mostrar todo el ciclo pedido (andar + telegrafía + disparo, o avance real si es un efecto en movimiento), a **≥15 fps** (`duration <= 65 ms`) y **4x NEAREST**.
   - Antes de responder, comprobar visualmente cada punto que pidió el usuario (encuadre, partes no cortadas, velocidad).
9. **Decisiones de diseño antes de código**: ningún comportamiento visual o de juego nuevo (transparencias, siluetas, feedback, FSM, armas) sin una decisión escrita en `DESIGN.md`. Si falta la decisión, proponer opciones al usuario y parar; no inventar un "provisional" en código. Lo que hoy es provisional está marcado así en `TECHNICAL.md` §4.6 y no se amplía.
10. **Comunicación con el usuario**: el usuario es ingeniero y arquitecto del juego, no programador de DS/C. Explicar causas, opciones y resultados en lenguaje de producto/arquitectura y *tradeoffs* (impacto en juego, riesgo, esfuerzo), sin jerga técnica de bajo nivel (git, BlocksDS, registros, funciones C o detalles internos de hardware DS). Cuando falte una decisión, hacer **una sola pregunta por turno** con recomendación clara; nunca bloques de varias preguntas a la vez.
11. **2 fallos → diagnóstico mínimo**: si un render, animación, física de Blender o encaje de mapa falla visualmente 2 veces seguidas, **parar los renders completos** y ejecutar primero una prueba mínima (1 solo modelo, 1 frame o impresión numérica de coordenadas/bounding box) antes de relanzar el proceso completo.

---

## Flujo de VFX

Cómo se hicieron los efectos de armas (2026-11): histórico en `walkthroughs/weapon-previews/` y `walkthroughs/mejoras-v04/`.

- **Decisión antes de código** (regla 9): dirección artística escrita en `DESIGN.md` con referencias y reglas comunes (perspectiva 2:1 del suelo, oclusión por el cuerpo).
- **Saturación obligatoria:** todo efecto, del héroe o de cualquier enemigo, usa paletas apagadas (`DESIGN.md` §6.10, «Efectos desaturados en todos los personajes»; paleta `FX_SH_*` de `source/weapons.c`). Nunca primarios puros ni rampas «de neón». Lo comprueba `tests/test_guardrails.py`; un efecto en un archivo nuevo se añade a su lista, no a un test propio.
- **Evidencia:** escenas de sandbox con enemigos parados y héroe invulnerable (`tools/sandbox_scenes.py`), geometría exacta (regla 5), GIFs de la ROM real y hojas de contacto 4x NEAREST que se miran de verdad. Los mockups no valen como evidencia (regla 8). Cierre con medición en la DS (reglas 4 y 6); las escenas de comparación A/B/C del sandbox llevan `"suite": false`.
- **Rondas A/B/C para el usuario:** una escena montada por elemento (`cathedral-sandbox`, `tools/abc_scenes.py`) con solo el héroe y los enemigos necesarios; GIFs en columnas A | B | C a 4x y ≥15 fps (`tools/abc_gif.py`) con una frase antes de cada uno (qué mejora es y cuándo aparece); un único HTML con las imágenes dentro (el usuario revisa desde el móvil); sin ruido de depuración; efectos que nacen del mundo y respetan la oclusión; el arte de las cartas se captura de la ROM (`tools/levelup_cards/capture_cards.py`). El usuario elige o descarta por elemento y cada vuelta se apunta en `DESIGN.md`.

## Subagentes y Modelos

- Todo plan que lance subagentes indica el modelo de cada uno. Por defecto: **Haiku** solo para búsquedas, listados, verificar que algo sigue presente o leer logs; **Sonnet** para implementar (también efectos y VFX), análisis de código, revisiones y auditorías por área; **Opus** solo para decisiones de arquitectura o diseño que no se puedan partir.
- **Modelos de otros proveedores:** el plan nombra el modelo (`luna`, `sol`, `terra`, `astra` por Codex; `argon`, `flash`, `gpt-oss` por Antigravity) y se ejecuta con la skill compartida `delegate-agents` (`C:\codexlocal\skills\delegate-agents`, alias en su `models.json`, `delegate.py --list`). Haiku, Sonnet, Opus y Fable siguen siendo el tool Agent. Escritura solo en worktrees; la respuesta externa se verifica como cualquier otra.
- **Límite de los agentes Codex:** en su sandbox no arrancan Python, Docker ni WSL (sí gcc y Node). El brief les pide intentarlo una vez y entregar los comandos sin reintentar. Quien coordina compila la ROM, pasa los tests y los escenarios y ejecuta los renders del lab.
- Usar el modelo más barato que no baje la calidad del resultado. El usuario lo ha pedido repetidamente: un plan sin esta asignación se considera incompleto.

---

## Protocolo de Sesiones Atómicas, Ramas y Worktrees

1. **Un Chat = Una Sesión Atómica:** cada conversación se dedica a una feature, fix u optimización concreta.
2. **Ramas:** `main` integra las entregas. `feat/<nombre>`, `fix/<nombre>`, `perf/<nombre>`, `docs/<nombre>` o `proto/<nombre>` para el trabajo aislado.
3. **Worktrees obligatorios** para cada tarea sustancial, bajo `.worktrees/` (ignorado por git):
   ```bash
   git worktree add .worktrees/<nombre> -b feat/<nombre>
   ```
   - Todo el trabajo y las compilaciones de la sesión se hacen en ese worktree. Las ROMs `dungeonds*.nds` de la raíz del repo principal no son la versión de trabajo.
   - **Grafo graphify:** ver la sección graphify, abajo.
4. **Commits:**
   - Añadir archivos por ruta (`git add <rutas>`); nunca `git add -A`, `git add .` ni `git commit -a`. Revisar `git status --short` antes de cada commit.
   - Commit, merge y push solo cuando el usuario lo pida o lo apruebe para esa entrega.
5. **Cierre:** al terminar, fusionar a `main` y limpiar:
   - **Revisar los MDs antes de cerrar (obligatorio):** repasar lo que cambió la sesión (comportamiento, cifras, controles, enemigos, assets, variantes, toolchain, reglas de proceso) y actualizar en la misma entrega cada documento afectado según la taxonomía de arriba: `DESIGN.md` (que siga reflejando el juego actual, sin parches «corrige lo de arriba»; lo retirado va a `DESIGN-ARCHIVE.md`), `TECHNICAL.md`, `LORE.md`, `assets/MANIFEST.md`, `STATUS.md` y este archivo. Si ninguno cambia, decirlo en una línea en el walkthrough. Un texto obsoleto es peor que ninguno: se corrige o se mueve al archivo, no se deja.
   - Mover los archivos ya usados de `assets/inbox/` a `assets/inbox/processed/` en el repo principal y confirmar que no quedan zips/fbx procesados huérfanos en `inbox/`.
   - Si el usuario pidió cerrar o consolidar la sesión, commitear también `DESIGN.md`, `STATUS.md`, `TECHNICAL.md` y `walkthroughs/` sin pedir una segunda confirmación.
   - **Rescatar los assets no versionados antes de borrar el worktree:** todo archivo sin trackear o ignorado de `assets/` (modelos 3D, FBX derivados, texturas, fuentes) debe existir, idéntico, en la carpeta principal del repo aunque no se versione. Copiar los que falten sin sobrescribir; si alguno existe con contenido distinto, preguntar al usuario. Comprobar archivo a archivo, comparando el contenido, antes de `worktree remove`. Sin esa comprobación no se borra el worktree.
   - Comprobar `git worktree list` para no dejar ramas terminadas sin mergear.
   - En Windows, salir antes del worktree (`cd` a la raíz del repo) y cerrar procesos que lo usen; si no, `worktree remove` falla con "Permission denied".
   ```bash
   cd /c/codexlocal/dungeonds
   git worktree remove .worktrees/<nombre>
   git branch -d feat/<nombre>
   ```
6. **Walkthroughs por sesión:**
   - Cada entrega genera `walkthroughs/<nombre-sesion>/walkthrough.md` con sus imágenes en `walkthroughs/<nombre-sesion>/assets/`.
   - Se añade una fila a `walkthroughs/README.md` cuyo enlace apunte a una carpeta que exista.
   - `STATUS.md` recibe la entrega (resumen corto + enlace) y se actualiza su sección "Estado actual" si cambia lo que hay que saber para retomar.
7. **Etiqueta de estado del chat (Antigravity):**
   - Al iniciar una sesión en Antigravity (en cuanto exista título en `C:\Users\malfonso\.gemini\antigravity\annotations\<conversation-id>.pbtxt`), añadir el prefijo `[EN CURSO] ` al título si no tiene ya un tag de estado (`[EN CURSO]`, `[MERGEADO]` o `[ABANDONADO]`).
   - Al acabar la sesión (al mergear a `main` o descartar el trabajo), actualizar el prefijo a `[MERGEADO] ` o `[ABANDONADO] ` según corresponda, tanto en `annotations\<conversation-id>.pbtxt` como en la columna `title` de `conversation_summaries.db`.

## graphify

El grafo `graphify-out/` (no versionado) sirve para dudas arquitectónicas amplias: `graphify query "<pregunta>"`, `graphify path "<A>" "<B>"`, `graphify explain "<concepto>"` (o MCP `query_graph` con `project_path`). Si ya sabes el archivo o símbolo, usa `rg`. Si existe `graphify-out/wiki/index.md`, úsalo para navegar; `GRAPH_REPORT.md` solo para revisiones amplias. El worktree nace sin grafo: no lo copies al arrancar salvo que vayas a consultarlo. **Al mergear en `main`**, ejecutar `graphify update .` (AST-only, sin API); los archivos sucios de `graphify-out/` son normales. Ejecutable: `$env:GRAPHIFY_EXE` o `C:/Users/malfonso/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0/LocalCache/local-packages/Python313/Scripts/graphify.exe`.
- PowerShell: `Copy-Item -Recurse -Force graphify-out .worktrees\<nombre>\graphify-out; Push-Location .worktrees\<nombre>; & "$env:GRAPHIFY_EXE" update .; Pop-Location`
- Bash: `cp -r graphify-out .worktrees/<nombre>/ && (cd .worktrees/<nombre> && "$GRAPHIFY_EXE" update .)` (sin `&`).
- Con `/graphify`, usar la skill instalada antes de nada.

---

## Assets

Catálogo y ciclo de vida completo (7 etapas): `assets/MANIFEST.md` §0. Lo esencial:
- Originales (modelos Tripo/Mixamo, vídeos finales) en git con **Git LFS**; solo se adopta lo final, porque LFS ocupa cupo para siempre.
- Derivados (FBX animados, GLB intermedios, renders del lab) no se versionan: se regeneran con el script del catálogo. Lo que lee la ROM va en git normal.
- Todo lo descargado cae en `assets/inbox/` (ignorado); solo lo que el usuario elige pasa a `source/` y al catálogo.
- Al cerrar una sesión que toca assets: catálogo al día, `git lfs ls-files` con los originales nuevos, `git push` sube LFS, y ningún original en uso queda solo en la carpeta principal (regla de rescate de «Protocolo de Sesiones»).

## Audio / SFX y vídeos

- **SFX (CLI `@elevenlabs/cli`):** requiere `ELEVENLABS_API_KEY` en el entorno (nunca en el repo). `elevenlabs text-to-sound-effects convert --text "<inglés, dry, no reverb, isolated>" --duration-seconds 0.5 --output-format wav_16000 -o assets/sfx/raw/<nombre>.wav` (si no permite `wav_16000`, mp3 y `ffmpeg`). Siempre `--duration-seconds` con el mínimo necesario (≥0,5 s). Se recorta el silencio inicial y se hornea a 16.384 Hz mono 8-bit en `assets/sfx/baked/` antes de integrarlo.
- **Vídeos de lore:** pipeline y reglas en la skill `codice-lore-video` (`.agents/skills/codice-lore-video/`). El MP4 final vive en `assets/videos/<nombre>.mp4` (LFS); el walkthrough guarda fotogramas y tira de control.
