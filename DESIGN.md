# DESIGN.md - Documento de Diseño

> La partida vigente es la de §6.13 (15 stages, 3 jefes, Dones y Reliquias por relicario). Historia y diseños superados: `DESIGN-ARCHIVE.md`.

## 1. Visión y Alcance
- **Concepto:** survivors de frente vertical para Nintendo DS, con apuntado manual y tono gótico/grimdark (el Corazón Abierto y otros futuros personajes contra los caídos de la Cruzada). Referencias: Halls of Torment y Vampire Survivors por el bucle; Diablo y Warhammer 40K: Inquisitor por lo que engancha (ir a la siguiente misión y mejorar); Isaac por la dificultad (lo normal es morir pronto hasta conocer las mejoras).
- **Pilar:** combate de Doom en isométrico (cada personaje con un arma contundente y mucho *feel*, esquivar con strafe), contra enemigos colocados con intención en salas que hay que abrirse a tiros. Las dos pantallas forman un campo vertical: la superior es parte del combate (también te dispara) y se puede apuntar a ella.
- **Bucle:** una subida de 15–18 min de 15 stages en tres actos, con jefe al final de cada uno (§6.13). Personaje = arma única. Hoy solo existe el Acto I y El Abanderado como jefe (repetido en los stages 10 y 15).
- **Fantasía:** la Columna intentó llegar al Altar de una catedral que no termina y cayó por el camino; el jugador hace el mismo recorrido (`LORE.md`). Los personajes, enemigos y mapas actuales son una primera versión con la estética buena; el sistema debe aguantar cambiarlos.
- **Fuera de la prueba, a propósito:** progresión entre partidas (equipo, desbloqueos), más de un personaje y más de un acto con contenido. La capa de equipo es el gancho a largo plazo (Diablo) y se diseña tras validar que una partida divierte.
- El prototipo ARPG (rama `proto/arpg`) tiene su diseño en `DESIGN-ARPG.md`.

## 2. Dirección de Arte y Pipeline
- **Técnica:** sprites 2D pre-renderizados a partir de modelos 3D con animación esquelética (FBX/GLB), **sin outline** en personajes, enemigos ni piezas de escenario.
- **Proyección:** isométrica/dimétrica en 8 direcciones; mapa y personajes con la misma cámara e iluminación.
- **Herramienta de render única:** el lab Three.js (`tools/lab/`), fuente de verdad visual para mapa y personajes. Detalle del pipeline en `TECHNICAL.md` §3.
- **Regla de personaje:** **1 personaje = 1 arma**; cualquier selector de armas, auras o animaciones en la ROM jugable es solo herramienta de depuración.
- **Personajes actuales:** héroe (El Corazón Abierto) y enemigos Exvoto, Cireneo v2, Ojo del Tribunal y Abanderado (§6.10).
- **FX reutilizables:**
  - Lanza ósea: salva de cinco astillas estrechas y puntiagudas dibujadas proceduralmente, sin outline, con motas en tonos marfil/hueso.
  - Muerte del enemigo: la silueta se rompe en fragmentos extraídos de sus propios píxeles que salen según el impacto y caen con una parábola breve.

## 3. Decisiones de plataforma
- **Actores detrás de muros:** personaje y enemigos se ocultan según la profundidad horneada; no parpadean ni reciben transparencias, siluetas o marcas negras auxiliares cuando quedan detrás. La base caminable no se dibuja sobre el muro.
- **Sombras de personajes:** la sombra de héroe y enemigos conserva la forma horneada del lab por dirección y frame y su tono (suelo al 50 %), pero la oscurece la propia consola en vez del procesador. Diferencias aceptadas: dos sombras solapadas se funden en un solo tono; si un enemigo queda detrás de una pieza o muro, su sombra se oculta entera en vez de recortarse; las marcas de suelo de las armas no quedan oscurecidas por las sombras. Mediciones: `walkthroughs/stress-enemies-profiling/`.
- **Sonido:** SFX base del héroe y música de combate hechos (§6.10); los de mejoras, pendientes (§6.12.14).
- **Por decidir:** lo de §6.13.4.

---

## 4. Game feel y efectos

> Solo siguen vigentes el game feel (§4.7) y la regla de perspectiva del suelo (§4.9). Las armas y arenas de la v0.1 están en `DESIGN-ARCHIVE.md`.

### 4.7 Game Feel
- **Al impactar:** hitstop de 2–4 frames y destello blanco del enemigo.
- **Al disparar:** temblor de pantalla proporcional al disparo.
- **Origen del disparo:** proyectiles, fogonazo y línea de mira salen de la boca del arma, no de los pies del personaje. El punto de boca por dirección lo exporta el lab junto al spritesheet.
- **Aspecto del disparo:** procedural, en la línea de la lanza ósea: fogonazo de 2–3 frames en la boca y chispas de impacto como líneas que salen según la normal y se apagan.
- **Ambas pantallas iguales:** la pantalla superior dibuja lo mismo que la inferior (suelo, actores, sombras, proyectiles enemigos y FX del disparo) desplazada una pantalla hacia arriba, para poder ver y apuntar a lo que queda fuera de la pantalla táctil. Solo la inferior lleva el HUD de depuración.
- **Muerte:** fragmentos (FX de §2).
- **Al recibir daño:** destello rojo e i-frames.

### 4.9 Perspectiva del suelo y presupuesto de efectos
- **Perspectiva del suelo:** todo lo que está *en el suelo* (marcador de apuntado, anillos de aviso, charcos, ondas de choque, el aro del Cilicio) es una elipse 2:1 en pantalla (semieje horizontal R, vertical R/2) y se pinta **en el suelo, bajo sombras y personajes** y respetando los muros. Lo que tiene volumen (fuego, escombros, humo, destellos) se dibuja encima.
- **Oclusión por el personaje:** lo que nace en la mitad trasera de la elipse 2:1 se pinta antes del sprite y lo tapa el cuerpo; lo delantero, después.
- **Sin transparencias:** los bordes suaves se hacen con tramado.
- **Presupuesto:** ninguna variante puede bajar de 60 FPS en la DS (`AGENTS.md` regla 6). Se descarta la que no lo cumpla.

---

## 6. El juego: diseño vigente

La partida es la de §6.13. Quiere la dificultad de Isaac (morir mucho hasta dominar las mejoras), el gancho de Diablo (siguiente misión, mejor equipo) y una fantasía clara con entorno que cambia.

### 6.3 Cámara y pantallas
- **Cámara hacia el grupo (en combate):** si hay enemigos vivos en la sala, el encuadre vertical apunta a un punto entre el héroe y el centro del grupo, pesando más los enemigos cercanos. Así se kitea hacia atrás sin perder de vista al grupo: manda dónde está el peligro, no hacia dónde anda el héroe.
  - **Sin saltos:** la cámara se acerca a ese punto con suavidad (rápida si está lejos, frenando al llegar); cuando muere un enemigo o el grupo se mueve, el encuadre se recoloca sin tirones.
  - **Límites:** el héroe nunca sale de una franja de la pantalla táctil (entre ~25 % y ~75 % de su altura) para que siempre se pueda apuntar a su alrededor; si el grupo queda más lejos, se ve solo la parte que cabe.
- **Cámara con adelanto vertical (*look-ahead*, sin enemigos):** el encuadre se adelanta suavemente según el sentido de marcha vertical:
  - **Al subir:** coloca al jugador en el tercio inferior (~69 %, ~132 px de vista delante y ~60 px detrás en la pantalla táctil).
  - **Al bajar (retroceder):** desliza la vista hacia atrás hasta dejar al jugador en el tercio superior (~33 %, ~128 px de vista detrás).
  - **Al parar o hacer *strafe* lateral:** la cámara mantiene el último encuadre, y requiere ~0,37 s (22 frames) de marcha vertical sostenida antes de empezar a deslizarse (a 2 px/frame) para que los esquives cortos no muevan el suelo bajo el stylus.
- **La pantalla superior es la vanguardia, no un menú:** muestra la parte de arriba de la sala, con enemigos que también te disparan, y avisos del jefe. Se le puede disparar con el apuntado por vector (el lápiz apunta desde el personaje, aunque el objetivo quede fuera de la pantalla táctil).
- Los menús, como la elección de Don, van en la pantalla inferior.
- **Menú inicial y menú de pausa:** la pantalla superior muestra solo la catedral de fondo; la inferior (táctil) la muestra oscurecida con el menú encima: cajas oscuras semitransparentes con texto plano en la paleta `FX_SH_*` (marfil y oro/carmesí apagado para la opción activa, ceniza para las inactivas). Se navega con lápiz o con cruceta + `A` (confirmar) / `B` (volver o reanudar). `START` abre y cierra la pausa (tras morir conserva el reinicio).
  - **Menú inicial:** `Nueva partida`, `Códice` y `Controles`. Solo las variantes de pruebas (`SKIP_TITLE`) arrancan directas.
  - **Pausa:** `Continuar`, `Reiniciar`, `Códice` y `Controles`; congela combate y música. `SELECT` e `Y` (comparación de efectos) solo existen en las variantes de pruebas (§6.5).
  - **Submenús:** `Códice` abre §6.11; `Controles` muestra los de §6.5 y un botón `Volver`.
  - **Tarjetas de introducción:** al elegir `NUEVA PARTIDA` salen 6 tarjetas (no al reiniciar desde la pausa; no hay guardado, así que siempre salen). Fondo negro y borde gris de 1 px en ambas pantallas; arriba, un bucle de vídeo de la pantalla inferior del juego real (~2 s, 30 imágenes por segundo), abajo título y texto corto con la fuente del códice. Botones: `SALTAR` siempre visible (también `START`), `< ANT` y `SIG >` (lápiz, cruceta, `A`/`B`, `L`/`R`); en la última, `EMPEZAR`.
    - **Tarjetas:** 1) La catedral. 2) Moverse y apuntar: la cruceta mueve; el lápiz apunta y mantenerlo carga el disparo. 3) Coberturas: agacharse tras bancos y sacos (§6.13.6). 4) Rematar: `L` sobre un enemigo tambaleante (§6.13.8), con las invulnerabilidades del remate y del golpe. 5) Relicarios: romperlos da un Don. 6) Vida: 5 Sagrados Corazones. El texto exacto vive en la ROM. Pendiente: la rotura del relicario se ve poco (la oferta de Don la tapa).

