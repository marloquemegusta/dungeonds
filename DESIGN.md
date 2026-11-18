# DESIGN.md - Documento de Diseño

## 1. Visión y Alcance
- **Concepto:** survivors de frente vertical para Nintendo DS, con apuntado manual y tono gótico/grimdark (el Corazón Abierto y otros futuros personajes contra los caídos de la Cruzada). Referencias: Halls of Torment y Vampire Survivors por el bucle; Diablo y Warhammer 40K: Inquisitor por lo que engancha al usuario (ir a la siguiente misión y mejorar); Isaac por la dificultad (lo normal es morir pronto hasta conocer las mejoras).
- **Pilar:** combate de Doom en isométrico (cada personaje con un arma contundente y mucho *feel*, esquivar con strafe), contra una horda que viene de arriba y por un pasillo que hay que abrirse a tiros. Las dos pantallas forman un campo vertical: la superior es la vanguardia que se ve llegar y a la que se puede disparar.
- **Bucle vigente (v0.3, decidido 2026-11-06; estructura revisada 2026-11-16):** una subida vertical de 15–18 min con una marea que sube desde abajo, horda continua, gemas → nivel → elegir 1 de 3 mejoras, élites y tres actos con un jefe al final de cada uno (Vía Crucis de 14 estaciones, §6.13). Personaje = arma única (no hay cambio de armas en partida). Detalle en §6.
- **Fantasía:** sin lore, pero clara y con entorno cambiante: ascender (o descender) por un pozo o una aguja infestada, cambiando de bioma por el camino. Los personajes, enemigos y mapas actuales son placeholders con la estética buena; el sistema debe aguantar cambiarlos.
- **Fuera de la prueba de la v0.3, a propósito:** progresión entre runs (equipo, desbloqueos), más de dos clases, sonido, más de dos biomas. La capa de equipo es el gancho a largo plazo (Diablo) y se diseña tras validar que una run divierte.
- **Historia de la dirección:** el proyecto nació como un Diablo de nigromancia con esbirros, descartado a favor del shooter. La v0.1 (4 arenas cerradas, §4) era fácil y poco divertida en la DS. La v0.2 (mazmorra de manadas con modificadores estilo Isaac, §5) fue más divertida pero se agotaba en un par de minutos: sin variedad entre runs ni motivo para volver. El 2026-11-06 se eligió el survivors vertical (§6) frente a un Isaac de salas (más barato pero menos del gusto del usuario) y a una campaña lineal tipo Diablo (demasiado contenido a mano). La lanza ósea y la muerte por fragmentos quedan como FX reutilizables.

## 2. Dirección de Arte y Pipeline
- **Técnica:** sprites 2D pre-renderizados a partir de modelos 3D con animación esquelética (FBX/GLB), **sin outline** en personajes, enemigos ni piezas de escenario.
- **Proyección:** isométrica/dimétrica en 8 direcciones; mapa y personajes con la misma cámara e iluminación.
- **Herramienta de render única:** el lab Three.js (`tools/lab/`), fuente de verdad visual para mapa y personajes; no abrir vías de render paralelas en Blender/Python salvo prototipos temporales marcados como tal. Detalle del pipeline en `TECHNICAL.md` §3.
- **Regla de personaje:** **1 personaje = 1 arma**; cualquier selector de armas, auras o animaciones en la ROM actual es solo herramienta de depuración.
- **Personajes actuales:** héroe (El Corazón Abierto), cargador (El Cireneo v2), esqueleto y tirador (necron, pendiente de sustituir por El Ojo del Tribunal, que trae mecánica propia: §6.10).
- **FX reutilizables:**
  - Lanza ósea: salva de cinco astillas estrechas y puntiagudas dibujadas proceduralmente, sin outline, con motas en tonos marfil/hueso.
  - Muerte del enemigo: la silueta se rompe en fragmentos extraídos de sus propios píxeles que salen según el impacto y caen con una parábola breve.

## 3. Decisiones Abiertas
- **Actores detrás de muros (decidido 2026-11-10):** personaje y enemigos se ocultan según la profundidad horneada; no parpadean ni reciben transparencias, siluetas o marcas negras auxiliares cuando quedan detrás. La base caminable no se dibuja sobre el muro.
- **Sombras de personajes por hardware (decidido 2026-11-13, rama `perf/hw-shadows`):** la sombra de héroe y enemigos conserva la forma horneada del lab por dirección y frame y su tono actual (suelo al 50 %), pero la oscurece la propia consola en vez del procesador. Se aceptan tres diferencias: dos sombras solapadas se funden en un solo tono (antes se oscurecían el doble); bajo la marea la sombra toma la oscuridad de la marea; y si un enemigo queda detrás de una pieza o muro, su sombra se oculta entera en vez de recortarse píxel a píxel. Además, las marcas de suelo de las armas (anillos y elipses del pase de suelo) ya no quedan oscurecidas por las sombras que pasan por encima, porque la consola solo oscurece la capa del suelo. Motivo: las sombras eran el 43 % del frame con horda (`walkthroughs/stress-enemies-profiling/`). Si con esto y la optimización de IA/dibujo no se duplica la horda a 60 FPS, la siguiente opción aceptada por el usuario es quitar la separación entre enemigos (que puedan solaparse, estilo *Vampire Survivors*). **Resultado (2026-11-14, medido en la DS):** con 48 enemigos el juego se mantiene casi siempre a 60 FPS, así que la separación se conserva.
- **Sonido:** fuera de la v0.3.
- **Por decidir antes de cada versión (§6.9):** árbol de mejoras de las dos clases y su presentación (antes de la 0.4); enjambre, élites, cofres y emboscadas (antes de la 0.5); catálogo y reglas de tramos, aspecto de cada acto, jefes y aspecto final de la marea (antes de la 0.6; estructura ya decidida en §6.13).
- **Tuning de combate y stats:** se hace jugando en la DS en la 0.3.1 (§6.9.1), sobre los valores de partida de §6.
- **Ya no aplican (v0.2):** mazmorra más grande con puertas y rediseño de pedestales; los sustituye la v0.3.

---

## 4. Diseño de Juego: Prueba de Diversión Mínima

> **Historia (v0.1).** El bucle de arenas (§4.2 muerte, §4.6, §4.8) está sustituido por §6. Siguen vigentes las armas (§4.3), la IA de cargador y tirador (§4.4, §4.5), el game feel (§4.7) y los efectos (§4.9). Los controles de §4.1 cambian en la v0.3 (§6.5).

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

**Arenas (decidido 2026-11-03).** Datos en `assets/arenas/arenas.json` (fuente única de geometría, inicio del jugador y enemigos).
- **Tamaño:** cada arena es una imagen de 384×384 px: dos pantallas de alto (la cámara no se mueve en vertical y las dos pantallas muestran la arena entera) y 1,5 de ancho (scroll horizontal; la cámara se queda dentro de la arena).
- **Forma, una distinta por arena:**
  1. Sala abierta con 2 pilares: aprender strafe contra cargadores.
  2. Muros bajos repartidos: cobertura para tiradores.
  3. Dos pasillos paralelos separados por un muro: filas para el francotirador.
  4. Sala grande con 4 pilares y un pasillo central.
- **Enemigos (todos activos a la vez):** A1 3 cargadores; A2 3 tiradores; A3 3 tiradores lejos + 1 cargador; A4 3 cargadores + 4 tiradores.
- **Encadenado:** automático. Al morir el último enemigo hay una pausa de medio segundo (30 frames) y se pasa a la siguiente arena con vida completa, sin puerta ni camino a pie. Tras la cuarta se vuelve a la primera. Morir reinicia la arena actual.

### 4.7 Game Feel
- **Al impactar:** hitstop de 2–4 frames, destello blanco del enemigo, empujón (escopeta).
- **Al disparar:** temblor de pantalla proporcional al arma; retroceso leve del jugador con la escopeta.
- **Origen del disparo:** proyectiles, fogonazo y línea de mira salen de la boca del arma, no de los pies del personaje. El punto de boca por dirección lo exporta el lab junto al spritesheet; el runtime no usa offsets escritos a mano.
- **Aspecto del disparo (decidido 2026-11-03):** procedural, en la línea de la lanza ósea. Perdigones como trazos cortos con estela que se desvanece; fogonazo de 2–3 frames en la boca; chispas de impacto como líneas que salen según la normal y se apagan; el francotirador, un trazo largo y brillante que se desvanece en pocos frames. Sustituye a los cuadrados y cruces de píxeles actuales.
- **Ambas pantallas iguales:** la pantalla superior dibuja lo mismo que la inferior (suelo, actores, sombras, proyectiles enemigos y FX del disparo) desplazada una pantalla hacia arriba, para poder ver y apuntar a lo que queda fuera de la pantalla táctil (decidido 2026-11-03, tras probar en la DS). Solo la inferior lleva el HUD de depuración.
- **Muerte:** fragmentos (FX existente, §2).
- **Al recibir daño:** destello rojo e i-frames.
- **Tuning pendiente:** velocidades, daño, dispersión, cadencias, bandas de distancia y nº máximo de enemigos en pantalla, en punto fijo, ajustados jugando en la DS.

### 4.9 Granada y variantes de efectos (decidido 2026-11-05, rama `proto/weapon-previews`)
Tras ver las previsualizaciones (`walkthroughs/weapon-previews/`), se implementan **de verdad** para compararlas en la DS. Es un banco de pruebas: tras elegir se borran las variantes descartadas.

- **Selector de estilo (solo depuración):** `SELECT` cambia el estilo global A/B/C (`g_fx_style`), que afecta a escopeta, francotirador y granada a la vez. El HUD de depuración muestra `FX:A|B|C`. No es un control de juego y desaparece al elegir.
- **Granada, tercera arma del ciclo de L** (escopeta, francotirador, granada). Tocar el suelo marca el punto de destino (se puede arrastrar para moverlo); levantar el stylus la lanza. Arrastrar el stylus sobre el personaje o pulsar L cancela. Alcance máximo 150 px de suelo (el punto se recorta al alcance y al último punto libre de la línea). Munición infinita, enfriamiento 60 frames, como mucho 2 granadas a la vez.
- **Mecha y daño:** explota 90 frames (1,5 s) después del lanzamiento, por tiempo y no por impacto. Radio 56 px de suelo (elipse 2:1 en pantalla). Daño 60 en el centro bajando linealmente hasta 15 en el borde (cargador 60 PS, tirador 20 PS); empuja y aturde en radio, más cuanto más cerca. **Fuego amigo:** si el jugador está dentro del radio recibe un golpe (`player_take_hit`, respetan los i-frames). Los muros protegen: no hay daño si la línea recta entre el centro y la víctima está bloqueada.
- **Antes de explotar, variantes:** A, anillo de radio que se contrae hacia el centro durante la mecha; B, la granada rebota dos veces con luz roja que parpadea cada vez más rápido y solo un círculo punteado tenue del radio; C, zona de peligro rayada y parpadeante en el suelo y el proyectil cae desde arriba al final (el vuelo no se dibuja).
- **Explosión (común a A/B/C, dirección artística):** ni un círculo perfecto ni solo rojo y naranja.
  - Destello blanco de 2 frames en forma de estrella irregular (8–10 puntas de longitud desigual).
  - Bola de fuego como **racimo de 7–9 lóbulos** (círculos rellenos de 5–11 px) con ángulo, distancia y retraso de aparición aleatorios (0–4 frames) que suben mientras crecen y se encogen; silueta asimétrica y dentada. Cada lóbulo se pinta en dos tonos (cuerpo más frío, núcleo más caliente desplazado arriba a la izquierda) para dar volumen. Rampa de color por edad: blanco, amarillo, naranja, rojo, rojo oscuro, gris.
  - Onda de choque en el suelo: elipse 2:1 **pálida (blanco hueso, polvo)**, fina y con huecos (dibujada solo en ~65 % de los ángulos), que se expande hasta el radio de daño en 8 frames; no es roja.
  - Escombros y brasas: ~14 trazos con gravedad que pasan de naranja a gris.
  - Humo: 4–5 volutas grises con borde tramado (damero) que suben despacio ~40 frames.
  - Sin transparencias: los bordes suaves se hacen con tramado.
  - Temblor de pantalla 4 px durante 10 frames y hitstop de 3 frames.
- **Escopeta y francotirador, variantes** (las de las previsualizaciones): escopeta A estelas cortas (la de §4.7), B estallido en cono con casquillo y humo, C pesada con onda de choque en abanico y polvo; francotirador A trazo largo que se desvanece, B anillos de choque en la boca y en cada enemigo atravesado, C trazo irregular de dos tonos con retícula en el primer objetivo. Límite de partículas simultáneas por arma: 32.
- **Perspectiva del suelo (regla, decidida 2026-11-05):** todo lo que está *en el suelo* (marcador de apuntado, anillos de aviso, zona de peligro, onda de choque, anillos del francotirador, arco de la escopeta) es una elipse 2:1 en pantalla (semieje horizontal R, vertical R/2) y se pinta **en el suelo, bajo sombras y personajes** y respetando los muros (`groundfx`, pase de suelo). Lo que tiene volumen (bola de fuego, escombros, humo, destellos) se sigue dibujando encima.
- **Granada C, «láser desde el espacio» (rediseño):** zona de peligro = disco elíptico 2:1 en el suelo, tramado diagonal en perspectiva, solo sobre el suelo (los personajes se ven por encima y no se tiñen de rojo plano). Los personajes dentro del radio se **iluminan**: durante la mecha una columna de luz cilíndrica sobre la zona aclara y tiñe de rojo los píxeles de los personajes (pase de luz tras los sprites), con intensidad creciente. En los últimos 12 frames cae un haz láser fino y brillante desde lo alto de la pantalla hasta el centro, y la columna se pone al máximo justo antes de la explosión.
- **Aura de carga del francotirador (histórico: sustituida por las auras del Corazón Abierto, §6.10) (decidida 2026-11-05 tras ver referencias de Killua y SSJ2; tres variantes para comparar con el botón Y, `g_aura_style` 0=K, 1=C, 2=V; vale para los 3 estilos del haz):** mientras se carga el disparo (`AIM_AIMING` a `AIM_READY`) el personaje desprende un aura de **rayos azules angulosos** (no una línea continua ni una hélice lisa): polilíneas finas en zigzag de 3 px de paso con quiebros bruscos, alguna bifurcación y puntas en gancho, que **se regeneran cada 2-3 frames** para que crepiten. Colores: trazo de 1 px blanco con azul claro en píxeles alternos; sin halo oscuro (la v2 de K y C eran demasiado gruesas). Densidad, longitud y altura crecen con el progreso; al llegar a `AIM_READY` hay flash de 3 frames, anillo 2:1 en el suelo y aura al máximo hasta soltar; al soltar o cancelar se apaga en pocos frames. Respeta los muros, límite fijo de segmentos, sin `float`. **Oclusión por el personaje (regla común):** lo que nace en la mitad trasera de la elipse 2:1 (seno < 0) se pinta antes del sprite y lo tapa el cuerpo; lo delantero, después.
  - **Variante K (Killua / SSJ2, por defecto):** 5-6 rayos finos (1 px, blanco con azul claro en píxeles alternos, sin halo) que nacen en la elipse de los pies a distintas alturas y envuelven el cuerpo subiendo en tangente, 12-16 px de largo, con bifurcaciones ocasionales.
  - **Variante C (corona + rayos):** corona de 8 rayos de ~14 px que estallan desde un anillo 2:1 en el suelo hacia arriba y hacia fuera con bifurcaciones: base de 2 px (los 2 primeros pasos, borde azul claro y núcleo blanco) y el resto de 1 px como K; más 2 rayos finos de 1 px envolventes a media altura.
  - **Variante V (chispas verticales, la v1 con oclusión):** chispas finas de 6-14 px que suben desde la elipse de los pies, de blanco a amarillo a naranja según la altura, más densas con la carga.
- **Colimado del láser del francotirador (histórico: el francotirador usa ahora el haz «fuego» del Corazón Abierto, §6.10) (decidido 2026-11-06, rama `feat/sniper-collimation`, tras ver mockups `walkthroughs/sniper-collimation/assets/`):** mientras se carga, el haz no solo cambia de color: se va **colimando**. Empieza ancho, difuso y rojo; se estrecha, se vuelve estable y pasa a verde, hasta quedar en 1 px cuando está listo. Progreso `prog = s_aim_timer / aim_frames` (0..256, `aim_frames` = `aim_min_frames` + mejora; una sola división por frame). Anchura lateral máxima 6 px a 0 %, 0 a 100 %. El color de la línea central va de rojo a verde entre el 70 % y el 100 %. Al llegar a `AIM_READY` el haz queda fino, verde y estable (sin parpadeo). Compatible con el aura K/C/V (se dibujan en pasadas distintas).
  - **Estilo A (A1):** banda ancha **tramada** (borde en damero, interior rojo oscuro) que se cierra sobre la línea central hasta 1 px verde.
  - **Estilo B (B3):** **nube de puntos tramada** en cono alrededor de la línea de puntos (cada 3 px, cada 2 al estar listo); la nube tiene densidad y anchura decrecientes y desaparece al llegar al 100 %. Posiciones deterministas por hash (sin `rng` acumulado), como mucho 128 puntos por frame.
  - **Estilo C (C1):** línea sólida con **halo ancho tramado** que se afina hacia el retículo (el halo mide un 40 % en el extremo del objetivo) y se cierra a 1 px; el retículo de corchetes sigue cerrándose como hasta ahora.
  - **Reglas:** nada en el suelo, es luz en el aire a la altura de la boca (no aplica 2:1); la longitud la sigue dando `s_aim_len` (recortada por muros); el halo lateral se recorta con la misma comprobación de píxel de pantalla que el resto de FX. Sin `float`; los bucles tienen tope fijo (longitud del rayo × anchura ≤ 13 px, nube ≤ 128 puntos).
- **Presupuesto:** ninguna variante puede bajar de 60 FPS en la DS (`AGENTS.md` regla 6). Se descarta la que no lo cumpla.

### 4.8 Plan por Fases
1. **Fase A — Jugador y armas:** controles de §4.1, salud y reinicio de §4.2, escopeta y francotirador de §4.3 con el feel de §4.7.
2. **Fase B — Cargador:** navegación BFS, persecución, mordisco, empujón.
3. **Fase C — Tirador:** banda de distancia, telegraph y ráfagas.
4. **Fase D — Arenas:** 3–4 mapas sencillos (tras decidir su forma, §3), cierre/apertura y encadenado.
5. **Fase E — Tuning y 60 FPS en la DS** con la arena más densa.
6. **Después, solo si engancha:** mejoras entre arenas, loot, enemigo grande, generador procedural.

---

## 5. v0.2: Mazmorra de Manadas (decidido 2026-11-04)

> **Historia.** Sustituida por la v0.3 (§6) el 2026-11-06. La tabla de modificadores se recicla como punto de partida de las mejoras (§6.4); el resto queda en el historial de git.

**Por qué.** La v0.1 se jugó en la DS: el feel del francotirador funciona, el de la escopeta menos, y el conjunto "se juega bien pero no es divertido" y se siente fácil. Con 3–7 enemigos cerrados en una sala no hay fantasía de segar ni progresión. Se descarta rediseñar cada encuentro a mano (estilo Hotline Miami) por coste de diseño. Dirección elegida: **limpiar una mazmorra de manadas** (Diablo) con **compromisos y modificadores que invitan a repetir** (Isaac/Hades). El objetivo único de esta versión es que matar sea divertido.

**Bucle de la run (sesión de ~5 min).** Una mazmorra grande, hecha a mano y fija. Dentro hay manadas dormidas. Se despiertan, se limpian, cada limpieza da un modificador. Se completa al matar todas las manadas. Morir reinicia la mazmorra completa (manadas y jugador) y **se pierden los modificadores** (como Hades/Isaac). Sin guardado entre runs.

**Mazmorra.**
- Un único mapa de 768×768 px (dos pantallas de alto ya no la cubren: la cámara sigue al jugador en ambos ejes, con la pantalla superior mostrando lo que queda sobre la inferior). Datos en `assets/arenas/arenas.json`.
- Seis salas: una sala inferior grande con pilares, tres salas superiores separadas por muros con puertas, y comunicación por pasos de 64 px.
- Estética: oscura, de mazmorra con toques cyberpunk (neones de acento por sala, losas con juntas, franjas en muros). Generada con el mismo pipeline lab → baker, sin Blender, sin transparencias.

**Manadas.**
- Cada enemigo del mapa pertenece a una manada (`pack`). Manadas: seis, de 3–4 enemigos, mezclando cargadores y tiradores (la mayoría de manadas, mixtas; ninguna cerca del inicio).
- **Estado `DORMANT`:** el enemigo está quieto en su punto, dibujado, sin IA. Se despierta **toda la manada a la vez** cuando el jugador queda a menos de ~220 px de suelo de cualquiera de sus miembros **o** cuando recibe daño un miembro (el francotirador puede abrir la pelea de lejos).
- Una manada despierta se comporta como en la v0.1 (cargador `CHASE`, tirador `POSITION`).
- Máximo de enemigos despiertos a la vez: el de la manada más grande más una vecina; el resto sigue dormido. El tope técnico lo fija el presupuesto de 60 FPS (§4.7).

**Modificadores (estilo Isaac: compromiso, no solo números).**
- Al matar al último enemigo de una manada aparecen **dos pedestales** donde murió. Se coge uno pisándolo; el otro desaparece. Cada pedestal muestra un icono de color y, al acercarse, el nombre del modificador (texto corto en la pantalla inferior).
- La limpieza de cada manada además **cura 1 golpe**.
- Un modificador se ofrece a lo sumo una vez por run. Son de una tabla de datos; los primeros son cambios de parámetros, algunos con condición:

