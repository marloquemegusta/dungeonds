# DESIGN.md - Documento de Diseño

## 1. Visión y Alcance
- **Concepto:** survivors de frente vertical para Nintendo DS, con apuntado manual y tono gótico/grimdark (space marine contra necrones y bestias). Referencias: Halls of Torment y Vampire Survivors por el bucle; Diablo y Warhammer 40K: Inquisitor por lo que engancha al usuario (ir a la siguiente misión y mejorar); Isaac por la dificultad (lo normal es morir pronto hasta conocer las mejoras).
- **Pilar:** combate de Doom en isométrico (pocas armas contundentes con mucho *feel*, esquivar con strafe), contra una horda que viene de arriba y por un pasillo que hay que abrirse a tiros. Las dos pantallas forman un campo vertical: la superior es la vanguardia que se ve llegar y a la que se puede disparar.
- **Bucle vigente (v0.3, decidido 2026-11-06):** un nivel vertical de ~8 min con una marea que sube desde abajo, horda continua, gemas → nivel → elegir 1 de 3 mejoras, élites, un minijefe a mitad y un jefe arriba. Clase = arma. Detalle en §6.
- **Fantasía:** sin lore, pero clara y con entorno cambiante: ascender (o descender) por un pozo o una aguja infestada, cambiando de bioma por el camino. Los personajes, enemigos y mapas actuales son placeholders con la estética buena; el sistema debe aguantar cambiarlos.
- **Fuera de la prueba de la v0.3, a propósito:** progresión entre runs (equipo, desbloqueos), más de dos clases, sonido, más de dos biomas. La capa de equipo es el gancho a largo plazo (Diablo) y se diseña tras validar que una run divierte.
- **Historia de la dirección:** el proyecto nació como un Diablo de nigromancia con esbirros, descartado a favor del shooter. La v0.1 (4 arenas cerradas, §4) era fácil y poco divertida en la DS. La v0.2 (mazmorra de manadas con modificadores estilo Isaac, §5) fue más divertida pero se agotaba en un par de minutos: sin variedad entre runs ni motivo para volver. El 2026-11-06 se eligió el survivors vertical (§6) frente a un Isaac de salas (más barato pero menos del gusto del usuario) y a una campaña lineal tipo Diablo (demasiado contenido a mano). La lanza ósea y la muerte por fragmentos quedan como FX reutilizables.

## 2. Dirección de Arte y Pipeline
- **Técnica:** sprites 2D pre-renderizados a partir de modelos 3D con animación esquelética (FBX/GLB).
- **Proyección:** isométrica/dimétrica en 8 direcciones; mapa y personajes con la misma cámara e iluminación.
- **Herramienta de render:** el lab Three.js (`tools/lab/`), fuente de verdad visual para mapa y personajes. Detalle del pipeline en `TECHNICAL.md` §3.
- **Personajes actuales:** héroe (space marine), charger y necron.
- **FX reutilizables:**
  - Lanza ósea: salva de cinco astillas estrechas y puntiagudas dibujadas proceduralmente, sin outline, con motas en tonos marfil/hueso.
  - Muerte del enemigo: la silueta se rompe en fragmentos extraídos de sus propios píxeles que salen según el impacto y caen con una parábola breve.

