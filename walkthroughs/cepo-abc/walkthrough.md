# Cepo legible (cepo-abc)

Rama `feat/cepo-abc`, base `arpg`, 2026-11-26.

## Problema

El cepo de las salas 4, 5 y 12 salía naranja y plano. El giro "de frente" de `props.json` nunca se aplicó (el lab rápido ignora `yaw`) y de frente no se leen los agujeros.

![antes](assets/antes.png)

## Ronda 1: giro 3/4 y tamaño

`yaw_extra` -45 (vista 3/4) y `target_width` 40. Variantes A/B/C:

![A](assets/var_A.png) ![B](assets/var_B.png) ![C](assets/var_C.png)

![yaws del modelo](assets/cepo_modelo_yaws.png)
![tira](assets/cepo_tira.png)
![contexto C](assets/cepo_contexto_C.png)

## Ronda 2: madera oscura por material

Nueva opción `material_grade` en `prerender_props.py`: madera, metal y sangre se clasifican sobre el render de alta resolución y cada uno recibe su ajuste.

![r2 A](assets/r2_A.png) ![r2 B](assets/r2_B.png) ![r2 C](assets/r2_C.png)
![r2 tira](assets/r2_tira.png)

**Elegida: B media** (`material_grade` wood 0.6, metal 1.3, blood 0.75, metal_desat 0.6).

![después](assets/despues.png)
![sala 12](assets/r2_B_sala12.png)

Página de la ronda: [`cepo_abc.html`](cepo_abc.html).

## Verificación

- Build `-Clean` PASS, sin avisos nuevos.
- Capturas de la ROM en las salas 4 y 12 (escenario `scenarios/cepo_abc.json`, `suite: false`, solo evidencia).
- Cepo: 23 tiles únicos (antes 16). `galerias` 743/1024 y `prisionero` 658/1024 tiles.
- No medido en la DS: prop fijo de decorado.

## Nota técnica

- Re-hornear un prop de sala: `arpg_light_props.py <grupo> --kit --only cepo`, luego sin `--kit`, `arpg_light_pack.py <grupo>` completo y build `-Clean`. Si no, la ROM descarta el `.rmk` o `nitrofiles` queda desfasado.
- El `yaw` de `props.json` no lo aplica el lab rápido; hace falta `yaw_extra` (anotado en `TECHNICAL.md` §3).

## MDs

`DESIGN-ARPG.md`, `TECHNICAL.md`, `STATUS-ARPG.md`, `STATUS-ARCHIVE.md` actualizados.
