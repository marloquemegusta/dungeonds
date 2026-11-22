# Lote 01 de lore: 10 guiones cortos

Escritos contra `LORE.md`. Este archivo es la entrada directa del generador de vídeos (`codice-lore-video`, `render_guiones.py`).

> **Guiones preliminares.** Salvo los marcados como cerrados, estos guiones son una primera idea: sirven de punto de partida, no de versión final. Cada uno se reescribe en detalle el día que le toca (texto revisado contra `LORE.md` y puesta en escena plano a plano) y, al publicarlo, queda aquí tal cual se renderizó.
>
> **El guion lo contiene todo.** Cada plano dice qué personaje, qué animación, hacia dónde mira y qué objetos se ven. Cualquier ajuste que se haga al producir el vídeo se apunta en el guion, de modo que volver a ejecutar el generador rehaga el mismo vídeo. No hay desgloses aparte.
>
> **Cerrados:** 08 (pendiente de que el generador admita las fichas nuevas de props y las animaciones de rezar de Elías).

**Cómo se lee cada guion**

- **Narrador:** una sola voz (Carmelo). Cada línea `- ` es una frase locutada y subtitulada.
- **Silencio dentro de una frase:** `(pausa N)` con N en segundos (p. ej. `(pausa 1.2)`) calla ese tiempo en la voz; no aparece en los subtítulos.
- **Frase final:** `> Nombre: «frase»` es el aforismo del personaje, con su propia voz (tabla `## Voces`). `A + B` suenan a la vez, igualadas de volumen. Una voz `archivo:<ruta>` usa un audio ya grabado (p. ej. la frase recortada de la muestra que eligió el usuario).
- **Partes:** `### Parte N · <animación> · <modo> [· modificadores]` es lo que se ve. Puede haber tantas partes como haga falta; cambiar de parte = cambiar de animación (andar, cargar, mirar…).
- **Dos personajes:** `animA + animB` los pone juntos (B algo más bajo, detrás, con otro ritmo y el paso desfasado). Opcionales: `escala B 0.9`, `separación 140`.
- **Modo `cortes` (el habitual):** un plano por frase, con corte seco. Cada frase lleva al principio su etiqueta de plano entre corchetes (no se locuta ni se subtitula; en la cita va tras `>`):
  - `cerca` primer plano de busto; `S`, `SE`, `E`, `NE`, `N`, `NW`, `W`, `SW` hacia dónde mira (S = de frente, N = de espaldas).
  - `DIR origen>destino` viajan juntos; `A DIR …` y `B DIR …` cada uno por su lado; una posición sola = quieto ahí.
  - Posiciones: `centro`, `izq`, `der`, `fuera-izq`, `fuera-der`, `arriba`, `abajo`, `fuera-arriba`, `fuera-abajo` (combinables con `+`). Mirar S = bajar por la pantalla, N = subir.
  - Los planos con trayecto salen en plano general; los quietos llevan un acercamiento lento.
  - **Trayectos solo con el exvoto** (`exvoto_walk`, `exvoto_walk_b`): es el único con la zancada medida; con otros personajes los pies resbalarían. Los demás, quietos o andando en el sitio.
  - **Props** (de `assets/environment/cathedral/props/render/`, a la misma escala de píxel que el personaje; delante o detrás de él según su fila): `bancos` (bancos rotos, volcados y enteros repartidos alrededor); `columnas` (dos hileras de columnas a los lados, formando una nave, fijas; implica plano general); `columnas desfilan` (las mismas hileras bajan en bucle al paso del personaje, que anda en el sitio de espaldas `N`); `general` (fuerza plano general, personaje pequeño). Combinan con la dirección: `[N · columnas desfilan]`.
  - **Props, fichas nuevas:** cualquier prop de `assets/videos/props/` por su nombre, con posición opcional: `vela delante`, `santo der`, `relicario izq`, `detrás`. Posición = en pantalla: `delante` es más cerca de cámara (se dibuja sobre el personaje, a sus pies), `detrás` más lejos; `izq`/`der` a su lado; sin posición, a la derecha. `vela apagada` (misma vela sin llama), `bancos volcados` (solo rotos y volcados, como tras un registro), `bancos en fila` (dos filas de bancos enteros a los lados del pasillo, fijas o desfilando con las columnas), `lápidas` (sueltas en el suelo, siempre bajo los personajes; desfilan si desfilan las columnas), `pasa <prop> [izq|der]` (el prop entra por arriba y sale por abajo durante el plano). `bancos`, `columnas`, `lápidas`, `general` y `lejos` fuerzan plano general. Con `columnas desfilan` el suelo sube si el personaje mira al sur y baja si mira al norte, y el personaje marcha a 1,6x. En partes `una vez` la animación se ajusta para acabar justo al final del plano.
  - **Fichas de cámara/multitud (2.ª vuelta del 08):** `sigue` (la frase continúa el plano de la anterior sin corte: se construye un solo plano con la suma de duraciones y cada frase muestra su tramo; el desfile y la fase del paso no saltan; la ficha de la primera frase define la escena); `altar` (relicario sobre tarima baja con 6 velas encendidas, centrado arriba al fondo, detrás de todo; no desfila: se aleja un 18 % y sube un poco durante el plano; `altar lejos` = el mismo, diminuto); `solemne` (en desfiles, marcha a 1,0x en vez de 1,6x); `alejar` arranca sin fundido de entrada; `entero` (con `cerca`: el personaje entero y centrado, a la mayor escala que quepa; sin él, `cerca` es un busto con zoom); `alejar` (zoom out lento, un solo plano: del encuadre cercano al personaje entero con todo lo que abre; úsalo con `una vez`); `multitud N` (N figuras en bloque de 3 carriles y N/3 filas, más grandes delante que detrás, que avanzan juntas hacia cámara a su paso natural, mezclando TODAS las animaciones de la parte: `### Parte 5 · exvoto_walk + exvoto_walk_b + monaguillo_walk`). Una parte puede llevar más de dos animaciones con `+`, pero solo `multitud` usa más de dos. `cerca` en un plano escenificado ajusta la escala para que el personaje quepa entero (sin cabeza cortada). `una vez` en un plano: la animación ocupa el 85 % del plano y se queda en su último fotograma. Sprites a más resolución (celda 320×320, p. ej. `abanderado_solo`, sin cortejo): el generador los encuadra a la misma altura que uno de 160. Naves (A/B): columnas a ±3,4 Elías (cada hilera entera y con margen al borde) con un hueco de negro entre una y la siguiente (4,6 Elías); bancos en fila dentro de la nave (±1,5), dos hileras densas (un banco tras otro con medio banco de hueco, separación = 1,5 alturas de banco) y con el pasillo central libre; en `multitud` las filas alternas se desplazan medio hueco y se separan más en profundidad; la vela se dibuja a 0,45 de escala (vela votiva real); `vela delante` = hacia donde mira el personaje (de espaldas queda entre él y el fondo, algo a su derecha para que asome).
  - **Estilo del vídeo** (línea `Estilo: A|B|C` bajo el título del guion; `--estilo` la sobrescribe): **A** negro puro, sin suelo, props a escala real del juego (por defecto); **B** como A con suelo insinuado (sombras del lab de personajes y props y un charco tenue de suelo de la catedral con viñeta radial hacia el negro, solo bajo el grupo); **C** escala metafórica (props al tamaño que tenían en la DS, columnas que se leen como pasillo), con los props nuevos más nítidos.
  - **Fichas del 07 (Lope):** `medio` (plano de cintura para arriba; con `altar` lo dibuja detrás del personaje, a escala de plano general y sin recuadro negro, para no cortar el penacho); `multitud N` con dirección `N` y la primera animación como capitán (`abanderado_solo + monaguillo_walk`): el capitán va solo arriba a 2,3× y, detrás, la formación en bloque ordenado a 0,8×; `entero` con `cerca` en la parte `abanderado_derrota`. Citas lentas: `CHAR_SPEED` por personaje en `render_guiones.py` y `(pausa N)` en la frase.
  - **Fichas del 04 (Liebre):** `negro` (plano en negro, solo con la cabecera y los subtítulos: para contar con sonido lo que no conviene enseñar); `sfx <archivo> [fin]` (efecto de sonido, ruta desde la raíz: al empezar la frase o, con `fin`, al acabarla, y la frase siguiente espera a que termine).
  - **Cambiar de personaje en la cita:** una parte propia solo con la cita, p. ej. `### Parte 3 · ojo_look · cortes` y `> [S] Gaspar: «…»`.
