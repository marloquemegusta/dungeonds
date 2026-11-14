# Mostrar daño no letal como desmembramiento progresivo

Los impactos no letales no alteran visiblemente la silueta enemiga. Haz que el daño acumulado arranque partes del borde del sprite y lance esos mismos píxeles como restos, respetando paleta, salud restante y coste de CPU en DS. Evita fragmentos flotantes y reinicia el estado al reutilizar una ranura de enemigo.
