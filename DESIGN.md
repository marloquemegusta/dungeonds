# DESIGN.md - Documento de Diseño

## 1. Visión y Alcance
- **Concepto:** shooter isométrico para Nintendo DS por salas-arena, con tono gótico/grimdark (space marine contra necrones y bestias).
- **Pilar:** combate de Doom en isométrico: pocas armas contundentes con mucho *feel* (la escopeta como referencia), esquivar con strafe y salas como pequeño puzzle de prioridades (a quién matar primero y desde dónde), con el control preciso y el frenetismo de Hotline Miami.
- **Bucle de la prueba de diversión (vigente):** arena cerrada → todos los enemigos se activan → al matarlos se abre la salida → siguiente arena, más difícil. 3–4 arenas hechas a mano.
- **Fuera de la prueba, a propósito:** loot y progresión RPG (Diablo), mejoras entre salas (Vampire Survivors), generador procedural, enemigo grande. Se añaden solo si el combate pelado engancha; las armas se definen por parámetros para que una capa de mejoras pueda tocarlos sin rehacerlas.
- **Historia de la dirección:** el proyecto nació como un Diablo de nigromancia con esbirros. Se descartó en una sesión de diseño (`/grill-me`) a favor del shooter. El 2026-11-03 una entrevista de diseño recortó el shooter a la prueba mínima de §4. La lanza ósea y la muerte por fragmentos quedan como FX reutilizables, no como pilar de juego.

## 2. Dirección de Arte y Pipeline
- **Técnica:** sprites 2D pre-renderizados a partir de modelos 3D con animación esquelética (FBX/GLB).
- **Proyección:** isométrica/dimétrica en 8 direcciones; mapa y personajes con la misma cámara e iluminación.
- **Herramienta de render:** el lab Three.js (`tools/lab/`), fuente de verdad visual para mapa y personajes. Detalle del pipeline en `TECHNICAL.md` §3.
- **Personajes actuales:** héroe (space marine), charger y necron.
- **FX reutilizables:**
  - Lanza ósea: salva de cinco astillas estrechas y puntiagudas dibujadas proceduralmente, sin outline, con motas en tonos marfil/hueso.
  - Muerte del enemigo: la silueta se rompe en fragmentos extraídos de sus propios píxeles que salen según el impacto y caen con una parábola breve.

## 3. Decisiones Abiertas
- **Lectura tras paredes (transparencias):** qué se ve del personaje y de los enemigos detrás de una pared y cómo se marca la base de la pared. Sin decidir; preguntas en `TECHNICAL.md` §4.6. No se toca código hasta decidirlo aquí.
- **Mapas de las arenas:** el mapa actual (`isometric_shooter_bl`) se sustituye por 3–4 mapas sencillos hechos a mano. Falta decidir su forma (tamaño, coberturas, pasillos) y cómo se encadenan.
- **Sonido:** si entra en la prueba o después. Sin decidir.
- **Tuning de combate:** números concretos; ver §4.7.

---

## 4. Diseño de Juego: Prueba de Diversión Mínima

Alcance de la prueba: 1 jugador, 2 armas, 2 enemigos, 3–4 arenas a mano. Sin loot, armadura, munición, pickups ni generador. Lo que no está en esta sección no se implementa para la prueba.

### 4.1 Controles
| Input | Acción |
| :--- | :--- |
| D-pad | Mover en 8 direcciones. |
| Stylus | Apuntar y disparar. La dirección es el vector del personaje al punto tocado (no un cursor): se puede disparar hacia enemigos fuera de la pantalla táctil. |
| L | Cambiar entre las dos armas. |

Solo L es accesible sin dejar de apuntar; ninguna mecánica de la prueba usa otro botón.

### 4.2 Jugador
- **Salud:** 4–5 golpes. Tras cada golpe, i-frames breves con destello rojo.
- **Muerte:** reinicio instantáneo de la arena actual. Vida completa al empezar cada arena.
- **Esquiva:** solo con movimiento (strafe). Sin dash.

### 4.3 Armas
Ambas con munición infinita; las limita su ritmo y su coste de uso.