### 6.5 Personaje y controles
- **Personaje = arma única.** Cada personaje tiene su única arma fija: El Corazón Abierto, su rayo de fuego sagrado. Otra clase sería otro personaje. Hoy solo hay uno.
- **Controles:**
  - Cruceta: mover. Se agacha solo tras coberturas bajas (§6.13.6).
  - Lápiz: apuntar por vector; mantenerlo pulsado carga el rayo y al soltar dispara. Al volver a pulsar, la carga empieza de cero al instante (§6.12.10).
  - `L`: remate sobre el enemigo tambaleante más cercano (§6.13.8).
  - `START`: pausa (§6.3).
- **Controles de depuración (solo en variantes de pruebas, no son del juego):** `SELECT` (estilo de efectos A/B/C), `Y` (aura de carga L/G/E/H), el ciclo de armas de la v0.1 y los cambios de animación en vivo.
- **Vida:** 5 golpes de partida más i-frames; el Don de Vida sube el tope. Los relicarios no curan.

### 6.6 Mejoras
- **Sin gemas ni experiencia.** Las mejoras salen de romper un relicario por pasillo, que abre la pantalla de elección de **1 de 3 Dones**; las Reliquias, del relicario dorado al vencer a cada jefe (§6.13.5).
- **Dones** (estadísticas apilables) y **Reliquias** (únicas, cambian cómo se juega), diseñados por arquetipos en §6.12.
- **Presentación:** cada mejora se muestra con icono, nombre y su efecto en una línea (los modificadores sin explicar parecían aleatorios).
- **Cofres de élite:** descartados; el relicario ocupa ese lugar.

### 6.9 Hoja de ruta por versiones
Cada versión se construye en su sesión y su rama y se cierra con el cierre de `AGENTS.md`. Las que traen comportamiento nuevo empiezan con una sesión de diseño que lo deja escrito aquí (regla 9).

| Versión | Contenido | Estado |
| :--- | :--- | :--- |
| **0.3.2 escenario** | Catedral: suelo en rombos, lápidas, muros, piezas 3D, godrays. | Hecha; las piezas del acto I son 3D (`walkthroughs/props-catedral-v2/`) y el escenario se organiza en las salas de §6.13.6 |
| **0.3.3 personajes** | Corazón Abierto, Cireneo v2, Exvoto, Ojo del Tribunal, Abanderado y monaguillo. | Hecha; faltan el Campanero y El Paso |
| **0.4 progresión** | Dones y Reliquias (§6.12). | Hecha; la fuente de mejoras son los relicarios (§6.13.6) |
| **0.6 estructura** | La Subida de §6.13: tres actos con jefe. | **En curso:** Acto I por encuentros, modo jefe y remate integrados; faltan actos II y III y dos jefes |

Escala de vida y daño en centésimas, 100 = 1,0 (sin `float`, `AGENTS.md` regla 2); las mejoras multiplican en porcentaje. Las vidas vigentes del acto I están en §6.11.1 y en `include/encounters_act1_hp.h`.

#### 6.9.1b Dirección de arte: escenario y personajes
No trae mecánicas nuevas. Compositor, tramos y presupuesto de tiles: `TECHNICAL.md`.
- **Estilo:** tipo Trench Crusade o Warhammer 40k, pero más sucio y sombrío: metal oxidado y gastado, fe fanática, reliquias, desgaste. Hilo conductor: «la Cruzada que no terminó»; los enemigos son los caídos de esa cruzada, con ficha diegética en el Códice (§6.11).
- **Nivel 1: una catedral** gótica oscura (Warhammer 40k, Trench Crusade, Blasphemous). Se sube por una nave hacia un altar que se aleja; la guerra se metió dentro (bancos en barricada, sacos, alambre, cruzados muertos). El orden de los biomas posteriores sigue abierto.
- **Coberturas bajas: bloquean el paso, no el fuego, y ocluyen.** Terreno (losas, alfombra, sangre, cera): solo decorativo. **Piezas altas:** columnas y estatuas (`santo`) paran todos los disparos, el rayo del jugador y cortan la visión y la sentencia del Ojo. Bancos, relicario y velas solo bloquean el paso.
- **Color y legibilidad:** sin colores reservados; contraste de luminancia: suelo transitable tranquilo, de valores medios-bajos y poco contraste local; el detalle fuerte en bordes, muros y piezas.
- **Suelo de la nave:** damero de losas giradas 45° que alternan dos piedras pardas casi iguales (rombo de 32×16 px), modeladas en 3D y renderizadas con la cámara del juego. **Lápidas:** la piedra tallada ocupa el bloque entero de losas (3×2 o 2×1), a ras del suelo y con la cabeza al fondo de la pantalla (`tools/catedral_editor/gen/README.md`).
- **Muros, perspectiva y luz:** todo se ve con la cámara del juego (ortográfica, 30°, mirando a lo largo de la nave); nada de alzados frontales pintados. Muros con el módulo 3D `gothic_arch` repetido; muros y columnas suben hasta un techo que no se dibuja. Las vidrieras y rosetones no se dibujan: se ven por su luz, que entra horizontal desde la cara interior del muro. Las piezas proyectan sombra horneada en sus tiles (las lápidas, planas, no). Piezas, suelo y personajes se renderizan con el preset «Neutra» (`tools/props/props_render_settings.json`), sin contorno; personajes con el pre-render «C2» (supersampling ×4, tono neutro, curva S suave, bordes al 30 % y enfoque suave; `walkthroughs/legibilidad-lab/`).
- **Escala única:** el héroe mide 2 m y ocupa 31 px de alto, así que el mapa se dibuja a ~17,9 px/m y los enemigos de 1,5 a 3 m miden 23–46 px (el Abanderado, ~3 m, unos 54 px en celda de 60×60). Una baldosa de 32×16 px = 1,8 m.
- **Método:** el suelo es un juego de tiles diseñado, no un render troceado. Las piezas siguen el flujo de los personajes: imagen de IA, 2D→3D (Tripo), render con la misma cámara y luz, estampa alineada a 8 px con su huella de colisión y profundidad de oclusión (`walkthroughs/v032-escenario/BIBLIA.md`).
- **Cierre:** el escenario se ve bien en la ROM real y 60 FPS en la DS (regla 6).

### 6.10 Reparto de la demo
Aspecto y papel de cada personaje. Las mecánicas base y las cifras de cada enemigo están en §6.11.1, §6.13.6 y §6.13.9; aquí no se repiten.

- **Personaje (clase láser): El Corazón Abierto:** pecho abierto con grapas de hierro y un sagrado corazón en llamas; carga con los brazos en cruz y el rayo sale del pecho (rayo que atraviesa filas, §6.12.2). El rayo no es un arma sino un milagro que consume el cuerpo: sale del propio personaje, que va quemado por usarlo y sigue vivo por fe. A 31 px el origen del rayo debe ser un punto de luz claro y la carga una pose que cambie la silueta. Las imágenes para 3D se generan en **T-pose, con las manos vacías**, y el arma en una imagen aparte (`walkthroughs/concepto-demo-personajes/`).
- **Color de personajes:** todos, protagonista y enemigos, llevan **acentos negros y rojos** por legibilidad; la base de cada uno (cera, piel, metal) y los brillos (dorado del corazón, verde de los caídos) se mantienen.
- **Enemigos:** son los caídos de la Cruzada, gente cuya fe se pudrió. **Cada uno hizo un pacto:** entregó algo de sí mismo a cambio de un poder; el precio se ve en el cuerpo y es su debilidad en el juego; su luz es **verde enfermiza** frente al dorado anaranjado del Corazón Abierto.
  - **Masa → Los Exvotos:** devotos convertidos en figuras de cera de tamaño humano, en procesión lenta. Se derriten al morir. Monja de cera con velo negro y faja roja, con las **manos juntas rezando** (las velas son atrezo del mapa junto al que rezan; modelo en `assets/models/characters/exvoto/source/`). Clips: rezar de pie, rezar de rodillas, levantarse y andar rezando (procesión con los brazos fijos en la pose de rezo, cuerpo encorvado y cabeza baja).
    - **En oración:** empiezan quietos rezando **de rodillas**, repartidos un poco al azar pero con sentido: junto a velas, frente a rosarios u otro atrezo devoto. Despiertan todos a la vez al cruzar el borde de abajo del encuentro (§6.13.6): la arrodillada se levanta (~70 frames, sin moverse) y anda; andan rezando hacia el héroe, con la esquiva del rayo de §6.13.6.
    - **Muerte («se derrite»):** el sprite se hunde y se aplasta en ~20 frames y deja un **charco de cera** (elipse 2:1 clara con borde oscuro, colores desaturados) que dura ~90 frames, se desvanece y no hace nada.
  - **Cargador → El Cireneo:** entregó sus brazos a cambio de la fuerza de la cruz. Gigante crucificado que camina: brazos clavados al travesaño (fijos en la pose del T-pose) y cruz atornillada a la espalda. Embiste encorvado con la cruz por delante y no puede girar; al chocar con una columna la cruz se clava y forcejea para sacarla (aturdimiento y marca visual). IA: §6.13.6.
  - **Tirador → El Ojo del Tribunal:** inquisidor con una linterna de vidrio verde enjaulada en lugar de ojos; su sentencia es su mirada escrita en el suelo (sigue, se fija, sentencia).
    - **Aspecto:** **bajo y gordo**, túnica **morada oscura** (no negra) con faja roja, pliego blanco y sello de lacre, para que no todos los caídos sean altos y delgados y el cuerpo se separe del suelo oscuro. Debe leerse visiblemente más grande que el protagonista (~+40 %, sprite de 56×56 px). Modelo en `assets/models/characters/ojo/source/`.
    - **Cabeza en la mano:** el **farol** ocupa su cabeza y vigila sin descanso; con el brazo extendido sostiene **su propia cabeza**, ciega (ojos cosidos) pero aún juzgadora. El farol mira y escribe la sentencia en el suelo; la cabeza solo la pronuncia (abre la boca con un destello y no dispara nada). Malla estática: el movimiento lo aporta el brazo.
    - **Mecánica «Sentencia escrita en el suelo»** (cifras `[TUNABLE-PLACEHOLDER]`; papel y reglas de sala en §6.13.9): sin efectos mientras busca; al fichar al héroe se para y escribe en el suelo una grieta verde hueso/fósforo con ojos que llega hasta él; al fijarla la prolonga hasta el muro y cuenta atrás con sus ojos; al cerrarse, toda la línea arde a la vez. Se esquiva saliendo de la línea a tiempo.
      1. *Buscar (andar):* camina despacio (velocidad 110, ≈ un tercio del héroe) oscilando la cabeza a izquierda y derecha (~0,5 s por paso). El farol solo titila tenue; no hay nada en el suelo.
      2. *Fichar y seguir (~40 frames):* al ver al héroe (línea de visión, sin alcance máximo), se para; fogonazo con un anillo verde hueso alrededor del farol (~8 frames). Desde sus pies avanza por el suelo una **grieta verde hueso/fósforo con ojos de 7×3** (cerrados, como rendija) que llega al héroe en ~14 frames y lo **sigue**.
      3. *Fijar (~20 frames):* la grieta se **congela** y se prolonga hasta el primer muro o columna en la dirección fijada; el núcleo pasa a 2 px. Una luz corre del Ojo a la punta **abriendo cada ojo** (la cuenta atrás) y en los últimos ~10 frames pulsa. Es la ventana para salir de la línea.
      4. *Sentencia:* **toda la línea estalla a la vez** en llamas espectrales verdes con motas; la cabeza abre la boca con un destello. El daño es esa misma franja de suelo, de los pies del Ojo al muro, **ancho de golpe 8** (la cobertura baja se comprueba desde los pies); 1 golpe si el héroe está en ella (respeta los i-frames). ~0,5 s: golpe 3 frames, arde ~20, disipa ~8; hace daño durante golpe y llama. Muros y columnas cortan la línea de visión y la sentencia. Matarlo antes de la sentencia la anula.
      5. *Enfriamiento* ~90 frames y vuelve a buscar; queda una **cicatriz** en el suelo que se apaga en ~1 s.
      - Tope de 2 Ojos apuntando a la vez (legibilidad); el resto se acerca o espera.
      - Animaciones: andar, mirar (quieto, linterna adelantada, en bucle) y sentenciar (gesto corto de 4-6 frames al soltar el haz).
