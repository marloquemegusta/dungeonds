# Concepto de personaje, enemigos, élites y jefe de la demo (2026-11-11)

Sesión de diseño conceptual, sin código. Las decisiones viven en `DESIGN.md` §6.10; aquí quedan el razonamiento, los prompts usados para generar los modelos y lo que falta. Son ideas para seguir iterando.

## Qué se decidió

- **Personaje (clase láser):** el rayo no es un arma sino un milagro que consume el cuerpo. Sale del propio personaje, que va quemado por usarlo y sigue vivo por fe (tono Trench Crusade).
  - **Elegido para continuar: El Corazón Abierto.** El usuario ya ha generado el modelo y la animación de carga (Gemini → Tripo). La consolidación como personaje (animaciones, efectos y lab) es la siguiente sesión.
  - **En reserva:** El Lector (rayo de boca y ojos, libro encadenado) y La Custodia (custodia soldada en lugar de cabeza, rayo desde la hostia).
  - **Descartados por genéricos:** Portaluz, Hermana del Cirio y Penitente tirador (armas al uso).
- **Enemigos base**, misma FSM que en la 0.3.1 y solo aspecto nuevo: fieles huecos (masa), flagelante (cargador) y farolero (tirador con linterna verde).
- **Élites a probar:** Portaestandarte (acelera a los enemigos cercanos) y Exorcista hueco (invoca masa en círculos en el suelo).
- **Jefe:** paso procesional cargado por costaleros muertos.

## Reglas para generar modelos

- Imagen en **T-pose, manos vacías**, fondo gris liso, luz plana y sin sombras. El arma o el objeto va en una imagen aparte y se ensambla después.
- A la escala de la DS, celda de **40×40 px** con el personaje de **~31 px** de alto (`TECHNICAL.md` §4.1), solo se lee un punto de luz grande y la silueta de la pose. Grapas, hilos o llagas finas se pierden.
- En el lab: preset de luz **«Neutra»**, contorno **«none»**, celda de 40.
- El brillo del corazón, la hostia o la cara no sobrevive al 3D. La luz del rayo y del aura se añade en el juego.

## Prompts usados

### El Corazón Abierto (personaje)
```
Full-body character for 3D modeling, single character, strict T-pose (arms straight out horizontally, palms down, legs slightly apart), front view, empty hands, nothing held. Plain light grey background, flat even lighting, no cast shadows. A grimdark martyr-zealot whose chest has been pried open and held apart by large crude iron clamps, revealing a burning sacred heart wrapped in a crown of thorns inside the ribcage, glowing bright orange-gold. The ragged penitent tunic is burned away in a wide charred circle around the open chest, skin around the wound cracked and blackened. Bandaged forearms, a rusted iron collar, tattered sash, heavy muddy boots, a gaunt face with sunken eyes and a shaved head with ritual scars. Strong readable focal point at the center of the chest. Chunky readable proportions for a low-resolution isometric game sprite. Trench Crusade and Blasphemous style, macabre Catholic gothic, muted palette of oxblood, charcoal, rusted iron and bone with a single bright orange-gold glow in the chest.
```

### El Corazón Abierto: animación de carga (1 s generada, comprimida a la carga del juego)
La carga actual dura 24 frames (0,4 s, `aim_min_frames`). Se genera de 1 s y en el juego avanza según el porcentaje de carga, no según el tiempo, para que valga si una mejora alarga la carga. El último frame se mantiene congelado hasta soltar el stylus.
```
A single continuous one-second animation, in place, feet planted shoulder-width apart, facing forward the whole time, no turning and no walking. The martyr starts in a neutral standing pose, arms relaxed at his sides, head slightly bowed. Over the second he gradually and painfully builds up: his shoulders pull back, his open chest pushes forward more and more, both arms rise and spread wide to the sides with palms opening forward, and his head tilts back as if in ecstatic, agonized prayer. The movement is strained and trembling, not graceful, accelerating toward the end. The animation ends on a fully extended climax pose: a rigid crucifixion pose, arms spread wide and straight, chest thrust forward as far as possible, back arched, head thrown back, fingers splayed and tense. The final frame must be a strong, clean, stable pose that can be held frozen for a long time.
```

