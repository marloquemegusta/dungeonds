# Póster del mapa ARPG (versión preliminar)

Póster de las 16 salas de la zona 1 con la composición de props de cada una, sombras bajo luz de techo, columnas frías de noche en los claustros y flechas que apuntan a la sala real. Es una versión preliminar: faltan las luces definitivas por sala y los enemigos. El cofre fijo choca con un enemigo en las salas 5, 7 y 12.

- Póster: [`assets/poster_arpg_v3.png`](assets/poster_arpg_v3.png), móvil [`assets/poster_arpg_v3_movil.png`](assets/poster_arpg_v3_movil.png), noche en los claustros [`assets/poster_arpg_v3_noche_claustros.png`](assets/poster_arpg_v3_noche_claustros.png).
- Visor con zoom: [`poster.html`](poster.html) (necesita las teselas HD, que no se versionan; se regeneran con `python tools/poster/rebuild_poster_arpg.py`). Artifact: https://claude.ai/artifact/FLjbY7xjFe71UgtT5RzwHk (versión 9).
- Herramientas: `tools/poster/` (motor `poster_arpg_v3.py`, composición por sala en `salas/`); `tools/props/prop_shadows.py` con `poster_shadow` opt-in (el juego no cambia). Props nuevos con render en `assets/environment/cathedral/props/render/`.
- Sin versionar (regenerable): `tools/poster/render_amb/`, teselas `assets/hd/`, recortes `assets/salas/` y las versiones v0-v2 del póster.

Verificación: revisión visual del póster; no toca la ROM, así que no hay build ni escenarios.

MDs: `DESIGN-ARPG.md` §11 (composición preliminar por sala), `TECHNICAL.md` §5.6 y `assets/MANIFEST.md` actualizados; `STATUS-ARPG.md` con la entrega.
