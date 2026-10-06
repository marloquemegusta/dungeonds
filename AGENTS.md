# AGENTS.md - Reglas de Operación y Roles de Agente

## Taxonomía Documental

El repositorio cuenta con fuentes de verdad canónicas sin duplicación:

| Documento | Ámbito | Contenido |
| :--- | :--- | :--- |
| `DESIGN.md` | Producto y Arte | Visión de juego, ambientación gótica/nigromancia, controles, mecánicas y paleta visual. |
| `TECHNICAL.md` | Arquitectura C / NDS | Toolchain (BlocksDS), punto fijo, VRAM/OAM budgets, pipeline de renderizado y generador procedural. |
| `AGENTS.md` | Proceso y Reglas | Protocolo de trabajo, workflow de desarrollo para Nintendo DS y verificación de cambios. |
| `STATUS.md` | Registro de Sesiones | Estado actual, historial auditable de entregas y siguientes pasos. |
| `SKILL.md` | Skill `ds-game-dev` | Flujo genérico y automatizado del toolchain NDS con Docker y DeSmuME. |

---

## Reglas del Toolchain y Ejecución

1. **Sin comandos interactivos del toolchain al usuario**: Todo el flujo de compilación, tests y emulación headless se ejecuta con los scripts de `scripts/` (`scripts/build-project.ps1`, `scripts/check-toolchain.ps1`, `scripts/run-scenario.ps1`).
2. **Nintendo DS es plataforma sin FPU**: Prohibido usar `float` o `double` en código de simulación o juego en tiempo de ejecución. Toda la física y movimiento se realiza en punto fijo (`int32_t` con precisión `8.8` o `12.12`).
3. **Presupuesto estricto de memoria**:
   - VRAM OAM: 128 entradas de sprites hardware máximo.
   - 4 MB RAM principal (DS clásica).
   - Fondo de mazmorra tileado en BG Layers (BGs de texto o affine) + entidades en sprites OAM.
4. **Verificación antes de dar por cerrada una tarea**:
   - Compilación limpia con Docker BlocksDS sin warnings graves.
   - Ejecución de escenarios headless o tests de host.
   - Generación de evidencia visual (capturas / GIFs) en caso de cambios gráficos.

---

## Protocolo de Sesiones Atómicas, Ramas y Worktrees

1. **Un Chat = Una Sesión Atómica (Feature/Fix-Scoped):** Cada nueva conversación se dedica exclusivamente a una feature, fix u optimización concreta, evitando dispersión de contexto.
2. **Estrategia y Jerarquía de Ramas:**
   - `master`: Rama principal del repositorio y foco de entregas integradas.
   - `feat/<nombre>` / `fix/<nombre>` / `perf/<nombre>`: Ramas de trabajo atómicas creadas en worktree para cambios aislados antes de mergear en `master`.
3. **Uso Obligatorio de Git Worktrees para Aislamiento:**
   - En cada nueva sesión o tarea sustancial, se debe instanciar un worktree físico separado dentro del repo bajo `.worktrees/` (ignorado por git):
     ```bash
     git worktree add .worktrees/<nombre> -b feat/<nombre>
     ```
   - Todo el trabajo de la sesión se desarrolla dentro de dicho worktree.
   - **Copia del runtime local:** Al ser un checkout limpio, copiar el runtime de emulación si se requiere ejecutar escenarios locales:
     ```powershell
     Copy-Item -Recurse -Force runtime\bin .worktrees\<nombre>\runtime\bin
     ```
   - Al concluir, verificar y fusionar a `master`, el worktree y la rama se limpian:
     ```bash
     git worktree remove .worktrees/<nombre>
     git branch -d feat/<nombre>
     ```
4. **Convención Canónica de Walkthroughs por Sesión:**
   - Cada entrega o sesión finalizada genera su resumen técnico auditable en `walkthroughs/<nombre-sesion>/walkthrough.md` junto con sus imágenes y capturas en `walkthroughs/<nombre-sesion>/assets/`.
   - Se actualiza invariablemente el índice acumulativo `walkthroughs/README.md`.
   - `STATUS.md` se mantiene sincronizado como changelog histórico de sesiones terminadas y validadas con evidencia real.