### El Corazón Abierto: disparo (pendiente de generar)
```
From the crucifixion pose, the martyr's whole body jolts violently backward as if struck by a massive force released from his own chest: the chest thrusts forward, the shoulders and arms snap back, the head whips back, and he slides half a step backward. He then sags forward, exhausted, arms dropping limply to his sides and head bowed for a moment, before slowly straightening into a neutral standing pose. Feet stay grounded, no falling over.
```

### El Lector (reserva)
```
Full-body character for 3D modeling, single character, strict T-pose (arms straight out horizontally, palms down, legs slightly apart), front view, empty hands, nothing held. Plain light grey background, flat even lighting, no cast shadows. A grimdark war-monk who channels holy light through prayer and is slowly burning alive from it: heavy coarse monk's robe in filthy brown wool, deep hood whose inner edge is scorched black, the face inside burned down to the skull on one side with charred blackened skin and cracked embers, eye sockets and open mouth glowing faintly white-gold. An iron manacle on the left wrist with a short broken chain hanging. Rope belt with nailed prayer scraps, bare blackened feet. Gaunt, hunched but defiant. Strong silhouette from the deep hood. Chunky readable proportions for a low-resolution isometric game sprite. Trench Crusade and Blasphemous style, macabre Catholic gothic, muted palette of mud brown, charcoal, bone and a single warm white-gold glow.
```
```
Single isolated prop for 3D modeling, three-quarter view, centered, plain light grey background, flat even lighting, no hands, no character, no cast shadows. A large heavy holy book, open, thick warped pages with burned edges, iron-bound cover with corner studs and a crude cross, a short heavy chain riveted to the spine ending in a broken link, faint white-gold light rising from the pages. Chunky readable shapes for a low-resolution game sprite. Trench Crusade style, macabre Catholic gothic, scorched parchment, dark leather, rusted iron.
```

### La Custodia (reserva)
```
Full-body character for 3D modeling, single character, strict T-pose (arms straight out horizontally, palms down, legs slightly apart), front view, empty hands, nothing held. Plain light grey background, flat even lighting, no cast shadows. A grimdark priest whose head has been replaced by a large gilded monstrance welded onto his neck: a big golden sunburst of long straight and wavy rays around a round glass window holding a pale glowing host at the center. The neck is raw burned flesh fused and riveted into the monstrance base. He wears a long tattered priest's cassock and a stained chasuble with faded gold embroidery, burned at the collar, a rosary of iron nails, dirty bare hands with blackened fingertips. Very strong silhouette from the sunburst head, which is wide and clearly larger than a normal head. Chunky readable proportions for a low-resolution isometric game sprite. Trench Crusade and Blasphemous style, macabre Catholic gothic, muted palette of black, faded crimson and tarnished gold with a single white-gold glow at the host.
```
Si los rayos salen finos: pedir «fewer, thicker rays» (8–12 rayos gruesos se leen mejor a 31 px).

## Pendiente (siguiente sesión: consolidar el Corazón Abierto)

- Meter el modelo y las animaciones en el repo (`assets/models/characters/`) y pasarlos por el lab: 8 direcciones, ancla de pies y punto de salida del rayo en el **centro del pecho** (el `muzzle` que exporta el lab).
- Animaciones de andar, carga (pose final congelada), disparo e impacto/muerte.
- Decidir en `DESIGN.md` el aspecto del rayo y del aura de carga para este personaje (hoy rayos azules y colimado rojo → verde, §4.9), y si la quemadura crece con las mejoras.
- Sin decidir: cifras, fases y telegrafías de élites y jefe, tamaño del paso en pantalla y si la demo lleva minijefe.
