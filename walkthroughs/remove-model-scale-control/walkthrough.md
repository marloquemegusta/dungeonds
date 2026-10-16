# Eliminar el slider «Escala modelo» del lab 3JS

## Cambio

Se quitó el control de escala del modelo de la interfaz. El cargador conserva la normalización automática a una altura de referencia; el tamaño del sprite sigue siendo el control para la resolución y el encuadre se ajusta automáticamente. Se eliminaron las referencias del control en el HTML y en el código de carga; permanece «Escala del rig», un campo numérico distinto.

## Verificación

- HTML standalone reconstruido con `python tools/lab/build_offline_renderer.py`.
- Chromium headless cargó la página y confirmó que no aparecen el slider ni sus referencias de UI; el control «Tamaño del sprite» sigue presente.
- Captura headless: `assets/lab-without-model-scale.png`.