- **Otros modos:** `girando` (da vueltas) o una dirección fija. Modificadores: `lento N`, `inverso`, `una vez` (se queda en el último fotograma), `ida y vuelta`.
- **Ritmo de los trayectos:** por defecto `--paso natural` (anda a su ritmo, llega antes y sigue andando en el sitio); `--paso lento` estira el paso a todo el plano. También por plano con la ficha `natural`/`lento`.
- **Pregunta final:** `> Pregunta: «¿…?»` justo después de la cita. El narrador la dice y añade «Deja tu veredicto en los comentarios»; la pregunta queda escrita arriba hasta el final del vídeo, también sobre el mosaico.
- **Cierre:** «Próximamente en tu Nintendo DS» y el mosaico los añade el generador. Opcional: `### Ficha · <imagen>` (ficha de la DS); este lote no la usa.

## Voces`). `A + B` suenan a la vez.
- Modificadores de una parte: `lento N`, `inverso`, `una vez` (se queda en el último fotograma), `ida y vuelta`.
- Dos personajes en una parte: `### Parte 1 · exvoto_walk + exvoto_walk_b · girando` los pone juntos (el segundo, algo más bajo, detrás y con el paso desfasado). Opcionales: `escala B 0.9`, `separación 140`.
- Dirección `cortes` (`### Parte 1 · exvoto_walk · cortes` o `cortes S,SE,W`): un plano por frase, corte seco y empuje lento. Cada frase admite una etiqueta `[ficha · ficha]` al inicio (o tras `>` en las citas: `> [S] Jimena + Aldonza: «...»`), que no se locuta ni se subtitula. Fichas: `cerca` (busto, de frente); `S`/`SW`/`W`/`NW`/`N`/`NE`/`E`/`SE` (ambas figuras miran ahí, andando en el sitio); `DIR pos>pos` (ambas viajan juntas); `A DIR pos>pos` y `B DIR pos>pos` (cada una por separado; una posición sola = quieta ahí). Posiciones: `centro`, `izq`, `der`, `fuera-izq`, `fuera-der`, `arriba`, `abajo`, `fuera-arriba`, `fuera-abajo` (combinables con `+`, p. ej. `der+arriba`). Mirar S = bajar por la pantalla, N = subir, E = derecha, W = izquierda; el ritmo del paso se ajusta a la distancia (0,6x-1,6x) y las salidas ocurren al final del plano. Ritmo del paso en planos con trayecto: `--paso lento` (por defecto, el trayecto dura todo el plano con la marcha ralentizada) o `--paso natural` (marcha a ritmo normal; llega antes y sigue andando en el sitio, las salidas se hacen al final del plano); también ficha `natural`/`lento` por plano.
- Opcional: una parte `### Ficha · <imagen>` muestra la ficha de doble pantalla de la DS. Este lote no la usa, para que la DS solo aparezca al final.

