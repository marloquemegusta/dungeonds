# Campamento (props)

Piezas de la zona de campamento, generadas con el mismo pipeline de props de la catedral.

| Pieza | Origen | Render / GLB |
| :--- | :--- | :--- |
| `camp_mesa` | Tripo `49adda99` (mesa de desguace, v2 19:21) | `assets/environment/cathedral/props/{render,glb}/camp_mesa` |
| `camp_jergon` | Tripo `8cc28e31` (jergón, v2 19:21) | `.../camp_jergon` |
| `camp_atril` | Tripo `b2e93f3e` (atril con libro, v2 19:21) | `.../camp_atril` |
| `camp_hoguera` | Tripo `701a10ac` (hoguera, nuevo) | `.../camp_hoguera` |

Versiones descartadas por la tanda de 19:21: `51d7242f` (mesa), `d7bffbe0` (jergón),
`b8297d1a` (atril) y el placeholder magenta que sustituía a la hoguera.

El pipeline escribe en `assets/environment/cathedral/props/render/` y `glb/` (rutas que lee
`tools/props/prerender_props.py` y `tools/bake_cathedral_kit.py`). Esta carpeta documenta el
conjunto de campamento; no duplica los binarios.
