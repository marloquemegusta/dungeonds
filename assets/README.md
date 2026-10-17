# assets/ - Catálogo Canónico de Assets de DungeonDS

Estructura organizada según el pipeline 3D a 2D para Nintendo DS:

```
assets/
  ├── models/                 # Modelos 3D fuente (.fbx, .glb) limpios y categorizados
  │    ├── characters/        # Personajes (monster, charger, skeleton, necron, spacemarine, custom)
  │    ├── environment/       # Escenarios y props modulares (scifi_dungeon, dreadhollow)
  │    ├── weapons/           # Armas (shotgun_marine, sniper_necron, sword)
  │    └── animations/        # Clips esqueléticos FBX adicionales (combat, rifle)
  │
  ├── sprites/                # Spritesheets 2D procesados y listos para el motor NDS
  │    ├── characters/        # Carpetas de sprites exportadas desde el Shader Lab HTML
  │    └── dungeon/           # Suelos, props y fondos pre-renderizados
  │
  └── icon.png                # Icono oficial del banner de la ROM NDS
```

Todo el material histórico previo (antiguos bakes de baja resolución, runs temporales del shader lab y demos de combate anteriores) se conserva en `archive/`.