- **Élites y jefes futuros** (sin cofres, §6.6). Hoy solo el Abanderado está programado, como jefe:
  - **El Campanero de Ánimas** (jefe del acto II, §6.13.2): se arrancó la lengua para hacerla badajo de su campana, a cambio de que los muertos le oigan; boca vacía y cosida. Arrastra la campana rajada (va en la mano, como un arma); al tocarla brotan Exvotos en un círculo de cera en el suelo (elipse 2:1, §4.9). El toque es la telegrafía.
  - **Jefe final: El Paso.** Paso de Semana Santa con costaleros muertos fusionados a las vigas; arriba, una Dolorosa viva con siete puñales que disparan rayos verdes que siguen al jugador. Embiste en línea; al matar costaleros cojea, se inclina y se ralentiza. Se decide en su sesión si se trata como bloque rígido con costaleros sencillos.
- **El Abanderado (jefe):** invocador que **no ataca**. El estandarte va **en la mano, como bastón**; ~54 px en celda de 60×60. Aparece en la sala del jefe de los stages 5, 10 y 15 (§6.13.1, §6.13.7); vida y disparos: §6.11.1, §6.13.6.
  - **Patrulla** despacio y **cabizbajo**, apoyado en el estandarte (clip «Sad Walk» de Mixamo), entre puntos al azar de su sala.
  - **Te ve** a menos de ~1 pantalla y sin pared en medio: se para, **levanta la cabeza, te mira e inclina el estandarte hacia ti** (gesto generado por programa). Si te alejas o te escondes unos 2 s, baja la cabeza y vuelve a patrullar.
  - **Invoca** mientras te apunta: cada ~3 s aparece un **charco color crema** a medio camino entre él y tú, y de cada charco salen **2 Exvotos monaguillo** (tope de 8 vivos). El monaguillo emerge poco a poco (~0,5 s), **invulnerable, sin hacer daño ni moverse**, y el charco se seca al terminar.
  - **Exvoto monaguillo:** variante del Exvoto (modelo «monje zombi», `tripo_convert_9a55a12b`). Mismas reglas: muere de un golpe, camina lento hacia ti en postura de rezar y hace daño por contacto.
- **Pendiente:** si la quemadura del cuerpo crece con las mejoras; cifras, fases y telegrafías de élites y jefe; tamaño del paso en pantalla (`TECHNICAL.md`); si hay minijefe en la demo.
- **Corazón Abierto en el juego** (`walkthroughs/corazon-abierto/`):
  - **Animaciones:** modelo Tripo con rig Mixamo (`assets/MANIFEST.md` §2); andar de Mixamo adaptado con la cadera en el sitio.
  - **Carga y disparo:** un solo clip de 8 frames por dirección (f0 = brazos en cruz, f7 = derrumbado). **Cargar** lo recorre **al revés** (f7 → f0) según el progreso de carga y se queda en f0 hasta soltar. **Soltar** dispara y vuelve de inmediato al andar/reposo; **cancelar** o soltar antes de armarse, también. **Volver a pulsar** reinicia la carga desde cero al instante. Mientras carga, el personaje está parado.
  - **Origen:** el rayo sale del **centro del pecho** del frame que se muestra.
  - **Estilo «fuego sagrado»:** sin verde en el jugador (el verde es del láser enemigo). Rampa: rojo sangre → naranja brasa → oro → blanco. Chispas de impacto: oro → naranja → ceniza. **Haz «fuego»:** banda tramada rojo sangre/naranja que se cierra a 1 px y suelta brasas por el borde; listo: línea amarilla de 1 px; disparo: núcleo blanco con amarillo y naranja por fuera.
  - **Efectos desaturados en todos los personajes:** paleta `FX_SH_*` de `source/weapons.c` (marfil cálido, oro viejo, ámbar, terracota, carmesí y sangre oscura, sin primarios puros) para el héroe y **todos los enemigos**. El verde enemigo es una rampa apagada (hueso fosforescente, verdín, musgo, humo); nada de verde ni blanco puros. Lo comprueba `tests/test_guardrails.py`.
  - **Auras de carga:** cada una es el aspecto de una reliquia (§6.12.8).
- **SFX base del Corazón Abierto:** `heart_charge` (400 ms, ignición creciente; se corta si se dispara, cancela o muere), `heart_fire` (280 ms, descarga al soltar con el disparo armado; sin timbre al llegar a cruz), `enemy_hit` (95 ms, pitch ±12 %, cooldown 2 frames), `enemy_death` (250 ms, cooldown 3 frames) y `player_hurt` (420 ms, prioridad máxima). Panning estéreo horizontal según la X del evento respecto a la cámara. Formato: `TECHNICAL.md`.
- **Música de combate:** `cathedral_battle_loop` (21,6 s, 12 compases sin letra ni drops bruscos: tecno industrial + coro grave) en bucle continuo al 42 % de amplitud para dejar espacio a los SFX. Pista de jefe (`nitro:/boss.raw`): se está rehaciendo.

### 6.11 Bestiario / Códice
- **Lore:** los textos de las fichas siguen la biblia del mundo, `LORE.md` (fuente canónica de nombres, cronología y tono).
- **Acceso y visibilidad:** las 5 fichas de la demo están visibles desde el principio, sin desbloqueo progresivo. Se entra desde el botón `CODICE` del menú inicial o de pausa y se vuelve con `B` o el botón táctil `Volver`.
- **Maquetación minimalista:**
  - **Estética:** fondo negro (`#000000`) y borde gris muy fino (1 px) en ambas pantallas.
  - **Pantalla superior (256×192):** ilustración animada en grande (160×160 px, C2) del personaje en su acción característica con rotación en 8 direcciones (`LEFT`/`RIGHT`), centrada dentro del marco y cargada bajo demanda.
  - **Pantalla inferior (256×192):** ficha de texto a ancho completo (nombre sin etiquetas de rol, 1 línea de comportamiento, párrafo breve de lore y cita) con soporte completo de español (tildes y `ñ`), más navegación minimalista (`< Ant`, `Volver`, `Sig >`), controlable con táctil, cruceta o `L`/`R`/`B`.
- **Fichas de la demo (5):** El Corazón Abierto, El Exvoto, El Cireneo, El Ojo del Tribunal y El Abanderado. Cada una lleva su animación en bucle (`corazon_disparo`, `exvoto_walk`, `cireneo_walk`, `ojo_walk_bestiary`, `abanderado_walk`), una línea de comportamiento, un párrafo de lore y una cita. El texto exacto vive en `source/bestiary.c` y se escribe contra `LORE.md`. Citas: Corazón *«No es mi corazón. Solo lo llevo.»*; Exvoto *«Pidieron no estar solos. Les fue concedido.»*; Cireneo *«Ayudó a cargar una cruz. Ahora la cruz le carga a él.»*; Ojo *«La linterna no ve culpables. Los fabrica.»*; Abanderado *«Mientras el asta siga en pie, nadie se retira.»*

#### 6.11.1 Datos de juego en las fichas
El Códice no es solo lore: cada ficha de **enemigo** enseña también cómo se comporta y cómo se le gana. Lo lleva todo enemigo nuevo como parte de su ficha.
- **Maquetación (pantalla inferior, una sola página):** nombre; una fila con tres escalas de marcas, `VIDA`, `VELOC.` y `AMENAZA` (de 1 a 5, marcas llenas y vacías con los colores del Códice); `HACE:` (1-2 líneas); `TRUCO:` (1 línea); y debajo el lore y la cita de §6.11. Si no cabe, se acorta el texto de `HACE`/`TRUCO`, no el lore; si aun así no cabe, se vuelve a preguntar.
- **Escalas derivadas de las tablas, no de memoria:** `VIDA` = vida entre la del Exvoto (hasta 1,25× es 1; hasta 2× 2; hasta 3× 3; hasta 5× 4; más 5); `VELOC.` = su velocidad más alta entre la del Exvoto al andar, con los mismos tramos (la embestida del Cireneo, 1000 frente a 130, es 5); `AMENAZA` = subjetiva, contra el Exvoto, que es el mínimo (1). Son rangos: ajustar un número del juego no obliga a reescribir fichas salvo que cambie de marca.
- **Valores de partida** (vidas del acto I en `include/encounters_act1_hp.h`: Exvoto 250, monaguillo 100, Cireneo 600, Ojo 400, Abanderado 5500; velocidades en `g_enemy_tuning`):

