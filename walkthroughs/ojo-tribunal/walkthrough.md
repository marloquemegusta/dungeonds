# Ojo del Tribunal: cabeza abierta y carga de sentencia

**Rama:** `feat/ojo-tribunal`  
**Fecha:** 2026-11-14  
**Diseño:** [`DESIGN.md` §6.10](../../DESIGN.md)

## Cambios

- Se usa la cabeza abierta nueva del inbox (`tripo_convert_5f17753f-45e7-4137-b616-5fe4530a11f8`) adjunta a la mano, a 150 % de la escala de la cabeza anterior. El punto de agarre se conserva.
- El FBX de la cabeza contiene una sola malla estática, sin clips. Caminar, mirar y sentenciar siguen viniendo de las animaciones del cuerpo y la cabeza acompaña al hueso de la mano.
- El cuerpo del Ojo mantiene el tamaño acordado y se ve más grande que el protagonista. La sombra conserva su huella de suelo y el volumen de impacto acompaña la escala.
- Durante el segundo de fijación, la boca pasa de apagada a muy brillante: el aura verde irregular crece pegada a la boca y las lenguas ascendentes aparecen al final. El efecto ya no forma una cruz de puntos.
- Al terminar la fijación, el cono del suelo se estrecha durante 0,5 s y el haz sale hacia la dirección fijada; el jugador puede esquivarlo y una columna lo anula.
- El haz de sentencia ahora tiene 3 px de ancho y se dibuja debajo de los actores; las siluetas lo ocluyen según su profundidad.

## Captura de la ROM

Vídeo compuesto únicamente con capturas reales de DeSmuME del escenario sandbox, frames 040–070: un segundo de carga, medio segundo de cierre y el disparo. Muestra la escena completa a 4× vecino más próximo a la izquierda y un recorte del Ojo a 8× a la derecha; 20 fps. Se regeneró tras afinar el haz y corregir su oclusión por los actores.

![Cabeza nueva y carga progresiva de la boca en la ROM](assets/nueva_cabeza_carga_real_4x.mp4)

## Verificación

- Pipeline real de arte completado: Blender adjunta el FBX y el exporter headless del lab genera los sprites usados por la ROM.
- Compilación normal y sandbox: `0` warnings nuevos.
- Tests de host: `16/16` PASS.
- Escenario de ciclo del Ojo: PASS, `enemy_ojo_andar_mirar_sentenciar` (305 frames); la captura actualizada se revisó visualmente, incluido el disparo ocluido por la silueta del héroe.
- Pendiente antes de integrar: medir el coste de render en Nintendo DS física. No se subió la ROM.
