# Reducir el coste del pase de oclusión y blit

La oclusión exacta al píxel corrige los actores, pero su pase de render consume tiempo. Reduce el coste de oclusión, sombras, base de pared y blit manteniendo el resultado visual correcto. Respeta 560190 ticks/frame y valida en hardware; el emulador solo sirve para comparar A/B.
