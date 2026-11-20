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