| Nombre | Efecto | Coste |
| :--- | :--- | :--- |
| Perdigones perforantes | Los perdigones atraviesan 1 enemigo. | −25 % daño de la escopeta. |
| Recámara doble | +3 perdigones. | +12 frames de bombeo. |
| Gatillo ligero | Francotirador: −8 frames de apuntado. | −25 % daño del francotirador. |
| Cañón largo | Francotirador: +50 % daño. | +10 frames de apuntado. |
| Sed de sangre | Cada muerte reinicia el bombeo de la escopeta. | −1 golpe de vida máxima. |
| Coraza ósea | +2 golpes de vida máxima (y cura 2). | −12 % velocidad. |
| Pies ligeros | +15 % velocidad. | −20 frames de invulnerabilidad. |
| Retroceso brutal | Escopeta: ×2 empuje y aturdimiento. | ×2 retroceso propio. |

**HUD de la run (siempre visible, solo pantalla inferior).** Golpes de vida como cuadrados rojos arriba a la derecha, un cuadrado de color por modificador cogido debajo, `MANADAS n DE m` abajo a la izquierda, el nombre del modificador del pedestal cercano (o del último cogido) abajo en el centro. Sustituye a que la vida solo se viera con el HUD de depuración (START).

**Final de la run.** Al limpiar todas las manadas: texto "MAZMORRA COMPLETADA" durante unos 3 s y vuelta a una run nueva sin modificadores. Los jefes se añaden después.

**Dificultad.** La v0.1 se sentía fácil. La presión sube por cantidad y mezcla de enemigos, no por vida ni daño, y la curva de la mazmorra por manadas. El jugador sigue con 5 golpes y 60 frames de invulnerabilidad; se ajusta jugando.

**Fuera de la v0.2.** Jefes, sonido, transparencias, tercer tipo de enemigo, mazmorras aleatorias, botín de estadísticas. Se evalúa tras probarlo en la DS.

**Plan.** (1) Mapa y datos (agente + baker). (2) Manadas durmientes, despertar, NAV 48×48 y run completa. (3) Modificadores. (4) Pruebas, tuning y 60 FPS en la DS (`PERF_PROFILE`). La v0.1 no se mergea aparte: v0.2 parte de su rama.

### Feedback de la primera prueba de la v0.2 en la DS (2026-11-04)
- **Más divertida que la v0.1**, sin duda: la dirección de manadas dormidas + modificadores se confirma.
- **Gráficos:** bien y legibles; las sombras del lab encajan con los personajes.
- **Tuning pendiente (prioridad):** los números del daño de las armas, del daño que hacen los enemigos al jugador y, en general, las stats de todo (vida, velocidades, cadencias). Hoy siguen siendo los placeholders de la v0.1. Sesión de tuning propia, jugando en la DS.
- **Modificadores:** se sienten "random" y no queda claro qué hace cada uno. Falta presentación: icono y descripción corta del efecto y del coste antes de cogerlos, y que el nombre no sea lo único que se ve. Los pedestales y la UI son provisionales y "cutres" (diamante de color y texto con la fuente de depuración); rediseño pendiente.
- **Mazmorra:** debe ser bastante más grande y con salas más diferenciadas entre sí (tal vez con puertas). Sin decidir cuántas salas, tamaño ni si las puertas bloquean hasta limpiar. Decisión de diseño antes de modelar (`AGENTS.md` regla 9).
- **Rendimiento:** la ROM con `PERF_PROFILE` midió CPU media 35,5 %, el 0,89 % de frames con más de un vblank y tramos de 300–411 k ticks con varias manadas despiertas. No certifica 60 FPS. Detalle en `walkthroughs/v0.2/walkthrough.md`.


---

## 6. v0.3: Frente Vertical (decidido 2026-11-06)

**Por qué.** La v0.2 divierte un par de minutos, pero después no hay nada que hacer: el mapa y las manadas son fijos, los modificadores son números y morir no deja nada. Faltaban una run que cambie y una meta. El usuario quiere la dificultad de Isaac (morir mucho hasta dominar las mejoras), el gancho de Diablo (siguiente misión, mejor equipo) y una fantasía clara con entorno cambiante. El bucle de Halls of Torment y Vampire Survivors junta las tres cosas, y el giro vertical lo adapta a la DS. Objetivo de esta versión: que una run de ~8 min entretenga de verdad y apetezca jugar otra.

### 6.0 Hito 0.3 mínima (decidido 2026-11-06, cerrado el mismo día; siguiente versión en §6.9)
Primer paso jugable hacia §6.1–6.8: el juego actual (armas, cargador, tirador, vida e i-frames) en un escenario vertical, sin mejoras, gemas, élites ni jefes. Donde contradice a §6.1–6.8, manda esto **solo para este hito**.
- **Mapa:** arena abierta de **2 pantallas de ancho (512 px de mundo)** e **infinita hacia arriba**, generada en tiempo de ejecución con una semilla por run. Suelo de un solo acento neón de la mazmorra de la v0.2 (**cian**) con su patrón; muros altos solo en los dos laterales.
- **Obstáculos:** solo **columnas bajas** (~0,5 m) con las piezas de la mazmorra. Bloquean el paso pero no las balas, y no ocluyen: los actores se dibujan siempre por encima. Se colocan por franjas de 128 px, entre 0 y 3 por franja, y siempre queda un carril libre de lado a lado del recorrido.
- **Cámara:** el jugador va centrado en la pantalla inferior y la superior muestra lo que viene (§6.3). Hay scroll horizontal dentro de los 512 px.
- **Enemigos:** cargador y tirador actuales. Nacen por encima del borde superior de la pantalla de arriba y bajan a buscar al jugador. La frecuencia crece con el tiempo. Los que quedan muy por debajo del jugador o se traga la marea se reciclan sin recompensa.
- **Marea:** una línea de **oscuridad** (oscurece la imagen con mezcla por hardware) que sube desde abajo a velocidad constante. Dentro de ella el jugador recibe 1 golpe cada cierto tiempo (respetando los i-frames) y va a la mitad de velocidad. Nunca se para.
- **Drops:** al morir, un enemigo suelta a veces un **pickup que cura 1 golpe** (sin pasar del máximo). Se recoge pisándolo y la marea se lo traga.
- **Run:** infinita. Morir la reinicia con una semilla nueva. El HUD muestra la **altura alcanzada en metros y el tiempo**, y en la pantalla de muerte la mejor marca de la sesión (sin guardar).
- **Fuera de este hito:** gemas, niveles y mejoras, élites, minijefe y jefe, emboscadas desde abajo, biomas y salas laterales.

### 6.1 Bucle de la run (prueba)
> **Revisado 2026-11-16:** la estructura vigente es la de §6.13 (15–18 min, tres actos, tres jefes). Lo de abajo queda como historia de la prueba de la v0.3.

- Un solo nivel. Se empieza abajo del todo y se sube abriéndose paso entre la horda mientras una **marea** sube detrás (§6.4).
- A mitad, al cambiar de bioma, hay un **minijefe**. Arriba, en una sala final, espera el **jefe**. Matar al jefe gana la run.
- Duración objetivo: unos 8 min hasta el jefe. La fija la velocidad de la marea.
- Morir reinicia la run de cero. Sin progresión entre runs en esta prueba (§1).

### 6.2 Mapa: franja vertical por tramos
- Una franja de **2 pantallas de ancho (512 px de mundo)** y muchas de alto. Se propuso de 1 a 1,5 pantallas (256–384 px), pero tras jugar la 0.3 mínima el usuario prefiere 512 (decidido 2026-11-07). No hay sitio para huir en círculos como en un survivors abierto: hay que abrirse paso, y eso da valor al apuntado, al empujón de la escopeta y al láser que atraviesa filas.
- Se monta con **tramos** hechos a mano de una pantalla de alto, encadenados por reglas que el usuario pule (por ejemplo: abierto, estrechamiento, sala lateral con cofre o élite, coberturas bajas). Las reglas y el catálogo de tramos se deciden en la sesión de contenido (§6.9).
- **Dos biomas** en la prueba, uno en cada mitad, para comprobar que el cambio de entorno se nota. El tema de cada bioma está por decidir.
- Muros altos solo en los laterales. En el centro, coberturas bajas, para que la lectura no dependa de las transparencias (§3).
- La longitud es la que dé ~8 min a la velocidad de la marea; se ajusta jugando.

### 6.3 Cámara y pantallas
- **Cámara con adelanto vertical (*look-ahead*, decidido 2026-11-14):** en lugar de centrar al jugador en el 50 % de la pantalla inferior, el encuadre se adelanta suavemente según el sentido de marcha vertical:
  - **Al subir:** coloca al jugador en el tercio inferior (~69 %, ~132 px de vista delante y ~60 px detrás en la pantalla táctil).
  - **Al bajar (retroceder):** desliza la vista hacia atrás hasta dejar al jugador en el tercio superior (~33 %, ~128 px de vista detrás para ver la marea y retroceder con comodidad), **salvo si está apuntando hacia delante con el stylus (*kiting*)**, en cuyo caso mantiene la vista al frente.
  - **Al parar o hacer *strafe* lateral:** la cámara mantiene el último encuadre (no vuelve sola al centro), y requiere ~0,37 s (22 frames) de marcha vertical sostenida antes de empezar a deslizarse (a 2 px/frame) para que los esquives cortos no muevan el suelo bajo el stylus.
- **La pantalla superior es la vanguardia, no un menú:** muestra la horda que llega, los puntos de aparición y los avisos de élite, minijefe y jefe. Se le puede disparar con el apuntado por vector de §4.1. Premia a las clases de largo alcance.
- Los menús, como la elección al subir de nivel, van en la pantalla inferior.
- **Menú inicial y menú de pausa (decidido 2026-11-14):**
  - **Reparto entre pantallas:** la pantalla superior muestra únicamente la catedral de fondo (sin título ni adornos); la pantalla inferior (táctil) muestra la catedral por detrás con un tinte oscurecido y el menú encima.
  - **Estilo minimalista:** cajas semitransparentes oscuras con texto plano sobre la catedral oscurecida, usando la paleta `FX_SH_*` (marfil y oro/carmesí apagado para la opción activa, ceniza para las inactivas), sin marcos ni títulos postizos.
  - **Navegación (ambos):** táctil con lápiz sobre cualquier botón y cruceta (`Arriba`/`Abajo`) + `A` (confirmar) / `B` (volver o reanudar en pausa). `START` abre y cierra la pausa durante la partida (cuando el jugador sigue vivo; tras morir conserva el reinicio).
  - **Menú inicial (al arrancar la ROM):** `NUEVA PARTIDA`, `CODICE` y `CONTROLES`.
  - **Menú de pausa (`START` en partida):** `CONTINUAR`, `REINICIAR`, `CODICE` y `CONTROLES`. Congela horda, marea, temporizador, combate y música (sin coste por frame durante la partida activa). `SELECT` e `Y` siguen funcionando en partida para comparar efectos de la demo.
  - **Submenús:** `CODICE` abre el códice de personajes (§6.11); `CONTROLES` muestra `CRUCETA: MOVERSE`, `LAPIZ: APUNTAR Y MANTENER PARA CARGAR`, `START: PAUSA` y `SELECT / Y: COMPARAR EFECTOS (DEMO)`, más botón `VOLVER`.
  - **Tarjetas de introducción (decidido 2026-11-14, rama `feat/intro-tarjetas`):** al elegir `NUEVA PARTIDA` se muestra una secuencia de 4 tarjetas antes de empezar; no aparece al reiniciar desde la pausa.
    - **Maquetación (como el códice, §6.11):** fondo negro y borde gris de 1 px en ambas pantallas. Arriba, un **bucle de vídeo de la pantalla inferior del juego real** (256×192 completa, ~2 s a 30 imágenes por segundo, grabado de la ROM en el escenario de pruebas y guardado sin pérdida en NitroFS, cargado bajo demanda como los retratos del códice). Bucles: 1) héroe avanzando con la horda delante; 2) mover, apuntar y cargar con el lápiz; 3) la marea subiendo; 4) un enemigo suelta un Sagrado Corazón y el héroe lo pisa. Descartado por ahora: ejecutar el juego en directo dentro de la tarjeta (mejora futura, solo cambiaría esta ilustración). Abajo, título y texto corto en español con la fuente del códice.
    - **Botones (pantalla inferior):** `SALTAR` siempre visible, que empieza la partida al instante (también con `START`); `< ANT` y `SIG >` para moverse (lápiz, cruceta o `A`/`B`; `R` avanza como derecha y `L` retrocede como izquierda). En la última tarjeta `SIG >` pasa a `EMPEZAR`.
    - **Tarjetas:** 1) **La catedral:** una horda de caídos y tú abriéndote paso por una nave que no termina. 2) **Moverse y apuntar:** la cruceta mueve; el lápiz apunta y mantenerlo pulsado carga el disparo. 3) **La marea:** sube desde abajo y empuja; quedarse atrás es peligroso. 4) **Vida:** 5 Sagrados Corazones; los enemigos a veces sueltan uno que cura 1 si lo pisas.
    - **Sin memoria entre sesiones:** no hay guardado en la consola, así que siempre sale; `SALTAR` es el atajo.

### 6.4 Marea y aparición de enemigos
- **Marea (revisada 2026-11-13, muelle elástico):** sube desde el borde inferior con velocidad elástica en función de la distancia al jugador (`dist = tide_y - player_y`):
  - **Cerca (`dist <= 80 px`):** frena a velocidad mínima (`40` en 8.8, ~0,16 px/frame), ~4,5× más lenta que el héroe (`181`), dando margen para retroceder un momento o escapar si te roza.
  - **Tramo elástico (`80 < dist < 336 px`):** sube linealmente con la distancia hasta alcanzar equilibrio con el jugador en torno a ~320 px.
  - **Lejos (`dist >= 336 px`):** velocidad máxima (`190` en 8.8, ~0,74 px/frame), algo superior al héroe para recortar distancia si avanza sin parar.
  - **Dentro de ella:** el jugador recibe daño continuo y su velocidad se reduce un 25 % (`* 3 / 4`, ~135 en 8.8 frente a 40 de la marea), así que siempre puede salir corriendo hacia arriba. Los enemigos y gemas que alcanza desaparecen sin dar recompensa. Se para durante el minijefe y el jefe. El aspecto (fuego, plaga u oscuridad) está por decidir.
- **Aparición:** la mayoría de los enemigos nacen arriba, fuera de la vista o en puntos visibles en la pantalla superior. Algunos salen de las salas laterales. Desde abajo vienen pocos y siempre con aviso en el borde inferior (emboscadas). La densidad sube con el tiempo.
- **Totales frente a simultáneos:** cientos de enemigos a lo largo de la run, unas pocas decenas a la vez entre las dos pantallas. Los que quedan muy atrás se reciclan. Cifras técnicas en `TECHNICAL.md` §4.7.

### 6.5 Clases y controles
- **Personaje = arma única.** En el juego actual ya no hay múltiples armas por personaje ni cambio de armas en partida: cada personaje tiene su única arma fija (por ejemplo, El Corazón Abierto con su rayo de fuego sagrado; la clase de escopeta será otro personaje). Se elige personaje al empezar la run.
- **Controles:**
  - D-pad: mover.
  - Stylus: apuntar por vector, como en §4.1. Mantener pulsado dispara solo al ritmo del arma, para no tener que tocar cientos de veces por run. En la escopeta repite cada bombeo. En el francotirador/láser sigue siendo cargar y soltar: la carga es su gracia. Si cansa en la DS, se revisa.
  - L (futuro): **habilidad activa con enfriamiento**, común a los personajes (como la granada de §4.9).
- **Controles de depuración en la ROM actual (solo debug, no son del juego):** `L` (ciclo de armas escopeta/francotirador/granada heredado de la v0.1), `SELECT` (estilo de efectos A/B/C) e `Y` (aura de carga L/G/E/H), así como cualquier cambio de animaciones en vivo, existen únicamente para depurar y probar en la DS.
- **Vida:** golpes más i-frames, como ahora (5 golpes de partida). De vez en cuando cae un pickup que cura 1 golpe.

### 6.6 Economía y mejoras
- **Gemas:** cada muerte suelta una gema cuyo valor depende del tipo de enemigo. Se recoge pisándola, con un imán corto que se puede mejorar. Las que se traga la marea se pierden, así que hay que decidir si se vuelve a por ellas.
- **Subir de nivel:** al llenar la barra se pausa el juego y se elige **1 de 3 mejoras** tocando la pantalla inferior. Unos 15–20 niveles por run. Sin reroll en la prueba.
- **Mejoras:** Dones (estadísticas apilables) en cada nivel y Reliquias (únicas, cambian cómo se juega) cada 4 niveles, diseñadas por arquetipos. Detalle en §6.12 (decidido 2026-11-15), que sustituye el reparto «mitad arma, mitad personaje».
- **Presentación:** cada mejora se muestra con icono, nombre y su efecto en una línea. Es la lección de la v0.2, donde los modificadores parecían aleatorios porque solo se veía el nombre.
- **Cofres:** los sueltan élites y minijefe. Dan una mejora extra.

### 6.7 Enemigos por escalones
| Escalón | Qué es | Estado |
| :--- | :--- | :--- |
| Enjambre | Débil y abundante: muere de un tiro y viene en grupos. Da la sensación de horda. | Nuevo; modelo nuevo en el lab |
| Cargador | §4.4 | Existe |
| Tirador | §4.5 | Existe |
| Élite | Versión mayor o tintada de los anteriores, con más vida. Aparece cada cierto tiempo y suelta un cofre. | Nuevo (reutiliza modelos) |
| Minijefe | A mitad de la run, al cambiar de bioma. | Nuevo |
| Jefe | Arriba, con 2–3 patrones. | Nuevo |

### 6.8 Qué se reutiliza y qué se sustituye
- **Se reutiliza:** armas y game feel (§4.3, §4.7), efectos (§4.9), IA de cargador y tirador, navegación por campo de distancias (adaptada a la franja), pipeline lab → baker, sandbox y escenarios.
- **Se sustituye:** las manadas dormidas por un generador de oleadas; los pedestales por la elección al subir de nivel; la mazmorra por la franja; el HUD de la run por uno de vida, experiencia, nivel y tiempo.

### 6.9 Hoja de ruta por versiones (revisada 2026-11-07)
La prueba de §6.1–6.8 se construye en versiones jugables pequeñas, cada una en su sesión y su rama. Una versión se cierra con el cierre de `AGENTS.md` (reglas 4 y 6), que en los hitos de versión incluye la batería completa de escenarios, y se fusiona en `main` antes de empezar la siguiente. Las que traen comportamiento nuevo empiezan con una sesión de diseño que lo deja escrito aquí (regla 9). Tras cada versión el usuario la juega en la DS y su feedback entra en la siguiente.

| Versión | Contenido | Antes de empezar | Estado |
| :--- | :--- | :--- | :--- |
| **0.3 mínima** | Franja infinita de 512 px, horda desde arriba, marea, curas y HUD de altura (§6.0). | — | Cerrada 2026-11-06 (`walkthroughs/v03-minima/`) |
| **0.3.1** | Tuning y pulido de la 0.3 mínima, con tres tiers de enemigos (esqueleto, cargador que carga, tirador láser) y escala de cifras 100 = 1,0 (§6.9.1). | Nada | Cerrada 2026-11-07 (`walkthroughs/v031-tuning/`) |
| **0.3.2** | Escenario del primer nivel: estilo, ambientación y piezas del entorno (§6.9.1b). | Sesión de dirección de arte | **En curso** (v2 en `main`, `walkthroughs/catedral-v2-salon/`, pendiente de ajustes de escala y variedad) |
| **0.3.3** | Personajes: reevaluar los sprites, ajustar tamaño y pasar al estilo definido en la 0.3.2 (§6.9.1b). | 0.3.2 cerrada | **En curso** (Corazón Abierto, Cireneo v2, telegrafía y SFX base en `main`; faltan Exvotos, Ojo del Tribunal y elegir aura) |
| **0.4** | Progresión dentro de la run: gemas con imán corto, experiencia, subir de nivel con pausa y elegir 1 de 3 mejoras con icono y una línea de efecto (§6.6), HUD de vida, experiencia, nivel y tiempo y controles de §6.5 que falten. Un solo personaje. | Sesión de diseño de mejoras | Diseño en curso (§6.12; faltan cifras) |
| **0.5** | Enemigos y recompensas: enjambre, élites que sueltan cofre, emboscadas desde abajo con aviso. Pool de 48 y criterio de horda de `TECHNICAL.md` §4.7 (IA por niveles de detalle, separación por rejilla, blit más barato). | Sesión de diseño de enemigos | Pendiente de diseño |
| **0.6** | Estructura de la run: la Subida de §6.13 (Vía Crucis de 14 estaciones, tres actos, jefes en las estaciones V, X y XIV, encuentros con sala cerrada), tramos hechos a mano por acto. ~15–18 min, ganar matando a El Paso. | Sesiones de escenario y de cada jefe | Estructura decidida (§6.13); faltan escenario y jefes |

**Correspondencia con el plan anterior por pasos:**
- La prueba de horda está medida con 24 enemigos (CPU media del 39 %, sin frames perdidos). El techo se mide en la 0.3.1 y el criterio de 48 activos se cumple en la 0.5.
- La sesión de diseño de contenido se reparte entre las versiones que la necesitan, en lugar de hacerse toda al principio.
- La franja procedural por bandas está hecha. Los tramos a mano llegan en la 0.6.
- Del bucle jugable, la marea, las oleadas y el HUD están hechos. Las gemas, el nivel y la elección llegan en la 0.4 y los cofres en la 0.5.
- El tuning se hace en cada versión y, a fondo, en la 0.3.1.

