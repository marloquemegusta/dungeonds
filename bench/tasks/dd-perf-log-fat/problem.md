# Persistir el tamaño del log de rendimiento en SD

La ROM de perfilado escribe muestras en la SD, pero el archivo no refleja el tamaño actualizado cuando se consulta durante la sesión. Corrige la persistencia con la API FAT disponible sin perder las muestras. El perfilado debe seguir apagado por defecto para la ROM normal.
