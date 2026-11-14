# Diagnosticar y eliminar la caída de FPS bajo carga máxima

En una Nintendo DS sin FPU, el pico de enemigos reduce el juego a unos 30 FPS o menos. Las optimizaciones existentes de caché del suelo, dirty rects y bucles de blit no han demostrado resolverlo y algunas dejan rastros visuales. Diagnostica con mediciones reproducibles qué etapas consumen el frame y entrega una mejora que mantenga 60 FPS bajo una carga máxima, sin degradar la imagen ni el combate. Incluye un perfil de estrés estable y repetible.
