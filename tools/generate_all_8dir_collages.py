import os
import sys
import subprocess
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, 'tools')
import ds_look as look

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

def make_collage_from_sheet(sheet_path, out_gif_path, title, cell=64, zoom=2, duration=100):
    sheet = Image.open(sheet_path).convert('RGBA')
    cols = 4
    rows = 2
    pad = 12
    header_h = 40
    cell_pad_bottom = 22
    cell_w = cell * zoom
    cell_h = cell * zoom
    total_w = pad * (cols + 1) + cols * cell_w
    total_h = header_h + pad * (rows + 1) + rows * (cell_h + cell_pad_bottom)

    gif_frames = []
    for fi in range(8):
        canvas = Image.new('RGBA', (total_w, total_h), (16, 14, 20, 255))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([0, 0, total_w, header_h], fill=(24, 21, 30, 255))
        draw.text((pad, 12), title, fill=(245, 240, 250, 255))

        for d in range(8):
            col = d % cols
            row = d // cols
            x0 = pad + col * (cell_w + pad)
            y0 = header_h + pad + row * (cell_h + cell_pad_bottom + pad)

            draw.rectangle([x0 - 2, y0 - 2, x0 + cell_w + 1, y0 + cell_h + 1],
                           fill=(28, 25, 34, 255), outline=(50, 45, 62, 255))

            box = (fi * cell, d * cell, (fi + 1) * cell, (d + 1) * cell)
            spr = sheet.crop(box)
            spr_scaled = spr.resize((cell_w, cell_h), Image.Resampling.NEAREST)
            canvas.paste(spr_scaled, (x0, y0), spr_scaled)

            draw.text((x0 + 4, y0 + cell_h + 4), DIR_NAMES[d], fill=(180, 175, 195, 255))

        gif_frames.append(canvas.convert('P', palette=Image.Palette.ADAPTIVE))

    os.makedirs(os.path.dirname(out_gif_path), exist_ok=True)
    gif_frames[0].save(out_gif_path, save_all=True, append_images=gif_frames[1:], duration=duration, loop=0)
    print(f"[OK] Generated {out_gif_path}")


def make_collage_from_frames(frames_dir, out_gif_path, title, cell=64, zoom=2, duration=100):
    cols = 4
    rows = 2
    pad = 12
    header_h = 40
    cell_pad_bottom = 22
    cell_w = cell * zoom
    cell_h = cell * zoom
    total_w = pad * (cols + 1) + cols * cell_w
    total_h = header_h + pad * (rows + 1) + rows * (cell_h + cell_pad_bottom)

    gif_frames = []
    for fi in range(8):
        canvas = Image.new('RGBA', (total_w, total_h), (16, 14, 20, 255))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([0, 0, total_w, header_h], fill=(24, 21, 30, 255))
        draw.text((pad, 12), title, fill=(245, 240, 250, 255))

        for d in range(8):
            col = d % cols
            row = d // cols
            x0 = pad + col * (cell_w + pad)
            y0 = header_h + pad + row * (cell_h + cell_pad_bottom + pad)

            draw.rectangle([x0 - 2, y0 - 2, x0 + cell_w + 1, y0 + cell_h + 1],
                           fill=(28, 25, 34, 255), outline=(50, 45, 62, 255))

            fpath = os.path.join(frames_dir, f'd{d:02d}_f{fi:03d}.png')
            if os.path.exists(fpath):
                im = Image.open(fpath).convert('RGBA')
                im = look.apply_outline(im)
                im = look.grade(im)
                im_scaled = im.resize((cell_w, cell_h), Image.Resampling.NEAREST)
                canvas.paste(im_scaled, (x0, y0), im_scaled)

            draw.text((x0 + 4, y0 + cell_h + 4), DIR_NAMES[d], fill=(180, 175, 195, 255))

        gif_frames.append(canvas.convert('P', palette=Image.Palette.ADAPTIVE))

    os.makedirs(os.path.dirname(out_gif_path), exist_ok=True)
    gif_frames[0].save(out_gif_path, save_all=True, append_images=gif_frames[1:], duration=duration, loop=0)
    print(f"[OK] Generated {out_gif_path}")


def extract_git_file(commit_ref, repo_path, out_file):
    cmd = ['git', 'show', f"{commit_ref}:{repo_path}"]
    with open(out_file, 'wb') as f:
        res = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)
    if res.returncode != 0:
        raise RuntimeError(f"Failed to extract {commit_ref}:{repo_path}: {res.stderr.decode()}")


