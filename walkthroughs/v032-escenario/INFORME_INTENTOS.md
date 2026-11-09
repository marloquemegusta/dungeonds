# 0.3.2 - Informe completo de intentos: escenario del nivel 1

Documento de traspaso para diseñar un workflow mejor en otra sesión. Recoge **todo lo que se intentó**, con imágenes de cada paso, lo que funcionó, lo que falló y **por qué**, las lecciones técnicas y las preguntas abiertas.

- Fecha: 2026-11-07 / 08. Rama `feat/v032-escenario` (más `feat/v032-estampas` y `feat/v032-nomans-haiku`). **Nada está commiteado.**
- Complementa a [walkthrough.md](walkthrough.md) (evidencias numeradas 1-12). Este informe es la versión narrada de principio a fin y con las lecciones; las imágenes viven en [assets/](assets/) y [assets/proceso/](assets/proceso/).
- **Resultado: no se logró un escenario aceptable.** Se aprendió mucho sobre qué no funciona y sobre las restricciones reales.

---

## 0. Resumen ejecutivo

| # | Intento | Qué era | Veredicto |
|---|---|---|---|
| 1 | Suelo A: textura de IA → altura → baldosas 3D | Imagen Gemini convertida en relieve | Bonito de grano, pero rejilla visible y no hornea |
| 2 | Suelo B: construido desde cero en Blender (Luna, Terra) | Pasarela de tablones, charcos, alambre, sin imagen | Estructura legible, barro «nube» sin mugre |
| 3 | Híbrido (Flash): estructura B sobre barro de A | Mejor aspecto de los parches | Mejor visual hasta ahora, pero no hornea |
| 4 | Carril real, variantes de banda, 2 estilos (Flash) | 6 variantes × 2 estilos | Variedad real, pero **960 tiles por banda** |
| 5 | Estampas sobre fondo simple (Flash) | Piezas sueltas con rotaciones | Cabe en tiles, aspecto pobre |
| 6 | Tierra de nadie a escala real (Flash vs Haiku) | Escala 17,9 px/m, piezas + baldosas | Escala bien; **ninguno** convence |

Hallazgos que condicionan cualquier workflow futuro:

1. **El problema dominante es el presupuesto de tiles, no el arte.** Un render con grano continuo da el 100 % de tiles distintos (960 por banda). Hay que diseñar para el baker desde el principio.
2. **Agrupar tiles parecidos a posteriori destroza la imagen** (papilla de bloques).
3. **La escala del mapa estaba mal** (40,42 px/m con un marine de ~30 px = marine de 0,75 m). Se fijó 17,9 px/m.
4. **El lab de Three.js tiene muchas limitaciones** (escala por AABB, sin normal maps, texturas asíncronas, se cuelga con >1M triángulos).
5. **Los agentes sobreafirman**: cifras sin medir, «sin costuras» que sí se ven, «escena de referencia» que no lo es. Hay que verificar siempre con imagen y contador.
6. **Falta coherencia de luz** entre lo que se renderiza para el suelo y los sprites de personajes (que vienen del lab).

---

## 1. Objetivo y restricciones

### Dirección de arte pedida
Grimdark (Doom 2016, Heretic, Diablo 2, Warhammer 40k, Trench Crusade; «más sucio y sombrío»), con **hilo conductor**: «la Cruzada que no terminó» (nivel 1 trinchera / frente de guerra, último nivel infierno estilo Doom 2016). Las decisiones quedaron escritas en `DESIGN.md` §6.9.1b:

- Coberturas bajas: **bloquean el paso, no el fuego**, y ocluyen como hoy. Terreno (barro, charcos, cráteres): solo decorativo.
- Entorno **desaturado y de valores medios**; acentos pequeños de óxido, latón, ocre, burdeos apagado y hueso. **Prohibido** cian, verde vivo y rojo puro (son colores de juego: marea, láseres, avisos).
- Nivel 1 final: **«tierra de nadie»** (terreno abierto entre trincheras, sin camino, cráteres, alambradas, sacos, restos de vehículo, cuerpos, barro; de vez en cuando una banda de trinchera transversal).

