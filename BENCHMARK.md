# BENCHMARK.md - Corpus de tareas y protocolo para elegir el modelo más barato

Documento vivo. Objetivo: partir el historial real de towerds y dungeonds en tareas (problema, solución de referencia, evaluación) y ejecutarlas sobre distintos modelos para saber **qué modelo, con qué esfuerzo, es el más barato que resuelve cada clase de problema**. No se concluye nada del historial por sí mismo: el historial solo aporta las tareas.
Corpus: [bench/README.md](bench/README.md) (índice), `bench/tasks/<id>/{problem.md,item.json}`, `bench/manifest.json`.

## 1. Qué hay ahora

71 ítems generados el 2026-11-07 por 6 agentes luna:high leyendo git, STATUS/KNOWN_ISSUES y los resúmenes de sesión: towerds 32 (12 macro, 20 micro), dungeonds 35 (8 macro, 27 micro), skill `agentic-ds-dev` 4. Todos los hashes están verificados con `git cat-file` y `merge-base --is-ancestor` (`base_commit` es ancestro de la primera solución).
Pendiente: **ninguno está calibrado** (§4) y 47 de 71 son `reproducible: parcial`. Los comandos de evaluación son propuestas de los agentes, no se han ejecutado.

Estado de cada ítem (`item.json`): `tipo` macro/micro (los micro cuelgan de un macro por `parent`), `clase`, `base_commit`, `solution_commits`, `evaluacion` (puertas + rúbrica + trampas), `dificultad` 1-5, `historia`, `reproducible`, `calibrado`.

## 2. Ejecutar un ítem

1. **Entorno**: `git worktree` o `git archive` de `base_commit` en un directorio nuevo. El modelo no ve commits posteriores.
2. **Entrada**: solo `problem.md` más las reglas del repo (AGENTS.md del `base_commit`). Mismo texto para todos los modelos.
3. **Ejecución**: el modelo trabaja con sus herramientas (Claude por Agent; Codex y Antigravity por `delegate.py`, `--allow-toolchain` solo en worktree desechable). Se registra alias, esfuerzo, tokens in/cached/out, segundos y el diff.
4. **Overlay**: se copian encima del resultado los tests y escenarios que añadió la solución de referencia (`fuente: solution_commit`). El modelo nunca los ve.
5. **Puertas** en orden, con la más alta superada guardada: E ejecutó el oráculo, G1 build sin warnings nuevos, G2 tests, G3 escenario headless, G4 métrica, G5 rúbrica, G6 humano.
6. **Rúbrica LLM** (G5): juez de **otra familia** que el modelo evaluado, con el diff del modelo, el diff de referencia, la rúbrica con anclas del ítem y las trampas. Temperatura 0, dos jueces y se promedia; los desacuerdos mayores de 1 punto van a revisión humana. Es gasto asumido.
7. **Aceptado** = supera todas las puertas aplicables. Una mejora de métrica con regresión visual no cuenta.
8. **Repeticiones**: k=3 en ítems baratos, 1 en los que necesitan DS o humano.

Fallo del entorno (sin Python/Docker/WSL, FTP caído) se anota como `E`, no como fallo del modelo.

## 3. Coste y decisión

- **Coste de un intento** = tokens in, cached y out × tarifa vigente (guardar tarifa y fecha) + coste del juez. **Coste por resultado aceptado** = coste total de los k intentos / intentos aceptados.
- **Modelo más barato suficiente** para un ítem o clase: el de menor coste por aceptado entre los que aceptan al menos 2 de 3, con intervalo de confianza. Tabla final: clase → modelo y esfuerzo por defecto → modelo de escalado.
- **Cascada**: se simula con los datos de las ejecuciones (barato primero, un reintento con el feedback del oráculo, luego subir) y se compara su coste con "siempre el fuerte".
- **Los macro puntúan distinto**: además de pasar la métrica, se evalúa el *proceso* (ver §5). Los micro responden a "¿puede un modelo barato hacer este trozo?" y permiten un enrutado trocito a trocito.
- Orden de ejecución para gastar poco: ítems con oráculo automático y bajo coste primero; macro y G6 al final y solo con los modelos que ya pasan los micro.

