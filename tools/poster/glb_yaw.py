#!/usr/bin/env python3
"""Copia un GLB girado sobre la vertical (glTF: eje Y) sin Blender. El giro se hornea en los vertices y normales
(sin nodos con transformacion), asi lo leen igual el lab y la sombra (prop_shadows.read_glb).
uso: python tools/poster/glb_yaw.py <entrada.glb> <salida.glb> <grados>"""
import json, math, struct, sys


def main(src, dst, deg):
    b = bytearray(open(src, "rb").read())
    jl = struct.unpack_from("<I", b, 12)[0]
    js = json.loads(b[20:20 + jl])
    bo = 20 + jl + 8                                     # inicio del bloque binario
    a = math.radians(float(deg))
    c, s = math.cos(a), math.sin(a)
    done = set()
    for m in js["meshes"]:
        for p in m["primitives"]:
            for key in ("POSITION", "NORMAL"):
                i = p["attributes"].get(key)
                if i is None or i in done:
                    continue
                done.add(i)
                acc = js["accessors"][i]
                bv = js["bufferViews"][acc["bufferView"]]
                stride = bv.get("byteStride", 12)
                off = bo + bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
                lo, hi = [1e30] * 3, [-1e30] * 3
                for k in range(acc["count"]):
                    x, y, z = struct.unpack_from("<3f", b, off + k * stride)
                    x, z = c * x + s * z, -s * x + c * z          # giro sobre Y
                    struct.pack_into("<3f", b, off + k * stride, x, y, z)
                    for j, v in enumerate((x, y, z)):
                        lo[j] = min(lo[j], v); hi[j] = max(hi[j], v)
                if "min" in acc:
                    acc["min"], acc["max"] = lo, hi
    jb = json.dumps(js, separators=(",", ":")).encode()
    jb += b" " * (-len(jb) % 4)
    rest = bytes(b[20 + jl:])
    out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(jb) + len(rest)) + struct.pack("<II", len(jb), 0x4E4F534A) + jb + rest
    open(dst, "wb").write(out)


if __name__ == "__main__":
    main(*sys.argv[1:4])