#### 6.9.1 Versión 0.3.1: tuning y pulido
**Objetivo:** que la 0.3 mínima se juegue bien varios minutos seguidos y deje unas cifras base estables antes de que las mejoras de la 0.4 las multipliquen.

**Dentro:**
1. **Tuning jugando en la DS.** Se ajustan las cifras marcadas `[TUNABLE-PLACEHOLDER]`:
   - horda (`include/horde.h`): intervalo, tope, rampas, grupos y mezcla de cargadores y tiradores;
   - marea (`include/tide.h`): distancia inicial, velocidad, ritmo de golpes y oscuridad;
   - curas (`include/pickups.h`);
   - stats de enemigos (`include/gameplay.h`);
   - daño y cadencia de las armas;
   - vida e i-frames del jugador.

   Los valores finales se escriben en esta sección como "valores de la 0.3.1".
2. **Fallos y molestias** que el usuario anote jugando, hasta dejar la run limpia.
3. **Techo de la horda:** subir el pool de 24 a 32 (y a 48 si cabe) y medir con `PERF_PROFILE`, vigilando `proj` (pico de 106.000 ticks en la 0.3 mínima). Si no cabe sin optimizar, la 0.3.1 se queda en lo que quepa a 60 FPS y la optimización pasa a la 0.5.
4. **Pulido de assets sin modelos nuevos:** contraste y lectura del suelo cian y de las columnas, lectura del borde de la marea y de la cruz de cura, y legibilidad del HUD.
5. **Limpieza:**
   - los escenarios `dungeon_pack_*` pasaban sin probar nada desde que la ROM principal es la franja. **Decidido 2026-11-07: no se borran.** Se movieron a `scenarios_legacy/dungeon_v02/` (fuera de `scenarioDirectory`, con su README) hasta que exista una variante de la ROM que arranque la mazmorra;
   - borrar `/dungeonds_perf.log` de la DS antes de medir.

6. **Tres tiers de enemigos y escala de cifras (decidido 2026-11-07, tras jugar la 0.3 en la DS).** Sustituye al reparto cargador/tirador de la 0.3 mínima y adelanta el "enjambre" de §6.7, que usa el modelo del esqueleto. Detalle en "Enemigos de la 0.3.1" abajo.

**Fuera:** gemas, mejoras, clases, biomas, tramos a mano y sonido. El único modelo nuevo es el esqueleto. Si el tuning muestra que algo más hace falta, se apunta para su versión y no se adelanta.

**Valores de la 0.3.1 (cerrada 2026-11-07).** El usuario jugó la ROM en la DS (`dungeonds.nds`, rama `feat/v031-tuning`, `PERF_PROFILE 0`) y dio por buenas las cifras: el rendimiento le pareció bien y el juego "se siente mucho mejor". Se quedan los valores de partida de "Enemigos de la 0.3.1" como definitivos de esta versión. Todo sigue marcado `[TUNABLE-PLACEHOLDER]` en código y se puede retocar en las siguientes.

| Cifra | Antes (0.3 mínima) | Valor de la 0.3.1 |
| :--- | :--- | :--- |
| Escala de vida y daño | enteros pequeños | centésimas, 100 = 1,0 |
| Vida del cargador | 60 | 300 |
| Vida del tirador | 20 | 200 |
| Vida del esqueleto | no existía | 100 |
| Velocidad del cargador | 90 % de la del héroe | 150 al acercarse, 650 al cargar |
| Velocidad del esqueleto / tirador | — | 130 / 180 |
| Reparto de la horda (esqueleto / cargador / tirador) | 0 / 75 / 25 % | 60 / 15 / 25 % |
| Cargadores vivos a la vez | sin tope | 3 |
| Láseres de tirador cargando a la vez | — (ráfagas de proyectiles) | 2 |
| Francotirador, daño | 30 | 150 |
| Escopeta, daño por perdigón | 8 | 40 |
| Granada, centro / borde | 60 / 15 | 300 / 75 |
| Borde de la marea | 2 px, tapado por el fundido | 3 px con degradado, fuera del fundido |
| Pool de enemigos | 24 | 24 (sin cambio) |

**Lo que no entró en la 0.3.1** y pasa a la lista de pendientes:
- **Techo de la horda 32/48:** no se subió el pool ni se midió el coste de los láseres con `PERF_PROFILE`. La percepción del usuario con el pool de 24 es de 60 FPS sin problemas, pero no hay log. Se mide en la 0.5, que es cuando se necesita el pool de 48, o antes si se ven caídas.
- **Marca visual del aturdimiento del cargador:** hoy no se ve cuándo está aturdido. Decisión de diseño pendiente; se resuelve junto al estilo de la 0.3.3.
- **Cruz de cura y vida en el HUD de la franja:** la vida no se dibuja en modo franja. Entra en el HUD de la 0.4.
- **Láser tras muros altos:** el rayo del tirador no se oculta tras ellos.
- **Divisiones `/` por frame** en persecución, apuntado y dibujo del láser: pasar a `div32` si una medición futura las señala.

**Enemigos de la 0.3.1 (decidido 2026-11-07).** Motivo: en la DS el cargador (60 de vida, 90 % de la velocidad del héroe, 75 % de la horda) se acumulaba y sobrepasaba en 10–15 s, y el tirador (proyectiles lentos, frágil) no amenazaba. Los números son `[TUNABLE-PLACEHOLDER]`.

- **Escala de vida y daño: enteros en centésimas, 100 = 1,0.** Sin `float` (`AGENTS.md` regla 2). Las mejoras multiplican en porcentaje (+20 % = 100 → 120), como `modifiers.h`. Todo el daño de armas pasa a ×5 (francotirador 30 → 150, borde de granada 15 → 75, perdigones ×5), con las proporciones de antes. La vida del jugador no cambia (5 golpes).

| Tier | Papel | Vida | Velocidad | Peso en la horda |
| :--- | :--- | :--- | :--- | :--- |
| Esqueleto (modelo nuevo) | Masa lenta que muere de un toque. Persigue y muerde como el cargador de la 0.3. | 100 | 130 (≈40 % del héroe, que va a 326) | 60 % |
| Cargador | Amenaza rara y rápida (FSM nueva). | 300 | 150 al acercarse, 650 al cargar | 15 %, máx. 3 vivos |
| Tirador | Amenaza a distancia con láser (FSM nueva). | 200 | 180 | 25 %, máx. 2 cargando a la vez |

- **Armas contra esa escala:** el francotirador mata esqueletos de 1 disparo (150 ≥ 100) y tiradores y cargadores de 2 (200 y 300). La escopeta a quemarropa debe matar a un esqueleto de 1 disparo y a un cargador en 2; con la distancia pierde daño, como hoy.
- **Cargador (cargar y esquivar):**
  1. *Acercamiento* lento por el campo de distancias hasta tener línea de visión a menos de ~160 px.
  2. *Telegrafía* ~30 frames (decidido 2026-11-13, rama `feat/cireneo-telegraph`): sin parpadeo del sprite. Reproduce el clip `cireneo_telegraph` (agachado progresivo con los pies abiertos) con un temblor de tensión de 1 px en los últimos frames y un pulso único de brasa tras la cruz al fijar la dirección hacia el jugador.
  3. *Carga* en línea recta con la dirección fijada, a 650 y hasta ~160 px. Daña al tocar al jugador (1 golpe, respeta los i-frames).
  4. *Recuperación* ~60 frames quieto y sin dañar, vulnerable. Luego vuelve al acercamiento.
  - Si choca contra un muro o columna durante la carga, queda **aturdido** ~90 frames.
  - **Aturdir con la escopeta y la granada (decidido 2026-11-07):** un golpe de escopeta o una explosión de granada durante la telegrafía o la carga lo interrumpe y lo deja aturdido ~60 frames. El francotirador no aturde: se le apunta desde lejos mientras sube.
- **Tirador con láser verde (esquivar la carga):** sustituye a los proyectiles.
  1. *Posicionarse* hasta su banda de distancia (como hoy).
  2. *Carga* ~60 frames: una línea fina verde sale de él y **sigue al jugador**.
  3. *Fijar* los últimos ~20 frames: la línea ya no gira y se ensancha; se esquiva saliendo de ella.
  4. *Disparo* ~8 frames: el rayo hace 1 golpe si el jugador está en la línea (respeta los i-frames).
  5. *Enfriamiento* ~90 frames.
  - El rayo **no se detiene en columnas** (igual que las balas, §6.0). Se dibuja con el mismo efecto que el láser del jugador, en verde.
  - Tope de 2 láseres cargando a la vez; el siguiente tirador espera en su banda. Motivo: coste de dibujar la línea y legibilidad.
- **Escenarios:** los tres tiers se prueban con sandbox (enemigos parados, héroe invulnerable salvo en la prueba de golpe) con geometría real (`AGENTS.md` regla 5).

**Condición:** si al medir aparecen caídas a 30 FPS, el juego va a media velocidad y las cifras no valen. En ese caso se resuelve antes el timestep (`TECHNICAL.md` §4.5) o se baja la carga.

#### 6.9.1b Versiones 0.3.2 y 0.3.3: dirección de arte (decidido 2026-11-07, detalle por decidir en sus sesiones)
Tras cerrar la 0.3.1, el usuario quiere dedicar dos versiones al aspecto antes de seguir con la progresión (0.4). No traen mecánicas nuevas.

**Dirección de estilo para las dos:** pasar el aspecto a algo del tipo **Trench Crusade o Warhammer 40k, pero más sucio y sombrío ("chungo")**: guerra de trincheras, metal oxidado y gastado, fe fanática, reliquias, suciedad y desgaste. Hoy el juego tiene suelo azul pizarra con acento cian y un space marine limpio; la nueva dirección reemplaza esa lectura. El estilo exacto, la paleta y la ambientación definitiva del primer nivel se deciden en la 0.3.2, con referencias del usuario (regla 9: nada se implementa sin decisión escrita aquí).

