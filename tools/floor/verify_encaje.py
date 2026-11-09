#!/usr/bin/env python3
"""Numerically verify periodic encaje, mud height identity, and border clearance."""
import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "assets/models/environment/floor_proc"


def quat_to_mat(q):
    """Convert [x, y, z, w] quaternion to 3x3 rotation matrix."""
    x, y, z, w = q
    return np.array([
        [1 - 2*(y*y + z*z),     2*(x*y - z*w),     2*(x*z + y*w)],
        [    2*(x*y + z*w), 1 - 2*(x*x + z*z),     2*(y*z - x*w)],
        [    2*(x*z - y*w),     2*(y*z + x*w), 1 - 2*(x*x + y*y)],
    ], dtype=np.float32)


def parse_glb(path):
    data = Path(path).read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data)
    jl = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20 + jl].decode("utf-8").rstrip(" \0"))
    bin_offset = 20 + jl + 8

    def get_accessor(acc_idx):
        acc = gltf["accessors"][acc_idx]
        bv = gltf["bufferViews"][acc["bufferView"]]
        start = bin_offset + bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        count = acc["count"]
        dtype = np.float32
        arr = np.frombuffer(data[start:start + count * 12], dtype=dtype).reshape(count, 3)
        return arr

    return gltf, get_accessor


def verify_glb(glb_path):
    gltf, get_acc = parse_glb(glb_path)
    tag = Path(glb_path).stem
    print(f"\n--- Verifying {tag} ---")

    mud_edge_err = None
    mud_vertices = None
    non_walkway_violations = []
    walkway_z_min = 999.0
    walkway_z_max = -999.0

    for node in gltf.get("nodes", []):
        m_idx = node.get("mesh")
        if m_idx is None:
            continue
        mesh = gltf["meshes"][m_idx]
        node_name = node.get("name", "")
        mesh_name = mesh.get("name", "")
        name = node_name or mesh_name

        for prim in mesh["primitives"]:
            pos = get_acc(prim["attributes"]["POSITION"]).copy()
            # Apply node transform: scale -> rotation -> translation
            if "scale" in node:
                pos *= np.array(node["scale"], dtype=np.float32)
            if "rotation" in node:
                R = quat_to_mat(node["rotation"])
                pos = (R @ pos.T).T
            if "translation" in node:
                pos += np.array(node["translation"], dtype=np.float32)

            if "mud ground" in name.lower() or "periodic mud" in name.lower():
                mud_vertices = pos
                # In glTF, Z is along the depth of the band (-3.168 to +3.168)
                z_coords = pos[:, 2]
                z_min, z_max = z_coords.min(), z_coords.max()
                top_mask = np.abs(z_coords - z_max) < 1e-4
                bot_mask = np.abs(z_coords - z_min) < 1e-4
                top_v = pos[top_mask]
                bot_v = pos[bot_mask]
                top_v = top_v[np.argsort(top_v[:, 0])]
                bot_v = bot_v[np.argsort(bot_v[:, 0])]
                if len(top_v) == len(bot_v) and len(top_v) > 0:
                    diff = np.abs(top_v[:, 1] - bot_v[:, 1])
                    mud_edge_err = float(diff.max())
                else:
                    mud_edge_err = float("inf")
            elif any(w in name.lower() for w in ["walkway", "panel", "batten", "branch"]):
                walkway_z_min = min(walkway_z_min, float(pos[:, 2].min()))
                walkway_z_max = max(walkway_z_max, float(pos[:, 2].max()))
            else:
                # Non-walkway object: must be at least 0.50m away from borders (|Z| <= 2.668m)
                z_abs = np.abs(pos[:, 2])
                if np.any(z_abs > 2.668):
                    violating_max = float(z_abs.max())
                    non_walkway_violations.append((name, violating_max))

    if mud_vertices is not None:
        print(f"  Mud bounds: X=[{mud_vertices[:, 0].min():.3f}, {mud_vertices[:, 0].max():.3f}], Z=[{mud_vertices[:, 2].min():.3f}, {mud_vertices[:, 2].max():.3f}] m")
    print(f"  Mud self-periodicity max height error: {mud_edge_err:.12e} m")
    print(f"  Non-walkway border violations (|Z| > 2.668m): {len(non_walkway_violations)}")
    if non_walkway_violations:
        for v in non_walkway_violations[:5]:
            print(f"    VIOLATION: {v[0]} reached |Z|={v[1]:.3f} m (>2.668 m)")
    print(f"  Walkway Z span: [{walkway_z_min:.3f}, {walkway_z_max:.3f}] m (boundary is +/- 3.168 m)")

    return {
        "tag": tag,
        "mud_edge_err": mud_edge_err,
        "mud_vertices": mud_vertices,
        "violations": len(non_walkway_violations),
        "walkway_span": (walkway_z_min, walkway_z_max),
    }


def main():
    glbs = sorted(PROC.glob("floor_band_*.glb"))
    if not glbs:
        print("No floor_band_*.glb found to verify.")
        return

    results = []
    for g in glbs:
        results.append(verify_glb(g))

    print("\n=== Cross-Variant Mud Mesh Consistency ===")
    base_mud = results[0]["mud_vertices"]
    all_mud_match = True
    for r in results[1:]:
        if r["mud_vertices"] is not None and base_mud is not None:
            diff = np.abs(r["mud_vertices"] - base_mud).max()
            print(f"  Diff between {results[0]['tag']} and {r['tag']}: {diff:.12e} m")
            if diff > 1e-5:
                all_mud_match = False
    if all_mud_match:
        print("  PASS: Mud relief mesh is strictly IDENTICAL across all variants!")
    else:
        print("  FAIL: Mud relief mesh differs between variants!")


if __name__ == "__main__":
    main()
