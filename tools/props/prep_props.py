"""Blender prep: import Tripo FBX, drop loose junk, apply yaw, export GLB.
usage: blender -b -P prep_props.py -- <repo_root> [piece ...]  (yaw/override via env PROP_YAW_<name>)
"""
import bpy, bmesh, sys, os, json, math
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--")+1:]
root = argv[0]
only = argv[1:]
cfg = json.load(open(os.path.join(root, "tools/props/props.json")))
src = os.path.join(root, "assets/environment/cathedral/props")
out = os.path.join(src, "glb")
os.makedirs(out, exist_ok=True)

def components(bm):
    seen = set(); comps = []
    for v in bm.verts:
        if v.index in seen: continue
        stack = [v]; seen.add(v.index); c = []
        while stack:
            a = stack.pop(); c.append(a)
            for e in a.link_edges:
                b = e.other_vert(a)
                if b.index not in seen: seen.add(b.index); stack.append(b)
        comps.append(c)
    return comps

for name, c in cfg.items():
    if only and name not in only: continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=os.path.join(src, c["fbx"]))
    obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if c.get("loose_filter"):
        bm = bmesh.new(); bm.from_mesh(obj.data)
        comps = components(bm)
        # Tripo "vela": the candles + wax puddle are the largest connected component; the
        # sandbag/barbed-wire fragments are two smaller loose parts (checked by bbox + render).
        comps.sort(key=len, reverse=True)
        for comp in comps[:8]: print("COMP verts", len(comp))
        print("total components", len(comps))
        drop = [v for comp in comps[1:] for v in comp]
        print("dropping verts", len(drop), "of", len(bm.verts))
        bmesh.ops.delete(bm, geom=drop, context='VERTS')
        bm.to_mesh(obj.data); bm.free()
    # yaw about Z (Blender), applied, then drop to ground at origin
    # optional "pitch" (X, degrees) lays down models that Tripo built standing up
    if c.get("align_slab"):
        # Flat slabs from Tripo can come tilted and turned inside their own frame: after the pitch,
        # level the slab (smallest-variance axis -> +Z, keeping the side that faced up) and turn its
        # long side onto X (minimum-area bounding rectangle), so "yaw" then works like for the rest.
        import numpy as np
        obj.rotation_euler = (math.radians(c.get("pitch", 0)), 0, 0)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        P = np.array([v.co[:] for v in obj.data.vertices])
        P0 = P - P.mean(axis=0)
        w, V = np.linalg.eigh(P0.T @ P0)
        n = V[:, 0] if V[2, 0] >= 0 else -V[:, 0]
        q = Vector(n.tolist()).rotation_difference(Vector((0, 0, 1)))
        obj.rotation_mode = 'QUATERNION'; obj.rotation_quaternion = q
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        obj.rotation_mode = 'XYZ'
        XY = np.array([v.co[:2] for v in obj.data.vertices])
        best = min(((np.ptp(XY @ np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]]), axis=0).prod(), a)
                    for a in np.radians(np.arange(0, 90, 0.25))))
        ang = best[1]
        R = XY @ np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]])
        if np.ptp(R[:, 1]) > np.ptp(R[:, 0]): ang += math.pi / 2
        ang += math.radians(c.get("slab_turn", 0))
        print(name, "align_slab: normal", np.round(n, 3).tolist(), "turn", round(math.degrees(ang), 2))
        obj.rotation_euler = (0, 0, -ang)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        obj.rotation_euler = (0, 0, math.radians(c["yaw"]))
    else:
        obj.rotation_euler = (math.radians(c.get("pitch", 0)), 0, math.radians(c["yaw"]))
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if c.get("top_only"):
        # Floor-level pieces (tombstones): keep only the upward-facing surface, so no side or
        # thickness is drawn and the slab reads flush with the floor.
        bm = bmesh.new(); bm.from_mesh(obj.data)
        side = [f for f in bm.faces if f.normal.z < 0.5]
        bmesh.ops.delete(bm, geom=side, context='FACES')
        bm.to_mesh(obj.data); bm.free()
        print(name, "top_only: removed faces", len(side))
    vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
    mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    obj.location = Vector((-(mn.x+mx.x)/2, -(mn.y+mx.y)/2, -mn.z))
    bpy.ops.object.transform_apply(location=True)
    print(name, "dims", [round(x,3) for x in (mx-mn)])
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, name + ".glb"), export_format='GLB',
                              export_yup=True, export_image_format='AUTO', export_materials='EXPORT')
