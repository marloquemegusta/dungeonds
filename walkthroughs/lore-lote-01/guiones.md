# Lote 01 de lore: 10 guiones cortos

Escritos contra `LORE.md`. Este archivo es la entrada directa del generador de vídeos (`codice-lore-video`, `render_guiones.py`).

**Cómo se lee cada guion**

- **Narrador:** una sola voz (Carmelo). Cada línea `- ` es una frase locutada y subtitulada.
- **Frase final:** `> Nombre: «frase»` es el aforismo del personaje, con su propia voz (tabla `## Voces`). `A + B` suenan a la vez, igualadas de volumen. Una voz `archivo:<ruta>` usa un audio ya grabado (p. ej. la frase recortada de la muestra que eligió el usuario).
- **Partes:** `### Parte N · <animación> · <modo> [· modificadores]` es lo que se ve. Puede haber tantas partes como haga falta; cambiar de parte = cambiar de animación (andar, cargar, mirar…).
- **Dos personajes:** `animA + animB` los pone juntos (B algo más bajo, detrás, con otro ritmo y el paso desfasado). Opcionales: `escala B 0.9`, `separación 140`.
- **Modo `cortes` (el habitual):** un plano por frase, con corte seco. Cada frase lleva al principio su etiqueta de plano entre corchetes (no se locuta ni se subtitula; en la cita va tras `>`):
  - `cerca` primer plano de busto; `S`, `SE`, `E`, `NE`, `N`, `NW`, `W`, `SW` hacia dónde mira (S = de frente, N = de espaldas).
  - `DIR origen>destino` viajan juntos; `A DIR …` y `B DIR …` cada uno por su lado; una posición sola = quieto ahí.
  - Posiciones: `centro`, `izq`, `der`, `fuera-izq`, `fuera-der`, `arriba`, `abajo`, `fuera-arriba`, `fuera-abajo` (combinables con `+`). Mirar S = bajar por la pantalla, N = subir.
  - Los planos con trayecto salen en plano general; los quietos llevan un acercamiento lento.
  - **Trayectos solo con el exvoto** (`exvoto_walk`, `exvoto_walk_b`): es el único con la zancada medida; con otros personajes los pies resbalarían. Los demás, quietos o andando en el sitio.
- **Otros modos:** `girando` (da vueltas) o una dirección fija. Modificadores: `lento N`, `inverso`, `una vez` (se queda en el último fotograma), `ida y vuelta`.
- **Ritmo de los trayectos:** por defecto `--paso natural` (anda a su ritmo, llega antes y sigue andando en el sitio); `--paso lento` estira el paso a todo el plano. También por plano con la ficha `natural`/`lento`.
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
- Jimena: archivo:walkthroughs/lore-lote-01/assets/cita_jimena_muestra3.mp3
- Aldonza: archivo:walkthroughs/lore-lote-01/assets/cita_aldonza_muestra.mp3
- Bartolomé: 5Nyqo2cUdr59EbFivYhz
- Leonor: pCiVQwaEUl8YwVxKhOCd
- Inés: archivo:walkthroughs/lore-lote-01/assets/ines_cita.mp3
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
### Parte 1 · exvoto_walk · cortes
- [cerca · S] Remedios fue la primera condenada en volverse cera.
- [SE] En Valdenoche, era ella quien hacía las velas de la Catedral.
- [S] El nombre también lo eligió ella. El pueblo tardó un invierno en aprenderlo, y luego nunca lo olvidó.
- [W der>izq] Con la cera y el pan de los diezmos alumbraba y daba de comer a quien no tenía nada.
### Parte 2 · exvoto_walk · cortes
- [N] El inquisidor Gaspar Valcárcel la acusó de robar a Dios. Y de llevar un nombre que no le dieron en la pila.
- [N centro>fuera-arriba] La condenaron a rezar dentro de la Catedral hasta el fin de los tiempos.
### Parte 3 · exvoto_walk + exvoto_walk_b · cortes
- [S arriba>centro] Y las figuras que había hecho con sus manos echaron a andar detrás de ella.
> [S] Remedios: «Que me fundan las veces que quieran. Seguiré siendo Remedios.»

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
### Parte 1 · cireneo_walk · cortes
- [cerca · S] El Tribunal le llamó cobarde por no disparar contra sus vecinos.
- [E] Bartolomé Ruiz era el más rápido de la Columna. Le llamaban el Liebre.
- [S] La noche de la Quiebra, una procesión de cera avanzó hacia las trincheras. En aquellos rostros reconoció a su pueblo.
- [W] Bajó el fusil. Y corrió. Martín Arce se quedó atrás para cubrirle.
### Parte 2 · cireneo_walk · cortes
- [N] Le encontraron días después en Valdenoche, escondido en el desván de la madre de Martín.
- [SW] El acta del Tribunal dice que volvió de rodillas y pidió que le clavaran la cruz a la espalda.
- [cerca · S] El acta la escribió el Tribunal.
### Parte 3 · cireneo_charge · cortes
- [S] Desde entonces, el Liebre solo sabe correr en línea recta. Hacia quien le mira.
> [cerca · S] Bartolomé: «Cobarde fue el que disparó.»

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
### Parte 1 · abanderado_walk · cortes
- [cerca · S] Íñigo Albar calló. Y el hombre al que amaba ardió en la plaza.
- [SE] El capitán había jurado que el estandarte jamás tocaría el suelo.
- [E] Lo sostenía a su lado su alférez, Lope de Ayala.
- [N] Cuando el Tribunal vino a por Lope, Íñigo bajó la mirada. Calló para conservar el mando.
### Parte 2 · abanderado_walk · cortes
- [SW] Desde entonces cose a la tela las mortajas de sus caídos, para que nadie se quede atrás.
- [cerca · S] La de Lope la lleva junto al asta, justo donde aprieta la mano.
- [S] La de Martín Arce está vacía.
> [cerca · S] Íñigo: «Mi silencio pesa más que el estandarte.»