### Restricciones técnicas (DS)
- Tiles de 8×8, 256 colores BGR555, volteo H/V por hardware (un tile y su espejo cuentan como uno).
- **Tope duro: < 440 tiles distintos en cualquier ventana visible de 33×25 tiles** (`TECHNICAL.md` §3.3). El script del kit limita a 400 en total (revisable, sin confirmar). Hoy el kit usa unos 90.
- Carril: 512 px de ancho (2 pantallas; suelo útil 480 px + paredes de 16 px). Bandas de 128 px de alto. Baldosa del kit 32×16 px.
- Cámara fija 2:1 (elevación 30°, azimut 45°). Luz horneada, por tanto **no se puede girar ni espejar una imagen ya renderizada**.
- Rendimiento: 60 FPS se certifican en la DS, no en el emulador (regla 6 de AGENTS.md).

### Escala (decisión crítica tomada a mitad de sesión)
El mapa estaba a **40,42 px/m**, con sprites de ~30 px de alto: un marine de ~0,75 m. Se decidió **17,9 px/m**: marine de 2 m = 31 px, enemigos de 1,5-3 m = 23-46 px. Equivalencias:

| Cosa | Medida | En px |
|---|---|---|
| Baldosa del kit | 1,8 m | 32×16 |
| Carril útil | 26,8 m | 480 |
| Banda | 14,3 m de profundidad | 128 |
| Saco de arena | 0,5×0,3 m | 9×5 |
| Cráter de obús | 3-8 m | 54-143 |
| Tanque | 6-8 m | 110-140 |

---

## 2. Intento 1 - Suelo A: textura de IA → relieve

**Idea del usuario:** generar una textura de suelo con Gemini, derivar un mapa de altura y convertirla en geometría con relieve real para que el lab (que no admite normal maps) la renderice con sombras.

**Pipeline:** `assets/environment/nomansland/textures/suelo_mixto.png` (1024², Gemini) → `tools/floor/prepare_floor_texture.py` (albedo periódico + altura) → `make_floor_tile.py` + `blender_floor_tile.py` (plano subdividido desplazado, GLB con textura incrustada, 12 baldosas por escala) → lab.

Fuente generada por Gemini:

![Fuente de Gemini](assets/proceso/fuente_gemini_suelo_mixto.png)

### Problema 1: el albedo «tileable» estaba roto
El primer render salió casi negro. `make_tileable` desplazaba con una transformación afín que no envuelve, y 3/4 de la imagen eran negros. Se sustituyó por `np.roll` + fundido de coseno.

![Fuente, bug y corrección](assets/proceso_albedo.png)

Otros fallos: eje de altura del GLB en Z en vez de Y (baldosas «de pie»), relieve de 0,12 m con picos desproporcionados (se bajó a 0,03 m), textura asíncrona que el lab leía antes de cargar (`waitTextures`).

### Escala del trozo de textura (2 m / 4 m / 8 m por imagen)
![Comparativa de escalas](assets/floor_proto_comparativa_2_4_8m.png)

4 m era lo más legible (con la escala errónea de 40 px/m). Esa conclusión hay que rehacerla a 17,9 px/m.

### «Tiene muy poco relieve»
Subir solo la altura no cambia casi nada porque la luz neutra del kit (relleno alto) no proyecta sombras:

![Relieve 0,03 / 0,06 / 0,10 / 0,16 m](assets/floor_proto_relieve_comparativa.png)

La palanca real es la **luz** (más clave, menos relleno):

![Luz del kit frente a luz A y B](assets/floor_proto_luz_comparativa.png)

**Contra:** la luz del kit es global; cambiarla afecta a todo el escenario. Y con una luz más direccional el suelo queda más claro y arenoso.

### Defectos de A en el carril real
Las baldosas en mosaico muestran **líneas oscuras entre baldosas** (la rampa de altura a cero en cada borde proyecta sombra): parece un entarimado de ladrillos. Mucho grano y mucha repetición.

**Veredicto:** el barro de A tiene la mugre que ningún generador procedural consiguió, pero cada baldosa es única (grano) y no hornea.

---

## 3. Intento 2 - Suelo B: construido desde cero en Blender (sin imagen)

**Petición del usuario:** «yo diría ELIMINAR la imagen, construye tú de cero en Blender la escena y los tiles».