| Ficha | VIDA | VELOC. | AMENAZA | HACE | TRUCO |
| :--- | :--- | :--- | :--- | :--- | :--- |
| El Exvoto | 1 | 1 | 1 (alta en masa) | Te sigue sin parar y, si lo apuntas con el rayo cargado, se aparta a un lado. | Dispara justo tras su esquiva: tarda en repetirla. |
| El Cireneo | 3 | 5 | 3 | Se agacha y embiste en línea recta; no gira durante la embestida. | Dispárale al recuperarse. |
| El Ojo del Tribunal | 2 | 1 | 3 | Se para a distancia, escribe en el suelo una sentencia hacia ti y la ejecuta por la línea fijada. | La línea se congela antes de disparar: muévete. |
| El Abanderado (jefe) | 5 | 1 | 5 | Al verte, invoca monaguillos lentos. | Úsale las columnas; limpia monaguillos. |
- **El Corazón Abierto** (el héroe) no es enemigo: su ficha no lleva bloque de datos y mantiene su línea de comportamiento.
- **El Monaguillo** no tiene ficha propia hasta que exista su lore (`LORE.md`); mientras tanto sus datos van en la del Abanderado.
- **Texto fijo, no generado en ejecución:** los datos de cada ficha se escriben a mano en `source/bestiary.c`; si cambia una IA o una vida, se revisa la ficha en la misma entrega.

#### 6.11.2 Tipografía del juego
Todo el texto que se lee usa **una sola fuente: Palatino de 11 px, con el trazado nítido (hinting) de la propia fuente**, con tildes y `ñ`. Detalle y rondas en `walkthroughs/tipografia/`.
- **Dónde:** fichas del Códice, tarjetas de introducción, pantallas del jefe, título, pausa, controles, subida de nivel (nombres y efecto) y HUD de partida (`Enc. 1 de 15`, `Altura 0 m`, `Tiempo 0:00`, avisos).
- **Mayúsculas:** las etiquetas pasan a minúscula inicial (`Nueva partida`, `Códice`, `Continuar`). Siguen en mayúsculas las etiquetas de datos del Códice (`VIDA`, `VELOC.`, `AMENAZA`, `HACE:`, `TRUCO:`) y el nombre grande del jefe.
- **Fila de escalas del Códice:** marcas de 3 px con paso 5 y hueco de 5 entre bloques, para que `VIDA`, `VELOC.` y `AMENAZA` quepan en el marco.
- **Fuera de alcance:** el contador de FPS y los datos de rendimiento (depuración) siguen en la fuente de 5×7.
- **Aceptado con matices:** el HUD de partida sale más fino y se lee con menos fuerza sobre el suelo con textura; los botones inactivos y la fila de datos del Códice quedan algo tenues. Se pule si molesta en la DS.

### 6.12 Sistema de mejoras del Corazón Abierto
La demo tiene un solo personaje. Las cifras están en `[TUNABLE-PLACEHOLDER]` hasta la sesión de números (§6.12.10).

#### 6.12.1 Filosofía
- **Pool abierto, espíritu *The Binding of Isaac*.** Todas las mejoras conviven en el mismo pool, sin ramas excluyentes. Elegir bien rompe la partida; elegir sin criterio te deja sin nada. Con poco contenido ya tiene que divertir, y añadir mejoras no debe empeorarlo.
- **Builds como en *League of Legends*.** Hay estadísticas que solo valen para unas builds, y la misma mejora vale oro en una partida y es basura en otra. Ejemplo: «carga más rápida» no le sirve de nada a quien juega a mantener el rayo cargado.
- **La build cero crece sumando; las demás, multiplicando.** La Ráfaga (§6.12.3) es fiable desde el primer minuto y tiene techo. Las demás necesitan juntar varias piezas: con una sola están peor que antes (valle) y con tres se disparan. **Cuanto más rota es una build, peores son sus piezas por separado y más hondo es su valle.**
- **Contrapartida solo cuando la mejora rompe una regla del personaje** (por ejemplo, moverse mientras carga). Las demás reliquias son ventaja pura o llevan un riesgo que depende de la habilidad.
- **Frenarse cuesta.** No es un survivors abierto: no se puede uno plantar. Todo lo que frena al héroe es un coste real porque los enemigos te rodean y las salas se cierran.

#### 6.12.2 Reglas comunes
**El rayo base:**
- **Atraviesa a quien mata y se detiene en el primero que sobrevive.** Con poco daño se queda en el primer enemigo duro; con mucho, limpia filas. Atravesar es la recompensa natural de subir el daño.
- **Muros y columnas cortan el rayo y la línea de apuntado**, con chispas en el punto de impacto, como la sentencia del Ojo del Tribunal (§6.10). Lore: es fuego que sale de la carne, y la piedra lo detiene. Las columnas dan cobertura a los dos lados.
- **Alcance base corto,** para que haya que acercarse a la vanguardia (cifra en §6.12.10).

**Dos tipos de daño:**
- **Daño del rayo:** solo el disparo.
- **Daño de fuego:** todo lo demás (quemadura, explosiones, aro, ondas, línea de apuntado).

**Un único estado en los enemigos, «Quemado».** Se acumula en capas. Cada capa hace daño de fuego por segundo y frena un poco al enemigo; seguir quemándolo renueva la duración. Hay un tope de capas. No existe un estado aparte de «ralentizado»: frenar va dentro de Quemado.

**Vocabulario de las mejoras.** Toda mejora, presente o futura, se construye con estas piezas. Así las sinergias salen solas y no se diseñan de dos en dos:
- **Momentos:** al cargar, mientras cargas, al disparar, al impactar, al matar y al recibir un golpe.
- **Toda muerte cuenta como muerte,** también las de explosiones, quemaduras o aros. Así, por ejemplo, Martirio alimenta a Sed de Ceniza sin programarlo aparte.
- **Todo fuego usa el daño de fuego, y todo rayo hereda los modificadores del rayo.**
- **Topes visibles** de capas de quemadura y de explosiones encadenadas, para que una partida rota no baje de 60 FPS en la DS.

**Texto de cada mejora:** icono, nombre y una línea que **empieza por el momento en que actúa** («Mientras cargas: …», «Al matar: …»). Permite aprender las builds leyendo.

#### 6.12.3 Arquetipos
Son una guía de diseño para dar variedad, no ramas ni clases. El jugador no los ve nombrados: los descubre combinando.

| Arquetipo | Fantasía | Cómo mata | Piezas clave | Valle |
|---|---|---|---|---|
| **Ráfaga** (build cero) | La ametralladora: «pa, pa, pa», cada disparo limpia una fila | Daño del rayo y cadencia | Fervor, Prisa, Alcance, Sed de Ceniza, Lanza de Longinos | Ninguno. Es la opción segura cuando vas apurado; con ella se puede pasar el juego, pero tiene techo |
| **Vigilia** | Cargar y no soltar: barrer la pantalla con la línea (de lejos) y quemar lo que se acerca con el aro (de cerca) | Capas de Quemado | Llama Votiva, Aura de Cilicio, Paso de Procesión, Brasa, Rescoldo, Paso | Hondo. Sin el Don de Paso, Procesión va tan lenta que los enemigos te rodean y hay que soltar; sin Brasa, la quemadura hace poco |
| **Mártir** | Kamikaze: vivir a 1-2 corazones a cambio de mucho daño y curarse jugándosela | Todo su daño crece con la vida perdida; se cura matando de cerca | Llaga Abierta, Corazón Flagelado, Viático, Paso | El más hondo. Llaga sola solo quita vida |
| **Puentes** | Mezclan arquetipos | — | Auto de Fe (rayo ↔ fuego), Martirio Contagioso (fuego para Vigilia y Mártir) | — |

#### 6.12.4 Ritmo de la partida
- **Cada relicario normal roto ofrece 1 de 3 Dones**, sin volver a tirar: uno por pasillo, **14 Dones por partida completa** (§6.13.5).
- **3 Reliquias por partida** (1 de 3, pantalla de marco dorado, que se note como el momento especial): una al vencer a cada jefe, en el relicario dorado de su sala (§6.13.5).
- **Ofertas con cabeza:** a partir de la segunda reliquia, al menos una de las tres opciones comparte arquetipo con alguna reliquia que ya tengas. No asegura la pieza que falta, solo que el camino sigue abierto; romper la partida sigue dependiendo de elegir bien y de algo de suerte.
- **Requisitos:** una mejora solo se ofrece si ya tienes lo que la activa. Hoy: Brasa, Rescoldo, Auto de Fe y Martirio Contagioso necesitan una fuente de quemadura (Llama Votiva, Aura de Cilicio o Corazón Flagelado). La primera reliquia de fuego abre ese camino. Toda mejora futura declara su requisito.
- Una reliquia cogida sale del pool. Un Don al máximo deja de ofrecerse; si no queda ninguno, la oferta es curar 1 corazón.

#### 6.12.5 Dones (estadísticas apilables, 7 rangos)
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
| **Lanza de Longinos** | Siempre: el rayo atraviesa a todos los enemigos, mueran o no | Todas | Sin efecto propio: se ve en que el rayo atraviesa a todos | Ninguna |
| **Auto de Fe** | Al impactar: el rayo hace el doble a los quemados y consume sus capas | Puente rayo ↔ fuego | Láser: núcleo del disparo en hoguera; los quemados estallan en chispas al recibirlo | Ninguna |
| **Llama Votiva** | Mientras cargas: la línea de apuntado aplica capas de Quemado a lo que toca | Vigilia de lejos | Láser: la línea de apuntado arde en llamas | Ninguna |
| **Aura de Cilicio** | Mientras cargas: un aro de brasas a tus pies quema a quien entra; crece con la carga | Vigilia de cerca | Aura E, corona de espinas, en el suelo | Ninguna |
| **Paso de Procesión** | Mientras cargas: puedes andar despacio | Vigilia | Cuerpo: anda en cruz mientras carga | Carga más lenta (rompe una regla) |
| **Martirio Contagioso** | Al matar a un quemado: explota con daño de fuego y aplica Quemado alrededor | Puente de fuego | En los enemigos: explosiones | Ninguna; tope de cadena |
| **Corazón Flagelado** | Al recibir un golpe: onda de fuego alrededor y siguiente disparo cargado al instante | Mártir | Onda de fuego al recibir el golpe; aura L, llamas, mientras espera el disparo instantáneo | Ninguna |
| **Llaga Abierta** | Al cogerla: tu vida máxima baja a la mitad. Siempre: todo tu daño sube por cada corazón por debajo de 5 | Mártir | Sangre que gotea y aura pálida dorada: cuantos menos corazones, más gotea y más brilla (no rojo, §6.12.13) | Pierdes vida máxima |
| **Viático** | Al matar con el rayo: probabilidad de robar 1 corazón al enemigo, el doble si estaba pegado a ti | Mártir | Sifón: la vida del enemigo viaja hasta el pecho del héroe; aura G, gloria, al cargar | Ninguna |

