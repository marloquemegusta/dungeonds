# DESIGN.md - Documento de Diseño

> **Estado vigente (revisado 2026-11-19).** Lo que describe este documento y la ROM por defecto, de un vistazo. El texto histórico (v0.1, v0.2, la franja infinita y la marea) está en `DESIGN-ARCHIVE.md`.
> - **Partida:** el Acto I por encuentros (§6.13.6): salas hechas a mano de 2 pantallas, barrera que se abre al limpiar, pasillo con relicario y jefe al final. Sin marea, sin horda continua, sin gemas ni experiencia. La ROM juega 14 stages con 3 jefes: El Abanderado en el 5, el 10 y el 14.
> - **Mejoras:** se rompe un relicario por pasillo y se elige un Don; la reliquia, en el relicario dorado a mitad del acto y al vencer a cada jefe (§6.12, §6.13.5, §6.13.6).
> - **Rayo del Corazón Abierto:** se carga y se suelta; al volver a pulsar la carga empieza al instante, sin recuperación tras el disparo (§6.10). El ritmo lo marca solo el tiempo de carga.
> - **Enemigos:** Exvoto, Cireneo, Ojo del Tribunal y Abanderado (jefe) con las vidas de `include/encounters_act1_hp.h` (§6.11.1).
> - **Acciones:** cruceta mueve; lápiz apunta y carga; `L` remata (§6.13.8); agacharse tras coberturas bajas es automático (§6.13.6).

## 1. Visión y Alcance
- **Concepto:** survivors de frente vertical para Nintendo DS, con apuntado manual y tono gótico/grimdark (el Corazón Abierto y otros futuros personajes contra los caídos de la Cruzada). Referencias: Halls of Torment y Vampire Survivors por el bucle; Diablo y Warhammer 40K: Inquisitor por lo que engancha al usuario (ir a la siguiente misión y mejorar); Isaac por la dificultad (lo normal es morir pronto hasta conocer las mejoras).
- **Pilar:** combate de Doom en isométrico (cada personaje con un arma contundente y mucho *feel*, esquivar con strafe), contra enemigos colocados con intención en salas que hay que abrirse a tiros. Las dos pantallas forman un campo vertical: la superior es parte del combate (también te dispara) y se puede apuntar a ella.
- **Bucle vigente (decidido 2026-11-16 y 2026-11-17, §6.13):** una subida de 15–18 min por un Vía Crucis de 14 estaciones en tres actos, con un jefe al final de cada uno. Cada acto es una cadena de encuentros (sala cerrada que se abre al limpiarla) y pasillos con un relicario que da un Don. Personaje = arma única. Hoy solo existe el Acto I y El Abanderado como jefe (repetido en los stages 10 y 14).
- **Fantasía:** la Columna intentó llegar al Altar de una catedral que no termina y cayó por el camino; el jugador hace el mismo recorrido (`LORE.md`). Los personajes, enemigos y mapas actuales son una primera versión con la estética buena; el sistema debe aguantar cambiarlos.
- **Fuera de la prueba, a propósito:** progresión entre partidas (equipo, desbloqueos), más de un personaje y más de un acto con contenido. La capa de equipo es el gancho a largo plazo (Diablo) y se diseña tras validar que una partida divierte.
- **Historia de la dirección:** nació como un Diablo de nigromancia con esbirros y pasó por arenas (v0.1), mazmorra de manadas (v0.2) y survivors con marea y horda (v0.3). El 2026-11-16 se sustituyó por salas a mano (encuentros, §6.13.6) porque el apuntado manual y las coberturas piden enemigos colocados con intención. Detalle en `DESIGN-ARCHIVE.md`. La lanza ósea y la muerte por fragmentos quedan como FX reutilizables.

## 2. Dirección de Arte y Pipeline
- **Técnica:** sprites 2D pre-renderizados a partir de modelos 3D con animación esquelética (FBX/GLB), **sin outline** en personajes, enemigos ni piezas de escenario.
- **Proyección:** isométrica/dimétrica en 8 direcciones; mapa y personajes con la misma cámara e iluminación.
- **Herramienta de render única:** el lab Three.js (`tools/lab/`), fuente de verdad visual para mapa y personajes; no abrir vías de render paralelas en Blender/Python salvo prototipos temporales marcados como tal. Detalle del pipeline en `TECHNICAL.md` §3.
- **Regla de personaje:** **1 personaje = 1 arma**; cualquier selector de armas, auras o animaciones en la ROM actual es solo herramienta de depuración.
- **Personajes actuales:** héroe (El Corazón Abierto) y enemigos Exvoto, Cireneo v2, Ojo del Tribunal y Abanderado (§6.10). El esqueleto y el tirador necrón ya no aparecen en el juego.
- **FX reutilizables:**
  - Lanza ósea: salva de cinco astillas estrechas y puntiagudas dibujadas proceduralmente, sin outline, con motas en tonos marfil/hueso.
  - Muerte del enemigo: la silueta se rompe en fragmentos extraídos de sus propios píxeles que salen según el impacto y caen con una parábola breve.

## 3. Decisiones de plataforma y abiertas
- **Actores detrás de muros (decidido 2026-11-10):** personaje y enemigos se ocultan según la profundidad horneada; no parpadean ni reciben transparencias, siluetas o marcas negras auxiliares cuando quedan detrás. La base caminable no se dibuja sobre el muro.
- **Sombras de personajes por hardware (decidido 2026-11-13, rama `perf/hw-shadows`):** la sombra de héroe y enemigos conserva la forma horneada del lab por dirección y frame y su tono (suelo al 50 %), pero la oscurece la propia consola en vez del procesador. Diferencias aceptadas: dos sombras solapadas se funden en un solo tono; si un enemigo queda detrás de una pieza o muro, su sombra se oculta entera en vez de recortarse; las marcas de suelo de las armas no quedan oscurecidas por las sombras. Motivo y mediciones: `walkthroughs/stress-enemies-profiling/`. Medido en la DS, la separación entre enemigos se conserva.
- **Sonido:** SFX base del héroe y música de combate hechos (§6.10); los de mejoras, pendientes (§6.12.14).
- **Por decidir (estructura, §6.13.4):** poder del Campanero y escolta de cada jefe, pieza visual de las estaciones y aspecto de cada acto, qué es el Altar.

---

## 4. Game feel y efectos de armas

> Esta sección era la prueba de diversión mínima de la v0.1. Solo siguen vigentes el game feel (§4.7) y la regla de perspectiva del suelo (§4.9); el resto se archivó.

> **Archivado.** Controles, jugador, armas (escopeta y francotirador), cargador, tirador y arenas de la prueba v0.1. Vigente hoy: un solo personaje con un solo rayo (§6.10, §6.12). Texto en `DESIGN-ARCHIVE.md`, «§4.1–4.6».

### 4.7 Game Feel
- **Al impactar:** hitstop de 2–4 frames y destello blanco del enemigo.
- **Al disparar:** temblor de pantalla proporcional al disparo.
- **Origen del disparo:** proyectiles, fogonazo y línea de mira salen de la boca del arma, no de los pies del personaje. El punto de boca por dirección lo exporta el lab junto al spritesheet; el runtime no usa offsets escritos a mano.
- **Aspecto del disparo (decidido 2026-11-03):** procedural, en la línea de la lanza ósea: fogonazo de 2–3 frames en la boca y chispas de impacto como líneas que salen según la normal y se apagan.
- **Ambas pantallas iguales:** la pantalla superior dibuja lo mismo que la inferior (suelo, actores, sombras, proyectiles enemigos y FX del disparo) desplazada una pantalla hacia arriba, para poder ver y apuntar a lo que queda fuera de la pantalla táctil (decidido 2026-11-03, tras probar en la DS). Solo la inferior lleva el HUD de depuración.
- **Muerte:** fragmentos (FX existente, §2).
- **Al recibir daño:** destello rojo e i-frames.

### 4.9 Perspectiva del suelo y presupuesto de efectos
- **Perspectiva del suelo (regla, decidida 2026-11-05):** todo lo que está *en el suelo* (marcador de apuntado, anillos de aviso, charcos, ondas de choque, el aro del Cilicio) es una elipse 2:1 en pantalla (semieje horizontal R, vertical R/2) y se pinta **en el suelo, bajo sombras y personajes** y respetando los muros (`groundfx`, pase de suelo). Lo que tiene volumen (fuego, escombros, humo, destellos) se dibuja encima.
- **Oclusión por el personaje (regla común):** lo que nace en la mitad trasera de la elipse 2:1 se pinta antes del sprite y lo tapa el cuerpo; lo delantero, después.
- **Sin transparencias:** los bordes suaves se hacen con tramado.
- Historia (granada, variantes A/B/C, aura y colimado del francotirador) en `DESIGN-ARCHIVE.md`.
- **Presupuesto:** ninguna variante puede bajar de 60 FPS en la DS (`AGENTS.md` regla 6). Se descarta la que no lo cumpla.

> **Archivado:** plan por fases de la v0.1 (`DESIGN-ARCHIVE.md`, «§4.8»).


---

> **Archivado.** La v0.2 (mazmorra de manadas con modificadores) quedó sustituida por la v0.3 y, después, por los encuentros (§6.13.6). Texto íntegro, con el feedback de su primera prueba, en `DESIGN-ARCHIVE.md`, «§5».


---

## 6. El juego: diseño vigente

**Por qué.** La v0.2 divierte un par de minutos, pero después no hay nada que hacer: el mapa y las manadas son fijos, los modificadores son números y morir no deja nada. Faltaban una run que cambie y una meta. El usuario quiere la dificultad de Isaac (morir mucho hasta dominar las mejoras), el gancho de Diablo (siguiente misión, mejor equipo) y una fantasía clara con entorno cambiante. El bucle de Halls of Torment y Vampire Survivors junta las tres cosas, y el giro vertical lo adapta a la DS. La partida vigente es la de §6.13.

> **Archivado:** hito 0.3 mínima (franja infinita, marea, curas). `DESIGN-ARCHIVE.md`, «§6.0».

> **Archivado:** bucle de la prueba de 8 min. Vigente: §6.13. `DESIGN-ARCHIVE.md`, «§6.1».

> **Archivado:** franja de 512 px por tramos. Vigente: ancho 256 y encuentros (§6.13.6). `DESIGN-ARCHIVE.md`, «§6.2».

### 6.3 Cámara y pantallas
- **Cámara con adelanto vertical (*look-ahead*, decidido 2026-11-14):** en lugar de centrar al jugador en el 50 % de la pantalla inferior, el encuadre se adelanta suavemente según el sentido de marcha vertical:
  - **Al subir:** coloca al jugador en el tercio inferior (~69 %, ~132 px de vista delante y ~60 px detrás en la pantalla táctil).
  - **Al bajar (retroceder):** desliza la vista hacia atrás hasta dejar al jugador en el tercio superior (~33 %, ~128 px de vista detrás para retroceder con comodidad), **salvo si está apuntando hacia delante con el stylus (*kiting*)**, en cuyo caso mantiene la vista al frente.
  - **Al parar o hacer *strafe* lateral:** la cámara mantiene el último encuadre (no vuelve sola al centro), y requiere ~0,37 s (22 frames) de marcha vertical sostenida antes de empezar a deslizarse (a 2 px/frame) para que los esquives cortos no muevan el suelo bajo el stylus.
