# Sesión de diseño: layout de la catedral

**Fecha:** 2026-11-09
**Alcance:** cerrar la composición espacial de la catedral para la 0.3.2. Diseño, sin código ni assets de juego.
**Base aceptada para continuar:** [`DESIGN.md` §6.9.1b](../../DESIGN.md). La apariencia final se validará en ROM al integrar el kit.

## Objetivo

Que el avance se lea como una procesión por una catedral que no termina: una nave central continua, flanqueada por respiros laterales, con el combate alterado por barricadas y el ritmo puntuado por cruceros abiertos y capillas opcionales.

Los patrones son **familias con variaciones**, no franjas idénticas que se repiten en un ciclo. Los planos de abajo son esquemas de diseño, no capturas ni evidencia de una ROM.

## Medidas y recorridos

- Pantalla/carril: 512 px de ancho; muros laterales de 48 px; interior jugable de 416 px.
- Tramo lógico: 192 px de alto, una pantalla. Las bandas de 128 px siguen siendo una división técnica del motor, no una junta visible en el escenario.
- Mantener tres corredores longitudinales libres, continuos de arriba abajo y de al menos 48 px: uno central y dos laterales. El objetivo del central es 64 px.
- Referencia inicial para revisar planos: corredor izquierdo `x=80–128`, central `x=224–288`, derecho `x=384–432`. Son zonas guía; los tres corredores pueden desplazarse dentro del suelo útil siempre que sigan conectados y respeten los anchos mínimos.
- Bancos en bloques cortos de 2–3 filas, sin superar el 15 % de huella de colisión del suelo útil. En las naves barricadas se escalonan a ambos lados del eje central.

### Esquema transversal

```text
x:     0      48  80  128       224  288       384  432  464     512
        muro    L    margen      CENTRAL       margen   R    muro
        48 px  48 px   96 px       64 px        96 px 48 px 48 px
```

Los márgenes alojan variación de losas, suciedad, velas y elementos de atrezo. Los bancos nunca cierran los corredores. La composición puede cambiar la decoración y el lado de las barricadas sin mover la ruta central fuera de su lectura dominante.

## Tres familias de composición

### Nave despejada

- Es el tramo de descanso y lectura del suelo: damero tranquilo, alguna lápida Vía A o cirio junto al margen.
- No necesita una fila de props en cada pantalla. Deja zonas amplias de suelo vacío y contraste bajo.
- Columnas y elementos altos se reservan para bordes o encuentros arquitectónicos; no aparecen como obstáculos sorpresa en los corredores.

```text
avance ↑
┌────────────────────────────────────────────────────────────┐
│ muro   lápida A                         cirio       muro   │
│        ··········· corredor L ·····················       │
│                         NAVE                               │
│        ··········· corredor central ···············       │
│                              losas                         │
│        ··········· corredor R ·····················       │
└────────────────────────────────────────────────────────────┘
```

### Nave barricada

- Bancos y sacos forman bloques breves de 2–3 filas, desplazados hacia los intersticios entre corredores.
- Una aparición puede cargar el lado izquierdo y la siguiente el derecho; no se duplica la misma silueta ni la misma posición en tramos consecutivos.
- El centro sigue siendo la ruta más legible. Los laterales siguen abiertos de principio a fin, aunque la cobertura haga que el espacio parezca más apretado.

```text
avance ↑
┌────────────────────────────────────────────────────────────┐
│ muro   [banco][banco]                   saco        muro   │
│        ····· corredor L ·····         ··· corredor R ···  │
│                     ··· corredor central ···               │
│        saco                    [banco][banco]               │
│        ····· corredor L ·····         ··· corredor R ···  │
└────────────────────────────────────────────────────────────┘
```

Las piezas del esquema son indicativas; el baker/compositor futuro deberá validar con sus huellas reales los tres corredores y el límite del 15 %.

### Crucero abierto

