# Biblia del escenario: la catedral (v1, 2026-11-08)

Guía paso a paso para producir el escenario del nivel 1. Las **decisiones** viven en `DESIGN.md` §6.9.1b; aquí está el **cómo**: fases, contratos de archivos, presupuestos, verificación y quién hace cada paso. Si algo de aquí contradice a `DESIGN.md`, manda `DESIGN.md` y se corrige esta guía.

Antecedentes: [INFORME_INTENTOS.md](INFORME_INTENTOS.md) (por qué fallaron los intentos de suelo con render continuo).

---

## 0. Ideas que sostienen todo

1. **Lo que se ve en la DS son tiles de 8×8, no imágenes.** El suelo se diseña como juego de tiles desde el principio. Nunca se renderiza una escena entera para trocearla después.
2. **El detalle es gratis si se repite.** Lo que se paga es cada tile *distinto* visible a la vez, no el grano ni el dither de dentro de cada tile.
3. **Las piezas siguen el flujo que ya funciona con los personajes:** imagen → 2D→3D → render con la misma cámara y la misma luz.
4. **La paleta sale de las piezas, no de un concept.** Ningún agente decide la paleta ni la composición: el usuario aprueba la hoja de muestras extraída de los prerenders del lote 1 y las piezas a escala junto al marine.
5. **La verificación es automática y la hace el coordinador.** El contador de tiles, la escala y las costuras se miden; lo que diga un agente no vale como prueba.

## 1. Vocabulario

| Término | Qué es |
|---|---|
| **Tile** | Cuadrado de 8×8 px, el único tamaño que pinta el hardware. 64 bytes a 8 bpp. Un tile y sus volteos H/V cuentan como uno. |
| **Tileset** | La lista de tiles distintos: las "piezas de Lego". |
| **Tilemap** | Cuadrícula que dice qué tile va en cada casilla. El de hardware es de 64×32 casillas (512×256 px) y funciona como cinta circular: al subir se reescriben las filas que entran. |
| **Baldosa / metatile** | Unidad de diseño hecha de varios tiles (32×16 = 8 tiles; 16×16 = 4). |
| **Wang** | Baldosas con bordes etiquetados que encajan sin costura con cualquier vecina de la misma etiqueta. Con 8 piezas el suelo no forma trama visible. |
| **Autotile por esquinas** | 16 baldosas (2⁴ combinaciones de esquinas) que dibujan la orilla entre dos materiales con cualquier forma. |
| **Estampa** | Pieza grande prerenderizada (banco, columna…) alineada a la rejilla de 8 px que se escribe en el tilemap. |
| **Banda** | Trozo de 128 px de alto que el juego elige por hash (`source/strip.c`, kit en `source/strip_kit.c`). |
| **Tramo** | Unidad de diseño de nivel (nave, crucero…) hecha de una o varias bandas. |
| **Estado** | Nivel de profanación 0-3 que se aplica a un tramo con las mismas piezas. |
| **Ventana** | 33×25 tiles: una pantalla más el margen de scroll. Aquí se mide el presupuesto. |

## 2. Medidas fijas

| Cosa | Valor |
|---|---|
| Escala | 17,9 px/m en horizontal, 8,95 px/m en profundidad (suelo achatado 2:1). Marine de 2 m = 31 px de alto. |
| Cámara | Ortográfica, elevación 30°, mirando hacia arriba del carril. Los muros laterales se ven de canto. |
| Carril | 512 px de ancho: muros de **48 px** por lado y **416 px de suelo útil** (23 m). |
| Banda | 128 px de alto (14,3 m de profundidad). |
| Pantalla DS | 256×192. |
| Rejilla de colocación | 8 px (tiles). Baldosa Wang 32×16; baldosa de transición 16×16. |
| Escala de juego | Las piezas pueden ir un 30-50 % por encima de su tamaño real si lo necesitan para leerse. Se decide por pieza mirando el marine al lado. |

La altura y las reglas de composición del tramo lógico están en `DESIGN.md` §6.9.1b, Sesión 1. El usuario dio paso a la sesión 2 usando esa composición como base.

## 3. Presupuestos

