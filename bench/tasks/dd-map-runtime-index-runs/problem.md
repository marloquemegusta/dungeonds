# Consultar oclusión visible sin picos de coste

El aumento de runs de profundidad eleva el trabajo al mover la cámara; el escaneo completo puede provocar picos y caídas de FPS. Optimiza la consulta para procesar solo las filas y runs visibles y evita que suelo oscuro se interprete como vacío. Mantén la colisión como fuente única de suelo.