- **La pantalla superior es la vanguardia, no un menú:** muestra la parte de arriba de la sala, con enemigos que también te disparan, y avisos del jefe. Se le puede disparar con el apuntado por vector (el lápiz apunta desde el personaje, aunque el objetivo quede fuera de la pantalla táctil).
- Los menús, como la elección de Don, van en la pantalla inferior.
- **Menú inicial y menú de pausa (decidido 2026-11-14):**
  - **Reparto entre pantallas:** la pantalla superior muestra únicamente la catedral de fondo (sin título ni adornos); la pantalla inferior (táctil) muestra la catedral por detrás con un tinte oscurecido y el menú encima.
  - **Estilo minimalista:** cajas semitransparentes oscuras con texto plano sobre la catedral oscurecida, usando la paleta `FX_SH_*` (marfil y oro/carmesí apagado para la opción activa, ceniza para las inactivas), sin marcos ni títulos postizos.
  - **Navegación (ambos):** táctil con lápiz sobre cualquier botón y cruceta (`Arriba`/`Abajo`) + `A` (confirmar) / `B` (volver o reanudar en pausa). `START` abre y cierra la pausa durante la partida (cuando el jugador sigue vivo; tras morir conserva el reinicio).
  - **Menú inicial (al arrancar la ROM):** `Nueva partida`, `Códice` y `Controles`.
  - **Menú de pausa (`START` en partida):** `Continuar`, `Reiniciar`, `Códice` y `Controles`. Congela combate y música (sin coste por frame durante la partida activa). Los controles de comparación de efectos (`SELECT`, `Y`) solo existen en las variantes de pruebas (§6.5).
  - **Submenús:** `Códice` abre el códice de personajes (§6.11); `Controles` muestra los controles de §6.5 (cruceta, lápiz, `L` y `START`) y un botón `Volver`.
  - **Tarjetas de introducción (decidido 2026-11-14, rama `feat/intro-tarjetas`):** al elegir `NUEVA PARTIDA` se muestra una secuencia de 6 tarjetas antes de empezar; no aparece al reiniciar desde la pausa.
    - **Maquetación (como el códice, §6.11):** fondo negro y borde gris de 1 px en ambas pantallas. Arriba, un **bucle de vídeo de la pantalla inferior del juego real** (256×192 completa, ~2 s a 30 imágenes por segundo, guardado sin pérdida en NitroFS, cargado bajo demanda como los retratos del códice). Los clips se graban en escenas montadas del sandbox (`tools/clip_scene.py`) y de la ROM `encuentros` (relicario). Descartado por ahora: ejecutar el juego en directo dentro de la tarjeta (mejora futura, solo cambiaría esta ilustración). Abajo, título y texto corto en español con la fuente del códice.
    - **Botones (pantalla inferior):** `SALTAR` siempre visible, que empieza la partida al instante (también con `START`); `< ANT` y `SIG >` para moverse (lápiz, cruceta o `A`/`B`; `R` avanza como derecha y `L` retrocede como izquierda). En la última tarjeta `SIG >` pasa a `EMPEZAR`.
    - **Tarjetas (vigentes, `feat/intro-tarjetas`, 2026-11-19):** 1) **La catedral.** 2) **Moverse y apuntar:** la cruceta mueve; el lápiz apunta y mantenerlo pulsado carga el disparo. 3) **Coberturas:** agacharse tras bancos y sacos (§6.13.6). 4) **Rematar:** `L` sobre un enemigo tambaleante (§6.13.8), con la aclaración de las invulnerabilidades del remate y del golpe. 5) **Relicarios:** romperlos da un Don. 6) **Vida:** 5 Sagrados Corazones. El texto exacto vive en la ROM. Pendiente: la rotura del relicario se ve poco (la oferta de Don la tapa).
    - **Sin memoria entre sesiones:** no hay guardado en la consola, así que siempre sale; `SALTAR` es el atajo.

> **Archivado.** Ni la marea ni la horda continua existen en la partida por encuentros (§6.13.6). Siguen en las variantes de pruebas antiguas. `DESIGN-ARCHIVE.md`, «§6.4».

### 6.5 Personaje y controles
- **Personaje = arma única.** Cada personaje tiene su única arma fija: El Corazón Abierto, su rayo de fuego sagrado. Otra clase sería otro personaje. Hoy solo hay uno.
- **Controles vigentes:**
  - Cruceta: mover. Se agacha solo tras coberturas bajas (§6.13.6).
  - Lápiz: apuntar por vector; mantenerlo pulsado carga el rayo y al soltar dispara. Al volver a pulsar, la carga empieza de cero al instante (§6.10).
  - `L`: remate sobre el enemigo tambaleante más cercano (§6.13.8).
  - `START`: pausa (§6.3).
- **Controles de depuración (solo en variantes de pruebas, no son del juego):** `SELECT` (estilo de efectos A/B/C), `Y` (aura de carga L/G/E/H), el ciclo de armas de la v0.1 y los cambios de animación en vivo.
- **Vida:** 5 golpes de partida más i-frames; el Don de Vida sube el tope. Los relicarios ya no curan.

### 6.6 Mejoras
- **Sin gemas ni experiencia** (decidido 2026-11-16, §6.13.6). Las mejoras salen de romper un relicario por pasillo, que abre la pantalla de elección de **1 de 3 Dones**; las Reliquias, en el relicario dorado y al vencer a cada jefe (§6.13.5).
- **Dones** (estadísticas apilables) y **Reliquias** (únicas, cambian cómo se juega), diseñados por arquetipos en §6.12.
- **Presentación:** cada mejora se muestra con icono, nombre y su efecto en una línea. Es la lección de la v0.2, donde los modificadores parecían aleatorios porque solo se veía el nombre.
- **Cofres de élite:** descartados por ahora; el relicario ocupa ese lugar.

> **Archivado:** escalones de enemigos (enjambre, élite, minijefe) y reutilización de la v0.3. Vigente: §6.10 y §6.13.9. `DESIGN-ARCHIVE.md`, «§6.7 y §6.8».

### 6.9 Hoja de ruta por versiones (estado a 2026-11-19)
Cada versión se construye en su sesión y su rama y se cierra con el cierre de `AGENTS.md`. Las que traen comportamiento nuevo empiezan con una sesión de diseño que lo deja escrito aquí (regla 9).
Las versiones 0.3 mínima, 0.3.1 y 0.5 (horda y élites) están cerradas o absorbidas; su historia está en `DESIGN-ARCHIVE.md`.

| Versión | Contenido | Estado |
| :--- | :--- | :--- |
| **0.3.2 escenario** | Catedral: suelo en rombos, lápidas, muros, piezas 3D, godrays. | Hecha; el escenario infinito se sustituye por las salas de §6.13.6 y las piezas del acto I son 3D (`walkthroughs/props-catedral-v2/`) |
| **0.3.3 personajes** | Corazón Abierto, Cireneo v2, Exvoto, Ojo del Tribunal, Abanderado y monaguillo. | Hecha; faltan el Campanero y El Paso |
| **0.4 progresión** | Dones y Reliquias (§6.12). | Hecha, pero la fuente de mejoras ya no son gemas sino relicarios (§6.13.6) |
| **0.6 estructura** | La Subida de §6.13: tres actos con jefe. | **En curso:** Acto I por encuentros, modo jefe y remate integrados; faltan actos II y III y dos jefes |

Escala de vida y daño en centésimas, 100 = 1,0 (sin `float`, `AGENTS.md` regla 2); las mejoras multiplican en porcentaje. Las vidas vigentes del acto I están en §6.11.1 y en `include/encounters_act1_hp.h`; las cifras de la 0.3.1, en el archivo.

> **Archivado:** valores de la 0.3.1 y enemigos de esa versión (cerrada 2026-11-07). Las vidas vigentes están en §6.11.1 y en `include/encounters_act1_hp.h`. `DESIGN-ARCHIVE.md`, «§6.9.1».

#### 6.9.1b Dirección de arte: escenario y personajes (decidido 2026-11-07 a 2026-11-14)
No traen mecánicas nuevas. La parte de compositor, tramos y presupuesto de tiles está en `TECHNICAL.md`; la historia de cada ronda, en `DESIGN-ARCHIVE.md`.
- **Estilo:** tipo Trench Crusade o Warhammer 40k, pero más sucio y sombrío: metal oxidado y gastado, fe fanática, reliquias, desgaste. Hilo conductor: «la Cruzada que no terminó»; los enemigos son los caídos de esa cruzada, con ficha diegética en el Códice (§6.11).
- **Nivel 1: una catedral** gótica oscura (Warhammer 40k, Trench Crusade, Blasphemous). Se sube por una nave hacia un altar que se aleja; la guerra se metió dentro (bancos en barricada, sacos, alambre, cruzados muertos). El orden de los biomas posteriores sigue abierto.
- **Coberturas bajas: bloquean el paso, no el fuego, y ocluyen.** Terreno (losas, alfombra, sangre, cera): solo decorativo. **Piezas altas (decidido 2026-11-16, rama `fix/cobertura-estatuas`):** columnas y estatuas (`santo`) paran todos los disparos, el rayo del jugador y el del Ojo, y cortan la visión del Ojo. Bancos, relicario y velas solo bloquean el paso.
- **Color y legibilidad (2026-11-08):** sin colores reservados; la legibilidad se basa en el contraste de luminancia: suelo transitable tranquilo, de valores medios-bajos y poco contraste local; el detalle fuerte en bordes, muros y piezas.
- **Suelo de la nave:** damero de losas cuadradas giradas 45° que alternan dos piedras pardas casi iguales (rombo de 32×16 px), modeladas en 3D y renderizadas con la cámara del juego. **Lápidas v5 (2026-11-11):** la piedra tallada ocupa el bloque entero de losas (3×2 o 2×1), a ras del suelo y con la cabeza al fondo de la pantalla; la retícula real del damero y el proceso están en `tools/catedral_editor/gen/README.md`.
- **Muros, perspectiva y luz (2026-11-11):** todo se ve con la cámara del juego (ortográfica, 30°, mirando a lo largo de la nave); nada de alzados frontales pintados. Muros con el módulo 3D `gothic_arch` repetido; muros y columnas suben hasta un techo que no se dibuja. Las vidrieras y rosetones no se dibujan: se ven por su luz, que entra horizontal desde la cara interior del muro. El ancho y la planta de las salas son los de §6.13.6.
- **Sombras de las piezas (2026-11-08):** proyectan sombra como los personajes, con la dirección de la luz principal del lab, horneada en los tiles de la estampa (sin coste por frame). Las lápidas, planas, no llevan.
- **Luz única «Neutra» y sin contorno (2026-11-08):** piezas, suelo y personajes se renderizan con el preset «Neutra» (`tools/props/props_render_settings.json`) y los personajes van sin contorno. Pre-render de personajes «C2» (2026-11-14): supersampling ×4, tono neutro, curva S suave, bordes al 30 % de cobertura y enfoque suave; evidencia en `walkthroughs/legibilidad-lab/`.
- **Escala única (2026-11-07, corrige `TECHNICAL.md` §4.1):** el héroe mide 2 m y ocupa 31 px de alto, así que el mapa se dibuja a ~17,9 px/m y los enemigos de 1,5 a 3 m miden 23–46 px (el Abanderado, ~3 m, unos 54 px en celda de 60×60). Una baldosa de 32×16 px = 1,8 m.
- **Método:** el suelo es un juego de tiles diseñado, no un render troceado. Las piezas (bancos, columnas, estatuas, relicarios, sacos) siguen el flujo de los personajes: imagen de IA, 2D→3D (Tripo), render con la misma cámara y luz, estampa alineada a 8 px con su huella de colisión y profundidad de oclusión. Flujo completo en `walkthroughs/v032-escenario/BIBLIA.md`. Presupuesto de tiles: `TECHNICAL.md` §3.
- **Cierre:** el escenario se ve bien en la ROM real y 60 FPS en la DS (regla 6).

> **Archivado:** demo para un colega y borradores de las versiones 0.4, 0.5 y 0.6. Vigente: §6.12 (mejoras), §6.13 (estructura). `DESIGN-ARCHIVE.md`, «§6.9.1c y §6.9.2–6.9.4».

### 6.10 Reparto de la demo (sesión de concepto, 2026-11-11)
Conceptos para la demo de la catedral. Solo cambia el aspecto y se añaden élites y jefe; las mecánicas base son las de las fichas de §6.11.1 y la IA de la ROM. Nada de esto se programa hasta que su detalle esté escrito aquí (regla 9).