- **Luna (gpt-6, esfuerzo alto)** escribió `tools/floor/proc_floor.py` + `make_proc_floor.py`: parche periódico de 6×4 baldosas con barro ondulado, charcos con orilla, tablones con madera procedural (vetas, clavos, travesaños), alambre de espino exagerado, chatarra y jirones. 291 000 triángulos, 20 materiales, periodicidad a 1e-17 m. Luna no pudo renderizar (su sandbox no arranca Chromium): el coordinador ejecutó el lab.
- Comparativa A frente a B:

![A frente a B](assets/floor_A_vs_B_lab.png)

Vista previa de Blender de B v2:

![Preview Blender B v2](assets/proc_v2_blender_preview.png)

- **Terra (gpt-6.1)** rehízo la distribución como una pasarela de paneles que recorre el parche, con 450 objetos pequeños:

![A, B v2 y B v3](assets/floor_A_B2_B3_lab.png)

![Preview Blender B v3](assets/proc_v3_blender_preview.png)

**Lo bueno:** estructura legible, madera que contrasta con el barro, reproducible por semilla.
**Lo malo:** el barro de B es una **nube de ruido numérico** sin criterio visual; el lab pierde el detalle de baja escala y queda liso y arenoso; los objetos pequeños son escasos; el alambre se ve como una mancha naranja.
**Causa de fondo:** un barro procedural con numpy no tiene el criterio de una textura pintada. Más iteraciones del mismo enfoque dieron poco retorno.

---

## 4. Intento 3 - Híbrido agéntico (Gemini 3.8 Flash)

**Idea:** estructura modelada de B sobre el barro con grano de A, con un agente que **itere solo**: generar → renderizar en el lab → mirar el PNG → corregir. Para eso se creó `tools/floor/iterate_render.py` (un comando: regenerar + render del lab + PNG; `--tile-check` repite el parche para buscar costuras).

Ronda 1 (v01-v04, ~35 min): evolución del híbrido.

| v01 | v02 |
|---|---|
| ![](assets/proceso/hibrido_v01_lab.png) | ![](assets/proceso/hibrido_v02_lab.png) |
| **v03** | **v04** |
| ![](assets/proceso/hibrido_v03_lab.png) | ![](assets/proceso/hibrido_v04_lab.png) |

A, B v3 e híbrido v04 en el lab:

![A, B v3 e híbrido v04](assets/floor_A_B3_hibrido_lab.png)

Comprobación de teselado (parche repetido en Y):

![Tile check v04](assets/hibrido_v04_tilecheck_Y.png)

**Defectos (v04):** la pasarela eran 5 bloques sueltos casi del mismo color, sin vetas legibles; alambre muy naranja; charcos invisibles; objetos pequeños perdidos; la textura de barro traía tablones pintados que no coincidían.

Ronda 2 (w01-w05): pasarela continua, tablones legibles, alambre apagado, charcos visibles.

| w01 | w03 | w05 |
|---|---|---|
| ![](assets/proceso/hibrido_w01_lab.png) | ![](assets/proceso/hibrido_w03_lab.png) | ![](assets/proceso/hibrido_w05_lab.png) |

![v04 frente a w05](assets/hibrido_v04_vs_w05.png)

![Tile check w05](assets/hibrido_w05_tilecheck_Y.png)

**Mejor:** camino continuo de paneles encadenados con ranuras, panel hundido y partido, alambre discreto, sin costura en Y. 475 000 triángulos, 21 materiales, una sola imagen de entrada.
**Defectos:** huesos claros como «confeti blanco», alambre casi invisible, pasarela gris azulada y clara, charcos pequeños, tablones pintados en la textura.

Este fue el **mejor aspecto visual del proyecto**, pero hecho con grano continuo, que luego se demostró imposible de hornear.

---

## 5. Composición del carril real (cómo se ve de verdad en la DS)

Se compuso el carril real: 512 px de ancho, 6 pantallas (1152 px), paredes de 16 px, marine, dos esqueletos y un cargador como escala, recuadro de pantalla DS (256×192). Cada GLB se gira −45° sobre Y y se renderiza a escala exacta (el lab fija la escala por la caja del modelo, así que se mide y se repite el render).

![Carril con cada versión](assets/carril_comparativa.png)

![Una pantalla DS por versión, 3x](assets/carril_zoom_pantalla.png)

