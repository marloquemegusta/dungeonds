# Evitar limpiar y copiar el framebuffer entero

Cada frame el compositor hace trabajo de pantalla completa aunque solo cambien regiones pequeñas. Reduce la limpieza y copia del framebuffer para actores sobre mapas grandes, sin dejar píxeles residuales. Nintendo DS tiene presupuesto de 560190 ticks/frame y no tiene FPU; demuestra que las regiones sucias se marcan y limpian correctamente.