- **Personaje (clase láser): El Corazón Abierto** (pecho abierto con grapas de hierro y un sagrado corazón en llamas dentro; carga con los brazos en cruz y el rayo sale del pecho). Las otras dos propuestas, El Lector y La Custodia, quedaron en reserva (historia en `DESIGN-ARCHIVE.md`). Prompts y pendientes: `walkthroughs/concepto-demo-personajes/`. Mecánica: cargar, soltar, rayo que atraviesa filas (desde 2026-11-15 atraviesa a quien mata y lo cortan muros y columnas, §6.12.2). El rayo no es un arma sino un milagro que consume el cuerpo: sale del propio personaje, que va quemado por usarlo y sigue vivo por fe (tono Trench Crusade). A 31 px el origen del rayo debe ser un punto de luz claro y la carga una pose que cambie la silueta. Las imágenes para 3D se generan en **T-pose, con las manos vacías**, y el arma en una imagen aparte.
- **Color de personajes (decidido 2026-11-12):** todos los personajes, protagonista y enemigos, llevan **acentos negros y rojos** por legibilidad; la base de cada uno (cera, piel, metal) y los brillos (dorado del corazón, verde de los caídos) se mantienen.
- **Enemigos (revisado 2026-11-12):** son los caídos de la Cruzada, gente cuya fe se pudrió. **Cada uno hizo un pacto:** entregó algo de sí mismo a cambio de un poder, el precio se ve en el cuerpo y es su debilidad en el juego; su luz es **verde enfermiza** frente al dorado anaranjado del Corazón Abierto.
  - **Masa → Los Exvotos:** devotos convertidos en figuras de cera de tamaño humano, en procesión lenta con cirios fundidos en las manos. Se derriten al morir.
    - **Aspecto y animaciones (decidido 2026-11-14):** monja de cera con velo negro y faja roja (`assets/models/characters/exvoto/source/`, Tripo con rig Mixamo). Llevan las **manos juntas rezando** en lugar de cirios; las velas pasan a ser atrezo del mapa junto al que rezan. Clips: **rezar de pie** (bucle), **rezar de rodillas** (bucle), **levantarse** (de rodillas a de pie) y **andar rezando** (andar genérico de procesión con los brazos fijos en la pose de rezo, cuerpo encorvado y cabeza baja). Fuentes de rezo: clips de Mixamo en `assets/models/animations/pray/`.
    - **Comportamiento «en oración» (decidido 2026-11-14; cifras `[TUNABLE-PLACEHOLDER]`):** los Exvotos empiezan quietos rezando de rodillas (desde 2026-11-15, ver «Postura»), repartidos un poco al azar pero con sentido en el mapa: junto a velas, frente a rosarios u otro atrezo devoto. Al empezar el encuentro despiertan y andan hacia él (§6.13.6; los arrodillados se levantan primero).
    - **Exvoto en el juego (decidido 2026-11-14, rama `feat/exvoto`):** colocado a mano en cada sala (§6.13.6); su vida es la de §6.11.1 (250). Sustituyó al esqueleto.
      - **Postura (decidido 2026-11-15):** los que nacen rezando lo hacen de rodillas y se levantan al despertar. El rezo de pie sigue en la ROM (`EXVOTO_KNEEL_PERCENT`) pero no se usa.
      - **Despertar:** todos a la vez al cruzar el borde de abajo del encuentro (§6.13.6). La arrodillada reproduce *levantarse* (~70 frames de clip, sin moverse) y luego anda; la de pie anda al instante.
      - **Andar:** clip *andar rezando* hacia el héroe, con la esquiva del rayo de §6.13.6.
      - **Muerte («se derrite»), sin animación 3D nueva:** el sprite se hunde y se aplasta en ~20 frames y deja un **charco de cera** en el suelo (elipse 2:1 clara con borde oscuro, colores desaturados) que dura ~90 frames, se desvanece y no hace nada.
  - **Cargador → El Cireneo:** entregó sus brazos a cambio de la fuerza de la cruz. Es un gigante crucificado que camina: brazos clavados al travesaño y cruz atornillada a la espalda. Embiste encorvado con la cruz por delante y no puede girar; al chocar con una columna la cruz se clava y forcejea para sacarla (aturdimiento y marca visual). Los brazos van fijos en la pose del T-pose.
  - **Tirador → El Ojo del Tribunal:** inquisidor con una linterna de vidrio verde enjaulada en lugar de ojos; su láser es su mirada (sigue, se fija, sentencia).
    - **Aspecto (decidido 2026-11-14):** **bajo y gordo**, túnica **morada oscura** (no negra) con faja roja, pliego blanco y sello de lacre. Motivo: que no todos los caídos sean altos y delgados (silueta reconocible entre los demás) y que el cuerpo se separe del suelo oscuro y de los demás enemigos. El Ojo debe leerse visiblemente más grande que el protagonista (objetivo aproximado: +40 % de altura). En juego el sprite pasa de 40×40 a 56×56 px (140 %) y el volumen de impacto acompaña la escala; la sombra de suelo conserva su huella actual. Modelo definitivo en `assets/models/characters/ojo/source/` (farol en lugar de cabeza, sin capucha); quedan descartados el gordo con capucha (`source_capucha/`) y el alto y delgado (`source_delgado/`).
    - **Cabeza en la mano (actualizado 2026-11-14):** antes interrogaba alumbrando a los reos con un farol en la mano; el pacto intercambió las dos cosas. El **farol** ocupa ahora su cabeza y vigila sin descanso; con el brazo extendido, donde llevaba el farol, sostiene **su propia cabeza**, ciega (ojos cosidos) pero aún juzgadora. Reparto en el juego: el **cono de vigilancia** nace del farol y el **haz de sentencia sale de la boca de la cabeza** (el `muzzle` del lab va al hueso de esa mano). La nueva cabeza de boca abierta `tripo_convert_5f17753f-45e7-4137-b616-5fe4530a11f8` sustituye a la anterior y se renderiza al 150 % de su escala previa, conservando el punto de agarre. Es una malla estática: el movimiento de caminar, mirar y sentenciar lo aporta el brazo del Ojo.
    - **Carga de la boca (decidido 2026-11-14):** durante el segundo de fijación pasa de apagada a muy brillante en una progresión continua y legible. El brillo nace dentro de la boca y crece como un aura verde irregular pegada a la cabeza; en la parte final aparecen unas pocas lenguas de energía ascendentes. La luz permanece localizada en la cabeza, sin cruz en forma de puntos ni resplandor alrededor del héroe o del cuerpo entero.
    - **Mecánica «Mirada colimada» (decidido 2026-11-14, rama `feat/ojo-tribunal`; estado vigente en §6.13.9; cifras `[TUNABLE-PLACEHOLDER]`):** sin efectos mientras busca; al fichar al héroe se para, la mirada se colima desde el farol y, al cerrarse, la cabeza de la mano dispara por la boca. Se esquiva saliendo de la línea a tiempo.
      1. *Buscar (andar):* camina despacio (velocidad 110, ≈ un tercio del héroe) **oscilando la cabeza/mirada** (~0,5 s por paso) a izquierda y derecha. **El farol no emite luz** ni hay nada en el suelo: solo el giro del cuerpo dice que busca. Vida 400 (tres disparos del rayo base, §6.11.1).
      2. *Fichar y seguir (~40 frames):* al ver al héroe (línea de visión, sin alcance máximo, §6.13.9), se para y nace del **farol** una **mirada verde ancha, difusa y tramada** hacia el pecho del héroe, que lo **sigue** mientras se estrecha (ancha y difusa al principio y de 1 px al cerrarse, en la rampa verde del Ojo). A la vez carga la boca de la cabeza en la mano (arriba).
      3. *Fijar (~20 frames):* la línea queda **fija** donde estaba el héroe y termina de cerrarse hasta 1 px. En los últimos ~10 frames **parpadea** (aviso de «dispara ya»). Es la ventana para salir de la línea.
      4. *Sentencia:* al cerrarse, la mirada se apaga en el mismo frame y la cabeza dispara por la **boca** a lo largo de la línea fijada; 1 golpe si el héroe está en ella (respeta los i-frames). **Aviso y golpe se distinguen por forma y brillo, no solo por tono (decidido 2026-11-14):** la mirada es tramada y en verde frío apagado; el disparo es **sólido, grueso (3-5 px) y lo más brillante de la pantalla durante 2-3 frames**, en **hielo espectral** (azul pálido frío y apagado; elegido 2026-11-14 frente a ámbar, que se confundía con el fuego sagrado del héroe, y violeta, que perdía contraste; mockup `walkthroughs/ojo-tribunal/assets/mockup_color_disparo.png`), con fogonazo en la boca e impacto en el pecho del mismo color. Lenguaje visual: **verde = te apuntan, hielo = te disparan**. **Llamarada espectral (decidido 2026-11-14):** el disparo no es un láser recto y limpio ni un zigzag; es un **núcleo recto** (la línea exacta del daño, para que esquivar sea justo) con **bordes de llama irregulares y vivos** (la anchura varía a lo largo del rayo y frame a frame, con lenguas que escapan a los lados) y **volutas** de hielo que se desprenden y suben (heredadas del Maleficio original). Fogonazo grande en la boca mientras dura. Duración ~0,5 s: **golpe** 3 frames (máximo grosor y brillo), **llamarada** ~20 frames (ancha, bordes ardiendo) y **disipación** ~8 frames (se estrecha, se rompe en tramos y deja volutas). **Hace daño durante golpe y llamarada** (no en la disipación): el rayo es un muro temporal que corta el paso; como mucho 1 golpe gracias a los i-frames. Sigue la regla de efectos desaturados (sin blanco ni verde puros). Muros y columnas cortan tanto la mirada como el haz, así que esconderse tras una columna también salva. Matarlo antes del disparo lo anula.
      5. *Enfriamiento* ~90 frames y vuelve a buscar.
      - Tope de 2 Ojos apuntando a la vez (legibilidad); el resto se acerca o espera.
      - Animaciones: andar, mirar (quieto, linterna adelantada, en bucle) y sentenciar (gesto corto de 4-6 frames al soltar el haz).
- **Élites y jefes futuros (concepto, 2026-11-11; sin cofres, §6.6).** Hoy solo el Abanderado está programado, como jefe (abajo); el Campanero es el jefe del acto II (§6.13.2):
  - **El Campanero de Ánimas:** se arrancó la lengua para hacerla badajo de su campana, a cambio de que los muertos le oigan; boca vacía y cosida. Arrastra la campana rajada; al tocarla brotan Exvotos en un círculo de cera en el suelo (elipse 2:1, §4.9). El toque es la telegrafía.
- **Jefe: El Paso.** Paso de Semana Santa con costaleros muertos fusionados a las vigas; arriba, una Dolorosa viva con siete puñales que disparan rayos verdes que siguen al jugador. Embiste en línea; al matar costaleros cojea, se inclina y se ralentiza. Probablemente se trate como bloque rígido con costaleros sencillos, no como un modelo rigeado entero (decidir en su sesión).
- **Objetos en el cuerpo:** Tripo rigea y anima el cuerpo pero no gestiona objetos aparte. La cruz del Cireneo y el asta del Abanderado se modelan aparte y se pegan al hueso de la espalda en el lab de armas (hoy solo pega a las manos; falta comprobarlo). La campana va en la mano, como un arma.
- **El Abanderado (jefe) (decidido 2026-11-14, rama `feat/abanderado-jefe`).** Jefe sencillo que **no ataca**: es un invocador.
  - **Aspecto:** el estandarte va **en la mano, como bastón** (no atravesando el cuerpo). Tamaño: ~54 px en celda de 60×60 («Tamaño del Abanderado»), exportado con el preset de legibilidad C2.
  - **Aparición:** en la sala del jefe de los stages 5, 10 y 14 (§6.13.1, §6.13.7).
  - **Vida y barra:** la de §6.11.1 (`include/encounters_act1_hp.h`); disparos necesarios, en §6.13.6. Barra de vida fija del modo jefe (§6.13.7).
  - **Patrulla:** anda despacio y **cabizbajo**, apoyado en el estandarte como bastón (clip «Sad Walk» de Mixamo), entre puntos al azar de su sala.
  - **Te ve:** si estás a menos de ~1 pantalla y no hay pared en medio. Entonces se para, **levanta la cabeza, te mira e inclina el estandarte hacia ti** (no como una varita: el asta se inclina en tu dirección). Este gesto se genera por programa sobre el modelo (cabeza y brazo), sin clip de Mixamo. Si te alejas o te escondes unos 2 s, baja la cabeza y vuelve a patrullar.
  - **Invocar:** mientras te apunta, aparece un **charco color crema** en el suelo cada ~3 s, a medio camino entre él y tú. De cada charco salen **2 Exvotos monaguillo**. Tope de 8 monaguillos vivos.
  - **Salir del charco:** el monaguillo emerge poco a poco del charco, como si este lo fuera soltando (~0,5 s); el charco se seca al terminar. Mientras emerge **es invulnerable**, no hace daño ni se mueve.
  - **Exvoto monaguillo:** variante nueva del Exvoto (modelo «monje zombi», `tripo_convert_9a55a12b`). Mismas reglas que el Exvoto: muere de un golpe, camina lento hacia ti en postura de rezar (animación de andar rezando del Exvoto) y hace daño por contacto.
