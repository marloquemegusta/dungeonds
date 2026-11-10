# Catedral 0.3.2: análisis de siguientes pasos

**Fecha:** 2026-11-10
**Punto de partida:** `main` tras fusionar `feat/muros-catedral`. La oclusión y la colisión de los props están resueltas (`walkthroughs/props-depth-units/`).
**Formato:** una sesión por paso. Cada sesión la dirige un coordinador (Claude), que da el brief a Luna, revisa su diff, compila, pasa los tests y escenarios, y enseña capturas al usuario. Luna no puede ejecutar Python, Docker ni WSL (`AGENTS.md`, «Límite de los agentes Codex»).

## Dónde estamos

| Área | Estado | Hueco |
|---|---|---|
| Suelo, muros, lancetas, crucero | En ROM; estética general aceptada | Arte de muro provisional (pixel art de primer pase) |
| Godrays | Integrados; el usuario los da casi por buenos | Todos los haces salen de muros laterales; el rosetón del crucero no emite el suyo y falta la prioridad entre haces |
| Oclusión y colisión de props | Resueltas y dadas por buenas en la DS | Solo la columna y el banco roto tienen escenario; los demás props no tienen prueba reproducible |
| Distribución de bancos y estatuas | **No aprobada por el usuario** | El generador pone de 1 a 4 piezas sueltas por banda, por hash; no hay bloques de bancos ni familias de tramo |
| Presupuesto del kit | 1.024 de 1.024 tiles, 224 en la peor ventana | No cabe ninguna pieza nueva; `test_strip_kit.py` está desfasado |
| Rendimiento | Jugable a 60 FPS según el usuario | No hay log `PERF_PROFILE` de la build final |

## Orden y por qué

1. **[Banco de pruebas de props](brief-01-banco-pruebas-props.md).** Hace falta antes de mover la distribución. Hoy cada escenario depende de dónde caen los props con una semilla concreta, y cualquier cambio de layout rompe las coordenadas. Una variante con los seis props físicos en posiciones fijas da una regresión estable para colisión y oclusión.
2. **[Distribución de bancos y estatuas](brief-02-distribucion-props.md).** Es lo que el usuario no aprueba. Empieza con una **decisión del usuario** (regla 9): se le enseñan alternativas y solo se programa la elegida.
3. **[Emisores de godrays](brief-03-godrays-emisores.md).** Las reglas ya están escritas en `DESIGN.md` §6.9.1b: lanceta en el muro lateral, rosetón frontal en el crucero y un solo haz por pantalla en el crucero. Es independiente de los pasos 1 y 2.
4. **[Presupuesto del kit y deuda de tests](brief-04-presupuesto-kit.md).** Libera tiles antes de sustituir el arte provisional de los muros y antes de añadir piezas. Arregla el test desfasado y regenera la profundidad de las lápidas.
5. **Certificación en la DS.** No es trabajo de Luna. El coordinador compila `cathedral-playground-perf` con todo lo anterior y el usuario juega 2–3 minutos subiendo. Se lee `/dungeonds_perf.log` (media, máximos y frames con más de un vblank, regla 6) y se vuelve a dejar `PERF_PROFILE 0`. Cierra la 0.3.2 junto con la aprobación visual del usuario.

Los pasos 3 y 4 pueden ir en paralelo con el 1 o el 2, porque no tocan los mismos archivos. El paso 2 necesita el 1 terminado.

## Fuera de esta lista

- **Arte definitivo de muros, lanceta y rosetón:** prerender con Blender y el lab. Necesita referencias y aprobación del usuario, así que no encaja con un agente sin criterio.
- **Profundidad del lab por debajo de 0,25 m:** sería la fuente limpia para los props bajos, pero exige los `.glb` de los props, que no están en el repo.
- **0.3.3 (personajes):** tras cerrar la 0.3.2.

## Plantilla común de los briefs

Cada brief incluye: objetivo, contexto mínimo, archivos, pasos, restricciones, criterio de aceptación y los comandos que ejecuta el coordinador. Restricciones que se repiten en todos:

- Trabajar solo en el worktree que indique el coordinador. Nada de commit, merge ni stash.
- C sin `float` ni `double`; punto fijo; sin `/` ni `%` en bucles calientes (`AGENTS.md`, regla 2).
- No inventar comportamiento visual o de juego sin decisión escrita en `DESIGN.md` (regla 9). Ante la duda, parar y preguntar.
- Intentar una sola vez Python, Docker o WSL; si no arrancan, entregar los comandos sin reintentar.
- Entregar: lista de archivos tocados, resumen de cada cambio y comandos de verificación.