**0.3.2: escenario del primer nivel.**
- Objetivo: un escenario que de verdad guste al usuario, que fije estilo y ambientación del primer nivel.
- Flujo previsto: **generar imágenes** de las piezas (suelo, columnas, muros, atrezo) → pasarlas por **2D→3D** para obtener mallas 3D muy trabajadas → **pre-renderizarlas** con el lab como hoy (`TECHNICAL.md` §3).
- Se decide aquí: estilo, ambientación, paleta, lectura del suelo, las columnas y el borde de la marea con el nuevo aspecto, y presupuesto de tiles (hoy 90 de 400).
- **Decisiones de arte de la 0.3.2 (2026-11-07):**
  - **Hilo conductor: «la Cruzada que no terminó».** Un mundo que se pudría y una cruzada que perdió. Los enemigos son los «caídos» de esa cruzada, con ficha diegética breve (bestiario o diario de campaña) por tipo. Sin gran historia. El orden de biomas tras el nivel 1 queda abierto (candidatos: tierra de nadie, catacumbas/osarios, la brecha estilo Doom 2016 con marea de lava).
  - **Nivel 1: una catedral (decidido 2026-11-08, sustituye a la tierra de nadie del 2026-11-07).** Estética católica gótica oscura inspirada en Warhammer 40k, Trench Crusade y Blasphemous. Premisa: **la catedral que no termina**: se sube por una nave hacia un altar que se aleja, la guerra se metió dentro (bancos en barricada, sacos, alambre, cruzados muertos) y la marea se traga los bancos por detrás. La tierra de nadie pasa a bioma posterior (su suelo orgánico es el más caro en tiles).
    - **Tramos** de una pantalla de alto: nave, nave barricada, arco transversal, crucero (arena abierta), capilla o relicario lateral (cofre o élite); coro, cripta y ábside quedan para la 0.6.
    - **Progresión por estados:** cada tramo es una planta más un estado de profanación (0 sagrado → 3 ruina en guerra) que cambia variantes de pieza, densidad de suciedad, paleta y luz; las mismas piezas sirven para todos los estados. La primera demo empieza ya en guerra (estados 2-3); la degradación progresiva llega después.
    - **Bancos:** coberturas bajas. Cada tramo deja siempre 3 pasillos libres de ≥ 48 px (central y laterales), bancos en bloques cortos de 2-3 filas y huella de colisión ≤ 15 % del suelo. Se diseñan como estampa alineada a 8 px con versión rota del mismo tamaño, porque **bancos destructibles** es una mecánica candidata para más adelante (no en la 0.3.2).
    - **Vidrieras:** en los muros laterales; con la cámara ortográfica los muros se ven de canto, así que la vidriera se lee por sus **haces de luz que entran en horizontal hacia el centro** y su mancha de color en el suelo. Haces prerenderizados como sprites de hardware translúcidos y aditivos (tiñen también a los personajes), con polvo y respiración de intensidad. Pendiente del prototipo `proto/godrays` en la DS.
    - **Velas:** tiles de suelo con vela; llama animada reescribiendo los tiles de llama compartidos y halo con ciclo de paleta.
    - **Muros laterales:** pasan de 16 a 48 px por lado (suelo útil 416 px), con base de columnas, remate de muro y arranque de capillas.
  - **Coberturas bajas: bloquean el paso, no el fuego, y ocluyen como hoy.** Terreno (losas, alfombra, sangre, cera): solo decorativo. Cada arma es una clase: no se tienen ambas en una run.
    - **Piezas altas como cobertura (decidido 2026-11-16, rama `fix/cobertura-estatuas`):** las columnas y las estatuas (`santo`) paran todos los disparos, el rayo del jugador y el del Ojo, y cortan la visión del Ojo. Bancos, relicario y velas solo bloquean el paso.
  - **Color y legibilidad (2026-11-08, sustituye a la paleta de colores prohibidos):** sin colores reservados por ahora; entorno y personajes son preliminares y pueden compartir acentos mientras no estorben. La legibilidad se basa en **contraste de luminancia**: suelo transitable tranquilo, de valores medios-bajos y poco contraste local; el detalle fuerte en bordes, muros y piezas. Los personajes finales podrían ir **sin contorno**, con luz de contorno (rim light) del lab; se valida con el marine sobre el suelo nuevo.
  - **Suelo de la nave: damero en rombos (decidido 2026-11-08).** Losas cuadradas giradas 45° que alternan dos piedras pardas casi iguales (poco contraste, por legibilidad). A 30° cada losa es un **rombo de 32×16 px** (lado real 1,26 m). Losas modeladas en 3D (junta hundida, bisel, desgaste) y renderizadas con la cámara del juego y la luz neutra, nunca dibujadas en plano. Encima, **lápidas de cruzado** sueltas como piezas planas (estampas sin colisión) cada pocas pantallas. Cenefa geométrica y laberinto quedan como piezas especiales del crucero, más adelante. Referencias: damero de York Minster, lápidas de la nave de 's-Hertogenbosch, Cosmati de Westminster y laberinto de Amiens.
  - **Lápidas de suelo (decidido 2026-11-08; cerrado 2026-11-09).** La lápida **es** la losa. Se eliminaron definitivamente los stickers 2D y los cajeados oscuros con corte booleano. Se unificó el pipeline al 100% en el Shader Lab de Three.js (`tools/lab/export_map_package_headless.cjs`), con Blender únicamente como ensamblador 3D (`tools/floor/build_lapidas_lab_blender.py`), relieve escultórico v2 aumentado a 12 cm, cero outlines y cuantización nativa BGR555 de Nintendo DS. Ambas variantes quedan abiertas y viables para el mapa:
    1. **Vía A ($3 \times 2$ teselas = $80 \times 40\text{ px}$, diagonal a 45°):** sigue los ejes de las juntas del suelo. Muy natural para pasillos y tramos longitudinales de la nave.
    2. **Vía B ($3 \times 3$ teselas = $96 \times 48\text{ px}$, rombo con figura horizontal):** rombo de 9 losas con la figura tallada horizontalmente respecto a la pantalla. Gran presencia como hito central o focal.
    Evidencia maestra: `walkthroughs/v032-escenario/assets/cat_lapidas_lab_unified.png`.
    - **Sustituido el 2026-11-11 (lápidas v5).** La piedra tallada **ocupa el bloque entero de losas**: su borde es la junta del damero. Va a ras del suelo, con los surcos oscurecidos (oclusión ambiental horneada) y la cabeza o el travesaño al fondo de la pantalla (se lee desde los pies). Hay dos tamaños, **3×2 y 2×1 losas**, en cruz y caballero. La **Vía B se descarta**: una figura rectangular no puede llenar un rombo y se lee pegada encima. Retícula real del damero: juntas en `x + 2y ≡ 22,5` y `x − 2y ≡ 16,5` (mod 32). Proceso y lecciones: `tools/catedral_editor/gen/README.md`.

  - **Planta, muros y luz (decidido 2026-11-11, sustituye a lo que contradiga más abajo).**
    - **Planta de salón:** muros laterales continuos y rectos a los dos lados, sin entrantes ni capillas por ahora. Las columnas van en una línea paralela a cada muro. Crucero, capillas, coro y ábside quedan para más adelante.
    - **Regla de perspectiva:** todo se ve con la cámara del juego (ortográfica, 30°, mirando a lo largo de la nave). Nada de alzados frontales pintados en los muros.
    - **Muros:** el módulo 3D `gothic_arch` del usuario (zip `f450c095`), renderizado con el lab y repetido cada 128 px. Ocupa la franja entera de 48 px, como está. Con esta cámara se ve su remate superior: la cara con los arcos queda de canto.
    - **Corte en el techo:** muros y columnas suben hasta un techo que no se dibuja.
    - **Vidrieras y rosetones:** no se dibujan; se ven por su luz. El haz entra horizontal desde la cara interior del muro (x = 48 a la izquierda, x = 464 a la derecha). En `source/godrays.c` hoy sale de x = 16 y 240, que es un resto del muro antiguo de 16 px y hay que corregirlo.
    - **El muro y las lancetas pintadas de `make_cathedral_map()` se retiran.**
    - **Herramienta de diseño:** `tools/catedral_editor/editor.html`, para componer secciones a mano estampando las piezas reales. De sus diseños se sacarán las reglas del compositor.
  - **Compositor v2: la pantalla como unidad (decidido 2026-11-11 a partir del diseño del usuario en el editor; sustituye al ciclo de 4 tramos de 256 px).**
    > **Sustituido (2026-11-16) por el escenario por actos de §6.13.6** cuando se implemente; hasta entonces la ROM sigue con este compositor.
    - **Unidad:** una pantalla de 192 px. El número de pantalla decide el tipo y el azar (hash estable) solo las variantes, igual que antes: mismo cálculo en Python y en C, con test de paridad.
    - **Columnata:** una `columna_entera` por pantalla y lado, a la misma altura en las dos hileras (sprite en x = 64 y x = 416; la base cae en el borde inferior de la pantalla). Periodo de 192 px. Todas enteras: la columna rota y la caída salen de la demo.
    - **Tipos de pantalla, alternados al azar:**
      - **Bancadas:** dos grupos de 4 `banco_entero`, uno a cada lado del eje, con un paso vertical de 24 px. El marine (elipse de 12×6 px) cabe justo entre dos bancos: quedan 8–10 px libres entre huellas. Fila derecha en x = 288; fila izquierda en x = 136–160, por azar. El pasillo central mide entre 64 y 88 px.
      - **Relicario:** un `relicario` en el eje de la nave con 3–5 `vela` a su alrededor.
    - **Velas junto a las columnas:** 1–2 por columna con desplazamiento aleatorio, a veces parcialmente detrás de la columna (la oclusión es buscada).
    - **Luz:** un haz por pantalla, en el muro izquierdo o el derecho por azar (no simétrico) y a una altura variable dentro de la pantalla.
    - **Lápidas v5:** sueltas al azar (0–2 por pantalla) y, de vez en cuando, en grupos de 4–8 en escalera siguiendo la diagonal del damero. Nunca bajo un banco ni un relicario.
    - **Fuera de la demo:** `banco_roto`, `banco_volcado`, `columna` rota, columna caída, la barricada de `sacos` y el crucero del ciclo anterior. Los sacos se conservan como asset: el usuario los quiere usar más adelante.
    - **Implicaciones técnicas:**
      - El paso de bancos de 24 px (3 tiles) y la pantalla de 192 px (3 × 64) obligan a revisar las fases del baker, que hoy coloca piezas en múltiplos de 64 px más fases de 32 px.
      - Los godrays pasan de un periodo fijo de 256 px a uno por pantalla con lado aleatorio.
      - Hay que recontar el presupuesto de tiles con las lápidas v5 y el muro nuevo.
    - Diseño de referencia: el JSON del editor del usuario, guardado en `walkthroughs/distribucion-catedral/assets/diseno_usuario_v1.json`.
    - **Implementado (2026-11-11), con estos ajustes técnicos:**
      - **Bloques de 2 pantallas.** El compositor trabaja en bloques de 384 px (2 pantallas = 3 bandas) y la tira se desplaza 768 px por rebase, antes 512.
      - **Bancos como grupo.** Los 4 bancos de cada fila se hornean como una sola pieza, `banco_grupo4`, porque a 24 px se solapan en tiles. El grupo arranca en la fila 0 u 8 de su pantalla; el diseño del usuario arrancaba 6 filas más abajo.
      - **Velas en sitios fijos.** Las velas eligen entre un juego cerrado de posiciones (`VELA_PHASES`), porque cada posición cuesta tiles. Alrededor del relicario salen 3–4, no 3–5.
      - **Lápidas en dos fases.** Cada lápida tiene dos estampas, (0,2) y (2,3) en tiles, una por cada color del damero. Así encaja en cualquier posición de las juntas sin invertir el color del borde.
      - **Presupuesto:** 857 de 1.024 tiles, peor ventana de 379 de 440 y 2.416 KB de RAM de 4.096.

  - **Hoja de ruta para cerrar el escenario de la catedral (Sesiones atómicas):**
    Para que la catedral tenga forma y se sienta como un templo gótico completo y jugable antes de dar por cerrada la 0.3.2, el trabajo restante se divide en 5 sesiones atómicas:
    1. **Sesión 1: Composición espacial y distribución del mapa (primera propuesta; distribución visual pendiente de revisión).**
       - **Unidad de composición:** tramo lógico de 192 px de alto (una pantalla). El motor puede seguir generando bandas técnicas de 128 px; sus cortes no deben leerse como cortes arquitectónicos.
       - **Eje y circulación:** nave central continua hacia arriba, con respiros laterales. Se conservan tres corredores longitudinales de suelo libre, cada uno de al menos 48 px; el corredor central apunta a 64 px. Los muros de 48 px por lado y el suelo útil de 416 px siguen siendo la medida del carril.
       - **Familias de composición, no ciclo fijo:** nave despejada, nave con barricadas cortas y crucero abierto. Cada aparición cambia el lado, la posición y la variante de sus piezas; no se repite la misma planta consecutivamente. La secuencia puede variar, pero no pierde el eje central ni los tres corredores.
       - **Cadencia objetivo:** un crucero cada 4–6 pantallas. Capilla lateral opcional cada 8–12 pantallas, como desvío corto de fondo ciego que se abre a un solo lado y no interrumpe la ruta principal; alternar el lado cuando vuelva a aparecer. No emparejar capilla y crucero en el mismo tramo.
       - **Elementos:** bancos en bloques de 2–3 filas, huella total ≤15 % del suelo útil y colocados fuera de los tres corredores; las barricadas se alternan entre ambos lados. Lápida Vía A como acento longitudinal ocasional de nave; Vía B como hito infrecuente en cruceros. Cirios y altares quedan en márgenes o capillas, sin estrechar los corredores.
       - **Compositor de la catedral (decidido 2026-11-10, sustituye al reparto aleatorio de la primera pasada).** El número de banda decide qué se coloca; el azar solo elige variantes. Sin estado entre bandas: el mismo cálculo en Python (`tools/bake_cathedral_kit.py`) y en C (`source/strip.c`), con test de paridad.
         - **Unidad:** el **tramo** de 256 px (2 bandas de 128 px; `tramo = banda >> 1`). Una pieza nunca cruza el borde de una banda y solo se coloca sobre la retícula del baker (múltiplos de 64 px más la fase de la pieza).
         - **Ciclo de 4 tramos (1.024 px, unas 5,3 pantallas), repetido:** posiciones 0 y 1 = **sección de bancadas**; 2 = **barricada de sacos**; 3 = **crucero**. Cada tercer ciclo (por hash del ciclo) la posición 2 es un tramo **despejado** (sin sacos) para respirar. La zona inicial sin piezas (`STRIP_START_CLEAR_BANDS`) se mantiene.
         - **Columnata (todos los tramos salvo el crucero):** dos hileras junto a los muros, en x_tile 8 y 48 (cuerpos en px 72..112 y 392..432), una columna por banda. Cada columna es **entera** (55 %), **rota** (30 %) o **caída** (15 %, sin pieza) por hash estable; nunca dos caídas seguidas en la misma hilera. Una columna rota es una entera que cayó: nunca va fuera de la retícula. Piezas: `columna_entera` y `columna` (rota).
         - **Sección de bancadas (tramos 0 y 1):** dos filas paralelas de bancos, centradas en el eje de la nave (x=256): carriles en x_tile 19 y 35 (cuerpos en px 160..224 y 288..352, pasillito central de 64 px; el `banco_roto` de 72 px se comprueba contra las columnas). Los bancos de una fila van **pegados** con paso de 32 px (4 tiles: la altura del sprite) y todos con la misma orientación. **No son filas continuas sino grupos:** en cada tramo y cada fila hay **un grupo de 4–6 bancos pegados** (por hash, casi siempre 5), en una posición del tramo también por hash, siempre dentro del tramo (8 posiciones de 32 px); el resto de la fila queda libre. Los grupos de la fila izquierda y de la derecha se escalonan, de modo que el jugador zigzaguea entre grupos y por el pasillito. El marine **puede colarse entre dos bancos de un mismo grupo** (hueco de 16 px entre huellas; decidido 2026-11-11 que se queda así). Tipo de banco: **`banco_entero` 75 %, `banco_roto` 25 %** por hash de cada banco. `banco_volcado` no va en las filas: solo suelto junto a los sacos como escombro. Sin estatuas, velas ni lápidas dentro de la sección.
         - **Barricada (tramo 2):** una línea de `sacos` que cierra algo más de la mitad de la nave, con 1–2 `banco_volcado` junto a ella; alterna de lado en cada ciclo; el otro lado queda abierto con ≥48 px.
         - **Crucero (tramo 3):** sin columnas, bancos ni sacos. Dos `santo` simétricos junto a las posiciones de la columnata, 2–4 `vela` junto a cada uno y un `relicario` en un lateral; la lápida de Vía B puede ir en el centro. Es la arena abierta del primer nivel.
         - **Atrezo libre:** velas y lápidas planas solo en el tramo despejado y en el crucero. Nunca dentro de una sección de bancadas.
         - **Invariantes:** el pasillo central (entre las hileras) y al menos un paso lateral abiertos en toda la tira, cada uno ≥48 px; las lápidas siguen sin colisión ni oclusión. Mientras no existan los sprites definitivos de los laterales, la anchura de los pasos laterales junto a los muros no se valida.
         - **Estado de las piezas:** `banco_entero`, `sacos`, `columna_entera` y la `vela` reducida (14 px) se renderizan en esta sesión; la escala general de las piezas queda para otra sesión.
         - **Restricción técnica:** las piezas solo pueden colocarse sobre la retícula del baker (múltiplos de 8 tiles = 64 px más la fase de cada pieza), porque cada estampa lleva el suelo cocido en 4 fases. El baker y los assets no se tocan en esta sesión.
       - **Ritmo de recorrido:** iniciar con nave despejada, introducir una barricada tras uno o dos tramos y abrir el primer crucero tras varias pantallas. Después alternar naves de distinta densidad, transiciones y capillas infrecuentes; los cruceros son hitos espaciados. No se impone una secuencia repetible.
       - Ejemplo de recorrido y reglas de colocación: `walkthroughs/layout-catedral/walkthrough.md`. Incluye ocho pantallas con coordenadas y comprobación geométrica. La primera propuesta ya se llevó a ROM; el usuario no está satisfecho con la distribución de bancos y estatuas. Conservar los requisitos de circulación, pero rehacer la composición y validarla en una ROM reproducible.
       - **Pendiente de decisión del usuario:** qué falla en la distribución actual. Hoy el generador coloca de 1 a 4 piezas sueltas por banda de 128 px, elegidas por hash y sin bloques de bancos de 2–3 filas. La sesión que lo rehaga empieza enseñando alternativas y no programa nada hasta que el usuario elija (regla 9). Orden y briefs: `walkthroughs/catedral-siguientes-pasos/`.
    2. **Sesión 2: Muros laterales, arcadas y vanos de vidrieras/rosetones (primera pasada autorizada 2026-11-09; revisión visual del usuario pendiente).**
       - **Base de planta:** muros continuos dentro de las franjas laterales $X=0..48$ y $X=464..512$; el suelo jugable sigue siendo $X=48..464$ (416 px). Pilastras y contrafuertes quedan dentro de esas franjas y no estrechan los corredores de la Sesión 1.
       - **Ritmo lateral:** módulos de pared repetibles; cada tramo de 128 px forma un arco apuntado poco profundo entre pilastras. Una bahía de luz cada 256 px alterna el muro izquierdo y el derecho según los anclajes del prototipo (`GODRAY_PERIOD=256`, `GODRAY_ANCHOR=64`); los arcos sin vidrio quedan ciegos. La alternancia de las dos paredes se repite cada 512 px; el primer ciclo de escena es de 1.024 px para incluir un hito de crucero cada 4–6 pantallas (`TECHNICAL.md` §4.7).
       - **Vanos:** lanceta geminada con parteluz en muro lateral. En coordenadas actuales del prototipo, la apertura ocupa $X=0..32$, $Y=256n+80..128$ en el muro izquierdo para $n$ par; en el derecho se refleja en $X=480..512$ para $n$ impar. La misma abertura conserva posición y marco en estados 2-3; cambia el vidrio (primera pasada multicolor de burgundy, azul-violeta y oro apagado; estado 2 entero agrietado → estado 3 roto). El haz queda separado del prerender.
       - **Arte provisional autorizado:** piedra caliza gris cálida de bajo contraste; tracería de plomo oscura, vidrio multicolor profundo y formas grandes legibles a escala DS. Altura inicial de muro 4 m junto al marine de 2 m; se revisa tras ver la ROM y no congela el arte final.
       - **Rosetón:** pieza independiente, centrada en $X=256$ y mirando hacia el jugador, en el arco transversal del crucero; diámetro objetivo 64 px con 12 sectores radiales. No se coloca como una ventana lateral periódica. La Sesión 3 debe anclar su haz a ese rosetón frontal, porque el prototipo actual coloca todas sus variantes en los muros laterales.
         - **Decisión 2026-11-10: el inlay de rosetón y el umbral gris pintados en el suelo se retiran.** Leídos en la ROM, un círculo frontal plano sobre el suelo de la nave parece una calcomanía fuera de la perspectiva 2:1 y se repetía cada 1.024 px sin relación con el crucero. El rosetón vuelve solo como pieza vertical del arco transversal del crucero (ver arriba), cuando exista ese sprite.
       - **Prioridad de luz en crucero:** en la pantalla que muestre el rosetón no se dibuja a la vez un haz lateral; la mezcla de hardware tiene una intensidad global y dos haces solapados no se suman. La sesión 3 aplica esta prioridad y mantiene visible el vano lateral sin su haz mientras domina el rosetón.
       - **Arco transversal:** conservar la pieza de 416 × 64–96 px del catálogo, en el borde norte del crucero y con el rosetón centrado. La huella de suelo queda transitable; la profundidad de oclusión sale del mismo render (`TECHNICAL.md` §3.3).
       - **Presupuesto y render:** repetir el atlas de piedra y reutilizar pilastras/paños; no prerenderizar cada pantalla de muro como una imagen única. Exportar color, huella y profundidad con la cámara y luz neutra canónicas. Primer bake: 1.024 tiles totales, 224 en la ventana de 33×25; la sesión 4 optimiza el margen del kit antes de sumar las piezas finales.
       - **Revisión pendiente del usuario:** corregir estilo, altura, color y silueta después de probar esta primera ROM. El modelo emparejado de vidriera se compone en Blender; el primer kit usa una traducción pixelada de esa silueta, más muros laterales y un inlay de rosetón. La primera ROM y sus límites están en `walkthroughs/muros-catedral/walkthrough.md`.
    3. **Sesión 3: Integración de Rayos de Luz (Godrays) — prototipo integrado, cierre técnico pendiente.**
       - Los godrays ya están integrados en las variantes de catedral y el usuario los considera prácticamente resueltos.
       - Sigue pendiente asociar cada haz a su emisor correcto (lancetas laterales y rosetón frontal), confirmar la convivencia con la marea y certificar rendimiento en DS con `PERF_PROFILE`.
       - Walkthrough del prototipo: `walkthroughs/proto-godrays/`; revisión actual: `walkthroughs/catedral-cierre/`.
    4. **Sesión 4: Cierre del Kit de Catedral y presupuesto VRAM ($\le 1024$ tiles)**.
       - Integrar/optimizar en `tools/bake_cathedral_kit.py` el suelo de rombos, las lápidas (Vía A / B), muros y props seleccionados; el primer pase del mapa visual ya está integrado. La distribución de bancos y estatuas debe rehacerse tras la revisión del usuario.
       - **Coherencia de color, colisión y profundidad de props: resuelta (2026-11-10, validada por el usuario en la DS).** La causa era de unidades: la profundidad de los props seguía en píxeles del render fuente. Detalle técnico: `TECHNICAL.md` §3.3; walkthrough: `walkthroughs/props-depth-units/`.
       - **Decisión (2026-11-10): un prop físico bloquea toda su planta sobre el suelo.** Los bancos, que son bajos, toman la envolvente convexa de su planta, de pata a pata, así que no se puede pasar por debajo del asiento ni entre las patas. Columnas, estatuas, relicarios y velas usan la huella del lab (geometría entre 0,30 y 1,20 m). Los props físicos ocluyen por profundidad como los muros; las lápidas siguen sin colisión ni oclusión.
       - **Presupuesto actual:** el kit está en 1.024 de 1.024 tiles. No cabe ninguna pieza nueva sin liberar tiles antes.
       - Cumplir estrictamente el presupuesto de VRAM: $\le 1024$ tiles totales y $< 440$ tiles en la peor ventana visible de 512 px para scroll sin fallos.
    5. **Sesión 5: Certificación de Rendimiento a 60 FPS en Hardware Nintendo DS**.
       - Compilar la ROM final con `PERF_PROFILE 1`, subir por FTP (`upload-rom.ps1`) y registrar `/dungeonds_perf.log`.
       - Certificar que la combinación de suelo Tripo + lápidas + godrays se mantiene bajo los 560.190 ticks por frame en la consola real.
  - **Sombras de las piezas (decidido 2026-11-08).** Las piezas proyectan sombra sobre el suelo igual que los personajes: misma dirección de la luz principal del lab (preset «Neutra») y oscurecimiento parecido. Se hornea en los tiles de la estampa (sin coste por frame): la estampa crece lo que ocupe la sombra y los píxeles de suelo bajo ella se oscurecen. Las lápidas, planas, no llevan sombra.
  - **Luz única neutra y sprites sin contorno (decidido 2026-11-08).** Piezas, suelo y personajes se renderizan en el lab con **la misma luz: el preset «Neutra»** (`tools/props/props_render_settings.json`: contraste 1,2, saturación 1,0) en lugar del ámbar con saturación 1,5, que volvía todo naranja y borraba piedra, oro y burdeos. La paleta de la catedral se extrae de los prerenders con esa luz (comparativa en `walkthroughs/v032-escenario/assets/paleta_A_vs_B.png`). Los personajes (marine, cargador, tirador y esqueleto) se prueban desde ahora **sin contorno** (`outlineMode` «none») y con esa luz; se adoptan si se leen sobre el suelo nuevo en la ROM, y si no se vuelve al contorno de 1 px.
  - **Legibilidad del pre-render de personajes (decidido 2026-11-14, rama `feat/legibilidad-lab`, variante «C2»).** Sigue sin contorno. El lab exporta los personajes con: **supersampling ×4** (antes ×2); **tono neutro** en lugar del tono de cine actual, que apagaba la imagen y obligaba a subir el contraste a toda la imagen (eso aplastaba sombras a negro y quemaba luces: 12,6 % de negros en el cargador, 19,4 % de blancos en el esqueleto); una **curva S suave** con el punto medio en el brillo medio del propio personaje, que sube el contraste de los tonos medios sin recortar extremos; **bordes al 30 %** de cobertura (antes al 16 %, que dejaba píxeles negros sueltos; al 50 % se comía brazos y astas finas); y un **enfoque suave** tras reducir, que solo compara píxeles del propio personaje para no crear halo contra el suelo. Al convertir a colores de DS se redondea en vez de truncar. Descartado tras probarlo: contraluz direccional detrás del personaje (a 40–60 px no se ve), brillo de borde por ángulo de visión (desteñía sobre suelo claro), enfoque medio (ruidoso) y bajar el relieve de los materiales (sin efecto en los modelos actuales). Evidencia A/B con Corazón y Abanderado: `walkthroughs/legibilidad-lab/`. Se adopta definitivamente cuando se vea en la ROM sobre la DS. **Estado (2026-11-14):** el lab tiene el preset «Legibilidad: Anterior / C2» (por defecto Anterior; en exportación headless `--legibility c2`), que cubre supersampling, tono, curva S y enfoque. Falta la parte de la conversión a DS (bordes al 30 % y redondeo en `tools/generate_player_sprites_c.py`), re-exportar los personajes de la ROM y el botón para alternar sets en la consola. El escenario no se toca: faltan los modelos 3D de la columna y el banco.
  - **Tamaño del Abanderado:** mide ~3 m, unos 54 px de alto en celda de 60×60 (Corazón, 1,80 m: 31–33 px en celda de 40×40), coherente con la escala única de abajo.
  - **Escala única (corrige `TECHNICAL.md` §4.1):** el marine mide **2 m** y ocupa 31 px de alto, así que el mapa se dibuja a **~17,9 px/m** (no 40,42) y los enemigos de 1,5 a 3 m miden 23–46 px. Equivalencias: baldosa de 32×16 px = 1,8 m; el carril de 480 px = 26,8 m; una banda de 128 px = 14,3 m de profundidad; un saco de arena (0,5 × 0,3 m) = 9 × 5 px; un cráter de 4–8 m = 72–144 px. Los sprites actuales no cambian de tamaño.
  - **Método (2026-11-08):** el suelo es un **juego de tiles diseñado**, no un render troceado: losas con tiles Wang y transiciones por esquinas (alfombra, mosaico, sangre, cera). Las **piezas** (bancos, columnas, estatuas, relicarios, sacos, cirios) siguen el flujo de los personajes: imagen de IA → 2D→3D (Tripo) → render con la misma cámara y luz que los personajes → estampa alineada a 8 px con su huella de colisión y profundidad de oclusión. Escala de juego: piezas un 30-50 % mayores que las reales si hace falta para leerse. Paleta: se extrae de los prerenders de las piezas del lote 1 y la aprueba el usuario (el arte objetivo de pantalla completa se canceló el 2026-11-08). Flujo completo paso a paso: `walkthroughs/v032-escenario/BIBLIA.md`. Motivo: con relieve o grano continuo ningún tile se repite (medido: 960 tiles distintos por banda de 480×128 y 825 en la ventana visible, frente al tope de 440; `walkthroughs/v032-escenario/INFORME_INTENTOS.md`).
  - **Presupuesto:** hard: < 440 tiles distintos en cualquier ventana visible de la pantalla superior (cache de 448). El tope de 400 totales del kit es del script de bake y puede revisarse. Pruebas y evidencias en `walkthroughs/v032-escenario/`.
- Cierre: el escenario se ve bien en la ROM real (capturas) y 60 FPS en la DS (regla 6).

**0.3.3: personajes.**
- **Reevaluar** si los sprites actuales (héroe, cargador, tirador, esqueleto) valen con el nuevo estilo.
- **Ajustar ligeramente su tamaño** (`TECHNICAL.md` §4.1, escala personaje/mapa) y mantener anclas, muzzle y sombras.
- Mejorar el estilo pasando de nuevo el flujo imagen → 2D→3D → pre-render, incluida la **marca visual del aturdimiento** del cargador (pendiente de la 0.3.1).
- Cierre: contactos de las 8 direcciones revisados de verdad, build sin warnings, tests de sprites y 60 FPS en la DS.

#### 6.9.1c Demo para un colega (decidido 2026-11-14)
**Objetivo:** una ROM que un colega juegue ~5 minutos para **evaluar los gráficos y el *juice***, sin subir de nivel y sin cosas a medias a la vista. La economía y las mejoras (0.4) no tienen código, así que no hay nada que ocultar ahí.
- **Vida en pantalla con corazones:** la vida del jugador (5 golpes) se muestra como fila de **sagrados corazones** (`14×18` px, sin outline) en la pantalla inferior, arriba a la derecha (lleno = vida, apagado = perdida). Los iconos salen del modelo 3D del Sagrado Corazón pre-renderizado con el lab (`--legibility c2`) y horneado con `tools/hud/prerender_hud_heart.py`, `tools/hud/bake_hud_heart.py` y `tools/generate_hud_icons_c.py`.
- **Drops de vida:** siguen activos y sustituyen la cruz verde por el mismo icono del **Sagrado Corazón** (`g_hud_heart_full`), levitando suavemente arriba y abajo sobre una pequeña sombra en el suelo.
- **Arma única:** el héroe sale con el **láser** (su arma real, §6.10) y `L` deja de cambiar de arma en la ROM principal. Escopeta y granada siguen solo en las variantes de prueba (sandbox y catedral de revisión).
- **Comparación de efectos se mantiene:** `SELECT` (estilo de efectos) e `Y` (aura de carga) siguen activos para que el colega compare gráficos.
- **Marea:** se queda la actual. La marea de esqueletos (`walkthroughs/marea-esqueletos/`, solo maquetas) no entra.
- **Run infinita:** no hay meta ni pantalla de fin; se juega hasta morir y se reinicia (§6.0).
- **Falta, fuera de esta demo:** **pantalla inicial** con tres botones (**Nueva partida**, **Bestiario**, **Controles**), que también se abre con `START` durante la partida (pausa). El bestiario lleva gráficos y lore de cada enemigo. Ambas son sesiones propias.

> **Versiones 0.4 a 0.6: borrador.** Recogen lo que se espera hoy de cada una según §6.1–6.8. Se revisan con el feedback de la versión anterior y en su sesión de diseño, que decide los detalles y puede mover piezas de una versión a otra.