## Voces
- Narrador: 5egO01tkUjEzu7xSSE8M
- Elías: AZSMzFaZsuZZS1Qsqytv
- Remedios: BFUc9BU4Tlk58ZBkwuS3
- Jimena: archivo:assets/videos/voces/cita_jimena_muestra3.mp3
- Aldonza: archivo:assets/videos/voces/cita_aldonza_muestra.mp3
- Bartolomé: archivo:assets/videos/voces/bartolome_cita.mp3
- Leonor: pCiVQwaEUl8YwVxKhOCd
- Inés: archivo:assets/videos/voces/ines_cita.mp3
- Íñigo: iHCoxvyy4J2mUw5uRJED
- Gaspar: rC1yBQViNSR6g3kqT94H
- Monaguillos: PJca6lR0NZwKiJY56HrR
- Martín: b3pxCaASmiYnfI28HI7s

---

## 01 · CÓDICE · I — EL CORAZÓN ABIERTO
### Parte 1 · corazon_walk · girando
- Dios le abrió el pecho, y le puso dentro un corazón que no era suyo.
- Elías Montoro era capellán de la Columna de Lázaro.
- Bendecía lo que el Tribunal condenaba: el amor entre dos soldados de su propia columna, Martín y Bartolomé.
- La noche de la Quiebra no quedaba pólvora. Martín Arce se le moría en los brazos.
### Parte 2 · corazon_disparo · S · inverso · lento 5 · una vez
- Elías pidió un arma. Y Dios le escuchó... al pie de la letra.
- Desde entonces, cada milagro le consume un poco más... y la fe no le deja morir.
> Elías: «No es mi corazón. Solo lo llevo.»

## 02 · CÓDICE · II — REMEDIOS, LA CERERA
Estilo: A
### Parte 1 · exvoto_rezar · cortes
- [cerca · S · vela delante] La condenaron por robar a Dios. Ella solo daba de comer a quien no tenía nada.
- [SE · vela izq · vela der] Remedios era la cerera de Valdenoche. Con la cera y el pan de los diezmos alumbraba a los pobres y les llenaba la mesa.
- [S · vela delante] En la pila la bautizaron con nombre de varón. El de Remedios lo eligió ella, y el pueblo tardó un invierno en aprenderlo.
### Parte 2 · exvoto_rezar · cortes
- [N · vela apagada delante] El inquisidor Gaspar Valcárcel añadió otro cargo: vestir de mujer y renegar del nombre que Dios le dio.
- [cerca · S · vela apagada delante] La condenaron a rezar en la Catedral hasta el fin de los tiempos. Fue la primera en volverse cera.
### Parte 3 · exvoto_levantarse · cortes · una vez
- [S · vela izq · vela der] Se levantó, y las figuras que había hecho con sus manos echaron a andar detrás de ella.
### Parte 4 · exvoto_walk + exvoto_walk_b · cortes
> [S arriba>centro] Remedios: «Que me fundan las veces que quieran. Seguiré siendo Remedios.»
> Pregunta: «¿Remedios robó a Dios… o hizo lo que Dios no hacía?»

## 03 · CÓDICE · II — JIMENA Y ALDONZA
### Parte 1 · exvoto_walk + exvoto_walk_b · cortes
- [cerca · S] El Tribunal quiso separarlas. La Catedral las fundió en la misma cera.
- [S] Jimena y Aldonza compartían casa, mesa y lecho en Valdenoche.
- [SE] Todo el pueblo lo sabía. El capellán Elías las bendijo en secreto. Nadie dijo nada... hasta que llegó el Tribunal.
- [A W centro>fuera-izq · B E centro>fuera-der] Las condenaron, y ordenaron separarlas: una a cada extremo de la nave, a rezar por su alma.
### Parte 2 · exvoto_walk + exvoto_walk_b · cortes
- [A E izq · B W der] Y rezaron. La misma noche, la misma plegaria: no estar solas.
- [A E izq>centro · B W der>centro] En la Catedral, ninguna plegaria queda sin respuesta.
- [S arriba>centro] Hoy caminan juntas, y ya nadie podrá separarlas.
> [S] Jimena + Aldonza: «Nos mandaron rezar por nuestra alma. Rezamos la una por la otra.»

