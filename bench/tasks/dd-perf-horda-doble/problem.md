# Duplicar la horda manteniendo 60 FPS en la DS

El juego mantiene 60 FPS en una Nintendo DS física con la horda normal (24 enemigos). Se quiere el doble, unos 48 enemigos a la vez, a 60 FPS en la consola y sin cambiar el juego, o cambiándolo lo mínimo.

Medido en la DS: con 48–72 enemigos el frame cuesta 34–36 ms (20 FPS) y el presupuesto es 16,7 ms. Sin sombras, cuesta 17–21 ms (30–38 FPS). El desglose está en `walkthroughs/stress-enemies-profiling/walkthrough.md`.

Requisitos:
- Mantener la forma y el tono actuales de las sombras de héroe y enemigos, la oclusión tras muros y piezas, la marea y el comportamiento de los enemigos. Si propones una diferencia visible, escríbela como decisión en `DESIGN.md` y justifícala.
- Sin `float`/`double` en tiempo de ejecución y sin warnings nuevos.
- Una forma reproducible de cargar 48 enemigos y medir por etapa, tanto en el emulador (solo comparativo) como en la DS.
- Ningún pico de un solo frame (avanzar por la franja, láseres, muertes en masa) debe pasarse del presupuesto con la horda llena.
