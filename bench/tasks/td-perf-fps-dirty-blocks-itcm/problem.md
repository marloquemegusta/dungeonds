# Reducir restauraciones repetidas del fondo en el renderer inferior

En la DS, el renderer restaura zonas del suelo varias veces cuando muchos enemigos se mueven. Reduce el trabajo redundante bajo estrés, conservando movimiento, colisiones e imagen correcta. Mantén las restricciones ARM9 y evita usar coma flotante.