## 04 · CÓDICE · III — EL LIEBRE
Estilo: A
### Parte 1 · cireneo_sincruz_triste · cortes
- [cerca · entero · S] El Tribunal le llamó cobarde.
### Parte 2 · cireneo_sincruz_run · cortes
- [cerca · entero · E] Bartolomé Ruiz era el más rápido de la Columna. Le llamaban el Liebre.
### Parte 3 · exvoto_walk + exvoto_walk_b · cortes
- [S · multitud 9 · solemne] La noche de la Quiebra, una procesión de cera avanzó hacia las trincheras. En sus rostros vio a sus vecinos. A su familia. A sus amigos.
### Parte 4 · cireneo_sincruz_triste · cortes
- [cerca · entero · SW] Bajó el fusil.
### Parte 5 · cireneo_sincruz_run · cortes
- [cerca · entero · N] Y corrió.
- [cerca · entero · N · sigue] Martín Arce, el soldado al que amaba, se quedó atrás para cubrirle.
### Parte 6 · exvoto_walk · cortes · lento 1.5
- [cerca · entero · S] Días después le encontraron en casa de Inés, la madre de Martín. No sabía que su hijo había muerto por él.
### Parte 7 · cireneo_walk · cortes
- [cerca · entero · S] La cruz la pidió él. Para no volver a huir.
- [negro · sfx assets/videos/sfx/martillo_clavo.wav fin] Tadeo, el herrero, la clavó.
- [negro] No ha vuelto a tocar un clavo.
### Parte 8 · cireneo_charge · cortes
- [cerca · entero · E] Desde entonces solo corre en línea recta. Hacia quien le mira.
### Parte 9 · cireneo_walk · cortes
> [cerca · entero · S] Bartolomé: «El cobarde fue el que disparó.»
> Pregunta: «¿Cobarde… o el único valiente?»

## 05 · CÓDICE · IV — SOR LEONOR
### Parte 1 · ojo_walk · cortes
- [cerca · S] Dijo que no a un sacerdote. Y el Tribunal la condenó a ella.
- [SE] Sor Leonor era novicia en la Sacristía de los Faroles.
- [S] Sabía por qué los monaguillos del padre Anselmo dejaban de cantar.
- [SW] Cuando el padre fue a por ella, dijo que no. Y al día siguiente lo dijo en voz alta, ante el Tribunal.
### Parte 2 · ojo_look · cortes
- [E] El Gran Inquisidor Gaspar Valcárcel alzó su farol sobre el confesor... y no halló culpa.
- [cerca · S] Lo alzó sobre ella, y la halló.
### Parte 3 · ojo_sentence · S
- La condenaron por calumnia. Porque la linterna no ve culpables. Los fabrica.
> Leonor: «Dije que no. Que lo oiga toda la Catedral.»

## 06 · CÓDICE · II — INÉS
### Parte 1 · exvoto_walk · cortes
- [cerca · S] Inés Arce escondió en su desván al muchacho por el que murió su hijo.
- [S] Su hijo, Martín, servía en la Columna.
- [SE] Una noche llamó a su puerta un soldado empapado y temblando. Bartolomé, el desertor.
- [S] Inés no preguntó. Le dio pan, una manta y el desván.
### Parte 2 · exvoto_walk · cortes
- [SW] Ella no supo la verdad hasta el juicio.
- [W] El Tribunal los encontró a los dos, y la condenó por dar refugio a un cobarde.
- [N abajo>fuera-arriba] Hoy sube en procesión, nave arriba, siguiendo un latido que reconoce.
> [cerca · S] Inés: «Le di pan sin saber quién era. Se lo volvería a dar sabiéndolo.»

## 07 · CÓDICE · V — LOPE
Estilo: A
### Parte 1 · abanderado_solo · cortes · lento 1.5
- [cerca · S] Íñigo Albar calló. Y el hombre al que amaba ardió en la plaza.
- [SE · altar lejos · medio] Era capitán de la Columna y había jurado que su estandarte jamás tocaría el suelo.
- [E · vela der] Lo sostenía su alférez, Lope.
### Parte 2 · ojo_look · cortes
- [cerca · S] Cuando el Tribunal fue a por él, Íñigo pudo plantarle cara: «Yo también le amo. Atreveos a tocar al capitán».
### Parte 3 · abanderado_solo · cortes · lento 1.5
- [cerca · S] Era un pulso contra la Iglesia. Bajó la mirada. Calló para conservar el mando.
### Parte 4 · abanderado_derrota · cortes · una vez
- [cerca · entero · S] Lope ardió, y el estandarte cayó con él. Íñigo lo alzó y juró que nunca más caería, ni nadie se quedaría atrás.
### Parte 5 · abanderado_solo + monaguillo_walk · cortes · lento 1.5
- [N · multitud 9 · solemne] Condujo a la Columna a la Catedral, al servicio de quien lo quemó.
### Parte 6 · abanderado_solo · cortes · lento 1.5
- [SW] Hoy cose a la tela la mortaja de cada caído.
- [cerca · S] La de Lope la lleva junto al asta, justo donde aprieta la mano.
- [S · vela apagada delante] Solo una va vacía: la de Martín Arce, que murió cubriendo la huida de otro.
> [cerca · S] Íñigo: «Mi silencio (pausa 0.5) pesa más que el estandarte.»
> Pregunta: «¿Habrías plantado tú cara al Tribunal?»