## 3. Decisiones Abiertas
- **Actores detrás de muros (decidido 2026-11-10):** personaje y enemigos se ocultan según la profundidad horneada; no parpadean ni reciben transparencias, siluetas o marcas negras auxiliares cuando quedan detrás. La base caminable no se dibuja sobre el muro.
- **Sonido:** fuera de la v0.3.
- **Por decidir antes de cada versión (§6.9):** árbol de mejoras de las dos clases y su presentación (antes de la 0.4); enjambre, élites, cofres y emboscadas (antes de la 0.5); catálogo y reglas de tramos, tema de los dos biomas, minijefe, jefe y aspecto final de la marea (antes de la 0.6).
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
- **Aura de carga del francotirador (decidida 2026-11-05 tras ver referencias de Killua y SSJ2; tres variantes para comparar con el botón Y, `g_aura_style` 0=K, 1=C, 2=V; vale para los 3 estilos del haz):** mientras se carga el disparo (`AIM_AIMING` a `AIM_READY`) el personaje desprende un aura de **rayos azules angulosos** (no una línea continua ni una hélice lisa): polilíneas finas en zigzag de 3 px de paso con quiebros bruscos, alguna bifurcación y puntas en gancho, que **se regeneran cada 2-3 frames** para que crepiten. Colores: trazo de 1 px blanco con azul claro en píxeles alternos; sin halo oscuro (la v2 de K y C eran demasiado gruesas). Densidad, longitud y altura crecen con el progreso; al llegar a `AIM_READY` hay flash de 3 frames, anillo 2:1 en el suelo y aura al máximo hasta soltar; al soltar o cancelar se apaga en pocos frames. Respeta los muros, límite fijo de segmentos, sin `float`. **Oclusión por el personaje (regla común):** lo que nace en la mitad trasera de la elipse 2:1 (seno < 0) se pinta antes del sprite y lo tapa el cuerpo; lo delantero, después.
  - **Variante K (Killua / SSJ2, por defecto):** 5-6 rayos finos (1 px, blanco con azul claro en píxeles alternos, sin halo) que nacen en la elipse de los pies a distintas alturas y envuelven el cuerpo subiendo en tangente, 12-16 px de largo, con bifurcaciones ocasionales.
  - **Variante C (corona + rayos):** corona de 8 rayos de ~14 px que estallan desde un anillo 2:1 en el suelo hacia arriba y hacia fuera con bifurcaciones: base de 2 px (los 2 primeros pasos, borde azul claro y núcleo blanco) y el resto de 1 px como K; más 2 rayos finos de 1 px envolventes a media altura.
  - **Variante V (chispas verticales, la v1 con oclusión):** chispas finas de 6-14 px que suben desde la elipse de los pies, de blanco a amarillo a naranja según la altura, más densas con la carga.
- **Colimado del láser del francotirador (decidido 2026-11-06, rama `feat/sniper-collimation`, tras ver mockups `walkthroughs/sniper-collimation/assets/`):** mientras se carga, el haz no solo cambia de color: se va **colimando**. Empieza ancho, difuso y rojo; se estrecha, se vuelve estable y pasa a verde, hasta quedar en 1 px cuando está listo. Progreso `prog = s_aim_timer / aim_frames` (0..256, `aim_frames` = `aim_min_frames` + mejora; una sola división por frame). Anchura lateral máxima 6 px a 0 %, 0 a 100 %. El color de la línea central va de rojo a verde entre el 70 % y el 100 %. Al llegar a `AIM_READY` el haz queda fino, verde y estable (sin parpadeo). Compatible con el aura K/C/V (se dibujan en pasadas distintas).
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
- El jugador va **centrado en la pantalla inferior**, porque solo ahí se toca. Quedan ~96 px de vista detrás de él y ~288 delante.
- **La pantalla superior es la vanguardia, no un menú:** muestra la horda que llega, los puntos de aparición y los avisos de élite, minijefe y jefe. Se le puede disparar con el apuntado por vector de §4.1. Premia a las clases de largo alcance.
- Los menús, como la elección al subir de nivel, van en la pantalla inferior.

### 6.4 Marea y aparición de enemigos
- **Marea:** sube desde el borde inferior a velocidad constante en la prueba (sin adaptarse al jugador). Dentro de ella el jugador recibe daño continuo y va más lento, pero no muere al instante. Los enemigos y gemas que alcanza desaparecen sin dar recompensa. Se para durante el minijefe y el jefe. El aspecto (fuego, plaga u oscuridad) está por decidir.
- **Aparición:** la mayoría de los enemigos nacen arriba, fuera de la vista o en puntos visibles en la pantalla superior. Algunos salen de las salas laterales. Desde abajo vienen pocos y siempre con aviso en el borde inferior (emboscadas). La densidad sube con el tiempo.
- **Totales frente a simultáneos:** cientos de enemigos a lo largo de la run, unas pocas decenas a la vez entre las dos pantallas. Los que quedan muy atrás se reciclan. Cifras técnicas en `TECHNICAL.md` §4.7.

### 6.5 Clases y controles
- **Clase = arma principal.** Dos clases separadas: **francotirador/láser** (la que más aprovecha la pantalla superior; se prueba primero) y **escopeta**. Se elige al empezar la run.
- **Controles:**
  - D-pad: mover.
  - Stylus: apuntar por vector, como en §4.1. Mantener pulsado dispara solo al ritmo del arma, para no tener que tocar cientos de veces por run. En la escopeta repite cada bombeo. En el francotirador sigue siendo cargar y soltar: la carga es su gracia. Si cansa en la DS, se revisa.
  - L: **habilidad activa con enfriamiento**, común a las dos clases. En la prueba es la granada de §4.9.