## 08 · CÓDICE — LA CATEDRAL QUE NO TERMINA
### Parte 1 · corazon_walk · cortes
- [cerca · N] Dicen que el Altar retrocede un paso por cada plegaria de misericordia.
- [NE] Por eso el Tribunal prohibió rezarlas.
- [NW] La Iglesia levantó una catedral sobre Valdenoche para que el cielo volviera a responder.
- [N] Un día, el altar empezó a alejarse. La Iglesia lo llamó milagro, y prometió la salvación a quien llegara hasta él.
### Parte 2 · corazon_disparo · cortes
- [S] Pero la nave no termina.
- [cerca · S] La cruzada no terminó. Nadie se atrevió a darla por terminada.
> [S] Gaspar: «La misericordia es el camino más largo hacia Dios.»

## 09 · CÓDICE · II — LOS MONAGUILLOS
### Parte 1 · monaguillo_walk · cortes
- [cerca · S] El Tribunal condenó a los monaguillos por decir la verdad sobre un hombre de Dios.
- [SE] El padre Anselmo Ribas confesaba en la Sacristía de los Faroles.
- [S] Le gustaban los muchachos del coro. Demasiado.
- [SW] Los que obedecían cantaban en misa. Los que se negaban, dejaban de cantar.
- [N] Los condenaron a rezar para siempre.
### Parte 2 · abanderado_walk + monaguillo_walk · cortes
- [S] Nadie fue a buscarlos. Solo el capitán Íñigo Albar, que los recogió bajo su estandarte.
- [SE] Aún marchan tras él. Es la primera orden que no les pide nada a cambio.
> [S] Monaguillos: «Nos mandaron callar. Seguimos cantando.»

## 10 · CÓDICE · I — NO ES MI CORAZÓN
### Parte 1 · corazon_walk · cortes
- [cerca · S] Martín Arce recibió tres balas para que el hombre al que amaba pudiera huir.
- [SE] La noche de la Quiebra, cubrió la huida de Bartolomé.
- [S] Murió en brazos del capellán, Elías Montoro.
- [SW] Elías había bendecido aquel amor en secreto, en una capilla sin velas.
### Parte 2 · corazon_disparo · S · inverso · lento 5 · una vez
- Sin pólvora, con el muchacho frío entre las manos, pidió un arma.
- Dios le abrió el pecho, y le dio lo único que aún latía en la nave.
### Parte 3 · corazon_walk · cortes
- [cerca · S] Por eso, cuando le preguntan, Elías responde siempre lo mismo: no es mi corazón. Solo lo llevo.
> [S] Martín: «Llévame hasta el final, capellán.»

---

## Publicado

