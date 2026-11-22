# Arranque para vídeos (lore y gameplay)

Guía para montar un PC nuevo que haga los vídeos del juego. Se trabaja con Claude Code, que lee `AGENTS.md` y las skills por su cuenta: basta con pedirle el vídeo.

## 1. Programas (una vez)

| Programa | Para qué | Instalación (PowerShell) |
| :--- | :--- | :--- |
| Git + Git LFS | bajar el repo y sus modelos 3D | `winget install Git.Git GitHub.GitLFS` |
| Python 3.12+ con Pillow y numpy | scripts de render y de vídeo | `winget install Python.Python.3.13` y luego `pip install pillow numpy` |
| Node.js LTS | lab rápido de render de personajes | `winget install OpenJS.NodeJS.LTS` |
| FFmpeg | montar los vídeos | `winget install Gyan.FFmpeg` |
| ElevenLabs CLI | voces | `npm install -g @elevenlabs/cli` y la variable de entorno `ELEVENLABS_API_KEY` con tu clave (nunca en el repo) |
| Docker Desktop | compilar la ROM (solo gameplay) | `winget install Docker.DockerDesktop` |
| WSL2 | emulador sin ventana para capturas (solo gameplay) | `wsl --install` y reiniciar |
| DeSmuME con ventana | grabar partidas jugadas a mano (opcional) | desmume.org |
| Claude Code | el agente | app de escritorio de Claude |

Blender no hace falta salvo para escenas de remate o props nuevos (`TECHNICAL.md` §3).

## 2. Repos (una vez)

Hacen falta dos repos de GitHub (pide acceso a los dos) y **en estas rutas exactas**, porque las reglas del proyecto las usan así:

```powershell
git lfs install
mkdir C:\codexlocal\skills
git clone https://github.com/marloquemegusta/dungeonds.git C:\codexlocal\dungeonds
git clone https://github.com/marloquemegusta/agentic-ds-dev.git C:\codexlocal\skills\agentic-ds-dev
```

Después, solo para gameplay, con Docker Desktop abierto:

```powershell
powershell -ExecutionPolicy Bypass -File C:\codexlocal\skills\agentic-ds-dev\scripts\setup.ps1
powershell -ExecutionPolicy Bypass -File C:\codexlocal\skills\agentic-ds-dev\scripts\check-toolchain.ps1 -ProjectPath C:\codexlocal\dungeonds
```

`check-toolchain` debe acabar sin errores. Prueba final: pedir a Claude «compila la ROM y saca una captura de la catedral».

## 3. Mantenerse al día (cada vez que empiezas)

```powershell
powershell -ExecutionPolicy Bypass -File C:\codexlocal\dungeonds\tools\sync.ps1
```

Actualiza los dos repos y baja los modelos nuevos. Si avisa de cambios sin guardar, díselo a Claude antes de seguir.

## 4. Cómo se trabaja

- **Una rama por vídeo o lote** (`video/<nombre>`), en su worktree (`AGENTS.md`, «Protocolo de Sesiones»). Claude la crea.
- **Al acabar, se sube la rama** (`git push -u origin video/<nombre>`) y se avisa para integrarla en `main`. No se trabaja directamente sobre `main`.
- **Vídeos de lore:** skill `codice-lore-video` (`.agents/skills/codice-lore-video/SKILL.md`), escritos contra `LORE.md`.
- **Gameplay:** skill `ds-game-dev` (el repo `agentic-ds-dev`): compila la ROM y saca capturas y GIF de escenarios guionizados (`scenarios/*.json`). Para partidas jugadas de verdad, grabar DeSmuME con ventana.
- **Cupo de LFS:** cada clon nuevo baja ~1 GB del cupo mensual de 10 GB de la cuenta. Clonar una vez y luego `sync.ps1`; no reclonar.