- **Vida:** golpes más i-frames, como ahora (5 golpes de partida). De vez en cuando cae un pickup que cura 1 golpe.

### 6.6 Economía y mejoras
- **Gemas:** cada muerte suelta una gema cuyo valor depende del tipo de enemigo. Se recoge pisándola, con un imán corto que se puede mejorar. Las que se traga la marea se pierden, así que hay que decidir si se vuelve a por ellas.
- **Subir de nivel:** al llenar la barra se pausa el juego y se elige **1 de 3 mejoras** tocando la pantalla inferior. Unos 15–20 niveles por run. Sin reroll en la prueba.
- **Mejoras:** la mitad son del arma y cambian su comportamiento, no solo un número (perforar, rebotar, explotar al matar, más proyectiles...). La otra mitad son del personaje (vida máxima, velocidad, imán, i-frames). La tabla de modificadores de §5 sirve de semilla.
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
La prueba de §6.1–6.8 se construye en versiones jugables pequeñas, cada una en su sesión y su rama. Una versión se cierra con build sin warnings, tests de host, escenarios y 60 FPS medidos en la DS (`AGENTS.md` reglas 4 y 6), y se fusiona en `main` antes de empezar la siguiente. Las que traen comportamiento nuevo empiezan con una sesión de diseño que lo deja escrito aquí (regla 9). Tras cada versión el usuario la juega en la DS y su feedback entra en la siguiente.

| Versión | Contenido | Antes de empezar | Estado |
| :--- | :--- | :--- | :--- |
| **0.3 mínima** | Franja infinita de 512 px, horda desde arriba, marea, curas y HUD de altura (§6.0). | — | Cerrada 2026-11-06 (`walkthroughs/v03-minima/`) |
| **0.3.1** | Tuning y pulido de la 0.3 mínima, con tres tiers de enemigos (esqueleto, cargador que carga, tirador láser) y escala de cifras 100 = 1,0 (§6.9.1). | Nada | Cerrada 2026-11-07 (`walkthroughs/v031-tuning/`) |
| **0.3.2** | Escenario del primer nivel: estilo, ambientación y piezas del entorno (§6.9.1b). | Sesión de dirección de arte | **Siguiente** (pendiente de diseño) |
| **0.3.3** | Personajes: reevaluar los sprites, ajustar tamaño y pasar al estilo definido en la 0.3.2 (§6.9.1b). | 0.3.2 cerrada | Pendiente de diseño |
| **0.4** | Progresión dentro de la run: gemas con imán corto, experiencia, subir de nivel con pausa y elegir 1 de 3 mejoras con icono y una línea de efecto (§6.6), HUD de vida, experiencia, nivel y tiempo, elección de clase al empezar y controles de §6.5 que falten. | Sesión de diseño de mejoras y clases | Pendiente de diseño |
| **0.5** | Enemigos y recompensas: enjambre, élites que sueltan cofre, emboscadas desde abajo con aviso. Pool de 48 y criterio de horda de `TECHNICAL.md` §4.7 (IA por niveles de detalle, separación por rejilla, blit más barato). | Sesión de diseño de enemigos | Pendiente de diseño |
| **0.6** | Estructura de la run: tramos hechos a mano encadenados por reglas (§6.2), dos biomas, minijefe a mitad y jefe arriba, marea que se para en los combates. Cierra la prueba completa de §6.1 (~8 min, ganar matando al jefe). | Sesión de diseño de tramos, biomas y jefes | Pendiente de diseño |

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
  2. *Telegrafía* ~30 frames: parpadeo del sprite y se queda quieto. Fija ahí la dirección hacia el jugador.
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
  - **Escala única (corrige `TECHNICAL.md` §4.1):** el marine mide **2 m** y ocupa 31 px de alto, así que el mapa se dibuja a **~17,9 px/m** (no 40,42) y los enemigos de 1,5 a 3 m miden 23–46 px. Equivalencias: baldosa de 32×16 px = 1,8 m; el carril de 480 px = 26,8 m; una banda de 128 px = 14,3 m de profundidad; un saco de arena (0,5 × 0,3 m) = 9 × 5 px; un cráter de 4–8 m = 72–144 px. Los sprites actuales no cambian de tamaño.
  - **Método (2026-11-08):** el suelo es un **juego de tiles diseñado**, no un render troceado: losas con tiles Wang y transiciones por esquinas (alfombra, mosaico, sangre, cera). Las **piezas** (bancos, columnas, estatuas, relicarios, sacos, cirios) siguen el flujo de los personajes: imagen de IA → 2D→3D (Tripo) → render con la misma cámara y luz que los personajes → estampa alineada a 8 px con su huella de colisión y profundidad de oclusión. Escala de juego: piezas un 30-50 % mayores que las reales si hace falta para leerse. Paleta: se extrae de los prerenders de las piezas del lote 1 y la aprueba el usuario (el arte objetivo de pantalla completa se canceló el 2026-11-08). Flujo completo paso a paso: `walkthroughs/v032-escenario/BIBLIA.md`. Motivo: con relieve o grano continuo ningún tile se repite (medido: 960 tiles distintos por banda de 480×128 y 825 en la ventana visible, frente al tope de 440; `walkthroughs/v032-escenario/INFORME_INTENTOS.md`).
  - **Presupuesto:** hard: < 440 tiles distintos en cualquier ventana visible de la pantalla superior (cache de 448). El tope de 400 totales del kit es del script de bake y puede revisarse. Pruebas y evidencias en `walkthroughs/v032-escenario/`.
