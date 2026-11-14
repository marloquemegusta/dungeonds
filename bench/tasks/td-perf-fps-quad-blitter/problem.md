# Optimizar transferencias de píxeles y restauración de bloques

La restauración del fondo y el blit de sprites mueven muchos píxeles durante una oleada. Optimiza las rutas de copia en ARM9 y la restauración por bloques, sin omitir contenido ni dejar rastros.