#### 6.9.2 Versión 0.4: progresión dentro de la run (borrador)
**Objetivo:** que cada run tenga decisiones que cambien cómo se juega y que morir enseñe qué elegir la próxima vez. Es el criterio de éxito de la prueba (abajo).

**Dentro:**
- **Gemas** al matar, con valor según el tipo de enemigo. Se recogen pisándolas, con un imán corto, y la marea se las traga (§6.6). Se dibujan en OAM (`TECHNICAL.md` §4.7).
- **Experiencia y nivel.** Al llenar la barra se pausa el juego y se elige **1 de 3 mejoras** tocando la pantalla inferior. Unos 15–20 niveles por run, sin reroll.
- **Mejoras:** sistema de §6.12: 7 Dones y 10 Reliquias del Corazón Abierto, nuevo comportamiento base del rayo y estado Quemado en los enemigos.
- **Clases:** fuera de la demo; un solo personaje, El Corazón Abierto (decidido 2026-11-15).
- **Controles de §6.5 que falten:** mantener pulsado para disparar al ritmo del arma y la granada en L con enfriamiento.
- **HUD:** vida, barra de experiencia, nivel y tiempo; se mantiene la altura.

**Antes de empezar (sesión de diseño):**
- ~~lista de mejoras y cómo se combinan~~: hecho en §6.12;
- lo que queda está en §6.12.9 (cifras, curva de experiencia, curas e iconos).

**Fuera:** cofres, élites y enemigos nuevos (0.5); progresión entre runs (§1).

#### 6.9.3 Versión 0.5: horda con escalones y recompensas (borrador)
**Objetivo:** que la horda tenga ritmo y picos (masas fáciles, amenazas puntuales) y que haya algo que perseguir además de subir.

**Dentro:**
- **Enjambre:** enemigo débil y abundante, que muere de un tiro y llega en grupos. Necesita un modelo nuevo en el lab (§6.7).
- **Élites:** versiones mayores o tintadas del cargador y del tirador, con más vida. Aparecen cada cierto tiempo y sueltan un **cofre** con una mejora extra.
- **Emboscadas desde abajo:** pocas y siempre con aviso en el borde inferior (§6.4).
- **Motor de horda:** pool de 48 con IA por niveles de detalle, separación por rejilla y blit más barato, hasta cumplir el criterio de `TECHNICAL.md` §4.7 (32 visibles, 48 activos, 60 FPS en la DS).
- Ritmo de aparición por oleadas o picos en lugar de la rampa lineal de la 0.3.

**Antes de empezar (sesión de diseño):**
- aspecto y comportamiento del enjambre;
- cómo se reconoce un élite;
- frecuencia de élites y emboscadas;
- contenido de los cofres.

**Fuera:** minijefe, jefe, biomas y tramos (0.6).

#### 6.9.4 Versión 0.6: estructura de la run completa (borrador)
**Objetivo:** la prueba completa. Una run de 15–18 min con principio, mitad y final, que se gana matando al jefe. **La estructura está decidida en §6.13 (2026-11-16) y prevalece sobre este borrador** (tres actos en lugar de dos biomas, tres jefes en lugar de minijefe y jefe, encuentros en el pasillo con sala cerrada).

**Dentro:**
- **Mapa por tramos** hechos a mano de una pantalla de alto, encadenados por reglas (abierto, estrechamiento, sala lateral con cofre o élite, coberturas bajas), en lugar de las bandas procedurales de la 0.3 (§6.2). Pipeline lab → baker para los tramos.
- **Dos biomas,** uno en cada mitad, con su paleta y su kit.
- **Minijefe** al cambiar de bioma y **jefe** en una sala final, con 2–3 patrones. La marea se para durante los dos combates (§6.4).
- **Final de run:** pantalla de victoria; la de muerte se mantiene.
- Longitud total ajustada para que dure ~8 min a la velocidad de la marea.

**Antes de empezar (sesión de diseño):**
- catálogo y reglas de los tramos;
- tema de los biomas;
- diseño del minijefe y del jefe;
- aspecto final de la marea (fuego, plaga u oscuridad);
- si la run sigue siendo infinita después del jefe o termina ahí.

**Fuera:** progresión entre runs, más clases, sonido y más biomas (§1). Se deciden después de comprobar que la prueba divierte.

**Criterio de éxito de la prueba:** el usuario juega varias runs seguidas en la DS, muere pronto en las primeras y aun así quiere otra porque sabe qué elegiría distinto.

### 6.10 Reparto de la demo (sesión de concepto, 2026-11-11)
Conceptos para la demo de la catedral. Solo cambia el aspecto y se añaden élites y jefe; las mecánicas base son las de "Enemigos de la 0.3.1" (§6.9.1). Nada de esto se programa hasta que su detalle esté escrito aquí (regla 9).

- **Personaje (clase láser): se continúa con El Corazón Abierto** (el usuario ya generó modelo y animación de carga); El Lector y La Custodia quedan en reserva. Prompts y pendientes: `walkthroughs/concepto-demo-personajes/`. Mecánica: cargar, soltar, rayo que atraviesa filas (desde 2026-11-15 atraviesa a quien mata y lo cortan muros y columnas, §6.12.2). Las imágenes para 3D se generan en **T-pose, con las manos vacías**, y el arma en una imagen aparte; se ensamblan después.
  El rayo no es un arma sino un milagro que consume el cuerpo: sale del propio personaje, que va quemado por usarlo y sigue vivo por fe (tono Trench Crusade). A 31 px el origen del rayo debe ser un punto de luz claro y la carga una pose que cambie la silueta. Descartados (2026-11-11, genéricos): Portaluz, Hermana del Cirio y Penitente tirador.
  1. **El Lector:** monje con un libro encadenado a la muñeca; al cargar alza libro y cabeza recitando y el rayo sale de boca y ojos. Cara quemada hasta el hueso, capucha chamuscada.
  2. **El Corazón Abierto:** pecho abierto con grapas de hierro y un sagrado corazón en llamas dentro; carga con los brazos en cruz y el rayo sale del pecho. Ropa quemada en círculo alrededor.
  3. **La Custodia:** sacerdote con una custodia soldada en lugar de cabeza; carga echando la cabeza atrás mientras crecen sus rayos y dispara desde la hostia. Cuello de carne fundida con el metal.
- **Color de personajes (decidido 2026-11-12):** todos los personajes, protagonista y enemigos, llevan **acentos negros y rojos** por legibilidad; la base de cada uno (cera, piel, metal) y los brillos (dorado del corazón, verde de los caídos) se mantienen.
- **Enemigos (revisado 2026-11-12):** son los caídos de la Cruzada, gente cuya fe se pudrió. **Cada uno hizo un pacto:** entregó algo de sí mismo a cambio de un poder, el precio se ve en el cuerpo y es su debilidad en el juego; su luz es **verde enfermiza** frente al dorado anaranjado del Corazón Abierto. Mecánicas base sin cambios (misma FSM que en la 0.3.1).
  - **Masa → Los Exvotos:** devotos convertidos en figuras de cera de tamaño humano, en procesión lenta con cirios fundidos en las manos. Mueren de un golpe y se derriten.
    - **Aspecto y animaciones (decidido 2026-11-14):** monja de cera con velo negro y faja roja (`assets/models/characters/exvoto/source/`, Tripo con rig Mixamo). Llevan las **manos juntas rezando** en lugar de cirios; las velas pasan a ser atrezo del mapa junto al que rezan. Clips: **rezar de pie** (bucle), **rezar de rodillas** (bucle), **levantarse** (de rodillas a de pie) y **andar rezando** (andar genérico de procesión con los brazos fijos en la pose de rezo, cuerpo encorvado y cabeza baja). Fuentes de rezo: clips de Mixamo en `assets/models/animations/pray/`.
    - **Comportamiento «en oración» (decidido 2026-11-14; cifras `[TUNABLE-PLACEHOLDER]`):** los Exvotos empiezan quietos rezando de rodillas (desde 2026-11-15, ver «Postura»), repartidos un poco al azar pero con sentido en el mapa: junto a velas, frente a rosarios u otro atrezo devoto. Cuando el héroe se acerca, despiertan y empiezan a andar hacia él (los arrodillados se levantan primero). Pendiente para su integración: radio de despertar, si despiertan en grupo y cómo se colocan los puntos de oración en los tramos.
    - **Exvoto en el juego, versión mínima (decidido 2026-11-14, rama `feat/exvoto`; cifras `[TUNABLE-PLACEHOLDER]`):**
      - **Sustituye al esqueleto** como masa: misma vida (100), velocidad (130), ataque por contacto (1 golpe) y peso en la horda (60 %). El esqueleto deja de aparecer.
      - **Dónde rezan:** nunca al azar. Cuando la horda saca Exvotos, los coloca **delante de una pieza devota** del tramo que entra por arriba (la misma franja de aparición que hoy): **estatua de santo, vela o relicario**. Se ponen a 1-2 celdas de la pieza, en hueco libre, **de cara a ella** (la dirección del sprite mira al centro de la pieza). Un grupo de la horda (hasta 4) se reparte en arco alrededor de la misma pieza. Si en esa franja no hay ninguna pieza devota libre, el Exvoto aparece **ya despierto y andando** (como el esqueleto hoy), nunca rezando a la nada.
      - **Postura (decidido 2026-11-15):** todos los que nacen rezando lo hacen de rodillas; como gran parte de la masa llega ya andando desde arriba, los que te encuentras rezando se levantan al despertar. El rezo de pie queda disponible en la ROM (`EXVOTO_KNEEL_PERCENT`, `[TUNABLE-PLACEHOLDER]`) pero la horda no lo usa.
      - **Despertar:** cuando el héroe está a menos de **96 px** o cuando recibe daño. **En grupo:** al despertar uno, despiertan también los Exvotos rezando a menos de **48 px** de él (en cadena, así una procesión arranca de golpe). La arrodillada reproduce *levantarse* (~70 frames de clip, sin moverse) y luego anda; la de pie anda al instante.
      - **Andar:** clip *andar rezando* hacia el héroe con la IA del esqueleto.
      - **Muerte («se derrite»), sin animación 3D nueva:** el sprite se hunde y se aplasta en ~20 frames y deja un **charco de cera** en el suelo (elipse 2:1 clara con borde oscuro, colores desaturados) que dura ~90 frames, se desvanece y no hace nada.
      - **Marea:** si alcanza Exvotos rezando, desaparecen sin recompensa, como el resto.
  - **Cargador → El Cireneo:** entregó sus brazos a cambio de la fuerza de la cruz. Es un gigante crucificado que camina: brazos clavados al travesaño y cruz atornillada a la espalda. Embiste encorvado con la cruz por delante y no puede girar; al chocar con una columna la cruz se clava y forcejea para sacarla (aturdimiento y marca visual). Los brazos van fijos en la pose del T-pose.
  - **Tirador → El Ojo del Tribunal:** inquisidor con una linterna de vidrio verde enjaulada en lugar de ojos; su láser es su mirada (sigue, se fija, sentencia).
    - **Aspecto (decidido 2026-11-14):** **bajo y gordo**, túnica **morada oscura** (no negra) con faja roja, pliego blanco y sello de lacre. Motivo: que no todos los caídos sean altos y delgados (silueta reconocible en la horda) y que el cuerpo se separe del suelo oscuro y de los demás enemigos. El Ojo debe leerse visiblemente más grande que el protagonista (objetivo aproximado: +40 % de altura). En juego el sprite pasa de 40×40 a 56×56 px (140 %) y el volumen de impacto acompaña la escala; la sombra de suelo conserva su huella actual. Modelo definitivo en `assets/models/characters/ojo/source/` (farol en lugar de cabeza, sin capucha); quedan descartados el gordo con capucha (`source_capucha/`) y el alto y delgado (`source_delgado/`).
    - **Cabeza en la mano (actualizado 2026-11-14):** antes interrogaba alumbrando a los reos con un farol en la mano; el pacto intercambió las dos cosas. El **farol** ocupa ahora su cabeza y vigila sin descanso; con el brazo extendido, donde llevaba el farol, sostiene **su propia cabeza**, ciega (ojos cosidos) pero aún juzgadora. Reparto en el juego: el **cono de vigilancia** nace del farol y el **haz de sentencia sale de la boca de la cabeza** (el `muzzle` del lab va al hueso de esa mano). La nueva cabeza de boca abierta `tripo_convert_5f17753f-45e7-4137-b616-5fe4530a11f8` sustituye a la anterior y se renderiza al 150 % de su escala previa, conservando el punto de agarre. Es una malla estática: el movimiento de caminar, mirar y sentenciar lo aporta el brazo del Ojo.
    - **Carga de la boca (decidido 2026-11-14):** durante el segundo de fijación pasa de apagada a muy brillante en una progresión continua y legible. El brillo nace dentro de la boca y crece como un aura verde irregular pegada a la cabeza; en la parte final aparecen unas pocas lenguas de energía ascendentes. La luz permanece localizada en la cabeza, sin cruz en forma de puntos ni resplandor alrededor del héroe o del cuerpo entero.
    - **Mecánica «Mirada colimada» (en prueba 2026-11-14 en `feat/ojo-tribunal`; sustituye al cono con cuenta compartida, que se descarta por complejo y poco legible; recupera el ritmo del francotirador anterior de §6.9.1; cifras `[TUNABLE-PLACEHOLDER]`):** sin efectos mientras busca; al fichar al héroe se para, la mirada se colima desde el farol y, al cerrarse, la cabeza de la mano dispara por la boca. Se esquiva saliendo de la línea a tiempo.
      1. *Buscar (andar):* camina despacio (velocidad 110, ≈ un tercio del héroe) **oscilando la cabeza/mirada** (~0,5 s por paso) a izquierda y derecha. **El farol no emite luz** ni hay nada en el suelo: solo el giro del cuerpo dice que busca. Vida 300 (dos tiros de francotirador). Peso en la horda 25 %, como el tirador.
      2. *Fichar y seguir (~40 frames):* al ver al héroe a menos de ~140 px de suelo, se para y nace del **farol** una **mirada verde ancha, difusa y tramada** hacia el pecho del héroe, que lo **sigue** mientras se estrecha (colimado A1 de §4.9 en la rampa verde del Ojo). A la vez carga la boca de la cabeza en la mano (arriba).
      3. *Fijar (~20 frames):* la línea queda **fija** donde estaba el héroe y termina de cerrarse hasta 1 px. En los últimos ~10 frames **parpadea** (aviso de «dispara ya»). Es la ventana para salir de la línea.
      4. *Sentencia:* al cerrarse, la mirada se apaga en el mismo frame y la cabeza dispara por la **boca** a lo largo de la línea fijada; 1 golpe si el héroe está en ella (respeta los i-frames). **Aviso y golpe se distinguen por forma y brillo, no solo por tono (decidido 2026-11-14):** la mirada es tramada y en verde frío apagado; el disparo es **sólido, grueso (3-5 px) y lo más brillante de la pantalla durante 2-3 frames**, en **hielo espectral** (azul pálido frío y apagado; elegido 2026-11-14 frente a ámbar, que se confundía con el fuego sagrado del héroe, y violeta, que perdía contraste; mockup `walkthroughs/ojo-tribunal/assets/mockup_color_disparo.png`), con fogonazo en la boca e impacto en el pecho del mismo color. Lenguaje visual: **verde = te apuntan, hielo = te disparan**. **Llamarada espectral (decidido 2026-11-14):** el disparo no es un láser recto y limpio ni un zigzag; es un **núcleo recto** (la línea exacta del daño, para que esquivar sea justo) con **bordes de llama irregulares y vivos** (la anchura varía a lo largo del rayo y frame a frame, con lenguas que escapan a los lados) y **volutas** de hielo que se desprenden y suben (heredadas del Maleficio original). Fogonazo grande en la boca mientras dura. Duración ~0,5 s: **golpe** 3 frames (máximo grosor y brillo), **llamarada** ~20 frames (ancha, bordes ardiendo) y **disipación** ~8 frames (se estrecha, se rompe en tramos y deja volutas). **Hace daño durante golpe y llamarada** (no en la disipación): el rayo es un muro temporal que corta el paso; como mucho 1 golpe gracias a los i-frames. Sigue la regla de efectos desaturados (sin blanco ni verde puros). Muros y columnas cortan tanto la mirada como el haz, así que esconderse tras una columna también salva. Matarlo o empujarlo con la escopeta antes del disparo lo anula.
      5. *Enfriamiento* ~90 frames y vuelve a buscar.
      - Tope de 2 Ojos apuntando a la vez (legibilidad); el resto se acerca o espera.
      - Animaciones: andar, mirar (quieto, linterna adelantada, en bucle) y sentenciar (gesto corto de 4-6 frames al soltar el haz).
- **Élites, se prueban dos** (sueltan cofre):
  - **El Abanderado:** empalado en el asta de su propio estandarte, hecho con tabardos cosidos de caídos. Los enemigos cercanos se aceleran. El asta lo hace el más alto de la pantalla. *(Concepto original; la versión que se programa es la de abajo, «El Abanderado (jefe, versión mínima)», que lo sustituye.)*
  - **El Campanero de Ánimas:** se arrancó la lengua para hacerla badajo de su campana, a cambio de que los muertos le oigan; boca vacía y cosida. Arrastra la campana rajada; al tocarla brotan Exvotos en un círculo de cera en el suelo (elipse 2:1, §4.9). El toque es la telegrafía.
- **Jefe: El Paso.** Paso de Semana Santa con costaleros muertos fusionados a las vigas; arriba, una Dolorosa viva con siete puñales que disparan rayos verdes que siguen al jugador. Embiste en línea; al matar costaleros cojea, se inclina y se ralentiza. Probablemente se trate como bloque rígido con costaleros sencillos, no como un modelo rigeado entero (decidir en su sesión).
- **Objetos en el cuerpo:** Tripo rigea y anima el cuerpo pero no gestiona objetos aparte. La cruz del Cireneo y el asta del Abanderado se modelan aparte y se pegan al hueso de la espalda en el lab de armas (hoy solo pega a las manos; falta comprobarlo). La campana va en la mano, como un arma.
- **El Abanderado (jefe, versión mínima) (decidido 2026-11-14, rama `feat/abanderado-jefe`).** Jefe sencillo que **no ataca**: es un invocador. Sustituye al concepto de élite de arriba (sin aura de aceleración, sin clavar el asta, sin parar la marea y sin cura al morir).
  - **Aspecto:** el estandarte va **en la mano, como bastón** (no atravesando el cuerpo). Tamaño: ~54 px en celda de 60×60 («Tamaño del Abanderado»), exportado con el preset de legibilidad C2.
  - **Aparición:** cada **2 minutos**. La primera a los 2:00 de partida; el siguiente reloj de 2 minutos empieza cuando muere el anterior, así que nunca hay dos a la vez.
  - **Vida:** aguanta unos **8 disparos cargados**. Barra de vida **sencilla flotando sobre el enemigo**, con colores que encajen con la paleta (rojo y negro de los personajes, §6.10). La presentación definitiva de los jefes está sin decidir.
  - **Patrulla:** anda despacio y **cabizbajo**, apoyado en el estandarte como bastón (clip «Sad Walk» de Mixamo), entre puntos al azar **dentro de la banda visible alrededor de la cámara** (si el avance o la marea lo dejan atrás, avanza hacia arriba hasta reentrar en pantalla).
  - **Te ve:** si estás a menos de ~1 pantalla y no hay pared en medio. Entonces se para, **levanta la cabeza, te mira e inclina el estandarte hacia ti** (no como una varita: el asta se inclina en tu dirección). Este gesto se genera por programa sobre el modelo (cabeza y brazo), sin clip de Mixamo. Si te alejas o te escondes unos 2 s, baja la cabeza y vuelve a patrullar.
  - **Invocar:** mientras te apunta, aparece un **charco color crema** en el suelo cada ~3 s, a medio camino entre él y tú. De cada charco salen **2 Exvotos monaguillo**. Tope de 8 monaguillos vivos.
  - **Salir del charco:** el monaguillo emerge poco a poco del charco, como si este lo fuera soltando (~0,5 s); el charco se seca al terminar. Mientras emerge **es invulnerable**, no hace daño ni se mueve.
  - **Exvoto monaguillo:** variante nueva del Exvoto (modelo «monje zombi», `tripo_convert_9a55a12b`). Mismas reglas que el Exvoto: muere de un golpe, camina lento hacia ti en postura de rezar (animación de andar rezando del Exvoto) y hace daño por contacto.
  - **Al morir:** en esta versión mínima suelta una **cruz de curación** (el cofre entra en la 0.5). Los monaguillos que queden siguen vivos.