**Detalles:**
- **Llama Votiva** quema solo donde apuntas en ese momento; no deja rastro en el suelo (por coste y rendimiento).
- **Aura de Cilicio:** el aro a carga completa es su tamaño máximo. Sin Procesión, mantenerlo te deja clavado y los enemigos te rodean.
- **Paso de Procesión:** para la Ráfaga, la carga lenta es un castigo; para la Vigilia, que no suelta, no cuesta nada.
- **Llaga Abierta:** el bonus de daño se cuenta **siempre respecto a los 5 corazones de partida**, no respecto al tope actual. Subir Vida te protege pero te quita daño.
- **Martirio** solo explota con enemigos quemados: en una Ráfaga pura no hace nada.

**Reserva para la segunda tanda (sin código en la demo):** Ascua Impaciente (soltar antes de tiempo dispara un rayo corto), Óleo Sagrado (disparo instantáneo periódico), Pilar Consagrador (rayo ancho que empuja), Tierra Quemada (la línea deja brasas persistentes; parches con tope) y Reflejo de Penitencia (el rayo rebota 1 vez en los muros). Descartado: Botafumeiro (incensario que gira), redundante con el Aura de Cilicio.

#### 6.12.7 Ejemplos de builds
- **Ráfaga limpia:** Fervor, Prisa y Alcance; Sed de Ceniza y Lanza de Longinos. Cada disparo mata a una fila y la siguiente carga llega casi al instante. Fuerte desde el principio y estable, pero sin explosiones ni cadenas: te lleva al final, no lo rompe.
- **Procesión de fuego (Vigilia):** Llama Votiva, Aura de Cilicio y Paso de Procesión, con Brasa, Rescoldo y Paso. Avanzas con los brazos en cruz arrastrando la línea y con el aro al máximo. Valle: hasta juntar 2 rangos de Paso, los enemigos te rodean.
- **Penitente kamikaze (Mártir):** Llaga Abierta, Corazón Flagelado y Viático, con Paso y Brasa. Vives a 1-2 corazones con el daño al máximo; cada golpe suelta una onda y un disparo instantáneo, y robas vida al matar. Valle: Llaga sola solo te deja con 3 corazones.

#### 6.12.8 Presentación
- **Cada reliquia se ve donde actúa:** los efectos pegados a personajes respetan la oclusión con sus cuerpos, como las auras. No todas son auras: unas son auras del cuerpo, otras cambian el láser o la línea de apuntado, y otras se ven en los enemigos o en el movimiento (columna «Cómo se ve» de §6.12.6). Las cuatro auras de carga son el aspecto de una reliquia cada una: E → Cilicio, H → Sed de Ceniza, G → Viático y L → Corazón Flagelado, y se apilan según lo que lleves. Sin reliquias, la carga muestra solo el rayo. Cada aura tiene un coste fijo por frame: con 3 o 4 apiladas se mide en la DS y, si se pasa, se dibujan las dos últimas cogidas. El selector `Y` solo existe en las variantes de pruebas.
- **Enemigos quemados:** brasas procedurales sobre el cuerpo (más capas, más brasas subiendo) y una lengua de fuego sobre la cabeza al tope de capas; tope global de partículas. Descartados: sprites requemados (doblan el arte y la memoria) y teñir el sprite entero (encarece el paso de dibujo que más pesa). **Fuego en el suelo:** solo efectos breves: el aro del Cilicio y un anillo corto por explosión de Martirio.
- **Pantalla de elección:** estilo Códice (§6.11: fondo negro, borde gris fino). Sobre el juego pausado y oscurecido aparecen **3 cartas en paralelo** en primer plano en la pantalla inferior; la seleccionada se ilumina (borde y brillo) y se adelanta un poco. Cada carta lleva su nombre y un **arte que es una vista previa del efecto tal como se ve en el juego**: una escena de la propia ROM (héroe, efecto y los enemigos que hagan falta, sobre fondo oscuro) capturada en bucle y ampliada 2×, enmarcada al estilo Códice. El efecto completo de la carta seleccionada se lee en una franja de texto. Las reliquias llevan marco dorado. El arte se captura de la ROM y se carga bajo demanda; se regenera cuando cambie un efecto.
- **Ronda A/B/C:** cada elemento visual nuevo se presenta con tres variantes sacadas de la ROM y el usuario elige (formato en `AGENTS.md`). Resultado vigente: §6.12.13.

#### 6.12.10 Cifras vigentes (provisionales)
Se ajustan con la lista que salga de la partida de prueba en la DS. Frames a 60 FPS; distancias en píxeles de suelo; vida en la escala 100 = 1,0 (vidas del acto I: §6.11.1).

**Rayo base:** daño 150 (`source/weapons.c`). **Carga 48 frames (0,8 s). Alcance 110.** Con el rayo inicial lento y corto las primeras salas empiezan justas y el poder se gana con los Dones. **No hay recuperación tras disparar:** al volver a pulsar, la carga empieza de cero al instante; el ritmo lo marca solo la carga. **Prisa llega rápido al tope y se acepta:** el techo es estilo metralleta (carga 8), el principio es lento.

**Dones (7 rangos cada uno):** el efecto total se reparte en 7 pasos (`rank_step` en `source/upgrades.c`). Con 14 Dones por partida y 7 Dones de 7 rangos (49 plazas), no se pueden llevar todos al máximo. **Descartado: limitar a 4 el número de Dones distintos** (estilo Vampire Survivors): cualquier Don puede subirse. **Riesgo a vigilar jugando:** con ofertas aleatorias de igual peso los picks se reparten y las builds pueden quedar planas; palancas: pesos por Don, rechazar una carta o sesgar la oferta hacia lo que ya tienes.

| Don | Por rango | Al máximo |
|---|---|---|
| Fervor | +14 % daño del rayo (15 o 14 según el rango) | +100 % (×2) |
| Prisa | −6 frames de carga (−5 en el 4.º y el 7.º) | carga 8 |
| Alcance | +37 de alcance del rayo y de la línea (36 y 37) | 366 |
| Brasa | +14 % daño de fuego (15 o 14 según el rango) | ×2 |
| Rescoldo | +1 capa de tope en 4 de los 7 rangos y +17 frames de duración (18 en el primero) | 9 capas, 240 frames |
| Paso | +7 % velocidad (también con Procesión) | +48 % |
| Vida | +1 corazón de tope en 4 de los 7 rangos; cada rango cura 1 | 9 corazones |

**Quemado:** tope base 5 capas; duración base 120 frames, que se renueva al volver a aplicar. Cada 15 frames hace 3 de daño de fuego por capa (12 por capa y segundo). Frena un 10 % por capa, hasta un 50 %. Las muertes por fuego no congelan la imagen (sin *hitstop*).

**Reliquias** (la línea de efecto está en §6.12.6):
- **Sed de Ceniza:** cada muerte del disparo resta un 15 % a la siguiente carga (hasta −60 %); un disparo sin muertes suma un 30 %.
- **Auto de Fe:** ×2 a los enemigos con al menos 1 capa y les quita todas.
- **Llama Votiva:** 1 capa cada 8 frames de contacto.
- **Aura de Cilicio:** radio de 12 + 28 × carga (de 12 a 40); 1 capa cada 10 frames a quien esté dentro.
- **Paso de Procesión:** andar al 35 % de la velocidad mientras cargas; la carga dura un 50 % más.
- **Martirio Contagioso:** al morir quemado, explosión de radio 32 con 60 de daño de fuego y 2 capas. Tope de 4 explosiones por frame (las demás esperan).
- **Corazón Flagelado:** al recibir un golpe, onda de radio 48 con 100 de daño de fuego y 3 capas; la siguiente carga llega lista al instante.
- **Llaga Abierta:** vida máxima a la mitad, redondeando hacia arriba (5 → 3); todo el daño (rayo y fuego) +20 % por cada corazón por debajo de 5.
- **Viático:** cada muerte por el rayo tiene un 8 % de probabilidad de robar 1 corazón (16 % si el enemigo estaba a menos de 40 del héroe), sin pasar del tope.

**Pendiente (sesión de números):** alcance base y máximo, tiempos de carga, daño del rayo y del fuego frente a las vidas del acto I, valor por rango de cada Don, capas y duración de Quemado, bonus de Llaga y probabilidad de Viático.

#### 6.12.11 y 6.12.12 Rondas A/B/C (primera y segunda vuelta)
Retiradas: ver `DESIGN-ARCHIVE.md`. Resultado vigente de las tres vueltas en §6.12.13.

#### 6.12.13 Resultado vigente de la ronda A/B/C
- **Enemigo quemado:** A (brasas y lenguas) y B (corona de llamas a los pies) gustan las dos; se decide jugando. El sprite se tiñe según las capas: claro con 1 capa y más rojo con cada una, hasta el tope a las 3–4 capas; se mide el coste en la DS.
- **Llama Votiva:** B, chispas sueltas que giran de forma irregular y procedural (como manchas solares), no una hélice perfecta; se afina más adelante.
- **Corazón Flagelado:** A, anillo grande. **Martirio Contagioso:** A, con el mismo lenguaje por consonancia.
- **Auto de Fe:** A (chispas minimalistas al impactar) y C (la corona de llamas del quemado sube y se evapora al consumirse). Regla: todo efecto nace del mundo (del suelo, del cuerpo o del punto de impacto), nunca flota como un icono.
- **Llaga Abierta:** B, sangre que gotea y aspecto de ascendido (aura pálida dorada); cuantos menos corazones, más gotea y más brilla. No es rojo: es un poder, no un castigo, y el rojo se confunde con el quemado.
- **Viático:** A, hilo de sangre (C, alma pálida, queda como alternativa). Al robar vida, la víctima queda inerte y suspendida ~0,3 s mientras se le extrae el hilo, y luego muere con su animación normal.

#### 6.12.14 Pendiente: efectos de sonido (sesión aparte)
El sistema de mejoras no tiene sonido propio todavía. Faltan, como mínimo: romper un relicario; mover la selección y elegir carta (Don, y Reliquia más solemne); enemigo empezando a arder y tic de quemadura (discreto, con enfriamiento); explosión de Martirio Contagioso; onda de Corazón Flagelado; Auto de Fe al consumir la quemadura; Llama Votiva y Aura de Cilicio (bucles mientras se carga); robo de vida de Viático; Llaga Abierta (latido o goteo según la vida que falte). Se generan con el flujo de `AGENTS.md` (ElevenLabs CLI) en su propia sesión.


### 6.13 Estructura de la partida: la Subida
La catedral infinita no tenía intención; una partida con principio, mitad y final se entiende, se recuerda y encaja con el lore (`LORE.md`: la Columna intentó llegar al Altar y cayó por el camino; Elías hace el mismo recorrido).