- **Pendiente:** si la quemadura del cuerpo crece con las mejoras (las auras L/G/E/H ya no compiten: cada una es el aspecto de una reliquia, §6.12.8); cifras, fases y telegrafías de élites y jefe; tamaño del paso en pantalla (sprites grandes o capa de fondo, `TECHNICAL.md`); si hay minijefe en la demo.
- **Corazón Abierto en el juego (decidido 2026-11-11/12, rama `feat/corazon-abierto`, `walkthroughs/corazon-abierto/`):**
  - **Animaciones:** modelo Tripo con rig Mixamo (archivos: `assets/MANIFEST.md` §2). **Andar:** un andar de Mixamo adaptado al modelo con la cadera en el sitio; se descartaron el andar del nigromante (el torso se retorcía) y uno renqueante (a 31 px no se distinguía).
  - **Carga y disparo (ajustado 2026-11-18, sesión 135):** un solo clip de 8 frames por dirección, el de disparo (f0 = brazos en cruz, f7 = derrumbado con los brazos delante). **Cargar** lo recorre **al revés** (f7 → f0) según el progreso de carga (`prog` 0..256 de §4.9), no según el tiempo, y se queda en f0 (cruz) desde `AIM_READY` hasta soltar. **Soltar** dispara en f0 y corta la animación de inmediato volviendo al andar/reposo sin atrapar al héroe en la recuperación si el jugador no toca la pantalla. **Cancelar** o soltar antes de armarse vuelve al andar al instante. **Volver a pulsar** en cualquier momento reinicia la carga desde cero (f7 → f0) al instante sin esperar ningún enfriamiento previo. Mientras carga, el personaje está parado. Se acepta el salto de la pose de andar a la encorvada al empezar a cargar.
  - **Origen:** el rayo (`muzzle`) sale del **centro del pecho** del frame que se muestra (hueso `Spine2` en el lab).
  - **Estilo «fuego sagrado»:** sin verde en el jugador (el verde es del láser enemigo). Rampa común: rojo sangre → naranja brasa → oro → blanco. Chispas de impacto del rayo: oro → naranja → ceniza.
  - **Efectos desaturados en todos los personajes (decidido 2026-11-14):** la misma regla que se aplicó al haz y al aura del héroe (paleta `FX_SH_*` de `source/weapons.c`: marfil cálido, oro viejo, ámbar, terracota, carmesí y sangre oscura, sin primarios puros) vale para los efectos de **todos los enemigos**, para que encajen en el mundo del juego. El verde enemigo pasa a una rampa apagada (hueso fosforescente, verdín, musgo, humo) con un brillo máximo similar al del héroe; nada de verde ni blanco puros. Se aplica primero al Ojo del Tribunal y después al resto de enemigos.
  - **Haz del rayo (elegido 2026-11-12 entre tres variantes; capturas en `walkthroughs/corazon-abierto/assets/contacto_haz.png`): «fuego».** Banda tramada rojo sangre/naranja que se cierra a 1 px (el colimado A1 de §4.9 recoloreado) y suelta brasas por el borde (≤ 32). Listo: línea amarilla de 1 px. Disparo: núcleo blanco con amarillo y naranja por fuera, que deja brasas rojas al apagarse.
  - **Auras de carga (llamas L, resplandor G, corona de espinas E, ceniza H):** cada una es hoy el aspecto de una reliquia (§6.12.8). El selector `Y` solo existe en las variantes de pruebas.

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
  - **Pista de jefe:** `nitro:/boss.raw`; se está rehaciendo.

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

#### 6.11.1 Datos de juego en las fichas (decidido 2026-11-19)
El Códice deja de ser solo lore: cada ficha de **enemigo** enseña también cómo se comporta y cómo se le gana. Lo lleva todo enemigo nuevo como parte de su ficha.
- **Maquetación (pantalla inferior, una sola página):** nombre; una fila con tres escalas de marcas, `VIDA`, `VELOC.` y `AMENAZA` (de 1 a 5, marcas llenas y vacías con los colores del Códice); `HACE:` (1-2 líneas); `TRUCO:` (1 línea); y debajo el lore y la cita de §6.11. Si no cabe, se acorta el texto de `HACE`/`TRUCO`, no el lore; si aun así no cabe, se vuelve a preguntar.
- **Escalas derivadas de las tablas, no de memoria:** `VIDA` = vida del enemigo entre la del Exvoto (hasta 1,25× es 1; hasta 2× 2; hasta 3× 3; hasta 5× 4; más 5); `VELOC.` = su velocidad más alta entre la del Exvoto al andar, con los mismos tramos (la embestida del Cireneo, 1000 frente a 130, es 5); `AMENAZA` = subjetiva, medida contra el Exvoto, que es el mínimo (1) de las tres escalas. Lo que va por debajo del Exvoto se queda en 1. Son rangos: ajustar un número del juego no obliga a reescribir fichas salvo que cambie de marca.
- **Valores de partida** (con las vidas del acto I, `encounters_act1_hp.h`, y `g_enemy_tuning`):
| Ficha | VIDA | VELOC. | AMENAZA | HACE | TRUCO |
| :--- | :--- | :--- | :--- | :--- | :--- |
| El Exvoto | 1 | 1 | 1 (alta en masa) | Te sigue sin parar y, si lo apuntas con el rayo cargado, se aparta a un lado. | Dispara justo tras su esquiva: tarda en repetirla. |
| El Cireneo | 3 | 5 | 3 | Se agacha y embiste en línea recta; no gira durante la embestida. | Dispárale al recuperarse. |
| El Ojo del Tribunal | 2 | 1 | 3 | Se para a distancia, te marca con una banda verde y dispara por la línea fijada. | La línea se congela antes de disparar: muévete. |
| El Abanderado (jefe) | 5 | 1 | 5 | Al verte, invoca monaguillos lentos. | Úsale las columnas; limpia monaguillos. |
- **El Corazón Abierto** (el héroe) no es enemigo: su ficha no lleva bloque de datos y mantiene su línea de comportamiento.
- **El Monaguillo** no tiene ficha propia hasta que exista su lore (`LORE.md`); mientras tanto sus datos van en la del Abanderado.
- **Texto fijo, no generado en ejecución:** los datos de cada ficha se escriben a mano en `source/bestiary.c`; si cambia una IA o una vida, se revisa la ficha en la misma entrega.

#### 6.11.2 Tipografía del juego (decidido 2026-11-19, rama `feat/tipografia`)
Todo el texto que se lee usa **una sola fuente: Palatino de 11 px, dibujada con el trazado nítido (hinting) de la propia fuente**, con tildes y `ñ`. Sustituye a Georgia 11 recortada por umbral (trazos finos rotos, letras pegadas) y a la fuente de 5×7 solo en mayúsculas del menú y del HUD.
- **Dónde:** fichas del Códice, tarjetas de introducción, pantallas del jefe, título, pausa, controles, subida de nivel (nombres y efecto) y HUD de partida (`Enc. 1 de 14`, `Altura 0 m`, `Tiempo 0:00`, avisos). Los nombres de los pedestales antiguos (`modifiers.c`) también llevan tilde.
- **Mayúsculas:** las etiquetas pasan a minúscula inicial (`Nueva partida`, `Códice`, `Continuar`). Siguen en mayúsculas las etiquetas de datos del Códice (`VIDA`, `VELOC.`, `AMENAZA`, `HACE:`, `TRUCO:`) y el nombre grande del jefe.
- **Elegida entre** la actual, Palatino nítida (misma altura y hueco que hoy) y Georgia nítida (más ancha: desborda las fichas con datos y haría falta recortar textos). Descartadas: Georgia a 12, Georgia negrita (demasiado pesada) y Book Antiqua, Sitka, Constantia y Book Old Style (peor trazo). Detalle y rondas en `walkthroughs/tipografia/`.
- **Fila de escalas del Códice:** marcas de 3 px con paso 5 y hueco de 5 entre bloques (antes 4, 6 y 7) para que `VIDA`, `VELOC.` y `AMENAZA` quepan en el marco con la fuente nueva.
- **Fuera de alcance:** el contador de FPS y los datos de rendimiento (depuración) siguen en la fuente de 5×7.
- **Aceptado con matices (visto en el walkthrough):** el HUD de partida sale más fino que el 5×7 y se lee con menos fuerza sobre el suelo con textura; los botones inactivos y la fila de datos del Códice quedan algo tenues. Se pule más adelante si molesta en la DS; no se midió rendimiento (decisión del usuario: no hace falta).
- **Menú de título:** la ROM jugable vuelve a abrir en él (§6.3). Solo las variantes de pruebas (`SKIP_TITLE`) arrancan directas.

### 6.12 Sistema de mejoras del Corazón Abierto (decidido 2026-11-15)
Sesión de diseño de la v0.4. Sustituye la regla de §6.6 «mitad del arma, mitad del personaje» y la elección de clase: la demo tiene un solo personaje. Las cifras están en `[TUNABLE-PLACEHOLDER]` hasta la sesión de números.

#### 6.12.1 Filosofía
- **Pool abierto, espíritu *The Binding of Isaac*.** Todas las mejoras conviven en el mismo pool, sin ramas excluyentes. Elegir bien rompe la partida; elegir sin criterio te deja sin nada. Con poco contenido ya tiene que divertir, y añadir mejoras no debe empeorarlo.
- **Builds como en *League of Legends*.** Hay estadísticas que solo valen para unas builds, y la misma mejora vale oro en una partida y es basura en otra. Ejemplo: «carga más rápida» no le sirve de nada a quien juega a mantener el rayo cargado.
- **La build cero crece sumando; las demás, multiplicando.** La Ráfaga (§6.12.3) es fiable desde el primer minuto y tiene techo. Las demás necesitan juntar varias piezas: con una sola están peor que antes (valle) y con tres se disparan. **Cuanto más rota es una build, peores son sus piezas por separado y más hondo es su valle.**
- **Contrapartida solo cuando la mejora rompe una regla del personaje** (por ejemplo, moverse mientras carga). Las demás reliquias son ventaja pura o llevan un riesgo que depende de la habilidad.
- **Frenarse cuesta.** No es un survivors abierto: no se puede uno plantar. Todo lo que frena al héroe es un coste real porque los enemigos te rodean y las salas se cierran.

#### 6.12.2 Reglas comunes
**El rayo base (cambia el comportamiento actual):**
- **Atraviesa a quien mata y se detiene en el primero que sobrevive.** Con poco daño se queda en el primer enemigo duro; con mucho, limpia filas. Atravesar es la recompensa natural de subir el daño.
- **Muros y columnas cortan el rayo y la línea de apuntado**, con chispas en el punto de impacto, como el haz del Ojo del Tribunal (§6.10). Lore: es fuego que sale de la carne, y la piedra lo detiene. Las columnas dan cobertura a los dos lados.
- **Alcance base más corto,** para que haya que acercarse a la vanguardia (cifra en §6.12.10).

**Dos tipos de daño:**
- **Daño del rayo:** solo el disparo.
- **Daño de fuego:** todo lo demás (quemadura, explosiones, aro, ondas, línea de apuntado).

**Un único estado en los enemigos, «Quemado».** Se acumula en capas. Cada capa hace daño de fuego por segundo y frena un poco al enemigo; seguir quemándolo renueva la duración. Hay un tope de capas. No existe un estado aparte de «ralentizado»: frenar va dentro de Quemado.

**Vocabulario de las mejoras.** Toda mejora, presente o futura, se construye con estas piezas. Así las sinergias salen solas y no se diseñan de dos en dos:
- **Momentos:** al cargar, mientras cargas, al disparar, al impactar, al matar y al recibir un golpe.
- **Toda muerte cuenta como muerte,** también las de explosiones, quemaduras o aros. Así, por ejemplo, Martirio alimenta a Sed de Ceniza sin programarlo aparte.
- **Todo fuego usa el daño de fuego, y todo rayo hereda los modificadores del rayo.**
- **Topes visibles** de capas de quemadura y de explosiones encadenadas, para que una partida rota no baje de 60 FPS en la DS.

**Texto de cada mejora:** icono, nombre y una línea que **empieza por el momento en que actúa** («Mientras cargas: …», «Al matar: …»). Es la lección de la v0.2 (§6.6) y lo que permite aprender las builds leyendo.

