# Contador de FPS en la pantalla superior

## Cambio

El HUD permanente de la pantalla superior sigue el estilo de TowerDS: fuente pixelada, verde brillante y panel oscuro. La segunda línea desglosa el trabajo de CPU como `F` (suelo), `S` (sombras), `B` (sprites/blits) y `L` (lógica), además de `C` (CPU completa) y `P` (presentación). Es telemetría solamente: no cambia controles ni gameplay.

La comparación del código explica una diferencia estructural que merece medirse: TowerDS dibuja el framebuffer inferior directamente en el buffer de VRAM que luego presenta mediante flip; esta rama construye ambas pantallas en RAM y copia 192 KB a VRAM cada frame. Además, la escena FBX compone los sprites por software. Esto sugiere fuentes de coste, pero no demuestra cuál causa la caída física.

## Verificación

La build BlocksDS, las pruebas host (incluido el contrato de los glifos/contadores) y el escenario FBX pasan. La captura DeSmuME muestra `FPS:60 C:10 P:06` y `F:06 S:00 B:01 L:00`. Es una comprobación visual/emulada, no una medición de DSi.

En la DSi, el usuario midió `FPS:20 C:40 P:10` y luego `F:38`, con `S/B/L:0`. El coste está en la copia del fondo: 256×192 píxeles por pantalla, fila a fila, para dos pantallas.

La capa BG1 tileada no es un sustituto visual seguro: su generador usa el mapa modular `g_floor_map/g_obj_map`, no el bitmap FBX. Además, el actual streaming de esa capa está marcado `unused`. Quitar la copia mostraría un fondo distinto. TowerDS sí presenta su framebuffer inferior directamente desde VRAM y lo cambia con flip, pero ese patrón no elimina el trabajo `F` de esta escena: el FBX sigue siendo un bitmap que hay que recortar a la cámara en cada pantalla.

Como ensayo para eliminar la sobrecarga de 384 arranques DMA por frame, sustituí esas copias por ráfagas ARM9 `LDMIA/STMIA` para filas alineadas y pares `LDRH` seguros cuando la cámara desplaza la fuente 2 bytes. Los límites siguen copiando exactamente 256 píxeles por fila, sin cambiar la lógica del juego.

La build BlocksDS, los tests host y el escenario FBX pasan; la posición inicial/final del jugador coincide con el build previo. La captura estática del escenario no muestra cambios del fondo. **Límite:** el escenario headless ejecuta DeSmuME en modo intérprete y con esta ruta mide 30 FPS frente a los 60 previos (`F:07` quieto, hasta `F:15` al caminar). No la considero una mejora confirmada hasta medirla en DSi; el intérprete emulado ejecuta estas ráfagas ARM de forma distinta.

![Captura del HUD con desglose de tiempos por etapa](assets/fps-hud-stage-breakdown.png)

Build de prueba pendiente de subir: CRC `4A0B2288`, SHA-256 `269BFC72206230499B6D3DCC77EE4784160B88C65E12DD66FE29EF55B9868F4E`.