| Recurso | Límite duro | Reparto objetivo |
|---|---|---|
| Tiles distintos por ventana | < 440 (pantalla superior: 448 huecos; inferior: 1024) | Terreno ≤ 200 + piezas ≤ 200 + margen 40 |
| Tileset total del nivel (ROM) | Sin límite duro; el juego carga por zonas | Terreno ~256 + piezas ~600 |
| Paleta de fondo | 256 colores BGR555 (el 0 es transparente o el vacío) | Terreno ~48, piezas ~150, luz y velas con ciclo ~16, reserva ~40 |
| Sprites de hardware (OAM) | 128 por pantalla | Haces y polvo ≤ 40; resto para pickups y HUD |
| VRAM de sprites | Banco E 64 KiB (abajo), banco I 16 KiB (arriba) | Haces a 4 bpp |
| CPU | 560190 ticks por frame (regla 6 de AGENTS) | Escenario: ~0 por píxel (todo por hardware o tilemap) |

Cuentas del terreno: 8 baldosas Wang × 8 tiles = 64; tres transiciones × 16 baldosas × 4 tiles = 192; en total **256** en ROM, de los que se ven ~150-200 a la vez.

---

## 4. Fase A: paleta (el arte objetivo se canceló el 2026-11-08)

**Cambio (2026-11-08):** no se generan concepts de pantalla completa. La referencia de estilo es la imagen del banco de `prompts.md`, y la paleta se extrae de los **prerenders del lote 1** (Fase B), que ya llevan la luz de los personajes. Lo que sigue del método antiguo queda como historia.

**Método vigente:**
1. Prerender del lote 1 (§5.2, pasos 1-5 sin la cuantización).
2. `tools/palette/extract_palette.py` sobre los `color.png` de las piezas (piezas) y la textura fuente del suelo (terreno) → `assets/environment/cathedral/palette.json` y hoja de muestras.
3. **Puerta:** el usuario aprueba la paleta mirando la hoja y las piezas a escala.

<details><summary>Método antiguo (cancelado)</summary>


**Para qué:** fijar qué buscamos antes de producir nada. Sale de aquí el criterio de todas las revisiones.

1. **Prompts** (los prepara el coordinador): una pantalla DS de 256×192 vista en 3/4 cenital, a la escala de la §2, con el marine para escala:
   - Nave barricada: bancos volcados, sacos entre columnas, alfombra raída, haces de vidriera desde el muro.
   - Crucero: espacio abierto, mosaico, gran haz del rosetón, velas.
   - Capilla lateral: relicario, santo guerrero, cirios.

   Referencias de estilo: Blasphemous, Trench Crusade, Warhammer 40k, Diablo 2.
2. **Generación**: el usuario con Gemini, 3-6 imágenes por tramo.
3. **Elección**: el usuario marca 1-2 imágenes objetivo por tramo y qué le gusta de cada una.
4. **Paleta**: un script extrae de las imágenes elegidas unos 48 colores de terreno y unos 150 de piezas, en BGR555 (k-means en Lab y redondeo a 5 bits). Salida: `assets/environment/cathedral/palette.json` y una hoja de muestras.
5. **Puerta**: el usuario aprueba la paleta mirando la hoja.

Salidas: `assets/environment/cathedral/target/*.png` (referencia, nunca asset ni evidencia de juego) y `palette.json`.

</details>

## 5. Fase B: piezas (2D→3D)

### 5.1 Catálogo (lote 1 en negrita)

| Pieza | Categoría de colisión | Variantes / estados | Tamaño aprox. en px | Notas |
|---|---|---|---|---|
| **Banco** | Baja (bloquea el paso, no el fuego) | intacto, volcado, roto (madera en el suelo) | 64-72 × 24 | Huella fina (~70×6). La versión rota tiene el mismo tamaño (bancos destructibles en el futuro). |
| **Columna** | Alta (bloquea y ocluye) | entera, desconchada | 24-32 × 64-80 | Va en el muro de 48 px o exenta en el crucero. |
| **Santo guerrero** (estatua) | Alta | entero, decapitado | 32 × 56 | Capilla, crucero. |
| **Relicario** | Baja | cerrado, saqueado | 32 × 32 | Capilla; puede ser el cofre. |
| **Sacos con alambre** | Baja | tramo recto, esquina | 48 × 24 | Guerra (estados 2-3). |
| **Cirio grande / candelabro** | Baja | encendido, apagado | 16 × 32 | La llama va en tiles animados (Fase D). |
| Sarcófago | Baja | cerrado, abierto | 48 × 24 | |
| Púlpito | Alta | | 32 × 48 | Crucero. |
| Confesionario | Alta | | 40 × 48 | |
| Pila bautismal | Baja | | 24 × 24 | |
| Cruzado muerto | Decoración | 3 poses | 24-32 × 16 | |
| Estandarte caído, escombro de bóveda, campana caída | Decoración / baja | | variable | |
| Arco transversal | Alta, ocluye al pasar | con vidriera frontal | 416 × 64-96 | La única ventana vista de frente. |