## 4. Calibración (antes de fiarse de un ítem)

Para cada ítem, con el toolchain actual:
1. Aplicar el overlay sobre `base_commit` → las puertas **deben fallar**.
2. Aplicar el overlay sobre el último `solution_commit` → las puertas **deben pasar**.
3. Revisar las `trampas`: ¿alguna solución obviamente incorrecta pasa? Si sí, endurecer el oráculo.
4. Marcar `calibrado: true`. Un ítem que no se calibra se queda en rúbrica-LLM o se retira.
Las tareas de dungeonds antiguas pueden no compilar con el toolchain actual; se anota en `motivo_reproducible`.

## 5. Ítems centinela

- **`td-perf-fps-root-cause`** (macro, dificultad 5) con sus 7 micro `td-perf-fps-*`. Hipótesis del usuario: con un modelo (GPT 5.6) hubo decenas de commits sin efecto real (cache del suelo, dirty rects, ghost trails, "tighten bounds", "remove overhead") y, tras cambiar a Gemini 3.8 Flash, una o dos sesiones arreglaron el rendimiento (~x3 FPS) con menos bugs. Git muestra el corte: 17 sep 23:39 → 18 sep 11:51 los intentos sin ganancia (KNOWN_ISSUES registra pico a 30 FPS) y 18 sep 23:09 → 19 sep 01:23 el profiler, el harness de estrés, dirty blocks 8x8, ITCM, sprites 8 bit, doble buffer VRAM y quads 32 bit. Git no guarda el modelo por commit, así que el ítem lo trata como **hipótesis a contrastar**.
  Lo que se puntúa: ¿mide antes de optimizar (perfila por etapas) o repite micro-optimizaciones? Es el patrón "mucho esfuerzo sin efecto" que el benchmark debe detectar. Se añade una puntuación de proceso: nº de iteraciones sin mejora medida antes de cambiar de hipótesis.
  Ojo con las unidades: en towerds el presupuesto aparece como 545 en el HUD; la regla vigente es 560190 ticks de `cpuGetTiming()`. Fijar la equivalencia en la calibración.
- **`dd-perf-horda-doble`** (macro, dificultad 5, añadido 2026-11-14): pasar de 24 a 48 enemigos a 60 FPS en la DS sin cambiar el juego. Según el usuario, otro modelo lo intentó antes y no lo resolvió (se quedó en sombras alternadas que parpadean y techo de 18-20 enemigos). Lo resolvió Claude Opus 5.5 coordinando subagentes (`walkthroughs/hw-shadows/`): perfilar por etapas, atacar primero las sombras (43 % del frame) pasándolas al hardware, y después IA, blit, limpieza y picos, cada paso medido A/B. DS: 34-36 ms → 14,3-15,1 ms.
  Lo que se puntúa: ¿llega el modelo a la idea de sacar las sombras de la CPU, o se queda en micro-optimizaciones o en recortes de arte (quitar o alternar sombras, quitar separación)? Certificación solo en DS (G6). **Reproducir:** `python bench/run_item.py calibrate dd-perf-horda-doble` (unos 6 min: base 30,3 ms REJECTED, referencia 15,3 ms ACCEPTED) y `python bench/run_item.py run dd-perf-horda-doble --alias <modelo>`. Punto de partida y solución en la rama `bench/dd-perf-horda-doble` (tags `.../base` y `.../ref`); `git diff bench/dd-perf-horda-doble/base bench/dd-perf-horda-doble/ref` es exactamente la solución. Los finalistas se certifican en la DS (G6).
- **`dd-enemy-death-data-abort`** (dungeonds): refactor del camino de muerte que dio `data abort` en DS con build y tests en verde. Solo valida un humano en hardware (G6); sirve para medir si el modelo declara resuelto sin evidencia.
- **Mejores micro para empezar** (oráculo automático y reproducibles `si`): `td-perf-fps-stress-harness`, `td-purge-legacy-turrets`, `dd-gameplay-los-refactor`, `dd-v02-manadas`, `dd-v02-modificadores`, `td-dial-steps-hold-gate`.

