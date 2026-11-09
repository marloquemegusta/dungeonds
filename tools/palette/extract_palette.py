#!/usr/bin/env python3
"""Extrae una paleta BGR555 a partir de imágenes de referencia."""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


METHOD = (
    "Cada imagen se reduce a 256 px de ancho con Pillow BOX. Los píxeles se agrupan en CIELAB D65; "
    "se inicializa k-means++ de forma determinista. Para conservar acentos, se buscan cubetas RGB555 "
    "con croma Lab > 35 y al menos 0,3% de los píxeles del grupo: cada cubeta seleccionada reserva "
    "un centro fijo y sus píxeles se asignan a él en cada iteración. Si hay más acentos que centros, "
    "se priorizan por frecuencia y luego por croma. El resto de centros se ajusta por media Lab. "
    "Finalmente se redondea a RGB555, se eliminan duplicados y se ordena por luminancia."
)


def srgb_to_lab(rgb):
    """Convierte RGB sRGB 0..255 a CIELAB, iluminante D65, observador 2 grados."""
    rgb = np.asarray(rgb, dtype=np.float64) / 255.0
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    matrix = np.array(
        [[0.4124564, 0.3575761, 0.1804375],
         [0.2126729, 0.7151522, 0.0721750],
         [0.0193339, 0.1191920, 0.9503041]], dtype=np.float64
    )
    xyz = linear @ matrix.T
    xyz /= np.array([0.95047, 1.0, 1.08883], dtype=np.float64)
    delta = 6.0 / 29.0
    threshold = delta ** 3
    f = np.where(xyz > threshold, np.cbrt(xyz), xyz / (3.0 * delta * delta) + 4.0 / 29.0)
    fx, fy, fz = f[..., 0], f[..., 1], f[..., 2]
    return np.stack((116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz)), axis=-1)


def lab_to_srgb(lab):
    """Convierte Lab D65 a RGB sRGB 0..255; se usa para cuantizar centros."""
    lab = np.asarray(lab, dtype=np.float64)
    fy = (lab[..., 0] + 16.0) / 116.0
    fx = fy + lab[..., 1] / 500.0
    fz = fy - lab[..., 2] / 200.0
    f = np.stack((fx, fy, fz), axis=-1)
    delta = 6.0 / 29.0
    xyz = np.where(f > delta, f ** 3, 3.0 * delta * delta * (f - 4.0 / 29.0))
    xyz *= np.array([0.95047, 1.0, 1.08883], dtype=np.float64)
    matrix = np.array(
        [[3.2404542, -1.5371385, -0.4985314],
         [-0.9692660, 1.8760108, 0.0415560],
         [0.0556434, -0.2040259, 1.0572252]], dtype=np.float64
    )
    linear = xyz @ matrix.T
    srgb = np.where(linear <= 0.0031308, 12.92 * linear, 1.055 * np.maximum(linear, 0.0) ** (1.0 / 2.4) - 0.055)
    return np.clip(np.rint(srgb * 255.0), 0, 255).astype(np.uint8)


def rgb8_to_rgb5(rgb):
    return np.clip(np.floor(np.asarray(rgb, dtype=np.float64) * (31.0 / 255.0) + 0.5), 0, 31).astype(np.uint8)


