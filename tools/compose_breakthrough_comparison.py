from PIL import Image, ImageDraw
import os

brain = r"C:\Users\malfonso\.gemini\antigravity\brain\86aaf12c-62b7-44f6-a2bf-df88a67a446a"

im_ray = Image.open(f"{brain}/binary_mode1_ground_ray.png").resize((256, 192), Image.Resampling.NEAREST)
im_bvh = Image.open(f"{brain}/bvh_true_3d_visibility_ds.png").resize((256, 192), Image.Resampling.NEAREST)
im_blender = Image.open(f"{brain}/blender_real_lighting_ds_view.png").resize((256, 192), Image.Resampling.LANCZOS)

comp = Image.new("RGB", (256 * 3, 192 + 28), (15, 15, 18))
draw = ImageDraw.Draw(comp)

comp.paste(im_ray, (0, 28))
comp.paste(im_bvh, (256, 28))
comp.paste(im_blender, (512, 28))

draw.text((10, 8), "1. RAYCASTING 2D (Bandas y cortes)", fill=(255, 120, 120))
draw.text((266, 8), "2. VISIBILIDAD 3D BAKED (Exacta)", fill=(100, 255, 140))
draw.text((522, 8), "3. BLENDER 3D (Referencia fisica)", fill=(100, 220, 255))

final_comp = comp.resize((comp.width * 2, comp.height * 2), Image.Resampling.NEAREST)
out_p = f"{brain}/baked_3d_breakthrough_comparison.png"
final_comp.save(out_p)
print("Saved comparison to:", out_p)