## 08 · CÓDICE — LA CATEDRAL QUE NO TERMINA
Estilo: A
### Parte 1 · corazon_rezar · cortes
- [cerca · N · vela delante] Dicen que el Altar retrocede un paso por cada plegaria de misericordia.
### Parte 2 · corazon_levantarse · cortes · una vez
- [NE · bancos en fila · vela izq] Por eso el Tribunal de la Luz prohibió rezarlas.
### Parte 3 · corazon_walk · cortes
- [general · N · columnas desfilan · bancos en fila · altar · solemne] Valdenoche llevaba años de hambre, y el cielo había dejado de responder.
- [sigue] La Iglesia levantó una catedral en lo alto de la colina.
- [sigue] Un día, el altar empezó a alejarse.
- [sigue] La Iglesia lo llamó milagro: quien llegara al Altar devolvería la voz al cielo.
- [cerca · S] Y proclamó una cruzada.
### Parte 4 · abanderado_solo · cortes · lento 2
- [cerca · S · entero] Los hombres de Valdenoche formaron la Columna de Lázaro, y entraron armados.
### Parte 5 · exvoto_walk + exvoto_walk_b + monaguillo_walk · cortes
- [S · multitud 12] Entre ellos y el Altar, Dios había puesto a los herejes: sus madres, sus vecinos, sus hermanos.
### Parte 6 · corazon_walk · cortes
- [general · N · columnas desfilan · lápidas · altar lejos] Pero la nave no termina.
### Parte 7 · corazon_disparo · cortes · inverso · una vez
- [cerca · S · alejar] Y la cruzada nunca se dio por terminada.
### Parte 8 · ojo_look · cortes
> [S · vela apagada delante] Gaspar: «La misericordia es el camino más largo hacia Dios. (pausa 1.2) Por eso la prohibimos.»

**Notas del 08 (2026-11-16):**
- Arranca con el gesto prohibido (Elías reza y enciende una vela); la vela vuelve, apagada, a los pies del Ojo en la cita: el Tribunal sobre el sitio donde rezó.
- Frase 9 es la frase fuerte de la mitad: el narrador los llama «herejes» y en la misma frase dice quiénes son. Cuenta la Marcha y la guerra contra el propio pueblo (`LORE.md` §4.5-6) sin afirmar nada abierto (ni por qué se alargó la nave ni qué hay en el Altar).
- Apariciones breves del Abanderado y los exvotos: anticipan Remedios (día 2) y Lope (día 3).
- Necesita: `corazon_rezar` (rezar de rodillas) y `corazon_levantarse` (de rodillas a de pie) desde `assets/models/animations/pray/`; props re-renderizados a la densidad de píxel de los personajes del Códice; las fichas nuevas de props.
- Primera prueba sin voz (con el guion anterior y props a escala de la DS, fuera de escala): `walkthroughs/lore-video-08/`.

## 09 · CÓDICE · II — LOS MONAGUILLOS
### Parte 1 · monaguillo_walk · cortes
- [cerca · entero · S] El Tribunal condenó a los monaguillos por decir la verdad sobre un hombre de Dios.
- [SE] El padre Anselmo Ribas confesaba en la Sacristía de los Faroles.
- [S] Le gustaban los muchachos del coro. Demasiado.
- [SW] Los que obedecían cantaban en misa. Los que se negaban, dejaban de cantar.
- [N] Los condenaron a rezar para siempre.
### Parte 2 · abanderado_solo + monaguillo_walk · cortes · lento 1.5
- [N · multitud 9 · solemne] Nadie fue a buscarlos. Solo el capitán Íñigo Albar, que los recogió bajo su estandarte.
### Parte 3 · monaguillo_walk · cortes
- [S · multitud 9 · solemne] Aún marchan tras él. Es la primera orden que no les pide nada a cambio.
> [cerca · entero · S] Monaguillos: «Nos mandaron callar. Seguimos cantando.»
> Pregunta: «¿Habrías hablado tú, sabiendo el castigo?»

## 10 · CÓDICE · I — NO ES MI CORAZÓN
### Parte 1 · corazon_walk · cortes
- [cerca · S] En el pecho de este capellán late el corazón de un soldado muerto.
- [SE] La noche de la Quiebra, Martín Arce cubrió la huida del hombre al que amaba, Bartolomé.
- [S] Y murió por él, en brazos de Elías Montoro.
- [SW] Elías había bendecido aquel amor en secreto, en una capilla sin velas.
### Parte 2 · corazon_disparo · S · inverso · lento 5 · una vez
- Sin pólvora, con el muchacho frío entre las manos, pidió un arma.
- Dios le abrió el pecho, y le puso dentro el corazón de Martín.
### Parte 3 · corazon_walk · cortes
- [N] Su madre, Inés, aún sube nave arriba siguiendo ese latido.
- [cerca · entero · S] Cuando le preguntan, Elías responde siempre lo mismo: no es mi corazón. Solo lo llevo.
> [cerca · S] Martín: «Llévame hasta el final, capellán.»
> Pregunta: «¿Quién está más vivo: el que murió o el que lo lleva?»

---

## Publicado

