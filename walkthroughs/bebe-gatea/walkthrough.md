# El Bebé gatea (fix/campana-pobl, 2026-11-27)

**Causa:** dos cosas. (1) El reposo por papel (`rest_assign`, estado `ENC_S_CRAWL`) solo se activaba si un escenario escribía `dbg_rest_mode`; en la ROM normal ningún enemigo reposaba y los Bebés dormían quietos. (2) El clip del Bebé en la ROM era el andar de pie (`exvoto_bebe_walk`); el FBX de gateo solo se había usado para los vídeos de lore y nunca se horneó para la ROM.

**Cambio:**
- `source/encounters_act1.c` (`rest_mode_for`): por defecto solo el Bebé tiene reposo (gatea en vueltas cortas y se para). El resto de papeles siguen quietos salvo `dbg_rest_mode = 1`.
- `exvoto_bebe` se renderiza ahora desde `exvoto_bebe_crawl.fbx` (8 fotogramas, mismo tamaño que el andar anterior: se fijaron `fitExtent` y `normScale`, ver `assets/MANIFEST.md`). Es su único andar: también gatea al perseguir.
- Re-horneado: sprites del día, `nitrofiles/chars/exvoto_bebe.bin`, `source/player_sprite.c` y las 12 luces (`nitrofiles/arpg_luz/*.bin`, `arpg_light_pack.py <luz> --render`; el paquete de `nave_100` salió idéntico antes del cambio, así que el proceso es reproducible).
- `tools/room_light_slots.py` ignoraba solo los `_fix.bin`; con los `_verja.bin` el generador de sprites fallaba al final. Ahora ignora ambos.

**Evidencia:** `scenarios/arpg_bebe_gatea.json` (Procesión forzada en la Nave 2, héroe a ~90 px sin despertarla): el bebé cambia de sitio y de fotograma, sigue dormido (estado 14) y usa `CHAR_EXVOTO_BEBE`. GIF 4x NEAREST a 20 fps de la ROM: `assets/bebe_gatea.gif`; hoja de 8 fotogramas: `assets/bebe_gatea_hoja.png`.

**Pendiente:** medir en la DS (el clip de gateo comprime distinto: los paquetes de luz pesan ~6 KB menos cada uno). `arpg_reposos` falla igual en la rama base (grupos de la campaña cambiaron slots); no es de este cambio. Los `.rmk` de las salas 9 y 12 que regenera el empaquetado salieron distintos de los versionados y no se tocaron.
