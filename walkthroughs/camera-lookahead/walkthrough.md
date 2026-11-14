# Cámara con adelanto vertical (*look-ahead*)

**Rama:** `feat/camera-lookahead` (integrada en `main`)
**Fecha:** 2026-11-14

## Qué se hizo

Se sustituyó el encuadre vertical centrado fijo (`50 %` en la pantalla inferior) por una cámara con adelanto vertical (*look-ahead*) en `source/main.c`:

- **Al avanzar hacia arriba:** coloca al jugador en el tercio inferior (`CAM_ANCHOR_UP = 132`, ~69 % de altura), dando ~132 px de visión frontal en la pantalla táctil.
- **Al retroceder hacia abajo:** desliza la vista hacia atrás (`CAM_ANCHOR_DOWN = 64`, ~33 % de altura), dando ~128 px por detrás para ver la marea y recular con comodidad.
- **Al parar o hacer *strafe* lateral:** congela el encuadre actual sin volver al centro para no mover el suelo bajo el stylus.
- **Histéresis y *kiting*:** requiere `CAM_LOOK_DELAY_FRAMES = 22` (~0,37 s) de marcha vertical sostenida antes de deslizarse a `CAM_LOOK_STEP_PX = 2` px/frame, y si el jugador camina hacia atrás mientras apunta hacia delante con el stylus (*kiting*), mantiene la vista al frente.

## Verificación

- **Compilación ROM (`default`):** `DS_BUILD=PASS` (`warnings=0`, `new_warnings=0`, `dungeonds.nds` 1.441.792 bytes).
- **Tests de contrato host (`test_upper_screen_contract.py`, `test_gameplay_contract.py`):** `14/14` OK.
- **Nintendo DS física:** subida por FTP (`/roms/nds/dungeonds.nds`) y validada por el usuario en consola real tras dos iteraciones de tuning.
