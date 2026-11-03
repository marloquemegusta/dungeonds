# Measures where the muzzle flash lands in the shot_origin_8_dirs scenario output
# against the muzzle exported by the lab. usage: python.exe tools/check_shot_origin.py <scenario output dir>
import json, glob, sys
from PIL import Image
R = sys.argv[1]
mz = json.load(open('assets/sprites/characters/marine/settings.json'))['dirMuzzle']
targets = {"S": (128, 170), "SW": (66, 115), "W": (56, 80), "NW": (66, 45),
           "N": (128, 20), "NE": (190, 45), "E": (200, 80), "SE": (190, 115)}
FLASH = {(248, 248, 192), (248, 192, 48)}   # flash core + hot (the cool tail is shared with pellet streaks)

def aim_dir(dx, dy):
    ax, ay = abs(dx), abs(dy)
    if ax * 2 < ay: dx = 0
    elif ay * 2 < ax: dy = 0
    else: dx = -1 if dx < 0 else 1; dy = -1 if dy < 0 else 1
    if dx == 0: return 0 if dy >= 0 else 4
    if dy == 0: return 2 if dx < 0 else 6
    if dx < 0: return 1 if dy > 0 else 3
    return 5 if dy < 0 else 7

worst = 0
for name, (tx, ty) in targets.items():
    d = aim_dir(tx - 128, ty - 80)
    gx, gy, h = mz[d][0]
    exp = (128 + gx, 96 + gy - h)
    best = None
    for f in sorted(glob.glob(R + f'/shot_{name}_*.png')):
        im = Image.open(f).convert('RGB').crop((0, 192, 256, 384))
        pts = [(x, y) for y in range(192) for x in range(256) if im.getpixel((x, y)) in FLASH]
        if pts and (best is None or len(pts) > len(best[1])): best = (f, pts)
    if not best:
        print(f"{name:2} dir={d} NO FLASH expected={exp}"); worst = 99; continue
    pts = best[1]
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
    err = ((cx - exp[0]) ** 2 + (cy - exp[1]) ** 2) ** 0.5
    worst = max(worst, err)
    print(f"{name:2} dir={d} flash_px={len(pts):3} centroid=({cx:5.1f},{cy:5.1f}) muzzle={exp} err={err:4.1f}px")
print("worst error px:", round(worst, 1))
