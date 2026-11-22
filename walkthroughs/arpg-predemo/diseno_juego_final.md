# Diseño del juego final ARPG y alcance de la protodemo (documento de trabajo)

Documento vivo de la rama `proto/arpg`: se itera con el usuario y, cuando se cierre, lo decidido pasa a `DESIGN.md` §7. Marca: **[DECIDIDO]**, **[PROPUESTA]** (pendiente de visto bueno), **[ABIERTO]**.

## 1. Modelo de juego [DECIDIDO]
- Modelo Diablo 1 / Castlevania: **un campamento y un castillo-mazmorra persistente**, sin mundo exterior. Copiamos a Diablo sin complejos.
- El progreso se acumula (no es un roguelite): lo explorado se queda en el mapa, y las puertas abiertas, los altares tocados, los cofres y los secretos encontrados no vuelven.
- **[DECIDIDO 2026-11-20] Al dormir reaparecen todos los enemigos, también élites, minijefes y jefes**, para poder repetirlos a por mejor botín (farmeo, como en Diablo). Vencer a un jefe por primera vez abre el camino y queda registrado; repetirlo solo da botín y experiencia.
- Combate por **densidad, no precisión**: grupitos de 3-6 enemigos que mueren en 1-2 golpes y quitan un 5-8 % de vida; muchos grupos por sala; élites y jefes largos (minutos). El reto es la build y no dejarse rodear. Tope técnico: ~24 enemigos activos a la vez (los grupos aparecen al acercarse).
- Hitos: protodemo en 2 días (este finde); con ella se decide si la demo final es el roguelike o el ARPG.

## 2. Duración objetivo [DECIDIDO]
| Qué | Duración |
|---|---|
| Una bajada (campamento → volver) | 10-20 min |
| Zona 1 (protodemo), primera vez | 45-60 min |
| Una zona del juego final | 1,5-2 h |
| Campaña final (5 zonas) | 8-10 h |
| Con 3 dificultades | ~25 h |

## 3. La mazmorra [DECIDIDO salvo lo marcado]
**Piezas**
- **Pantalla:** 256×192.
- **Sala:** rectángulo de 1 pantalla de ancho × N de alto (el motor actual). Tipos:
  - **Nave** (8-12 pantallas): forma el **camino principal** de la zona, de la entrada a la cripta. Combate continuo, sin rejas.
  - **Galería** (2-4 pantallas): sala secundaria que cuelga de una puerta. Puede ser **sin salida** (acaba en premio) o **de enlace** (tiene otra puerta que lleva a otra sala: un atajo o un rodeo).
  - **Capilla** (1-2 pantallas): sala cerrada con reja; el combate táctico del roguelike. Siempre con premio.
  - **Cripta** (2 pantallas): el jefe de la zona.
- **Puerta:** arriba al final de la sala, o en un lateral (izquierdo o derecho) a cualquier altura. Al cruzarla: fundido y apareces en la puerta correspondiente de la otra sala. Variantes: normal, **con llave** (la suelta un élite de la zona), **atajo** (solo se abre desde un lado).
- **Altar:** *waypoint*. Desde el campamento se viaja a cualquier altar ya tocado.
- **Zona:** un bioma = un grafo de 10-15 salas que termina en su cripta.

**Qué va dónde (regla)** [PROPUESTA]
| Sala | Qué contiene |
|---|---|
| Nave | Grupos de enemigos, élites sueltos, objetos rompibles, santuarios, un altar al empezar |
| Galería sin salida | Siempre un premio al fondo: tesoro, minijefe, secreto o prisionero |
| Galería de enlace | Combate normal; su gracia es el atajo o el rodeo |
| Capilla | Élite con escolta o reto táctico; premio garantizado |
| Tras puerta con llave | Lo mejor de la zona (un único) |
| Cripta | Jefe y su botín |

