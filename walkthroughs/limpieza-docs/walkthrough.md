# Limpieza de documentación (2026-11-19)

Rama `docs/limpieza-docs`. Solo documentación, un borrado de archivos y comentarios de código; no cambia el juego.

## Qué se hizo
- Cuatro auditorías de solo lectura (DESIGN primera y segunda mitad, TECHNICAL/STATUS/AGENTS, resto de MDs) contrastadas con el código.
- `DESIGN.md` refleja el juego actual: vidas y disparos para matar (Cireneo 4, Abanderado ~37), Ojo sin alcance, relicarios (13 pasillos, 12 Dones y 1 Reliquia dorada), Llaga Abierta con sangre y aura dorada, sin marea, horda, gemas ni XP. Lo retirado está en `DESIGN-ARCHIVE.md` («Retirado en la limpieza de 2026-11-19»).
- `STATUS.md` (30 KB a 7,5 KB) y `TECHNICAL.md` (42 KB a 28 KB) recortados; lo histórico está en `STATUS-ARCHIVE.md`.
- `AGENTS.md` recortado y con una regla nueva: al cerrar, cada sesión revisa y actualiza los MDs afectados. El ciclo de vida de los assets pasa a `assets/MANIFEST.md`.
- `LORE.md` sin la Marea.
- Borrados: `scenarios_legacy/`, tres briefs de encuentros, `FUENTES.md`, `guiones_iteraciones.md`, sprites legacy `marine`/`necron`/`charger` y el test de golpes para matar con armas que ya no existen.
- `bench/` y `BENCHMARK.md` se quedan, con aviso de que no son documentación del juego (72 ítems).

## Pendiente conocido
- `tools/floor/rombos.py`, `tools/floor/build_lapidas_lab.py` y `tools/godrays_art/build_all.py` usaban el sprite `marine` como figura de escala y ya no pueden ejecutarse.
- La cifra de Dones por sala media y dura (~4 y ~8) en `DESIGN.md` es deducida y está como placeholder.
- No se compiló ni se ejecutaron escenarios: no hay cambios de comportamiento.