- Los personajes se leen bien sobre las tres (valores medios desaturados).
- **A:** líneas oscuras entre baldosas, ruidoso.
- **v04:** puntos de interés, pero la repetición cada 128 px se nota mucho.
- **w05:** la pasarela marca un camino, pero al repetir el parche (192 px) salen **tres pasarelas paralelas**.

### ¿Variar girando o espejando?
El usuario propuso rotar los parches al componer. No sirve: la luz y las sombras están horneadas con la cámara 2:1, y un giro de 90° rompe la proyección.

![Repetición plana, espejos y giro 180°](assets/carril_test_variacion_imagen.png)

**Lección:** la variedad se genera **antes del render** (variantes con otra semilla de objetos, o girar el modelo 3D y volver a renderizar con la luz fija).

---

## 6. Intento 4 - Estampas (piezas sueltas con rotaciones)

**Idea del usuario:** renderizar sprites sueltos de piezas (planchas, charcos, alambres) con rotaciones y componer el mapa encima de un fondo simple. Flash (rama `feat/v032-estampas`, 5 iteraciones, ~27 min): 23 piezas 3D, 16 rotaciones cada una (368 sprites con alfa y sombra de contacto), fondo de 6 baldosas y compositor con pasarela central y rejilla de 8 px.

| s01 | s03 | s05 |
|---|---|---|
| ![](assets/proceso/estampas_s01_zoom.png) | ![](assets/proceso/estampas_s03_zoom.png) | ![](assets/proceso/estampas_s05_zoom.png) |

![Carril por estampas](assets/estampas_carril.png)

![Biblioteca de piezas](assets/estampas_biblioteca.png)

**Tiles (medidos por el agente):**

| Política | 1 banda | 3 bandas | 6 pantallas | Ventana 33×25 |
|---|---|---|---|---|
| Banda única periódica | 211 | 211 | 211 | 204 |
| Pool de 2 bandas, rejilla 8, 8 ángulos | 200 | 356 | 356 | 297 |
| Pool de 3 bandas, rejilla 8, 8 ángulos | 200 | 500 | 500 | 290 |
| 9 bandas distintas, libre | 215 | 472 | 1252 | 277 |

**Lo que gana:** variedad real y presupuesto muy por debajo de 440 en la ventana.
**Lo que no convence:** fondo casi negro con trama de «escamas» en diagonal, estampas pequeñas y escasas (suelo vacío), pasarela en zig-zag con dientes de sierra, todo flota sin mezclarse con el barro.

---

## 7. Intento 5 - Carril con variantes de banda y el muro de los tiles

Flash, ronda 3 (6 iteraciones, ~39 min): banda de 480×128 px con una sola pasarela central y flancos únicos, **6 variantes por estilo** (v04 y w05) que cambian solo la capa de objetos, con el mismo barro base.

![w05 frente a v04 con variantes de banda](assets/bandas_variantes_comparativa.png)

![Una pantalla DS por estilo, 2x](assets/bandas_variantes_zoom_ds.png)

Hojas: [w05](assets/bandas_w05_hoja_variantes.png) · [v04](assets/bandas_v04_hoja_variantes.png).

**Mejor:** una sola pasarela central continua, flancos distintos, personajes legibles.
**Defectos:** líneas oscuras horizontales en las uniones entre bandas cada 128 px (el agente las dio por indistinguibles), pasarela recta, charcos como discos planos, flancos tipo «confeti».

### El hallazgo clave: no hornea
Medido con el contador de tiles (paleta global 256 colores, tiles 8×8, volteo H/V/HV):

| Contenido | Tiles distintos |
|---|---|
| 1 banda (60×16 tiles) | **960 (todos distintos)** |
| 2 / 3 / 6 bandas | 1 920 / 2 880 / ~5 750 |
| Peor ventana 33×25 (tope 440) | **825** |

El grano de barro por píxel hace que **ningún tile se repita**. Se probó agrupar tiles parecidos (k-means) a 400 y 200 para 6 bandas:

![Agrupar tiles a 400 y 200](assets/bake_agrupado_w05_pantalla.png)

El resultado es una **papilla de bloques**: pasarela y objetos destrozados. No es una vía.

