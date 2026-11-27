# Lote 02 de lore: gente nueva

Escritos contra `LORE.md`. Entrada directa del generador (`codice-lore-video`, `render_guiones.py`), con el mismo formato que `lote-01.md` (sección «Cómo se lee cada guion»; no se repite aquí).

> **Guiones preliminares.** Salvo los marcados como cerrados, son una primera idea. Cada uno se reescribe en detalle el día que le toca y, al publicarlo, queda aquí tal cual se renderizó.
>
> **Cerrados:** 01 (Los Bebés) y 02 (Gaspar), publicados abajo tal cual se renderizaron.

**Lo que trae este lote:** personas que el lore ya nombraba sin vídeo propio (Martín, Gaspar, Tadeo, la Columna) y las dos figuras nuevas de `LORE.md` (los Bebés y don Tomás, el Párroco). Anselmo queda fuera hasta decidir qué fue de él (`LORE.md` §9).

## Calendario

Regla del lote 01: nunca el mismo personaje en pantalla dos días seguidos.

| Día | Vídeo | En pantalla | Pregunta final | Pendiente |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 01 Los Bebés | Bebés y Remedios | ¿Merecía un nombre quien no llegó a bautizarse? | — |
| 2 | 02 Gaspar | El Ojo | ¿Juzgar sin mirar es justicia? | — |
| 3 | 03 Don Tomás | Párroco y monaguillos | ¿Habrías abierto la puerta? | Animaciones del Párroco en el generador; voz de Tomás |
| 4 | 04 Martín Arce | Corazón Abierto | ¿Murió por amor o por la Columna? | — |
| 5 | 05 La Columna de Lázaro | Abanderado | ¿Seguirías a quien no puede morir? | — |
| 6 | 06 Tadeo, el herrero | Cireneo | ¿Es culpable el que clava por orden? | Voz de Tadeo; decidir qué fue de Tadeo |
| 7 | 07 El que calló y el que se plantó | Párroco frente al Abanderado | ¿Quién de los dos pecó? | Escribir en `LORE.md` que Tomás marcha bajo el estandarte de Íñigo |

**Material nuevo:** `exvoto_bebe` y `exvoto_parroco` (andar, rezar de pie, rezar de rodillas, levantarse; el Párroco también corre) en `assets/models/characters/`. Ninguno tiene la zancada medida: con ellos, planos quietos o andando en el sitio; los trayectos, solo con el exvoto.

## Voces
- Narrador: 5egO01tkUjEzu7xSSE8M
- Elías: AZSMzFaZsuZZS1Qsqytv
- Remedios: BFUc9BU4Tlk58ZBkwuS3
- Bartolomé: archivo:assets/videos/voces/bartolome_cita.mp3
- Íñigo: iHCoxvyy4J2mUw5uRJED
- Gaspar: rC1yBQViNSR6g3kqT94H
- Monaguillos: PJca6lR0NZwKiJY56HrR
- Martín: b3pxCaASmiYnfI28HI7s

Por elegir: Tomás (voz grave, mayor, de cura de pueblo) y Tadeo.

---

## 01 · CÓDICE · II — LOS BEBÉS
Estilo: A
### Parte 1 · exvoto_bebe_rezar · cortes
- [cerca · S · vela delante] En Valdenoche hubo niños que nunca tuvieron nombre.
- [S · vela izq · vela der] Fueron los años del hambre. Muchos murieron antes de llegar a la pila.
- [cerca · S · vela apagada delante] Sin bautismo, la Iglesia no les dio nombre (pausa 0.6) ni tierra sagrada. Los enterraron fuera del camposanto, junto al camino.
### Parte 2 · exvoto_rezar · cortes
- [SE · vela delante] Sus madres fueron a ver a Remedios, la cerera.
- [cerca · S · vela izq · vela der] Y Remedios les hizo uno de cera por cada niño. Para que tuvieran un sitio en la iglesia.
### Parte 3 · exvoto_levantarse · cortes · una vez
- [S · vela izq · vela der] Cuando el Tribunal la condenó, Remedios se volvió cera. Y se levantó.
### Parte 4 · exvoto_walk + exvoto_bebe_gatear · cortes
- [S] Y los niños de cera fueron tras ella.
- [S · multitud 9 · solemne] Desde entonces suben nave arriba, en su procesión. Ella no ha vuelto a quedarse sola. Ellos tampoco.
### Parte 5 · exvoto_bebe_gatear · cortes
> [S · vela delante] Remedios: «No les dieron nombre. (pausa 0.6) Yo les di cera.»
> Pregunta: «¿Merecía un nombre quien no llegó a bautizarse?»

