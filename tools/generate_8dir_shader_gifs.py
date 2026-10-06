import os, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, 'tools')
import ds_look as look

ROOT = '.'
RENDER_DIR = os.path.join(ROOT, 'assets', 'render_runs')
OUT_ASSETS = os.path.join(ROOT, 'assets')
WALKTHROUGH_ASSETS = os.path.join(ROOT, 'walkthroughs', '04-enemy-charger-and-character-swap', 'assets')
BRAIN_DIR = r"C:\Users\malfonso\.gemini\antigravity\brain\888384cb-d696-4f94-9aef-6725345f06d1"

# 8 directions in order (0 to 7):
# d00: S, d01: SW, d02: W, d03: NW, d04: N, d05: NE, d06: E, d07: SE
DIR_NAMES = [
    "0: S (Sur)",
    "1: SW (Suroeste)",
    "2: W (Oeste)",
    "3: NW (Noroeste)",
    "4: N (Norte)",
    "5: NE (Noreste)",
    "6: E (Este)",
    "7: SE (Sureste)"
]

VARIANTS = [
    ("0_in_game_current", "Original en Juego: Escala 1.0x + Postura Base + Textura 2K"),
    ("A_original", "Opción A: Escala 1.35x + Cuello +20° + Textura 2K Original"),
    ("B_contrast_clean", "Opción B: Escala 1.35x + Cuello +20° + Contraste Tonal + Normal 15%"),
    ("C_contrast_horns_glow", "Opción C: Escala 1.35x + Cuello +20° + Ramp Óseo/Fauces + Glow 5x")
]

# Layout: 4 columns x 2 rows
# Row 0: S (0), SW (1), W (2), NW (3)
# Row 1: N (4), NE (5), E (6), SE (7)
ZOOM = 2 # 64x64 at 2x = 128x128 per cell (fits neatly on screen: 4*128 + padding = ~570px wide)
CELL_W = 64 * ZOOM
CELL_H = 64 * ZOOM
COLS = 4
ROWS = 2
PAD = 12
HEADER_H = 40
CELL_PAD_BOTTOM = 22 # for direction label text

TOTAL_W = PAD * (COLS + 1) + COLS * CELL_W
TOTAL_H = HEADER_H + PAD * (ROWS + 1) + ROWS * (CELL_H + CELL_PAD_BOTTOM)

def build_variant_gif(variant_key, variant_title):
    var_dir = os.path.join(RENDER_DIR, variant_key)
    gif_frames = []
    
    # 8 animation frames
    for fi in range(8):
        # Create base canvas for this tick
        canvas = Image.new("RGBA", (TOTAL_W, TOTAL_H), (16, 14, 20, 255))
        draw = ImageDraw.Draw(canvas)
        
        # Header banner
        draw.rectangle([0, 0, TOTAL_W, HEADER_H], fill=(24, 21, 30, 255))
        draw.text((PAD, 12), variant_title, fill=(245, 240, 250, 255))
        
        for d in range(8):
            col = d % COLS
            row = d // COLS
            x0 = PAD + col * (CELL_W + PAD)
            y0 = HEADER_H + PAD + row * (CELL_H + CELL_PAD_BOTTOM + PAD)
            
            # Draw subtle cell background (dungeon floor tone simulation)
            draw.rectangle([x0 - 2, y0 - 2, x0 + CELL_W + 1, y0 + CELL_H + 1], 
                           fill=(28, 25, 34, 255), outline=(50, 45, 62, 255))
            
            # Load frame
            frame_path = os.path.join(var_dir, f"d{d:02d}_f{fi:03d}.png")
            if os.path.exists(frame_path):
                im = Image.open(frame_path).convert("RGBA")
                # Postprocess with outline and grade
                im = look.apply_outline(im, (16, 16, 24))
                im = look.grade(im)
                im_scaled = im.resize((CELL_W, CELL_H), Image.Resampling.NEAREST)
                canvas.paste(im_scaled, (x0, y0), im_scaled)
                
            # Direction label under each cell
            draw.text((x0 + 4, y0 + CELL_H + 4), DIR_NAMES[d], fill=(180, 175, 195, 255))
            
        gif_frames.append(canvas.convert("RGB"))
        
    out_filename = f"charger_8dirs_{variant_key}.gif"
    
    # Save to assets, walkthrough assets and brain artifacts
    destinations = [
        os.path.join(OUT_ASSETS, out_filename),
        os.path.join(WALKTHROUGH_ASSETS, out_filename),
        os.path.join(BRAIN_DIR, out_filename)
    ]
    
    # The original 3D FBX run cycle is 19 frames @ 30 fps = ~0.63s total cycle.
    # With 8 sampled frames, natural speed is 0.63s / 8 = ~80ms per frame.
    duration_ms = 80
    
    for dst in destinations:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        gif_frames[0].save(
            dst,
            save_all=True,
            append_images=gif_frames[1:],
            optimize=True,
            duration=duration_ms,
            loop=0
        )
        print(f"SAVED: {dst}")

for v_key, v_title in VARIANTS:
    build_variant_gif(v_key, v_title)

print("ALL_GIFS_BUILT_SUCCESS")
