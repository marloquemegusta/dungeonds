from pathlib import Path
from PIL import Image

root = Path(r"C:\codexlocal\dungeonds")

def bbox(path):
    return Image.open(path).convert("RGBA").getchannel("A").getbbox()

player = root / "assets/characters/monster/player_e30.png"
player_im = Image.open(player).convert("RGBA")
print("player sheet", player_im.size)
for d, f in [(0, 0), (0, 4), (4, 0), (7, 7)]:
    box = player_im.crop((f * 64, d * 64, (f + 1) * 64, (d + 1) * 64)).getchannel("A").getbbox()
    print(f" player d{d} f{f}: {box} size={(box[2]-box[0], box[3]-box[1]) if box else None}")

for name in ["WR_crypt_r000", "WR_crypt_r090", "P_soul_r000", "AR_row_r000"]:
    path = root / "assets/dungeon_e30" / f"{name}.png"
    print(name, Image.open(path).size, bbox(path))