## 6. Cómo crece (el benchmark vivo)

- **Regla de entrada**: cualquier problema que (a) cueste más de 3 intentos o commits sin efecto, (b) provoque una corrección del usuario o un bug posterior, o (c) obligue a cambiar de modelo, se convierte en ítem con: `base_commit` (antes del problema), `problema` (redactado como síntoma, sin solución), solución de referencia (commit o diff), puertas y trampas. El `walkthrough` de la sesión es el lugar natural donde dejar los tres datos.
- **Plantilla**: copiar un `item.json` existente de su misma clase. Añadir con `git` el hash base **antes** de arreglar el problema; si no se hizo, el hash del último estado malo conocido.
- **Retiro**: ítem que pasan todos los modelos con 3/3 en 3 rondas deja de rotar y queda de regresión; los nuevos modelos se prueban primero en los ítems "frontera" (20-80 % de aciertos).
- **Delegaciones reales** (tareas no sintéticas) se registran en el ledger con clase, tokens y si hubo corrección del usuario; alimentan las mismas estadísticas pero no sustituyen a los ítems calibrados.

## 7. Trampas y límites

- Contaminación: el modelo puede conocer los repos o ver commits futuros; usar `git archive` del padre.
- Modelos de otros proveedores (DeepSeek, Qwen, GLM, MiniMax…) solo si se pueden lanzar con `delegate.py`; hoy no hay alias.
- El emulador no certifica FPS (regla 6 de AGENTS). Los ítems `perf-hw` se puntúan en emulador para filtrar y en DS para confirmar los finalistas.
- Escenarios con nombre engañoso (regla 5): auditar la geometría de cada escenario usado como oráculo.
- Juez LLM nunca como único oráculo si existe uno automático.
- Muestras pequeñas: con k=3 y pocos ítems por clase, diferencias de menos de 20 puntos no son señal.
- WSL en frío tarda ~28 s: calentar antes de medir tiempos.
- Los ítems de arte y diseño (`arte-impl` parcial, `diseno`) dependen de rúbrica y juicio humano; tratarlos aparte.

## 7b. Arnés: estado (2026-11-07)

`bench/run_item.py` ya funciona para un ítem: `python bench/run_item.py run <id> --alias luna:medium` (prepara copia limpia del commit base, lanza el agente con `delegate.py`, aplica el overlay y puntúa build, escenarios y métricas de pantalla) y `calibrate <id>` (base debe fallar, solución debe pasar). Resultados en `bench/results.jsonl`; artefactos en `.worktrees/bench-runs/`.
- **Modo por defecto: sandbox sin toolchain.** Luna edita y no puede compilar; califica el evaluador. `--toolchain` (Codex sin sandbox) está desactivado por defecto: el clasificador de seguridad de Claude Code lo bloqueó y solo debe usarse con permiso explícito.
- **Primer ítem calibrado:** `td-dial-steps-hold-gate`. La calibración destapó que los escenarios originales eran un oráculo débil (la base con el bug también pasaba); se añadió `oraculo_auto` con medidas sobre capturas (longitud de la barra de munición). Cubre 1 de 3 conductas.
- **Lección para el resto**: calibrar es obligatorio; las puertas heredadas (`screen_changed`, tests espejo en Python) pueden aceptar el código con el bug.
- Primer resultado: luna:medium ACEPTADO, 188 s, 894k tokens de entrada, 6k de salida, sin compilar.

## 8. Próximos pasos

1. Revisar los centinelas y 10-15 ítems a mano (el usuario decide cuáles entran en la primera ronda).
2. Escribir `bench/run_item.ps1` (worktree base → modelo → overlay → puertas → ledger) y el prompt del juez.
3. Calibrar los micro con oráculo automático.
4. Primera ronda: ~15 micro × {haiku, sonnet, opus, luna:medium, luna:high, flash, argon} × k=3, más los 2 centinelas con los modelos que pasen los micro.
5. Tabla clase → modelo; revisar las reglas de "Subagentes y Modelos" de AGENTS.md con datos.
