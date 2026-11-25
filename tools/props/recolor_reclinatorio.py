"""Recolor del reclinatorio (ronda v2, variante C): madera casi negra de marron frio y herrajes/cruz en plata fria.
La textura es un atlas unico (sin materiales separados), asi que se recolorea por zonas de color/luminancia.
uso: python tools/props/recolor_reclinatorio.py <in.glb> <out.glb>"""
import io, json, struct, sys
import numpy as np
from PIL import Image

def main(src, dst):
    b = bytearray(open(src, "rb").read())
    jl = struct.unpack_from("<I", b, 12)[0]
    js = json.loads(b[20:20 + jl])
    bo = 20 + jl
    bl = struct.unpack_from("<I", b, bo)[0]
    binb = bytearray(b[bo + 8:bo + 8 + bl])
    bv = js["bufferViews"][js["images"][0]["bufferView"]]
    img = np.array(Image.open(io.BytesIO(bytes(binb[bv["byteOffset"]:bv["byteOffset"] + bv["byteLength"]]))).convert("RGB")).astype(np.float32)
    r, g, bb = img[..., 0], img[..., 1], img[..., 2]
    L = 0.30 * r + 0.59 * g + 0.11 * bb
    cush = (r > g * 1.5) & (r > bb * 1.2)
    metal = np.clip((L - 80) / 22, 0, 1)                      # claros (cruz, clavos, hueso)
    metal = np.maximum(metal, np.clip((bb - r - 4) / 8, 0, 1) * (L > 60))   # correas gris azuladas
    wood = (np.array([20, 18, 20], np.float32) + (L * 0.22)[..., None] * np.array([1.0, 0.94, 0.96], np.float32))
    sil = np.clip(185 + (L - 100) * 0.7, 185, 245)[..., None] * np.array([0.93, 0.97, 1.03], np.float32)
    out = wood * (1 - metal[..., None]) + sil * metal[..., None]
    # cojin: granate/carmin frio (sombra #4a0c1c, medio #9a1a2e, luz #c8354a; compensa el tinte ambar de la sala) segun la luminancia original
    t = np.clip((L - 30) / 70, 0, 1)[..., None]
    sh, md, li = (np.array(c, np.float32) for c in ((80, 0, 20), (125, 0, 28), (165, 0, 38)))
    red = np.where(t < 0.5, sh + (md - sh) * (t * 2), md + (li - md) * ((t - 0.5) * 2))
    out = np.where(cush[..., None], red, out)
    buf = io.BytesIO(); Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(buf, "JPEG", quality=95)
    data = buf.getvalue()
    while len(binb) % 4: binb.append(0)
    bv["byteOffset"] = len(binb); bv["byteLength"] = len(data)
    binb += data
    while len(binb) % 4: binb.append(0)
    js["buffers"][0]["byteLength"] = len(binb)
    jb = json.dumps(js, separators=(",", ":")).encode()
    while len(jb) % 4: jb += b" "
    total = 12 + 8 + len(jb) + 8 + len(binb)
    open(dst, "wb").write(struct.pack("<4sII", b"glTF", 2, total) + struct.pack("<I4s", len(jb), b"JSON") + jb + struct.pack("<I4s", len(binb), b"BIN\0") + binb)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