Publicados a 2026-11-17: **01, 03 y 08**, nada más. Los MP4 de 02, 04-07, 09 y 10 que hay en `assets/videos/` son pruebas antiguas del lote, con el cierre viejo y sin la puesta en escena final; cada uno se rehace el día que le toca en el calendario.

**Cifras de partida (2026-11-17):** ~2.200 vistas por vídeo en Instagram, 600-800 en TikTok y ~500 en YouTube Shorts (el primero, en 3 días). Muy pocos comentarios.

**Cierre con pregunta moral (desde el 02):** para pedir comentarios, cada vídeo acaba con una pregunta moral de respuesta corta (sí/no o elegir entre dos) tras la cita del personaje, dicha por el narrador y seguida de «Deja tu veredicto en los comentarios». Para hacerle sitio, la historia se acorta unos 10 s quitando frases de contexto del medio (nunca el arranque ni la cita). La misma pregunta abre el texto del post y se fija como primer comentario. Al 08 se le fija en comentarios «¿Rezarías la plegaria, sabiendo que aleja el altar?».

| Vídeo | Pregunta | Vistas IG / TikTok / YT | Comentarios | Por 1.000 vistas |
| :--- | :--- | :--- | :--- | :--- |
| 01, 03, 08 (sin pregunta) | — | | | |
| 02 Remedios | ¿Remedios robó a Dios… o hizo lo que Dios no hacía? | | | |
| 07 Lope | ¿Habrías plantado tú cara al Tribunal? | | | |
| 04 El Liebre | ¿Cobarde… o el único valiente? | | | |
| 10 No es mi corazón | ¿Quién está más vivo: el que murió o el que lo lleva? | | | |

- **01 El Corazón Abierto** (2026-11-15): v1 con arranque en negro; v2 sin negro y frase fuerte primero; v3 recortada a 38 s. La v2 retuvo algo mejor que la v3.
- **03 Jimena y Aldonza** (2026-11-16): primera versión con puesta en escena plano a plano y paso natural. Es el modelo para los siguientes.
- **08 La Catedral que no termina** (2026-11-17): `assets/videos/lore01_08_la_catedral_que_no_termina.mp4`, estilo A, 67,9 s. TikTok a mano; Instagram y YouTube por Metricool. Textos de los posts:
  - **Título (YouTube y portada):** «La catedral que no termina · Códice». Alternativa: «Rezar aleja el altar · Códice».
  - **TikTok e Instagram:**
    > Dicen que el Altar retrocede un paso por cada plegaria de misericordia.
    > Por eso el Tribunal de la Luz prohibió rezarlas.
    >
    > La Iglesia prometió la salvación a quien llegara hasta él.
    > Nadie ha llegado. La cruzada nunca se dio por terminada.
    >
    > Próximamente en tu Nintendo DS.
    >
    > #pixelart #nintendods #gamedev #indiedev #darkfantasy #gothic #lore #homebrew
  - **Descripción de YouTube:**
    > Valdenoche levantó una catedral para que el cielo volviera a responder. Un día, el altar empezó a alejarse. La Columna de Lázaro entró armada para alcanzarlo, y al otro lado la esperaban sus propios vecinos.
    >
    > Próximamente en tu Nintendo DS.
    >
    > #Shorts #pixelart #nintendods #gamedev #darkfantasy
- **02 Remedios, la cerera** (lista 2026-11-17, sin publicar): `assets/videos/lore01_02_remedios_la_cerera.mp4`, estilo A, 75,2 s. Primer vídeo con cierre de pregunta moral: la pregunta queda escrita arriba hasta el final y también sale como subtítulo mientras el narrador la dice (decisión del usuario: dejar las dos). TikTok a mano; Instagram y YouTube por Metricool. Textos de los posts:
  - **Título (YouTube y portada):** «Remedios, la cerera · Códice». Alternativa: «¿Robó a Dios? · Códice».
  - **TikTok e Instagram:**
    > ¿Remedios robó a Dios… o hizo lo que Dios no hacía?
    >
    > Con la cera y el pan de los diezmos alumbraba a los pobres de Valdenoche y les llenaba la mesa.
    > El Tribunal la condenó a rezar en la Catedral hasta el fin de los tiempos. Fue la primera en volverse cera.
    >
    > Deja tu veredicto en los comentarios.
    > Próximamente en tu Nintendo DS.
    >
    > #pixelart #nintendods #gamedev #indiedev #darkfantasy #gothic #lore #homebrew
  - **Descripción de YouTube:**
    > ¿Remedios robó a Dios… o hizo lo que Dios no hacía? La cerera de Valdenoche repartía entre los pobres la cera y el pan de los diezmos. La bautizaron con nombre de varón; el de Remedios lo eligió ella. El inquisidor Gaspar Valcárcel la condenó a rezar en la Catedral para siempre. Fue la primera en volverse cera, y la primera en levantarse.
    >
    > Deja tu veredicto en los comentarios.
    > Próximamente en tu Nintendo DS.
    >
    > #Shorts #pixelart #nintendods #gamedev #darkfantasy
  - **Comentario fijado (en las tres redes):** «¿Remedios robó a Dios… o hizo lo que Dios no hacía?»