- Cierre: el escenario se ve bien en la ROM real (capturas) y 60 FPS en la DS (regla 6).

**0.3.3: personajes.**
- **Reevaluar** si los sprites actuales (héroe, cargador, tirador, esqueleto) valen con el nuevo estilo.
- **Ajustar ligeramente su tamaño** (`TECHNICAL.md` §4.1, escala personaje/mapa) y mantener anclas, muzzle y sombras.
- Mejorar el estilo pasando de nuevo el flujo imagen → 2D→3D → pre-render, incluida la **marca visual del aturdimiento** del cargador (pendiente de la 0.3.1).
- Cierre: contactos de las 8 direcciones revisados de verdad, build sin warnings, tests de sprites y 60 FPS en la DS.

> **Versiones 0.4 a 0.6: borrador.** Recogen lo que se espera hoy de cada una según §6.1–6.8. Se revisan con el feedback de la versión anterior y en su sesión de diseño, que decide los detalles y puede mover piezas de una versión a otra.

#### 6.9.2 Versión 0.4: progresión dentro de la run (borrador)
**Objetivo:** que cada run tenga decisiones que cambien cómo se juega y que morir enseñe qué elegir la próxima vez. Es el criterio de éxito de la prueba (abajo).

**Dentro:**
- **Gemas** al matar, con valor según el tipo de enemigo. Se recogen pisándolas, con un imán corto, y la marea se las traga (§6.6). Se dibujan en OAM (`TECHNICAL.md` §4.7).
- **Experiencia y nivel.** Al llenar la barra se pausa el juego y se elige **1 de 3 mejoras** tocando la pantalla inferior. Unos 15–20 niveles por run, sin reroll.
- **Mejoras:** la mitad del arma, que cambian su comportamiento (perforar, rebotar, explotar al matar, más proyectiles…); la otra mitad del personaje (vida máxima, velocidad, imán, i-frames). Cada una con icono, nombre y una línea de efecto. La tabla de modificadores de §5 sirve de semilla.
- **Clases:** se elige francotirador/láser o escopeta al empezar (§6.5), cada una con su árbol de mejoras.
- **Controles de §6.5 que falten:** mantener pulsado para disparar al ritmo del arma y la granada en L con enfriamiento.
- **HUD:** vida, barra de experiencia, nivel y tiempo; se mantiene la altura.

**Antes de empezar (sesión de diseño):**
- lista de mejoras de cada clase, con sus cifras de partida y cómo se combinan;
- curva de experiencia;
- iconos y presentación de la elección;
- si las curas de la 0.3 conviven con la mejora de vida o se ajustan.

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
**Objetivo:** la prueba completa de §6.1. Una run de unos 8 min con principio, mitad y final, que se gana matando al jefe.

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