- Hito poco frecuente que ensancha la lectura del espacio y deja que se crucen visualmente las naves.
- El área central queda libre para esquivar y combatir. Columnas, altar bajo o velas pueden enmarcar el espacio desde los márgenes.
- La lápida Vía B puede aparecer como foco ocasional; no se convierte en una marca obligatoria de cada crucero.
- Un arco o cambio de pavimento puede anunciar la transición, sin convertirla en una barrera que cierre la ruta.

```text
avance ↑
┌────────────────────────────────────────────────────────────┐
│ muro    columna       arco / apertura       columna  muro  │
│        ····· corredor L ···························       │
│             espacio abierto de combate                      │
│        ········· corredor central ···············         │
│                 lápida B (ocasional)                         │
│        ····· corredor R ·························       │
└────────────────────────────────────────────────────────────┘
```

## Capilla lateral opcional

La capilla es una pequeña bahía accesible desde un lado de la nave, con fondo ciego y retorno por el mismo acceso. No corta ni sustituye la ruta vertical principal, y no aparece en el mismo tramo que un crucero. En esta fase se decide su forma y conexión espacial; cofre/élite y recompensa pertenecen a versiones posteriores.

```text
avance ↑
┌────────────────────────────────────────────────────────────┐
│ muro       ┌──────── capilla opcional ────────┐      muro  │
│ corredor L └─ acceso ≥48 px ──┐ altar/relicario│            │
│ ·····························┘                │            │
│           ····· corredor central ·············             │
│           ····· corredor R ···················             │
└────────────────────────────────────────────────────────────┘
```

Alternar el lado de la capilla en la próxima aparición. El interior puede estrecharse, pero la entrada debe ser clara y el combate principal no debe empujar al jugador dentro de ella.

## Ejemplo de recorrido: primeras 12 pantallas

Es una muestra de ritmo, no una secuencia fija para todas las runs. Las dos barricadas usan lados y siluetas distintas; los cruceros llegan con seis pantallas de separación; la capilla queda entre ellos y no coincide con ninguno.

| Pantalla | Composición | Variación visible |
|---:|---|---|
| 1 | Nave despejada | Presenta el eje central y el suelo de rombos. |
| 2 | Nave despejada | Lápida Vía A junto a un margen; el resto del suelo respira. |
| 3 | Nave barricada | Bloques cortos cargan el lado izquierdo. |
| 4 | Nave despejada | Se abre el espacio; cambian velas y suciedad. |
| 5 | Nave barricada | Barricada desplazada al lado derecho, sin copiar la planta 3. |
| 6 | Crucero | Primera apertura amplia, con foco lateral discreto. |
| 7 | Nave despejada | Retoma el eje después del hito. |
| 8 | Nave con capilla derecha | Desvío opcional de fondo ciego; tres corredores principales intactos. |
| 9 | Nave barricada | Nueva distribución, ligera asimetría y bancos rotos. |
| 10 | Nave de transición | Arco anuncia el próximo espacio abierto. |
| 11 | Nave despejada | Deja respirar el combate antes del hito. |
| 12 | Crucero | Segundo crucero; cambia el foco y puede usar Vía B. |

## Composición concreta: pantallas 1–8

Este ejemplo traduce la gramática a posiciones verificables, en píxeles de pantalla. Origen `(0,0)` en la esquina inferior izquierda; `x` va a la derecha y `y` hacia arriba, en sentido de ascenso. Las cajas usan intervalos `[inicio, fin)`. Todas las coordenadas caen en la rejilla de 8 px. Los bancos son cajas conservadoras de 64×24 px; losas y lápidas son suelo decorativo sin colisión.