**Cómo se construye una zona**
- **Esqueleto a mano** (el usuario, ~15 min por zona): qué salas hay, su tipo y alto, dónde está cada puerta (lado y pantalla), la llave, los atajos, los altares y la cripta. Siempre el mismo mapa.
- **Interior por reglas:** cada sala tiene ranuras (una de combate cada pantalla y media, otras de objetos); el combate se llena con **grupos tipo** de la zona según un presupuesto que crece con la profundidad; probabilidad de élite; los premios salen de un cupo garantizado por zona.
- **Lo que el usuario diseña son listas, no salas:** grupos tipo, secretos, lápidas con lore, únicos, santuarios, prisioneros. El generador los coloca sin repetir.
- **Mapa** en la pausa, estilo Castlevania: se revela al explorar; marca puertas, altares y lo encontrado.

**Borrador del esqueleto de la zona 1** [PROPUESTA, a corregir]
```
                     [CRIPTA · Abanderado]
                              |
 [Galería · tesoro] ── [NAVE 3 · 10p] ── [Capilla · élite]
                              |   └─ atajo ↓ a la Nave 1 (pantalla 2)
 [Capilla con llave] ─ [NAVE 2 · 10p] ── [Galería · minijefe: Exvoto gigante]
   (único)                    |                  └─ enlace → Nave 3 (pantalla 6)
 [Galería · prisionero] ─ [NAVE 1 · 8p] ── [Galería · secreto]
                              |
                         [Entrada]
```
Altares al empezar cada nave. ~45 pantallas.

## 4. Progresión [ABIERTO: propuesta para unificar]
Problema: árbol + niveles + únicos + inventario son demasiadas vertientes que se pisan. Toda capa debe aportar algo que no aporte otra.

**Propuesta: dos capas, cada una con un papel**
| Capa | Qué da | Cómo se consigue | Decisión del jugador |
|---|---|---|---|
| **Nivel** | Vida, maná y **engarces** (huecos para mejoras: se abren uno en los niveles 3, 6, 10, 15…) | Experiencia (runas), al dormir | Ninguna o mínima: es «cuánto aguantas y cuánto cabe» |
| **Botín: hechizos y mejoras** | Qué haces y cómo lo haces | Se encuentran en la mazmorra (élites, jefes, cofres, secretos) | Qué hechizos llevas y qué mejoras engarzas en cada uno |

- **Sin árbol de habilidades ni armaduras.** El inventario es la bolsa de hechizos y mejoras encontradas.
- **Cada hechizo tiene sus engarces:** se le engarzan mejoras de su escuela (estilo gemas de soporte de Path of Exile o runas de Diablo 3). Huecos limitados = elegir una u otra; se cambian en el campamento.
- **[DECIDIDO 2026-11-20] Reliquias aleatorias con tiradas, estilo Borderlands.** Una sola clase de objeto, la reliquia:
  | Parte | Qué es |
  |---|---|
  | Escuela | En qué hechizo se encaja (Rayo, Ejecución, Glifo, Levantar) o **pasiva** del héroe |
  | Rareza | Común: 1 línea · Poco común: 2 líneas · Rara: 1 mecánica + 1 línea · Épica: mecánica fuerte + 2 líneas · Legendaria: nombre propio, mecánica única fija diseñada a mano + 2 líneas tiradas |
  | Mecánica (opcional) | Cambia cómo funciona el hechizo, con su número tirado (ej. Llama Votiva 50-110 % de quemadura) |
  | Líneas | Estadísticas tiradas (daño, carga, alcance, coste de maná…) |
  | Nivel de objeto | El piso donde cae; escala todos los números |
  - Ejemplo: una épica «Llama Votiva 110 % + 10 % de alcance» frente a una rara «Llama Votiva 50 % + 30 % de alcance»: el jugador elige. Una reliquia claramente mejor puede obligar a cambiar de estilo.
- **Huecos:** cada hechizo tiene los suyos (al principio 0 o 1, el nivel abre más). **Pasivas/auras** (Cilicio, robo de vida, Llaga…): 1-2 huecos propios del héroe («el relicario del pecho»), que se abren más tarde.
- **Qué puede salir y cuándo:** cada mecánica tiene un **piso mínimo** (las suaves desde el piso 1; las fuertes, a mitad de zona o en zonas siguientes). Las **legendarias** salen solo de jefes, puertas con llave y secretos; cada zona tiene su conjunto propio de 2-3 (diseñarlas es parte de añadir una zona).
- **Reliquias obsoletas:** se **desguazan en el campamento a cambio de cera** (moneda). Juego final: la cera sirve para volver a tirar una línea de una reliquia (el místico de Diablo 3) y para comprar pociones. Protodemo: solo pociones.
- **Interfaz clave:** comparar «lo que llevas» frente a «lo nuevo» (líneas que suben en verde, que bajan en rojo) y bolsa limitada (16-20) con desguace.