- **07 Lope** (lista 2026-11-19, sin publicar): `assets/videos/lore01_07_lope.mp4`, estilo A, 88,3 s (el usuario no quiere recortarlo). Animación nueva `abanderado_derrota` (el estandarte cae al suelo cuando arde Lope; Íñigo se derrumba, golpea el suelo y recoge el asta); el Ojo aparece como el Tribunal; los monaguillos solo en el plano de la Columna. Textos de los posts:
  - **Título (YouTube y portada):** «Íñigo y Lope · Códice». Alternativa: «¿Habrías plantado cara al Tribunal? · Códice».
  - **TikTok e Instagram:**
    > ¿Habrías plantado tú cara al Tribunal?
    >
    > Íñigo Albar era capitán y pudo salvar a Lope. Bastaba con decir «yo también le amo».
    > Calló para conservar el mando, y Lope ardió en la plaza. Ahora cose a su estandarte la mortaja de cada caído.
    >
    > Deja tu veredicto en los comentarios.
    > Próximamente en tu Nintendo DS.
    >
    > #pixelart #nintendods #gamedev #indiedev #darkfantasy #gothic #lore #homebrew
  - **Descripción de YouTube:**
    > ¿Habrías plantado tú cara al Tribunal? El capitán Íñigo Albar juró que el estandarte de la Columna de Lázaro jamás tocaría el suelo. Cuando el Tribunal de la Luz fue a por su alférez Lope de Ayala, Íñigo tenía rango para exigir una excepción y no se atrevió. Calló para conservar el mando, y Lope ardió. Hoy cose a la tela la mortaja de cada caído, para que nadie se quede atrás.
    >
    > Deja tu veredicto en los comentarios.
    > Próximamente en tu Nintendo DS.
    >
    > #Shorts #pixelart #nintendods #gamedev #darkfantasy
  - **Comentario fijado (en las tres redes):** «¿Habrías plantado tú cara al Tribunal?»

- **04 El Liebre** (lista 2026-11-20, sin publicar): `assets/videos/lore01_04_el_liebre.mp4`, estilo A, 74,7 s (la historia acaba a los 60 s; el resto es la pregunta y el cierre). Versión simplificada tras 9 pruebas fallidas: solo animaciones que ya funcionaban (Mixamo tal cual y las del juego), sin poses montadas a mano; lo que no se puede animar bien se cuenta con otro personaje (Inés), con el resultado (Bartolomé ya en la cruz) o con sonido sobre negro (el martillo de Tadeo). Todos los planos de personaje a cuerpo entero. Textos de los posts:
  - **Título (YouTube y portada):** «El Liebre · Códice». Alternativa: «¿Cobarde o el único valiente? · Códice».
  - **TikTok e Instagram:**
    > ¿Cobarde… o el único valiente?
    >
    > La noche de la Quiebra, Bartolomé Ruiz vio a sus vecinos avanzar hacia las trincheras y bajó el fusil.
    > Huyó. Martín, el soldado al que amaba, murió cubriéndole. La cruz que hoy carga la pidió él, para no volver a huir.
    >
    > Deja tu veredicto en los comentarios.
    > Próximamente en tu Nintendo DS.
    >
    > #pixelart #nintendods #gamedev #indiedev #darkfantasy #gothic #lore #homebrew
  - **Descripción de YouTube:**
    > ¿Cobarde… o el único valiente? Bartolomé Ruiz, el Liebre, era el más rápido de la Columna de Lázaro. La noche de la Quiebra, una procesión de cera avanzó hacia las trincheras y en sus rostros reconoció a su pueblo. Se negó a disparar y corrió. Martín Arce, el soldado al que amaba, se quedó atrás para cubrirle. Le encontraron escondido en casa de Inés, la madre de Martín. El Tribunal le llamó cobarde; la cruz la pidió él. Tadeo, el herrero, la clavó, y no ha vuelto a tocar un clavo.
    >
    > Deja tu veredicto en los comentarios.
    > Próximamente en tu Nintendo DS.
    >
    > #Shorts #pixelart #nintendods #gamedev #darkfantasy
  - **Comentario fijado (en las tres redes):** «¿Cobarde… o el único valiente?»

- **09 Los monaguillos** (lista 2026-11-21, sin publicar): `assets/videos/lore01_09_los_monaguillos.mp4`, estilo A, 57,8 s. Dos animaciones ya probadas (monaguillo y abanderado), Columna de espaldas tras Íñigo y después de frente hacia cámara solo con monaguillos. Textos de los posts:
  - **Título (YouTube y portada):** «Los monaguillos · Códice». Alternativa: «¿Habrías hablado tú? · Códice».
  - **TikTok e Instagram:**
    > ¿Habrías hablado tú, sabiendo el castigo?
    >
    > Los monaguillos de la Sacristía de los Faroles dijeron la verdad sobre un hombre de Dios.
    > El Tribunal los condenó a rezar para siempre. Solo el capitán Íñigo Albar los recogió bajo su estandarte.
    >
    > Deja tu veredicto en los comentarios.
    > Próximamente en tu Nintendo DS.
    >
    > #pixelart #nintendods #gamedev #indiedev #darkfantasy #gothic #lore #homebrew
  - **Descripción de YouTube:**
    > ¿Habrías hablado tú, sabiendo el castigo? Los monaguillos eran los muchachos del coro de la Sacristía de los Faroles. El padre Anselmo Ribas los confesaba: los que obedecían cantaban en misa; los que se negaban dejaban de cantar. Cuando dijeron la verdad, el Tribunal de la Luz los condenó a rezar para siempre. Nadie fue a buscarlos, salvo el capitán Íñigo Albar, que los recogió bajo su estandarte. Aún marchan tras él: la primera orden que no les pide nada a cambio.
    >
    > Deja tu veredicto en los comentarios.
    > Próximamente en tu Nintendo DS.
    >
    > #Shorts #pixelart #nintendods #gamedev #darkfantasy
  - **Comentario fijado (en las tres redes):** «¿Habrías hablado tú, sabiendo el castigo?»

