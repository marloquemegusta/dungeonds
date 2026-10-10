# Contador de FPS en la pantalla superior

## Cambio

Añadí una etiqueta permanente `FPS:NN` en la esquina superior izquierda. Sigue el estilo del HUD de TowerDS: fuente pixelada, verde brillante y panel oscuro para conservar el contraste. El valor reutiliza `g_perf.fps`; no afecta a los controles ni al gameplay.

## Verificación

La build BlocksDS y las pruebas host pasan. El escenario FBX capturó el estado en reposo y tras caminar. La captura registra `FPS:60 C:09 P:07` en DeSmuME. `C` es lógica+render en ms; `P` es espera de VBlank+copia a pantalla en ms.

El usuario reporta que la DSi física muestra 20 FPS en reposo y al moverse. El resultado emulado no representa el rendimiento físico; la causa de esa diferencia sigue investigándose.

![Captura de la pantalla superior con el contador FPS](assets/fps-hud-top-screen.png)

ROM compilada con CRC `392122B6`. La prueba fue en DeSmuME; la lectura física de la consola queda pendiente.
