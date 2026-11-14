# Fallar ante pasos inválidos y soportar tap_grid

El runner ignora claves desconocidas en pasos de escenario, por lo que una acción mal escrita o específica de un fork puede omitirse y dejar que la prueba aparente pasar. Añade validación estricta previa a iniciar el emulador y una acción genérica para tocar varios puntos de una cuadrícula manteniendo botones opcionales.
