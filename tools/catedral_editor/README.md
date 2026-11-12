# Editor de Planta de la Catedral

Herramienta HTML de archivo único y autocontenido para componer y estampar piezas prerenderizadas sobre el carril de la catedral (512 px de ancho, muros en x=0..48 y x=464..512).

## Regeneración
No requiere dependencias npm. Para regenerar `editor.html` tras añadir o modificar piezas:
```bash
node tools/catedral_editor/build_editor.cjs
```
Abre `tools/catedral_editor/editor.html` directamente en el navegador con doble clic (`file://`).

## Elementos y Reglas de la Segunda Ronda

1. **Muro nuevo:**
   - Textura RGBA de 48×128 px con repetición vertical sin costura (periodo de 128 px).
   - Muro izquierdo en x=0..48; muro derecho en x=464..512 volteado horizontalmente.
   - Pinta fondo base `#1c1920` bajo las transparencias y prescinde de líneas interiores provisionales.

2. **Ventanas con haz de luz (categoría «Luz»):**
   - Dos tipos: «Haz vidriera» (`haz_vidriera`) y «Haz rosetón» (`haz_roseton`), sprites de 256×128 px.
   - La ventana física queda fuera del tiro de cámara; solo se proyecta su luz.
   - Lado automático al hacer clic: mitad izquierda (x < 256) coloca en muro izquierdo (`side: "L"`, esquina en x=16); mitad derecha (x ≥ 256) coloca en muro derecho (`side: "R"`, esquina en x=240 con volteo horizontal).
   - Renderizado aditivo translúcido (`lighter`, opacidad 0,6) por encima de piezas y sombras.
   - Seleccionable, movible solo en vertical y orientable con `F` (conmuta L/R).
   - Casilla «Ver luces» en la barra de herramientas para alternar su visibilidad.

3. **Lápidas definitivas (4 variantes de Vía A y Vía B):**
   - Sustituyen a las 36 lápidas provisionales antiguas.
   - Variantes: `via_a_3x2_cruz`, `via_a_3x2_cab`, `via_b_3x3_cruz`, `via_b_3x3_cab` (128×96 px).
   - **Encaje obligatorio con las juntas del suelo:** al estampar o mover, ajusta la esquina superior izquierda a `Y` múltiplo de 8 y, con `k = (Y - 16) / 8`: si `k` es par, `X ≡ 0 (mod 32)`; si `k` es impar, `X ≡ 16 (mod 32)`.
   - Se dibujan al nivel del suelo (debajo de sombras y props con volumen).
   - Al cargar un JSON antiguo que contenga lápidas viejas, se descartan y se avisa («N lápidas antiguas ignoradas»).

## Formato del JSON (`catedral_seccion.json`)
```json
{
  "version": 1,
  "width": 512,
  "height": 1920,
  "screens": 10,
  "items": [
    { "piece": "columna_entera", "x": 72, "y": 1500, "flip": false },
    { "piece": "via_a_3x2_cruz", "x": 64, "y": 1456, "flip": false },
    { "piece": "haz_vidriera", "x": 0, "y": 1400, "side": "L" }
  ]
}
```
- `width`: 512 px (ancho fijo del carril).
- `height`: alto total en píxeles (`screens * 192`).
- `screens`: número de pantallas DS (192 px de alto cada una; Pantalla 1 en la base, avance hacia arriba).
- `items`: lista de piezas estampadas.
  - Para props y lápidas: `x, y` en píxeles (esquina superior izquierda de `color.png`) y `flip` (espejado horizontal).
  - Para haces de luz: `piece`, `x: 0`, `y` y `side: "L" | "R"` (`x` se ignora).
