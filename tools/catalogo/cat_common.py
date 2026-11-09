"""Utilidades compartidas de las hojas de comparacion del catalogo de la catedral."""
import json
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FLOOR = os.path.join(ROOT, "assets/environment/cathedral/floor")
RENDER = os.path.join(ROOT, "assets/environment/cathedral/props/render")
ASSETS_OUT = os.path.join(ROOT, "walkthroughs/v032-escenario/assets")

BG = (30, 27, 24, 255)
INK = (232, 224, 208, 255)
DIM = (168, 158, 140, 255)
ACCENT = (226, 170, 74, 255)
GRID = (255, 255, 255, 22)
MAX_WIDTH = 1600
CELL_GAP = 4
MARGIN = 2


def out_path(name):
    os.makedirs(ASSETS_OUT, exist_ok=True)
    return os.path.join(ASSETS_OUT, name)


def font(size):
    for name in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def floor_crop(floor_name, size, box):
    path = os.path.join(FLOOR, floor_name, "floor_512x256.png")
    image = Image.open(path).convert("RGB")
    return image.crop(box).resize(size, Image.NEAREST)


def prop_image(name):
    return Image.open(os.path.join(RENDER, name, "color.png")).convert("RGBA")


def prop_shadow(name):
    folder = os.path.join(RENDER, name)
    meta = json.load(open(os.path.join(folder, "meta.json"), encoding="utf-8"))
    mask = Image.open(os.path.join(folder, "shadow.png")).convert("L")
    return mask, tuple(meta.get("shadow_offset_px", (0, 0)))


def shadow_rgba(mask, alpha=0.55):
    rgba = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    rgba.putalpha(mask.point(lambda v: int(v * alpha)))
    return rgba


def char_frame(kind, char, direction, frame):
    path = os.path.join(ROOT, "assets/sprites", kind, char, "spritesheet.png")
    sheet = Image.open(path).convert("RGBA")
    x, y = frame * 40, direction * 40
    return sheet.crop((x, y, x + 40, y + 40))


def char_anchor(kind, char):
    path = os.path.join(ROOT, "assets/sprites", kind, char, "settings.json")
    return tuple(json.load(open(path, encoding="utf-8"))["anchor"])


def fit_font_size(draw, text, size, max_w):
    while size > 8 and draw.textlength(text, font=font(size)) > max_w:
        size -= 1
    return size


def fit_text(draw, text, fnt, max_w):
    if draw.textlength(text, font=fnt) <= max_w:
        return text
    while text and draw.textlength(text + "\u2026", font=fnt) > max_w:
        text = text[:-1]
    return text + "\u2026"


def draw_label(draw, x, y, max_w, badge, label, size):
    fnt = font(size)
    bfnt = font(int(size * 0.95))
    bw = draw.textlength(str(badge), font=bfnt)
    label = fit_text(draw, label, fnt, max_w - bw - 26)
    box_w = int(min(max_w, bw + 26 + draw.textlength(label, font=fnt)))
    box_h = size + 7
    draw.rectangle((x, y, x + box_w, y + box_h), fill=(0, 0, 0, 165))
    draw.rectangle((x, y, x + bw + 14, y + box_h), fill=ACCENT)
    draw.text((x + 7, y + 2), str(badge), font=bfnt, fill=(20, 16, 10, 255))
    draw.text((x + bw + 18, y + 2), label, font=fnt, fill=INK)


def build_grid(cells, cols, cell_w, cell_h, filename, title, scale=3, footer=""):
    """cells: lista de (imagen RGBA de cell_w x cell_h, badge, etiqueta)."""
    rows = (len(cells) + cols - 1) // cols
    base_w = cols * cell_w + (cols - 1) * CELL_GAP
    base_h = rows * cell_h + (rows - 1) * CELL_GAP
    base = Image.new("RGBA", (base_w, base_h), BG)
    for index, (image, _badge, _label) in enumerate(cells):
        col, row = index % cols, index // cols
        base.alpha_composite(image, (col * (cell_w + CELL_GAP), row * (cell_h + CELL_GAP)))

    big = base.resize((base_w * scale, base_h * scale), Image.NEAREST)
    title_h = int(23 * scale)
    footer_h = int(17 * scale) if footer else 0
    width = big.width + MARGIN * 2
    height = big.height + MARGIN * 2 + title_h + footer_h
    if width > MAX_WIDTH:
        raise SystemExit(f"{filename}: {width} px de ancho > {MAX_WIDTH}")

    out = Image.new("RGBA", (width, height), BG)
    out.alpha_composite(big, (MARGIN, MARGIN + title_h))
    draw = ImageDraw.Draw(out)
    title_size = fit_font_size(draw, title, int(14 * scale), width - 2 * MARGIN - 6)
    draw.text((MARGIN + 4, 3), title, font=font(title_size), fill=INK)

    for index, (_image, badge, label) in enumerate(cells):
        col, row = index % cols, index // cols
        fx = MARGIN + col * (cell_w + CELL_GAP) * scale
        fy = MARGIN + title_h + row * (cell_h + CELL_GAP) * scale
        cell_px_w = cell_w * scale
        draw_label(draw, fx + 4, fy + cell_h * scale - int(13 * scale) - 5,
                   cell_px_w - 8, badge, label, int(7 * scale))

    if footer:
        footer_size = fit_font_size(draw, footer, int(9 * scale), width - 2 * MARGIN - 6)
        draw.text((MARGIN + 4, height - footer_h + 3), footer,
                  font=font(footer_size), fill=DIM)

    out.convert("RGB").save(out_path(filename))
    print(out_path(filename), out.size)
    return out
