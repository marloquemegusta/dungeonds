# Sesión: Sistema de Niebla de Guerra (Fog of War), Línea de Visión y 60 FPS Locked

## Objetivo
Implementar el sistema integral de visibilidad, radio de luz y niebla de guerra (*Fog of War / Line of Sight*) inspirado en *Diablo* y *Doom* para Nintendo DS:
1. Las habitaciones no exploradas permanecen en oscuridad absoluta (vacío negro).
2. Los muros y esquinas bloquean estrictamente la visión; las puertas y arcos proyectan conos de luz hacia el interior.
3. Los enemigos situados detrás de esquinas, en otras habitaciones o fuera del radio de luz son **100% invisibles** y no se dibujan.
4. Las áreas ya visitadas permanecen en la memoria del jugador en penumbra (trama retro al 50%), permitiendo la orientación sin revelar entidades dinámicas.
5. Todo el cómputo se ejecuta en punto fijo a **60 FPS bloqueados constantes** en el hardware ARM9 de la Nintendo DS.

---

## Arquitectura del Sistema de Visibilidad

### 1. Rejillas de Memoria en EWRAM (`include/fog_of_war.h`)
- **Resolución:** $96 \times 64$ tiles de $8 \times 8$ píxeles (tamaño completo del mundo $768 \times 512$).
- **Mapas de Bits (768 bytes cada uno):**
  - `g_fog_explored[768]`: 1 bit por tile. Registra de forma permanente los tiles descubiertos por el jugador (memoria cartográfica).
  - `g_fog_visible[768]`: 1 bit por tile. Registra los tiles en línea de visión directa en el fotograma actual.

### 2. Raycaster Bresenham sin Divisiones (`source/fog_of_war.c`)
- **Radio de Luz:** 24 celdas de colisión (~96 píxeles de mundo, ~5 metros tácticos).
- **Emisión Circular:** 64 rayos distribuidos uniformemente sobre la circunferencia mediante tabla precalculada de extremos `(s_ray_dx, s_ray_dy)`.
- **Interpolación Entera:** Cada rayo avanza mediante acumulador de error Bresenham puro (3 sumas y comparaciones enteras por celda, **cero divisiones por software en ARMv5**).
- **Oclusión por Muros:** Cada celda consulta `g_dungeon_collision`. Los muros altos (`flags == 3`) absorben el rayo y detienen la propagación, revelando la cara frontal del muro pero ocultando el espacio posterior.

### 3. Ocultación en Hardware de Fondo (`source/main.c`)
- En `update_screen_hardware_bg`:
  - Si un tile no ha sido explorado (`!fog_is_explored`), su ID en el mapa de hardware BG1 se fuerza a `0` (tile vacío/negro de VRAM). El chip de vídeo de la DS renderiza el fondo inexplorado como negro abisal con **0.00 ms** de coste de CPU.
  - Cuando el raycast descubre nuevos tiles, se invalidan las páginas de mapa para refrescar inmediatamente la geometría recién descubierta.

### 4. Filtrado de Entidades y Despertar de Monstruos
- En `render_screen`:
  - Cada enemigo consulta `fog_is_point_visible(enemy_x, enemy_y)`.
  - Si el enemigo está tras una esquina o fuera del cono de visión, **no se añade a la lista de dibujo** y **no genera sombra dinámica**, impidiendo cualquier revelación a través de paredes.
- En `enemies_update`:
  - Los enemigos en la penumbra u ocultos mantienen su patrulla tranquila en bucle. Al entrar en el haz de visión del jugador, se activan y persiguen al nigromante.

### 5. Penumbra al 50% por Escritura de Palabras de 32 Bits
- Las zonas exploradas pero fuera del cono activo reciben una trama checkerboard del 50% en el buffer de 16-bit (`s_bot_screen_buf`).
- La rutina `draw_fog_penumbra` escribe patrones alternados de 32 bits (`0x80000000` / `0x00008000`) bloque a bloque ($8 \times 8$ px), ejecutándose en tan solo **0.19 ms**.

---

## Verificación de Rendimiento y Contratos

- **Presupuesto de Rendimiento (DeSmuME Telemetría HUD):**
  - **FPS:** 60 FPS bloqueados (`FPS:60`).
  - **CPU:** 11–12 ms por fotograma (`C:11`), muy por debajo del límite de 16.6 ms.
  - **VBlank Wait:** 4 ms limpios de espera (`P:04`).
  - **VBlanks transcurridos:** 1 frame por ciclo (`F:01`).
- **Suite de Pruebas Automatizadas:**
  - `tests/test_fog_of_war.py`: 5 contratos verificando inicialización inexplorada, revelación en radio circular, bloqueo por muros de colisión y persistencia de memoria.
  - Total de tests del repositorio: **41/41 PASS**.

---

## Evidencia Visual

### 1. Gameplay con Niebla de Guerra Dinámica en Nintendo DS (60 FPS Locked)
![Recorrido con Niebla de Guerra a 60 FPS](assets/fog_dungeon_walk.gif)

### 2. Capturas Clave del Escenario
- **Spawn en Plaza Central (Fondo inexplorado en negro abisal):**
  ![Spawn](assets/00_spawn.png)
- **Avance al Sur bajo el Arco (Cono de luz ilumina el paso):**
  ![Cruce Sur](assets/01_arch_cross_south.png)
- **Desplazamiento al Pasillo Oeste (Monstruo oculto se revela tras la esquina):**
  ![Pasillo Oeste](assets/03_arch_cross_north.png)
- **Retorno al Centro (Zonas visitadas quedan en penumbra cartográfica):**
  ![Retorno Este](assets/04_return_east.png)
