# Walkthrough: renderizador dimétrico y sombras horneadas

**Ámbito:** alineación de los assets, anclas y sombras 3D pre-renderizadas para
Nintendo DS. La implementación y evidencia de sombras descritas aquí
corresponden al preset `e30`; `e60` queda por volver a hornear y validar.

## Resumen del método

El mundo se modela y compone en 2D durante el juego, pero la forma, dirección,
oclusión y cobertura de las sombras se obtienen fuera de línea desde las
escenas 3D. El conversor empaqueta los resultados para ARM9. Se conserva el
aspecto de la iluminación 3D sin ejecutar iluminación ni geometría 3D durante
el juego.

Flujo actual:

1. `tools/ds_look.py` define escala, elevación, cámaras, orientación y anclas.
2. `tools/bake_dungeon_iso.py` renderiza suelo y cada objeto en cuatro
   rotaciones. Para cada objeto genera la imagen normal y un pase separado de
   Cycles Shadow Catcher.
3. `tools/bake_player.py` renderiza al personaje en ocho direcciones y hornea
   una sombra por dirección desde una pose plantada de referencia.
4. `tools/shadow_masks.py` convierte el pase RGB de sombra en cobertura
   normalizada. `tools/convert_iso_to_c.py` recorta, cuantiza y empaqueta las
   máscaras en arrays C junto con sus cajas no vacías.
5. `source/main.c` compone esas coberturas sobre el suelo dinámico y pinta los
   sprites encima para conservar la oclusión.

## Lecciones sobre anclas y composición

Los errores recurrentes de alineación no se resuelven ajustando a ojo el
desplazamiento de cada sprite. El punto de apoyo 3D debe viajar con el asset:
para los objetos del entorno, el origen del suelo `(0,0,0)` cae en el centro de
la celda proyectada; para el personaje, el modelo se coloca respecto al origen
de la armature y cada pose se planta midiendo el punto más bajo de la geometría
evaluada. El conversor emite el ancla y el runtime coloca ambos sobre la misma
proyección de suelo. Así no dependemos de los márgenes transparentes ni de la
caja visual del sprite.

La pared, el arco y la columna deben escoger el sprite horneado para su
orientación de mundo. Una pared norte no puede usar por conveniencia el sprite
sur: aunque el muro parezca aproximadamente simétrico, la luz, los extremos y
las uniones del tile revelan el error. Se hornean cuatro rotaciones en vez de
inferirlas a partir de dos.

La misma separación de responsabilidades aplica a las sombras: el horneador
resuelve dirección de luz, silueta y contacto con el suelo; el runtime sólo
mezcla una máscara con el tile de suelo que haya debajo en ese frame. La cámara
puede desplazarse y el fondo cambiar sin recalcular una sombra geométrica.

## Intentos que fallaron y causa

- **Elipses de sombra dibujadas por C.** Se usaba una elipse genérica,
  desplazada respecto a los pies y con forma/tamaño idénticos para entidades
  distintas. No representa la luz de la escena ni la silueta real y se percibe
  como una mancha pegada al personaje. Se eliminó; el runtime ya no inventa
  formas de sombra.
- **Leer el alfa del PNG del Shadow Catcher.** En Blender 5.2 el archivo de
  salida era RGB de luminancia, con alfa constante; el alfa no medía la sombra.
  La cobertura se deriva del oscurecimiento relativo respecto al nivel
  iluminado estimado en las esquinas.
- **Usar `Combined` o activar sólo nodos de composición antiguos.** El pase
  Shadow Catcher no aparecía automáticamente en la imagen final. Hay que
  habilitar `use_pass_shadow_catcher` en la view layer y conectar el socket del
  pase a la salida del compositor nuevo (`scene.compositing_node_group`).
- **API de Blender anterior a 5.2.** `catcher.cycles.is_shadow_catcher`,
  `scene.use_nodes` y `scene.node_tree` no correspondían a esta versión. El
  catcher se marca con `Object.is_shadow_catcher` y se configura el compositor
  nuevo. Son detalles del horneador, no supuestos del runtime.
- **Mismo encuadre estrecho que el sprite visible.** Algunas sombras de arcos
  quedaban truncadas por los bordes. Se amplió el canvas del pase de sombras a
  128×128 manteniendo la escala de píxel y se conserva el recorte central de
  96×96 que consume el juego.
