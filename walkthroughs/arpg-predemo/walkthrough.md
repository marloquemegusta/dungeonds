# Pre-demo ARPG (rama `proto/arpg`, 2026-11-19)

Prueba de concepto: convertir la partida por encuentros en un Action RPG pequeño. Diseño en `DESIGN.md` §7, plan y cifras en [`plan.md`](plan.md). Implementado por fases con subagentes Haiku (petición del usuario); el coordinador compiló, revisó y probó cada fase en el emulador.

## Qué hay
- **Campamento** (pantalla de menú): Dormir, Árbol, Entrar en la Catedral, Códice. Muestra nivel, experiencia, puntos y piso más hondo. El título ofrece Continuar / Nueva partida.
- **Vida y maná en puntos** con dos orbes en la pantalla inferior. Cada enemigo quita su propio daño.
- **Rayo** con coste de maná (15) y daño base 100.
- **`L` corto**: remate si hay un enemigo tambaleante; si no, puñetazo (50 de daño, deja tambaleante). El remate suelta orbes de vida (60 %) y maná (75 %).
- **`L` mantenido**: cambia entre Rayo y Maldición (si está aprendida).
- **Maldición**: se lanza al punto del lápiz y deja una zona violeta que quema durante 4 s (6 s con Miasma).
- **Resurrección**: los enemigos que mueren en la zona se levantan como Exvotos aliados con una marca encima; con Ofrenda explotan al caer.
- **Experiencia en runas** que se recogen al pasar; los jefes sueltan seis. No se pierde nunca; solo sube de nivel al dormir (curva ×1,45 por nivel).
- **Árbol** de 13 nodos (Maldición + Metralleta, Quemadura, Veneno, Resurrección), reutilizando las Reliquias y Dones existentes.
- **Mazmorra infinita sala tras sala** (100 pisos): sin pasillos ni relicarios ni Altar; jefe cada 5 (Abanderado; élite con más vida y monaguillos; élite con escolta de 2 Ojos y 2 Cireneos). La vida enemiga sube un 12 % por piso.
- **Guardado** en la tarjeta (`dungeonds_arpg.sav`).
- **Variante de pruebas `arpg-todo`**: nivel 10 y todo el árbol aprendido, con su propio archivo de guardado.

## Evidencia (emulador)
- Bucle título → campamento → mazmorra: `assets/bucle.png`.
- Árbol: `assets/arbol.png`.
- Maldición (variante `arpg-todo`): `assets/maldicion.png`.
- Combate sin invulnerabilidad (la sala te mata y vuelves al campamento): `assets/combate_muerte.png`.
- Puñetazo y remate en modo invulnerable: experiencia 0 → 32 en 8 Exvotos, el maná se recupera con el remate: `assets/combate_remate.png`.
- HUD legible con recuadros oscuros, cambio a Maldición en pleno combate, pantalla de muerte y campamento: `assets/hud_muerte_campamento.png`.
- Placeholders: `assets/placeholders_4x.png`.

Escenarios de captura (sin aserciones, `"suite": false`): `scenarios/arpg_bucle.json`, `arpg_arbol.json`, `arpg_maldicion.json`, `arpg_combate.json`, `arpg_muerte.json` (los de Maldición y muerte con la ROM `arpg-todo`).

## No verificado
- **Nada probado en la DS**: ni rendimiento (24 objetos en el suelo, aliados, zonas), ni guardado en una tarjeta real.
- Aliados, jefes élite y pisos profundos no se han visto en el emulador.
- Sin pasada de tests de host ni batería de escenarios (es un prototipo; los escenarios antiguos de encuentros pueden fallar porque cambian la vida del héroe, los relicarios y la estructura).

## Pendiente
- **Fallo visual conocido:** los orbes del último fotograma siguen viéndose en las esquinas del campamento (se intentó borrar la página al volver; no bastó).
- La reja trasera de la sala no se dibuja mientras está en la franja del HUD (para que no lo tape).
- Lista de assets para pre-renderizar: [`assets_pendientes.md`](assets_pendientes.md).
- Equilibrio: la vida enemiga a piso 100 es enorme (Abanderado ~640.000); el nivel no sube el daño, solo vida y maná.
- Documentos: si el usuario aprueba el rumbo, `DESIGN.md` §7 pasa a ser el diseño vigente y lo de §6 que deja de aplicar va a `DESIGN-ARCHIVE.md`; `STATUS.md`, `TECHNICAL.md` y `assets/MANIFEST.md` se actualizan al cerrar.

## Segunda sesión (2026-11-20): hacia la protodemo