#### 6.12.3 Arquetipos
Son una guía de diseño para dar variedad, no ramas ni clases. El jugador no los ve nombrados: los descubre combinando.

| Arquetipo | Fantasía | Cómo mata | Piezas clave | Valle |
|---|---|---|---|---|
| **Ráfaga** (build cero) | La ametralladora: «pa, pa, pa», cada disparo limpia una fila | Daño del rayo y cadencia | Fervor, Prisa, Alcance, Sed de Ceniza, Lanza de Longinos | Ninguno. Es la opción segura cuando vas apurado; con ella se puede pasar el juego, pero tiene techo |
| **Vigilia** | Cargar y no soltar: barrer la pantalla con la línea (de lejos) y quemar lo que se acerca con el aro (de cerca) | Capas de Quemado | Llama Votiva, Aura de Cilicio, Paso de Procesión, Brasa, Rescoldo, Paso | Hondo. Sin el Don de Paso, Procesión va tan lenta que los enemigos te rodean y hay que soltar; sin Brasa, la quemadura hace poco |
| **Mártir** | Kamikaze: vivir a 1-2 corazones a cambio de mucho daño y curarse jugándosela | Todo su daño crece con la vida perdida; se cura matando de cerca | Llaga Abierta, Corazón Flagelado, Viático, Paso | El más hondo. Llaga sola solo quita vida |
| **Puentes** | Mezclan arquetipos | — | Auto de Fe (rayo ↔ fuego), Martirio Contagioso (fuego para Vigilia y Mártir) | — |

#### 6.12.4 Ritmo de la partida
- **Cada relicario roto ofrece 1 de 3 Dones** (uno por pasillo: 13 pasillos en los 14 stages, uno de ellos el dorado, que da una reliquia: 12 Dones por partida completa), sin volver a tirar. Antes se ganaban por nivel de experiencia; ya no hay experiencia (§6.13.6).
- **Unas 4 Reliquias por partida** (1 de 3, pantalla de marco dorado, que se note como el momento especial): la primera en el relicario dorado a mitad del acto I y una al vencer a cada jefe (§6.13.5).
- **Ofertas con cabeza:** a partir de la segunda reliquia, al menos una de las tres opciones comparte arquetipo con alguna reliquia que ya tengas. No asegura la pieza que falta, solo que el camino sigue abierto; romper la partida sigue dependiendo de elegir bien y de algo de suerte.
- **Requisitos (decidido 2026-11-15):** una mejora solo se ofrece si ya tienes lo que la activa. Hoy: Brasa, Rescoldo, Auto de Fe y Martirio Contagioso necesitan una fuente de quemadura (Llama Votiva, Aura de Cilicio o Corazón Flagelado). La primera reliquia de fuego abre ese camino. Toda mejora futura declara su requisito.
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
| **Lanza de Longinos** | Siempre: el rayo atraviesa a todos los enemigos, mueran o no | Todas | Sin efecto propio: se ve en que el rayo atraviesa a todos (decidido 2026-11-15) | Ninguna |
| **Auto de Fe** | Al impactar: el rayo hace el doble a los quemados y consume sus capas | Puente rayo ↔ fuego | Láser: núcleo del disparo en hoguera; los quemados estallan en chispas al recibirlo | Ninguna |
| **Llama Votiva** | Mientras cargas: la línea de apuntado aplica capas de Quemado a lo que toca | Vigilia de lejos | Láser: la línea de apuntado arde en llamas | Ninguna |
| **Aura de Cilicio** | Mientras cargas: un aro de brasas a tus pies quema a quien entra; crece con la carga | Vigilia de cerca | Aura E, corona de espinas, en el suelo | Ninguna |
| **Paso de Procesión** | Mientras cargas: puedes andar despacio | Vigilia | Cuerpo: anda en cruz mientras carga | Carga más lenta (rompe una regla) |
| **Martirio Contagioso** | Al matar a un quemado: explota con daño de fuego y aplica Quemado alrededor | Puente de fuego | En los enemigos: explosiones | Ninguna; tope de cadena |
| **Corazón Flagelado** | Al recibir un golpe: onda de fuego alrededor y siguiente disparo cargado al instante | Mártir | Onda de fuego al recibir el golpe; aura L, llamas, mientras espera el disparo instantáneo | Ninguna |
| **Llaga Abierta** | Al cogerla: tu vida máxima baja a la mitad. Siempre: todo tu daño sube por cada corazón por debajo de 5 | Mártir | Sangre que gotea y aura pálida dorada: cuantos menos corazones, más gotea y más brilla (no rojo, §6.12.13) | Pierdes vida máxima |
| **Viático** (concepto cambiado 2026-11-15: robo de vida) | Al matar con el rayo: probabilidad de robar 1 corazón al enemigo, el doble si estaba pegado a ti | Mártir | Sifón: la vida del enemigo viaja hasta el pecho del héroe (ronda A/B/C); aura G, gloria, al cargar | Ninguna |

**Detalles:**
- **Llama Votiva** quema solo donde apuntas en ese momento; no deja rastro en el suelo (opción A, elegida por coste y rendimiento). El rastro persistente es Tierra Quemada, en reserva.
- **Aura de Cilicio:** el aro a carga completa es su tamaño máximo. Sin Procesión, mantenerlo te deja clavado y los enemigos te rodean; con Procesión avanzas con el aro al máximo.
- **Paso de Procesión:** andas al 35 % de la velocidad; los rangos de Paso lo compensan. Para la Ráfaga, la carga lenta es un castigo; para la Vigilia, que no suelta, no cuesta nada.
- **Llaga Abierta:** el bonus de daño se cuenta **siempre respecto a los 5 corazones de partida**, no respecto al tope actual. Al cogerla (de 5 a 3) ya tienes el bonus de 2 corazones; a 1 corazón, el máximo. Subir Vida te protege pero te quita daño.
- **Martirio** solo explota con enemigos quemados, así que en una Ráfaga pura no hace nada.

**Reserva para la segunda tanda (sin código en la demo):** Ascua Impaciente (soltar antes de tiempo dispara un rayo corto), Óleo Sagrado (disparo instantáneo periódico), Pilar Consagrador (rayo ancho que empuja), Tierra Quemada (la línea deja brasas persistentes; parches con tope) y Reflejo de Penitencia (el rayo rebota 1 vez en los muros). Descartado: Botafumeiro (incensario que gira), redundante con el Aura de Cilicio.

#### 6.12.7 Ejemplos de builds
- **Ráfaga limpia:** Fervor, Prisa y Alcance en casi todos los niveles; reliquias Sed de Ceniza y Lanza de Longinos. Cada disparo mata a una fila y la siguiente carga llega casi al instante. Fuerte desde el principio y estable, pero sin explosiones ni cadenas: es la que te lleva al final, no la que lo rompe.
- **Ametralladora en cadena (Ráfaga con fuego):** Sed de Ceniza, Llama Votiva, Martirio y Auto de Fe. Una carga corta marca con la línea, el disparo remata doble a los quemados, los muertos explotan y contagian, y cada muerte acelera la siguiente carga. Valle: hasta tener Llama Votiva, Martirio no hace nada.
- **Procesión de fuego (Vigilia):** Llama Votiva, Aura de Cilicio y Paso de Procesión, con Dones de Brasa, Rescoldo y Paso. Avanzas con los brazos en cruz arrastrando la línea por la sala y con el aro al máximo; ya casi no disparas. Valle: entre coger Procesión y juntar 2 rangos de Paso, los enemigos te rodean y la carga lenta estorba.
- **Hoguera (Vigilia de cerca con Martirio):** Aura de Cilicio, Martirio, Paso de Procesión y Brasa. Te metes en la masa con el aro a tope; los quemados revientan pegados a ti y contagian a los de detrás.
- **Penitente kamikaze (Mártir):** Llaga Abierta, Corazón Flagelado y Viático, con Dones de Paso y Brasa. Vives a 1-2 corazones con el daño al máximo. Cada golpe que recibes suelta una onda y un disparo instantáneo, y robas vida al matar, más aún de cerca. Con Aura de Cilicio, el aro hace las muertes cercanas por ti. Valle: Llaga sola solo te deja con 3 corazones.
- **Partida sin criterio (el contraejemplo):** Llama Votiva, Sed de Ceniza y tres rangos de Prisa. La línea quema medio segundo porque cargas rapidísimo, y Sed te castiga cada vez que barres sin matar. Las piezas se anulan entre sí.

#### 6.12.8 Presentación
- **Cada reliquia se ve donde actúa (decidido 2026-11-15):** los efectos pegados a personajes respetan la oclusión con sus cuerpos, como las auras. No todas son auras. Unas son auras del cuerpo, otras cambian el láser o la línea de apuntado, y otras se ven en los enemigos o en el movimiento (columna «Cómo se ve» de §6.12.6). Las cuatro auras de carga en comparación (§6.10, selector `Y` de depuración) dejan de competir: E → Cilicio, H → Sed de Ceniza, G → Viático y L → Corazón Flagelado, y se apilan según lo que lleves. Sin reliquias, la carga muestra solo el rayo. Cada aura tiene un coste fijo por frame: con 3 o 4 apiladas se mide en la DS y, si se pasa, se dibujan las dos últimas cogidas.
- **Enemigos quemados:** brasas procedurales sobre el cuerpo con el sistema de chispas del rayo (más capas, más brasas subiendo) y una lengua de fuego sobre la cabeza al tope de capas. Tope global de partículas. Descartados: sprites requemados (doblan el arte y la memoria y no muestran las capas) y teñir el sprite (encarece el paso de dibujo que hoy más pesa).
- **Fuego en el suelo:** en la demo solo hay efectos breves en el pase de suelo: el aro del Cilicio y un anillo corto por cada explosión de Martirio. Nada persistente.
- **Pantalla de elección (decidido 2026-11-15):** estilo Códice (§6.11: fondo negro, borde gris fino). Sobre el juego pausado y oscurecido aparecen **3 cartas en paralelo** en primer plano en la pantalla inferior; la seleccionada se ilumina (borde y brillo) y se adelanta un poco. Cada carta lleva su nombre y un **arte que es una vista previa del efecto tal como se ve en el juego** (decidido 2026-11-15, opción A): una escena de la propia ROM (héroe, efecto y los enemigos que hagan falta, sobre fondo oscuro) capturada en bucle y ampliada 2×, enmarcada al estilo Códice. Se descarta pintar el efecto aparte sobre el retrato del Códice (primer horneado: el efecto quedaba pobre frente al del juego). El efecto completo de la carta seleccionada se lee en una franja de texto. Las reliquias llevan marco dorado. El arte se genera fuera de la ROM a partir de esas capturas y se carga bajo demanda desde NitroFS; se regenera cuando cambie un efecto.
- **Ronda A/B/C (decidido 2026-11-15):** cada elemento visual nuevo se presenta en un walkthrough con tres variantes sacadas de la ROM y el usuario elige. Resultados: §6.12.11–13.

#### 6.12.9 Pendiente (siguiente paso de la sesión de diseño)
- Cifras de partida: alcance base y máximo, tiempos de carga, daño del rayo y del fuego frente a las vidas del acto I, valor por rango de cada Don, capas y duración de Quemado, bonus de Llaga y N de Viático.
- Si los relicarios deben dar también corazones (§6.13.6 lo dice, la ROM solo da Dones) y cómo conviven con el Don de Vida y con Viático.
- Aspecto definitivo de los cambios del láser (Auto de Fe, Llama Votiva y Llaga), en la ronda A/B/C.

#### 6.12.10 Cifras vigentes (provisionales; sin gemas ni recuperación, revisado 2026-11-19)
Provisionales (ver el aviso de arriba): se ajustan con la lista que salga de la partida de prueba en la DS. Frames a 60 FPS; distancias en píxeles de suelo; vida en la escala 100 = 1,0 (exvoto 250, monaguillo 100, cireneo 600, ojo 400, abanderado 5500; fuente: `include/encounters_act1_hp.h`).

**Rayo base (decidido 2026-11-19, a probar en la DS):** daño 150. **Carga 48 frames (0,8 s)**, antes 24. **Alcance 110**, antes 160 (320 y 240 en versiones anteriores). Motivo: con el rayo inicial muy rápido y de largo alcance las primeras salas no eran un reto; se quiere que empiecen justas y que el poder se gane con los Dones. **No hay recuperación tras disparar:** al volver a pulsar, la carga empieza de cero al instante (§6.10); el ritmo lo marca solo la carga. **Prisa llega rápido al tope y se acepta:** el techo es estilo metralleta (carga 8), el principio es lento.

