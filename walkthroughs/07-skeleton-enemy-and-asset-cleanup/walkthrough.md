# Walkthrough: Integración del Enemigo Skeleton y Reorganización Canónica de Assets

**Hito / Sesión:** `07-skeleton-enemy-and-asset-cleanup`  
**Preset de vista:** `e30` (30° elevación, suelo dimétrico 2:1)  
**Estado:** Verificado en DeSmuME headless al 100% de éxito (`scenarios/character_switch_test.json`).

---

## 1. Resumen Ejecutivo

En esta sesión se abordaron dos objetivos primordiales para la calidad arquitectónica y de contenido del proyecto:

1. **Reorganización Estricta de Assets y Limpieza del Repositorio:**
   - La raíz del proyecto acumulaba capturas sueltas (`test_*.png`, `real_*.png`, `scratch_*.png`, `wall_*.png`), modelos duplicados (`Run.fbx`) y scripts de test sueltos.
   - Se trasladaron los renders de tests y comparativas previas a `assets/tests_and_previews/`.
   - Se movieron los scripts utilitarios sueltos a `tools/` y `tools/lab/`.
   - Se ubicó cada modelo 3D en su subcarpeta dedicada bajo `assets/characters/<nombre>/` (`monster`, `charger`, `skeleton`).

2. **Integración Completa del Enemigo Skeleton (`skeleton.fbx`):**
   - **Diagnóstico del FBX:** Modelo de esqueleto con animación de marcha bípeda en 47 fotogramas (`mixamo.com|Layer0`). Se detectó que el modelo poseía mallas sin materiales asignados (`sub01`, `sub02`) y una escala métrica en el armature de $0.01\times$ ($0.516\text{ m}$ de altura real evaluada).
   - **Pipeline de Horneado (`tools/bake_player.py`):** Se adaptó el pipeline con un material óseo gótico dedicado (`BoneGothic`, color hueso marfil con rugosidad difusa), escalado anatómico al estándar de los demás personajes ($1.39\text{ m}$ con zancada visible), fijación de root motion en caderas y renderizado Cycles en 8 direcciones y 8 fotogramas.
   - **Contrato de Máscaras de Sombra (`tools/shadow_masks.py`):** El esqueleto, por su delgadez ósea, producía una sombra Cycles de menor huella superficial que no alcanzaba el umbral de percentil 0.5% anterior. Se ajustó el muestreo a percentil 0.1% (`dark_idx`), satisfaciendo el contrato estricto de contraste y permitiendo generar máscaras de 4 bits perfectamente recortadas para NDS.
   - **Generador C (`tools/convert_iso_to_c.py`):** Se expandió el soporte a 3 personajes (`CHAR_HERO`, `CHAR_CHARGER`, `CHAR_SKELETON`), exportando `g_skeleton_frames`, `g_skeleton_shadow_masks` y `g_skeleton_shadow_bounds`.
   - **Validación en NDS:** Compilación limpia con Docker BlocksDS y ejecución headless en DeSmuME (`character_switch_test.json`), demostrando la transición cíclica completa entre el Héroe, el Cargador y el Esqueleto con control por cruceta y renderizado dual-screen impecable.

---

## 2. Evidencia de Ejecución en Nintendo DS

### 2.1. Ciclo de Conmutación en Juego (Héroe -> Cargador -> Esqueleto)

El escenario `character_switch_test.json` recorre de forma interactiva los tres personajes en la Nintendo DS:

![Ciclo de conmutación de personajes en Nintendo DS](assets/character_switch_cycle.gif)

*Figura 2.1: Conmutación en tiempo real en la consola Nintendo DS ejecutándose en DeSmuME.*

### 2.2. Detalle a 4x del Esqueleto en la Cripta

![Detalle a 4x del esqueleto en la consola](assets/skeleton_real_closeup_4x.png)
*Figura 2.2: Sprite renderizado a resolución nativa NDS escalado a 4x. Obsérvese la legibilidad de la caja torácica, cráneo y piernas sobre el suelo oscuro junto a su sombra de contacto calculada en Cycles.*

Comparativa de escala con los otros dos personajes:
- **Héroe (Monster)**:  
  ![Hero Closeup](assets/hero_real_closeup_4x.png)
- **Cargador (Charger)**:  
  ![Charger Closeup](assets/charger_real_closeup_4x.png)

### 2.3. Spritesheet Horneado y Sombra 3D

- **Spritesheet 8x8 (8 direcciones x 8 frames):**  
  ![Skeleton Spritesheet e30](assets/skeleton_e30.png)
- **Máscara de sombra Cycles proyectada:**  
  ![Skeleton Shadow e30](assets/skeleton_e30_shadow.png)

---

## 3. Estructura Limpia de Directorios

Tras la reorganización canónica, la jerarquía de assets queda perfectamente clasificada:

```
dungeonds/
├── assets/
│   ├── characters/
│   │   ├── charger/         # Run.fbx, texturas PBR, spritesheets e30/e60
│   │   ├── monster/         # Walking.fbx, spritesheets e30/e60
│   │   └── skeleton/        # skeleton.fbx, spritesheet e30 y sombras
│   ├── dungeon_e30/         # Sprites de escenario a 30°
│   ├── dungeon_e60/         # Sprites de escenario a 60°
│   ├── dungeon_tiles/       # Tiles base de suelo y muros
│   ├── tests_and_previews/  # Capturas históricas, gifs comparativos y tests
│   └── docs_references/     # Documentos y diagramas de referencia
├── include/                 # Cabeceras C (dungeon_data.h, player_sprite.h)
├── source/                  # Código fuente C Nintendo DS
├── tools/                   # Herramientas de horneado y conversión
│   └── lab/                 # Laboratorios interactivos HTML
└── walkthroughs/            # Registros auditables de cada sesión
```

---

## 4. Verificación de Tests y Toolchain

- **Tests unitarios de sombras (`tests/test_shadow_masks.py`):** `PASS` (2/2 pruebas superadas).
- **Compilación BlocksDS Docker (`scripts/build-project.ps1`):** `PASS` (ROM `dungeonds.nds` generada limpiamente sin warnings de memoria).
- **Escenario DeSmuME (`scenarios/character_switch_test.json`):** `PASS` (7 capturas, 25 eventos, screen change verificado).
