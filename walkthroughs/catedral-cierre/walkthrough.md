# Cierre de revisión de la primera ROM de catedral

**Fecha:** 2026-11-10
**Rama:** `feat/muros-catedral`
**Estado:** primera pasada jugable; escenario todavía abierto.

## Conseguido

- Suelo, muros laterales, lancetas y crucero integrados en el kit de la franja y compilados en la variante de catedral.
- Godrays integrados en `cathedral-playground` y `cathedral-playground-perf`. El usuario considera que esta parte está prácticamente hecha.
- Retirados los efectos de lectura a través del muro: parpadeo/transparencia y línea negra.
- La ROM `cathedral-playground-perf` se subió como `dungeonds.nds` y se probó en la DS. El usuario encuentra bien el rendimiento y la estética general.
- El primer layout y su propuesta de recorrido están documentados en [layout-catedral](../layout-catedral/walkthrough.md); la primera pasada de muro, en [muros-catedral](../muros-catedral/walkthrough.md).

## No cerrado

- **Distribución:** al usuario no le convence cómo aparecen bancos y estatuas. Hay que rehacer la composición y verla en una secuencia reproducible.
- **Colisión y oclusión:** el usuario confirma que siguen mal en la DS. La implementación actual hornea color al tilemap, huellas desde `footprint.png` y profundidad desde `depth.png`. Que compartan tamaño y desplazamiento al estamparse no demuestra que compartan cámara, escala y origen con la geometría visible.
- **Diagnóstico pendiente:** se preparó una prueba de ocho direcciones, pero las capturas no demostraron que el marine alcanzara la estatua. Se eliminó esa prueba y no se usan sus resultados. El escenario de contacto anterior solo cubría su caso concreto y no acredita el comportamiento general.
- **Certificación:** falta guardar un log `PERF_PROFILE` de la configuración final en hardware.

## Próxima sesión

1. Fijar una semilla/composición y verificar en capturas que cada posición de prueba cae sobre el prop correcto.
2. Revisar desde la raíz el pipeline de props. Preferencia a evaluar: generar color, profundidad y huella desde la misma escena GLB, cámara y referencia de suelo, con pruebas de coherencia entre canales.
3. Corregir la distribución de bancos y estatuas; mantener los tres corredores como condición geométrica.
4. Crear y ejecutar escenarios que crucen la huella real desde ocho direcciones y comprueben que el sprite se oculta al pasar detrás y reaparece delante.
5. Cuando eso esté correcto, repetir build y validación de rendimiento en la DS.

## Evidencia y límites

Los escenarios, builds y capturas de las pasadas anteriores permanecen en sus walkthroughs respectivos. La observación actual de fallo procede de la revisión del usuario en DS; no se afirma que la prueba de ocho direcciones haya reproducido el problema.