- **Duración objetivo: 15–18 min** hasta ganar al jefe final. Referencias: Isaac hasta Mom, 20–30 min en pisos de 3–5 min; Vampire Survivors y Halls of Torment, 30 min. Se queda por debajo porque es una portátil sin guardado a mitad de partida. Si se queda corta en la DS, se alarga cada acto sin cambiar el esqueleto.
- **Columna vertebral: un Vía Crucis de 14 estaciones.** Cada estación es un hito visible en el muro con su número romano (la pieza exacta se decide en la sesión del escenario) y es ambientación: el jugador sabe dónde está y cuánto le falta sin barra de progreso, pero las estaciones no marcan dónde pasan las cosas (§6.13.6). La ROM juega 15 stages con 3 jefes (stages 5, 10 y 15).

| Tramo | Estaciones | Tiempo | Final del tramo |
| :--- | :--- | :--- | :--- |
| **Pórtico** | — | ~0:30 | Entrada tranquila, último campamento de la Columna. |
| **Acto I: la nave** | I–IV | ~5 min | **Jefe 1: El Abanderado** en la estación V. |
| **Acto II: el coro** | VI–IX | ~5 min | **Jefe 2: El Campanero de Ánimas** en la estación X. |
| **Acto III: el Calvario** | XI–XIII | ~5 min | **Jefe final: El Paso** en la estación XIV (el altar). Victoria. |

- **Cada acto es como un piso de Isaac:** cadena de encuentros y pasillos → encuentro con el jefe → respiro y recompensa → el siguiente acto empieza con otro ambiente, más profanado que el anterior (§6.9.1b).
- **Los enemigos entran por actos:** acto I, Exvotos y, en toda sala salvo el atrio, un Ojo; el Cireneo desde las salas medias (§6.13.9). Acto II, se suma el Abanderado como élite. Acto III, todos.
- **Cada jefe vuelve después como enemigo normal (élite):** el Abanderado en los actos II y III; el Campanero en el acto III. El jugador reconoce al que ya venció y la partida tiene memoria. Su versión élite es más débil que la de jefe; las cifras se deciden en la sesión de cada jefe.
- **El escenario se ordena por actos:** tramos hechos a mano para cada acto, en orden fijo y reconocible entre partidas; el azar solo elige variantes dentro de cada tramo. «La catedral que no termina» queda como lore (el altar se aleja), no como mapa infinito.
- **Morir** reinicia la partida desde el pórtico.

#### 6.13.1 Encuentros con jefe
- **En el mismo pasillo, no en una sala aparte.** Al llegar a la estación del jefe:
  1. **Presentación:** pantalla de intro del jefe con un zoom sobre él y su nombre (§6.13.7).
  2. **Sala cerrada:** el jugador no puede avanzar ni retroceder fuera de la sala del jefe hasta que gane o muera. La cámara no se fija: sigue al héroe (§6.13.7).
  3. **Solo el jefe y su escolta:** no aparece nada más en la sala.
- **Encuentro coreografiado (por defecto):** el jefe llega con una escolta definida que se renueva desde arriba según la vas matando; por ejemplo, el Abanderado con varios Ojos y algún Cireneo. Qué escolta lleva cada jefe y a qué ritmo vuelve se decide en su sesión.
- **Alternativa por jefe: el jefe solo,** reforzado para que sea interesante sin escolta. Se elige una u otra en la sesión de cada jefe.
- **Al ganar:** en la propia sala del jefe aparece un **relicario dorado** que da una Reliquia al romperlo (§6.13.5), se abre la barrera superior y se avanza al pasillo siguiente (con relicario normal tras los jefes 1 y 2, o con el Altar tras el jefe 3).
- **El Abanderado** es el jefe fijo del stage 5 y su invocación de monaguillos es la base de su encuentro; repite en los stages 10 y 15 hasta que existan el Campanero y El Paso.

#### 6.13.2 El Campanero de Ánimas (jefe del acto II, dirección inicial)
- **Poder (dirección del usuario, detalle por decidir):** refuerza a los enemigos que tiene alrededor: más fuertes o invulnerables mientras dura el efecto. El toque de campana es la telegrafía (§6.10). El combate pide romper su protección o separar a los enemigos de él antes de atacarlos.
- Lore y ficha del Códice: pendientes (`LORE.md` §9, «Enemigos nuevos»).

#### 6.13.3 Al ganar la partida
- Tras vencer a El Paso aparecen **unas escaleras que bajan a las criptas**: el siguiente nivel. Encaja con `LORE.md` §5 («se puede salir, por abajo»).
- **La partida sigue:** al bajar las escaleras se continúa en las criptas sin cortar la partida, con el mismo personaje y sus mejoras, como Isaac tras Mom. No hay desbloqueo ni guardado en la consola (§6.3). Ganar a El Paso es la victoria de la catedral; las criptas son contenido extra para quien llega.
- **Pendiente:** qué hay en las criptas (estructura, enemigos y jefe), si tienen final propio y qué pasa mientras no existan (por ahora, pantalla de victoria al vencer a El Paso).

#### 6.13.4 Pendiente
1. Poder exacto del Campanero y escolta de cada jefe.
2. Pieza visual de las estaciones y aspecto de cada acto (sesión del escenario).
3. Qué es el Altar y qué encuentra Elías al llegar (`LORE.md` §9).

#### 6.13.5 Ritmo de mejoras en la Subida
- **3 reliquias por partida (una por jefe):** al vencer a cada jefe (stages 5, 10 y 15) aparece un **relicario dorado** en la propia sala del jefe. Al romperlo a tiros se abre la oferta de Reliquia con marco dorado (§6.12.4).
- **Cada jefe es un punto de inflexión de la build.** Las reglas de oferta de §6.12.4 (arquetipo compartido, requisitos, una reliquia cogida sale del pool) valen igual.
- **Dones:** salen de los relicarios normales de los 14 pasillos entre stages (§6.13.6): 14 por partida completa.
- **Altar final:** en el pasillo posterior al último jefe (stage 15), en lugar de un relicario normal, está el Altar; al destruirlo termina la demo («Fin de la demo»).

#### 6.13.6 Escenario por actos: encuentros y pasillos
Los encuentros colocados a mano sustituyen a la marea y la horda aleatoria: el apuntado manual y las coberturas piden enemigos colocados con intención (ADN de *twin-stick*: Enter the Gungeon, Isaac), y se quiere premiar pensar el encuentro y desviarse al relicario.

**Lo que juega la ROM:** 15 stages (encuentros y pasillos) con 3 jefes: El Abanderado en el 5, el 10 y el 15, más el pasillo final del Altar.

**Qué es juego y qué es lore.** El juego se describe con cinco palabras: partida, acto, encuentro, pasillo, pieza. Nave, coro y Calvario son el lore de cada acto y deciden qué piezas usa; el Vía Crucis y sus estaciones son ambientación y no marcan dónde pasan cosas. El pórtico son las primeras pantallas despejadas del acto I.

**Los actos (qué cuentan y cómo se nota).**
| Acto | Capítulo | Sitio | Piezas propias |
| :--- | :--- | :--- | :--- |
| I | La guerra: donde cayó la Columna | La nave | Columna, estatua, bancos, relicario, velas, lápidas, sacos, banco volcado y roto, columna rota y **alambre de espino** (cierra el paso, deja pasar los disparos). Cadáveres de cruzado, más adelante. |
| II | El juicio: el Tribunal y los monaguillos | El coro | Por decidir (candidatas: sillería, rejas, faroles, atril). |
| III | La condena: las cruces de los penitentes | El Calvario | Por decidir (candidatas: cruces, cera derretida). |
- Cada acto está más profanado que el anterior y tiene su propio juego de piezas, que se carga durante el respiro tras el jefe (cada acto tiene su propio presupuesto de tiles).
- El jefe llega por distancia (al final del acto), no por tiempo.

**Estructura de un acto: encuentro, barrera, pasillo.**
- **Encuentro: 2 pantallas de alto** (384 px), diseñado a mano con piezas y enemigos colocados. Las dos pantallas de la DS forman parte del combate: lo de arriba no es «lo que viene», también te dispara.
- **La cámara sigue siempre al héroe** (se apunta en la pantalla de abajo); no hay cámara fija, tampoco en el jefe (§6.13.7).
- **Barrera en el borde de arriba del encuentro** (en el acto I, el rastrillo; en el II, la reja del coro): no se abre hasta matar a todos.
- **Pasillo de ~2 pantallas** detrás de la barrera: colchón para que, estando arriba del encuentro, la pantalla superior no enseñe el siguiente. Al subir por él asoma la parte baja del siguiente encuentro con sus enemigos dormidos (aviso, no revelación).
- **Un encuentro despierta al cruzar su borde de abajo.** Los enemigos despiertos te siguen a cualquier parte. Nada reaparece.
- **Antes de despertar, los enemigos del encuentro no reciben daño** (el rayo los atraviesa), para que no se pueda vaciar un encuentro desde el pasillo sin riesgo.
- **Catálogo:** diseños por acto, encadenados al azar y espejados (izquierda ↔ derecha); el catálogo vigente del acto I está abajo. Cada diseño enseña o examina una cosa.
- **Reglas de oficio:** nunca hacer aparecer un enemigo encima del jugador; avisar de dónde sale cada uno; mezclar 1–2 que disparan con varios cuerpo a cuerpo; acto I con 3–6 enemigos por encuentro, subiendo poco a poco; nunca un hueco cerrado (siempre dos caminos hasta el héroe).
- **Sensación:** como el primer piso de Isaac, fácil si lo entiendes, mortal si vas a lo loco. Encuentros con bastantes enemigos colocados con intención: unos esperan en su puesto (el Ojo y su guarnición) y otros van a por ti.

