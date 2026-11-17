# assets/

Catálogo de todos los assets (qué es cada cosa, de dónde sale y dónde se guarda): [`MANIFEST.md`](MANIFEST.md).
Política de entrada, adopción, retirada y limpieza: `AGENTS.md`, «Ciclo de vida de los assets».

```
assets/
  ├── inbox/        # entrada de descargas (zips de Tripo, packs); ignorado por git
  ├── models/       # originales 3D en Git LFS: characters/<p>/source/ (modelo), animations/<grupo>/ (clips sin malla), environment/, hud/
  ├── environment/  # catedral: losas del suelo, renders de props, lápidas, muros, paleta
  ├── sprites/      # paquetes del lab y sprites 2D que lee el generador de la ROM
  ├── arenas/       # arenas.json, fuente de la mazmorra
  ├── sfx/          # raw/ (ElevenLabs) y baked/ (16.384 Hz para la DS)
  ├── music/        # bucles de música
  ├── videos/       # vídeos finales de redes (Git LFS)
  └── icon.png      # icono del banner de la ROM
```
