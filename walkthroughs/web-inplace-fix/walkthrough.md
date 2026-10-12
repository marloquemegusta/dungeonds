# Corrección de animación in-place del visor web

## Cambio

- La ampliación del detector a RootNodeL se basó en los nombres presentes en el FBX, sin confirmar una pista de traslación en ese nodo. El análisis posterior con el lector real no encontró esa pista: en Walking.fbx el movimiento está en Hips. En Mario, el fallo real era confundir los ejes locales de la armadura con los de la escena; corregido en [la sesión 31](../web-inplace-axis-fix/walkthrough.md).
- El visor ahora reconoce los nombres de raíz RootNode y RootNodeL, y bloquea X/Z en pistas vectoriales o escalares.
- Y se conserva como eje vertical y la casilla desactivada restaura las pistas originales.
- El estado indica cuántas pistas de raíz se han fijado; si muestra «No se detectó pista de raíz», ese FBX usa una jerarquía/nombre distinto.

## Verificación

- Node comprueba la sintaxis del script completo embebido.
- Prueba sintética PASS para RootNodeL y Hips, bloqueo de X/Z, conservación de Y y restauración al desactivar.
- La prueba visual del FBX desde file:// sigue pendiente porque el navegador del entorno bloquea la automatización de esa URL. No se afirma que el ciclo real ya esté validado.