- **Máscaras completas 128×128 a 8 bits en C.** La primera compilación excedió
  EWRAM. Se recorta al canvas central de 96×96, se cuantiza a 4 bits y se
  guardan límites de cobertura para no recorrer el rectángulo vacío. Dos
  píxeles ocupan un byte. Este formato compacto permitió compilar.
- **Capturar inmediatamente al iniciar DeSmuME.** La primera captura precedía
  al primer frame completo del doble búfer y salía negra. El escenario espera
  ahora 60 frames para la captura inicial.

## Invariantes técnicos

- Proyección de suelo y ancla de sprite deben provenir del mismo `ds_look`; no
  se arregla una discrepancia cambiando offsets independientes para muro,
  columna y personaje.
- Cada pared/arco/columna usa la orientación de mundo correspondiente. Se
  hornean cuatro rotaciones (`r000`, `r090`, `r180`, `r270`); las uniones
  dependen de que cada celda seleccione la correcta.
- Máscara de objeto comparte el índice y orientación del sprite: se hornea una
  máscara por orientación. El jugador usa una máscara por cada una de las ocho
  direcciones.
- El catcher es un pase independiente. En el RGB de luminancia, el fondo se
  estima desde las esquinas y la reducción de luz representa cobertura; alfa
  no es fuente válida. Si falta contraste o fondo separable, el conversor debe
  fallar, no emitir silenciosamente una máscara vacía.
- El pase del entorno mide 128×128 y se centra al recortarlo a la máscara de
  runtime de 96×96. Cambiar tamaño/cámara exige actualizar horneador,
  conversor, límites, tests y arrays C conjuntamente.
- El jugador usa una máscara 96×96 por orientación, muestreada desde la pose
  plantada de referencia; no es una sombra distinta por cada frame del ciclo
  de andar. Esto reduce memoria y evita que la sombra fluctúe con la animación.
- Máscaras runtime: cobertura de 4 bits por píxel, dos por byte, más límites
  `[x,y,w,h]`. ARM9 usa enteros; el horneado offline puede usar punto flotante.
- Orden por frame: suelo → máscaras de sombra → sprites ordenados por
  profundidad. Las máscaras sólo oscurecen píxeles de suelo válidos y nunca el
  color de vacío. Las sombras siguen a las entidades y a la cámara; no se
  hornean dentro del tile ni del mapa.
- El suelo recibe sombras pero no emite una máscara. No se sintetizan elipses o
  conos de sombra en C.

## Verificación reproducible

Para el preset actualmente validado, desde la raíz:

```powershell
python tests\test_shadow_masks.py -v
python tools\convert_iso_to_c.py --preset e30
scripts\build-project.ps1 -ProjectPath .
scripts\run-scenario.ps1 -RomPath .\dungeonds.nds `
  -ScenarioPath .\scenarios\integration_showcase_walk.json `
  -OutputPath .\artifacts\baked_shadows_final
```

La prueba comprueba 40 máscaras de objetos (10 familias × cuatro rotaciones)
y las ocho direcciones del jugador, incluyendo dimensiones y contraste. La
compilación comprueba que el conjunto cabe en el presupuesto enlazado; el
escenario arranca la ROM y guarda capturas antes y después de enviar la
secuencia de movimiento. La validación registrada fue
`DSM_SCENARIO_RESULT=PASS` con tres capturas y cinco eventos. Esta ejecución no
incluye una aserción independiente de que el juego consumió la entrada: un
hash o cambio de píxeles por sí solo no lo demuestra. La evidencia es de
DeSmuME, no de hardware real.

La salida registrada está en `artifacts/baked_shadows_final/`: `00_spawn.png`,
`01_walking.png`, `manifest.json`, `events.jsonl` y `emulator.log`.

## Alcance y siguientes pasos

La sombra del personaje representa una pose plantada de referencia por
dirección, no cada frame del ciclo. No se ha medido rendimiento en una DS ni
validado audio/hardware físico. Para cerrar el soporte de `e60`, hay que
rehacer bake de objetos y personaje, ejecutar las mismas pruebas y revisar
close-ups de anclas y sombras.