**Dones (7 rangos cada uno, decidido 2026-11-19):** el efecto total al máximo es el de antes con 4 rangos (salvo Alcance, que baja de 416 a 366 al bajar la base); se reparte en 7 pasos (en el código, `rank_step` en `upgrades.c`, que reparte lo que haya aunque `UPG_MAX_RANK` cambie). Motivo: con un Don por relicario, una partida completa (12 Dones: 13 pasillos en los 14 stages, uno de ellos el dorado) no debe permitir llevar todos los Dones al máximo: 7 Dones de 7 rangos son 49 plazas frente a 12 picks. Se pasó por 4, 5 y 8 rangos antes de llegar a este. **Descartado (decidido 2026-11-19): limitar a 4 el número de Dones distintos** (estilo Vampire Survivors); el usuario prefiere que cualquier Don pueda subirse. **Riesgo conocido, a vigilar jugando:** con ofertas aleatorias y todos los Dones con el mismo peso, los picks tienden a repartirse y las builds pueden quedar planas; si pasa, las palancas son pesos por Don, poder rechazar una carta o sesgar la oferta hacia lo que ya tienes.
| Don | Por rango | Al máximo |
|---|---|---|
| Fervor | +14 % daño del rayo (15 o 14 según el rango) | +100 % (×2) |
| Prisa | −6 frames de carga (−5 en el 4.º y el 7.º) | carga 8 (mínimo 6) |
| Alcance | +37 de alcance del rayo y de la línea (36 y 37) | 366 |
| Brasa | +14 % daño de fuego (15 o 14 según el rango) | ×2 |
| Rescoldo | +1 capa de tope en 4 de los 7 rangos y +17 frames de duración (18 en el primero) | 9 capas, 240 frames |
| Paso | +7 % velocidad (también con Procesión) | +48 % |
| Vida | +1 corazón de tope en 4 de los 7 rangos; cada rango cura 1 | 9 corazones |

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

**Gemas y experiencia: retiradas** (2026-11-16, §6.13.6). Sus cifras antiguas siguen en el código sin uso en la ROM por defecto.

#### 6.12.11 Elecciones de la ronda A/B/C (2026-11-15, primera vuelta)
Resultado final de las tres vueltas en §6.12.13. Texto íntegro de cada vuelta en `DESIGN-ARCHIVE.md`.

#### 6.12.12 Elecciones de la ronda A/B/C (2026-11-15, segunda vuelta)
Resultado final en §6.12.13.

#### 6.12.13 Elecciones de la ronda A/B/C (2026-11-15, tercera vuelta) y resultado vigente
Una línea por efecto, con lo que vale hoy:
- **Enemigo quemado:** A (brasas y lenguas) y B (corona de llamas a los pies) gustan las dos; se decide jugando. El sprite se tiñe según las capas: claro con 1 capa y más rojo con cada una, hasta el tope a las 3–4 capas; se mide el coste en la DS. C descartada.
- **Llama Votiva:** B, chispas sueltas que giran de forma irregular y procedural (como manchas solares), no una hélice perfecta; se afina más adelante.
- **Corazón Flagelado:** A, anillo grande. **Martirio Contagioso:** A, con el mismo lenguaje por consonancia.
- **Auto de Fe:** A (chispas minimalistas al impactar) y C (la corona de llamas del quemado sube y se evapora al consumirse); B descartada. Regla: todo efecto nace del mundo (del suelo, del cuerpo o del punto de impacto), nunca flota como un icono.
- **Llaga Abierta:** B, sangre que gotea y aspecto de ascendido (aura pálida dorada); cuantos menos corazones, más gotea y más brilla. No es rojo: es un poder, no un castigo, y el rojo se confunde con el quemado.
- **Viático:** A, hilo de sangre (C, alma pálida, queda como alternativa). Al robar vida, la víctima queda inerte y suspendida ~0,3 s mientras se le extrae el hilo, y luego muere con su animación normal.

#### 6.12.14 Pendiente: efectos de sonido (sesión aparte)
El sistema de mejoras no tiene sonido propio todavía. Faltan, como mínimo:
- romper un relicario (se abre la pantalla de elección);
- mover la selección y elegir carta (Don y Reliquia, esta más solemne);
- enemigo empezando a arder y tic de quemadura (muy discreto, con enfriamiento);
- explosión de Martirio Contagioso;
- onda de Corazón Flagelado;
- Auto de Fe al consumir la quemadura;
- Llama Votiva (línea ardiendo mientras se carga, en bucle);
- Aura de Cilicio (aro ardiendo mientras se carga, en bucle);
- robo de vida de Viático (sifón y cura);
- Llaga Abierta (latido o goteo según la vida que falte).
Se generan con el flujo de `AGENTS.md` (ElevenLabs CLI) en su propia sesión.


### 6.13 Estructura de la partida: la Subida (decidido 2026-11-16, rama `docs/estructura-partida`)
Sustituyó al nivel infinito de la 0.3 (historia en `DESIGN-ARCHIVE.md`). Motivo: la catedral infinita no tiene intención (el compositor alterna piezas al azar y nada anuncia lo que viene) y es difícil de hacer bien. Una partida con principio, mitad y final se entiende, se recuerda y encaja con el lore (`LORE.md`: la Columna intentó llegar al Altar y cayó por el camino; Elías hace el mismo recorrido).

- **Duración objetivo: 15–18 min** hasta ganar al jefe final (antes ~8). Referencias: Isaac hasta Mom, 20–30 min en pisos de 3–5 min; Vampire Survivors y Halls of Torment, 30 min. Se queda por debajo porque es una portátil sin guardado a mitad de partida. Si se queda corta en la DS, se alarga cada acto sin cambiar el esqueleto.
- **Columna vertebral: un Vía Crucis de 14 estaciones.** Cada estación es un hito visible en el muro con su número romano (la pieza exacta se decide en la sesión del escenario) y es ambientación: el jugador sabe dónde está y cuánto le falta sin barra de progreso, pero las estaciones no marcan dónde pasan las cosas (§6.13.6). La ROM juega 14 stages con 3 jefes (stages 5, 10 y 14).

| Tramo | Estaciones | Tiempo | Final del tramo |
| :--- | :--- | :--- | :--- |
| **Pórtico** | — | ~0:30 | Entrada tranquila, último campamento de la Columna. |
| **Acto I: la nave** | I–IV | ~5 min | **Jefe 1: El Abanderado** en la estación V. |
| **Acto II: el coro** | VI–IX | ~5 min | **Jefe 2: El Campanero de Ánimas** en la estación X. |
| **Acto III: el Calvario** | XI–XIII | ~5 min | **Jefe final: El Paso** en la estación XIV (el altar). Victoria. |

- **Cada acto es como un piso de Isaac:** cadena de encuentros y pasillos → encuentro con el jefe → respiro y recompensa → el siguiente acto empieza con otro ambiente, más profanado que el anterior (estados de profanación de §6.9.1b).
- **Los enemigos entran por actos:** acto I, Exvotos y, en toda sala salvo el atrio, un Ojo; el Cireneo desde las salas medias (§6.13.9). Acto II, se suma el Abanderado como élite. Acto III, todos.
- **Cada jefe vuelve después como enemigo normal (élite):** el Abanderado en los actos II y III; el Campanero en el acto III. El jugador reconoce al que ya venció y la partida tiene memoria. Su versión élite es más débil que la de jefe; las cifras se deciden en la sesión de cada jefe.
- **El escenario se ordena por actos:** tramos hechos a mano para cada acto, en orden fijo y reconocible entre partidas; el azar solo elige variantes dentro de cada tramo. «La catedral que no termina» queda como lore (el altar se aleja), no como mapa infinito.
- **Morir** reinicia la partida desde el pórtico, como hoy.

#### 6.13.1 Encuentros con jefe
- **En el mismo pasillo, no en una sala aparte.** Al llegar a la estación del jefe:
  1. **Presentación:** pantalla de intro del jefe con un zoom sobre él y su nombre (presentación concreta en su propia ronda A/B/C).
  2. **Sala cerrada:** el jugador no puede avanzar ni retroceder fuera de la sala del jefe hasta que gane o muera. La cámara no se fija: sigue al héroe (§6.13.7).
  3. **Solo el jefe y su escolta:** no aparece nada más en la sala.
- **Encuentro coreografiado (por defecto):** el jefe llega con una escolta definida que se renueva desde arriba según la vas matando; por ejemplo, el Abanderado con varios Ojos y algún Cireneo. Qué escolta lleva cada jefe y a qué ritmo vuelve se decide en su sesión.
- **Alternativa por jefe: el jefe solo,** reforzado para que sea interesante sin escolta. Se elige una u otra en la sesión de cada jefe.
- **Al ganar:** el jefe da una reliquia (§6.13.5), se desbloquea la pantalla y, tras un respiro, empieza el acto siguiente.
- **El Abanderado** es ya el jefe fijo de la estación V (stage 5) y su invocación de monaguillos es la base de su encuentro; repite en los stages 10 y 14 hasta que existan el Campanero y El Paso.

#### 6.13.2 El Campanero de Ánimas (jefe del acto II, dirección inicial)
- **Poder (dirección del usuario, detalle por decidir):** refuerza a los enemigos que tiene alrededor: más fuertes o invulnerables mientras dura el efecto. El toque de campana es la telegrafía (concepto de §6.10). El combate pide romper su protección o separar a los enemigos de él antes de atacarlos.
- Lore y ficha del Códice: pendientes (`LORE.md` §9, «Enemigos nuevos»).

#### 6.13.3 Al ganar la partida
- Tras vencer a El Paso aparecen **unas escaleras que bajan a las criptas**: el siguiente nivel. Encaja con `LORE.md` §5 («se puede salir, por abajo»).
- **La partida sigue (decidido 2026-11-16):** al bajar las escaleras se continúa en las criptas sin cortar la partida, con el mismo personaje y sus mejoras, como Isaac tras Mom. No hay desbloqueo ni guardado en la consola (§6.3). Ganar a El Paso es la victoria de la catedral; las criptas son contenido extra para quien llega.
- **Pendiente:** qué hay en las criptas (estructura, enemigos y jefe), si tienen final propio y qué pasa mientras no existan (por ahora, pantalla de victoria al vencer a El Paso).

#### 6.13.4 Pendiente
1. Poder exacto del Campanero y escolta de cada jefe.
2. Pieza visual de las estaciones y aspecto de cada acto (sesión del escenario).
3. Qué es el Altar y qué encuentra Elías al llegar (`LORE.md` §9).

#### 6.13.5 Ritmo de mejoras en la Subida (decidido 2026-11-16)
Sustituyó al reparto de reliquias por nivel de experiencia (ya retirado).
- **4 reliquias por partida, como ahora,** para no tocar el equilibrio de §6.12:
  1. **Relicario dorado a mitad del acto I:** la primera, en el pasillo que sigue al stage 6 (la sala posterior al primer jefe, stage 5; `ENC_GOLDEN_AFTER`), para que la construcción empiece a definirse en el acto I.
  2. **Jefe 1 (Abanderado), jefe 2 (Campanero) y jefe final (El Paso):** una al vencer a cada uno, con la misma pantalla de marco dorado de §6.12.4. La de El Paso llega para las criptas.
- **Cada jefe es un punto de inflexión de la build.** Las reglas de oferta de §6.12.4 (arquetipo compartido, requisitos, una reliquia cogida sale del pool) valen igual.
- **Dones:** salen de los relicarios de los pasillos (§6.13.6), 12 por partida completa.

#### 6.13.6 Escenario por actos: encuentros y pasillos (decidido 2026-11-16, rama `docs/escenario-actos`)
Sustituyó (implementado en la ROM desde 2026-11-17) al compositor v2 de la catedral, a la marea y la horda aleatoria y a las gemas y la experiencia, todo archivado en `DESIGN-ARCHIVE.md`. Motivo: el apuntado manual y las coberturas piden enemigos colocados con intención (ADN de *twin-stick*: Enter the Gungeon, Isaac), y la marea castigaba justo lo que se quiere diseñar (pensar el encuentro, desviarse al relicario).

**Lo que juega la ROM:** 14 stages (encuentros y pasillos) con 3 jefes: El Abanderado en el 5, el 10 y el 14.

