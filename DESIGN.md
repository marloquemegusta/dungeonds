# DESIGN.md - Documento de Diseño de DungeonDS

## 1. Visión del Juego
Un ARPG cenital/isométrico para Nintendo DS con mazmorras procedurales, ambientación oscura y enfoque central en la **nigromancia**:
- El jugador controla a un nigromante que no lucha únicamente en cuerpo a cuerpo, sino levantando y comandando esbirros de los cadáveres caídos.
- Perspectiva isométrica/cenital (60 grados dimétrica) inspirada visualmente en *Diablo* clásico.

## 2. Dirección de Arte y Sprites
- **Técnica de Renderizado:** Sprites 2D pre-renderizados a partir de modelos 3D esqueléticos (Blender headless + script `render_spritesheet.py`).
- **Resolución de Sprites:** 64×64 o 32×32 píxeles en 8 direcciones de movimiento.
- **Legibilidad:** Siluetas con contorno oscuro de 1px y curvas de contraste marcadas para evitar el empastado en los paneles LCD de Nintendo DS.
- **Herramienta de calibración:** `sprite_lab.html` para auditar escalado nearest-neighbor (4x/8x), rotaciones y paletas.

## 3. Esquema de Controles Previsto (NDS)
- **D-Pad:** Movimiento del Nigromante (8 direcciones).
- **Botón A:** Ataque básico / Proyectil de hueso / magia negra.
- **Botón B:** Resucitar cadáver (invocar esqueleto/zombie).
- **Botón X / Y:** Comandar esbirros (modo agresivo / seguir / defender).
- **Pantalla Táctil:** Inventario, mapa de mazmorra procedural y selección de hechizos.
