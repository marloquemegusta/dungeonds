# Briefing para continuar el benchmark de delegación (2026-11-10)

Pensado para pegar o leer desde otra sesión. Fuente canónica del diseño: [../BENCHMARK.md](../BENCHMARK.md). Índice del corpus: [README.md](README.md).

## 1. Objetivo (palabras del usuario)
Trocear el historial de **dungeonds y towerds** en problemas (problema + solución de referencia + método de evaluación), ejecutarlos sobre sus modelos y saber **cuál habría sido el modelo más barato que los resolvía**. No se trata de concluir qué fue mejor en el pasado, sino de construir las tareas. Gastar dinero está bien (jueces LLM incluidos). Debe crecer: cada problema difícil nuevo entra como ítem. Quiere lanzarlo como **un solo prompt/comando** sin entrar en Code.

## 2. Qué existe (todo sin commitear, en `C:\codexlocal\dungeonds`)
- `BENCHMARK.md`: protocolo, centinelas, §7b estado del arnés.
- `bench/tasks/<id>/{problem.md,item.json}`: **71 ítems** (towerds 32, dungeonds 35, skill 4; 20 macro, 51 micro). Hashes verificados con git. Generados por 6 agentes luna:high. `ficheros` clave de `item.json`: `base_commit`, `solution_commits`, `evaluacion.puertas/rubrica/trampas`, `oraculo_auto` (solo en 1 ítem), `calibrado`.
- `bench/manifest.json`, `bench/README.md` (índice generado).
- `bench/run_item.py`: arnés de un ítem. Subcomandos `run <id> --alias luna:high`, `calibrate <id>`, `grade`. Hace `git archive` del commit base, lanza el agente con `delegate.py`, aplica overlay (tests/escenarios de la solución), `build-project.ps1`, `run-scenario.ps1`, medidas sobre capturas (`oraculo_auto`) y guarda en `.worktrees/bench-runs/<id>/<alias>-<ts>/`.
- `bench/results.jsonl`: 2 resultados.
- `bench/items/`: **carga antigua con ids erróneos, borrar a mano** (el sistema me bloqueó el `rm -rf`).

## 3. Resultados hasta ahora
| Ítem | Modelo | Resultado | Coste |
|---|---|---|---|
| `td-dial-steps-hold-gate` (bug acotado, calibrado) | luna:medium | ACEPTADO, y la revisión del diff confirma las 3 conductas | 188 s, 894k tokens in, 6k out |
| `td-city-defense-slice` (macro, dif. 5) | luna:high | Oráculo ACEPTA pero es **falso positivo**: sin tienda A1/A2 ni pantalla de fin de demo | 776 s, 7,06M in, 31k out |

Ambas ejecuciones fueron en **sandbox sin toolchain** (Luna edita; compila y puntúa el coordinador). Luna declaró en las dos que no pudo compilar.