**Notas del 01:**
- Enlaza con el 02 del lote 01 (Remedios): explica qué eran «las figuras que había hecho».
- Los Bebés gatean (`exvoto_bebe_gatear`, `walkthroughs/bebe-gatear/`), nunca andan erguidos. Falta comprobar en el render que `multitud` mezcla bien el exvoto con el Bebé, que es más pequeño.

## 02 · CÓDICE · IV — GASPAR
### Parte 1 · ojo_look · cortes · lento 2
- [cerca · entero · S] Gaspar Valcárcel se arrancó los ojos para no volver a perdonar.
- [SE] Era el Gran Inquisidor del Tribunal de la Luz. Juzgaba en la Sacristía de los Faroles.
- [S · vela apagada delante] La primera a la que juzgó fue Remedios, la cerera.
- [cerca · S] La miró a la cara. Vio a quien repartía el pan de los diezmos entre los pobres. (pausa 0.6) Y dudó.
### Parte 2 · ojo_walk · cortes · lento 2
- [negro] Firmó la condena igual. Esa noche se arrancó los ojos, para que no volviera a pasar.
- [cerca · entero · S] Decidió que la mirada humana era propensa al perdón. Y alzó un farol en su lugar.
- [SW] Sus inquisidores hicieron lo mismo.
### Parte 3 · ojo_sentence · S · lento 1.5
- Desde entonces firmó todas las condenas: Lope, Leonor, Simón, los monaguillos. El farol no ha absuelto a nadie.
### Parte 4 · ojo_look · cortes · lento 2
> [cerca · entero · S] Gaspar: «Los ojos se apiadan. (pausa 0.8) La luz, no.»
> Pregunta: «¿Juzgar sin mirar es justicia?»

## 03 · CÓDICE · II — DON TOMÁS
### Parte 1 · exvoto_parroco_rezar · cortes
- [cerca · S] Don Tomás Ayuso se puso delante. Todavía no se ha apartado.
- [SE] Era el cura de Valdenoche desde antes de la Catedral. Bautizó a medio pueblo.
- [S] Los monaguillos del coro eran muchachos de su parroquia.
### Parte 2 · monaguillo_walk · cortes
- [S · multitud 6] Cuando el Tribunal fue a por los que se habían negado al padre Anselmo…
### Parte 3 · exvoto_parroco_walk · cortes
- [cerca · entero · S] …don Tomás se plantó en la puerta de su iglesia, y no los entregó.
- [S] Lo sacaron a rastras y lo condenaron por desacato.
- [cerca · S] Rezó para que nada pudiera alcanzar a sus muchachos a través de él. Le fue concedido.
> [cerca · entero · S] Tomás: «Por esta puerta no pasáis.»
> Pregunta: «¿Habrías abierto la puerta?»

## 04 · CÓDICE · I — MARTÍN ARCE
### Parte 1 · corazon_walk · cortes
- [cerca · S] Martín Arce no tiene exvoto ni sepultura.
- [SE] Era hijo de Inés y soldado de la Columna de Lázaro.
- [S] Amaba a Bartolomé, el Liebre. El capellán Elías los bendijo en secreto.
- [SW] La noche de la Quiebra se quedó atrás para cubrir su huida.
### Parte 2 · abanderado_solo · cortes · lento 1.5
- [cerca · S] Su mortaja va cosida al estandarte de Íñigo. Vacía.
### Parte 3 · corazon_walk · cortes
- [cerca · entero · S] Lo único que queda de él late en el pecho de otro.
> [cerca · S] Martín: «Corre, Liebre. Yo me quedo.»
> Pregunta: «¿Murió por amor o por la Columna?»

## 05 · CÓDICE · V — LA COLUMNA DE LÁZARO
### Parte 1 · abanderado_solo · cortes · lento 1.5
- [cerca · S] La Columna lleva el nombre del que resucitó. Ninguno de sus hombres ha podido morir del todo.
- [SE · altar lejos · medio] Eran los hombres de Valdenoche, con fusil y bayoneta, al mando del capitán Íñigo Albar.
### Parte 2 · abanderado_solo + monaguillo_walk · cortes · lento 1.5
- [N · multitud 9 · solemne] Entraron en la Catedral para llegar al Altar. Entre ellos y el Altar estaban sus vecinos.
### Parte 3 · abanderado_solo · cortes · lento 1.5
- [S] Los que cayeron dentro se levantaron. Y siguieron marchando.
> [cerca · S] Íñigo: «Nadie se retira. (pausa 0.5) Nadie puede.»
> Pregunta: «¿Seguirías a quien no puede morir?»