**Las piezas tienen papel de combate.**
- Columnas y estatuas paran los disparos de todos. Te protegen del Ojo.
- Bancos y sacos paran cuerpos y cargas, no disparos. Los enemigos los rodean (campo de navegación), así que ordenan a la horda en hileras. Pendiente de comprobar: si el Cireneo queda aturdido al chocar con un banco como con un muro (si sí, el banco te protege del Cireneo).
- Bancos destructibles: mecánica candidata, no ahora.
- **Agacharse tras coberturas bajas.** Sin botón (la `L` es el remate, §6.13.8).
  - **Se agacha solo, y solo mientras pulsa hacia la cobertura** (arriba, o arriba con izquierda/derecha si está encima; el lateral si está al lado). Estar pegado a un banco o a unos sacos no basta, así que andar en paralelo a un banco no agacha por accidente. Agachado **anda más lento**, también en diagonal y en paralelo; al dejar de pulsar hacia ella, o al separarse, se levanta.
  - **No dispara agachado:** al tocar con el stylus se levanta y dispara (también mientras carga) y queda expuesto; al soltar, vuelve a agacharse si sigue pegado.
  - **Protege por un solo lado:** un disparo enemigo le pasa por encima solo si cruza la cobertura antes de llegarle; desde su lado le da igual que de pie. Cubre también de la sentencia del Ojo. Los cuerpo a cuerpo le alcanzan igual: el precio es quedarse quieto mientras la horda rodea el banco. Las coberturas altas no cambian nada (ya paran los disparos).
  - Cifras `[TUNABLE-PLACEHOLDER]`: «pegado» = a ≤ 4 px de la huella de la cobertura; velocidad agachado = 50 %; se levanta y se agacha en ~6 frames.
  - Arte: clip «agachado» quieto y andando en 8 direcciones: cadera 15 u más baja y torso más inclinado que el clip de Mixamo (20,8 px de alto frente a 32,3 de pie).

**Relicario en cada pasillo: mejora continua y periódica.**
- Sin gemas ni experiencia. En cada uno de los 14 pasillos entre stages, a un lado, hay un **relicario normal**: al romperlo a tiros da **elegir un Don** (14 por partida completa; las cifras de los Dones se ajustan jugando). Los relicarios decorativos al azar desaparecen.
- **Reliquias:** 3 por partida (§6.13.5), en un **relicario dorado** que aparece en la sala de cada jefe al derrotarlo.
- **Altar:** en el pasillo posterior al último jefe (stage 15), en vez de un relicario normal; al destruirlo termina la demo.

**Daño: varios disparos por enemigo** (vidas en §6.11.1).
| Enemigo | Disparos con el rayo base |
| :--- | :--- |
| Exvoto | 2 |
| Monaguillo | 1 |
| Ojo | 3 |
| Cireneo | 4 |
| Abanderado (jefe) | ~37 |
- **El rayo sigue solo con el daño que le sobra** al matar; si no mata, se para. Con el rayo base, poner a los enemigos en fila ayuda poco; con Fervor vuelve a barrer filas (el poder se gana). La Lanza de Longinos sigue atravesando a todos sin perder daño.

**Enemigos por acto:** ver §6.13. La IA vigente y los papeles: §6.13.9.

**Reglas de IA y colocación.**
- **Todos los enemigos están en la sala desde el principio, como en Isaac,** y despiertan todos a la vez al cruzar el borde de abajo (también los que rezan). Los refuerzos desde arriba (segunda oleada) son un recurso ocasional de las poblaciones duras, no la norma.
- **Más listos, no esponjas de balas.** La dificultad sale de la IA y de la colocación, no de subir la vida a secas. **El Exvoto esquiva el rayo:** si el héroe le está apuntando con el láser de carga, se aparta de la línea, y los de una fila se abren cada uno a un lado para romperla. No anda en línea recta hacia el héroe.
- **El Cireneo, perseguidor que embiste:** anda siempre hacia el héroe a buen paso; cuando lo tiene alineado carga muy rápido y con poco aviso; si choca con una columna, estatua, saco o alambre queda aturdido un buen rato (la recompensa por usar el escenario).
- **El Ojo** solo es difícil cuando hay más presión alrededor; subirle la vida no lo arregla. Diseño vigente: §6.13.9.
- **Salas:** cada planta plantea una sola pregunta y sus tres poblaciones (ligera, media y dura) son versiones más duras de esa misma pregunta.

**Ancho de la catedral: 256 px (una pantalla).** Sin desplazamiento lateral: el encuentro entero se ve y todo el ancho queda al alcance del lápiz; el escenario cuesta la mitad de tiles. Muros de ~24 px por lado (suelo útil ~208 px), columnas pegadas al muro como pilastras. Corte orientativo: paso lateral ~24 + bancos 64 + pasillo central 32–48 + bancos 64 + paso lateral ~24.

**Dificultad: planta y población por separado (como Isaac y Hades).**
- Cada diseño de encuentro es una **planta** (piezas y barrera) con **3 poblaciones**: ligera, media y dura.
- El acto pide los encuentros **por tramos**: primer tercio en ligera, segundo en media, último en dura (acto I: ligera, solo Exvotos; media, se suman el Cireneo y algún Ojo suelto; dura, mezcla completa). El azar elige planta y espejo. Una planta no sale dos veces seguidas y como mucho dos veces por acto (en tramos distintos).
- Cada acto empieza algo por encima de donde acabó el anterior, con su catálogo y sus enemigos nuevos. Último recurso si los Dones corren más que los encuentros: +25 % de vida enemiga por acto.
- Se equilibra jugando la vara de cada población, para que la curva de los encuentros vaya un poco por delante de la del jugador y el jefe sea el examen.

**Catálogo del acto I en la ROM (v2).** La propuesta v3 (7 plantas: el atrio, la procesión, la trinchera, el balcón, la pinza, el claro y la alambrada; la trinchera sustituye al embudo; esquemas en `walkthroughs/encuentros-tacticos/catalogo-salas-v3.html`) está pendiente de programar y se revisa con §6.13.9 y §6.13.10.
| Planta | Piezas | Qué enseña |
| :--- | :--- | :--- |
| **La procesión** | Dos filas de bancos y pasillo central | Los bancos alinean a los Exvotos; cada uno pide dos disparos: retroceder disparando. |
| **El embudo** | Sacos que cierran el centro, un solo paso | Leer y esquivar la carga del Cireneo; estrellarlo contra algo. |
| **El balcón** | Dos columnas arriba (pantalla superior) | Mirar arriba y cubrirse del Ojo; en ligera, Exvotos rezando tras las columnas. |
| **La pinza** | Centro abierto, piezas en los laterales | Dos frentes a la vez; no meterse en medio. |
| **El claro** | Sin bancos, estatuas en las esquinas | Arena abierta para la multitud. |
| **La alambrada** | Alambre de espino que cruza la nave | Los enemigos rodean y tú disparas a través. |
- 6 plantas × 3 poblaciones = 18 encuentros (36 con espejo) para los encuentros de una partida. Ideal a medio plazo: 8 plantas.
- Además: **pasillo** (con relicario a un lado, izquierda o derecha), **pasillo dorado** (el relicario de la primera reliquia), **inicio** (pantallas despejadas) y **pantalla del jefe** (Abanderado).
- Piezas: columna, estatua, banco, sacos, relicario, velas, lápidas, alambre de espino y la barrera que se abre (rastrillo), todas en 3D (abajo).
- **Piezas 3D de las salas** (`walkthroughs/props-catedral-v2/`):
  - **Rastrillo (barrera):** reja de hierro negro que cae hasta el suelo, en el borde de arriba de cada sala y de la del jefe. Está bajado al acercarse; al matar al último enemigo **sube despacio (~0,9 s)** y abre el paso al terminar. La barrera trasera y la de abajo del jefe siguen como franja.
  - **Sacos:** barricadas de tramos pegados que salen de una pared y acaban en un remate en escalón con un saco caído; los tramos alternan recto y con hueco. La colisión es la **huella de apoyo del render** (franja de 4 px donde apoyan los sacos), no la caja del sprite: el héroe se pega a la base por delante y por detrás.
  - **Bancos:** una variante con el **banco roto** sustituye a uno de cada cuatro grupos de las salas, elegido por posición (estable).
  - **Relicario** (templete dorado sobre base baja) en todo el juego. **Columna rota** en «el balcón» (una de las dos). **Alambre** a mitad de altura en «la alambrada».
  - **Simetría izquierda/derecha:** toda pareja simétrica respecto al eje de la nave se coloca por el cuerpo del arte y hornea su fase exacta (`TECHNICAL.md`).

#### 6.13.7 Modo jefe: lógica común
Objetivo: que meter un jefe nuevo sea rellenar una ficha (nombre, retrato, vida, fases y escolta) y escribir su IA, sin tocar la intro, la barra, las fases ni la victoria.

**Secuencia del encuentro.**
1. **Sala del jefe:** un bloque de 2 pantallas (384 px), como un encuentro, con su barrera arriba.
2. **Entrada:** al cruzar el borde de abajo se cierra una barrera también detrás del héroe y empieza la intro.
3. **Intro:** el juego se congela y se presenta al jefe (abajo). Se salta con `START`. Al terminar, entra la música de jefe (§6.10).
4. **Cámara libre:** la cámara sigue al héroe como en el resto del acto; solo se dispara desde la pantalla de abajo, así que fijarla no tiene sentido. El héroe se mueve por toda la sala. Por encima de la barrera de arriba la sala se cierra con una **reja** y, al otro lado, algo decorativo (que no se pueda tocar), para que la pantalla de arriba no quede vacía cuando el héroe sube al borde.
5. **Combate por fases** (abajo).
6. **Victoria:** el jefe muere; desaparecen su escolta e invocaciones; secuencia de victoria; pantalla de reliquia (marco dorado, §6.13.5); vuelve la música normal y se abren las dos barreras.
7. **Morir** durante el jefe reinicia la partida, como en cualquier otro sitio.

**Fases.**
- Cada jefe declara de 1 a 3 fases con el umbral de vida en que empieza cada una (por ejemplo 100 %, 66 %, 33 %). La IA del jefe solo pregunta «¿en qué fase estoy?».
- **Cambio de fase común a todos:** el jefe queda invulnerable ~1 s, se muestra una telegrafía (la misma para todos los jefes) y se renueva su escolta según la fase. Los disparos durante ese segundo no cuentan. La marca de la barra salta rota y aparece el número romano de la nueva fase sobre el jefe.
- La escolta, si la hay, es una lista por fase: qué enemigos, cuántos a la vez y cada cuánto vuelve uno que cae. Con la lista vacía el jefe pelea solo (§6.13.1).