| | Escopeta | Francotirador (cañón) |
| :--- | :--- | :--- |
| Disparo | Al tocar. Un disparo por toque: mantener el stylus no repite; hay que levantar y volver a tocar. | Al tocar, el personaje se para y aparece una línea de mira. Dispara al **levantar**. |
| Ritmo | Bombeo marcado entre disparos. | Apuntado mínimo ~0,4 s; si se levanta antes no dispara. La línea cambia de color al estar lista. |
| Proyectil | Ráfaga de perdigones con dispersión; letal de cerca, floja de lejos. | Atraviesa a todos los enemigos en línea. |
| Efecto | Retroceso leve del jugador; empuja y frena un momento al enemigo. | — |
| Cancelar | — | Arrastrar el stylus sobre el personaje o pulsar L. |
| Rol | Respuesta al cargador. | Respuesta al tirador y a filas de enemigos en pasillos. |

**Golpes para matar (objetivo de tuning):**

| | Tirador | Cargador |
| :--- | :--- | :--- |
| Escopeta a quemarropa | 1 | 2–3 (cada uno lo empuja) |
| Francotirador | 1 | 2 |

### 4.4 Enemigo: Cargador (melee, estilo Pinky)
- **Rol:** presión constante; castiga quedarse parado o acorralado.
- **Comportamiento:** persigue rápido y sin pausa, sin telegraph; muerde con cooldown corto al llegar a rango melee. El empujón de la escopeta es su contra.
- **Velocidad:** ~90 % de la del jugador (punto de partida de tuning).
- **Requisito:** debe encontrar al jugador en toda la arena. La persecución en línea recta actual se atasca; hace falta navegación (campo de distancias BFS, §4.6). Sin ella la prueba no sirve.
- **FSM:** `CHASE → ATTACK(cooldown) → CHASE`; `* → DEAD`.

### 4.5 Enemigo: Tirador Necrón (a distancia, estilo Imp)
- **Rol:** control de espacio; obliga a moverse en vez de solo disparar.
- **Comportamiento:** mantiene una banda de distancia `[d_min, d_max]` (retrocede si el jugador se acerca, avanza si se aleja) y hace strafe lateral entre ráfagas.
- **Ataque:** destello del arma ~0,3 s antes de cada ráfaga; ráfaga de 3 proyectiles lentos y esquivables, apuntados con ligero *lead* sobre la velocidad del jugador; pausa entre ráfagas.
- **FSM:** `POSITION → TELEGRAPH → BURST(3) → COOLDOWN → POSITION`; `* → DEAD`.

### 4.6 Arenas, Activación y Navegación
- **Arena cerrada:** al entrar, la salida se cierra y todos los enemigos de la arena se activan a la vez. Sin detección por visión ni por ruido en la prueba (no hay estados `IDLE`/`ALERT`/`SEARCH`).
- **Encuentros:** 3–4 arenas de dificultad creciente; orientativo: solo cargadores → solo tiradores → mezcla (tiradores lejos + un cargador) → mezcla densa.
- **Navegación:** campo de distancias por BFS sobre la rejilla de colisión desde el jugador, recalculado cada N frames y amortizado; los enemigos bajan por el gradiente. Persecución directa si hay línea de visión.
- **Separación:** repulsión simple entre enemigos para evitar apilamiento.
- **Presupuesto:** IA amortizada; 60 FPS certificados en la DS (`AGENTS.md` regla 6).

### 4.7 Game Feel
- **Al impactar:** hitstop de 2–4 frames, destello blanco del enemigo, empujón (escopeta).
- **Al disparar:** temblor de pantalla proporcional al arma; retroceso leve del jugador con la escopeta.
- **Muerte:** fragmentos (FX existente, §2).
- **Al recibir daño:** destello rojo e i-frames.
- **Tuning pendiente:** velocidades, daño, dispersión, cadencias, bandas de distancia y nº máximo de enemigos en pantalla, en punto fijo, ajustados jugando en la DS.

### 4.8 Plan por Fases
1. **Fase A — Jugador y armas:** controles de §4.1, salud y reinicio de §4.2, escopeta y francotirador de §4.3 con el feel de §4.7.
2. **Fase B — Cargador:** navegación BFS, persecución, mordisco, empujón.
3. **Fase C — Tirador:** banda de distancia, telegraph y ráfagas.
4. **Fase D — Arenas:** 3–4 mapas sencillos (tras decidir su forma, §3), cierre/apertura y encadenado.
5. **Fase E — Tuning y 60 FPS en la DS** con la arena más densa.
6. **Después, solo si engancha:** mejoras entre arenas, loot, enemigo grande, generador procedural.
