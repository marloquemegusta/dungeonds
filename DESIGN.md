# DESIGN.md - Documento de Diseño

## 1. Visión y Alcance Confirmado
- **Concepto:** Juego para Nintendo DS similar a Diablo (vista cenital/isométrica) procedural y centrado en la temática de nigromancia.
- **Objetivo actual:** Diseñar el setup gráfico inicial y elegir assets estéticos para montar la demo técnica donde se puedan mover personajes en 8 direcciones.

## 2. Dirección de Arte y Pipeline Confirmado
- **Técnica:** Sprites 2D pre-renderizados a partir de modelos 3D con animaciones esqueléticas (FBX / Blender).
- **Proyección:** Isométrica / dimétrica a 60 grados en 8 direcciones.
- **Herramienta de tuning:** `sprite_lab.html` para auditar escalado nearest-neighbor (1x, 2x, 4x, 8x), filtros de legibilidad (contorno oscuro, contraste) y animación en el sitio (*in-place*).
- **Efecto de lanza ósea:** astillas estrechas y puntiagudas dibujadas proceduralmente, sin outline, con motas espectrales irregulares en lugar de sprites idénticos horneados.

## 3. Decisiones Abiertas / Pendientes de Definición
- Mecánicas de juego y controles concretos: Pendiente de definición por el usuario.
- Generador procedural de mazmorras: Pendiente de definición por el usuario.
- Estructura y reglas del bucle de combate y nigromancia: Pendiente de definición por el usuario.
