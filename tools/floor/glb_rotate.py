#!/usr/bin/env python3
"""Rotate a GLB about Y by wrapping its scene roots in a new node (used to view floors axis-aligned in the lab)."""
import json
import math
import struct
import sys
from pathlib import Path


def rotate_glb_y(src, dst, degrees):
    data = Path(src).read_bytes()
    jl = struct.unpack("<I", data[12:16])[0]
    gltf = json.loads(data[20:20 + jl])
    rest = data[20 + jl:]
    scene = gltf["scenes"][gltf.get("scene", 0)]
    half = math.radians(degrees) / 2
    gltf["nodes"].append({"name": "yaw", "rotation": [0, math.sin(half), 0, math.cos(half)], "children": list(scene["nodes"])})
    scene["nodes"] = [len(gltf["nodes"]) - 1]
    jb = json.dumps(gltf, separators=(",", ":")).encode()
    jb += b" " * (-len(jb) % 4)
    Path(dst).write_bytes(data[:8] + struct.pack("<I", 12 + 8 + len(jb) + len(rest)) + struct.pack("<I", len(jb)) + data[16:20] + jb + rest)


if __name__ == "__main__":
    rotate_glb_y(sys.argv[1], sys.argv[2], float(sys.argv[3]))
