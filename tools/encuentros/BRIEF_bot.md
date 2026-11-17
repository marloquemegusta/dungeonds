# Brief: bot de prueba para el prototipo de encuentros (variante `encuentros`)

Worktree `C:\codexlocal\dungeonds\.worktrees\encuentros-acto1` (rama `feat/encuentros-acto1`). No hagas commit. Reglas de `AGENTS.md`: sin `float`/`double`, sin warnings nuevos. El prototipo de encuentros ya existe en esta rama (lee `DESIGN.md` §6.13.6, `tools/encuentros/acto1.json`, el código con `ENCOUNTERS_PROTO` y la estructura `g_enc_stats` / `g_enc_debug`).

## Objetivo
Un **autopiloto dentro de la ROM** (solo con un define `ENC_BOT=1`, en una variante nueva `encuentros-bot` de `.ds-game-dev/project.json`) que juegue el acto I como un jugador prudente, para medir dificultad sin humano. Inyecta la entrada donde el juego lee cruceta y lápiz (no simules hardware: sustituye el valor leído).

Comportamiento por frame, en este orden de prioridad:
1. **Esquivar al Ojo:** si un Ojo está en TRACK/LOCK con su línea sobre el héroe, moverse perpendicular a esa línea (y hacia una columna/estatua si hay una a < 48 px).
2. **Esquivar al Cireneo:** si uno está en TELEGRAPH/CHARGE hacia el héroe, moverse de lado (perpendicular).
3. **Distancia con cuerpo a cuerpo:** si el enemigo cuerpo a cuerpo más cercano está a < 40 px, alejarse (vector opuesto, sin salir del suelo; si está bloqueado, de lado).
4. **Disparar:** blanco = enemigo despierto más cercano con línea de visión y dentro del alcance del rayo; en un pasillo, el relicario sin romper. Apuntar con el lápiz a él, mantener hasta carga completa y soltar.
5. **Avanzar:** sin blanco al alcance y el encuentro sin limpiar, subir hacia el enemigo más cercano hasta quedar a ~120 px. Encuentro limpio: subir. En el pasillo, primero romper el relicario.
6. **Atasco:** si la posición no cambia en 60 frames, moverse de lado 30 frames.

Ofertas de Don/Reliquia: elegir al azar entre las 3 con una semilla fija (`g_enc_debug.seed`), no siempre la primera.

## Métricas
Amplía `g_enc_stats` si hace falta: por encuentro, frames hasta limpiar, golpes recibidos, vida al terminar, planta y tier; total de frames del acto; Dones cogidos; resultado (victoria / muerte y en qué encuentro).

## Escenarios (`"suite": false`, todos)
- `scenarios/encuentros_bot_natural.json`: progresión normal (Dones de los relicarios), semilla 1. Corre hasta victoria, muerte o 30000 frames. Captura cada ~600 frames y en cada encuentro despierto (3-4 capturas por encuentro como mucho).
- `scenarios/encuentros_bot_sin_mejoras.json`: igual pero sin coger Dones (`g_enc_debug`), para el suelo de dificultad.
- `scenarios/encuentros_bot_fuerte.json`: empieza con 10 Dones aplicados.
Cada uno vuelca `g_enc_stats` con `state_capture` al final. Ejecuta los tres con `run-scenario.ps1` (`powershell -NonInteractive -ExecutionPolicy Bypass -File C:\codexlocal\skills\agentic-ds-dev\scripts\run-scenario.ps1 ...`, lee sus parámetros) y entrega una tabla por escenario: encuentro | planta | tier | segundos | golpes | vida al acabar, más duración total y resultado. Mira tú algunas capturas para comprobar que el bot hace algo sensato (no se queda pegado a un muro, dispara a los enemigos).

## Entrega
Archivos tocados, las tres tablas, rutas de 4-6 capturas representativas, y lo que el bot hace mal (para saber cuánto fiarse de las cifras).