### 5.2 Flujo por pieza
1. **Concepto 2D** (usuario, Gemini): la pieza aislada sobre fondo liso, vista 3/4, con la imagen del banco como referencia de estilo. Hay plantilla de prompt en `assets/environment/cathedral/prompts.md`.
2. **2D→3D** (usuario, Tripo) → GLB en `assets/models/environment/cathedral/<pieza>/`.
3. **Variantes de estado**: preferiblemente sobre la misma malla (rotar, partir o hundir en Blender por script) y, si no, otra pasada de Tripo.
4. **Render** con la misma cámara y la **misma luz que los personajes** (perfil de `settings.json` de los personajes). Se renderiza la pieza sola, eligiendo el tamaño final en píxeles; así no molesta que el lab fije la escala por la caja del modelo. Del mismo render salen:
   - `color.png`: estampa con alfa.
   - `footprint.png`: huella sobre el suelo en la franja de 0,30-1,20 m. Es la colisión.
   - `depth.png`: profundidad de oclusión con el contrato de `TECHNICAL.md` §3.3.
   - `shadow.png`: sombra de contacto como máscara.
5. **Ajuste a la rejilla**: recorte alineado a 8 px; tras aprobar la paleta (Fase A, que sale de estos mismos prerenders), cuantizado a la paleta global sin dither en los bordes y con dither permitido dentro. Se cuentan sus tiles.
6. **Revisión**: hoja de contactos con la pieza a 1x y a 4x NEAREST junto al marine, sobre el suelo de la Fase C. La aprueba el usuario.

**Renderer:** por defecto el lab (`tools/lab/export_map_package_headless.cjs`), porque es la fuente de la luz de los personajes. Si el lab no da la calidad (no tiene normal maps, se cuelga con mallas grandes), se pasa a Blender Cycles, pero solo después de calibrar la luz para que el marine renderizado en Blender salga igual que el del lab.

## 6. Fase C: suelo

### 6.1 Materiales y lectura
| Material | Uso | Tratamiento |
|---|---|---|
| **Losas de piedra parda** | Base de la nave | Damero de rombos 3D de 32×16 px; dos piedras casi iguales y poco contraste local. |
| Alfombra, mosaico, sangre y cera | Variación de tramos y profanación | Conjuntos de tiles diseñados; transiciones por esquinas, manteniendo tranquilo el suelo transitable. |
| Lápidas de cruzados | Decoración ocasional cada pocas pantallas | Piezas planas prerenderizadas, colocadas a ras del suelo y sin colisión ni sombra. |

### 6.2 Generación
1. **Modelado:** las losas son piezas 3D cuadradas giradas 45°, con junta hundida, bisel y desgaste ligero. La cámara ortográfica a 30° las proyecta como rombos de 32×16 px (lado real aproximado de 1,26 m).
2. **Render:** prerenderizar con la misma cámara y luz única neutra («Neutra») que las piezas y personajes. Alinear cada losa a píxel para que ocupe exactamente su baldosa. El damero alterna dos tonos pardos casi iguales; el albedo permanece casi liso y se repiten variantes para controlar los tiles distintos.
3. **Piezas sobre el suelo:** las lápidas son estampas planas a ras, sin colisión y sin sombra. Columnas, bancos y demás piezas reciben la sombra de la luz neutra horneada en sus estampas, oscureciendo el suelo bajo la huella; la sombra puede extender el recorte de la estampa.
4. **Paleta y legibilidad:** extraer la paleta de los prerenders del lote 1 y mantener valores medios-bajos y poco contraste local en el suelo. Los personajes se prueban sin contorno sobre este suelo; el detalle fuerte queda en bordes, muros y piezas.
5. **Variantes y transiciones:** diseñar tiles de suelo repetibles con Wang y transiciones por esquinas para alfombra, mosaico, sangre y cera; comprobar las uniones y el presupuesto de tiles antes de componer tramos.

Salidas de suelo 2D: `assets/environment/cathedral/floor/` (tiles renderizados, metadatos de variantes y transiciones). Fuentes 3D y renders de piezas se organizan por separado según `REORDEN_ASSETS.md`.
## 7. Fase D: luz

- **Haces de vidriera**: sprites de hardware translúcidos y aditivos, prerenderizados en Blender (pase de luz sola sobre negro), entrando desde los muros laterales hacia el centro, con polvo y respiración global. Contrato y motor: prototipo `proto/godrays` (`assets/sprites/godrays/`, `tools/godrays/`, `source/godrays.c`). Límites:
  - La intensidad de mezcla es una sola por pantalla.
  - Dos haces que se solapan no se suman.
  - Conflicto con la marea, que usa los mismos registros de fusión.