- **Pendiente:** si la quemadura del cuerpo crece con las mejoras (las auras L/G/E/H ya no compiten: cada una es el aspecto de una reliquia, §6.12.8); cifras, fases y telegrafías de élites y jefe; tamaño del paso en pantalla (sprites grandes o capa de fondo, `TECHNICAL.md`); si hay minijefe en la demo.
- **Corazón Abierto en el juego (decidido 2026-11-11/12, rama `feat/corazon-abierto`, `walkthroughs/corazon-abierto/`):**
  - **Animaciones:** modelo Tripo con rig Mixamo (archivos: `assets/MANIFEST.md` §2). **Andar:** un andar de Mixamo adaptado al modelo con la cadera en el sitio; se descartaron el andar del nigromante (el torso se retorcía) y uno renqueante (a 31 px no se distinguía).
  - **Carga y disparo (ajustado 2026-11-18, sesión 135):** un solo clip de 8 frames por dirección, el de disparo (f0 = brazos en cruz, f7 = derrumbado con los brazos delante). **Cargar** lo recorre **al revés** (f7 → f0) según el progreso de carga (`prog` 0..256 de §4.9), no según el tiempo, y se queda en f0 (cruz) desde `AIM_READY` hasta soltar. **Soltar** dispara en f0 y corta la animación de inmediato volviendo al andar/reposo sin atrapar al héroe en la recuperación si el jugador no toca la pantalla. **Cancelar** o soltar antes de armarse vuelve al andar al instante. **Volver a pulsar** en cualquier momento reinicia la carga desde cero (f7 → f0) al instante sin esperar ningún enfriamiento previo. Mientras carga, el personaje está parado. Se acepta el salto de la pose de andar a la encorvada al empezar a cargar.
  - **Origen:** el rayo (`muzzle`) sale del **centro del pecho** del frame que se muestra (hueso `Spine2` en el lab).
  - **Estilo «fuego sagrado»:** sin verde en el jugador (el verde es del láser enemigo). Rampa común: rojo sangre → naranja brasa → oro → blanco. Chispas de impacto del rayo: oro → naranja → ceniza.
  - **Efectos desaturados en todos los personajes (decidido 2026-11-14):** la misma regla que se aplicó al haz y al aura del héroe (paleta `FX_SH_*` de `source/weapons.c`: marfil cálido, oro viejo, ámbar, terracota, carmesí y sangre oscura, sin primarios puros) vale para los efectos de **todos los enemigos**, para que encajen en el mundo del juego. El verde enemigo pasa a una rampa apagada (hueso fosforescente, verdín, musgo, humo) con un brillo máximo similar al del héroe; nada de verde ni blanco puros. Se aplica primero al Ojo del Tribunal y después al resto de enemigos.
  - **Haz del francotirador (elegido 2026-11-12 entre tres variantes; capturas en `walkthroughs/corazon-abierto/assets/contacto_haz.png`): «fuego».** Banda tramada rojo sangre/naranja que se cierra a 1 px (el colimado A1 de §4.9 recoloreado) y suelta brasas por el borde (≤ 32). Listo: línea amarilla de 1 px. Disparo: núcleo blanco con amarillo y naranja por fuera, que deja brasas rojas al apagarse. Sustituye al colimado A/B/C del francotirador de §4.9; `SELECT` (solo depuración) solo cambia escopeta y granada.
  - **Aura de carga, en comparación (selector `Y`, solo depuración; la primera ronda K/F1/F3 se descartó, `contacto_aura.png`).** Reglas comunes: crecen con `prog`, flash de listo de 3 frames, límites fijos de segmentos/puntos, sin `float`, deterministas por LCG, y lo que queda detrás del cuerpo se pinta antes del sprite.
    - **L, llamas:** 6-8 lenguas cortas onduladas desde la elipse de los pies, amarillo en la base, naranja y rojo en la punta, con borde tramado; anillo 2:1 dorado en listo.
    - **G, resplandor (gloria):** 10-12 rayos rectos de 1 px desde el **pecho**, alternando largos y cortos, oro con la punta blanca; crecen de 4 a 14 px y giran despacio. Detrás del sprite, como un halo.
    - **E, corona de espinas:** elipse 2:1 de espinas en el suelo que se cierra hacia los pies, con gotas rojas. Pase de suelo. En la primera captura las espinas negras no se leen sobre el suelo oscuro.
    - **H, ceniza:** volutas de humo tramado y brasas que suben desde hombros y pecho; bocanada de chispas oro en listo. En la primera captura el humo se lee como motas sueltas.

- **SFX base del Corazón Abierto (decidido 2026-11-13, rama `feat/sfx-core`):**
  - **Catálogo (5 SFX, 16.384 Hz mono 8-bit PCM, ~23,1 KB en total):**
    1. `heart_charge` (400 ms): ignición creciente al pulsar para cargar; se corta de inmediato si se dispara, cancela o muere.
    2. `heart_fire` (280 ms): descarga de fuego sagrado al soltar en `AIM_READY`. Sin timbre en `AIM_READY` (silencio limpio al llegar a cruz).
    3. `enemy_hit` (95 ms): impacto seco en hueso/chispazo, con variación de pitch ±12% y cooldown de 2 frames.
    4. `enemy_death` (250 ms): combustión súbita al fragmentarse un enemigo, con cooldown de 3 frames.
    5. `player_hurt` (420 ms): golpe en coraza + quejido de penitente, prioridad máxima al recibir daño.
  - **Mezcla y espacialidad:** panning estéreo horizontal (16..112) según la posición X del evento respecto a la cámara. Música fuera de esta entrega.
- **BSO de combate en streaming (decidido 2026-11-13, rama `feat/bgm-loop`):**
  - **Tema base (`cathedral_battle_loop`, 21,6 s, 11.025 Hz mono 8-bit PCM en NitroFS):** corte de 12 compases sin letra en inglés ni drops bruscos (`Loop A` de tecno industrial + coro grave) en streaming continuo (`mmStreamOpen`, buffer 2 KB) al 42 % de amplitud para dejar espacio a los SFX en `soundbank.bin`.
  - **Reserva para jefes (`boss_climax_loop`, 28,8 s):** corte `Loop B` con subida y drop guardado en `assets/music/` para futuros jefes.

### 6.11 Bestiario / Códice (decidido 2026-11-14)
- **Lore:** los textos de las fichas siguen la biblia del mundo, `LORE.md` (fuente canónica de nombres, cronología y tono).
- **Acceso y visibilidad:** todas las fichas de la demo (5 en total) están visibles desde el principio, sin desbloqueo progresivo. Se entra desde el botón `CODICE` del menú inicial o de pausa y se vuelve con `B` o el botón táctil `Volver`.
- **Maquetación B minimalista:**
  - **Estética:** fondo negro (`#000000`) y borde gris muy fino (1 px) en ambas pantallas.
  - **Pantalla superior (256×192):** ilustración animada en grande (160×160 px, C2) del personaje en su acción característica con rotación en 8 direcciones (`LEFT`/`RIGHT`), centrada dentro del marco y cargada bajo demanda desde NitroFS (`nitrofiles/bestiary/*.bin`).
  - **Pantalla inferior (256×192):** ficha de texto a ancho completo (nombre sin etiquetas de rol arquetípico, 1 línea de comportamiento, párrafo breve de lore y cita) en fuente bitmap legible con soporte completo de español (tildes y `ñ`), más navegación minimalista (`< Ant`, `Volver`, `Sig >`), controlable con táctil, cruceta o `L`/`R`/`B`.
- **Fichas de la demo (5):**
  1. **El Corazón Abierto** — vista pasando de encorvado a brazos en cruz (`corazon_disparo`). *Comportamiento:* carga su fe en cruz y desata un haz que atraviesa filas. *Lore:* último capellán de la columna. Pidió un arma cuando faltó la pólvora y Dios le abrió el pecho; cada milagro le consume un poco más, pero la fe no le deja morir. *«No es mi corazón. Solo lo llevo.»*
  2. **El Exvoto** — caminando *in-place* con las manos en rezo (sin cirio, `exvoto_walk`). *Comportamiento:* avanza en masa sin descanso; cae al primer impacto. *Lore:* fieles que rezaron hasta volverse figuras de cera. Siguen en procesión con las manos en rezo; la cera no resiste la luz. *«Pidieron no estar solos. Les fue concedido.»*
  3. **El Cireneo** — caminando encorvado en bucle *in-place* con la cruz a la espalda (`cireneo_walk`). *Comportamiento:* se agacha antes de embestir en línea recta; no puede girar. *Lore:* desertó y pidió que le clavaran la cruz a la espalda para no volver a huir. Si choca contra una columna, queda crucificado contra la piedra. *«Ayudó a cargar una cruz. Ahora la cruz le carga a él.»*
  4. **El Ojo del Tribunal** — caminando mientras gira la cabeza-farol a izquierda y derecha buscando (1 barrido cada 2 ciclos de paso, 16 frames por dirección en `ojo_walk_bestiary`). *Comportamiento:* vigila con su farol, fija la línea de juicio y sentencia desde la boca. *Lore:* inquisidores que cambiaron sus ojos por una linterna del juicio. Su mirada verde te examina; cuando se queda quieta, ya ha dictado sentencia. *«La linterna no ve culpables. Los fabrica.»*
  5. **El Abanderado** — caminando cabizbajo apoyado en el estandarte como bastón, seguido por dos exvotos de jóvenes suplicantes (`abanderado_walk`, 8 frames por dirección). *Comportamiento:* patrulla con el asta; al divisarte te apunta e invoca exvotos de jóvenes suplicantes. *Lore:* juró que el estandarte jamás tocaría el suelo. Apoyado en él vaga reuniendo a los caídos; de los charcos que señala brotan exvotos de jóvenes suplicantes que aún marchan tras su bandera. *«Mientras el asta siga en pie, nadie se retira.»*

### 6.12 Sistema de mejoras del Corazón Abierto (decidido 2026-11-15)
Sesión de diseño de la v0.4 (§6.9.2). Sustituye la regla de §6.6 «mitad del arma, mitad del personaje» y la elección de clase: la demo tiene un solo personaje. Las cifras están en `[TUNABLE-PLACEHOLDER]` hasta la sesión de números.

#### 6.12.1 Filosofía
- **Pool abierto, espíritu *The Binding of Isaac*.** Todas las mejoras conviven en el mismo pool, sin ramas excluyentes. Elegir bien rompe la partida; elegir sin criterio te deja sin nada. Con poco contenido ya tiene que divertir, y añadir mejoras no debe empeorarlo.
- **Builds como en *League of Legends*.** Hay estadísticas que solo valen para unas builds, y la misma mejora vale oro en una partida y es basura en otra. Ejemplo: «carga más rápida» no le sirve de nada a quien juega a mantener el rayo cargado.
- **La build cero crece sumando; las demás, multiplicando.** La Ráfaga (§6.12.3) es fiable desde el primer minuto y tiene techo. Las demás necesitan juntar varias piezas: con una sola están peor que antes (valle) y con tres se disparan. **Cuanto más rota es una build, peores son sus piezas por separado y más hondo es su valle.**
- **Contrapartida solo cuando la mejora rompe una regla del personaje** (por ejemplo, moverse mientras carga). Las demás reliquias son ventaja pura o llevan un riesgo que depende de la habilidad.
- **La marea manda.** No es un survivors abierto: no se puede uno plantar. Todo lo que frena al héroe es un coste real porque la marea empuja desde abajo.

#### 6.12.2 Reglas comunes
**El rayo base (cambia el comportamiento actual):**
- **Atraviesa a quien mata y se detiene en el primero que sobrevive.** Con poco daño se queda en el primer enemigo duro; con mucho, limpia filas. Atravesar es la recompensa natural de subir el daño.
- **Muros y columnas cortan el rayo y la línea de apuntado**, con chispas en el punto de impacto, como el haz del Ojo del Tribunal (§6.10). Lore: es fuego que sale de la carne, y la piedra lo detiene. Las columnas dan cobertura a los dos lados.
- **Alcance base más corto que el actual,** para que haya que acercarse a la vanguardia. El alcance actual de la ROM pasa a ser ~75 % del máximo con mejoras.

**Dos tipos de daño:**
- **Daño del rayo:** solo el disparo.
- **Daño de fuego:** todo lo demás (quemadura, explosiones, aro, ondas, línea de apuntado).

**Un único estado en los enemigos, «Quemado».** Se acumula en capas. Cada capa hace daño de fuego por segundo y frena un poco al enemigo; seguir quemándolo renueva la duración. Hay un tope de capas. No existe un estado aparte de «ralentizado»: frenar va dentro de Quemado.

**Vocabulario de las mejoras.** Toda mejora, presente o futura, se construye con estas piezas. Así las sinergias salen solas y no se diseñan de dos en dos:
- **Momentos:** al cargar, mientras cargas, al disparar, al impactar, al matar, al recibir un golpe y al recoger una gema.
- **Toda muerte cuenta como muerte,** también las de explosiones, quemaduras o aros. Así, por ejemplo, Martirio alimenta a Sed de Ceniza sin programarlo aparte.
- **Todo fuego usa el daño de fuego, y todo rayo hereda los modificadores del rayo.**
- **Topes visibles** de capas de quemadura y de explosiones encadenadas, para que una partida rota no baje de 60 FPS en la DS.

**Texto de cada mejora:** icono, nombre y una línea que **empieza por el momento en que actúa** («Mientras cargas: …», «Al matar: …»). Es la lección de la v0.2 (§6.6) y lo que permite aprender las builds leyendo.

#### 6.12.3 Arquetipos
Son una guía de diseño para dar variedad, no ramas ni clases. El jugador no los ve nombrados: los descubre combinando.

| Arquetipo | Fantasía | Cómo mata | Piezas clave | Valle |
|---|---|---|---|---|
| **Ráfaga** (build cero) | La ametralladora: «pa, pa, pa», cada disparo limpia una fila | Daño del rayo y cadencia | Fervor, Prisa, Alcance, Sed de Ceniza, Lanza de Longinos | Ninguno. Es la opción segura cuando vas apurado; con ella se puede pasar el juego, pero tiene techo |
| **Vigilia** | Cargar y no soltar: barrer la pantalla con la línea (de lejos) y quemar lo que se acerca con el aro (de cerca) | Capas de Quemado | Llama Votiva, Aura de Cilicio, Paso de Procesión, Brasa, Rescoldo, Paso | Hondo. Sin el Don de Paso, Procesión va más lenta que la marea y hay que soltar; sin Brasa, la quemadura hace poco |
| **Mártir** | Kamikaze: vivir a 1-2 corazones a cambio de mucho daño y curarse jugándosela | Todo su daño crece con la vida perdida; se cura matando de cerca | Llaga Abierta, Corazón Flagelado, Viático, Paso | El más hondo. Llaga sola solo quita vida |
| **Puentes** | Mezclan arquetipos | — | Auto de Fe (rayo ↔ fuego), Martirio Contagioso (fuego para Vigilia y Mártir) | — |

#### 6.12.4 Ritmo de la partida
- **Cada subida de nivel ofrece 1 de 3 Dones.** ~15-20 niveles por partida, sin volver a tirar.
- **En los niveles 4, 8, 12 y 16 se ofrece 1 de 3 Reliquias** en lugar de Dones, en una pantalla distinta (marco dorado) que se note como el momento especial de la partida. Unas 4 reliquias por partida. Con la estructura de la Subida pasan a darse en el nivel 5 y al vencer a cada jefe (§6.13.5).
- **Ofertas con cabeza:** a partir de la segunda reliquia, al menos una de las tres opciones comparte arquetipo con alguna reliquia que ya tengas. No asegura la pieza que falta, solo que el camino sigue abierto; romper la partida sigue dependiendo de elegir bien y de algo de suerte.
- **Requisitos (decidido 2026-11-15):** una mejora solo se ofrece si ya tienes lo que la activa. Hoy: Brasa, Rescoldo, Auto de Fe y Martirio Contagioso necesitan una fuente de quemadura (Llama Votiva, Aura de Cilicio o Corazón Flagelado). La primera reliquia de fuego abre ese camino. Toda mejora futura declara su requisito.
- Una reliquia cogida sale del pool. Un Don al máximo deja de ofrecerse; si no queda ninguno, la oferta es curar 1 corazón.

#### 6.12.5 Dones (estadísticas apilables, 4 rangos)
| Don | Qué sube | Le sirve a | Le estorba o no le sirve a |
|---|---|---|---|
| **Fervor** | Daño del rayo | Ráfaga, Auto de Fe | Fuego puro (no lo usa) |
| **Prisa** | Velocidad de carga | Ráfaga | Vigilia (no suelta nunca: desperdiciado) |
| **Alcance** | Largo del rayo y de la línea de apuntado | Ráfaga, Vigilia de lejos | — |
| **Brasa** | Daño de fuego | Vigilia, Mártir (Flagelado), Martirio | Ráfaga pura (no lo usa) |
| **Rescoldo** | Duración y tope de capas de Quemado | Vigilia | Ráfaga pura (no lo usa) |
| **Paso** | Velocidad de movimiento (también con Procesión) | Vigilia, Mártir | — |
| **Vida** | +1 corazón de tope y cura 1 | Cualquiera que vaya apurado | Mártir (le resta daño con Llaga) |

#### 6.12.6 Reliquias (10, una vez por partida)
| Reliquia | Línea de efecto | Arquetipo | Cómo se ve | Contrapartida |
|---|---|---|---|---|
| **Sed de Ceniza** | Al disparar: cada enemigo que matas acelera la siguiente carga; si no matas a nadie, va más lenta | Ráfaga | Aura H, ceniza, al cargar | Su propio riesgo |
| **Lanza de Longinos** | Siempre: el rayo atraviesa a todos los enemigos, mueran o no | Todas | Sin efecto propio: se ve en que el rayo atraviesa a todos (decidido 2026-11-15) | Ninguna |
| **Auto de Fe** | Al impactar: el rayo hace el doble a los quemados y consume sus capas | Puente rayo ↔ fuego | Láser: núcleo del disparo en hoguera; los quemados estallan en chispas al recibirlo | Ninguna |
| **Llama Votiva** | Mientras cargas: la línea de apuntado aplica capas de Quemado a lo que toca | Vigilia de lejos | Láser: la línea de apuntado arde en llamas | Ninguna |
| **Aura de Cilicio** | Mientras cargas: un aro de brasas a tus pies quema a quien entra; crece con la carga | Vigilia de cerca | Aura E, corona de espinas, en el suelo | Ninguna |
| **Paso de Procesión** | Mientras cargas: puedes andar despacio | Vigilia | Cuerpo: anda en cruz mientras carga | Carga más lenta (rompe una regla) |
| **Martirio Contagioso** | Al matar a un quemado: explota con daño de fuego y aplica Quemado alrededor | Puente de fuego | En los enemigos: explosiones | Ninguna; tope de cadena |
| **Corazón Flagelado** | Al recibir un golpe: onda de fuego alrededor y siguiente disparo cargado al instante | Mártir | Onda de fuego al recibir el golpe; aura L, llamas, mientras espera el disparo instantáneo | Ninguna |
| **Llaga Abierta** | Al cogerla: tu vida máxima baja a la mitad. Siempre: todo tu daño sube por cada corazón por debajo de 5 | Mártir | Láser: el rayo enrojece cuanta menos vida te queda; el pecho gotea sangre | Pierdes vida máxima |
| **Viático** (concepto cambiado 2026-11-15: robo de vida) | Al matar con el rayo: probabilidad de robar 1 corazón al enemigo, el doble si estaba pegado a ti | Mártir | Sifón: la vida del enemigo viaja hasta el pecho del héroe (ronda A/B/C); aura G, gloria, al cargar | Ninguna |

**Detalles:**
- **Llama Votiva** quema solo donde apuntas en ese momento; no deja rastro en el suelo (opción A, elegida por coste y rendimiento). El rastro persistente es Tierra Quemada, en reserva.
- **Aura de Cilicio:** el aro a carga completa es su tamaño máximo. Sin Procesión, mantenerlo te deja clavado y la marea te obliga a soltar; con Procesión avanzas con el aro al máximo.
- **Paso de Procesión:** su velocidad base está **por debajo de la marea**; con rangos de Paso llega a igualarla. Para la Ráfaga, la carga lenta es un castigo; para la Vigilia, que no suelta, no cuesta nada.
- **Llaga Abierta:** el bonus de daño se cuenta **siempre respecto a los 5 corazones de partida**, no respecto al tope actual. Al cogerla (de 5 a 3) ya tienes el bonus de 2 corazones; a 1 corazón, el máximo. Subir Vida te protege pero te quita daño.
- **Martirio** solo explota con enemigos quemados, así que en una Ráfaga pura no hace nada.

**Reserva para la segunda tanda (sin código en la demo):** Ascua Impaciente (soltar antes de tiempo dispara un rayo corto), Óleo Sagrado (cada X gemas, disparo instantáneo), Pilar Consagrador (rayo ancho que empuja), Tierra Quemada (la línea deja brasas persistentes; parches con tope, dibujados como las gemas) y Reflejo de Penitencia (el rayo rebota 1 vez en los muros). Descartado: Botafumeiro (incensario que gira), redundante con el Aura de Cilicio.

#### 6.12.7 Ejemplos de builds
- **Ráfaga limpia:** Fervor, Prisa y Alcance en casi todos los niveles; reliquias Sed de Ceniza y Lanza de Longinos. Cada disparo mata a una fila y la siguiente carga llega casi al instante. Fuerte desde el principio y estable, pero sin explosiones ni cadenas: es la que te lleva al final, no la que lo rompe.
- **Ametralladora en cadena (Ráfaga con fuego):** Sed de Ceniza, Llama Votiva, Martirio y Auto de Fe. Una carga corta marca con la línea, el disparo remata doble a los quemados, los muertos explotan y contagian, y cada muerte acelera la siguiente carga. Valle: hasta tener Llama Votiva, Martirio no hace nada.
- **Procesión de fuego (Vigilia):** Llama Votiva, Aura de Cilicio y Paso de Procesión, con Dones de Brasa, Rescoldo y Paso. Avanzas con los brazos en cruz arrastrando la línea por la horda y con el aro al máximo; ya casi no disparas. Valle: entre coger Procesión y juntar 2 rangos de Paso, la marea te come y la carga lenta estorba.
- **Hoguera (Vigilia de cerca con Martirio):** Aura de Cilicio, Martirio, Paso de Procesión y Brasa. Te metes en la masa con el aro a tope; los quemados revientan pegados a ti y contagian a los de detrás.
- **Penitente kamikaze (Mártir):** Llaga Abierta, Corazón Flagelado y Viático, con Dones de Paso y Brasa. Vives a 1-2 corazones con el daño al máximo. Cada golpe que recibes suelta una onda y un disparo instantáneo, y robas vida al matar, más aún de cerca. Con Aura de Cilicio, el aro hace las muertes cercanas por ti. Valle: Llaga sola solo te deja con 3 corazones.
- **Partida sin criterio (el contraejemplo):** Llama Votiva, Sed de Ceniza y tres rangos de Prisa. La línea quema medio segundo porque cargas rapidísimo, y Sed te castiga cada vez que barres sin matar. Las piezas se anulan entre sí.