## 5. Arquetipos (escuelas) [PROPUESTA]
Un solo héroe, el Corazón Abierto, con cuatro escuelas; la build sale de qué hechizos lleva y qué les engarza.

**Controles:** lápiz = hechizo activo; `L` corto = Ejecución (siempre); `L` mantenido = abrir el menú radial con los 3 hechizos equipados (el activo y 2 más).

| Escuela | Hechizo | Mejoras (engarces) | Fantasía |
|---|---|---|---|
| **Rayo** | Rayo cargado | Prisa, Fervor (daño), Alcance, Sed de Ceniza, Lanza (atraviesa), Llama Votiva (la línea quema), Tierra Quemada (rastro de fuego), Reflejo (rebota), Auto de Fe, Pilar (rayo ancho) | La metralleta o el láser que quema |
| **Ejecución** | Ejecución (fija en `L`, no ocupa hueco de hechizo) | Explosión al ejecutar, Viático (robo de vida), carga instantánea tras ejecutar, ejecución en cadena, tambaleo más largo, charco de cera | Cuerpo a cuerpo brutal: te recuperas matando de cerca |
| **Glifos** (maldiciones) | Glifo: se dibuja en el suelo y hace efecto tras un instante | Lentitud, Quemadura (daño por segundo), Juicio (los de dentro reciben más daño de todo), Marca (el marcado estalla al morir), detonación retardada, glifo mayor | Marcar un área y esperar a que pase algo; glifos guapos en el suelo |
| **Nigromancia de cera** | Levantar: convierte los restos de cera de los muertos en siervos | Más siervos, siervos ardientes, Ofrenda (explotan), siervo gigante (con restos de un Exvoto gigante), procesión (aura para siervos) | Ejército de cera; la Ejecución deja más restos (sinergia) |

**¿Arquetipo = clase?** [ABIERTO] Dos opciones:
- **A (recomendada):** un héroe con las cuatro escuelas; se mezclan (ej. Glifo de Juicio + Rayo). Más builds con menos contenido. Las clases futuras traen escuelas propias.
- **B:** cada escuela es una clase. Más identidad, pero cada clase necesita más profundidad y no se mezclan.

## 6. Otros sistemas
- **Santuarios** [PROPUESTA]: objetos de la nave que al tocarlos dan un efecto temporal (60 s): daño doble, maná infinito, velocidad, experiencia extra; alguno con riesgo (invoca un grupo). Son de Diablo. Para el lore: exvotos, cirios o reliquias que rezan.
- **Élites con propiedades** [PROPUESTA]: Rápido, Ardiente, Escoltado, Vampírico, Cera dura, Invocador.
- **Exvotos por tamaño** [DECIDIDO, el usuario los está haciendo]: bebé (enjambre), niño (relleno), adulta (base), grande (tanque), gigante (minijefe).

## 7. Alcance de la protodemo (este finde)
**Imprescindible:** zona 1 con salas y puertas (fundido), esqueleto como grafo, relleno por reglas, persistencia del mapa y reaparición al dormir, mapa en la pausa, élites con propiedades, progresión de §4 en mínimo (Rayo + Glifos + Ejecución, 3-4 mejoras cada uno, engarces), botín con nombre en el suelo por rareza.
**Si da tiempo:** santuarios, prisionero, secretos, Nigromancia, Exvotos por tamaño en el juego.
**Fuera:** zona 2+, dificultades, modo infinito, más clases.
**Si se tuerce:** lo primero que cae son los únicos y la Nigromancia, no la mazmorra.

## 8. Lista de diseños del usuario
P = protodemo, F = juego final. De todos puede prepararse un borrador para corregir.

