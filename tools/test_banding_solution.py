import os, sys, math
import numpy as np
from PIL import Image, ImageDraw

def main():
    artifact_dir = r"C:\Users\malfonso\.gemini\antigravity\brain\86aaf12c-62b7-44f6-a2bf-df88a67a446a"
    base_img_path = r"walkthroughs/fog-and-visibility/assets/00_spawn.png"
    
    if not os.path.exists(base_img_path):
        print("Base image not found:", base_img_path)
        return
        
    img = Image.open(base_img_path).convert("RGBA")
    w, h = img.size # 256, 384
    
    # We will demonstrate the bottom screen (256x192) around spawn (player at 128, 88)
    # 1. Discrete 64 rays (current banding)
    # 2. Continuous Angular Buffer (no gaps, crisp solid tactical shadow)
    # 3. Soft Penumbra (smooth gradient edge without dither)
    
    bot_y0 = 192
    crop = img.crop((0, bot_y0, 256, 384))
    
    px, py = 128, 88 # Player position in bottom screen
    
    # Let's create an obstacle: a pillar/wall at (100, 60) to (120, 60) and (150, 100) to (170, 100)
    # In the real dungeon, collision map has walls. Let's create a realistic shadow mask:
    
    # --- Mode 1 Current: 64 discrete rays ---
    mode1_discrete = crop.copy()
    draw_disc = ImageDraw.Draw(mode1_discrete, "RGBA")
    
    # Simulate discrete rays with gaps
    mask_disc = Image.new("L", (256, 192), 0)
    draw_mask = ImageDraw.Draw(mask_disc)
    
    # 64 discrete lines
    num_rays = 64
    r_max = 85
    for i in range(num_rays):
        angle = 2.0 * math.pi * i / num_rays
        # Simulate an obstacle blocking angles between 0.8 and 1.4 rad
        r = r_max
        if 0.6 <= angle <= 1.5:
            r = 35 # Hit obstacle
        elif 3.5 <= angle <= 4.2:
            r = 40 # Hit wall to north
        
        # Ray line with discrete width
        ex = px + r * math.cos(angle)
        ey = py + r * math.sin(angle)
        draw_mask.line([(px, py), (ex, ey)], fill=255, width=2)
        
    # Apply 8x8 tile discretization to mask (like NDS 8x8 tiles)
    mask_tiles = Image.new("L", (256, 192), 0)
    for ty in range(0, 192, 8):
        for tx in range(0, 256, 8):
            # Check center
            if mask_disc.getpixel((min(tx+4, 255), min(ty+4, 191))) > 100:
                for cy in range(ty, min(ty+8, 192)):
                    for cx in range(tx, min(tx+8, 256)):
                        # Checkerboard dither inside unlit or lit?
                        mask_tiles.putpixel((cx, cy), 255)
                        
    # Combine: where mask_tiles is 0, darken with 50% dither (current DS look)
    dither_img = crop.copy()
    pix = dither_img.load()
    for y in range(192):
        for x in range(256):
            if mask_tiles.getpixel((x, y)) == 0:
                if (x + y) % 2 == 0:
                    pix[x, y] = (0, 0, 0, 255) # 50% dither black
                    
    # --- Solution 1: Continuous Angular Polygon / Wedge (Crisp Tactical Shadow) ---
    sol_crisp = crop.copy()
    sol_mask = Image.new("L", (256, 192), 0)
    draw_sol = ImageDraw.Draw(sol_mask)
    
    # Continuous angular sweep (256 angular steps, dense sampling)
    poly_points = [(px, py)]
    for i in range(361):
        angle = 2.0 * math.pi * i / 360.0
        r = r_max
        if 0.6 <= angle <= 1.5:
            r = 35 # Blocked by prop
        elif 3.5 <= angle <= 4.2:
            r = 40 # Blocked by north wall
        ex = px + r * math.cos(angle)
        ey = py + r * math.sin(angle)
        poly_points.append((ex, ey))
    draw_sol.polygon(poly_points, fill=255)
    
    # Darken outside polygon with solid 50% darkness (or clean hardware blend)
    shadow_overlay = Image.new("RGBA", (256, 192), (0, 0, 0, 160))
    # Invert mask: 0 inside lit, 255 in shadow
    inv_mask = Image.eval(sol_mask, lambda v: 255 - v)
    sol_crisp.paste(shadow_overlay, (0, 0), inv_mask)
    
    # --- Solution 2: Soft Light Radius with Radial Falloff ---
    sol_soft = crop.copy()
    soft_mask = Image.new("L", (256, 192), 0)
    for y in range(192):
        for x in range(256):
            dx = x - px
            dy = y - py
            d = math.hypot(dx, dy)
            angle = math.atan2(dy, dx)
            if angle < 0: angle += 2 * math.pi
            
            # Wall limits
            limit_r = r_max
            if 0.6 <= angle <= 1.5:
                limit_r = 35
            elif 3.5 <= angle <= 4.2:
                limit_r = 40
                
            if d <= limit_r:
                # Radial gradient from 255 at center to 0 at limit_r
                factor = max(0.0, 1.0 - (d / limit_r)**2)
                soft_mask.putpixel((x, y), int(factor * 255))
            else:
                soft_mask.putpixel((x, y), 0)
                
    # Composite soft light
    # Areas with soft_mask == 0 have dark overlay (e.g. 70% black)
    # Areas with soft_mask == 255 have 0% black
    shadow_overlay2 = Image.new("RGBA", (256, 192), (0, 0, 0, 200))
    inv_soft = Image.eval(soft_mask, lambda v: int((255 - v) * 0.75))
    sol_soft.paste(shadow_overlay2, (0, 0), inv_soft)

    # Save outputs
    dither_img.save(os.path.join(artifact_dir, "banding_problem_current.png"))
    sol_crisp.save(os.path.join(artifact_dir, "banding_solution_continuous_wedge.png"))
    sol_soft.save(os.path.join(artifact_dir, "banding_solution_soft_torch.png"))
    
    # Create side-by-side comparison
    comp = Image.new("RGB", (256 * 3, 192 + 28), (20, 20, 25))
    draw_comp = ImageDraw.Draw(comp)
    
    comp.paste(dither_img, (0, 28))
    comp.paste(sol_crisp, (256, 28))
    comp.paste(sol_soft, (512, 28))
    
    draw_comp.text((10, 8), "ACTUAL: Rayos Discretos (Bandas)", fill=(255, 100, 100))
    draw_comp.text((266, 8), "SOLUCION 1: Conos Continuos (Sin Bandas)", fill=(100, 255, 100))
    draw_comp.text((522, 8), "SOLUCION 2: Antorcha Gradual Suave", fill=(100, 200, 255))
    
    comp_path = os.path.join(artifact_dir, "banding_comparison.png")
    comp.save(comp_path)
    print("Saved comparison to:", comp_path)

if __name__ == "__main__":
    main()
