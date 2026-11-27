#!/usr/bin/env python3
"""Compose one single-variant GIF (4x NEAREST, 60 ms) + contact sheet per gallery effect."""
import json, sys
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).parent))
from abc_gif import variant_frames, BOTTOM_Y
ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / ".ds-game-dev" / "g"
OUT = ROOT / "walkthroughs" / "galeria-vfx" / "assets"
C = (100, 62, 128, 96)
# nn, name, relic, run, scenario, variant, crop, description
E = [
 ("01", "enemigo_quemado_A", "(estado quemado)", "burn", "abc_burn", 0, (96, 62, 128, 96), "Brasas y lenguas sobre tres enemigos con 1, 2 y 4 capas de quemadura."),
 ("02", "enemigo_quemado_B", "(estado quemado)", "burn", "abc_burn", 1, (96, 62, 128, 96), "Corona de llamas a los pies de tres enemigos con 1, 2 y 4 capas."),
 ("03", "auto_de_fe_A", "Auto de Fe", "autofe", "galeria_abc_autofe", 0, (108, 62, 128, 96), "Carga, disparo sobre enemigo quemado y chispas al impactar."),
 ("04", "auto_de_fe_C", "Auto de Fe", "autofe", "galeria_abc_autofe", 2, (108, 62, 128, 96), "Corona de llamas a los pies; el disparo la consume y sube evaporandose."),
 ("05", "llama_votiva_B", "Llama Votiva", "votiva", "galeria_abc_votiva", 1, (100, 62, 128, 96), "Chispas que giran irregulares en la linea de apuntado durante la carga."),
 ("06", "corazon_flagelado_A", "Corazon Flagelado", "flagelado", "abc_flagelado", 0, (64, 62, 128, 96), "Onda en anillo grande alrededor del heroe que alcanza a los enemigos."),
 ("07", "martirio_contagioso_A", "Martirio Contagioso", "martirio", "galeria_abc_martirio", 0, (100, 62, 128, 96), "Disparo a un enemigo quemado: estalla y el anillo contagia a los vecinos."),
 ("08", "llaga_abierta_B", "Llaga Abierta", "llaga", "abc_llaga", 1, (88, 66, 80, 76), "Heroe teñido de dorado palido con sangre que gotea, a 4, 3, 2 y 1 corazones."),
 ("09", "viatico_A", "Viatico", "viatico", "galeria_abc_viatico", 0, (112, 58, 96, 60), "Hilo de sangre que sale del enemigo muerto y fluye al pecho del heroe."),
 ("10", "viatico_C", "Viatico", "viatico", "galeria_abc_viatico", 2, (112, 58, 96, 60), "Alma palida que sale del enemigo muerto y entra en el heroe."),
 ("11", "aura_E_cilicio", "Aura de Cilicio", "aura_E", "galeria_aura_E", 0, C, "Corona de espinas en el suelo durante la carga; el aro quema al enemigo; disparo."),
 ("12", "aura_H_ceniza", "Sed de Ceniza", "aura_H", "galeria_aura_H", 0, C, "Ceniza alrededor del heroe durante la carga y disparo."),
 ("13", "aura_G_gloria", "Viatico", "aura_G", "galeria_aura_G", 0, C, "Gloria (halo) durante la carga y disparo."),
 ("14", "aura_L_llamas", "Corazon Flagelado", "aura_L", "galeria_aura_L", 0, C, "Llamas alrededor del heroe durante la carga y disparo."),
 ("15", "rayo_base", "(ninguna)", "rayo", "galeria_rayo_base", 0, C, "Carga y disparo del rayo base (haz fuego) sin reliquias."),
]
OUT.mkdir(parents=True, exist_ok=True)
idx = []
for nn, name, relic, run, scn, vi, (x, y, w, h), desc in E:
    SC = 6 if run == "viatico" else 4
    files = variant_frames(RUNS / f"out_{run}", vi)
    frames = [Image.open(f).convert("RGB").crop((x, BOTTOM_Y + y, x + w, BOTTOM_Y + y + h)).resize((w * SC, h * SC), Image.NEAREST) for f in files]
    n = len(frames)
    sample = Image.new("RGB", (w * SC, h * SC * len(frames[::max(1, n // 8)])))
    for k, f in enumerate(frames[::max(1, n // 8)]): sample.paste(f, (0, k * h * SC))
    pal = sample.quantize(colors=96, dither=Image.Dither.NONE)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    plt = pal.getpalette(); bg = q[0].getpixel((0, 0))
    alt = min((i for i in range(96) if i != bg), key=lambda i: sum((plt[3*i+k]-plt[3*bg+k])**2 for k in range(3)))
    for i, f in enumerate(q): f.putpixel((w * SC - 1, 0), alt if i & 1 else bg)
    gif = OUT / f"{nn}_{name}.gif"
    q[0].save(gif, save_all=True, append_images=q[1:], duration=60, loop=0, optimize=True, disposal=1)
    pick = [frames[round(i * (n - 1) / 7)] for i in range(8)]
    cs = Image.new("RGB", (4 * w * 2, 2 * h * 2))
    for i, f in enumerate(pick): cs.paste(f.resize((w * 2, h * 2), Image.NEAREST), ((i % 4) * w * 2, (i // 4) * h * 2))
    cs.save(OUT / f"contacto_{name}.png")
    print(gif.name, n, "frames", gif.stat().st_size // 1024, "KB")
    idx.append({"archivo": gif.name, "nombre": name, "reliquia": relic, "variante": "ABC"[vi] if run.startswith(("burn","autofe","votiva","flagelado","martirio","llaga","viatico")) else "-",
                "que_se_ve": desc, "escenario": f"scenarios/{scn}.json" + (f" (dv={vi})" if "abc_" in scn else "")})
(OUT / "index.json").write_text(json.dumps(idx, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
