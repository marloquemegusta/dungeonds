# Dirección v0.3: survivors de frente vertical

Rama `docs/survivors-direction`. Sesión de diseño, sin código. Decisión en `DESIGN.md` §6 y requisitos técnicos en `TECHNICAL.md` §4.7.

## El problema
La v0.2 (mazmorra de manadas con modificadores) divierte un par de minutos y se queda ahí. El combate funciona a la escala de segundos, pero falla en las otras dos:
- **Una run:** el mapa y las manadas son fijos y los modificadores son números, así que dos runs se juegan igual.
- **Entre runs:** morir no deja nada y no hay meta.

## Qué quiere el usuario
- La dificultad de Isaac: lo normal es morir pronto hasta conocer bien las mejoras y saber elegirlas.
- El gancho de Diablo y Warhammer 40K: Inquisitor: ir a la siguiente misión y mejorar equipo. La historia le da igual.
- Una fantasía clara con entorno cambiante (descenso, ascenso), aunque no haya lore.
- Hacer a mano unas cuantas salas pequeñas, o un sistema de reglas que él pule.
- Apuntado manual como seña del juego.
- Cientos de enemigos a lo largo de la run, pero solo unas pocas decenas a la vez en pantalla.

## Opciones consideradas
| Opción | Resultado |
| :--- | :--- |
| Isaac de salas: pisos con salas por plantillas y jefe | Más barata, pero al usuario le gusta menos que Diablo. Se descarta. |
| Incursión con extracción y armería persistente | Cambia el foco a la gestión. Se descarta. |
| Campaña lineal tipo Diablo | Demasiado contenido a mano que se consume una vez. Se descarta. |
| Descenso con ascensor (subir y cobrar o bajar y arriesgar) | La idea de la decisión por piso queda para la capa de progresión. |
| **Survivors tipo Halls of Torment** | **Elegida.** Junta dificultad, progresión y estética de Diablo. |

## El giro para la DS
Solo se puede tocar la pantalla inferior, así que el jugador va centrado en ella: ve ~96 px detrás y ~288 delante. En vez de pelear contra eso, el mapa es una **franja vertical** y la horda viene de arriba. La **pantalla superior es la vanguardia**: ahí se ve llegar lo que viene y se le puede disparar, lo que premia a las clases de largo alcance. Usarla como menú se descartó por ser menos interesante.

Para que el mapa vertical tenga sentido algo tiene que empujar hacia arriba. Se eligió una **marea que sube** desde abajo, frente a dejar el avance libre (riesgo de farmear quieto) o a un scroll forzado tipo shmup (demasiado rígido). La marea explica además por qué casi no vienen enemigos de abajo.

## Rendimiento: ¿cabe en la DS?
Se revisó cómo maneja hoy el motor los enemigos (detalle en `TECHNICAL.md` §4.7):
- Los enemigos totales no cuestan: con un pool de plazas recicladas, el total de la run no ocupa memoria.
- Lo que cuesta son los enemigos activos y visibles a la vez. Con 8–12 despiertos, la v0.2 ya llegaba a 300–411 k ticks de 560 k por frame.
- El objetivo de 32 visibles y 48 activos parece alcanzable optimizando el compositor actual (IA por niveles de detalle, separación por rejilla, blit en 8 bpp, gemas en OAM). Por eso la **prueba de horda en la DS es el primer paso**: si no llega, se evalúa OAM o el motor 3D para el enjambre.

## Decisiones de valor por defecto
Las propuso el agente y el usuario no las corrigió: velocidad constante de la marea, daño sin muerte instantánea dentro de ella, gemas con imán, 1 de 3 sin reroll, vida por golpes, granada en L común a las dos clases, dos biomas en la prueba. Son puntos de partida y se ajustan jugando.

## Siguientes pasos
`DESIGN.md` §6.9: (1) prueba de horda en la DS y (2) sesión de diseño de contenido, en paralelo; después franja vertical, bucle jugable, enemigos nuevos y tuning.