- **Mancha de color en el suelo**: si hace falta más que el haz, se hornea en tiles (~96 tiles por mancha de 96×64). Como mucho 1-2 por pantalla.
- **Velas**: tiles de suelo con vela. Las llamas comparten 1-2 tiles que se reescriben en VRAM cada pocos frames, y el halo usa entradas de paleta con ciclo.
- **Estados**: el estado 0 tiene más velas encendidas y vidrieras enteras; el 3, vidrieras rotas, menos luz y paleta más fría.

## 8. Fase E: composición de tramos

1. **Planta** de cada tramo en JSON: materiales del suelo por celda de 16 px, estampas con posición en la rejilla de 8 px y variante, haces y velas.
2. **Estado** 0-3: un script de "pase de estado" cambia variantes, añade suciedad (sangre, cera, escombro, cadáveres) según la densidad y elige el desplazamiento de paleta.
3. **Reglas que se comprueban** (el compositor falla si no se cumplen):
   - Tres pasillos libres de ≥ 48 px de lado a lado del tramo (búsqueda en la colisión).
   - Huella de bancos ≤ 15 % del suelo útil.
   - Costura con los tramos vecinos: misma etiqueta Wang en las filas de borde.
   - Presupuesto de tiles: peor ventana < 440, contada sobre el encadenado de tramos y no sobre un tramo suelto.
4. **Salida al kit**: tilemap, colisión y oclusión del tramo en el formato del baker (`tools/bake_strip_kit.py`), que se amplía para aceptar tramos.

## 9. Fase F: ROM y cierre

1. Build con la skill: 0 warnings nuevos.
2. Tests de host: contrato de presupuesto, pasillos, costuras, ausencia de `float`.
3. Escenarios headless con geometría verídica (regla 5 de AGENTS): marine cruzando un haz, oclusión tras una columna, colisión contra un banco.
4. Capturas y GIFs de la ROM real a ~50-60 ms por frame, con el marine sin contorno al lado.
5. **Medición en la DS** con `PERF_PROFILE 1` (regla 6): el usuario juega el tramo y se lee el log.
6. Walkthrough, `STATUS.md` y fusión a `main` (con aprobación del usuario).

---

## 10. Quién hace cada paso

| Paso | Quién | Modelo |
|---|---|---|
| Prompts de piezas | Coordinador | Opus |
| Generar imágenes y pasar por Tripo | Usuario | — |
| Script de paleta | Agente | Flash (alto) o Luna (alto) |
| Render de piezas en el lab y contratos (color, huella, profundidad, sombra) | Agente que itera con imagen | Flash (alto) |
| Generador Wang y autotile | Agente | Luna (alto) |
| Compositor de tramos, pase de estado y reglas | Agente | Luna (alto) |
| Motor: haces, velas, ampliación del kit | Agente | Luna (alto) |
| Compilar, escenarios, contar tiles, mirar capturas | Coordinador | Opus |
| Aprobar paleta, piezas y tramos | Usuario | — |

Notas de delegación:
- Luna no arranca Python, Docker ni WSL en su sandbox: escribe el código y el coordinador lo ejecuta.
- Flash itera bien pero sobreafirma, así que toda cifra o "sin costuras" que dé se verifica con imagen y contador.
- Cada brief lleva archivos permitidos, presupuesto y criterio de aceptación.

## 11. Orden de trabajo

1. Prototipo de haces en la DS (`proto/godrays`). **En curso.**
2. Fase B, lote 1: banco, columna, santo, relicario, sacos con alambre, cirio (prerender sin cuantizar).
3. Fase A: paleta extraída de esos prerenders y aprobada por el usuario.
4. Fase C: losa Wang + alfombra.
5. Tramo de prueba "nave barricada" en estado 3, en la ROM, con el marine sin contorno y medición en la DS.
6. Resto de tramos, estados 0-1 y crucero con el gran haz.

## 12. Decisiones abiertas

- Altura del tramo (§2).
- Lab o Blender para el render de piezas (§5.2), según la calidad del lote 1.
- Cómo conviven los haces y la marea cuando las dos están en la misma pantalla (lo dirá el prototipo).
- Personajes sin contorno: se valida en el tramo de prueba (0.3.3).
- Bancos destructibles: mecánica candidata, no entra en la 0.3.2.
