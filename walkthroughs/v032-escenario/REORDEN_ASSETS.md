# Propuesta de reordenación de assets

Propuesta documental; no se ha movido ningún archivo.

## Árbol propuesto

```text
assets/
├── models/
│   └── environment/cathedral/
│       ├── sources/                 # fuentes originales de modelado
│       │   ├── banco/               # FBX, GLB y zips originales
│       │   ├── columna/
│       │   ├── santo/
│       │   ├── relicario/
│       │   └── tripo/                # lápidas v2 y losas de Tripo
│       └── work/                     # mallas convertidas/variantes editables
└── environment/cathedral/            # resultados 2D y datos de juego
    ├── props/render/<pieza>/         # color, footprint, depth, shadow
    ├── floor/<variante>/             # tiles, mapas y metadatos
    └── palette/
```

Las fuentes FBX, GLB y ZIP quedan en `assets/models/environment/cathedral/...`; los prerenders 2D, paletas, tiles y datos de runtime permanecen bajo `assets/environment/cathedral/...`. Tras revisar los nombres de los archivos de entrada, mover desde `C:\codexlocal\dungeonds\assets\inbox` las **lápidas v2** y las **losas de Tripo** a `assets/models/environment/cathedral/tripo/`.

## Rutas de `tools/` que habría que actualizar

- `tools/props/prep_props.py` y `tools/props/prerender_props.py`: raíz de modelos/fuentes frente a salida de render.
- `tools/props/prop_shadows.py` y `tools/props/contact_sheet.py`: rutas de renders de props (mantener resultados 2D bajo `assets/environment`).
- `tools/bake_cathedral_kit.py`: rutas de `props/render` y paleta.
- `tools/floor/losas_3d.py`, `tools/floor/losas3d_h.py`, `tools/floor/rombos.py`, `tools/floor/rombos_h.py`: entradas de props prerenderizadas y salidas de suelo.
- `tools/floor/losas_cuadricula.py`, `tools/floor/tiles_sueltos.py`: salidas de suelo; `tools/palette/README.md`: ejemplo de ruta de salida.
- `tools/render_all_40px_headless.cjs`: entradas FBX existentes en `assets/inbox` si también se trasladan esas fuentes.