**Qué es juego y qué es lore.** El juego se describe con cinco palabras: partida, acto, encuentro, pasillo, pieza. Nave, coro y Calvario son el lore de cada acto y deciden qué piezas usa; el Vía Crucis y sus estaciones son ambientación y no marcan dónde pasan cosas. El pórtico son las primeras pantallas despejadas del acto I.

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
- **Barrera en el borde de arriba del encuentro** (en el acto I, el rastrillo; en el II, la reja del coro): no se abre hasta matar a todos.
- **Pasillo de ~2 pantallas** detrás de la barrera: colchón para que, estando arriba del encuentro, la pantalla superior no enseñe el siguiente. Al subir por él asoma la parte baja del siguiente encuentro con sus enemigos dormidos (aviso, no revelación).
- **Un encuentro despierta al cruzar su borde de abajo.** Los enemigos despiertos te siguen a cualquier parte. Nada reaparece.
- **Antes de despertar, los enemigos del encuentro no reciben daño** (el rayo los atraviesa). Se vio con el bot (2026-11-17): disparar desde el pasillo a los Exvotos que rezan vaciaba el encuentro sin riesgo.
- **Catálogo:** diseños por acto, encadenados al azar y espejados (izquierda ↔ derecha); el catálogo vigente del acto I está abajo. Cada diseño enseña o examina una cosa.
- **Reglas de oficio:** nunca hacer aparecer un enemigo encima del jugador; avisar de dónde sale cada uno; mezclar 1–2 que disparan con varios cuerpo a cuerpo; acto I con 3–6 enemigos por encuentro, subiendo poco a poco; nunca un hueco cerrado (siempre dos caminos hasta el héroe).
- **Sensación:** como el primer piso de Isaac, fácil si lo entiendes, mortal si vas a lo loco. Encuentros con bastantes enemigos colocados con intención: unos esperan en su puesto (el Ojo y su guarnición) y otros van a por ti.

**Las piezas tienen papel de combate.**
- Columnas y estatuas paran los disparos de todos (rama `fix/cobertura-estatuas`). Te protegen del Ojo.
- Bancos y sacos paran cuerpos y cargas, no disparos. Los enemigos los rodean (campo de navegación), así que ordenan a la horda en hileras. Pendiente de comprobar: si el Cireneo queda aturdido al chocar con un banco como con un muro (si sí, el banco te protege del Cireneo).
- Bancos destructibles: mecánica candidata, no ahora.
- **Agacharse tras coberturas bajas (decidido 2026-11-17, rama `feat/coberturas-bajas`).** Sin botón: la `L` sigue reservada para la habilidad activa (§6.5).
  - **Se agacha solo** al pegarse a un banco o a unos sacos. Mientras siga pegado y se mueva, **anda agachado y más lento**. Al separarse se levanta.
  - **No dispara agachado.** Al tocar con el stylus se levanta y dispara (también mientras carga el rayo), y queda expuesto. Al soltar, vuelve a agacharse si sigue pegado.
  - **Protege por un solo lado.** Un disparo enemigo le pasa por encima solo si cruza la cobertura antes de llegarle. Desde su lado de la cobertura le da igual que de pie. Cubre también del haz del Ojo.
  - Los cuerpo a cuerpo le alcanzan agachado igual que de pie: el precio es quedarse quieto mientras la horda rodea el banco.
  - Coberturas altas (columnas, estatuas): sin cambios ni animación propia, porque ya paran los disparos.
  - Cifras `[TUNABLE-PLACEHOLDER]`: «pegado» = a ≤ 4 px de la huella de la cobertura; velocidad agachado = 50 % de la normal; se levanta y se agacha en ~6 frames.
  - Arte: un clip «agachado» quieto y andando, en 8 direcciones, del héroe. Decidido (2026-11-18): variante A2 del andar agachado (cadera 15 u más baja, torso más inclinado que el clip de Mixamo, 20,8 px de alto frente a 32,3 de pie); el quieto es un fotograma fijo de ese andar.
  - Referencia de género: las mesas volcadas de Enter the Gungeon.

**Relicario en cada pasillo: mejora continua y periódica.**
- Sin gemas ni experiencia. En cada pasillo, a un lado, hay un **relicario**: al romperlo a tiros da **elegir un Don**. Los relicarios decorativos al azar desaparecen.
- Un relicario por pasillo da 12 Dones por partida completa: las cifras de los Dones valen como están y se ajustan jugando.
- **Reliquias:** 4 por partida, como en §6.13.5. Al vencer a cada jefe, y la primera en un relicario de marco dorado a mitad del acto I (sustituye a la del nivel 5).

**Daño: varios disparos por enemigo.**
| Enemigo | Disparos con el rayo base |
| :--- | :--- |
| Exvoto | 2 |
| Monaguillo | 1 |
| Ojo | 3 |
| Cireneo | 4 |
| Abanderado (jefe) | ~37 |
- **El rayo sigue solo con el daño que le sobra** al matar; si no mata, se para. Con el rayo base, poner a los enemigos en fila ayuda poco; con Fervor vuelve a barrer filas (el poder se gana). La Lanza de Longinos sigue atravesando a todos sin perder daño.

**Enemigos por acto.** Acto I: Exvotos y, en toda sala salvo el atrio, un Ojo (sin él las columnas no sirven); el Cireneo desde las salas medias. Acto II: se suma el Abanderado como élite. Acto III: todos. La IA vigente y los papeles: §6.13.9.

**Tras la primera prueba en la DS (decidido 2026-11-17).** El prototipo era trivial: el jugador decidía cuándo empezaba la pelea y la empezaba fuera del alcance de los enemigos, con pocos a la vez y un Cireneo que se esquivaba con un paso. Se decide:
- **Todos los enemigos están en la sala desde el principio, como en Isaac,** y despiertan todos a la vez al cruzar el borde de abajo (también los que rezan). Los refuerzos desde arriba (segunda oleada) son un recurso ocasional de las poblaciones duras, no la norma: no tiene sentido temático que salgan de la nada.
- **Más listos, no esponjas de balas.** La dificultad sale de la IA y de la colocación, no de subir la vida a secas. **El Exvoto esquiva el rayo:** si el héroe le está apuntando con el láser de carga, se aparta de la línea, y los de una fila se abren cada uno a un lado para romperla. No anda en línea recta hacia el héroe.
- **El Cireneo, perseguidor que embiste:** anda siempre hacia el héroe a buen paso; cuando lo tiene alineado carga muy rápido y con poco aviso; si choca con una columna, estatua, saco o alambre queda aturdido un buen rato (la recompensa por usar el escenario).
- **El Ojo** solo es difícil cuando hay más presión alrededor; subirle la vida no lo arregla. Su diseño vigente: §6.13.9.
- **Salas rediseñadas** en un catálogo revisado antes de tocar la ROM: cada planta plantea una sola pregunta y sus tres poblaciones (ligera, media y dura) son versiones más duras de esa misma pregunta.

**Ancho de la catedral: 256 px (una pantalla).** Sin desplazamiento lateral: el encuentro entero se ve y todo el ancho queda al alcance del lápiz; el escenario cuesta la mitad de tiles. Muros de ~24 px por lado (suelo útil ~208 px), columnas pegadas al muro como pilastras. Corte orientativo: paso lateral ~24 + bancos 64 + pasillo central 32–48 + bancos 64 + paso lateral ~24.

**Dificultad: planta y población por separado (como Isaac y Hades).**
- Cada diseño de encuentro es una **planta** (piezas y barrera) con **3 poblaciones**: ligera, media y dura (cuántos enemigos y de qué tipo).
- El acto pide los encuentros **por tramos**: el primer tercio en ligera, el segundo en media y el último en dura. El azar elige planta y espejo; la dificultad la marca la posición. Una planta no sale dos veces seguidas y como mucho dos veces por acto (en tramos distintos).
- En el acto I los tramos siguen la entrada de enemigos: ligera, solo Exvotos; media, se suman el Cireneo y algún Ojo suelto; dura, mezcla completa.
- Cada acto empieza algo por encima de donde acabó el anterior, con su propio catálogo de plantas y sus enemigos nuevos. Último recurso si los Dones corren más que los encuentros: +25 % de vida enemiga por acto.
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
- **Piezas 3D de las salas (decidido 2026-11-17, rama `feat/props-catedral-v2`).** Revisión en `walkthroughs/props-catedral-v2/`.
  - **Rastrillo (barrera):** reja de hierro negro que cae hasta el suelo; sustituye a la franja roja en el borde de arriba de cada sala y de la del jefe (también en el acto I), con la base sobre la línea de la barrera. Dos piezas de 104 px cubren la nave de pared a pared (cada una son dos tramos del modelo) y se dibujan con **sprites hardware** (libera 182 tiles del kit). Ya está bajado al acercarse a la sala; al matar al último enemigo **sube despacio (~0,9 s, 1 px/frame)** recortándose contra su borde superior para no flotar sobre el pasillo, y abre el paso al terminar de subir. La barrera trasera y la de abajo del jefe siguen como hoy.
  - **Sacos:** las barricadas son tramos de 64 px pegados que salen de una pared y acaban en un **remate** en escalón con un saco caído (el remate derecho es el izquierdo en espejo). Los tramos alternan **recto** y **con hueco** (falta un saco y otro está ladeado). Tono de arpillera oscurecido en el render.
  - **Bancos:** el grupo de 4 bancos tiene una variante con el **banco roto** en la segunda fila; sustituye a uno de cada cuatro grupos de las salas, elegido por posición (estable).
  - **Relicario nuevo** (templete dorado sobre base baja) sustituye al antiguo en todo el juego.
  - **Columna rota:** en «el balcón», una de las dos columnas es la rota (mismo fuste que la entera, cascotes en la base).
  - **Alambre:** el modelo de alambre de espino ya revisado sustituye a los rectángulos de «la alambrada», escalado a mitad de altura (tramos de 32×24 px, el doble de tramos por línea).
  - **Kit gráfico solo para las salas:** el kit hornea únicamente las posiciones que usan las salas, los pasillos y las lápidas. Con el rastrillo en sprites y el alambre a mitad de tamaño, las lápidas caben con margen dentro de las 1.024 tiles.
  - **Simetría izquierda/derecha:** toda pareja simétrica respecto al eje de la nave se coloca por el cuerpo del arte (`x_der = 208 - x_izq - ancho_cuerpo`) y hornea su fase exacta.

#### 6.13.7 Modo jefe: lógica común (decidido 2026-11-17, rama `feat/modo-jefe`; implementado)
Concreta §6.13.1 para el escenario por actos (§6.13.6). Objetivo: que meter un jefe nuevo sea rellenar una ficha (nombre, retrato, vida, fases y escolta) y escribir su IA, sin tocar la intro, la barra, las fases ni la victoria. Se prueba con el Abanderado tal como está hoy; su combate como jefe se ajusta en otra sesión.

**Secuencia del encuentro.**
1. **Sala del jefe:** un bloque de 2 pantallas (384 px), como un encuentro, con su barrera arriba.
2. **Entrada:** al cruzar el borde de abajo se cierra una barrera también detrás del héroe y empieza la intro.
3. **Intro:** el juego se congela; presentación con el nombre del jefe (y su título del Códice). Se salta con `START`. Al terminar, entra la música de jefe (§6.10).
4. **Cámara libre (decidido 2026-11-17):** la cámara sigue al héroe como en el resto del acto; solo se dispara desde la pantalla de abajo, así que fijarla no tiene sentido. El héroe se mueve por toda la sala. Por encima de la barrera de arriba la sala se cierra con una **reja** y, al otro lado, algo decorativo (que no se pueda tocar), para que la pantalla de arriba no quede vacía cuando el héroe sube al borde.
5. **Combate por fases** (abajo).
6. **Victoria:** el jefe muere; desaparecen su escolta e invocaciones; secuencia de victoria; pantalla de reliquia (marco dorado, §6.13.5); vuelve la música normal y se abren las dos barreras.
7. **Morir** durante el jefe reinicia la partida, como en cualquier otro sitio.

**Fases.**
- Cada jefe declara de 1 a 3 fases con el umbral de vida en que empieza cada una (por ejemplo 100 %, 66 %, 33 %). La IA del jefe solo pregunta «¿en qué fase estoy?».
- **Cambio de fase común a todos:** el jefe queda invulnerable ~1 s, se muestra una telegrafía (la misma para todos los jefes) y se renueva su escolta según la fase. Los disparos durante ese segundo no cuentan.
- La escolta, si la hay, es una lista por fase: qué enemigos, cuántos a la vez y cada cuánto vuelve uno que cae. Con la lista vacía el jefe pelea solo (§6.13.1).

