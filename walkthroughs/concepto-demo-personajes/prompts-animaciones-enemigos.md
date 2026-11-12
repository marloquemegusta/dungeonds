# Prompts de animación de enemigos (2026-11-12)

Reglas comunes a todos los clips: **in place** (sin desplazarse; el juego mueve al personaje), mirando siempre al frente sin girar el torso (el lab renderiza las 8 direcciones), y en los bucles el primer y el último frame idénticos. La muerte no necesita animación: el juego rompe el sprite en fragmentos (`DESIGN.md` §2). Se generan de ~1 s o más y se comprimen al exportar si hace falta.

**Presupuesto (2026-11-12).** Los sprites van en la ROM como `uint16_t` 40×40 (`source/player_sprite.c`) y el binario se carga entero en los 4 MB de RAM: cada frame en las 8 direcciones son 25,6 KB y un clip de 8 frames, 200 KB (el doble en celdas grandes como el Cireneo). Todos los clips de abajo pasarían de 3,5 MB, así que no caben. Se generan todos para elegir, pero en el juego entran solo los de **prioridad**: los estados a los que el jugador reacciona. El resto se cubre con el clip de andar, con poses de 1–2 frames y con efectos por código (parpadeo, temblor, destello).

| Enemigo | Prioridad (en el juego) | Sustituido por código o por otro clip |
| :--- | :--- | :--- |
| Exvotos | Andar (8 f) | Ataque: andar + empujón y destello |
| Cireneo | Andar (8 f), carga (6 f), telegrafía (1 f), atascado (2 f + temblor) | Recuperación: andar más lento |
| Ojo del Tribunal | Andar (8 f), juicio (1 f) | Sentencia: pose de juicio + sacudida y destello |
| Abanderado | Andar (8 f) | Arenga: brillo del aura |
| Campanero | Andar (8 f), toque (4 f) | — |

Ningún clip del catálogo del lab sirve para estos enemigos: andan rígidos, encorvados o con los brazos clavados, y las animaciones genéricas balancean los brazos y caminan erguidas.

## Los Exvotos
- **Andar (bucle, 1,2 s):**
```
In-place looping walk cycle, facing forward, no turning. A slow, heavy, shuffling procession walk of a melting wax figure: tiny dragging steps, feet barely lifting from the ground, body slightly hunched and swaying side to side, head bowed, both forearms held stiffly in front at waist height with palms up as if carrying candles. No arm swing. Limp, lifeless and monotonous, like a sleepwalker in a religious procession. First and last frame identical.
```
- **Ataque (0,6 s):**
```
In-place, facing forward. From the slow hunched walk pose, the wax figure suddenly lunges its upper body forward and grabs with both hands in front of it, head jerking forward, then slowly sags back into the hunched pose. Clumsy and heavy, no foot movement.
```

## El Cireneo
Los brazos van siempre extendidos en horizontal (clavados al travesaño): en ningún clip se mueven respecto a los hombros.
- **Acercamiento (bucle, 1,4 s):**
```
In-place looping walk cycle, facing forward, no turning. A giant walks slowly and painfully while his arms stay locked rigidly straight out to the sides at shoulder height, never moving relative to the shoulders, as if nailed to a crossbeam. He is bent forward under a huge weight on his back, torso leaning forward, heavy dragging steps, the whole upper body rocking side to side with each step. First and last frame identical.
```
- **Telegrafía (0,5 s, se mantiene el último frame):**
```
In-place, facing forward. Arms stay locked straight out to the sides at shoulder height the whole time. The giant stops, plants his feet wide, lowers his head and bends his torso far forward until his back is almost horizontal, like a bull about to charge, shoulders tensing. Ends on a stable, frozen crouched pose that can be held.
```
- **Carga (bucle, 0,6 s):**
```
In-place looping charge run, facing forward, no turning. Arms stay locked straight out to the sides at shoulder height, never moving. The giant runs furiously with his torso bent almost horizontal and head down, as if ramming with something on his back, long powerful stomping strides, the body shaking with each impact. First and last frame identical.
```
- **Aturdido contra la columna (bucle, 1,2 s):**
```
In-place looping animation, facing forward. Arms stay locked straight out to the sides at shoulder height. The giant is stuck, bent forward with his back pinned against something in front of him; he struggles desperately, pulling his body backward with his legs, feet slipping, torso jerking and twisting slightly, head thrashing, but he cannot free himself. First and last frame identical.
```
- **Recuperación (1 s, termina en la pose de andar):**
```
In-place, facing forward. Arms stay locked straight out to the sides at shoulder height. From a bent-forward pose, the exhausted giant slowly straightens up a little, panting heavily with the shoulders rising and falling, staggers half a step and settles back into a hunched standing pose bent under the weight on his back.
```

## El Ojo del Tribunal
- **Andar (bucle, 1,2 s):**
```
In-place looping walk cycle, facing forward, no turning. A tall, rigid, blind inquisitor walks with slow, stiff, measured steps, back perfectly straight, head held high and very still, arms held stiffly slightly away from the body with long fingers spread, feeling the air as if blind. No natural arm swing. First and last frame identical.
```
- **Juicio (1,5 s, se mantiene el último frame):**
```
In-place, facing forward. The blind inquisitor stops, plants his feet together, slowly raises one arm and points forward with a long bony finger, while his head tilts forward and stays perfectly locked in place, staring ahead. The rest of the body freezes rigidly. Ends on a stable, frozen accusing pose that can be held.
```
- **Sentencia (0,5 s, termina en reposo):**
```
In-place, facing forward. From the frozen pointing pose, the inquisitor's head snaps violently backward as if a blast came out of his face, the body jolting back, then he slowly lowers his arm and returns to an upright rigid standing pose.
```

## El Abanderado
- **Andar (bucle, 1,6 s):**
```
In-place looping walk cycle, facing forward, no turning. An armoured standard-bearer who cannot bend: the spine and neck are completely rigid and vertical, as if a pole runs through the whole body. Slow, heavy, solemn marching steps with stiff knees, the whole body tilting slightly side to side with each step like a statue being moved. Arms hang stiffly at the sides with a very small swing. First and last frame identical.
```
- **Arenga (bucle, 1,5 s):**
```
In-place looping animation, facing forward. The rigid standard-bearer stands still with feet apart, spine perfectly vertical, and raises both arms high and wide to the sides in a commanding rallying gesture, holds them, then lowers them slowly, as if urging an army forward. The torso and head never bend. First and last frame identical.
```

## El Campanero de Ánimas
- **Andar arrastrando la campana (bucle, 1,6 s):**
```
In-place looping walk cycle, facing forward, no turning. A very hunched, thin old man drags a heavy load behind him with his right hand: the right arm hangs back and down, straining, the body leans forward against the weight, slow labored steps, the left arm hangs limp. Head low, wide hat bobbing. First and last frame identical.
```
- **Toque (1,2 s, termina en reposo):**
```
In-place, facing forward. The hunched old man stops, lifts a heavy object in his right hand up to chest height with great effort, then swings it violently forward and back twice as if ringing a heavy bell, his whole body shaking with each swing, his jaw hanging open in a silent scream, then lowers it back down and sags into a hunched standing pose.
```

## El Paso
Se decide en su propia sesión: probablemente bloque rígido con costaleros sencillos, no un modelo rigeado entero.