- **01 El Corazón Abierto** (2026-11-15): v1 con arranque en negro; v2 sin negro y frase fuerte primero; v3 recortada a 38 s (iteraciones en `guiones_iteraciones.md`). La v2 retuvo algo mejor que la v3.
- **03 Jimena y Aldonza** (2026-11-16): primera versión con puesta en escena plano a plano y paso natural. Es el modelo para los siguientes.

## Calendario: un vídeo al día, más cuidado

Regla: **nunca el mismo personaje en pantalla dos días seguidos**, y los vídeos que necesitan modelos nuevos van más tarde para dar margen. Los días 9 y 10 no tienen guion todavía.

| Día | Vídeo | Personaje en pantalla | Lo nuevo | Pendiente del usuario |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 08 La Catedral que no termina | Corazón Abierto | Columnas y bancos que desfilan a los lados (la nave sin fin); Elías mira hacia arriba; cameo del Ojo en la cita de Gaspar | *Looking up* de Mixamo (opcional) |
| 2 | 02 Remedios, la cerera | Exvoto | Reza de rodillas entre velas y se levanta | — |
| 3 | 07 Lope | Abanderado | Íñigo se tapa la cara | *Crying* de Mixamo |
| 4 | 05 Sor Leonor | Gaspar humano → el Ojo | Gaspar con su cabeza y el farol en la mano, que acaba convertido en el Ojo | Modelo 3D de Gaspar humano |
| 5 | 06 Inés | Exvoto | Anda triste, se arrodilla ante una vela | — |
| 6 | 04 El Liebre | Bartolomé → Cireneo | Bartolomé sin cruz y su crucifixión | Modelo sin cruz y la cruz aparte |
| 7 | 09 Los monaguillos | Monaguillo + Abanderado | Rezan ante el santo y marchan tras el estandarte | — |
| 8 | 10 No es mi corazón | Corazón Abierto | Cierre de la historia de Martín | — |
| 9 | El Campanero de Ánimas | Campanero (modelo existente) | Personaje nuevo | Aprobar su lore en `LORE.md` |
| 10 | El padre Anselmo | Por decidir | Qué fue del confesor | Decidir su destino y forma (`LORE.md` §9) |

**Material disponible:** animaciones de rezar de pie, rezar de rodillas, arrodillarse/levantarse (al revés), andar triste y andar renqueante (`assets/models/animations/`); props renderizados de vela, santo, relicario, bancos (entero, roto, volcado), columna y lápidas (`assets/environment/cathedral/props/render/`). Prop nuevo opcional: un sagrario o altar pequeño.

**Regla de imagen:** la voz cuenta el pasado y la imagen enseña el presente del condenado; solo hay modelos de la forma condenada, salvo variaciones hechas a propósito para un vídeo (Gaspar humano, Bartolomé sin cruz).

## Desglose del día 1: 08 La Catedral que no termina

| # | Frase | Qué se ve | Necesita |
| :--- | :--- | :--- | :--- |
| 1 | «Dicen que el Altar retrocede un paso por cada plegaria de misericordia.» | Primer plano de Elías de espaldas, mirando hacia arriba | *Looking up*; si no, de espaldas quieto |
| 2 | «Por eso el Tribunal prohibió rezarlas.» | De tres cuartos entre bancos rotos y volcados | Bancos |
| 3 | «La Iglesia levantó una catedral sobre Valdenoche…» | Plano general: Elías pequeño de espaldas entre dos hileras de columnas | Columnas |
| 4 | «Un día, el altar empezó a alejarse…» | Elías anda de espaldas en el sitio y las columnas pasan a sus lados hacia abajo | Columnas, andar |
| 5 | «Pero la nave no termina.» | Sigue andando; las columnas no dejan de pasar | Igual |
| 6 | «La cruzada no terminó. Nadie se atrevió a darla por terminada.» | Primer plano de frente: la carga del corazón | Carga |
| 7 | Gaspar: «La misericordia es el camino más largo hacia Dios.» | Aparece el Ojo alzando el farol (es su voz) | Ojo mirando |

Trabajo del coordinador: capa de props en el generador (delante/detrás del personaje) y props que desfilan; exportar *Looking up* si llega; montar y enviar para revisar.

## Reserva

- **Lo que sube desde abajo** (la Marea): su naturaleza está [ABIERTO] en `LORE.md` §9; se recupera cuando se decida.
