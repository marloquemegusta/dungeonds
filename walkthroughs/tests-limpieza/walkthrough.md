# Limpieza de tests y reglas de verificación (2026-11-14, `docs/tests-limpieza`)

## Problema
- Se gastaba mucho tiempo en tests: ~25 archivos de «contratos de texto» (buscaban nombres y cifras en `source/*.c`), uno de 55 s que recompilaba en bucle, 18 tests sin declarar y la batería en rojo en `main` sin que nadie lo notara.
- 57 escenarios en la batería: 6 sin aserciones, ~20 que solo comprobaban «la pantalla cambió» y 4 de rendimiento en emulador (~25 % del tiempo).
- Las reglas empujaban a ello: «cada efecto lleva su test de contrato», cierre con todo en cada versión y `rebuild_all` pasando tests siempre.

## Cambios
- `AGENTS.md` regla 4 (cierre) y nueva 4b (qué tests se escriben): escenarios de la feature siempre; tests de host solo si el cambio toca su área; batería completa solo en hitos de versión; prohibidos los contratos de texto.
- 22 tests borrados; normas globales (sin `float`, paletas de efectos desaturadas, golpes para matar) en `tests/test_guardrails.py`.
- Quedan 16 tests, todos declarados en `hostTests` y en verde (~30-45 s según carga). `test_sniper_hit_volume` compila una vez (55 s → 2-12 s). Expectativa obsoleta de `test_cathedral_kit` corregida (el santo está en el kit a propósito).
- 21 escenarios con `"suite": false` (variantes A/B/C, capturas, rendimiento; los 6 sin aserciones además `evidence_only`). Ninguno borrado.
- `tools/rebuild_all.py`: los tests solo con `--tests`.

## Pendiente
- Dos blancos puros en efectos quedan como excepción en `test_guardrails.py`: tabla antigua `s_fx_rgb` de `weapons.c` y cruz de la granada.
