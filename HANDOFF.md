# HANDOFF.md - Estado Canónico del Proyecto DungeonDS

**Fecha:** 2026-10-14  
**Propósito:** Proporcionar al siguiente agente LLM el estado completo, arquitectura y directrices operativas sin depender del historial de chat.

---

## 1. Estado Actual del Repositorio

- **Rama activa:** `main` (única rama local; todas las ramas de features han sido consolidadas y eliminadas).
- **Worktrees:** 0 worktrees adicionales (el directorio `.worktrees/` está limpio y eliminado).
- **ROM NDS:** `dungeonds.nds` (2.28 MB), compilada limpia con BlocksDS Docker sin advertencias ni errores.
- **Rendimiento:** **60 FPS Locked** garantizados en DeSmuME y Nintendo DS física (`FPS:60 C:12 P:04`).
  - CPU total: **12 ms** (presupuesto: $< 16.6$ ms / $< 33514$ ticks).
  - Suelo con sombreado dinámico: **8–9 ms**.
  - Presentación BG2: **4 ms**.
  - Margen VBlank: $> 4.6$ ms de holgura por fotograma.

---

## 2. Arquitectura del Motor y Features Implementadas

### A. Escena Sci-Fi Dungeon 3D (FBX 50.000 polys)
- Escena modelada en Blender, horneada a $768 \times 512$ px y dividida en $96 \times 64$ tiles de $8 \times 8$ px.
- Proyección dimétrica isométrica exacta a `ortho_scale = 38.0`.
- Despeje de puertas y dinteles mediante detección volumétrica de torso ($Z \in [0.3, 1.4]$ m), eliminando falsos bloqueos y permitiendo navegación continua por toda la mazmorra.
- Oclusión 3D exacta de arcos y pilares sobre el personaje mediante tramos RLE ordenados.

### B. Sistema de Visibilidad y Niebla de Guerra (Fog of War)
- Rejillas de bits en EWRAM de 768 bytes cada una (`g_fog_explored` y `g_fog_visible`).
- Raycaster Bresenham de 64 rayos sin división por software (< 0.05 ms de coste ARM9).
- Ocultación de entidades fuera de la línea de visión (enemigos inactivos y ocultos tras esquinas).

### C. Iluminación Dinámica de Antorcha 3D (No Binaria)
- **Horneado 3D BVH (`tools/bake_full_smooth_lightgrid.py`):** Rejilla de $21 \times 21$ celdas precalculadas a 4 bits para las 1.614 posiciones caminables (356 KB en ROM).
- **Falloff Hermite Smoothstep:** Atenuación $t^2 (3 - 2t)$ a lo largo de un radio de 80 píxeles ($\sim 5.3$ px por nivel de luz), eliminando cortes duros.
- **Paleta Perceptiva DTCM con Calidez Ámbar (`source/smooth_lightmap.c`):** Corrección gamma $(l/15)^{0.7}$, R 105%, G 95%, B 75%. El nivel 1 emite penumbra visible (`RGB15(2, 1, 1)`).
- **Interpolación Bilineal ARM9 sin FPU:** Bucle interior DDA sin divisiones que interpola colores de la paleta DTCM directamente sobre el búfer bitmap de 16bpp (`s_bot_screen_buf`).

---

## 3. Reglas Críticas de Desarrollo (AGENTS.md)

1. **Nintendo DS es plataforma sin FPU:** Prohibido usar `float` o `double` en código de runtime. Toda la física y movimiento se realiza en punto fijo (`int32_t` con precisión `8.8` o `12.12`).
2. **Sin comandos interactivos:** Todo el flujo se ejecuta mediante scripts PowerShell en `scripts/` (`build-project.ps1`, `run-scenario.ps1`).
3. **Protocolo de Worktrees:** Toda nueva feature se debe desarrollar en un worktree aislado (`git worktree add .worktrees/<nombre> -b feat/<nombre>`) y fusionarse a `main` al terminar.
4. **Evidencia Visual sin "Preview Unavailable" (Regla 6):** Prohibido usar rutas de workspace o esquema `file:///` para incrustar imágenes en markdown. Copiar siempre los archivos al directorio de artefactos (`<appDataDir>/brain/<conversation-id>/`) y referenciarlos con su ruta absoluta sin prefijo de protocolo.

---

## 4. Prioridad Inmediata y Siguientes Pasos

> [!IMPORTANT]
> **DIRECTIVA DEL USUARIO — PRIORIDAD INMEDIATA Nº 1: Continuar iterando el sistema de iluminación.**
> El usuario ha solicitado explícitamente seguir refinando el sombreado y la iluminación en la próxima sesión antes de pasar a otras áreas.

### Líneas de iteración sobre iluminación:
1. **Calibración Visual y Estética de la Antorcha:**
   - Ajuste fino del radio, curva de caída (falloff) y radio de penumbra según el feedback visual del usuario.
   - Parpadeo dinámico/flicker procedural de la antorcha (variación sutil del radio o modulación de los factores de escala de la paleta DTCM en tiempo real).
   - Calibración de color/contraste: ajuste de las componentes R, G, B y penumbra fría/cálida para optimizar la legibilidad en la pantalla física de la Nintendo DS.
2. **Iluminación en Entidades y Personaje:**
   - Aplicar el nivel de luz de la antorcha al sprite del jugador, enemigos y armas para que no se vean desconectados del entorno oscurecido.
3. **Fuentes de Luz Secundarias o Antorchas de Pared:**
   - Explorar antorchas fijas en muros o fuentes de luz estáticas combinadas con la antorcha móvil.

### Backlog secundario (después de cerrar la iluminación):
- **Enemigos y Combate:** Integración activa de IA (Charger, Skeleton) y proyectiles de hueso.
- **Audio y Efectos:** Driver Maxmod / ADPCM para ambiente de mazmorra.
- **Inventario / UI Táctil:** Menú en pantalla táctil para selección de armas.
- **Prueba en Consola Física:** Subida por FTP (`ftp://192.168.1.151:5000/roms/nds/dungeonds.nds`).
