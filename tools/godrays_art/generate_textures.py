import math
from PIL import Image, ImageDraw
import numpy as np

def create_lancet_texture(mode="vitral", width=1024, height=2389):
    """
    Lancet window texture:
    width x height corresponds to 1.5m x 3.5m (aspect ratio 1 : 2.333).
    mode: 'vitral' or 'amber'
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    margin_x = int(width * 0.08)
    margin_bottom = int(height * 0.04)
    w_inner = width - 2 * margin_x
    
    # Springing line of the pointed arch (imposta)
    spring_y = int(height * 0.42)
    bottom_y = height - margin_bottom
    
    # Twin lancets
    num_lancets = 2
    lancet_w = w_inner // num_lancets
    mullion_w = int(width * 0.04)
    lead_w = max(3, int(width * 0.009))

    def get_color(li, row, is_rose=False):
        if mode == "amber":
            # Warm honey amber with subtle pane variations
            v = 0.88 + 0.12 * math.sin(row * 1.5 + li * 2.7)
            r = int(220 * v)
            g = int(145 * v)
            b = int(40 * v)
            return (r, g, b, 255)
        else: # vitral
            v = 0.90 + 0.10 * math.sin(row * 1.8 + li)
            if is_rose:
                if row % 2 == 0:
                    return (int(225 * v), int(155 * v), int(45 * v), 255) # Gold
                else:
                    return (int(210 * v), int(35 * v), int(55 * v), 255)  # Crimson
            if li == 0:
                # Left lancet: Royal Sapphire Blue & Muted Violet accents
                if row % 4 == 0:
                    return (int(130 * v), int(50 * v), int(160 * v), 255) # Violet
                else:
                    return (int(35 * v), int(95 * v), int(225 * v), 255)  # Deep sapphire blue
            else:
                # Right lancet: Burgundy Crimson & Sacred Gold accents
                if row % 4 == 0:
                    return (int(225 * v), int(150 * v), int(40 * v), 255) # Gold
                else:
                    return (int(215 * v), int(30 * v), int(55 * v), 255)  # Burgundy crimson

    diamond_h = int(height * 0.038)
    lancet_tops = []

    for li in range(num_lancets):
        lx0 = margin_x + li * lancet_w + mullion_w // 2
        lx1 = margin_x + (li + 1) * lancet_w - mullion_w // 2
        lcx = (lx0 + lx1) // 2
        lrw = (lx1 - lx0) // 2
        lancet_top_y = spring_y - int(lrw * 1.3)
        lancet_tops.append((lx0, lx1, lcx, lrw, lancet_top_y))

        # Diamond panes up to springing line
        y = bottom_y
        row = 0
        while y > lancet_top_y:
            y_next = y - diamond_h
            c = get_color(li, row)
            pane_poly = [(lx0, y), (lx1, y), (lx1, y_next), (lx0, y_next)]
            draw.polygon(pane_poly, fill=c)
            # Lead lattice lines
            draw.line([(lx0, y), (lx1, y_next)], fill=(12, 12, 12, 255), width=lead_w)
            draw.line([(lx1, y), (lx0, y_next)], fill=(12, 12, 12, 255), width=lead_w)
            draw.line([(lx0, y), (lx1, y)], fill=(15, 15, 15, 255), width=lead_w)
            y = y_next
            row += 1

        # Pointed arch top of lancet
        draw.rectangle([lx0, 0, lx1, lancet_top_y], fill=(0, 0, 0, 255))
        arch_tip = (lcx, lancet_top_y)
        draw.polygon([(lx0, spring_y), arch_tip, (lx1, spring_y)], fill=get_color(li, row))
        draw.line([(lx0, spring_y), arch_tip, (lx1, spring_y)], fill=(15, 15, 15, 255), width=lead_w * 2)

    # Upper Tracery / Rosette in the head of the arch
    rose_cx = width // 2
    rose_cy = int(spring_y - (w_inner // 2) * 0.45)
    rose_r = int((w_inner // 2) * 0.48)
    draw.ellipse([rose_cx - rose_r, rose_cy - rose_r, rose_cx + rose_r, rose_cy + rose_r],
                 fill=get_color(0, 0, is_rose=True), outline=(15, 15, 15, 255), width=mullion_w)

    num_petals = 6
    petal_r = int(rose_r * 0.42)
    for pi in range(num_petals):
        ang = pi * (2 * math.pi / num_petals)
        px = int(rose_cx + (rose_r - petal_r) * math.cos(ang))
        py = int(rose_cy + (rose_r - petal_r) * math.sin(ang))
        draw.ellipse([px - petal_r, py - petal_r, px + petal_r, py + petal_r],
                     outline=(12, 12, 12, 255), width=lead_w)

    # Center medallion of upper rose
    center_r = int(rose_r * 0.28)
    draw.ellipse([rose_cx - center_r, rose_cy - center_r, rose_cx + center_r, rose_cy + center_r],
                 fill=(220, 40, 50, 255) if mode == "vitral" else (225, 155, 45, 255),
                 outline=(15, 15, 15, 255), width=lead_w)

    # Central stone mullion
    cx = width // 2
    draw.rectangle([cx - mullion_w // 2, spring_y - 20, cx + mullion_w // 2, bottom_y], fill=(10, 10, 10, 255))

    # Gothic Outer Pointed Arch Mask (equilateral pointed arch)
    r_arch = w_inner
    arch_mask1 = Image.new("L", (width, height), 0)
    d1 = ImageDraw.Draw(arch_mask1)
    d1.ellipse([margin_x + w_inner - r_arch, spring_y - r_arch, margin_x + w_inner + r_arch, spring_y + r_arch], fill=255)

    arch_mask2 = Image.new("L", (width, height), 0)
    d2 = ImageDraw.Draw(arch_mask2)
    d2.ellipse([margin_x - r_arch, spring_y - r_arch, margin_x + r_arch, spring_y + r_arch], fill=255)

    m1 = np.array(arch_mask1)
    m2 = np.array(arch_mask2)
    arch_intersection = (m1 > 0) & (m2 > 0)

    base_mask = np.zeros((height, width), dtype=bool)
    base_mask[spring_y:bottom_y, margin_x:width - margin_x] = True
    base_mask[arch_intersection] = True
    # Keep inside margins and above bottom
    base_mask[bottom_y:, :] = False
    base_mask[:, :margin_x] = False
    base_mask[:, width - margin_x:] = False

    img_arr = np.array(img)
    img_arr[~base_mask] = [0, 0, 0, 255]

    # Draw dark stone surround along arch rim
    final_img = Image.fromarray(img_arr)
    d_fin = ImageDraw.Draw(final_img)
    d_fin.rectangle([0, bottom_y, width, height], fill=(0, 0, 0, 255))
    d_fin.rectangle([0, 0, margin_x, height], fill=(0, 0, 0, 255))
    d_fin.rectangle([width - margin_x, 0, width, height], fill=(0, 0, 0, 255))

    return final_img


def create_rose_texture(width=2048, height=2048):
    """
    Circular gothic rose window texture (rosetón):
    2048 x 2048 square.
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    cx = width // 2
    cy = height // 2
    r_outer = int(width * 0.44)
    r_mullion_ring = int(r_outer * 0.88)
    r_mid_ring = int(r_outer * 0.52)
    r_inner_ring = int(r_outer * 0.26)
    r_center = int(r_outer * 0.12)

    spoke_w = int(width * 0.022)
    lead_w = max(3, int(width * 0.007))

    num_sectors = 12

    # Draw sectors
    # Sector colors: alternate royal sapphire blue, sacred gold, burgundy crimson, and muted violet
    colors = [
        (35, 95, 225, 255),   # Blue
        (225, 155, 45, 255),  # Gold
        (215, 30, 55, 255),   # Crimson
        (135, 55, 165, 255),  # Violet
    ]

    # Base background circle
    draw.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], fill=(20, 20, 20, 255))

    # Outer petal ring (between r_mid_ring and r_outer)
    for i in range(num_sectors):
        a0 = i * (2 * math.pi / num_sectors)
        a1 = (i + 1) * (2 * math.pi / num_sectors)
        amid = (a0 + a1) / 2.0
        c_outer = colors[i % 4]
        c_inner = colors[(i + 2) % 4]

        # Draw outer polygon
        n_steps = 10
        pts_outer = []
        for s in range(n_steps + 1):
            ang = a0 + (a1 - a0) * (s / n_steps)
            pts_outer.append((cx + int(r_outer * math.cos(ang)), cy + int(r_outer * math.sin(ang))))
        for s in range(n_steps, -1, -1):
            ang = a0 + (a1 - a0) * (s / n_steps)
            pts_outer.append((cx + int(r_mid_ring * math.cos(ang)), cy + int(r_mid_ring * math.sin(ang))))
        draw.polygon(pts_outer, fill=c_outer)

        # Draw inner polygon
        pts_inner = []
        for s in range(n_steps + 1):
            ang = a0 + (a1 - a0) * (s / n_steps)
            pts_inner.append((cx + int(r_mid_ring * math.cos(ang)), cy + int(r_mid_ring * math.sin(ang))))
        for s in range(n_steps, -1, -1):
            ang = a0 + (a1 - a0) * (s / n_steps)
            pts_inner.append((cx + int(r_inner_ring * math.cos(ang)), cy + int(r_inner_ring * math.sin(ang))))
        draw.polygon(pts_inner, fill=c_inner)

        # Cusped petal / lancet top inside each outer sector
        petal_cx = cx + int((r_mid_ring + r_outer) * 0.5 * math.cos(amid))
        petal_cy = cy + int((r_mid_ring + r_outer) * 0.5 * math.sin(amid))
        petal_pr = int((r_outer - r_mid_ring) * 0.38)
        draw.ellipse([petal_cx - petal_pr, petal_cy - petal_pr, petal_cx + petal_pr, petal_cy + petal_pr],
                     fill=colors[(i + 1) % 4], outline=(15, 15, 15, 255), width=lead_w)

        # Cusped trefoil in inner ring
        inner_cx = cx + int((r_inner_ring + r_mid_ring) * 0.5 * math.cos(amid))
        inner_cy = cy + int((r_inner_ring + r_mid_ring) * 0.5 * math.sin(amid))
        inner_pr = int((r_mid_ring - r_inner_ring) * 0.32)
        draw.ellipse([inner_cx - inner_pr, inner_cy - inner_pr, inner_cx + inner_pr, inner_cy + inner_pr],
                     fill=colors[(i + 3) % 4], outline=(15, 15, 15, 255), width=lead_w)

    # Concentric stone divider rings
    draw.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], outline=(10, 10, 10, 255), width=spoke_w * 2)
    draw.ellipse([cx - r_mullion_ring, cy - r_mullion_ring, cx + r_mullion_ring, cy + r_mullion_ring], outline=(12, 12, 12, 255), width=lead_w * 2)
    draw.ellipse([cx - r_mid_ring, cy - r_mid_ring, cx + r_mid_ring, cy + r_mid_ring], outline=(15, 15, 15, 255), width=spoke_w)
    draw.ellipse([cx - r_inner_ring, cy - r_inner_ring, cx + r_inner_ring, cy + r_inner_ring], outline=(15, 15, 15, 255), width=spoke_w)

    # Radiating stone spokes (mullions)
    for i in range(num_sectors):
        ang = i * (2 * math.pi / num_sectors)
        x1 = cx + int(r_inner_ring * math.cos(ang))
        y1 = cy + int(r_inner_ring * math.sin(ang))
        x2 = cx + int(r_outer * math.cos(ang))
        y2 = cy + int(r_outer * math.sin(ang))
        draw.line([(x1, y1), (x2, y2)], fill=(12, 12, 12, 255), width=spoke_w)

    # Center Rosette Roundel
    draw.ellipse([cx - r_inner_ring, cy - r_inner_ring, cx + r_inner_ring, cy + r_inner_ring],
                 fill=(225, 155, 45, 255), outline=(15, 15, 15, 255), width=spoke_w)

    num_center_petals = 6
    c_petal_r = int(r_inner_ring * 0.40)
    for pi in range(num_center_petals):
        ang = pi * (2 * math.pi / num_center_petals)
        px = cx + int((r_inner_ring - c_petal_r) * math.cos(ang))
        py = cy + int((r_inner_ring - c_petal_r) * math.sin(ang))
        draw.ellipse([px - c_petal_r, py - c_petal_r, px + c_petal_r, py + c_petal_r],
                     fill=(215, 30, 55, 255), outline=(12, 12, 12, 255), width=lead_w)

    # Core golden eye
    draw.ellipse([cx - r_center, cy - r_center, cx + r_center, cy + r_center],
                 fill=(235, 180, 50, 255), outline=(15, 15, 15, 255), width=lead_w)

    # Mask outside r_outer to pure black
    arr = np.array(img)
    y_grid, x_grid = np.ogrid[:height, :width]
    dist_sq = (x_grid - cx)**2 + (y_grid - cy)**2
    arr[dist_sq > (r_outer - spoke_w // 2)**2] = [0, 0, 0, 255]

    return Image.fromarray(arr)

if __name__ == "__main__":
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("Generating tex_vitral.png...")
    im_v = create_lancet_texture("vitral")
    im_v.save(os.path.join(script_dir, "tex_vitral.png"))
    
    print("Generating tex_amber.png...")
    im_a = create_lancet_texture("amber")
    im_a.save(os.path.join(script_dir, "tex_amber.png"))
    
    print("Generating tex_rose.png...")
    im_r = create_rose_texture()
    im_r.save(os.path.join(script_dir, "tex_rose.png"))
    
    print("All textures generated successfully!")