**Decidido tras la ronda 2 (2026-11-17).** Esta es la versión que se programa:
- **Intro (B):** el juego se congela y la cámara se acerca ×2 al jefe dentro de la sala, en la pantalla de arriba, con un foco que oscurece los bordes. Abajo, la escena a oscuras con su nombre, su título y su frase, que el jefe dice con su voz. Se salta con `START`.
- **Voz del Abanderado:** la voz B de la ronda 2 (`walkthroughs/modo-jefe/assets/voz/`).
- **Barra de vida (C):** barra fina en la fila de arriba de la pantalla de abajo, desde el borde izquierdo hasta los corazones, **centrada en vertical con los corazones**; el nombre del jefe, debajo. Una marca en cada umbral de fase. Colores de la paleta (§6.10), sin primarios puros. Sustituye a la barra flotante sobre el enemigo durante el modo jefe.
- **Cambio de fase:** la marca de la barra salta rota y aparece el número romano de la nueva fase sobre el jefe, mientras este pasa ~1 s invulnerable. Sale del estilo de la barra; no hay más que elegir.
- **Victoria (A con la frase de B):** la cámara se acerca de nuevo ×2 al jefe y las dos pantallas se destiñen a blanco; abajo, en el mismo sitio que en la intro, su nombre tachado en rojo y su frase de derrota (el Abanderado: «El asta ha caído.»), también con su voz. Después, la pantalla de reliquia.
- **Ficha de cada jefe:** nombre, título, frase de entrada, frase de derrota, sus dos audios, vida, umbrales de fase y escolta por fase.
- **Ritmo de la intro (corregido tras verla en la ROM).** Cada cosa a su tiempo, con pausas; cifras `[TUNABLE-PLACEHOLDER]`:
  1. 0,0 s: se congela; se ve al jefe en la sala, sin acercar, ~0,8 s.
  2. 0,8–2,6 s: acercamiento lento ×1 → ×2 (con frenada al final) y el foco se cierra a la vez.
  3. Pausa ~0,6 s.
  4. Aparece el nombre (fundido ~0,5 s) y, ~0,4 s después, el título.
  5. Pausa ~0,6 s; entonces dice su frase y el texto aparece mientras la dice.
  6. Al acabar la voz, ~1,2 s quieto.
  7. Se aleja (~0,5 s), se va el texto, vuelve el juego y entra la música. En total, ~9 s. START la salta en cualquier momento.
- **Ritmo de la victoria:** congelado en su última pose ~1 s; acercamiento lento (~1,5 s); se destiñe (~1,5 s); se tacha el nombre (~0,6 s); pausa; dice su frase de derrota y se escribe; ~1,5 s quieto; reliquia. En total, ~8 s.

#### 6.13.8 Ejecuciones (remates / glory kills, 2026-11-18, rama `feat/remate`)
Mecánica de remate cuerpo a cuerpo para ritmo y recarga en combate:
- **Disparador:** un golpe que no mata y deja al enemigo a **≤ 50 % de su vida máxima** lo deja tambaleándose (`ENEMY_STATE_WOBBLE`) durante 180 frames (~3 s), quieto y con un pulso cálido de luz marfil/ocre (sin efectos neón, según §6.10). Con el rayo base (150 de daño), el Exvoto (250 HP) tambalea tras 1 disparo y el Cireneo (600 HP) tras 2 disparos.
- **Activación:** pulsar `L` a media/corta distancia (≤ 96 px de suelo) sobre el enemigo tambaleante más cercano, ejecutando la animación desde la dirección de entrada del héroe (8 ángulos).
- **Flujo:** el héroe queda invulnerable y bloqueado mientras transcurre la animación combinada (72 frames, ~1,2 s), la cámara acompaña suavemente hasta su posición final, y conserva 60 frames (~1 s) de invulnerabilidad con pulso marfil al terminar para reposicionarse. Al terminar, el enemigo muere de inmediato sin efectos estándar y el rayo del héroe queda recargado al instante (`weapons_ready_instant()`, sin encender auras de reliquia que no se posean).
- **Variantes integradas:**
  - **Exvoto:** agarre de muñecas, elevación y partición vertical en 96×96, dejando las dos mitades de cera en el suelo durante ~1 s (parpadeando al final).
  - **Cireneo (provisional hasta la ronda final A/B):** el héroe le arranca la cruz de la espalda, salta y lo atraviesa contra el suelo con ella (celda 116×116), dejando el cadáver atravesado en el suelo durante ~1 s antes de desaparecer.
- **Entrada con embestida previa (decisión del usuario, 2026-11-18):** la animación horneada empieza con el héroe a una distancia fija del enemigo (~30 px el Exvoto, ~42 px el Cireneo), pero `L` vale hasta 96 px; sin más, el héroe aparecía de golpe en ese punto. Ahora, al pulsar `L`, el héroe corre con su animación normal de andar, más rápido que al andar (~4 px por frame, [TUNABLE-PLACEHOLDER], tope ~0,3 s), hasta el punto exacto donde empieza el remate en la dirección elegida, mirando al enemigo; si ya está más cerca, retrocede ese poco sin dejar de mirarle. Durante la embestida el héroe ya es invulnerable y no dispara, y el enemigo deja de tambalearse y espera quieto, orientado como empieza su animación: el Exvoto se gira hacia el héroe (le agarra de frente) y el Cireneo le da la espalda (el héroe le arranca la cruz por detrás). El fotograma 0 horneado no se usa: el renderizador del lab lo saca distinto de la escena 3D (fallo pendiente), así que el remate arranca desde el fotograma 1, que se repite. Al llegar empieza la animación combinada sin salto.
- **Cámara pegada al héroe durante el remate:** la cámara sigue los pies del héroe tal como aparecen en cada fotograma de la animación (interpolados entre fotogramas para que no dé tirones), en vez de deslizarse en línea recta del punto de partida al final.
- **Pendiente de balance:** tunear el alcance de detección, la ventana de tambaleo, feedback y el equilibrio de la recarga instantánea.


#### 6.13.9 Encuentros tácticos: papeles, Ojo sin alcance y remate (decidido 2026-11-17, rama `docs/encuentros-tacticos`; vigente tras `feat/ojo-alcance`, 2026-11-19)
Corrige §6.13.6. **Motivo:** en las salas lo óptimo era quedarse abajo y matar lo que baja, aunque se cerrase la barrera de atrás. Toda la amenaza llegaba por un lado y todos los enemigos perseguían, así que la pelea acababa en la pantalla de abajo y la de arriba llegaba vacía. Esperar no costaba nada. **Referencias:** Doom 2016/Eternal, donde los enemigos débiles cuerpo a cuerpo no son la amenaza sino un recurso que se remata; Gears of War y XCOM, donde unos te clavan en la cobertura y otros te sacan de ella.

**Papeles de los enemigos.**
| Papel | Quién | Qué hace en la sala |
| :--- | :--- | :--- |
| **Te clava** | Ojo | Desde su puesto controla la sala con su línea de visión. Mientras te apunta, cúbrete o muévete. |
| **Te saca de la cobertura** | Exvoto | Viene a por ti en grupo y por los lados. Es también el recurso del remate. |
| **Guarda al Ojo y rompe la cobertura** | Cireneo | Espera junto al Ojo y embiste cuando te acercas. Si se estrella contra una pieza queda aturdido y se puede rematar. |
| **Ancla** | Ojo en el acto I; invocador desde el acto II | No baja: obliga a subir para abrir la barrera. |

- **Ojo sin alcance máximo:** solo cuenta la línea de visión; las columnas y estatuas se la cortan. Es un **tirador táctico, no un cazador:** cubierto tras una cobertura baja espera sin moverse ni disparar y, al salir, arranca el ciclo normal de apuntado (el héroe puede esquivar). Tras columnas y estatuas te sigue manteniendo la línea: se recoloca (correa que crece hasta toda la sala). Solo dos apuntan a la vez. Su aviso largo y legible (la mirada verde) es lo que hace justo no tener alcance máximo. **Palancas sin decidir:** velocidad de persecución y tiempo parado al apuntar (hoy anda a un tercio de la velocidad del héroe). Detalle y constantes: `walkthroughs/ojo-tactico/walkthrough.md`.
- **Guarnición:** Exvotos (y Cireneo desde la media) despiertos que se quedan junto al Ojo hasta que te acercas, los dañas o muere su Ojo. El Cireneo guardián es de guardia, no solo escolta.
- **Exvoto, flanqueo coordinado (sin programar):** se reúnen fuera del alcance del héroe y entran juntos; uno va de frente y los demás por los carriles laterales; si el héroe está agachado tras una cobertura baja, la rodean. Mantienen la esquiva del rayo.
- **Invocador (sin programar):** es un **enemigo nuevo con silueta propia**, no un Exvoto rezando: con el mismo dibujo no se distinguiría a quién disparar primero. Idea: levanta a los caídos si nadie lo interrumpe. Se aplaza al acto II, junto al Campanero y al Abanderado élite. En el acto I el ancla es el Ojo.

**Reglas de sala (se suman a las de §6.13.6).**
1. **Desde el primer momento en que el héroe puede dar a un Exvoto, algún Ojo puede darle a él.** Los Exvotos se colocan entre el héroe y el Ojo, en su línea de tiro.
2. **Los Ojos van en la mitad de arriba,** en su puesto. La cobertura buena (columnas y cobertura baja) va en medio y arriba; la entrada queda despejada.
3. **Composición tipo:** Exvotos arriba que bajan a flanquear, Ojos al fondo y algún Cireneo guardándolos.
4. Nada de embudos rectos hacia la entrada que pongan a la horda en fila delante del rayo.
- **El Ojo en toda sala (decidido 2026-11-18):** toda sala del acto I salvo el atrio lleva al menos un Ojo, porque es el ancla que obliga a subir. El Cireneo entra en media.
- **El atrio, primer encuentro fijo del acto:** solo Exvotos y espacio abierto; enseña el remate antes de meter presión. Es la única sala sin Ojo. La mecánica de remate existe (§6.13.8); la sala atrio aún no está en la ROM.
- **Catálogo:** el vigente y la propuesta v3 están en §6.13.6.
- **Sin programar:** flanqueo coordinado de los Exvotos, la sala atrio, el catálogo v3 y el invocador.

#### 6.13.10 Método de diseño de salas: una a una (decidido 2026-11-18)
Los sistemas (Ojo, flanqueo, Cireneo guardián, remate) se prueban **a través de salas concretas**, no en bloque: así el feedback es claro y la programación va atada a una prueba.
- **Una sala, una pregunta.** Cada sala se juega unos minutos con una sola pregunta y acaba en un veredicto: se queda, se cambia o se descarta. El registro vive en `walkthroughs/sala-<nombre>/plan_pruebas.md`.
- **Equipo de referencia fijo por sala** (la vara de medir, no todas las combinaciones): primera sala ligera, sin Dones; sala media, ~4 Dones de un equipo tipo; sala dura, ~8 (con 12 Dones por partida completa; [TUNABLE-PLACEHOLDER]). El equipo tipo se elige una vez con el usuario y no se toca. Que un equipo muy fuerte arrase una sala no es fallo de la sala; los Dones que rompen todas se buscan con el bot (`encuentros-bot`), no a mano.
- **Orden por mecánica nueva:** 1) la procesión ligera (Ojo con puesto fijo, cobertura baja); 2) el balcón (columnas y flanqueo de los Exvotos); 3) la primera sala media (Cireneo guardián). Después el resto del catálogo v3. El atrio (la mecánica de remate existe; la sala aún no está en la ROM) entra cuando se programe, sin prioridad: es un tutorial, no mide diversión.
- **Pasadas por sala:** como mucho dos (equipo de referencia; sin Dones en el atrio y la primera ligera). Un cambio por vuelta.
- **Primera prueba: partida de referencia.** Antes de rediseñar nada se juega la ROM actual 10 min puntuando cada sala (tensión, decisión, ¿repetir?) para tener una línea base de diversión y saber qué sala rediseñar primero. Plan en `walkthroughs/sala-atrio/plan_pruebas.md`.