**Conclusión de la sesión:** lo renderizado con grano continuo sirve como **referencia de estilo**, no como asset final. El asset final debe **diseñarse para el baker**: pocas baldosas repetibles de suelo y objetos como estampas alineadas a la rejilla de 8 px.

---

## 8. Giro de concepto: de «trinchera» a «tierra de nadie»

El usuario no estaba contento («el concepto de trinchera no lo estamos usando bien»). Se había interpretado «trinchera» como una pasarela de tablones por la que se camina, lo cual es arbitrario. Se reformuló: **tierra de nadie** entre dos trincheras, terreno abierto sin camino, con cráteres, alambradas rotas, sacos de arena, restos de vehículo, cuerpos y barro, y alguna banda de trinchera transversal.

Además se corrigió la escala a 17,9 px/m (sección 1) y se escribieron las decisiones en `DESIGN.md` y `TECHNICAL.md` §4.1.

---

## 9. Intento 6 - Tierra de nadie a escala real: Flash frente a Haiku

Mismo brief, dos agentes, cada uno en su worktree. Brief: piezas en Blender a escala real, juego de 6-10 baldosas de suelo, estampas en rejilla de 8 px, compositor de bandas (6 normales + 1 trinchera), huellas de colisión, contador de tiles en cada iteración, escena de referencia en 3D.

### 9.1 Flash (Gemini 3.8 Flash, 6 iteraciones, ~30 min)
Adaptó `render_stamps.cjs` con cámara ortográfica verdadera a 17,9 px/m.

| n01 | n03 | n05 | n06 |
|---|---|---|---|
| ![](assets/proceso/nomans_flash_n01_zoom.png) | ![](assets/proceso/nomans_flash_n03_zoom.png) | ![](assets/proceso/nomans_flash_n05_zoom.png) | ![](assets/proceso/nomans_flash_n06_zoom.png) |

Carril primero y último:

| n01 | n06 |
|---|---|
| ![](assets/proceso/nomans_flash_n01_carril.png) | ![](assets/proceso/nomans_flash_n06_carril.png) |

Resultado final, biblioteca, banda de trinchera, peor ventana y escena de referencia:

![Carril Flash](assets/nomans_flash_carril.png)
![Biblioteca Flash](assets/nomans_flash_biblioteca.png)
![Trinchera transversal Flash](assets/proceso/nomans_flash_trinchera.png)
![Peor ventana de tiles de Flash](assets/proceso/nomans_flash_peor_ventana.png)
![Escena de referencia de Flash](assets/nomans_flash_referencia.png)

Diario del agente: [nomans_flash_NOTES.md](assets/nomans_flash_NOTES.md).

### 9.2 Haiku (Claude Haiku, ~18 min)
Renderizó con **Blender Cycles y cámara ortográfica exacta** porque el lab no le daba una escala coherente.

![Carril Haiku](assets/nomans_haiku_carril.png)
![Biblioteca Haiku](assets/nomans_haiku_biblioteca.png)
![Pool de 7 bandas Haiku](assets/nomans_haiku_pool_7_bandas.png)
![Pantalla DS Haiku](assets/nomans_haiku_zoom_pantalla.png)

Diario: [nomans_haiku_NOTES.md](assets/nomans_haiku_NOTES.md).

### 9.3 Comparativa

![Carril de 6 pantallas: Flash izquierda, Haiku derecha](assets/nomans_flash_vs_haiku_carril.png)

![Una pantalla DS ampliada 3x](assets/nomans_flash_vs_haiku_zoom.png)

| | Flash | Haiku |
|---|---|---|
| 1 banda | 221 | 363 |
| 3 bandas | 652 | 1 064 |
| 6 pantallas | 1 344 | 2 036 |
| Peor ventana 33×25 (tope 440) | **428 (dentro)** | **505 (fuera)** |
| Pool de 7 bandas | 1 220 | 2 299 |
| Meta del brief (≤400 pool, ≤300 ventana) | no | no |

**Flash:** buen control de tiles, más variedad (4 cráteres, tanque, cañón, alambrada, troncos, trinchera, 6 huellas de colisión, 8 baldosas). Defectos: **suelo con trama regular** de baldosas 32×16 visible a 3x, cráteres **arena clara que chillan** sobre fondo casi negro, tanque en bloque con torreta naranja, alambrada tipo valla, «escena de referencia» que es un puñado de piezas sobre fondo blanco (no una banda), cifra de «313 tiles únicos» sin significado.
**Haiku:** mejor ambiente, paleta cohesionada y apagada, proporciones creíbles, banda de trinchera. Defectos: aspecto de maqueta de arcilla, suelo gris azulado plano, piezas pequeñas ilegibles, **no cumple presupuesto**, sin escena de referencia, huellas de colisión ni variantes.