def rgb5_to_rgb8(rgb5):
    values = np.asarray(rgb5, dtype=np.uint16)
    return (values * 8 + values // 4).astype(np.uint8)


def rgb5_ids(rgb5):
    rgb5 = np.asarray(rgb5, dtype=np.int32)
    return rgb5[..., 0] * 1024 + rgb5[..., 1] * 32 + rgb5[..., 2]


def parse_region(value):
    try:
        vals = [float(part.strip()) for part in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("usa x,y,w,h con números entre 0 y 1") from exc
    if len(vals) != 4 or any(not math.isfinite(v) for v in vals):
        raise argparse.ArgumentTypeError("usa x,y,w,h con números entre 0 y 1")
    x, y, w, h = vals
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > 1 or y + h > 1:
        raise argparse.ArgumentTypeError("la región debe quedar dentro de la imagen normalizada")
    return [x, y, w, h]


def load_ds_image(path, native=False):
    """Devuelve (rgb uint8 HxWx3, valid bool HxW o None si la imagen es opaca).

    valid es False donde alpha < 128: esos píxeles no cuentan para la paleta.
    Con native=True no se redimensiona; sin native se reduce a 256 px de ancho.
    """
    with Image.open(path) as source:
        rgb_source = source.convert("RGB")
        rgba_source = source.convert("RGBA")
    width, height = rgb_source.size
    alpha = np.asarray(rgba_source, dtype=np.uint8)[..., 3]
    if alpha.min() == 255:
        # Imagen opaca: mismo camino que antes, sin máscara.
        if native:
            return np.array(rgb_source, dtype=np.uint8), None
        ds_height = max(1, int(round(height * 256.0 / width)))
        # BOX integra el área de origen al reducir, evitando sesgo por muestreo puntual.
        resized = rgb_source.resize((256, ds_height), Image.Resampling.BOX)
        return np.asarray(resized, dtype=np.uint8), None
    if native:
        return np.array(rgb_source, dtype=np.uint8), alpha >= 128
    ds_height = max(1, int(round(height * 256.0 / width)))
    # Con alfa se reduce premultiplicado (evita franjas oscuras en los bordes) y se
    # umbraliza el alfa reducido a 128 para decidir qué píxeles son válidos.
    rgba = np.asarray(rgba_source, dtype=np.float32)
    channels = np.empty((height, width, 4), dtype=np.float32)
    channels[..., :3] = rgba[..., :3] * (rgba[..., 3:4] / 255.0)
    channels[..., 3] = rgba[..., 3]
    resized = np.empty((ds_height, 256, 4), dtype=np.float32)
    for index in range(4):
        plane = Image.fromarray(np.ascontiguousarray(channels[..., index]), "F")
        resized[..., index] = np.asarray(plane.resize((256, ds_height), Image.Resampling.BOX))
    alpha_small = resized[..., 3]
    valid = alpha_small >= 128.0
    coverage = np.maximum(alpha_small, 1e-6)[..., None] / 255.0
    rgb = np.clip(np.rint(resized[..., :3] / coverage), 0, 255).astype(np.uint8)
    return rgb, valid


def checker_pixels(height, width):
    """Damero gris de 2 px: color neutro para los píxeles transparentes en las vistas previas."""
    yy, xx = np.indices((height, width))
    light = ((xx // 2 + yy // 2) % 2) == 0
    out = np.empty((height, width, 3), dtype=np.uint8)
    out[...] = np.where(light, 200, 120).astype(np.uint8)[..., None]
    return out


def make_mask(shape, regions):
    height, width = shape
    mask = np.zeros((height, width), dtype=bool)
    pixel_regions = []
    for x, y, w, h in regions:
        x0 = max(0, min(width, int(math.floor(x * width))))
        y0 = max(0, min(height, int(math.floor(y * height))))
        x1 = max(x0 + 1, min(width, int(math.ceil((x + w) * width))))
        y1 = max(y0 + 1, min(height, int(math.ceil((y + h) * height))))
        mask[y0:y1, x0:x1] = True
        pixel_regions.append([x0, y0, x1 - x0, y1 - y0])
    return mask, pixel_regions


def choose_accent_centers(rgb, lab, color_count):
    rgb5 = rgb8_to_rgb5(rgb)
    ids = rgb5_ids(rgb5)
    unique_ids, counts = np.unique(ids, return_counts=True)
    share_limit = int(math.ceil(rgb.shape[0] * 0.003))
    candidates = []
    for color_id, count in zip(unique_ids.tolist(), counts.tolist()):
        if count < share_limit:
            continue
        r5, rem = divmod(color_id, 1024)
        g5, b5 = divmod(rem, 32)
        representative = rgb5_to_rgb8([r5, g5, b5])
        accent_lab = srgb_to_lab(representative)
        chroma = float(np.hypot(accent_lab[1], accent_lab[2]))
        if chroma > 35.0:
            candidates.append((count, chroma, color_id, accent_lab))
    candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
    limited = candidates[:color_count]
    return ids, limited, len(candidates) - len(limited)


def kmeans_lab(rgb, requested, seed):
    if requested <= 0 or len(rgb) == 0:
        return np.empty((0, 3), dtype=np.float64), 0
    lab = srgb_to_lab(rgb)
    ids, accents, omitted = choose_accent_centers(rgb, lab, requested)
    accent_centers = [item[3] for item in accents]
    center_count = min(requested, max(1, len(np.unique(rgb, axis=0))))
    fixed_count = min(len(accent_centers), center_count)
    centers = np.empty((center_count, 3), dtype=np.float64)
    if fixed_count:
        centers[:fixed_count] = np.asarray(accent_centers[:fixed_count])

    rng = np.random.default_rng(seed)
    min_dist = np.full(len(lab), np.inf, dtype=np.float64)
    for idx in range(fixed_count):
        dist = np.sum((lab - centers[idx]) ** 2, axis=1)
        min_dist = np.minimum(min_dist, dist)
    for idx in range(fixed_count, center_count):
        weights = min_dist.copy()
        total = float(weights.sum())
        if total <= 0.0 or not math.isfinite(total):
            pick = int(rng.integers(0, len(lab)))
        else:
            pick = int(rng.choice(len(lab), p=weights / total))
        centers[idx] = lab[pick]
        dist = np.sum((lab - centers[idx]) ** 2, axis=1)
        min_dist = np.minimum(min_dist, dist)

    # Enforce assignments for accent bins and keep their reserved centers fixed.
    pinned = np.full(len(lab), -1, dtype=np.int32)
    for accent_idx, item in enumerate(accents[:fixed_count]):
        pinned[ids == item[2]] = accent_idx
    for _ in range(40):
        labels = np.empty(len(lab), dtype=np.int32)
        nearest = np.empty(len(lab), dtype=np.float64)
        for start in range(0, len(lab), 8192):
            batch = lab[start:start + 8192]
            distances = np.sum((batch[:, None, :] - centers[None, :, :]) ** 2, axis=2)
            labels[start:start + len(batch)] = np.argmin(distances, axis=1)
            nearest[start:start + len(batch)] = np.min(distances, axis=1)
        pinned_mask = pinned >= 0
        labels[pinned_mask] = pinned[pinned_mask]
        updated = centers.copy()
        for idx in range(fixed_count, center_count):
            members = lab[labels == idx]
            if len(members):
                updated[idx] = members.mean(axis=0)
            else:
                # Empty cluster: reseed at the farthest point. No division by zero.
                updated[idx] = lab[int(np.argmax(nearest))]
        shift = float(np.max(np.abs(updated - centers))) if center_count else 0.0
        centers = updated
        if shift < 1e-3:
            break
    return centers, omitted


def centers_to_rgb5(centers):
    if not len(centers):
        return []
    rgb8 = lab_to_srgb(centers)
    rgb5 = rgb8_to_rgb5(rgb8)
    # Elimina colisiones posteriores a la cuantización a 5 bits.
    unique = {}
    for color in rgb5.tolist():
        unique.setdefault(tuple(int(v) for v in color), color)
    colors = list(unique.values())
    colors.sort(key=lambda c: float(srgb_to_lab(rgb5_to_rgb8(c))[0]))
    return colors


def bgr555(rgb5):
    r, g, b = (int(v) for v in rgb5)
    return r | (g << 5) | (b << 10)


def draw_swatches(path, terrain, props):
    groups = [("Terreno", terrain), ("Piezas", props)]
    columns, tile_w, tile_h, top = 8, 112, 78, 28
    total_h = 12
    for _, colors in groups:
        total_h += top + max(1, math.ceil(len(colors) / columns)) * tile_h
    image = Image.new("RGB", (columns * tile_w, total_h), (245, 245, 245))
    draw = ImageDraw.Draw(image)
    y = 8
    for label, colors in groups:
        draw.text((8, y), f"{label} ({len(colors)})", fill=(20, 20, 20))
        y += top
        for index, color in enumerate(colors):
            x = (index % columns) * tile_w + 6
            row_y = y + (index // columns) * tile_h
            draw.rectangle((x, row_y, x + 91, row_y + 39), fill=tuple(int(v) for v in rgb5_to_rgb8(color)))
            draw.text((x, row_y + 43), f"{index:03d}  0x{bgr555(color):04X}", fill=(15, 15, 15))
        y += max(1, math.ceil(len(colors) / columns)) * tile_h
    image.save(path)


def remap_image(rgb, palette_lab, palette_rgb8):
    lab = srgb_to_lab(rgb.reshape(-1, 3))
    output = np.empty_like(rgb.reshape(-1, 3))
    # Batches cap temporary distance arrays for tall inputs.
    for start in range(0, len(lab), 8192):
        batch = lab[start:start + 8192]
        distances = np.sum((batch[:, None, :] - palette_lab[None, :, :]) ** 2, axis=2)
        output[start:start + len(batch)] = palette_rgb8[np.argmin(distances, axis=1)]
    return output.reshape(rgb.shape)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extrae una paleta BGR555 desde imágenes de arte objetivo.")
    parser.add_argument("images", nargs="+", type=Path, metavar="IMG")
    parser.add_argument("--terrain-region", action="append", type=parse_region, default=[], metavar="x,y,w,h")
    parser.add_argument("--terrain-colors", type=int, default=48)
    parser.add_argument("--prop-colors", type=int, default=150)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--native", action="store_true", help="no redimensiona: usa los píxeles 1:1")
    args = parser.parse_args(argv)
    if args.terrain_colors < 0 or args.prop_colors < 0 or args.terrain_colors + args.prop_colors > 256:
        parser.error("los colores deben ser no negativos y sumar como máximo 256")
    if args.terrain_colors and not args.terrain_region:
        # Una solicitud de terreno sin regiones queda vacía por contrato.
        pass

    images, terrain_pixels, prop_pixels = [], [], []
    region_metadata, output_stems = [], set()
    for path in args.images:
        if not path.is_file():
            parser.error(f"no existe la imagen: {path}")
        stem = path.stem
        if stem in output_stems:
            parser.error(f"dos entradas comparten el nombre de salida '{stem}'")
        output_stems.add(stem)
        rgb, valid = load_ds_image(path, args.native)
        if valid is None:
            valid = np.ones(rgb.shape[:2], dtype=bool)
        transparent = int(np.count_nonzero(~valid))
        if transparent:
            print(f"{path.name}: {transparent} píxeles transparentes excluidos de la paleta.")
        mask, pixel_regions = make_mask(rgb.shape[:2], args.terrain_region)
        if args.terrain_region:
            terrain_pixels.append(rgb[mask & valid].reshape(-1, 3))
        prop_pixels.append(rgb[~mask & valid].reshape(-1, 3))
        images.append((path, stem, rgb, valid, pixel_regions))
        region_metadata.append({"source": str(path), "normalized": args.terrain_region, "ds_pixels": pixel_regions})

    terrain_rgb = np.concatenate(terrain_pixels, axis=0) if terrain_pixels else np.empty((0, 3), dtype=np.uint8)
    props_rgb = np.concatenate(prop_pixels, axis=0) if prop_pixels else np.empty((0, 3), dtype=np.uint8)
    terrain_centers, terrain_omitted = kmeans_lab(terrain_rgb, args.terrain_colors if args.terrain_region else 0, 1337)
    prop_centers, prop_omitted = kmeans_lab(props_rgb, args.prop_colors, 7331)
    terrain = centers_to_rgb5(terrain_centers)
    props = centers_to_rgb5(prop_centers)
    terrain_duplicates = max(0, len(terrain_centers) - len(terrain))
    prop_duplicates = max(0, len(prop_centers) - len(props))
    if terrain_omitted or prop_omitted:
        print(f"Aviso: se omitieron {terrain_omitted + prop_omitted} acentos porque excedían los centros disponibles.")
    if not terrain and not props:
        parser.error("no hay colores para formar la paleta")

    args.out.mkdir(parents=True, exist_ok=True)
    palette_rgb5 = terrain + props
    palette_rgb8 = rgb5_to_rgb8(palette_rgb5)
    palette_lab = srgb_to_lab(palette_rgb8)
    payload = {
        "terrain": terrain,
        "props": props,
        "bgr555_hex": {
            "terrain": [f"0x{bgr555(color):04X}" for color in terrain],
            "props": [f"0x{bgr555(color):04X}" for color in props],
        },
        "sources": [str(path) for path in args.images],
        "regions": region_metadata,
        "method": METHOD,
    }
    json_path = args.out / "palette.json"
    with json_path.open("w", encoding="utf-8", newline="") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    swatches_path = args.out / "swatches.png"
    draw_swatches(swatches_path, terrain, props)
    print(f"Terreno: {len(terrain)} colores finales; {terrain_duplicates} duplicados eliminados.")
    print(f"Piezas: {len(props)} colores finales; {prop_duplicates} duplicados eliminados.")
    print(f"Salida: {json_path}")
    print(f"Salida: {swatches_path}")

    for path, stem, rgb, valid, pixel_regions in images:
        checker = checker_pixels(rgb.shape[0], rgb.shape[1])
        remapped = remap_image(rgb, palette_lab, palette_rgb8)
        remapped[~valid] = checker[~valid]
        enlarged = Image.fromarray(remapped, "RGB").resize((rgb.shape[1] * 3, rgb.shape[0] * 3), Image.Resampling.NEAREST)
        ds_path = args.out / f"{stem}_ds.png"
        enlarged.save(ds_path)
        shown = rgb.copy()
        shown[~valid] = checker[~valid]
        region_image = Image.fromarray(shown, "RGB")
        draw = ImageDraw.Draw(region_image)
        for x, y, w, h in pixel_regions:
            draw.rectangle((x, y, x + w - 1, y + h - 1), outline=(255, 0, 255), width=1)
        regions_path = args.out / f"{stem}_regions.png"
        region_image.save(regions_path)
        print(f"Salida: {ds_path}")
        print(f"Salida: {regions_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
