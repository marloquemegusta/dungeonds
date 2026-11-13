# Fix: parpadeo de enemigos en la pantalla superior (`fix/top-flicker`)

## Problema
Algunos enemigos en la pantalla superior parpadeaban o titilaban de forma intermitente, incluso manteniendo 60 FPS.

## Causa
- La pantalla superior es de búfer único (`s_top_page`, 96 KiB en el banco C de 128 KiB), a diferencia de la pantalla inferior que usa doble búfer (`s_bot_active_page` / `s_bot_back_page`).
- El bucle anterior ejecutaba primero toda la lógica del juego (`player_update`, `strip_enemies_update`, `weapons_and_effects_update`) después de `swiWaitForVBlank()`, y solo después llamaba a `render_screen(s_top_page, ...)`.
- Cuando la lógica consumía la ventana de VBlank (~71 líneas / ~4,5 ms), `clear_dirty_spans` borraba los enemigos y `draw_enemy` los repintaba mientras el hardware ya estaba escaneando `s_top_page` línea a línea, haciendo desaparecer enemigos durante un frame.

## Solución
- Reordenado el bucle principal en `source/main.c` (`present_vblank_begin` y `present_hardware_bgs`):
  1. Se ejecuta la lógica del juego y se renderiza primero la **pantalla inferior** (doble búfer, inmune al barrido activo) más el HUD y `godrays_update`.
  2. Se espera al inicio exacto del VBlank (`swiWaitForVBlank()`).
  3. Nada más entrar en VBlank se intercambia el búfer inferior, se actualizan las ventanas de marea (`tide_render_window`) y OAM (`godrays_present`), y **se pinta inmediatamente `s_top_page`** antes de actualizar los fondos de tiles.

## Verificación
- **Compilación (`build-project.ps1`):** PASS, `0` warnings.
- **Tests de host:** `tests/test_upper_screen_contract.py` (`5/5` OK) y `tests/test_weapons_contract.py` (`58/58` OK).
- **Nintendo DS física:** subida a `/roms/nds/dungeonds.nds` (`1.363.968` bytes) y validada por el usuario; el parpadeo desaparece.
