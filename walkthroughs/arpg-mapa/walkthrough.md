# ARPG: mapa fijo de la zona 1

Rama `feat/arpg-mapa-zona1` (desde `proto/arpg` b27d882b, con `proto/arpg` a87601d7 fusionado), 2026-11-22.

## Qué cambia para el jugador
- **Mapa fijo de 12 salas** (variante D «cuatro naves cortas»): 4 naves de 6 pantallas apiladas, galerías y capillas a los lados y la Cripta encima de la Nave 4. Cada sala tiene su nombre, nivel fijo y grupos tipo; Ojo y Cireneo de escalón 2 (x2 vida, x1,5 daño) en las naves 3 y 4. Diseño: `DESIGN-ARPG.md` §7 y `arpg-predemo/diseno_juego_final.md` §11. Comparativa de tamaño frente a Diablo y Castlevania: [`tamano_zona1.html`](tamano_zona1.html).
- **Espacio coherente:** fundido a negro al cruzar; por un hueco lateral se llega junto al hueco opuesto de la sala destino, a la misma altura; por la puerta del fondo, al pie de la nave siguiente.
- **La sala flota en el vacío:** muro del fondo hecho con el mismo arco gótico de los laterales, girado hacia la cámara, con el arco central abierto (interior en piedra y negro detrás) si hay salida arriba. Huecos laterales de dos módulos: se ve el canto del módulo norte y el módulo sur tapa al héroe. Muros a la mitad de grosor. La cámara no se bloquea.
- **Persistencia:** cofres, altares, jefes vencidos y salas vistas en el guardado (v5); al dormir vuelven grupos y jefes. Desde el campamento se entra por el último altar.
- **SELECT abre un mapa isométrico** superpuesto en la pantalla de arriba, sin pausar, con el escenario oscurecido detrás.

## Evidencia (ROM real)
- Las 12 salas recorridas, antes del muro del fondo: [`sheet_r1.png`](assets/sheet_r1.png), [`sheet_r2.png`](assets/sheet_r2.png).
- Módulo del muro lateral (arco ciego) y arco pasante: [`arco_vistas.png`](assets/arco_vistas.png), [`arco_pasante.png`](assets/arco_pasante.png).
- Muro del fondo, cruce por el arco y cruce lateral de ida y vuelta, con muros finos y hueco de dos módulos: [`muro_fondo.png`](assets/muro_fondo.png); extremos del hueco a 4x: [`hueco_extremos_4x.png`](assets/hueco_extremos_4x.png).
- Mapa con SELECT: [`mapa_overlay.png`](assets/mapa_overlay.png).
- Escenarios de capturas (`suite: false`): `scenarios/arpg_mapa_salas.json`, `arpg_mapa_muro_fondo.json`, `arpg_mapa_overlay.json`.

## Verificación
- `default`, `arpg-todo` y `perf` compilan con 0 avisos nuevos; los tres escenarios PASS.
- DS: el usuario jugó la versión `perf` con el mapa abierto y cerrado. Frames con más de un vblank: ~1 por ventana de 60, el mismo ritmo que las partidas anteriores del registro (coincide con la escritura del log en la tarjeta); un pico aislado al cargar sala.

## Pendiente
- Llave, rejas de capilla, premios por sala, dificultades (Pesadilla, Infierno), atajo, viaje entre altares y santuarios.
- No hay puerta hacia abajo (ni salida de la Cripta salvo pausa o muerte).
- Afinar experiencia de jefe y élite; la tapa del módulo sur del hueco aún tiene algún pico suelto.

## Documentos
`DESIGN-ARPG.md` §1 y §7, `TECHNICAL.md` §5.1, `STATUS-ARPG.md`, `STATUS-ARCHIVE.md`, `assets/MANIFEST.md`, `walkthroughs/README.md`.
