# AGENTS.md - Reglas de Operación y Roles de Agente

## Taxonomía Documental

El repositorio cuenta con fuentes de verdad canónicas sin duplicación:

| Documento | Ámbito | Contenido |
| :--- | :--- | :--- |
| `DESIGN.md` | Producto y Arte | Visión de juego, controles, mecánicas, dirección visual y decisiones abiertas. |
| `TECHNICAL.md` | Arquitectura C / NDS | Toolchain, presupuestos, pipeline de assets y render, dependencias de host y deuda técnica. |
| `AGENTS.md` | Proceso y Reglas | Protocolo de trabajo, workflow de desarrollo para Nintendo DS y verificación de cambios. |
| `STATUS.md` | Estado y Registro | Estado actual para retomar el trabajo y entregas recientes verificadas. Lo anterior a 2026-11 está en `STATUS-ARCHIVE.md`. |
| `walkthroughs/` | Documentación por sesión | Un `walkthrough.md` por entrega, con su evidencia en `assets/`. Índice en `walkthroughs/README.md`. |
| `LEAN-CTX.md` | Herramienta | Reglas de la herramienta lean-ctx; no es documentación del juego. |
| Skill compartida `ds-game-dev` | `C:\codexlocal\skills\agentic-ds-dev` | Flujo genérico del toolchain NDS (Docker + DeSmuME + FTP). Vive fuera del repo y no se debe copiar aquí. |

Si una regla o cifra aparece en dos documentos, uno de ellos sobra: dejarla en su fuente canónica y referenciarla desde el otro.

---

## Reglas del Toolchain y Ejecución