#### 6.12.8 Presentación
- **Cada reliquia se ve donde actúa (decidido 2026-11-15):** los efectos pegados a personajes respetan la oclusión con sus cuerpos, como las auras. no todas son auras. Unas son auras del cuerpo, otras cambian el láser o la línea de apuntado, y otras se ven en los enemigos o en el movimiento (columna «Cómo se ve» de §6.12.6). Las cuatro auras de carga en comparación (§6.10, selector `Y` de depuración) dejan de competir: E → Cilicio, H → Sed de Ceniza, G → Viático y L → Corazón Flagelado, y se apilan según lo que lleves. Sin reliquias, la carga muestra solo el rayo. Cada aura tiene un coste fijo por frame: con 3 o 4 apiladas se mide en la DS y, si se pasa, se dibujan las dos últimas cogidas.
- **Enemigos quemados:** brasas procedurales sobre el cuerpo con el sistema de chispas del rayo (más capas, más brasas subiendo) y una lengua de fuego sobre la cabeza al tope de capas. Tope global de partículas. Descartados: sprites requemados (doblan el arte y la memoria y no muestran las capas) y teñir el sprite (encarece el paso de dibujo que hoy más pesa).
- **Fuego en el suelo:** en la demo solo hay efectos breves en el pase de suelo: el aro del Cilicio y un anillo corto por cada explosión de Martirio. Nada persistente.
- **Pantalla de elección (decidido 2026-11-15):** estilo Códice (§6.11: fondo negro, borde gris fino). Sobre el juego pausado y oscurecido aparecen **3 cartas en paralelo** en primer plano en la pantalla inferior; la seleccionada se ilumina (borde y brillo) y se adelanta un poco. Cada carta lleva su nombre y un **arte que es una vista previa del efecto tal como se ve en el juego** (decidido 2026-11-15, opción A): una escena de la propia ROM (héroe, efecto y los enemigos que hagan falta, sobre fondo oscuro) capturada en bucle y ampliada 2×, enmarcada al estilo Códice. Se descarta pintar el efecto aparte sobre el retrato del Códice (primer horneado: el efecto quedaba pobre frente al del juego). El efecto completo de la carta seleccionada se lee en una franja de texto. Las reliquias llevan marco dorado. El arte se genera fuera de la ROM a partir de esas capturas y se carga bajo demanda desde NitroFS; se regenera cuando cambie un efecto.
- **Gemas y HUD de nivel:** se quedan como la variante A, provisionales; irán prerrenderizados en 3D como los corazones del HUD (decidido 2026-11-15).
- **Ronda A/B/C (decidido 2026-11-15):** cuando todo funcione, cada elemento visual nuevo (pantalla y cartas, arte de cartas, gemas, HUD de nivel, enemigo quemado, línea de Llama Votiva, explosión de Martirio, onda de Flagelado y auras nuevas) se presenta en un walkthrough con tres variantes sacadas de la ROM, con `SELECT` como selector de depuración en vivo, y el usuario elige.

#### 6.12.9 Pendiente (siguiente paso de la sesión de diseño)
- Cifras de partida: alcance base y máximo, tiempos de carga, daño del rayo y del fuego frente a la vida de exvoto, cireneo y ojo, valor por rango de cada Don, capas y duración de Quemado, bonus de Llaga y N de Viático.
- Curva de experiencia (~15-20 niveles en ~8 min) y valor de las gemas por enemigo.
- Si las curas que caen en la v0.3 conviven con el Don de Vida y con Viático o se ajustan.
- Aspecto definitivo de los cambios del láser (Auto de Fe, Llama Votiva y Llaga), en la ronda A/B/C.

#### 6.12.10 Cifras de la primera versión (provisionales, 2026-11-15)
Todas son `[TUNABLE-PLACEHOLDER]`. Se fijaron a ojo partiendo de las cifras vigentes para montar la primera versión completa, y se ajustan con la lista que salga de la partida de prueba en la DS. Frames a 60 FPS; distancias en píxeles de suelo; vida en la escala 100 = 1,0 (exvoto 100, cireneo y ojo 300, abanderado 1200).

**Rayo base:** daño 150 (sin cambios). Carga 24 frames. Recuperación tras disparar 40 frames. **Alcance 160** (antes 320; 240 en la primera versión, demasiado largo según el usuario, 2026-11-15).

**Dones (4 rangos cada uno):**
| Don | Por rango | Al máximo |
|---|---|---|
| Fervor | +25 % daño del rayo | 300: mata cireneo y ojo de un disparo |
| Prisa | −4 frames de carga y −6 de recuperación | carga 8, recuperación 16 |
| Alcance | +64 de alcance del rayo y de la línea | 416 (el 320 de antes es ~77 %) |
| Brasa | +25 % daño de fuego | ×2 |
| Rescoldo | +1 capa de tope y +30 frames de duración | 9 capas, 240 frames |
| Paso | +12 % velocidad (también con Procesión) | +48 % |
| Vida | +1 corazón de tope y cura 1 | 9 corazones |

**Quemado:** tope base 5 capas; duración base 120 frames, que se renueva al volver a aplicar. Cada 15 frames hace 3 de daño de fuego por capa (12 por capa y segundo). Frena un 10 % por capa, hasta un 50 %. Las muertes por fuego no congelan la imagen (sin *hitstop*).

**Reliquias:**
- **Sed de Ceniza:** cada muerte del disparo resta un 15 % a la siguiente carga (hasta −60 %); un disparo sin muertes suma un 30 %.
- **Lanza de Longinos:** el rayo atraviesa a todos.
- **Auto de Fe:** el rayo hace ×2 a los enemigos con al menos 1 capa y les quita todas.
- **Llama Votiva:** la línea aplica 1 capa cada 8 frames de contacto.
- **Aura de Cilicio:** radio de 12 + 28 × carga (de 12 a 40); 1 capa cada 10 frames a quien esté dentro.
- **Paso de Procesión:** andar al 35 % de la velocidad mientras cargas; la carga dura un 50 % más.
- **Martirio Contagioso:** al morir quemado, explosión de radio 32 con 60 de daño de fuego y 2 capas a los que alcanza. Tope de 4 explosiones por frame (las demás esperan al siguiente).
- **Corazón Flagelado:** al recibir un golpe, onda de radio 48 con 100 de daño de fuego y 3 capas; la siguiente carga llega lista al instante.
- **Llaga Abierta:** vida máxima a la mitad, redondeando hacia arriba (5 → 3). Todo el daño (rayo y fuego) +20 % por cada corazón por debajo de 5.
- **Viático:** cada muerte por el rayo tiene un 8 % de probabilidad de robar 1 corazón (16 % si el enemigo estaba a menos de 40 del héroe), sin pasar del tope.

**Gemas y experiencia:**
- Valor de las gemas: exvoto y monaguillo 1; cireneo y ojo 3; abanderado 15.
- Imán de radio 24; se recogen a 10. Las que se traga la marea se pierden. Tope de 48 gemas en el suelo; si se llena, la experiencia se suma directamente.
- Experiencia para pasar del nivel n al n+1: 5 + 3·(n−1). Eso da ~440 de experiencia para el nivel 17.
- Reliquias en los niveles 4, 8, 12 y 16. Las curas de la v0.3 se mantienen (1 de cada 12 muertes).

**Depuración (solo para la prueba):** `X` sube de nivel al instante. `Y` deja de cambiar el aura: las auras salen de las reliquias.

#### 6.12.11 Elecciones de la ronda A/B/C (2026-11-15, primera vuelta)
- **Enemigo quemado:** A (brasas y lenguas, potenciada) o B (corona de llamas a los pies), por decidir entre las dos, **más un tinte en el propio sprite** del enemigo (oscurecido o enrojecido según las capas). Se acepta el coste del tinte en el dibujo de los enemigos quemados, pero se mide en la DS.
- **Llama Votiva:** mezcla de A y C: chispas alrededor de la línea que giran de forma irregular y procedural (como manchas solares), no una hélice perfecta.
- **Corazón Flagelado:** A (anillo grande).
- **Martirio Contagioso:** A, con el mismo lenguaje visual que Flagelado, por consonancia.
- **Auto de Fe:** A, pero las tres variantes se parecían demasiado: hay que hacerla más distinta de un impacto normal.
- **Llaga Abierta:** ninguna convence; nueva ronda con otras ideas.
- **Viático:** cambia de concepto: de curarse por muertes cercanas a **robar vida al disparar**, con un sifón visible de la víctima al héroe (tabla de §6.12.6).

#### 6.12.12 Elecciones de la ronda A/B/C (2026-11-15, segunda vuelta)
- **Enemigo quemado:** se descarta C. Siguen A y B. El tinte del sprite indica las capas: claro con 1 capa y más rojo con cada capa. El tinte actual es el tope, al que se llega con 3-4 capas.
- **Llama Votiva:** B (chispas sueltas que giran de forma irregular). Se seguirá afinando más adelante.
- **Auto de Fe:** A, chispas minimalistas en el punto de impacto. B y C no son un efecto aparte: **animan el propio estado de quemado al consumirse**. Las llamas del quemado se avivan, envuelven al enemigo y se evaporan hacia arriba mientras el tinte vuelve a la normalidad (B parte del quemado A; C, del B). Todo efecto tiene que nacer del mundo (del suelo, del cuerpo o del punto de impacto), nunca flotar como un icono.
- **Llaga Abierta:** se descarta A (se confunde con los efectos de fuego que se expanden). B pasa a ser **sangre que gotea** (con poca vida gotea poco y al límite mucho más) **y aspecto de ascendido**, no rojo: es un poder, no un castigo, y el rojo se confunde con el quemado. C (borde rojo que late) se mantiene como opción.
- **Viático:** A (hilo de sangre) o C (alma pálida). Al robar vida, la víctima no desaparece en el acto: se queda **inerte y suspendida unos 0,3 s** (ni ataca ni bloquea, ya cuenta como muerta para experiencia y gemas) mientras se le extrae el hilo o el alma, y luego muere con su animación normal. Propuesta del coordinador, a validar con el GIF.

#### 6.12.13 Elecciones de la ronda A/B/C (2026-11-15, tercera vuelta)
- **Enemigo quemado:** A y B gustan las dos; se decide más adelante jugando.
- **Auto de Fe:** A (chispas al impactar) y C (la corona de llamas sube y se evapora) gustan; se descarta B.
- **Llaga Abierta:** B. El aura de ascendido crece con la sangre: cuantos menos corazones, más gotea y más intenso es el brillo pálido dorado.
- **Viático:** A (hilo de sangre); C (alma pálida) se conserva como alternativa.

#### 6.12.14 Pendiente: efectos de sonido (sesión aparte)
El sistema de mejoras no tiene sonido propio todavía. Faltan, como mínimo:
- subir de nivel (se abre la pantalla de cartas);
- mover la selección y elegir carta (Don y Reliquia, esta más solemne);
- recoger gema (por valor: 1, 3 y 15) y el imán;
- enemigo empezando a arder y tic de quemadura (muy discreto, con enfriamiento);
- explosión de Martirio Contagioso;
- onda de Corazón Flagelado;
- Auto de Fe al consumir la quemadura;
- Llama Votiva (línea ardiendo mientras se carga, en bucle);
- Aura de Cilicio (aro ardiendo mientras se carga, en bucle);
- robo de vida de Viático (sifón y cura);
- Llaga Abierta (latido o goteo según la vida que falte).
Se generan con el flujo de `AGENTS.md` (ElevenLabs CLI) en su propia sesión.

#### 6.12.15 Estado y siguiente paso (2026-11-16)
- **Hecho:** primera versión jugable completa del sistema (gemas, nivel, cartas, 7 Dones, 10 Reliquias, quemado, requisitos de oferta) y la ronda A/B/C de efectos.
- **Pendiente de validar:** si es divertido. Se hará con el plan de pruebas de `walkthroughs/mejoras-v04/plan_pruebas.md` (Ráfaga, Vigilia, Mártir, sin criterio y techo con trucos, con puntos de control de tensión, poder y decisión) y una entrevista de ajustes posterior. Las cifras de §6.12.10 siguen siendo provisionales hasta entonces.
- **Mientras tanto:** se arreglan los problemas básicos que el usuario detecta jugando, uno a uno, sin tocar el equilibrio.


### 6.13 Estructura de la partida: la Subida (decidido 2026-11-16, rama `docs/estructura-partida`)
Sustituye al nivel infinito de la 0.3 y concreta §6.1 y la 0.6 (§6.9.4). Motivo: la catedral infinita no tiene intención (el compositor alterna piezas al azar y nada anuncia lo que viene) y es difícil de hacer bien. Una partida con principio, mitad y final se entiende, se recuerda y encaja con el lore (`LORE.md`: la Columna intentó llegar al Altar y cayó por el camino; Elías hace el mismo recorrido).

- **Duración objetivo: 15–18 min** hasta ganar al jefe final (antes ~8). Referencias: Isaac hasta Mom, 20–30 min en pisos de 3–5 min; Vampire Survivors y Halls of Torment, 30 min. Se queda por debajo porque es una portátil sin guardado a mitad de partida. Si se queda corta en la DS, se alarga cada acto sin cambiar el esqueleto.
- **Columna vertebral: un Vía Crucis de 14 estaciones.** Cada estación es un hito visible en el muro con su número romano (la pieza exacta se decide en la sesión del escenario). El jugador sabe dónde está y cuánto le falta sin barra de progreso. Las estaciones son también los sitios donde pasan cosas (crucero, capilla, élite, jefe).

| Tramo | Estaciones | Tiempo | Final del tramo |
| :--- | :--- | :--- | :--- |
| **Pórtico** | — | ~0:30 | Entrada tranquila, último campamento de la Columna. Empieza la marea. |
| **Acto I: la nave** | I–IV | ~5 min | **Jefe 1: El Abanderado** en la estación V. |
| **Acto II: el coro** | VI–IX | ~5 min | **Jefe 2: El Campanero de Ánimas** en la estación X. |
| **Acto III: el Calvario** | XI–XIII | ~5 min | **Jefe final: El Paso** en la estación XIV (el altar). Victoria. |

- **Cada acto es como un piso de Isaac:** subida con horda y marea → encuentro con el jefe → respiro y recompensa → el siguiente acto empieza con otro ambiente, más profanado que el anterior (estados de profanación de §6.9.1b).
- **Los enemigos entran por actos:** acto I, Exvotos, y el Cireneo a mitad del acto (la estación V del Vía Crucis es la del Cireneo); acto II, se suma el Ojo del Tribunal; acto III, todos.
- **Cada jefe vuelve después como enemigo normal (élite):** el Abanderado en los actos II y III; el Campanero en el acto III. El jugador reconoce al que ya venció y la partida tiene memoria. Su versión élite es más débil que la de jefe; las cifras se deciden en la sesión de cada jefe.
- **El escenario se ordena por actos:** tramos hechos a mano para cada acto, en orden fijo y reconocible entre partidas; el azar solo elige variantes dentro de cada tramo. Sustituye al compositor infinito de la catedral (§6.9.1b) cuando se implemente. «La catedral que no termina» queda como lore (el altar se aleja), no como mapa infinito.
- **Morir** reinicia la partida desde el pórtico, como hoy.

#### 6.13.1 Encuentros con jefe
- **En el mismo pasillo, no en una sala aparte.** Al llegar a la estación del jefe:
  1. **Presentación:** pantalla de intro del jefe con un zoom sobre él y su nombre (presentación concreta en su propia ronda A/B/C).
  2. **Sala cerrada:** el jugador no puede avanzar ni retroceder fuera de la sala del jefe hasta que gane o muera. La cámara no se fija: sigue al héroe (§6.13.7, corregido 2026-11-17).
  3. **Se para todo lo demás:** la marea se detiene y deja de aparecer la horda aleatoria.
- **Encuentro coreografiado (por defecto):** el jefe llega con una escolta definida que se renueva desde arriba según la vas matando; por ejemplo, el Abanderado con varios Ojos y algún Cireneo. Qué escolta lleva cada jefe y a qué ritmo vuelve se decide en su sesión.
- **Alternativa por jefe: el jefe solo,** reforzado para que sea interesante sin escolta. Se elige una u otra en la sesión de cada jefe.
- **Al ganar:** el jefe da una reliquia (§6.13.5), se desbloquea la pantalla y, tras un respiro, la marea vuelve a subir en el acto siguiente.
- **El Abanderado actual** (§6.10, aparición cada 2 min) se mantiene como está hasta que se implemente esta estructura; entonces pasa a ser el jefe fijo de la estación V y su invocación de monaguillos es la base de su encuentro.

#### 6.13.2 El Campanero de Ánimas (jefe del acto II, dirección inicial)
- **Poder (dirección del usuario, detalle por decidir):** refuerza a los enemigos que tiene alrededor: más fuertes o invulnerables mientras dura el efecto. El toque de campana es la telegrafía (concepto de §6.10). El combate pide romper su protección o separar a los enemigos de él antes de atacarlos.
- Lore y ficha del Códice: pendientes (`LORE.md` §9, «Enemigos nuevos»).

#### 6.13.3 Al ganar la partida
- Tras vencer a El Paso aparecen **unas escaleras que bajan a las criptas**: el siguiente nivel. Encaja con `LORE.md` §5 («se puede salir, por abajo»; la Marea como lo que la Iglesia enterró sin nombre).
- **La partida sigue (decidido 2026-11-16):** al bajar las escaleras se continúa en las criptas sin cortar la partida, con el mismo personaje y sus mejoras, como Isaac tras Mom. No hay desbloqueo ni guardado en la consola (§6.3). Ganar a El Paso es la victoria de la catedral; las criptas son contenido extra para quien llega.
- **Pendiente:** qué hay en las criptas (estructura, enemigos y jefe), si tienen final propio y qué pasa mientras no existan (por ahora, pantalla de victoria al vencer a El Paso).

#### 6.13.4 Pendiente
1. Poder exacto del Campanero y escolta de cada jefe.
2. Pieza visual de las estaciones y aspecto de cada acto (sesión del escenario).
3. Qué es el Altar y qué encuentra Elías al llegar (`LORE.md` §9).

#### 6.13.5 Ritmo de mejoras en la Subida (decidido 2026-11-16)
Sustituye al reparto de reliquias por nivel de §6.12.4 cuando se implemente la estructura; hasta entonces la ROM sigue con los niveles 4, 8, 12 y 16.
- **4 reliquias por partida, como ahora,** para no tocar el equilibrio de §6.12:
  1. **Nivel 5:** la primera, antes del primer jefe, para que la construcción empiece a definirse en el acto I.
  2. **Jefe 1 (Abanderado), jefe 2 (Campanero) y jefe final (El Paso):** una al vencer a cada uno, con la misma pantalla de marco dorado de §6.12.4. La de El Paso llega para las criptas.
- **Cada jefe es un punto de inflexión de la build.** Las reglas de oferta de §6.12.4 (arquetipo compartido, requisitos, una reliquia cogida sale del pool) valen igual.
- **Dones:** siguen saliendo en cada subida de nivel. La experiencia se espacia para unos **25 niveles** en la partida completa (cifra `[TUNABLE-PLACEHOLDER]`, se ajusta jugando).
- Los cofres de élite (§6.9.3) quedan como posible fuente extra, por decidir.

#### 6.13.6 Escenario por actos: encuentros y pasillos (decidido 2026-11-16, rama `docs/escenario-actos`; en diseño)
Sustituye, cuando se implemente, al compositor v2 de la catedral (§6.9.1b), a la marea y la horda aleatoria como sistema general (§6.4) y a las gemas y la experiencia (§6.12.4, §6.13.5). Motivo: el apuntado manual y las coberturas piden enemigos colocados con intención (ADN de *twin-stick*: Enter the Gungeon, Isaac), y la marea castigaba justo lo que se quiere diseñar (pensar el encuentro, desviarse al relicario).

**Qué es juego y qué es lore.** El juego se describe con cinco palabras: partida, acto, encuentro, pasillo, pieza. Nave, coro y Calvario son el lore de cada acto y deciden qué piezas usa; el Vía Crucis y sus estaciones son ambientación y no marcan dónde pasan cosas (§6.13 queda así matizado). El pórtico son las primeras pantallas despejadas del acto I.

**Los actos (qué cuentan y cómo se nota).**
| Acto | Capítulo | Sitio | Piezas propias |
| :--- | :--- | :--- | :--- |
| I | La guerra: donde cayó la Columna | La nave | Las de hoy (columna, estatua, bancos, relicario, velas, lápidas) más sacos, banco volcado y roto, columna rota y **alambre de espino** (nueva: cierra el paso, deja pasar los disparos). Cadáveres de cruzado, más adelante. |
| II | El juicio: el Tribunal y los monaguillos | El coro | Por decidir (candidatas: sillería, rejas, faroles, atril). |
| III | La condena: las cruces de los penitentes | El Calvario | Por decidir (candidatas: cruces, cera derretida). |
- Cada acto está más profanado que el anterior y tiene su propio juego de piezas, que se carga durante el respiro tras el jefe (cada acto tiene su propio presupuesto de tiles).
- El jefe llega por distancia (al final del acto), no por tiempo.