def main():
    target_dir = r"walkthroughs\08-standardize-character-shaders\assets"
    tmp_dir = r"tools\tmp_build_collages"
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(tmp_dir, exist_ok=True)

    print("=== 1. GENERANDO COLLAGES DE HÉROE (MONSTER) ===")
    # Conf 1: Héroe In-place Base (00-setup)
    c1_path = os.path.join(tmp_dir, "hero_raw_inplace.png")
    extract_git_file("2c383df", "assets/characters/monster/monster_walk_inplace.png", c1_path)
    make_collage_from_sheet(c1_path, os.path.join(target_dir, "hero_conf1_raw_inplace.gif"),
                            "Heroe: Conf 1 (In-place Base, Sin Grade Ni Outline Fuerte)")

    # Conf 2: Héroe Crisp/Outline Clásico (Hito 00)
    c2_path = os.path.join(tmp_dir, "hero_readable.png")
    extract_git_file("2c383df", "assets/characters/monster/monster_walk_readable.png", c2_path)
    make_collage_from_sheet(c2_path, os.path.join(target_dir, "hero_conf2_outline_antiguo.gif"),
                            "Heroe: Conf 2 (Outline 1px Antiguo, Brecha de Sub-Umbral Alfa)")

    # Conf 3: Héroe Actual Pulido (e30, Anti-Erosión)
    c3_path = r"assets\characters\monster\player_e30.png"
    make_collage_from_sheet(c3_path, os.path.join(target_dir, "hero_conf3_anti_erosion_actual.gif"),
                            "Heroe: Conf 3 (Definitivo e30: PBR + Solid Outline Anti-Erosión)")

    print("\n=== 2. GENERANDO COLLAGES DE CARGADOR (CHARGER) ===")
    # Conf 1: Escala 1.0x Base, cabeza encorvada
    make_collage_from_frames(r"assets\render_runs\0_in_game_current",
                             os.path.join(target_dir, "charger_conf1_scale100_base.gif"),
                             "Cargador: Conf 1 (Escala 1.0x Base, Cabeza Oculta)")

    # Conf 2: Escala 1.35x + Cuello +20° + PBR Textura Completa
    make_collage_from_frames(r"assets\render_runs\A_original",
                             os.path.join(target_dir, "charger_conf2_scale135_original.gif"),
                             "Cargador: Conf 2 (Escala 1.35x + Cuello +20° + Textura Base)")

    # Conf 3: Escala 1.35x + Normal 15% + Contraste Tonal Limpio
    make_collage_from_frames(r"assets\render_runs\B_contrast_clean",
                             os.path.join(target_dir, "charger_conf3_contrast_clean.gif"),
                             "Cargador: Conf 3 (Normal 15% + Contraste Limpio)")

    # Conf 4: Escala 1.35x + Fauces/Cuernos Glow 5x
    make_collage_from_frames(r"assets\render_runs\C_contrast_horns_glow",
                             os.path.join(target_dir, "charger_conf4_horns_glow.gif"),
                             "Cargador: Conf 4 (Ramp Óseo + Glow Fauces 5x)")

    # Conf 5: Opción A+ Pulida (Definitiva en juego)
    make_collage_from_frames(r"assets\render_runs\A_plus_colors",
                             os.path.join(target_dir, "charger_conf5_option_aplus_actual.gif"),
                             "Cargador: Conf 5 (Opcion A+ Definitiva: Normal 30% + Fill 0.75 + Fauces 2x)")

    print("\n=== 3. GENERANDO COLLAGES DE ESQUELETO (SKELETON) ===")
    # Conf 1: Esqueleto Blanco Original (Huesos finos, silueta plana rota)
    sk1_path = os.path.join(tmp_dir, "skeleton_white_orig.png")
    extract_git_file("4244047", "assets/characters/skeleton/skeleton_e30.png", sk1_path)
    make_collage_from_sheet(sk1_path, os.path.join(target_dir, "skeleton_conf1_white_raw.gif"),
                            "Esqueleto: Conf 1 (Blanco Plano Original, Sin Displace, Huesos Rotos)")

    # Conf 2: Esqueleto Engrosado + Color Base Marfil (Sin AO cavidades profundas)
    sk2_path = os.path.join(tmp_dir, "skeleton_fatten_base.png")
    extract_git_file("0fa57ae", "assets/characters/skeleton/skeleton_e30.png", sk2_path)
    make_collage_from_sheet(sk2_path, os.path.join(target_dir, "skeleton_conf2_fatten_marfil.gif"),
                            "Esqueleto: Conf 2 (Displace 0.12 + Marfil Estandar, AO Suave)")

    # Conf 3: Esqueleto Chiaroscuro Dramático (Definitivo en juego)
    sk3_path = r"assets\characters\skeleton\skeleton_e30.png"
    make_collage_from_sheet(sk3_path, os.path.join(target_dir, "skeleton_conf3_dramatic_chiaroscuro_actual.gif"),
                            "Esqueleto: Conf 3 (Definitivo: Vertex Color Anatomico + Cavity AO Ramp)")

    # Limpieza
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print("\n[TODOS LOS COLLAGES DE 8 DIRECCIONES GENERADOS EXITOSAMENTE]")


if __name__ == "__main__":
    main()
