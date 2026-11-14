# Corregir oclusión de actores al borde de paredes

Al caminar detrás de paredes y bloques, algunos píxeles del suelo aparecen sobre la silueta del actor o el actor queda mal oculto. Corrige la decisión de oclusión para que use la profundidad y cobertura del píxel correspondiente, conserve la transparencia compartida definida por el diseño y represente el límite caminable cuando el jugador queda oculto. No aumentes el coste de manera que rompa el presupuesto de DS.