**Presentación del jefe.**
- **Intro:** el juego se congela y la cámara se acerca ×2 al jefe dentro de la sala, en la pantalla de arriba, con un foco que oscurece los bordes. Abajo, la escena a oscuras con su nombre, su título (del Códice) y su frase, que el jefe dice con su voz. Se salta con `START`.
- **Voz del Abanderado:** la voz B de la ronda 2 (`walkthroughs/modo-jefe/assets/voz/`).
- **Barra de vida:** barra fina en la fila de arriba de la pantalla de abajo, desde el borde izquierdo hasta los corazones, **centrada en vertical con los corazones**; el nombre del jefe, debajo. Una marca en cada umbral de fase. Colores de la paleta (§6.10), sin primarios puros. Sustituye a la barra flotante sobre el enemigo durante el modo jefe.
- **Victoria:** la cámara se acerca de nuevo ×2 al jefe y las dos pantallas se destiñen a blanco; abajo, en el mismo sitio que en la intro, su nombre tachado en rojo y su frase de derrota (el Abanderado: «El asta ha caído.»), también con su voz. Después, la pantalla de reliquia.
- **Ficha de cada jefe:** nombre, título, frase de entrada, frase de derrota, sus dos audios, vida, umbrales de fase y escolta por fase.
- **Ritmo de la intro** (~9 s, `[TUNABLE-PLACEHOLDER]`; START la salta): se congela y se ve al jefe ~0,8 s; acercamiento lento ×1 → ×2 con frenada (~1,8 s) mientras se cierra el foco; pausa; aparece el nombre (fundido ~0,5 s) y ~0,4 s después el título; pausa; dice su frase y el texto aparece mientras la dice; ~1,2 s quieto; se aleja (~0,5 s) y vuelve el juego con la música. Cada cosa a su tiempo, con pausas.
- **Ritmo de la victoria** (~8 s): congelado ~1 s; acercamiento lento (~1,5 s); se destiñe (~1,5 s); se tacha el nombre (~0,6 s); pausa; frase de derrota que se escribe; ~1,5 s quieto; reliquia.

#### 6.13.8 Ejecuciones (remates / glory kills)
Mecánica de remate cuerpo a cuerpo para ritmo y recarga en combate:
- **Disparador:** un golpe que no mata y deja al enemigo a **≤ 50 % de su vida máxima** lo deja tambaleándose durante 180 frames (~3 s), quieto y con un pulso cálido de luz marfil/ocre (sin efectos neón, §6.10). Con el rayo base (150 de daño), el Exvoto (250 HP) tambalea tras 1 disparo y el Cireneo (600 HP) tras 2.
- **Activación:** pulsar `L` a media/corta distancia (≤ 96 px de suelo) sobre el enemigo tambaleante más cercano, ejecutando la animación desde la dirección de entrada del héroe (8 ángulos).
- **Flujo:** el héroe queda invulnerable y bloqueado mientras transcurre la animación combinada (72 frames, ~1,2 s), la cámara acompaña suavemente hasta su posición final, y conserva 60 frames (~1 s) de invulnerabilidad con pulso marfil al terminar para reposicionarse. Al terminar, el enemigo muere de inmediato sin efectos estándar y el rayo del héroe queda recargado al instante (sin encender auras de reliquia que no se posean).
- **Variantes:**
  - **Exvoto:** agarre de muñecas, elevación y partición vertical en 96×96, dejando las dos mitades de cera en el suelo durante ~1 s (parpadeando al final).
  - **Cireneo (provisional hasta la ronda final A/B):** el héroe le arranca la cruz de la espalda, salta y lo atraviesa contra el suelo con ella (celda 116×116), dejando el cadáver atravesado en el suelo durante ~1 s antes de desaparecer.
  - **Ojo del Tribunal** (`walkthroughs/remate-ojo/`): el héroe le arranca de un tirón el farol que lleva sobre los hombros (su cabeza) y lo tira al suelo; el cuerpo descabezado se incorpora encorvado y, cuando le llega la patada, cae de espaldas muerto; al caer se le escurre la otra cabeza que lleva en la mano y queda junto al cadáver. Mismas reglas que el resto de ejecuciones (tambalea al 50 %, `L` a ≤96 px, invulnerabilidad en embestida y animación, muerte limpia, rayo cargado al instante, restos ~1 s). 38 fotogramas en 8 direcciones (celda 96×96), 152 frames de juego (~2,5 s).
- **Entrada con embestida previa:** la animación horneada empieza con el héroe a una distancia fija del enemigo (~30 px el Exvoto, ~42 px el Cireneo), pero `L` vale hasta 96 px. Al pulsar `L`, el héroe corre (~4 px por frame, `[TUNABLE-PLACEHOLDER]`, tope ~0,3 s) hasta el punto exacto donde empieza el remate, mirando al enemigo; si ya está más cerca, retrocede ese poco. Durante la embestida es invulnerable y no dispara, y el enemigo deja de tambalearse y espera quieto: el Exvoto se gira hacia el héroe (le agarra de frente) y el Cireneo le da la espalda (el héroe le arranca la cruz por detrás). Al llegar empieza la animación sin salto.
- **Cámara pegada al héroe durante el remate:** la cámara sigue los pies del héroe tal como aparecen en cada fotograma de la animación (interpolados entre fotogramas para que no dé tirones), en vez de deslizarse en línea recta del punto de partida al final.
- **Pendiente de balance:** tunear el alcance de detección, la ventana de tambaleo, feedback y el equilibrio de la recarga instantánea.

#### 6.13.9 Encuentros tácticos: papeles, Ojo sin alcance y remate
Referencias: Doom 2016/Eternal, donde los enemigos débiles cuerpo a cuerpo no son la amenaza sino un recurso que se remata; Gears of War y XCOM, donde unos te clavan en la cobertura y otros te sacan de ella. Esperar abajo no debe salir gratis: la amenaza no llega toda por un lado ni la pelea acaba en la pantalla de abajo con la de arriba vacía.

**Papeles de los enemigos.**
| Papel | Quién | Qué hace en la sala |
| :--- | :--- | :--- |
| **Te clava** | Ojo | Desde su puesto controla la sala con su línea de visión. Mientras te apunta, cúbrete o muévete. |
| **Te saca de la cobertura** | Exvoto | Viene a por ti en grupo y por los lados. Es también el recurso del remate. |
| **Guarda al Ojo y rompe la cobertura** | Cireneo | Espera junto al Ojo y embiste cuando te acercas. Si se estrella contra una pieza queda aturdido y se puede rematar. |
| **Ancla** | Ojo en el acto I; invocador desde el acto II | No baja: obliga a subir para abrir la barrera. |

- **Ojo sin alcance máximo:** solo cuenta la línea de visión; las columnas y estatuas se la cortan. Es un **tirador táctico, no un cazador:** cubierto tras una cobertura baja espera sin moverse ni disparar y, al salir, arranca el ciclo normal de apuntado (el héroe puede esquivar). Tras columnas y estatuas te sigue manteniendo la línea: se recoloca (correa que crece hasta toda la sala). Solo dos apuntan a la vez. Su aviso largo y legible (la sentencia escrita en el suelo) es lo que hace justo no tener alcance máximo. **Palancas sin decidir:** velocidad de persecución y tiempo parado al apuntar (hoy anda a un tercio de la velocidad del héroe). Detalle y constantes: `walkthroughs/ojo-tactico/walkthrough.md`.
- **Guarnición:** Exvotos (y Cireneo desde la media) despiertos que se quedan junto al Ojo hasta que te acercas, los dañas o muere su Ojo. El Cireneo guardián es de guardia, no solo escolta.
- **Exvoto, flanqueo coordinado (sin programar):** se reúnen fuera del alcance del héroe y entran juntos; uno va de frente y los demás por los carriles laterales; si el héroe está agachado tras una cobertura baja, la rodean. Mantienen la esquiva del rayo.
- **Invocador (sin programar):** es un **enemigo nuevo con silueta propia**, no un Exvoto rezando: con el mismo dibujo no se distinguiría a quién disparar primero. Idea: levanta a los caídos si nadie lo interrumpe. Se aplaza al acto II, junto al Campanero y al Abanderado élite. En el acto I el ancla es el Ojo.

**Reglas de sala (se suman a las de §6.13.6).**
1. **Desde el primer momento en que el héroe puede dar a un Exvoto, algún Ojo puede darle a él.** Los Exvotos se colocan entre el héroe y el Ojo, en su línea de tiro.
2. **Los Ojos van en la mitad de arriba,** en su puesto. La cobertura buena (columnas y cobertura baja) va en medio y arriba; la entrada queda despejada.
3. **Composición tipo:** Exvotos arriba que bajan a flanquear, Ojos al fondo y algún Cireneo guardándolos.
4. Nada de embudos rectos hacia la entrada que pongan a la horda en fila delante del rayo.
- **El Ojo en toda sala:** toda sala del acto I salvo el atrio lleva al menos un Ojo, porque es el ancla que obliga a subir. El Cireneo entra en media.
- **El atrio, primer encuentro fijo del acto:** solo Exvotos y espacio abierto; enseña el remate antes de meter presión. Es la única sala sin Ojo. La mecánica de remate existe (§6.13.8); la sala atrio aún no está en la ROM.
- **Sin programar:** flanqueo coordinado de los Exvotos, la sala atrio, el catálogo v3 (§6.13.6) y el invocador.

#### 6.13.10 Método de diseño de salas: una a una
Los sistemas (Ojo, flanqueo, Cireneo guardián, remate) se prueban **a través de salas concretas**, no en bloque: así el feedback es claro y la programación va atada a una prueba.
- **Una sala, una pregunta.** Cada sala se juega unos minutos con una sola pregunta y acaba en un veredicto: se queda, se cambia o se descarta. El registro vive en `walkthroughs/sala-<nombre>/plan_pruebas.md`.
- **Equipo de referencia fijo por sala** (la vara de medir, no todas las combinaciones): primera sala ligera, sin Dones; sala media, ~4 Dones de un equipo tipo; sala dura, ~8 (de 14 por partida completa; `[TUNABLE-PLACEHOLDER]`). El equipo tipo se elige una vez con el usuario y no se toca. Que un equipo muy fuerte arrase una sala no es fallo de la sala; los Dones que rompen todas se buscan con el bot (`encuentros-bot`).
- **Orden por mecánica nueva:** 1) la procesión ligera (Ojo con puesto fijo, cobertura baja); 2) el balcón (columnas y flanqueo); 3) la primera sala media (Cireneo guardián); después el resto del catálogo v3. El atrio entra cuando se programe, sin prioridad: es un tutorial.
- **Pasadas por sala:** como mucho dos (equipo de referencia; sin Dones en el atrio y la primera ligera). Un cambio por vuelta.
- **Primera prueba: partida de referencia.** Antes de rediseñar nada se juega la ROM actual 10 min puntuando cada sala (tensión, decisión, ¿repetir?) para tener una línea base de diversión y saber qué sala rediseñar primero. Plan en `walkthroughs/sala-atrio/plan_pruebas.md`.