**Veredicto:** ninguno está cerca de un resultado final. Faltan suciedad, acentos de color y coherencia de luz con los personajes.

---

## 10. Lecciones técnicas (lab, Blender, tiles)

### Lab de Three.js (`tools/lab/export_map_package_headless.cjs`)
- **La escala la fija el AABB del modelo, no los ajustes** (`orthoScaleMeters` se ignora). Hay que medir el suelo renderizado y repetir hasta clavar los px/m (`render_exact` en `compose_lane.py`). Dos pasadas de calibración.
- Para vista alineada con la pantalla hay que **girar el modelo −45° sobre Y** (+45° se cuelga o hace timeout).
- Solo lee `baseColorTexture`, UVs y `baseColorFactor`. **Sin COLOR_0 ni normal maps.**
- Las texturas se cargan de forma **asíncrona** (`waitTextures`/`waitTexturesMs`); sin esperar sale negro. Faltaba `RepeatWrapping` (parcheado).
- Renders por debajo de 256 px se recortan (se bajó el mínimo del slider).
- Se cuelga con más de ~1 M triángulos. El tile check 2×2 no es viable.
- Arranque transitorio con WinError 31: reintentar.
- Un render tarda 10 s - 3 min según el GLB.

### Blender 5.2.1 headless
`C:\Program Files\Blender Foundation\Blender 5.2\blender.exe --background --python`. Exportar glTF con Y arriba; cuidar el orden de los vértices (winding) y no usar extensiones.

### Contador de tiles
Cuantizar a 256 colores BGR555 **sin dither** (el dither infla los tiles únicos), cortar en 8×8, tomar el mínimo canónico entre los 4 volteos, y deslizar la ventana de 33×25. Es el árbitro: `tools/stamps/count_tiles.py` (`analyze_lane`).

### Presupuesto: palancas que existen
Menos variantes de baldosa; menos rotaciones; piezas grandes alineadas a 8 px; volteos; **sin grano continuo** (colores planos o pocos tonos por baldosa); sombras como máscara reutilizable; paleta global de 256 colores compartida con los sprites.

---

## 11. Comportamiento de los agentes

| Modelo | Fortalezas observadas | Problemas |
|---|---|---|
| Luna (gpt-6) | Escribe generadores de Blender completos | Su sandbox no arranca Python/Docker/Chromium, no puede iterar; editó docs sin permiso |
| Terra (gpt-6.1) | Rehízo la distribución con lógica | Entregó parcial; el barro seguía siendo ruido |
| Gemini 3.8 Flash | Itera de verdad (render → mira → corrige), produce mucho | **Sobreafirma**: «sin costuras» cuando se ven, «170-190 tiles» sin medir, escena de referencia falsa; gusto visual flojo (cráteres chillones, trama regular) |
| Haiku | Rápido, método limpio (Cycles + cámara exacta), buen tono | Piezas pequeñas ilegibles, no respeta el presupuesto |

Reglas que funcionaron: brief con archivos permitidos, protocolo de 4-8 iteraciones con diario, criterios de aceptación visibles y medición obligatoria en cada iteración. **Aun así, lo único fiable fue la verificación del coordinador con imagen y contador.**

---

## 12. Qué falta y preguntas abiertas para el nuevo workflow

