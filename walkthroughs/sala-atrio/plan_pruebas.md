# Partida de referencia: ¿el juego divierte hoy? (2026-11-18)

**Qué se mide:** cuánto divierte la partida tal como está, sala por sala, antes de rediseñar nada. No se mide ninguna mecánica en concreto: el remate, el Ojo y el flanqueo salen en la partida como una cosa más y se comentan solo si llaman la atención.

**Para qué sirve:** da una línea base y ordena las salas de peor a mejor. La peor es la primera que se rediseña con las reglas de `DESIGN.md` §6.13.9, y esa es la prueba de la vuelta siguiente (método en §6.13.10).

**Reglas:** ROM normal de `main`, sin invulnerabilidad ni teclas de depuración, sin leer nada antes. Si a mitad de sala tienes que elegir entre seguir el plan y sobrevivir, sobrevive y apúntalo.

## Qué apuntar en cada sala
Puntúa de 1 a 5 al salir de cada sala y añade una frase si algo llama la atención. Si la ROM no te dice qué sala es, usa el orden (1.ª, 2.ª, …) y una palabra para reconocerla (por ejemplo «bancos» o «sacos»).

| Sala | Tensión (1 paseo · 5 agobio) | Decisión (1 da igual · 5 me lo pienso) | ¿Repetirla? (sí/no) | Frase |
| :--- | :--- | :--- | :--- | :--- |
| 1.ª | | | | |
| 2.ª | | | | |
| 3.ª | | | | |
| 4.ª | | | | |
| 5.ª | | | | |
| 6.ª | | | | |

## Alarmas (apúntalas en cuanto pasen)
- **Aburrido:** más de 30 s sin sentir peligro, o esperas a que lleguen los enemigos.
- **Injusto:** te hieren sin haber podido verlo venir.
- **No entiendo:** no sabes qué hace un enemigo o por qué moriste.
- **Roto:** limpias la sala sin apuntar o sin moverte.
- **Esperar gana:** te quedas atrás y matar lo que llega sale gratis.

## Al terminar (10 min o muerte)
1. ¿Cuánto duraste y hasta qué sala llegaste?
2. ¿Querías otra partida? (sí/no)
3. La mejor sala y la peor, con una frase cada una.
4. ¿Qué cambiarías primero?

## Registro (se rellena tras la prueba)
| Fecha | Versión (commit de `main`) | Duración | Mejor sala | Peor sala | ¿Repetir? | Sala a rediseñar primero |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| | | | | | | |

## Resultados (2026-11-18)

**Vuelta 0, ROM de `main` sin cambios del Ojo:** no se jugó a fondo; sirvió de «antes».

**Vuelta 1, `feat/ojo-alcance` (Ojo sin alcance, un Ojo en todas las salas):** dos partidas; la segunda llegó más lejos. Murió en la tercera pantalla.
- **Primera sala:** mucho mejor con el Ojo. Obliga a cubrirse con las columnas y se siente más la necesidad de usar la ejecución para ganar invulnerabilidad temporal.
- **Segunda sala:** bastante dura, «el Ojo es muy cabrón, me gusta». Los Exvotos se sienten peleones.
- **Problema 1:** la mitad de arriba casi no se usa. Los Exvotos bajan y, aunque subas, arriba solo queda el Ojo; se sube solo para ir a matarlo cuando ya no quedan Exvotos.
- **Problema 2:** el Ojo está demasiado estático: no se mueve para buscar ángulo cuando una columna le corta la línea.
- **Falta:** la cobertura baja tras bancos y sacos (rama `feat/coberturas-bajas`, no integrada).
- **Propuestas del usuario:** (a) IA del Ojo que se recoloque para darte pese a las columnas; (b) Exvotos y Cireneos arriba guardando al Ojo.

**Vuelta 2 (guarnición, recolocación del Ojo, cobertura baja de `main`):** el Ojo no se movía nunca; con una recolocación más rápida «tarda muchísimo en llegar»; tras volverlo tirador táctico (espera cubierto, te sigue tras columnas) «mucho mejor». Falló que al levantarte tras estar cubierto «te pilla siempre»: se cambió a ciclo completo de apuntado al salir de la cobertura (**sin jugar en la DS**). Sin tirones apreciados.
- **Pendiente de decidir:** el Ojo anda a un tercio de la velocidad del héroe (mantiene la línea ~57 % del tiempo moviéndote); palancas: velocidad de persecución y tiempo parado al apuntar.
- **Pendiente:** repetir la partida de referencia completa con esta ROM y elegir la sala a rediseñar primero.
