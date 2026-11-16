# Plan de pruebas de las mejoras (v0.4)

Objetivo: encontrar en qué momento cada forma de jugar deja de ser interesante, se vuelve aburrida, imposible o absurda.

**Reglas:**
- Partidas reales, sin `X` ni invulnerable, salvo en la prueba 5.
- Si a mitad de partida tienes que elegir entre seguir el plan y sobrevivir, sobrevive y apúntalo: eso también es información.

## Qué apuntar en cada partida
En cada punto de control, puntúa de 1 a 5 y añade una frase si algo llama la atención.

| Punto de control | Nivel | Tensión (1 paseo · 5 agobio) | Poder (1 inútil · 5 roto) | Decisión (1 da igual · 5 me lo pienso) |
|---|---|---|---|---|
| Minuto 1 | | | | |
| Primera reliquia (nivel 4) | | | | |
| Minuto 3 | | | | |
| Minuto 5 | | | | |
| Minuto 8 o muerte | | | | |

**Al terminar:** ¿cuánto duraste? ¿Querías otra partida (sí o no)? Y la frase de qué elegirías distinto.

**Alarmas** (apúntalas en cuanto pasen):
- **Aburrido:** más de 1 minuto sin sentir peligro, o eliges cartas sin leerlas.
- **Imposible:** mueres antes del nivel 4, o no puedes hacer nada contra lo que viene.
- **Roto:** limpias la pantalla sin apuntar, o la horda no llega a tocarte.
- **Valle demasiado hondo:** mueres en el minuto siguiente a coger la primera pieza de una build.
- **Carta muerta:** te ofrecen algo que no te sirve en ese momento.
- **No se entiende:** una carta o un efecto que no sabes qué hace al verlo.

## Las partidas
### 1. Ráfaga, la build obvia (la línea base)
Coge solo lo de disparar: Fervor, Prisa, Alcance, y Sed de Ceniza o Lanza de Longinos cuando salgan.
- [ ] ¿Se puede llegar a 8 minutos así? Es la build segura; debería aguantar, pero sin volverse absurda.
- [ ] ¿En qué minuto deja de mejorar? Es su techo.
- [ ] ¿El rayo corto del principio frustra o da tensión?

### 2. A por la Vigilia (quemar barriendo)
Plan: la primera reliquia de fuego que salga (Llama Votiva o Cilicio), después Procesión, Brasa, Rescoldo y Paso, y Martirio si aparece.
- [ ] ¿Salió alguna reliquia de fuego en el nivel 4? Si no, ¿pudiste reconducir la partida?
- [ ] ¿Notaste el valle: peor durante un rato y después despega?
- [ ] ¿Cuándo «se rompe»? Apunta el nivel y el minuto.
- [ ] ¿Procesión te deja seguir el ritmo de la marea, o te come?

### 3. A por el Mártir (kamikaze)
Plan: Llaga Abierta y después Flagelado y Viático, con Paso.
- [ ] ¿Vivir con 1 o 2 corazones da tensión buena o solo frustra?
- [ ] ¿Viático cura lo bastante para sostener el riesgo, o demasiado?
- [ ] ¿Se nota el daño extra al perder vida?

### 4. Sin criterio (el contraejemplo)
Coge siempre la carta del medio, sin leer.
- [ ] Debería salir débil. Si te va igual de bien que en las otras partidas, elegir no importa: alarma.

### 5. Techo de cada build (con trucos)
Con `X` hasta el nivel 16 y `L + R + B`, monta cada build entera y métete en la horda:
- [ ] Ráfaga completa.
- [ ] Vigilia completa con Martirio.
- [ ] Mártir completo.

Pregunta en las tres: ¿es divertido sentirse roto, o aburre a los 30 segundos? Aprovecha para elegir aquí el quemado (A o B), el Auto de Fe (A o C) y el Viático (A o C) con `SELECT`. Esta prueba también sirve para el registro de rendimiento.

## Al acabar
Pásame:
1. Las tablas de cada partida (aunque sea en una foto).
2. Las alarmas que saltaron.
3. Tu lista de ajustes, una línea por cosa.

Yo descargo el registro de rendimiento de la DS, y lo cruzamos todo para decidir los ajustes de una sola vez.