- **10 No es mi corazón** (lista 2026-11-22, sin publicar): `assets/videos/lore01_10_no_es_mi_corazon.mp4`, estilo A, 66,1 s. Dos animaciones de Elías (andar y el disparo al revés, que abre los brazos), Inés como pista final y la cita de Martín sobre el corazón en busto, a voz lenta (0,8). Textos de los posts:
  - **Título (YouTube y portada):** «No es mi corazón · Códice». Alternativa: «El corazón de Martín · Códice».
  - **TikTok e Instagram:**
    > ¿Quién está más vivo: el que murió o el que lo lleva?
    >
    > La noche de la Quiebra, Martín Arce murió cubriendo la huida del hombre al que amaba, en brazos del capellán Elías Montoro.
    > Elías pidió un arma. Dios le abrió el pecho y le puso dentro el corazón de Martín.
    >
    > Deja tu veredicto en los comentarios.
    > Próximamente en tu Nintendo DS.
    >
    > #pixelart #nintendods #gamedev #indiedev #darkfantasy #gothic #lore #homebrew
  - **Descripción de YouTube:**
    > ¿Quién está más vivo: el que murió o el que lo lleva? Elías Montoro era capellán de la Columna de Lázaro y bendecía en secreto el amor de dos de sus soldados, Martín y Bartolomé. La noche de la Quiebra, Martín cubrió la huida de Bartolomé y murió en brazos de Elías. Sin pólvora, el capellán pidió un arma, y Dios le abrió el pecho y le puso dentro el corazón de Martín. Su madre, Inés, aún sube nave arriba siguiendo ese latido. Elías responde siempre lo mismo: no es mi corazón. Solo lo llevo.
    >
    > Deja tu veredicto en los comentarios.
    > Próximamente en tu Nintendo DS.
    >
    > #Shorts #pixelart #nintendods #gamedev #darkfantasy
  - **Comentario fijado (en las tres redes):** «¿Quién está más vivo: el que murió o el que lo lleva?»

## Calendario: un vídeo al día, más cuidado

Regla: **nunca el mismo personaje en pantalla dos días seguidos**, y los vídeos que necesitan modelos nuevos van más tarde para dar margen. Los días 9 y 10 no tienen guion todavía.

| Día | Vídeo | Personaje en pantalla | Lo nuevo | Pendiente del usuario |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 08 La Catedral que no termina | Corazón Abierto | Guion reescrito (la Marcha y la guerra contra el propio pueblo); Elías reza y enciende una vela; columnas y bancos que desfilan; apariciones del Abanderado, los exvotos y el Ojo | — |
| 2 | 02 Remedios, la cerera | Exvoto | Reza de rodillas entre velas y se levanta | — |
| 3 | 07 Lope | Abanderado | Íñigo suelta el asta, se derrumba y golpea el suelo (`abanderado_derrota`); el Ojo como el Tribunal; la Columna de monaguillos | — (hecho) |
| 4 | 05 Sor Leonor | El Ojo (condenado) | El Ojo recreando su acción del pasado (decisión 2026-11-21: sin modelo de Gaspar humano) | — |
| 5 | 06 Inés | Exvoto | Anda triste, se arrodilla ante una vela | — |
| 6 | 04 El Liebre | Bartolomé → Cireneo | Bartolomé sin cruz y su crucifixión | Modelo sin cruz y la cruz aparte |
| 7 | 09 Los monaguillos | Monaguillo + Abanderado | Rezan ante el santo y marchan tras el estandarte | — |
| 8 | 10 No es mi corazón | Corazón Abierto | Cierre de la historia de Martín | — |
| 9 | El Campanero de Ánimas | Campanero (modelo existente) | Personaje nuevo | Aprobar su lore en `LORE.md` |
| 10 | El padre Anselmo | Por decidir | Qué fue del confesor | Decidir su destino y forma (`LORE.md` §9) |

**Material disponible:** animaciones de rezar de pie, rezar de rodillas, arrodillarse/levantarse (al revés), andar triste y andar renqueante (`assets/models/animations/`); props renderizados de vela, santo, relicario, bancos (entero, roto, volcado), columna y lápidas (`assets/environment/cathedral/props/render/`). Prop nuevo opcional: un sagrario o altar pequeño.

**Regla de imagen:** la voz cuenta el pasado y la imagen enseña el presente del condenado; solo hay modelos de la forma condenada. Todo es metafórico: los personajes, tal como están ahora, recrean sus acciones del pasado (decisión del usuario, 2026-11-21: no se hace Gaspar humano). Excepción ya hecha a propósito: Bartolomé sin cruz.
