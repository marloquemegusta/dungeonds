# Prompts para las siguientes sesiones (desde la demo para un colega, 2026-11-14)

Decisión de partida: `DESIGN.md` §6.9.1c. Orden recomendado: primero el menú (deja el hueco del bestiario), después el bestiario.

---

## Sesión A: menú inicial y pausa

```
Sesión nueva: menú inicial y menú de pausa de DungeonDS. Lee AGENTS.md, STATUS.md y DESIGN.md §6.9.1c, §6.3 y §6.10.

Objetivo: al arrancar la ROM aparece una pantalla inicial con tres botones: NUEVA PARTIDA, BESTIARIO y CONTROLES. Durante la partida, START abre el mismo menú como pausa (con "Continuar" en lugar de "Nueva partida", más "Reiniciar"; confírmalo conmigo). El bestiario de esta sesión es solo un placeholder ("Próximamente") con la navegación de entrar y volver ya hecha, para que la sesión del bestiario solo rellene contenido.

Antes de programar (regla 9 de AGENTS.md), propónme en lenguaje de producto, con una sola pregunta por turno:
1. Qué pantalla muestra qué: menú abajo (táctil) y arte/título arriba, o al revés.
2. Cómo se navega: lápiz, cruceta + A/B o ambos.
3. Estilo visual de los botones y del título, coherente con la catedral y la paleta FX_SH_* (marfil, oro antiguo, ámbar, carmesí). Enséñame 2-3 maquetas baratas para elegir, sin dar ninguna por evidencia de juego.
4. Texto de la pantalla de Controles: lápiz para apuntar y mantener para cargar el láser, cruceta para moverse, SELECT y Y para comparar efectos (son para la demo), START para pausa.
Escribe la decisión en DESIGN.md y solo entonces implementa.

Cuidado con lo que ya existe: START hoy reinicia tras morir; SELECT y Y cambian efectos y deben seguir funcionando en partida; la pausa congela horda, marea, música (o la baja) y temporizador; no puede costar frames en partida.

Flujo: worktree feat/menu-inicial; implementación delegada en subagentes con modelo indicado (AGENTS.md "Subagentes y Modelos"); compilación sin warnings, tests de host, un escenario headless que entre en el menú, pase a partida, pause con START y vuelva (geometría y nombres verídicos), capturas de la ROM real; medir en la DS con PERF_PROFILE que la partida sigue a 60 FPS. Walkthrough en walkthroughs/menu-inicial/ y entrada en STATUS.md.
```

---

## Sesión B: bestiario (gráficos y lore)

```
Sesión nueva: bestiario de DungeonDS. Lee AGENTS.md, STATUS.md, DESIGN.md §6.9.1c y §6.10 (reparto de personajes), y walkthroughs/concepto-demo-personajes/. Requiere que el menú inicial con el botón BESTIARIO (placeholder) ya esté en main; si no, para y avísame.

Objetivo: sustituir el placeholder por un bestiario jugable desde el menú: una ficha por enemigo con su sprite animado (los frames que ya exporta el lab en assets/sprites/characters/<nombre>/), nombre, una línea de comportamiento ("embiste en línea recta tras agacharse") y un párrafo corto de lore. Enemigos: esqueleto, El Cireneo (cargador), el tirador (hoy necron; El Ojo del Tribunal si su rama ya está en main) y El Exvoto si está integrado. Incluye también al héroe, El Corazón Abierto, como primera ficha.

Antes de programar (regla 9):
1. Lore: propónme el tono y un borrador por personaje (iconografía de Semana Santa / catedral gótica / exvotos y tribunal, coherente con §6.10). Yo lo corrijo; nada de texto final sin mi visto bueno.
2. Maquetación: qué va arriba (sprite grande girando en 8 direcciones o en su animación de ataque) y qué abajo (texto y navegación). Enséñame 2-3 maquetas baratas para elegir.
3. ¿Se desbloquea al encontrar al enemigo o está todo visible? Para la demo recomiendo todo visible; pregúntamelo.
Una sola pregunta por turno. Escribe las decisiones en DESIGN.md y solo entonces implementa.

Técnico: la fuente actual es la de depuración; si hace falta una fuente nueva con acentos y ñ, propónla. Vigila ROM y RAM (TECHNICAL.md §3.3): reutilizar los sprites ya en ROM, no duplicarlos. El bestiario no corre durante la partida, así que no toca el presupuesto de frame, pero sí debe entrar y salir sin tirones.

Flujo: worktree feat/bestiario; implementación delegada en subagentes con modelo indicado; compilación sin warnings, tests de host, escenario headless que recorra todas las fichas con captura de cada una (mirarlas a 4x NEAREST de verdad), prueba en la DS. Walkthrough en walkthroughs/bestiario/ y entrada en STATUS.md.
```