Diseño cerrado en [`propuestas_protodemo.html`](propuestas_protodemo.html) (v3) y apuntado en [`diseno_juego_final.md`](diseno_juego_final.md) §10. Implementado con agentes DeepSeek v4.1 flash en paralelo, un carril por copia de trabajo, y unido por el coordinador.

### Qué hay nuevo en la ROM
- **HUD:** cáliz de vida, ampolla de maná, cadena de experiencia, viril del hechizo activo y números de daño flotantes.
- **Combo de puñetazos** (`L` corto): directo → cruzado → gancho (daño 50 · 50 · 90, el gancho empuja); si hay un tambaleante al alcance, `L` remata. GIF: `assets/combo_punetazos.gif`.
- **Tambaleo solo por vida baja** (≤ 25 %).
- **Glifo** en lugar de Maldición: 30 de maná, 0,5 s de espera y ralentiza un 40 % durante 4 s.
- **Salas:** naves sin rejas; puerta del usuario arriba y hueco negro en un lateral, los dos con fundido a la sala siguiente; cofres que se abren y sueltan botín; altares que quedan tocados.
- **Población por grupos** de 4 a 12 con curva de inicio: salas 1-2 solo Bebés y Exvotos, como mucho un Ojo o Cireneo en 1 de cada 3 salas desde la 3, Párroco y Monja desde la 6, mezcla completa desde la 8.
- **Tiers de Exvoto:** Bebé (enjambre), Párroco (tanque que empuja) y Monja (reza y cura a los cercanos). GIF: `assets/exvotos_tiers.gif`.
- **Campamento andable** (claustro): jergón = dormir, arcón = árbol, atril = Códice, mesa sin acción, puerta = entrar a la catedral; props con sombra y hoguera con brasas.

Evidencia (emulador): `assets/protodemo_v1_rom.png`, `assets/campamento_*.png`, `assets/salas_*.png`, `assets/tiers_*.png`, `assets/props_contacto.png`. Build sin avisos; escenarios `campamento_captura` y `tiers_combate` PASS. Subida a la DS el 2026-11-20 (sin medir rendimiento).

### No verificado o pendiente
- 60 FPS en la DS con ~24 enemigos y el guardado en tarjeta real.
- `salas_captura` se atasca tras la primera sala (columnas y enemigos en el camino; la semilla depende del tiempo).
- Suelo del campamento demasiado azul y con dibujo de manchas; cabeza del Párroco girada; la puerta destaca por clara (se puede oscurecer con `tone` en `tools/props/props.json`).
- Puerta y hueco llevan a la misma sala de arriba: faltan las salas laterales de verdad (castillo), las reliquias, la bolsa, el desguace, los santuarios (estatuas) y el viaje entre altares.
- Documentos revisados en esta entrega: `assets/MANIFEST.md`, `TECHNICAL.md`, `STATUS.md`, `diseno_juego_final.md` y este walkthrough; `DESIGN.md` §7 sigue remitiendo al documento de trabajo.

## Tercera sesión (2026-11-21): menús, inventario de reliquias y menú radial

- **Campamento y pausa:** eliminado el menú viejo (MENU_CAMP); salir del inventario o del Códice devuelve directo al campamento andable. Pausa en campamento sin «Volver al campamento»; Controles actualizado al flujo ARPG.
- **Menú radial (source/radial.c):** mantener L despliega los hechizos alternativos en anillo (sin caja negra) alrededor del viril activo; con 1 solo hechizo equipado no abre. Soporta hasta 3 hechizos equipados (activo + 2).
- **Inventario de reliquias y tomos (source/arpg_inv.c, source/inventory.c):** sustituye al árbol de habilidades (MENU_TREE eliminado). Pantalla superior con escuela/hechizo, engarces grandes (3 en Rayo/Ejecución, 2 en Pecho) y comparación ▲/▼; pantalla inferior con 5 pestañas, bolsa 6×3 (16 huecos), ficha y desguace por cera. Las reliquias equipadas aplican sus modificadores del roguelike. Glifo y Levantar quedan como «Sin definir». Guardado v2.
- **Pendientes anotados en DESIGN.md:** re-escalar props del campamento (jergón +50 %, mesa 2–3×, arcón 2×), drag & drop táctil en el inventario (comparar al mantener sobre hueco ocupado e intercambiar al soltar), y ajuste vertical de la pausa de mazmorra.
 (emulador, rpg-todo, escenario rpg_menus): ssets/menus/m03_inventario.png, m04_glifo_sin_definir.png, m05_pecho_dos_engarces.png, m07_engarzada.png, m08_confirmar_desguace.png, m09_desguazada.png, m12_pausa.png, m13_inventario_pausa.png, m09_radial_abierto.png, m10_tras_elegir.png.
