"""Turn Blender's opaque Shadow Catcher pass into portable 8-bit coverage."""

from statistics import median

from PIL import Image


def read_shadow_coverage(path, expected_size):
    with Image.open(path) as source:
        rgba = source.convert("RGBA")
        image = rgba.convert("RGB")
    if image.size != expected_size:
        raise ValueError(f"{path}: {image.size} != {expected_size}")

    return shadow_coverage(image, str(path), rgba.getchannel("A").getextrema())


def shadow_coverage(image, label="image", alpha_extrema=None):
    image = image.convert("RGB")

    gray = image.convert("L")
    width, height = gray.size
    pixels = list(gray.tobytes())
    corner = [
        gray.getpixel((x, y))
        for x in range(min(8, width))
        for y in range(min(8, height))
    ]
    corner += [
        gray.getpixel((x, y))
        for x in range(max(0, width - 8), width)
        for y in range(max(0, height - 8), height)
    ]
    corner += [
        gray.getpixel((x, y))
        for x in range(max(0, width - 8), width)
        for y in range(min(8, height))
    ]
    corner += [
        gray.getpixel((x, y))
        for x in range(min(8, width))
        for y in range(max(0, height - 8), height)
    ]
    lit = median(corner)
    dark_idx = max(0, min(len(pixels) // 200, max(4, len(pixels) // 1000)))
    dark = sorted(pixels)[dark_idx]
    contrast = lit - dark
    if contrast < 8:
        raise ValueError(f"{label}: shadow pass has insufficient RGB contrast ({contrast:.1f}), alpha={alpha_extrema}")

    return [
        0 if lit - value <= 2 else min(255, round((lit - value) * 255 / contrast))
        for value in pixels
    ]


def coverage_bounds(coverage, width, height, threshold=8):
    points = [i for i, value in enumerate(coverage) if value > threshold]
    if not points:
        raise ValueError("shadow mask has no coverage")
    xs = [i % width for i in points]
    ys = [i // width for i in points]
    left, top = min(xs), min(ys)
    return left, top, max(xs) - left + 1, max(ys) - top + 1
