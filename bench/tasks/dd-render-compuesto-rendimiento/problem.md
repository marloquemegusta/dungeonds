# Reducir el coste del compositor y la oclusión

El render presenta trabajo costoso por frame y problemas de oclusión de actores. Diagnostica y reduce el coste de limpiar/copiar el framebuffer y reconstruir la oclusión al mover la cámara, manteniendo la imagen correcta. Nintendo DS no tiene FPU y el presupuesto es 560190 ticks/frame. Entrega código, pruebas visuales y perfilado; usa emulador solo para A/B, no para certificar FPS.
