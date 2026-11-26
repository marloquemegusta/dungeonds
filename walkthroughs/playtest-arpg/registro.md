# Registro de playtests del ARPG (acto I)

Cada partida del usuario en la DS: qué ROM, qué notó, qué se hizo. La más reciente arriba.

## Partida 1 — 2026-11-26

**ROM:** `feat/pulido-final` e6280e9a (16 salas del póster, luz por sala, aviso antes del mordisco, monja curandera, arreglo de la Nave 3).

| # | Sala | Feedback del usuario | Tipo | Estado |
|---|---|---|---|---|
| 1 | Galería del cofre | Los props parecen al azar: hay pocos de la entrada hacia arriba y casi todos están hacia abajo. Los sacos de arriba también parecen al azar. | Disposición | Arreglado: cepos a la izquierda y sacos a la derecha, repartidos de arriba abajo (fix/pt1-galeria) |
| 2 | Galería del cofre | La sala parece infinita hacia abajo y te sales del mapa. | Fallo | Arreglado: muro invisible al sur en todas las salas. Al sur se sigue viendo suelo; falta decidir si se dibuja una pared (fix/pt1-galeria) |
| 3 | Galería del cofre | Los cepos no se entienden: habría que rediseñarlos o recolorearlos. | Arte | Decidido: de frente y recoloreado. Ya se veía de frente; se le ha subido el contraste entre madera y agujeros. La mejora es moderada: verlo en la DS (fix/pt1-cepo) |
| 4 | Galería del cofre | Las ejecuciones y el boxeo no usan la luz de la sala; parecen usar la de la nave principal. | Fallo | Arreglado el puñetazo, que ahora se tiñe con la luz de la sala. Los remates ya salían con la luz de la sala en las capturas: si en la DS se siguen viendo mal, decir con qué enemigo (fix/pt1-luz) |
| 5 | Nave 1 | Las sombras de los bancos apuntan hacia el centro (unas a la derecha y otras a la izquierda), pero la del héroe siempre apunta a la derecha. | Fallo | Arreglado: las piezas espejadas ya no voltean su sombra. Se han regenerado las 7 salas que las tienen (fix/pt1-luz) |
| 6 | Nave 2 y otras | Los enemigos no se activan o no son vulnerables hasta que estás cerca: el Ojo no ataca desde el principio, solo tras derrotar a los Monaguillos y acercarte. El rayo a los Bebés de lejos a menudo no hace nada. | Fallo o diseño | Arreglado en parte: los enemigos dormidos ya reciben daño, y golpear o matar a uno despierta a su grupo. El Ojo de la Nave 2 estaba de guardia y no se soltaba nunca; ya no. Rayo: el haz y el daño ya coincidían (en vertical el haz mide la mitad en pantalla por la perspectiva). Los fallos de lejos eran los Bebés dormidos. Quedan escenarios que lo vigilan (fix/pt1-rayo) |

**ROM para la partida 2:** `feat/pulido-final` 2139a85a (todo lo anterior integrado; bot llega a la cripta).
| 7 | — | Los Ojos no llegan a quedarse tambaleantes. | Fallo | Arreglado: solo tambaleaban mientras perseguían, no mientras apuntaban o disparaban (fix/pt1-ojo) |
