# Generación de assets del editor

Scripts usados el 2026-11-11 para generar `assets/environment/cathedral/lapidas/` y `muros/`. Las rutas de entrada son locales (zips de Tripo de `assets/inbox`, sin versionar).

## Muro (`assets/environment/cathedral/muros/muro_izq_128.png`)
1. `blender -b -P wall_row_glb.py -- <gothic_arch.fbx> wall_row.glb 5 -45` arma 5 módulos `gothic_arch` (zip `f450c095`). Cada uno mide 14,3 m (128 px de nave), 2,7 m de fondo (48 px) y 8 m de alto. La fila se gira -45° para que el lab la vea a lo largo de la nave.
2. `node tools/lab/export_map_package_headless.cjs wall_row.glb settings.json pkg` con `props_render_settings.json` (luz Neutra), `width` 1322 y `shadows` false. Así sale a 17,9 px/m: la franja mide 48 px y el periodo 128 px.
3. Se recorta una franja de 48×128 que empieza 6 px antes de la junta entre módulos. Alfa = `occlusion.png` ∪ píxeles no negros.

## Lápidas (`assets/environment/cathedral/lapidas/`, v5 del 2026-11-11)
Cuatro estampas: cruz y caballero en bloques de 3×2 y 2×1 losas. La piedra tallada **sustituye al bloque entero de losas**: su borde es la junta del damero. Está a ras del suelo, con los surcos oscurecidos, y la cabeza o el travesaño quedan al fondo de la pantalla (se lee desde los pies).

Cadena (las rutas `<S>` son una carpeta de trabajo fuera del repo):
1. `blender -b -P tomb_glb.py -- <fbx> assets/environment/cathedral/props/glb/lapida_<cruz|caballero>_v2.glb -90 180`: tumba la losa (pitch -90°), la gira 180° y la deja opaca, sin metálico ni alfa. Zip `abc4677e` = cruz, `ceaaedd5` = caballero.
2. `blender -b -P lapida_ao.py -- <glb> <S>/ao/lapida_<n>_v2_ao.glb 0.85`: hornea la oclusión ambiental y la multiplica sobre la textura (surcos oscuros).
3. `python floor_ref.py <S>/floor_ref`: render del lab del suelo con el mismo proceso que `rombos_tripo`. Es la referencia exacta del PNG del suelo.
4. `python lapidas_flush_run.py <S> <tmp>`: monta cada bloque con `lapidas_flush.py` y lo renderiza en el lab (base y sombra). `lapidas_flush.py` es `build_lapidas_lab_blender.py` con tres cambios:
   - la lápida llena el bloque;
   - queda a ras del suelo;
   - se abre un hueco en el mortero bajo el bloque.
5. `python lapidas_cut.py <S>/lapidas_flush <S>/floor_ref/lab_pkg/world.png <salida>`: alinea con el render del suelo, cuantiza y recorta el bloque exacto. Origen de la estampa en el PNG del suelo: (0, 16).

**Retícula real del damero** (medida en `floor_512x256.png`): juntas en `x + 2y ≡ 22,5` y `x − 2y ≡ 16,5` (mod 32). La herramienta original suponía 16 y 16, y eso causó todos los desencajes.

Lecciones:
- Medir la retícula en la imagen; no fiarse de una fórmula heredada.
- Diagnosticar con un bloque de color plano antes de iterar sobre texturas.
- Comparar contra el render del lab del suelo, no contra el PNG cuantizado.
- La lápida tiene que llenar el bloque. Si sobresale, se corre 1–2 px en pantalla: corta el borde norte y deja ver la losa base en el sur.
- Un material de Tripo con el alfa conectado se exporta a GLB como transparente: en Blender salen manchas negras (el lab lo ignora). Convertir siempre a opaco.
- `rot_z` dentro de la escena no surtió efecto en el lab; girar el GLB en origen sí.