**Mecánicas**
1. P · Escuelas: por cada hechizo y mejora, qué hace, qué mejora con la calidad, coste de maná, sinergias.
2. P · 3 únicos.
3. P · Propiedades de élite (4-6).
4. P · Botín: rarezas y qué sube la calidad.
5. F · Santuarios (5-6).
6. F · Resto de mejoras y únicos.

**Reglas de combate**
7. P · Papel de cada tamaño de Exvoto (una línea).
8. P · Validar jugando las cifras base (daño en % de vida, golpes para matar, maná, pociones).
9. F · Familias de las zonas siguientes.

**Población de salas**
10. P · Grupos tipo de la zona 1 (8-10).
11. P · Densidad por tipo de sala y probabilidad de élite.
12. P · Premios por tipo de sala (tabla de §3).

**Mazmorra**
13. P · Esqueleto de la zona 1 (borrador en §3).
14. P · Cosas escondidas de la zona 1: 3-5 secretos o lápidas y 1 prisionero.
15. F · Esqueletos y listas de las zonas 2-5.

**Assets**
16. P · Exvotos por tamaño (en curso).
17. P · Piezas: puerta lateral (normal, con llave, atajo), puerta superior, altar, cofre (cerrado y abierto), llave.
18. P · Sustitutos de los placeholders (`assets_pendientes.md`).
19. P · Iconos de mejoras/hechizos por escuela (se tiñen por rareza).
20. F · Animaciones de puñetazo y lanzar, Abanderado élite, campamento.
21. P · Elección de sonidos definitivos (los actuales son provisionales).
22. F · Biomas de las zonas 2-5.

**Bloquean más:** 13 (esqueleto) y 10 (grupos); después 1 y 17.

## 9. Respuestas de cierre de la sesión (2026-11-20)
| Pregunta | Respuesta |
|---|---|
| Un solo héroe con las cuatro escuelas mezclables (no una clase por escuela) | **Sí** [DECIDIDO] |
| `L` corto = Ejecución fija; `L` mantenido = cambiar entre los 2 hechizos del lápiz | **Sí, provisional**: probarlo en la consola; si no funciona, otro botón abre el menú de hechizos |
| Capillas cerradas con reja (combate táctico) dentro del castillo | **No lo sé** [ABIERTO] |
| Los cofres se rellenan al dormir | **No lo sé** [ABIERTO] |
| Misiones por plantilla en la protodemo | **No**: quedan para después |
| Pociones: se beben tocando el orbe con el lápiz | **Sí** [DECIDIDO] |
| Nigromancia en la protodemo | **Después**: la protodemo lleva Rayo, Ejecución y Glifos |
| Tres dificultades (Normal, Pesadilla, Infierno) en el juego final | **Sí** [DECIDIDO] |

