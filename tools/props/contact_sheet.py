"""1x + 4x contact sheet of the prerendered props next to the marine (scale reference)."""
import argparse, json, os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RENDER = os.path.join(ROOT, "assets/environment/cathedral/props/render")
OUT = os.path.join(ROOT, "walkthroughs/v032-escenario/assets/props_lote1_escala.png")
BG = (0x2a, 0x26, 0x22, 255)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", default=RENDER)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    order = list(json.load(open(os.path.join(ROOT, "tools/props/props.json"))))

    sheet = Image.open(os.path.join(ROOT, "assets/sprites/characters/marine/spritesheet.png")).convert("RGBA")
    marine = sheet.crop((0, 0, 40, 40))      # row 0 = S (faces camera), col 0
    anchor = (20, 32)

    items = [("marine", marine, anchor[0], anchor[1], 40, 40)]   # name, img, anchor x, ground row (rows above ground line)
    for n in order:
        im = Image.open(os.path.join(args.render, n, "color.png"))
        items.append((n, im, im.width // 2, im.height, im.width, im.height))

    pad, labh = 10, 22
    maxabove = max(a_y for _, _, _, a_y, _, _ in items)
    W = pad + sum(i[1].width + pad for i in items)
    H1 = labh + maxabove + 14
    x = pad; base = labh + maxabove
    s1 = Image.new("RGBA", (W, H1), BG)
    d = ImageDraw.Draw(s1); f = ImageFont.load_default()
    for n, im, ax, ay, w, h in items:
        s1.alpha_composite(im, (x, base - ay))
        d.text((x, 2), n, fill=(230, 220, 200, 255), font=f)
        d.text((x, base + 2), "%dx%d" % ((40, 40) if n == "marine" else (w, h)), fill=(160, 150, 135, 255), font=f)
        x += w + pad
    d.line([(0, base), (W, base)], fill=(90, 80, 70, 255))
    s4 = s1.resize((W * 4, H1 * 4), Image.NEAREST)
    d4 = ImageDraw.Draw(s4)
    for gx in range(0, s4.width, 32): d4.line([(gx, 0), (gx, s4.height)], fill=(255, 255, 255, 14))
    for gy in range(0, s4.height, 32): d4.line([(0, gy), (s4.width, gy)], fill=(255, 255, 255, 14))
    out = Image.new("RGBA", (s4.width, H1 + 8 + s4.height), BG)
    out.alpha_composite(s1, (0, 0)); out.alpha_composite(s4, (0, H1 + 8))
    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    out.convert("RGB").save(out_path)
    print(out_path, out.size)

if __name__ == "__main__": main()
