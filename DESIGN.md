# DESIGN.md - Documento de Diseño

## 1. Visión y Alcance Confirmado
- **Concepto:** Juego para Nintendo DS similar a Diablo (vista cenital/isométrica) procedural y centrado en la temática de nigromancia.
- **Objetivo actual:** Diseñar el setup gráfico inicial y elegir assets estéticos para montar la demo técnica donde se puedan mover personajes en 8 direcciones.

## 2. Dirección de Arte y Pipeline Confirmado
- **Técnica:** Sprites 2D pre-renderizados a partir de modelos 3D con animaciones esqueléticas (FBX / Blender).
- **Proyección:** Isométrica / dimétrica a 60 grados en 8 direcciones.
- **Herramienta de tuning:** `tools/lab/shader_lab_ui.html` (`tools/lab/shader_lab_server.py`) para cargar FBX, elegir clips, ajustar renderizado y revisar sprites en 8 direcciones. El antiguo `sprite_lab.html` de tuning 2D se retiró.
- **Lanza ósea:** salva de cinco astillas estrechas y puntiagudas dibujadas proceduralmente, sin outline; proyectiles rápidos con motas de tonos marfil/hueso.
- **Muerte del enemigo:** al golpe final, la silueta se rompe en pequeños fragmentos extraídos de sus propios píxeles, que salen según el impacto y caen con una parábola breve.

## 3. Decisiones Abiertas / Pendientes de Definición
- Mecánicas de juego y controles concretos: Pendiente de definición por el usuario.
- Generador procedural de mazmorras: Pendiente de definición por el usuario.
- Estructura y reglas del bucle de combate y nigromancia: Pendiente de definición por el usuario.

---

## 4. Giro de Dirección: Shooter Isométrico tipo Doom (Decidido en /grill-me)

> Reemplaza el enfoque de nigromancia/esbirros de la sección 1 y 3. La "lanza ósea" y la "muerte por fragmentos" de la sección 2 quedan como assets/FX reutilizables, no como pilar de juego.

- **Pilar:** Kiting y posicionamiento. Shooter isométrico "Doom" en mazmorras procedurales por salas.
- **Bucle:** salas con grupos mixtos de enemigos → salida al final → siguiente piso con más densidad. Armas se recogen en el mapa.
- **Tono:** Armas ruidosas y contundentes, enemigos legibles por silueta y velocidad.

### 4.1 Jugador
| Aspecto | Decisión |
| :--- | :--- |
| Movimiento | D-pad, 8 direcciones. |
| Apuntado/disparo | Touchscreen (toque/stylus = dirección de disparo). Cambio de arma con L/R. |
| Salud | 100 HP + armadura estilo Doom. Pickups de vida/armadura/munición en sala y como drop de enemigos. |
| Munición | Separada por arma. Pistola base con munición infinita. |

### 4.2 Armas (pistola base + 3)
| Arma | Rol | Munición | Contra |
| :--- | :--- | :--- | :--- |
| Pistola | Cadencia baja, daño bajo, fallback infinito | ∞ | Tirador a distancia (precisión) |
| Escopeta | Corto alcance, ráfaga de perdigones con dispersión, retroceso/recarga marcados | Media | Charger al acercarse |
| Gatling | Fuego sostenido; arranque (spin-up) y ralentiza al jugador mientras dispara | Alta (gasta rápido) | Grupos; castiga al estático |
| Pesada (sniper/cohete) | Muy lento, largo alcance, daño alto (cohete con explosión de área) | Escasa | Tirador lejano, priority targets |

Valores numéricos finales (daño, cadencia, dispersión) quedan por definir en `TECHNICAL.md` con tablas en punto fijo 8.8.

### 4.3 Enemigo: Charger (melee, estilo Pinky)
- **Rol:** presión constante; castiga quedarse parado o acorralado.
- **Comportamiento:** persecución continua y rápida, **sin telegraph**; muerde con cooldown corto al llegar a rango melee.
- **Velocidad (supuesto recomendado, pendiente de tuning):** ~90% de la del jugador en recto con aceleración; alcanza si el jugador se acorrala o dispara parado. El jugador lo esquiva por velocidad y geometría.
- **Stats (propuesta):** HP alto (≈ 3× el del tirador), daño melee moderado, sin drop garantizado salvo vida.
- **FSM:** `IDLE → ALERT → CHASE → ATTACK(cooldown) → CHASE`; `CHASE → SEARCH` (pierde al jugador); `* → DEAD`.

### 4.4 Enemigo: Tirador Necrón (a distancia)
- **Rol:** control de espacio y presión a media distancia; obliga a moverse en vez de solo disparar.
- **Comportamiento:** mantiene distancia media (banda `[d_min, d_max]`): retrocede si el jugador se acerca, avanza si se aleja, hace strafe lateral entre ráfagas.
- **Ataque:** ráfaga de 3 proyectiles lentos esquivables, pausa entre ráfagas; apunta a la posición del jugador con ligero *lead* (predicción lineal con velocidad actual).
- **Stats (propuesta):** HP bajo, daño por proyectil bajo-medio, drop de munición probable.
- **FSM:** `IDLE → ALERT → POSITION (mantener banda/strafe) → AIM → BURST(3) → COOLDOWN → POSITION`; `POSITION → SEARCH`; `* → DEAD`.

### 4.5 Percepción y Navegación (compartido)
- **Detección:** línea de visión pura (Bresenham sobre `g_dungeon_collision`, sin fog explorado/visible ni máscaras baked) **o** radio de ruido al disparar (la gatling y la pesada tienen radio mayor). El fog de guerra actual se purga (Fase 0).
- **Pérdida:** tras ~3 s sin ver al jugador pasan a `SEARCH` hacia la última posición conocida y luego a `IDLE`.
- **Navegación:** sin FPU, punto fijo. Persecución directa si hay LOS; si no, seguir campo de distancias (BFS por tiles desde el jugador, recalculado cada N frames y amortizado entre enemigos).
- **Separación:** repulsión simple entre enemigos para evitar apilamiento.
- **Presupuesto:** IA amortizada (cada enemigo piensa 1 de cada N frames); 60 FPS bloqueado.

### 4.6 Sinergia de Encuentros
- Charger empuja a mover; tirador penaliza el movimiento predecible. Mezclados obligan a elegir prioridad de objetivo.
- Armas contrastan: escopeta para charger, pesada/pistola para tirador, gatling para grupos.
- Progresión por piso: más densidad y proporción mixta, mismos dos arquetipos en esta fase.

### 4.7 Plan por Fases
1. **Fase A:** Sistema de entidades enemigas + HP/daño del jugador + pickups (punto fijo).
2. **Fase B:** Charger con FSM, detección y persecución (escenario headless con muros reales).
3. **Fase C:** Tirador con banda de distancia, ráfagas y proyectiles enemigos.
4. **Fase D:** Armas: pistola, escopeta, gatling, pesada con munición independiente y control táctil.
5. **Fase E:** Encuentros por sala sobre el generador procedural y progresión por piso.
6. **Fase F:** Tuning y verificación de 60 FPS (`cpu_ticks` ≤ 33514) con mezcla máxima de enemigos.

### 4.8 Decisiones Abiertas
- Valores exactos de velocidad, HP y daño (tuning en juego).
- Alcance y feedback de la pesada (sniper vs. cohete).
- Número de enemigos simultáneos máximo en pantalla según presupuesto OAM/CPU.