## 10. Cerrado para la protodemo (2026-11-20, segunda tanda)
Detalle con mapa y tablas: [`propuestas_protodemo.html`](propuestas_protodemo.html) (v3). Sustituye a lo de arriba que lo contradiga.
- **Combo de puñetazos** [DECIDIDO]: `L` corto encadena directo → cruzado → gancho (Mixamo «Punching», «Punching (1)», «Hook Punch»), daño 50 · 50 · 90; el gancho empuja. Si hay un tambaleante al alcance, `L` ejecuta.
- **Tambaleo solo por vida baja** [DECIDIDO]: ningún golpe tambalea por sí solo; un enemigo se tambalea al quedarle un 25 % de vida o menos, le dé lo que le dé.
- **Esqueleto de la zona 1** [DECIDIDO, primera versión]: el del mapa v3 (3 naves de 8-10 pantallas, 4 galerías, 2 capillas, cripta; llave en la capilla de la Nave 3 que abre la capilla cerrada de la Nave 2; enlace de la galería del minijefe a la Nave 3; atajo de la Nave 3 a la Nave 1).
- **Capillas** [DECIDIDO]: salas laterales cuya puerta se convierte en reja al entrar y se abre al limpiar. Las naves no llevan rejas.
- **Sin propiedades de élite; escalones fijos y dirección de arte «etapas de corrupción»** [DECIDIDO 2026-11-22]: los enemigos tienen nivel y población fijos por ala del castillo (sin auto-escalado con el jugador). Árbol de 3 escalones en Exvoto: Bebé / Exvoto base → Monaguillo (choque) y Monja (apoyo/curación) → Súper Monaguillo y Súper Monja (modelos FBX ya en el repo). **Estética de los escalones superiores:** se descarta convertir los tiers en especies distintas o versiones «Hulk»; cada escalón muestra una etapa más avanzada de corrupción biológica/sobrenatural del mismo cuerpo humano/de cera (*La Monja / Valak*, *The Ritual*, *Pennywise*, *Skinwalker*: cabezas falsas que caen abriendo bocas verticales en las costillas, siluetas cuadrúpedas o tipo mantis con el torso colgando como señuelo), aplicable también a variantes futuras del Cireneo y el Ojo.
- **Grupos tipo** [DECIDIDO]: 10 grupos de 4 a 12 enemigos (el doble de la primera propuesta); un grupo cada pantalla y media; como mucho 2 despiertos a la vez (~24 enemigos, a medir en la DS).
- **Reliquias** [DECIDIDO]: todo el botín son reliquias que van en un hueco de hechizo (Rayo, Ejecución, Glifo) o del pecho; traen stats de ese hechizo y, desde rara, un aura con su número. Auras de la protodemo: Lanza y Llama Votiva (Rayo), Viático y Estallido (Ejecución), Quemadura, Juicio y Marca (Glifo). Descartadas: Reflejo y Fervor; Prisa y Glifo mayor pasan a ser stats.
- **Rarezas, huecos, bolsa y premios** [DECIDIDO]: como en la v3 (común 1 stat … legendaria aura única; huecos que abren los niveles 2, 4, 6, 8 y 10; bolsa de 16; los cofres no se rellenan al dormir).
- **Puertas** [DECIDIDO 2026-11-20]: la **lateral** no es un modelo (por la perspectiva no se vería): es un **hueco negro en el muro**, un trozo de pared que falta; al cruzarlo, fundido a negro y apareces en la otra sala. La **superior** es el modelo de puerta de Tripo escalado para **sustituir a un bloque de pared** del muro del fondo, encajando como uno más.
- **Altar y cofres** [primera versión]: modelos de Tripo del usuario (altar, cofre cerrado, cofre abierto). El cofre se abre al tocarlo y cambia al modelo abierto; el altar se enciende al pasar junto a él y queda tocado.
- **Campamento** [DECIDIDO]: es un **escenario propio**, como la catedral: con sus tiles de suelo y sus props. Se diseña aparte; los props de la lista anterior quedan en suspenso hasta entonces.
- **Estatuas = santuarios** [DECIDIDO 2026-11-20]: las estatuas de santo de la catedral hacen de santuario (§6: efecto temporal al tocarlas). El altar de viaje es el modelo de altar de Tripo.
- **Lápidas con lore** [DECIDIDO, más adelante]: las lápidas del suelo serán legibles y contarán lore; no entra en la protodemo.
- **Curva de dificultad del inicio** [DECIDIDO 2026-11-20]: los primeros minutos tienen que sentirse como Diablo: machacar enemigos débiles. Salas 1-4: solo Bebés y Exvotos, y desde la sala 3 alguna sala suelta (1 de cada 3) con un único Ojo o Cireneo. Párroco y Monja desde la sala 5. Desde la sala 8, hasta 2 Ojos o Cireneos por grupo. Cifras provisionales; se ajustan jugando.

## 11. Mapa de la zona 1: variante D «cuatro naves cortas» (decidido 2026-11-22)
Sustituye al esqueleto de §10 (3 naves de 8-10 pantallas). Comparativa con Diablo y Castlevania y cuentas de duración: `walkthroughs/arpg-mapa/tamano_zona1.html`.
- **Objetivo de duración:** al menos 1 h en Normal la primera vez y 2-3 h con las 3 dificultades. Modelo: pasada limpia ≈ 1 min por pantalla; Normal ≈ pasada × 1,3-1,5; cada dificultad extra ≈ Normal × 0,6-0,7. El «1 min por pantalla» se mide en la consola con la Nave 1 y se ajusta la densidad.
- **12 salas, 46 pantallas, todas de 6 pantallas o menos** (se recorren arriba y abajo):