1. **Sin comandos interactivos del toolchain al usuario**: compilación, tests, emulación headless y subida a la DS se ejecutan con los scripts de la skill (`build-project.ps1`, `check-toolchain.ps1`, `run-scenario.ps1`, `upload-rom.ps1`, `fetch-device-log.ps1`), invocados desde `C:\codexlocal\skills\agentic-ds-dev\scripts\` con `-ProjectPath <ruta del worktree>`. Si Docker Desktop no está arrancado, arrancarlo y esperar con una condición (no con `sleep` fijo). Los arreglos genéricos del toolchain se hacen en el repo de la skill, en su propia rama, nunca parcheados aquí.
2. **Nintendo DS es plataforma sin FPU**: prohibido `float` o `double` en código de simulación o juego en tiempo de ejecución (existen por software, pero son lentísimos). Física y movimiento en punto fijo (`int32_t` con 8.8 o 12.12). La ARM9 sí tiene divisor y raíz cuadrada por hardware (`div32`, `sqrt32`); evitar `/` y `%` de C en bucles calientes.
3. **Presupuesto estricto de memoria**:
   - OAM: 128 entradas de sprites hardware.
   - 4 MB de RAM principal (DS clásica).
   - Cifras actuales de uso y la arquitectura de render vigente: `TECHNICAL.md` §3.3 y §4.5.
4. **Verificación antes de dar por cerrada una tarea**:
   - Compilación limpia con la skill, sin warnings nuevos.
   - Tests de host y escenarios headless relevantes.
   - Evidencia visual (capturas / GIFs) de la ROM real en caso de cambios gráficos.
   - **Automatización de navegador exclusivamente headless:** toda validación con navegador usa Chromium/Playwright en modo headless explícito.
5. **Escenarios de prueba headless**:
   - **Precondición geométrica obligatoria:** al escribir o modificar un escenario (`scenarios/*.json`), verificar que las coordenadas del actor crucen de verdad la entidad o volumen a probar (muro, oclusión, proyectil). Nunca probar oclusión o colisión en suelo abierto.
   - **Nomenclatura verídica:** prohibido nombrar eventos o capturas como `behind_wall_occluded` o similar si la geometría en esas coordenadas no produce lo que el nombre dice.
6. **Rendimiento: 60 FPS se certifican en la DS, no en el emulador.**
   - **Presupuesto único:** un frame son 560190 ticks de `cpuGetTiming()` (bus a 33,514 MHz, 16,7 ms). 33514 ticks es 1 ms, no el presupuesto. No usar otras cifras.
   - **Emulador:** DeSmuME solo sirve para comparar A/B el mismo escenario antes y después de un cambio. Un frame "barato" en DeSmuME puede pasarse del presupuesto en la DS (ya pasó: ~190.000 ticks en el emulador y caídas a 30 FPS en la consola).
   - **Hardware:** todo cambio que toque render, oclusión, actores o bucles por frame se valida en la DS antes de mergear. Ciclo: compilar con `PERF_PROFILE 1` (`include/perfprof.h`) → `upload-rom.ps1` → el usuario juega la situación → `fetch-device-log.ps1 -RemoteFile /dungeonds_perf.log` → leer media, máximos y frames con más de un vblank. Volver a dejar `PERF_PROFILE 0` antes del merge.
   - Si la feature se ve bien pero la DS baja de 60 FPS, la tarea está bloqueada hasta optimizar.
7. **Subida a la DS (FTP)**:
   - Solo con confirmación explícita del usuario, que vale para esa subida.
   - La ROM se sube con el nombre de `romUploadName` en `.ds-game-dev/project.json` (`dungeonds.nds`); el script lo lee solo. No pasar `-RemoteName` salvo que el usuario lo pida.
   - Subir la ROM del worktree en el que se ha trabajado y recién compilada. Tras subir, decir al usuario rama, commit, nombre remoto y tamaño verificado, y qué debe mirar en la consola para reconocer la versión nueva.
   - Si el FTP no responde, la DS no tiene `ftpd.nds` abierto: pedir al usuario que lo abra; no reintentar a ciegas.
8. **Evidencia visual en el chat**: las imágenes que se quieran mostrar al usuario van en `walkthroughs/<sesión>/assets/` (o en el scratchpad mientras se trabaja) y se enlazan con rutas relativas o se envían como archivo. Nunca generar mockups fuera de la ROM como evidencia de juego.
9. **Decisiones de diseño antes de código**: ningún comportamiento visual o de juego nuevo (transparencias, siluetas, feedback, FSM, armas) sin una decisión escrita en `DESIGN.md`. Si falta la decisión, proponer opciones al usuario y parar; no inventar un "provisional" en código. Lo que hoy es provisional está marcado así en `TECHNICAL.md` §4.6 y no se amplía.

---

## Flujo de VFX (como se hicieron los efectos de armas, 2026-11)

1. **Decisión antes de código** (regla 9): la dirección artística se escribe en `DESIGN.md` con referencias (imágenes del usuario) y reglas comunes, por ejemplo la perspectiva 2:1 del suelo y la oclusión por el cuerpo.
2. **Mockups baratos primero**, solo para elegir: GIFs o hojas de píxeles con 3 alternativas por efecto. No valen como evidencia de juego (regla 8).
3. **Implementación real en la ROM**, con un selector de depuración para comparar variantes en vivo. El agente implementa (Haiku por defecto) y quien dirige el arte revisa; cada agente lleva un brief con archivos, tope de coste por frame y criterio de aceptación.
4. **Sandbox y capturas**: escenas con enemigos parados y héroe invulnerable (`tools/sandbox_scenes.py`), geometría exacta (regla 5), GIFs de la ROM real a ~50-60 ms por frame, y hojas de contacto ampliadas (4x NEAREST sobre el héroe) que se miran de verdad antes de dar nada por bueno.
5. **Iterar con referencias**: cada ronda ajusta una cosa (por ejemplo, de hélice a rayos angulosos y luego a trazo fino) y se descartan variantes en el walkthrough.
6. **Cierre**: tests de host (contratos de texto: topes, sin `float`, orden de pases), 0 warnings, escenarios PASS, y medición en la DS con la variante `playground-perf` (regla 6) antes de mergear.

Lecciones: un bucle sin tope congela el juego; el coste de la oclusión por píxel se come el frame, mejor por tramos; un agente que se atasca se reanuda con un mensaje corto; los pokes en el frame 0 los borra crt0.

## Subagentes y Modelos

- Todo plan que lance subagentes indica el modelo de cada uno. Por defecto: **Haiku** para búsquedas, listados, verificar que algo sigue presente o leer logs; **Sonnet** para análisis de código, revisiones y auditorías por área; **Opus** solo para decisiones de arquitectura o diseño que no se puedan partir.
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
   - **Grafo graphify:** `graphify-out/` no está versionado y el worktree nace sin él. Copiarlo y refrescarlo (AST-only, sin coste de API); en llamadas MCP usar `project_path` = ruta del worktree.
     - PowerShell:
       ```powershell
       Copy-Item -Recurse -Force graphify-out .worktrees\<nombre>\graphify-out
       Push-Location .worktrees\<nombre>; & "$env:GRAPHIFY_EXE" update .; Pop-Location
       ```
     - Bash (Git Bash):
       ```bash
       cp -r graphify-out .worktrees/<nombre>/ && (cd .worktrees/<nombre> && "$GRAPHIFY_EXE" update .)
       ```
     - Si `GRAPHIFY_EXE` no está definida, el ejecutable está en `C:/Users/malfonso/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0/LocalCache/local-packages/Python313/Scripts/graphify.exe`. En Bash no anteponer `&`.
4. **Commits:**
   - Añadir archivos por ruta (`git add <rutas>`); nunca `git add -A`, `git add .` ni `git commit -a`. Revisar `git status --short` antes de cada commit.
   - Commit, merge y push solo cuando el usuario lo pida o lo apruebe para esa entrega.
5. **Cierre:** al terminar, fusionar a `main` y limpiar. En Windows, salir antes del worktree (`cd` a la raíz del repo) y cerrar procesos que lo usen; si no, `worktree remove` falla con "Permission denied".
   ```bash
   cd /c/codexlocal/dungeonds
   git worktree remove .worktrees/<nombre>
   git branch -d feat/<nombre>
   ```
6. **Walkthroughs por sesión:**
   - Cada entrega genera `walkthroughs/<nombre-sesion>/walkthrough.md` con sus imágenes en `walkthroughs/<nombre-sesion>/assets/`.
   - Se añade una fila a `walkthroughs/README.md` cuyo enlace apunte a una carpeta que exista.
   - `STATUS.md` recibe la entrega (resumen corto + enlace) y se actualiza su sección "Estado actual" si cambia lo que hay que saber para retomar.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` (CLI) or `query_graph` (MCP). When using MCP tools, pass `project_path: "<path>"` (or rely on default in `mcp_config.json`). Use `graphify path "<A>" "<B>"` / `shortest_path` for relationships and `graphify explain "<concept>"` / `get_node` for focused concepts.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` (AST-only, no API cost) with the executable and shell syntax given in the worktree section above.