## 4. Lecciones y trampas (importantes)
1. **Calibrar es obligatorio**: base debe fallar y referencia pasar. En `td-dial-steps-hold-gate` el base con el bug también pasaba (escenarios solo comprueban `screen_changed`); se añadió `oraculo_auto` midiendo la longitud de la barra de munición (25 con bug, 39 corregido). Cubre 1 de 3 conductas.
2. **Oráculos débiles heredados**: `screen_changes` con mínimo de píxeles lo supera cualquier juego animado (caso city-defense). Tests Python que son **reimplementación espejo** del algoritmo C (`dd-gameplay-los-refactor`, `tests/test_los.py`) no prueban el código del modelo. No se ha auditado el resto de las 71.
3. **Enunciados sin contrato de interfaz**: el escenario recorre una UI (tienda A1/A2, pantalla final) que `problem.md` no menciona. Hay que añadir al enunciado lo que el oráculo exige.
4. `--allow-toolchain` (Codex sin sandbox) fue **bloqueado por el clasificador de seguridad**. Por defecto el arnés va sin él; `--toolchain` solo con permiso explícito del usuario.
5. **Saga de FPS de towerds** (`td-perf-fps-root-cause` + 7 micro): no evaluable aún. Sus escenarios usan `spawn_batch`, que el runner actual de la skill rechaza (`invalid_scenario`; lo tenía la copia antigua de la skill dentro de towerds). Hay que reconstruir un oráculo de rendimiento (idea: tiempo de pared en emulador A/B con un escenario de estrés, o un test de estado). Además, en towerds el presupuesto sale como 545 en el HUD y la regla vigente es 560190 ticks: fijar la equivalencia. Corte histórico según git: 17 sep 23:39 → 18 sep 11:51 intentos sin efecto (KNOWN_ISSUES: pico a 30 FPS); 18 sep 23:09 → 19 sep 01:23 profiler + harness + dirty blocks 8x8 + ITCM + sprites 8 bit + doble buffer VRAM + quads 32 bit. El usuario dice que lo primero fue con GPT 5.6 y lo segundo con Gemini 3.8 Flash (hipótesis a contrastar; git no guarda el modelo).
6. Entorno: `python -I` no ve PIL/numpy (usar `python` normal para medir capturas). En scripts con heredoc evitar `\c` en cadenas no raw. En Windows la consola imprime mal acentos (los ficheros están bien en UTF-8). El `towerds` y la skill son repos distintos (`C:\codexlocal\towerds`, `C:\codexlocal\skills\agentic-ds-dev`).
7. Tokens ≠ dinero: guardar tarifa y fecha. Luna cuenta ~2/3 de entrada en caché.

## 5. Decisión pendiente del usuario
¿Cómo cerrar los oráculos débiles?
- (A) **Juez LLM** de otra familia (Claude) con rúbrica, capturas y diff de referencia: es lo que el usuario sugirió; sirve para macros.
- (B) Ampliar enunciados con contrato de interfaz + comprobaciones agnósticas sobre capturas.
- (C) Ambas (recomendada: automático para lo medible, juez para el resto).

## 6. Siguientes pasos propuestos
1. Elegir A/B/C y escribir el **juez** (`bench/judge.py` o agente Claude con rúbrica, temperatura baja, otro modelo que el evaluado) y su prompt.
2. Reparar `td-city-defense-slice`: contrato de interfaz en `problem.md` + oráculo/juez; recalibrar y **repetir con luna:high**.
3. **Auditar las 71 puertas** (¿el test ejecuta el código del modelo? ¿el enunciado fija la interfaz?) con agentes baratos y marcar `calibrado` solo tras `calibrate`.
4. Reconstruir el oráculo de rendimiento para la saga de FPS.
5. Primera ronda comparativa: ~10 micro calibrados × {haiku, sonnet, luna:medium/high, flash, argon} × k=3. Registrar en `results.jsonl`.
6. Registrar aciertos/fallos de agentes en `delegate-agents/feedback/` (según la memoria del proyecto) y actualizar `AGENTS.md` (sección Subagentes) con datos, **no** antes.
7. Cuando se confirme: commit en rama `feat/bench-adaptativo` (por ruta, nunca `git add -A`), walkthrough y fila en `STATUS.md`.

## 7. Reproducir lo hecho
```bash
python bench/run_item.py calibrate td-dial-steps-hold-gate
python bench/run_item.py run td-dial-steps-hold-gate --alias luna:medium
```
Requiere Docker Desktop arrancado y `check-toolchain.ps1` en PASS (WSL caliente tarda ~28 s la primera vez).

## 8. Procedencia
Sesión `2b8cde01…` (2026-11-07). Material de trabajo en su scratchpad (`C:\Users\malfonso\AppData\Local\Temp\claude\eb4412e37933fca6\2b8cde01-f48f-4d51-bce1-0484a5305ae7\scratchpad`): `digests/` (resumen por sesión de las 29 sesiones), `out/` (8 informes luna), `out2/` (JSON de ítems por tramo), `ingest.py`, `mkbriefs.py`. **Ojo**: `ingest.py` regenera `bench/tasks/` desde `out2/` y **sobrescribiría** las ediciones posteriores de `item.json` (`oraculo_auto`, `calibracion`); no volver a ejecutarlo sin volcar antes esas ediciones. El scratchpad puede desaparecer: `bench/tasks/` es ya la fuente de verdad.