| Sala | Pantallas | Puertas (pN = pantalla N desde abajo) | Contenido |
|---|---|---|---|
| Nave 1 | 6 | izq p2 → Galería del cofre · der p5 → Galería del secreto · arriba → Nave 2 | altar al pie; Bebés y Exvotos |
| Nave 2 | 6 | izq p3 → Capilla del párroco · der p5 → Galería de la Misa · arriba → Nave 3 | altar; entran Párroco y Monja |
| Nave 3 | 6 | izq p4 → Galería del prisionero · arriba → Nave 4 | altar; mezcla completa (Ojos y Cireneos) |
| Nave 4 | 6 | izq p2 → Capilla con llave · der p4 → Galería del élite · arriba → Cripta | altar; mezcla completa |
| Galería del cofre | 2 | lateral → Nave 1 | cofre |
| Galería del secreto | 2 | lateral → Nave 1 | cofre (la mecánica de secreto, después) |
| Capilla del párroco | 2 | lateral → Nave 2 | reja; Párroco con grupo; suelta la **llave**; rara garantizada |
| Galería de la Misa | 4 | lateral → Nave 2 | **minijefe la Misa**: Párroco + Monja + 8 Exvotos con el doble de vida; épica |
| Galería del prisionero | 4 | lateral → Nave 3 | cofre (la mecánica de prisionero, después) |
| Capilla con llave | 2 | lateral → Nave 4, con reja hasta llevar la llave | legendaria fija de la zona |
| Galería del élite | 4 | lateral → Nave 4 | **minijefe Abanderado élite**; épica |
| Cripta | 2 | entrada desde la Nave 4 | **jefe Abanderado**; legendaria la primera vez |

- **Sin escalado:** cada sala tiene nivel fijo (Nave 1 = 1 … Cripta = 5; las laterales, el de su nave). Se retiran el «+12 % de vida por piso» y el «jefe cada 5 pisos».
- **Persistencia:** se recuerdan cofres abiertos, altares tocados, jefes vencidos y la llave. Lo que matas sigue muerto hasta dormir; al dormir vuelven todos los enemigos, minijefes y jefe incluidos; los cofres no se rellenan.
- **Entrada:** desde el campamento se entra por el último altar tocado (uno al pie de cada nave). Sin menú de viaje entre altares en la protodemo.
- **Al morir:** vuelves al campamento con todo lo explorado y lo matado (hasta dormir).
- **Dificultades:** vencer al jefe desbloquea Pesadilla y luego Infierno, en la misma catedral con enemigos más duros y botín de más nivel.
- **Mapa en la pausa:** las salas se revelan al explorar; marca altares, cofres y la llave.
- **Escalones de enemigos (decidido 2026-11-22):** Exvoto con dos ramas que comparten el Bebé: chica = Bebé → Exvoto → Monja; chico = Bebé → Monaguillo → Párroco. Ojo y Cireneo con 2 escalones; el segundo de momento solo pega y aguanta más (x2 vida, x1,5 daño); su mecánica propia y su aspecto se deciden después.
- **Población por grupos tipo** (los de §10, más «Monaguillos»): Ronda, Enjambre, Procesión, Monaguillos y Puesto desde la Nave 1; Carga, Guardia, Parroquia y Convento desde la Nave 2; Tiradores desde la Nave 3. Ojos y Cireneos de segundo escalón: la mitad en la Nave 3, todos en la Nave 4.
- **Fin de sala y huecos (decidido 2026-11-22):** la cámara nunca se bloquea en las salas (solo en el campamento); por encima del final de la sala se ve negro. Al final de cada sala va un **muro del fondo** hecho con el mismo módulo 3D del muro lateral (arco gótico) girado hacia la cámara, en un número impar de módulos a lo ancho; el central es la puerta abierta (interior del arco en negro) en las salas con salida arriba. Los **huecos laterales** son un módulo del muro lateral quitado: se ve el corte de los vecinos y negro al fondo.