**Estructura de un acto: encuentro, barrera, pasillo.**
- **Encuentro: 2 pantallas de alto** (384 px), diseñado a mano con piezas y enemigos colocados. Las dos pantallas de la DS forman parte del combate: lo de arriba no es «lo que viene», también te dispara.
- **La cámara sigue siempre al héroe** (se apunta en la pantalla de abajo); no hay cámara fija, tampoco en el jefe (§6.13.7).
- **Barrera en el borde de arriba del encuentro** (en el acto I, alambre o sacos; en el II, la reja del coro): no se abre hasta matar a todos.
- **Pasillo de ~2 pantallas** detrás de la barrera: colchón para que, estando arriba del encuentro, la pantalla superior no enseñe el siguiente. Al subir por él asoma la parte baja del siguiente encuentro con sus enemigos dormidos (aviso, no revelación).
- **Un encuentro despierta al cruzar su borde de abajo.** Los enemigos despiertos te siguen a cualquier parte. Nada reaparece.
- **Antes de despertar, los enemigos del encuentro no reciben daño** (el rayo los atraviesa). Se vio con el bot (2026-11-17): disparar desde el pasillo a los Exvotos que rezan vaciaba el encuentro sin riesgo.
- **Catálogo:** 8–10 diseños por acto, encadenados al azar y espejados (izquierda ↔ derecha). Acto I: 10–12 encuentros, ~40–48 pantallas, objetivo 5–6 min divertidos de principio a fin. Cada diseño enseña o examina una cosa.
- **Reglas de oficio:** nunca hacer aparecer un enemigo encima del jugador; avisar de dónde sale cada uno; mezclar 1–2 que disparan con varios cuerpo a cuerpo; acto I con 3–6 enemigos por encuentro, subiendo poco a poco; nunca un hueco cerrado (siempre dos caminos hasta el héroe).
- **Sensación:** como el primer piso de Isaac, fácil si lo entiendes, mortal si vas a lo loco. Encuentros con bastantes enemigos que no vienen todos a la vez: unos esperan en su puesto, otros van a por ti, otros entran en una segunda oleada.

**Las piezas tienen papel de combate.**
- Columnas y estatuas paran los disparos de todos (rama `fix/cobertura-estatuas`). Te protegen del Ojo.
- Bancos y sacos paran cuerpos y cargas, no disparos. Los enemigos los rodean (campo de navegación), así que ordenan a la horda en hileras. Pendiente de comprobar: si el Cireneo queda aturdido al chocar con un banco como con un muro (si sí, el banco te protege del Cireneo).
- Bancos destructibles y agacharse con `L` tras bancos y sacos: mecánicas candidatas, no ahora.

**Relicario en cada pasillo: mejora continua y periódica.**
- Sin gemas ni experiencia. En cada pasillo, a un lado, hay un **relicario**: al romperlo a tiros da **elegir un Don**, un corazón o las dos cosas. Los relicarios decorativos al azar desaparecen.
- Un relicario por encuentro da unos 30 Dones por partida, del orden de los ~25 niveles de §6.13.5: las cifras de los Dones valen como están y se ajustan jugando.
- **Reliquias:** 4 por partida, como en §6.13.5. Al vencer a cada jefe, y la primera en un relicario de marco dorado a mitad del acto I (sustituye a la del nivel 5).

**Daño: varios disparos por enemigo.**
| Enemigo | Disparos con el rayo base (antes) |
| :--- | :--- |
| Exvoto y monaguillo | 2 (1) |
| Ojo | 3 (2) |
| Cireneo | 3 (2) |
| Abanderado (jefe) | ~20 (8) |
- **El rayo sigue solo con el daño que le sobra** al matar; si no mata, se para. Con el rayo base, poner a los enemigos en fila ayuda poco; con Fervor vuelve a barrer filas (el poder se gana). La Lanza de Longinos sigue atravesando a todos sin perder daño.
- Cifras exactas de vida: `[TUNABLE-PLACEHOLDER]` en la sesión de implementación (actualizar §6.12.10 y `tests/test_guardrails.py`).

**Enemigos por acto (corrige §6.13).** Acto I: Exvotos; el Cireneo desde el primer tercio; **el Ojo desde la segunda mitad** (sin él las columnas no sirven). Acto II: se suma el Abanderado como élite. Acto III: todos. La IA de hoy vale casi tal cual (el Exvoto ya duerme rezando, el Cireneo telegrafía su carga, el Ojo se cubre y solo dos apuntan a la vez). Falta: que el Ojo y el Cireneo esperen en su puesto, despertar el encuentro entero, segunda oleada por arriba y abrir la barrera.

**Tras la primera prueba en la DS (decidido 2026-11-17).** El prototipo resultó trivial: el jugador decidía cuándo empezaba la pelea y la empezaba fuera del alcance de los enemigos, con pocos a la vez y un Cireneo que se esquivaba con un paso. Se decide:
- **Todos los enemigos están en la sala desde el principio, como en Isaac,** y despiertan todos a la vez al cruzar el borde de abajo (también los que rezan). Los refuerzos desde arriba son un recurso ocasional, no la norma: no tiene sentido temático que salgan de la nada. Sustituye a la «segunda oleada por arriba» como regla general.
- **Más listos, no esponjas de balas.** La dificultad sale de la IA y de la colocación, no de subir la vida a secas. **El Exvoto esquiva el rayo:** si el héroe le está apuntando con el láser de carga, se aparta de la línea, y los de una fila se abren cada uno a un lado para romperla. No anda en línea recta hacia el héroe.
- **El Cireneo, perseguidor que embiste:** anda siempre hacia el héroe a buen paso; cuando lo tiene alineado carga muy rápido y con poco aviso; si choca con una columna, estatua, saco o alambre queda aturdido un buen rato (la recompensa por usar el escenario).
- **El Ojo** solo es difícil cuando hay más presión alrededor; subirle la vida no lo arregla. Su cambio se decide con el catálogo de salas.
- **Salas rediseñadas** en un catálogo revisado antes de tocar la ROM: cada planta plantea una sola pregunta y sus tres poblaciones (ligera, media y dura) son versiones más duras de esa misma pregunta.

**Ancho de la catedral: 256 px (una pantalla), sustituye a los 512 de §6.2.** Sin desplazamiento lateral: el encuentro entero se ve y todo el ancho queda al alcance del lápiz; el escenario cuesta la mitad de tiles. Muros de ~24 px por lado (suelo útil ~208 px), columnas pegadas al muro como pilastras. Corte orientativo: paso lateral ~24 + bancos 64 + pasillo central 32–48 + bancos 64 + paso lateral ~24. Pide rehacer el muro, el editor (hoy a 512) y la navegación y colisión de la ROM.

**Dificultad: planta y población por separado (como Isaac y Hades).**
- Cada diseño de encuentro es una **planta** (piezas y barrera) con **3 poblaciones**: ligera, media y dura (cuántos enemigos, de qué tipo y si hay segunda oleada).
- El acto pide los encuentros **por tramos**: el primer tercio en ligera, el segundo en media y el último en dura. El azar elige planta y espejo; la dificultad la marca la posición. Una planta no sale dos veces seguidas y como mucho dos veces por acto (en tramos distintos).
- En el acto I los tramos siguen la entrada de enemigos: ligera, solo Exvotos; media, se suman el Cireneo y algún Ojo suelto; dura, mezcla completa y segunda oleada.
- Cada acto empieza algo por encima de donde acabó el anterior, con su propio catálogo de plantas y sus enemigos nuevos. Último recurso si los Dones corren más que los encuentros: +25 % de vida enemiga por acto.
- Se equilibra jugando la vara de cada población, para que la curva de los encuentros vaya un poco por delante de la del jugador y el jefe sea el examen.

**Catálogo mínimo del acto I.**
| Planta | Piezas | Qué enseña |
| :--- | :--- | :--- |
| **La procesión** | Dos filas de bancos y pasillo central | Los bancos alinean a los Exvotos; cada uno pide dos disparos: retroceder disparando. |
| **El embudo** | Sacos que cierran el centro, un solo paso | Leer y esquivar la carga del Cireneo; estrellarlo contra algo. |
| **El balcón** | Dos columnas arriba (pantalla superior) | Mirar arriba y cubrirse del Ojo; en ligera, Exvotos rezando tras las columnas. |
| **La pinza** | Centro abierto, piezas en los laterales | Dos frentes a la vez; no meterse en medio. |
| **El claro** | Sin bancos, estatuas en las esquinas | Arena abierta para la multitud y las oleadas. |
| **La alambrada** | Alambre de espino que cruza la nave | Los enemigos rodean y tú disparas a través. |
- 6 plantas × 3 poblaciones = 18 encuentros (36 con espejo) para los 10–12 de una partida. Ideal a medio plazo: 8 plantas.
- Además: **pasillo** (con relicario a un lado, izquierda o derecha), **pasillo dorado** (el relicario de la primera reliquia), **inicio** (pantallas despejadas) y **pantalla del jefe** (Abanderado).
- Piezas: columna, estatua, banco, sacos, relicario, velas y lápidas (existen) más **alambre de espino** (nueva) y la **barrera que se abre** (sacos o alambre con comportamiento nuevo).
- **Provisionales (decidido 2026-11-16):** sacos, alambre y barrera van en el prototipo con un sustituto provisional (rectángulos de color apagado); el usuario hace sus modelos 3D. El muro de 256 también es provisional en el prototipo.
- **Piezas 3D de las salas (decidido 2026-11-17, rama `feat/props-catedral-v2`; sustituye a los provisionales).** Revisión en `walkthroughs/props-catedral-v2/`.
  - **Rastrillo (barrera):** reja de hierro negro que cae hasta el suelo; sustituye a la franja roja en el borde de arriba de cada sala y de la del jefe (también en el acto I: corrige «alambre o sacos» de arriba), con la base sobre la línea de la barrera. Dos piezas de 104 px cubren la nave de pared a pared (cada una son dos tramos del modelo) y se dibujan con **sprites hardware** (libera 182 tiles del kit). Ya está bajado al acercarse a la sala; al matar al último enemigo **sube despacio (~0,9 s, 1 px/frame)** recortándose contra su borde superior para no flotar sobre el pasillo, y abre el paso al terminar de subir. La barrera trasera y la de abajo del jefe siguen como hoy.
  - **Sacos:** las barricadas son tramos de 64 px pegados que salen de una pared y acaban en un **remate** en escalón con un saco caído (el remate derecho es el izquierdo en espejo). Los tramos alternan **recto** y **con hueco** (falta un saco y otro está ladeado). Tono de arpillera oscurecido en el render.
  - **Bancos:** el grupo de 4 bancos tiene una variante con el **banco roto** en la segunda fila; sustituye a uno de cada cuatro grupos de las salas, elegido por posición (estable).
  - **Relicario nuevo** (templete dorado sobre base baja) sustituye al antiguo en todo el juego.
  - **Columna rota:** en «el balcón», una de las dos columnas es la rota (mismo fuste que la entera, cascotes en la base).
  - **Alambre:** el modelo de alambre de espino ya revisado sustituye a los rectángulos de «la alambrada», escalado a mitad de altura (tramos de 32×24 px, el doble de tramos por línea).
  - **Kit gráfico solo para las salas:** el kit hornea únicamente las posiciones que usan las salas, los pasillos y las lápidas; las de la catedral infinita salen del kit (las variantes de prueba que aún la usan muestran menos piezas). Con el rastrillo en sprites y el alambre a mitad de tamaño, las lápidas vuelven a caber con margen dentro de las 1.024 tiles.
  - **Simetría izquierda/derecha:** toda pareja simétrica respecto al eje de la nave se coloca por el cuerpo del arte (`x_der = 208 - x_izq - ancho_cuerpo`) y hornea su fase exacta.

**Siguiente paso:** adaptar el editor a 256 y componer las 6 plantas con sus 3 poblaciones para revisarlas en el móvil; después, prototipo de 3–4 encuentros en la ROM frente a la versión de hoy.

#### 6.13.7 Modo jefe: lógica común (propuesta 2026-11-17, rama `feat/modo-jefe`; en diseño)
Concreta §6.13.1 para el escenario por actos (§6.13.6). Objetivo: que meter un jefe nuevo sea rellenar una ficha (nombre, retrato, vida, fases y escolta) y escribir su IA, sin tocar la intro, la barra, las fases ni la victoria. Se prueba con el Abanderado tal como está hoy; su combate como jefe se ajusta en otra sesión.

**Secuencia del encuentro.**
1. **Sala del jefe:** un bloque de 2 pantallas (384 px), como un encuentro, con su barrera arriba.
2. **Entrada:** al cruzar el borde de abajo se cierra una barrera también detrás del héroe y empieza la intro.
3. **Intro:** el juego se congela; presentación con el nombre del jefe (y su título del Códice). Se salta con `START`. Al terminar, entra la música de jefe (`boss_climax_loop`).
4. **Cámara libre (decidido 2026-11-17):** la cámara sigue al héroe como en el resto del acto; solo se dispara desde la pantalla de abajo, así que fijarla no tiene sentido. El héroe se mueve por toda la sala. Por encima de la barrera de arriba la sala se cierra con una **reja** y, al otro lado, algo decorativo (que no se pueda tocar), para que la pantalla de arriba no quede vacía cuando el héroe sube al borde.
5. **Combate por fases** (abajo).
6. **Victoria:** el jefe muere; desaparecen su escolta e invocaciones; secuencia de victoria; pantalla de reliquia (marco dorado, §6.13.5); vuelve la música normal y se abren las dos barreras.
7. **Morir** durante el jefe reinicia la partida, como en cualquier otro sitio.

**Fases.**
- Cada jefe declara de 1 a 3 fases con el umbral de vida en que empieza cada una (por ejemplo 100 %, 66 %, 33 %). La IA del jefe solo pregunta «¿en qué fase estoy?».
- **Cambio de fase común a todos:** el jefe queda invulnerable ~1 s, se muestra una telegrafía (la misma para todos los jefes) y se renueva su escolta según la fase. Los disparos durante ese segundo no cuentan.
- La escolta, si la hay, es una lista por fase: qué enemigos, cuántos a la vez y cada cuánto vuelve uno que cae. Con la lista vacía el jefe pelea solo (§6.13.1).

#### 6.13.8 Ejecuciones (remates / glory kills, 2026-11-18, rama `feat/remate`)
Mecánica de remate cuerpo a cuerpo para ritmo y recarga en combate:
- **Disparador:** un golpe que no mata y deja al enemigo a **≤ 50 % de su vida máxima** lo deja tambaleándose (`ENEMY_STATE_WOBBLE`) durante 180 frames (~3 s), quieto y con un pulso cálido de luz marfil/ocre (sin efectos neón, según §6.10). Con el rayo base (150 de daño), el Exvoto (250 HP) tambalea tras 1 disparo y el Cireneo (600 HP) tras 2 disparos.
- **Activación:** pulsar `L` a media/corta distancia (≤ 96 px de suelo) sobre el enemigo tambaleante más cercano, ejecutando la animación desde la dirección de entrada del héroe (8 ángulos).
- **Flujo:** el héroe queda invulnerable y bloqueado mientras transcurre la animación combinada (72 frames, ~1,2 s), la cámara acompaña suavemente hasta su posición final, y conserva 60 frames (~1 s) de invulnerabilidad con pulso marfil al terminar para reposicionarse. Al terminar, el enemigo muere de inmediato sin efectos estándar y el rayo del héroe queda recargado al instante (`weapons_ready_instant()`, sin encender auras de reliquia que no se posean).
- **Variantes integradas:**
  - **Exvoto (Opción A de Sonnet, `proto_remate_exvoto_v2.py`):** agarre de muñecas, elevación y partición vertical en 96×96, dejando las dos mitades de cera en el suelo durante ~1 s (parpadeando al final). Corregido el 2026-11-18: la primera integración usaba por error la A de DeepSeek.
  - **Cireneo (Opción A de DeepSeek, `ds_remate_cireneo.py`, provisional hasta la ronda final A/B):** el héroe le arranca la cruz de la espalda, salta y lo atraviesa contra el suelo con ella (celda 116×116), dejando el cadáver atravesado en el suelo durante ~1 s antes de desaparecer.
- **Entrada con embestida previa (decisión del usuario, 2026-11-18):** la animación horneada empieza con el héroe a una distancia fija del enemigo (~30 px el Exvoto, ~42 px el Cireneo), pero `L` vale hasta 96 px; sin más, el héroe aparecía de golpe en ese punto. Ahora, al pulsar `L`, el héroe corre con su animación normal de andar, más rápido que al andar (~4 px por frame, [TUNABLE-PLACEHOLDER], tope ~0,3 s), hasta el punto exacto donde empieza el remate en la dirección elegida, mirando al enemigo; si ya está más cerca, retrocede ese poco sin dejar de mirarle. Durante la embestida el héroe ya es invulnerable y no dispara, y el enemigo deja de tambalearse y espera quieto, orientado como empieza su animación: el Exvoto se gira hacia el héroe (le agarra de frente) y el Cireneo le da la espalda (el héroe le arranca la cruz por detrás). El fotograma 0 horneado no se usa: el renderizador del lab lo saca distinto de la escena 3D (fallo pendiente), así que el remate arranca desde el fotograma 1, que se repite. Al llegar empieza la animación combinada sin salto.
- **Cámara pegada al héroe durante el remate:** la cámara sigue los pies del héroe tal como aparecen en cada fotograma de la animación (interpolados entre fotogramas para que no dé tirones), en vez de deslizarse en línea recta del punto de partida al final.
- **Pendiente de balance:** tunear el alcance de detección, la ventana de tambaleo, feedback y el equilibrio de la recarga instantánea.

**Barra de vida del jefe.** Sustituye a la barra flotante sobre el enemigo durante el modo jefe. Fija en pantalla, con el nombre del jefe y una muesca en cada umbral de fase. Colores de la paleta (§6.10), sin primarios puros.

**Pendiente de la ronda A/B/C (definitivo, ROM real):** aspecto de la intro, de la barra de vida, de la telegrafía de cambio de fase y de la secuencia de victoria.

**Ronda 1 de maquetas (2026-11-17, `walkthroughs/modo-jefe/ronda1_maquetas.html`).**
- **Intro:** el jefe se ve en grande y repartido en las dos pantallas (de la A), pero dentro del propio juego, sin pantalla aparte (de la B). Abajo, su nombre, su título y **su frase del Códice, dicha en voz alta por él**. Descartada la de franjas de cine.
- **Barra de vida:** barra (no rosario), en la **fila de arriba de la pantalla de abajo, junto a los corazones**: es donde se mira durante la pelea.
- **Cambio de fase:** la marca de la barra salta rota y aparece el número romano de la fase sobre el jefe (C).
- **Victoria:** fundido a blanco con su nombre tachado (C), a juego con la intro.
- Ronda 2 (`ronda2_maquetas.html`): variantes de cada una y tres voces para el Abanderado.

**Decidido tras la ronda 2 (2026-11-17).** Esta es la versión que se programa:
- **Intro (B):** el juego se congela y la cámara se acerca ×2 al jefe dentro de la sala, en la pantalla de arriba, con un foco que oscurece los bordes. Abajo, la escena a oscuras con su nombre, su título y su frase, que el jefe dice con su voz. Se salta con `START`.
- **Voz del Abanderado:** la voz B de la ronda 2 (`walkthroughs/modo-jefe/assets/voz/`).
- **Barra de vida (C):** barra fina en la fila de arriba de la pantalla de abajo, desde el borde izquierdo hasta los corazones, **centrada en vertical con los corazones**; el nombre del jefe, debajo. Una marca en cada umbral de fase.
- **Cambio de fase:** la marca de la barra salta rota y aparece el número romano de la nueva fase sobre el jefe, mientras este pasa ~1 s invulnerable. Sale del estilo de la barra; no hay más que elegir.
- **Victoria (A con la frase de B):** la cámara se acerca de nuevo ×2 al jefe y las dos pantallas se destiñen a blanco; abajo, en el mismo sitio que en la intro, su nombre tachado en rojo y su frase de derrota (el Abanderado: «El asta ha caído.»), también con su voz. Después, la pantalla de reliquia.
- **Ficha de cada jefe:** nombre, título, frase de entrada, frase de derrota, sus dos audios, vida, umbrales de fase y escolta por fase.
- **Ritmo de la intro (corregido 2026-11-17 tras verla en la ROM: iba demasiado rápida).** Cada cosa a su tiempo, con pausas; cifras `[TUNABLE-PLACEHOLDER]`:
  1. 0,0 s: se congela; se ve al jefe en la sala, sin acercar, ~0,8 s.
  2. 0,8–2,6 s: acercamiento lento ×1 → ×2 (con frenada al final) y el foco se cierra a la vez.
  3. Pausa ~0,6 s.
  4. Aparece el nombre (fundido ~0,5 s) y, ~0,4 s después, el título.
  5. Pausa ~0,6 s; entonces dice su frase y el texto aparece mientras la dice.
  6. Al acabar la voz, ~1,2 s quieto.
  7. Se aleja (~0,5 s), se va el texto, vuelve el juego y entra la música. En total, ~9 s. START la salta en cualquier momento.
- **Ritmo de la victoria:** congelado en su última pose ~1 s; acercamiento lento (~1,5 s); se destiñe (~1,5 s); se tacha el nombre (~0,6 s); pausa; dice su frase de derrota y se escribe; ~1,5 s quieto; reliquia. En total, ~8 s.