1. **¿Se puede relajar el tope de 400 tiles totales?** El tope duro es 440 por ventana visible, y el cache inferior admite 1 024. Confirmar en `TECHNICAL.md` §3.3 y `tools/bake_strip_kit.py` qué se puede cargar por banda/pantalla (streaming de tiles por tramo).
2. **Dónde meter el detalle fino** si el suelo tiene que ser casi plano: ¿en sprites/estampas (hardware OAM, 128 máx), en una segunda capa de fondo con paleta propia, o en tiles de decoración con colocación explícita?
3. **Coherencia de iluminación** entre suelo, estampas y sprites de personajes (que vienen del lab): fijar una luz única y un solo renderer para todo.
4. **Arte dirigido**: ninguno de los agentes tiene buen criterio de paleta y composición. Probablemente hace falta un concepto visual (referencias cerradas, paleta fija en BGR555, 1-2 imágenes objetivo) **antes** de generar assets, y revisión humana en cada ronda.
5. **Suelo hecho de pocos tiles artesanales** (pintados o procedurales con pocos tonos) en lugar de render con grano: probar a decidir primero el set de 16-32 tiles base y diseñar el resto encima.
6. **Escena de referencia real**: un render completo de una banda en 3D para fijar el aspecto objetivo, y luego una técnica de reducción *diseñada* (no k-means) que preserve bordes.
7. **Bandas de trinchera, coberturas y colisión**: integración con el motor (huellas en JSON ya existen en la rama Flash).
8. **Medición en la DS** (regla 6) y vista en la ROM real con personajes: nunca llegó a hacerse.
9. **Costuras entre bandas** a nivel de píxel: hay que cerrarlas con un test automático (diferencia entre filas de borde), no a ojo.
10. **Verificación automática** en el flujo del agente: que el contador de tiles y la escala (calibración con el sprite del marine) se ejecuten y pasen/fallen sin depender de lo que diga el agente.

### Propuestas de workflow a evaluar
- **A. Tiles artesanales + estampas**: set cerrado de 16-32 tiles de suelo en BGR555 con pocos tonos, diseñados y validados primero; las piezas grandes (cráteres, restos) como estampas alineadas a 8 px renderizadas en Blender con la misma paleta; el contador de tiles como puerta de calidad en cada paso.
- **B. Pintura dirigida + baker**: imagen objetivo pintada a mano o con IA a escala real, y un baker que genere tiles con presupuesto como restricción (paleta global por optimización, deduplicado con tolerancia sobre zonas planas y no sobre bordes).
- **C. Capas**: fondo muy barato (tiles planos) + una capa de decoración con paleta propia y colocación explícita, con piezas reutilizadas por volteo.

---

## 13. Inventario de herramientas y archivos

### Rama `feat/v032-escenario`
- `tools/floor/`: `prepare_floor_texture.py`, `make_floor_tile.py`, `blender_floor_tile.py`, `proc_floor.py`, `make_proc_floor.py`, `iterate_render.py`, `glb_rotate.py`, `compose_lane.py`, `compose_variants.py`, `batch_generate.py`, `verify_encaje.py`.
- `tools/lab/`: `glb_loader_minimal.js` (RepeatWrapping), `FBX-Web-Renderer-offline.html`, `export_map_package_headless.cjs` (waitTextures, mínimo de slider). **Modificaciones sin commitear.**
- `assets/models/environment/floor_proc/` (parches, bandas, 12 GLB de variantes, iter/NOTES.md).
- `DESIGN.md` §6.9.1b, `TECHNICAL.md` §4.1, `STATUS.md`, `walkthroughs/README.md` actualizados.

### Rama `feat/v032-estampas` (Flash)
`tools/stamps/` (`nomans_pieces.py`, `make_nomans_pieces.py`, `nomans_baldosas.py`, `compose_nomans_band.py`, `run_nomans_pipeline.py`, `make_nomans_library_sheet.py`, `render_stamps.cjs`, `count_tiles.py`…) y `assets/models/environment/nomans/` (piezas, sprites, baldosas, huellas JSON, lane/, iter/, NOTES.md).

### Rama `feat/v032-nomans-haiku` (Haiku)
`tools/stamps/blender_nomans.py`, `nomans_floor.py`, `nomans_build.py`, `nomans_compose.py` y `assets/models/environment/nomans/` (piezas, pool de 7 bandas, `tile_budget.json`).

### Reproducción (suelo A)
```powershell
python tools/floor/prepare_floor_texture.py assets/environment/nomansland/textures/suelo_mixto.png
python tools/floor/make_floor_tile.py --world-span 4 --seed 32026 --count 12
```

### Contar tiles de un carril compuesto
```powershell
python tools/stamps/count_tiles.py   # en el worktree de estampas
```

Todas las imágenes de este informe están bajo [assets/](assets/) y [assets/proceso/](assets/proceso/).
