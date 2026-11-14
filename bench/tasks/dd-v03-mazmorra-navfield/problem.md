# Ampliar navegación para un mapa de 1280×1280

La rama experimental de mazmorra necesita navegar un mapa de 1280×1280 en Nintendo DS. Amplía el campo de navegación sin desbordar el tipo de distancia ni aumentar innecesariamente el coste por nodo. La DS carece de FPU y la navegación corre durante el juego; evita división y módulo por nodo y limita el trabajo para que no haya recorridos sin cota.