| Pantalla | Colocación exacta | Lectura del tramo |
|---:|---|---|
| 1 | Lápida Vía A de 80×40 en `(136,72)`; cirio de 16×32 en `(440,24)`. | Nave despejada; la lápida queda entre el corredor izquierdo y el central. |
| 2 | Bancos de 64×24 en `(144,48)`, `(144,72)`, `(304,112)` y `(304,136)`. | Barricada en dos grupos, uno a cada lado del eje y en distintas alturas. |
| 3 | Lápida Vía A de 80×40 en `(296,88)`; cirio de 16×32 en `(56,32)`. | Vuelve a abrirse la nave; cambia el lado de los acentos respecto a la pantalla 1. |
| 4 | Bancos de 64×24 en `(304,48)`, `(304,72)`, `(144,112)` y `(144,136)`. | Barricada con el orden de lados invertido respecto a la pantalla 2. |
| 5 | Sin cobertura baja; se reserva el borde superior para el arco transversal. | Transición abierta que anticipa el crucero; el arco se define como pieza en la sesión 2. |
| 6 | Lápida Vía B de 96×48 en `(208,72)`; columnas de 24×64 en `(56,56)` y `(440,56)`. | Crucero despejado. Vía B es decorativa y puede cruzarse; las columnas quedan en los márgenes. |
| 7 | Lápida Vía A de 80×40 en `(136,112)`; sin bancos. | Nave de respiro después del crucero. |
| 8 | Bahía de capilla en `x=304–384`, `y=48–144`; abertura de 48 px hacia el corredor derecho en `y=72–120`; relicario de 32×32 en `(328,80)` y cirio de 16×32 en `(352,56)`. | Desvío opcional de fondo ciego. El corredor derecho sigue de `x=384` a `432` durante toda la pantalla. |

### Comprobación geométrica del ejemplo

- Los corredores libres de referencia siguen siendo `x=80–128`, `x=224–288` y `x=384–432` en las ocho pantallas. Las barricadas solo ocupan `x=144–208` o `x=304–368`, así que dejan 16 px de separación respecto a cada corredor adyacente.
- En las pantallas 2 y 4, las cajas visuales conservadoras de los cuatro bancos suman `4 × 64 × 24 = 6.144 px²`. El suelo útil mide `416 × 192 = 79.872 px²`; las cajas ocupan **7,7 %**, por debajo del límite de 15 % incluso antes de contar que la colisión real del banco es más fina que su imagen.
- En la pantalla 8, la capilla toca el corredor derecho por su borde y abre 48 px de ancho hacia él; no atraviesa el corredor central ni corta la ruta vertical.
- El crucero tiene una lápida de suelo sin colisión en el centro y columnas en los márgenes. No se está contando una decoración como obstáculo.

Esto demuestra la geometría de la propuesta en planta; **no demuestra todavía cómo se ve en la ROM**. La validación visual llegará cuando estas composiciones se integren en el kit, y la validación de tránsito usará escenarios con el actor cruzando las huellas reales.

## Reglas para el generador futuro

1. Construir cada tramo lógico a 192 px; mantener la retícula de colocación de 8 px y las piezas/terreno ya definidos en `DESIGN.md`.
2. Elegir variaciones de familia con semilla, pero evitar dos distribuciones de obstáculos idénticas consecutivas. No imponer un ciclo de tres tipos.
3. Usar el crucero cada 4–6 pantallas y una capilla opcional cada 8–12; las capillas no coinciden con cruceros.
4. Mantener los tres corredores ≥48 px a lo largo de cada tramo y sus uniones. Objetivo de 64 px para el corredor central.
5. Validar que la huella de colisión de los bancos no supera el 15 % del suelo útil; la cobertura baja bloquea movimiento, no disparos.
6. Ubicar velas, lápidas y atrezo sin invadir la huella libre de los corredores. Vía A es el acento común de nave; Vía B queda para focos ocasionales.
7. Toda futura prueba de colisión debe recorrer realmente una huella de banco o entrar en la capilla; una prueba de oclusión debe cruzar una pieza alta. Los esquemas de esta sesión no sustituyen escenarios geométricos.

## Criterio de cierre de esta sesión

- Preferencias base acordadas: nave central continua, laterales como respiros, cruceros espaciados y capillas recorribles.
- Se presenta la propuesta de tramo lógico, reglas para las tres familias y un recorrido de ejemplo.
- Las posiciones de las pantallas 1–8 pasan las cuentas geométricas descritas arriba.
- El usuario dio paso a la sesión 2 con esta composición como base. La apariencia en ROM se valida después de integrar el kit, y los cruces/colisiones se validan con escenarios geométricos.
- No se implementa aún el generador ni se crean piezas: eso corresponde a las siguientes sesiones de arte y motor.
