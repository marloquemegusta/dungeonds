# Limpiezas del ARPG (rama `fix/arpg-limpiezas`, 2026-11-22)

Quita los restos del primer prototipo ARPG que ya no encajan, sin tocar el mapa (lo cambia otra sesión en paralelo).

## Qué cambia
- **Árbol de habilidades eliminado del todo.** Ya solo era una capa que leía el inventario; ahora el Glifo depende directamente de tener su tomo puesto. El guardado no cambia: su campo del árbol ya estaba retirado, así que una partida antigua no arrastra mejoras fantasma.
- **Resurrección desenganchada:** los enemigos ya no pueden levantarse como aliados (Levantar está fuera de la protodemo). El código se conserva para cuando vuelva.
- **Escenario `arpg_arbol` borrado** (capturaba el menú del árbol, que ya no existe).
- **Runas de experiencia eliminadas** (ya no salían; quedaba su recogida y su dibujo). El dibujo de la runa sigue en los placeholders horneados porque lo genera `tools/placeholders/`; no se carga en ningún sitio.
- **Documentos:** `DESIGN-ARPG.md` §1–2 describen el juego actual (campamento andable, reliquias, Glifo y lista de hechizos, sin árbol ni Maldición); el texto viejo pasa a `DESIGN-ARCHIVE.md`. El escalón intermedio se llama **Párroco** (no «Monaguillo de choque») en `DESIGN-ARPG.md` §5 y `diseno_juego_final.md` §10, y se avisa de que los modelos de Súper Monaguillo y Súper Monja no están en el repo.

## Evidencia (emulador, escenario `glifo_equipar`, PASS)
- Inventario con el tomo del Glifo puesto y sus engarces: `assets/inventario_glifo.png`.
- Glifo lanzado en la catedral: `assets/glifo_lanzado.png`.

Build `default` sin avisos. Sin medición en la DS (no toca render ni bucles por frame). `TECHNICAL.md`, `assets/MANIFEST.md` y `LORE.md` no cambian. Al unir con la sincronización de MDs de `proto/arpg`, los cambios de diseño se trasladaron de `DESIGN.md` §7 a `DESIGN-ARPG.md` y la entrega va en `STATUS-ARPG.md`.