## 06 · CÓDICE · III — TADEO, EL HERRERO
### Parte 1 · cireneo_walk · cortes
- [cerca · entero · S] Tadeo, el herrero de la Columna, clavó una cruz a la espalda de un vecino.
- [SE] Herraba los caballos y arreglaba los fusiles. Conocía a Bartolomé desde niño.
- [negro · sfx assets/videos/sfx/martillo_clavo.wav fin] El Tribunal se lo ordenó. Y obedeció.
- [cerca · entero · S] No ha vuelto a tocar un clavo.
> [cerca · entero · S] Bartolomé: «No le guardo rencor. (pausa 0.6) Él sí.»
> Pregunta: «¿Es culpable el que clava por orden?»

## 07 · CÓDICE · V — EL QUE CALLÓ Y EL QUE SE PLANTÓ
### Parte 1 · abanderado_solo · cortes · lento 1.5
- [cerca · S] Íñigo Albar calló ante el Tribunal. Don Tomás Ayuso se plantó en su puerta.
### Parte 2 · exvoto_parroco_walk · cortes
- [cerca · entero · S] A uno le quemaron al hombre que amaba. Al otro le condenaron.
### Parte 3 · abanderado_solo + monaguillo_walk · cortes · lento 1.5
- [N · multitud 9 · solemne] Hoy marchan juntos, con los mismos muchachos en medio. Íñigo los recogió. Tomás no se aparta de ellos.
> [cerca · S] Íñigo: «Tú no callaste.»
> Pregunta: «¿Quién de los dos pecó?»

---

## Publicado

| Vídeo | Pregunta | Vistas IG / TikTok / YT | Comentarios | Por 1.000 vistas |
| :--- | :--- | :--- | :--- | :--- |
| 01 Los Bebés (Remotion) | ¿Merecía un nombre quien no llegó a bautizarse? | | | |
| 02 Gaspar (Remotion) | ¿Juzgar sin mirar es justicia? | | | |

- **01 Los Bebés** (lista 2026-11-26): `assets/videos/lore02_01_los_bebes_remotion.mp4` (Remotion, composición `Lore0201`, 69,1 s, con voz) y `lore02_01_los_bebes.mp4` (clásico).
  - **Título (YouTube y portada):** «Los Bebés · Códice». Alternativa: «Yo les di cera · Códice».
  - **TikTok e Instagram:**
    > ¿Merecía un nombre quien no llegó a bautizarse?
    >
    > En los años del hambre, muchos niños de Valdenoche murieron antes de llegar a la pila. Sin bautismo, la Iglesia no les dio nombre ni tierra sagrada.
    > Remedios, la cerera, les hizo uno de cera por cada niño. Cuando la condenaron, fueron tras ella.
    >
    > Deja tu veredicto en los comentarios.
    > Próximamente en tu Nintendo DS.
    >
    > #pixelart #nintendods #gamedev #indiedev #darkfantasy #gothic #lore #homebrew
  - **Encuesta (Instagram):** «¿Merecía un nombre?» · Sí / No.
  - **Comentario fijado (en las tres redes):** «¿Merecía un nombre quien no llegó a bautizarse?»
- **02 Gaspar** (lista 2026-11-27): `assets/videos/lore02_02_gaspar_remotion.mp4` (Remotion, composición genérica `LoreVideo` como `Lore0202`, 69,3 s, con voz). Lore nuevo en `LORE.md`: la primera condena de Gaspar fue Remedios; la miró, dudó, firmó y esa noche se arrancó los ojos.
  - **Título (YouTube y portada):** «Se arrancó los ojos para no perdonar · Códice». Alternativa: «La luz no se apiada · Códice».
  - **TikTok e Instagram:**
    > ¿Juzgar sin mirar es justicia?
    >
    > Gaspar Valcárcel, Gran Inquisidor del Tribunal de la Luz, miró a Remedios a la cara y dudó. Firmó su condena igual, y esa noche se arrancó los ojos para no volver a perdonar.
    > Desde entonces juzga con un farol. Y el farol no ha absuelto a nadie.
    >
    > Deja tu veredicto en los comentarios.
    > Próximamente en tu Nintendo DS.
    >
    > #pixelart #nintendods #gamedev #indiedev #darkfantasy #gothic #lore #homebrew
  - **Encuesta (Instagram):** «¿Juzgar sin mirar es justicia?» · Sí / No.
  - **Comentario fijado (en las tres redes):** «¿Juzgar sin mirar es justicia?»
