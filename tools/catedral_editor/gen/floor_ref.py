import sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(r"C:/codexlocal/dungeonds/.worktrees/distribucion-catedral")
sys.path.insert(0,str(ROOT/"tools/floor")); sys.path.insert(0,str(ROOT/"tools/props"))
import rombos_tripo as RT
R=RT.R
work=Path(sys.argv[1])
manifest, entries = RT.prepare_textures(work, 10.0)
glb_raw=work/"floor_tripo.glb"; glb_rot=work/"floor_tripo_rot.glb"
RT.run_blender(manifest, 20261108, glb_raw)
R.rotate_glb_y(glb_raw, glb_rot, -45)
world=np.array(RT.lab_render(glb_rot, work/"lab_settings.json", work/"lab_pkg"))
print("world", world.shape)
crop=world[96:480,384:768][128:256,128:256].astype(float)
fl=np.array(Image.open(ROOT/"assets/environment/cathedral/floor/rombos_tripo/floor_512x256.png").convert("RGB")).astype(float)[:128,:128]
print("diff crop vs floor png: mean %.2f max %.0f"%(np.abs(crop-fl).mean(), np.abs(crop-fl).max()))
