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
- **Lectura tras paredes (transparencias):** qué se ve del personaje y de los enemigos detrás de una pared y cómo se marca la base de la pared. Sin decidir; preguntas en `TECHNICAL.md` §4.6. No se toca código hasta decidirlo aquí.
- **Sonido:** fuera de la v0.3.
- **Transparencias tras paredes:** fuera de la v0.3; el comportamiento provisional actual no se amplía. Con muros sobre todo laterales en la franja vertical (§6.2) pesa menos que en la mazmorra.
- **v0.3, pendiente de su propia sesión de diseño (§6.9):** árbol de mejoras de cada clase, enemigo de enjambre, élites, minijefe y jefe, reglas de los tramos del mapa, tema concreto de los dos biomas y forma de la marea.
- **Tuning de combate y stats:** se hace jugando en la DS, sobre los valores de partida de §6.
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

### 6.0 Hito 0.3 mínima (decidido 2026-11-06)
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
- Una franja de 1 a 1,5 pantallas de ancho (256–384 px de mundo) y muchas de alto. No hay sitio para huir en círculos como en un survivors abierto: hay que abrirse paso, y eso da valor al apuntado, al empujón de la escopeta y al láser que atraviesa filas.
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

### 6.9 Plan
| # | Paso | Tipo | Agentes |
| :---: | :--- | :--- | :--- |
| 1 | **Prueba de horda en la DS:** pool de enemigos, IA por niveles de detalle, separación por rejilla y blit más barato, medidos con `PERF_PROFILE`. Criterio en `TECHNICAL.md` §4.7. Decide si el motor actual basta. | Técnica, primero | Sonnet implementa; la medición la juega el usuario |
| 2 | **Sesión de diseño de contenido:** árbol de mejoras de las dos clases, enjambre, élite, minijefe, jefe, catálogo y reglas de tramos, biomas y aspecto de la marea. Todo por escrito aquí antes de código (regla 9). | Diseño | Conversación; Haiku para buscar referencias |
| 3 | **Franja vertical:** tramos en el lab, encadenado por reglas, baker y navegación para mapas altos. | Técnica | Sonnet |
| 4 | **Bucle jugable:** marea, oleadas, gemas, nivel y elección, cofres y HUD. | Juego | Sonnet; Haiku para escenarios y logs |
| 5 | **Enemigos nuevos y jefes.** | Juego y arte | Sonnet; arte en el lab con el usuario |
| 6 | **Tuning y 60 FPS en la DS.** | Validación | Usuario en la DS; Haiku lee los logs |

Los pasos 1 y 2 no dependen entre sí y pueden ir en paralelo.

**Criterio de éxito de la prueba:** el usuario juega varias runs seguidas en la DS, muere pronto en las primeras y aun así quiere otra porque sabe qué elegiría distinto.
