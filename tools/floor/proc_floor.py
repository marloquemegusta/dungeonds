"""Blender worker for a full-lane trench floor band with variants."""
import json
import math
import random
import sys
import struct
import zlib
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Vector


WIDTH = 11.88
HEIGHT = 6.336
SPACING = 0.024


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for item in list(datablocks):
            if item.users == 0:
                datablocks.remove(item)


def material(name, rgba, roughness=0.92):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgba, 1.0)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgba, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def write_png_rgb(path, pixels):
    height, width, _ = pixels.shape
    raw = b"".join(b"\0" + pixels[row].astype(np.uint8).tobytes() for row in range(height))
    def chunk(kind, payload):
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)
    header = struct.pack(">2I5B", width, height, 8, 2, 0, 0, 0)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) +
                           chunk(b"IDAT", zlib.compress(raw, 7)) + chunk(b"IEND", b""))


def make_wood_atlas(path, seed, variants, look="w05"):
    rng = np.random.default_rng(seed ^ 0x71A1B04D)
    size, cell, inset = 512, 256, 7
    atlas = np.zeros((size, size, 3), dtype=np.uint8)
    yy, xx = np.mgrid[0:cell, 0:cell]
    u, v = xx / (cell-1), yy / (cell-1)
    if look == "v04":
        palette = [(27, 29, 32), (18, 20, 22), (38, 40, 42), (25, 27, 28)]
    else:
        # w05: darker, less blue-gray, damp umber tones
        palette = [(32, 35, 36), (22, 24, 25), (42, 44, 45), (28, 30, 29)]

    for variant in range(variants):
        phase = rng.uniform(0, 2*np.pi)
        noise = rng.normal(0, 2.5, (cell, cell))
        lateral = u * rng.uniform(8.0, 14.0) + .10*np.sin(v*2*np.pi*rng.uniform(1.0,2.5)+phase)
        grain = 6.5*np.sin(lateral*2*np.pi + phase) + 3.0*np.sin(lateral*2*np.pi*2.4 + phase*.7)
        fibers = (np.clip(np.sin(lateral * 6 * np.pi + phase * 1.5), 0, 1) ** 2) * (10.0 if look == "v04" else 7.0)
        strip_pos = rng.uniform(0.25, 0.75)
        strip = np.exp(-((u - strip_pos) / 0.09) ** 2) * (8.0 if look == "v04" else 5.5)
        damp = np.zeros((cell,cell), dtype=np.float64)
        for _ in range(8):
            kx, ky = rng.uniform(.05,.95), rng.uniform(.03,.97)
            rx, ry = rng.uniform(.035,.13), rng.uniform(.025,.14)
            blob = ((u-kx)/rx)**2 + ((v-ky)/ry)**2
            damp = np.maximum(damp, np.exp(-blob*1.7)*rng.uniform(3,10))
        value = noise + grain + fibers + strip - damp
        base = np.array(palette[variant], dtype=np.float64)
        tile = np.empty((cell,cell,3), dtype=np.float64)
        for c in range(3):
            tile[:,:,c] = base[c] + value
        for _ in range(5):
            x0 = rng.uniform(.05,.95)
            wav = x0 + .012*np.sin(v*rng.uniform(8,25)+rng.uniform(0,6.28))
            crack = np.exp(-((u-wav)/rng.uniform(.002,.008))**2) * rng.uniform(14,24)
            tile -= crack[:,:,None] * np.array([.95,.95,1.0])[None,None,:]
        for _ in range(2):
            kx, ky = rng.uniform(.12,.88), rng.uniform(.12,.88)
            r = np.sqrt(((u-kx)/rng.uniform(.025,.055))**2 + ((v-ky)/rng.uniform(.018,.04))**2)
            rings = np.exp(-((r-1.0)/.12)**2) * 11 + np.exp(-(r/.33)**2)*14
            tile -= rings[:,:,None] * np.array([.95,.96,1.0])[None,None,:]
        edge = np.maximum(np.exp(-(u/.045)**2), np.exp(-((1-u)/.045)**2))
        end = np.maximum(np.exp(-(v/.035)**2), np.exp(-((1-v)/.035)**2))
        tile += (edge*7 + end*4)[:,:,None] * np.array([.88,.92,.98])[None,None,:]
        tile[:,:,0] += np.sin(v*13 + phase) * 0.8
        tile[:,:,1] += damp * .14
        tile[:,:,2] += damp * (.25 if look == "v04" else .16)
        tile = np.clip(tile, 10, 80).astype(np.uint8)
        col, row = variant % 2, variant // 2
        x0, y0 = col*cell+inset, row*cell+inset
        atlas[y0:y0+cell-2*inset, x0:x0+cell-2*inset] = tile[inset:cell-inset,inset:cell-inset]
    for variant in range(variants, 4):
        source = (variant % variants)
        src = atlas[(source//2)*cell:(source//2+1)*cell,(source%2)*cell:(source%2+1)*cell].copy()
        atlas[(variant//2)*cell:(variant//2+1)*cell,(variant%2)*cell:(variant%2+1)*cell] = src
    write_png_rgb(path, atlas)


def periodic_value_noise(width, height, grid_x, grid_y, rng):
    lattice = rng.random((grid_y, grid_x), dtype=np.float32)
    x = np.arange(width, dtype=np.float32) * (grid_x / width)
    y = np.arange(height, dtype=np.float32) * (grid_y / height)
    x0 = np.floor(x).astype(np.int32); y0 = np.floor(y).astype(np.int32)
    fx = x - x0; fy = y - y0
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    a = lattice[y0[:, None] % grid_y, x0[None, :] % grid_x]
    b = lattice[y0[:, None] % grid_y, (x0[None, :] + 1) % grid_x]
    c = lattice[(y0[:, None] + 1) % grid_y, x0[None, :] % grid_x]
    d = lattice[(y0[:, None] + 1) % grid_y, (x0[None, :] + 1) % grid_x]
    top = a + (b - a) * fx[None, :]
    bottom = c + (d - c) * fx[None, :]
    return top + (bottom - top) * fy[:, None]


def muddy_material(path):
    mat = material("Procedural trench mud", (.9, .9, .9), .96)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(path), check_existing=True)
    tex.image.pack()
    tex.interpolation = "Linear"
    uv = mat.node_tree.nodes.new("ShaderNodeTexCoord")
    mat.node_tree.links.new(uv.outputs["UV"], tex.inputs["Vector"])
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def image_material(name, path, roughness=.92, base=(.82, .82, .82)):
    mat = material(name, base, roughness)
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(path), check_existing=True)
    tex.image.pack()
    tex.interpolation = "Linear"
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def wrapped_delta(delta, period):
    return (delta + period * 0.5) % period - period * 0.5


def make_height(mud_seed, nx, ny):
    """Generate fixed base mud relief, strictly periodic in Y and identical for all variants."""
    rng = np.random.default_rng(mud_seed)
    xs = np.linspace(-WIDTH * .5, WIDTH * .5, nx + 1, dtype=np.float64)
    ys = np.linspace(-HEIGHT * .5, HEIGHT * .5, ny + 1, dtype=np.float64)
    xx, yy = np.meshgrid(xs, ys)
    phase = rng.uniform(0, 2 * np.pi, 10)
    # Integer wave counts in Y ensure exact periodicity along Y.
    z = (0.0045 * np.sin(2 * np.pi * (3 * xx / WIDTH + 2 * yy / HEIGHT) + phase[0])
         + 0.0030 * np.sin(2 * np.pi * (7 * xx / WIDTH - 3 * yy / HEIGHT) + phase[1])
         + 0.0022 * np.cos(2 * np.pi * (11 * xx / WIDTH + 8 * yy / HEIGHT) + phase[2])
         + 0.0015 * np.sin(2 * np.pi * (17 * xx / WIDTH - 11 * yy / HEIGHT) + phase[3]))

    # Clods
    for gx, gy, amp in ((80, 53, .003), (145, 97, .0025)):
        fine = periodic_value_noise(nx, ny, gx, gy, rng)
        z[:-1, :-1] += (fine - .5) * amp * 2
    z[-1, :] = z[0, :]

    # Subtle wheel trails along Y
    for side, cx in ((-1, -2.4), (-1, -1.8), (1, 1.8), (1, 2.4)):
        direction = rng.uniform(-.08, .08)
        dy = wrapped_delta(yy, HEIGHT)
        dx = xx - (cx + direction * dy)
        d = np.abs(dx)
        trough = np.exp(-((d / .085) ** 4))
        z -= 0.0040 * trough

    # Ensure strictly exact match between top and bottom row
    z[-1, :] = z[0, :]
    return xs, ys, z


def build_base(xs, ys, z, mud_path, tex_span=3.168, mud_source="image"):
    ny, nx = z.shape[0] - 1, z.shape[1] - 1
    verts = []
    uvcoords = []
    # span_y = 3.168m: exactly 2.0 repeats in Y over HEIGHT=6.336m
    rep_y = max(1, round(HEIGHT / tex_span))
    span_y = HEIGHT / rep_y
    span_x = span_y
    for j, y in enumerate(ys):
        v = float((y + HEIGHT * 0.5) / span_y)
        for i, x in enumerate(xs):
            u = float((x + WIDTH * 0.5) / span_x)
            verts.append((float(x), float(y), float(z[j, i])))
            uvcoords.append((u, v))

    faces = []
    for j in range(ny):
        row = j * (nx + 1)
        nxt = row + nx + 1
        for i in range(nx):
            a = row + i
            faces.append((a, a + 1, nxt + i + 1, nxt + i))
    mesh = bpy.data.meshes.new("Periodic mud relief mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    uv_layer = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            uv_layer.data[li].uv = uvcoords[mesh.loops[li].vertex_index]
    obj = bpy.data.objects.new("Mud ground | full lane band", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(muddy_material(mud_path))
    return obj


def add_bevelled_box(name, location, dimensions, rotation, mat, bevel):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.rotation_euler = rotation
    if bevel > 0:
        mod = obj.modifiers.new("Worn softened edges", "BEVEL")
        mod.width = bevel
        mod.segments = 1
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.data.materials.append(mat)
    return obj


def add_ico(name, location, scale, mat, rng):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1, location=location)
    obj = bpy.context.object
    obj.name = name
    for vert in obj.data.vertices:
        jitter = rng.uniform(.78, 1.20)
        vert.co *= jitter
    obj.scale = scale
    obj.rotation_euler = tuple(rng.uniform(-.3, .3) for _ in range(3))
    obj.data.materials.append(mat)
    return obj


def add_cylinder(name, location, radius, depth, mat, rng, vertices=8):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = (rng.uniform(-.5, .5), rng.uniform(-.5, .5), rng.uniform(0, math.pi))
    obj.data.materials.append(mat)
    return obj


def sample_height(xs, ys, z, x, y):
    nx, ny = len(xs) - 1, len(ys) - 1
    fx = np.clip((x + WIDTH * .5) / WIDTH * nx, 0, nx)
    fy = np.clip((y + HEIGHT * .5) / HEIGHT * ny, 0, ny)
    ix, iy = int(round(fx)) % (nx + 1), int(round(fy)) % (ny + 1)
    return float(z[iy, ix])


def mesh_object(name, verts, faces, materials, material_ids=None, face_uvs=None, smooth=False):
    mesh = bpy.data.meshes.new(name + " mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    if smooth:
        for poly in mesh.polygons:
            poly.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for mat in materials:
        mesh.materials.append(mat)
    if material_ids:
        for poly, mid in zip(mesh.polygons, material_ids):
            poly.material_index = mid
    if face_uvs:
        layer = mesh.uv_layers.new(name="UVMap")
        for poly, coords in zip(mesh.polygons, face_uvs):
            for li, uv in zip(poly.loop_indices, coords):
                layer.data[li].uv = uv
    return obj


def make_wood_board(name, x, y, center_z, width, length, thick, rotation,
                    variant, atlas_mat, side_mat, edge_mat, rng, broken=False, roll=0.0, pitch=0.0):
    xs_local = [-.5, -.42, 0.0, .42, .5]
    rows = 7
    verts, faces, mids, face_uvs = [], [], [], []
    end_jitter = [rng.uniform(-.024, .024) if broken else rng.uniform(-.008, .008) for _ in xs_local]
    width_jitter = [rng.uniform(.94, 1.06) for _ in range(rows)]
    top_z = []
    for j in range(rows):
        v = j / (rows - 1)
        row_z = []
        for i, xf in enumerate(xs_local):
            factor = width_jitter[j]
            local_x = xf * width * factor
            local_y = (v - .5) * length + end_jitter[i] * ((1 - v) if j == 0 else (v if j == rows - 1 else 0))
            warp = .004 * math.sin(v * math.pi * 2 + rng.uniform(-.10, .10)) + rng.uniform(-.0025, .0025)
            if broken and (j == 0 or j == rows - 1):
                warp += rng.uniform(-.008, .006)
            row_z.append(thick * .5 + warp)
            verts.append((local_x, local_y, thick * .5 + warp))
        top_z.append(row_z)
    col, row = variant % 2, variant // 2
    inset = 7 / 512
    u0, u1 = col * .5 + inset, col * .5 + .5 - inset
    v0, v1 = row * .5 + inset, row * .5 + .5 - inset
    uv_top = []
    for j in range(rows):
        for i in range(len(xs_local)):
            uv_top.append((u0 + (u1 - u0) * i / (len(xs_local) - 1), v0 + (v1 - v0) * j / (rows - 1)))
    for j in range(rows - 1):
        for i in range(len(xs_local) - 1):
            a = j * len(xs_local) + i
            faces.append((a, a + 1, a + len(xs_local) + 1, a + len(xs_local)))
            mids.append(0)
            face_uvs.append((uv_top[a], uv_top[a + 1], uv_top[a + len(xs_local) + 1], uv_top[a + len(xs_local)]))
    left_top, right_top = [], []
    left_bottom, right_bottom = [], []
    for j in range(rows):
        v = j / (rows - 1)
        yloc = (v - .5) * length + (end_jitter[0] * (1 - v) + end_jitter[-1] * v)
        w = width * width_jitter[j]
        left_top.append(len(verts)); verts.append((-.5 * w, yloc, top_z[j][0] - .007))
        right_top.append(len(verts)); verts.append((.5 * w, yloc, top_z[j][-1] - .007))
        left_bottom.append(len(verts)); verts.append((-.5 * w, yloc, -thick * .5))
        right_bottom.append(len(verts)); verts.append((.5 * w, yloc, -thick * .5))
    flat_uv = (u0, v0)
    for j in range(rows - 1):
        a = j * len(xs_local); b = (j + 1) * len(xs_local)
        faces.append((a, left_top[j], left_top[j + 1], b)); mids.append(2); face_uvs.append((flat_uv,) * 4)
        faces.append((a + len(xs_local) - 1, b + len(xs_local) - 1, right_top[j + 1], right_top[j])); mids.append(2); face_uvs.append((flat_uv,) * 4)
        faces.append((left_top[j], left_bottom[j], left_bottom[j + 1], left_top[j + 1])); mids.append(1); face_uvs.append((flat_uv,) * 4)
        faces.append((right_top[j], right_top[j + 1], right_bottom[j + 1], right_bottom[j])); mids.append(1); face_uvs.append((flat_uv,) * 4)
    faces.append((0, 1, 2, 3, 4, left_top[0], left_bottom[0], right_bottom[0], right_top[0])); mids.append(2); face_uvs.append((flat_uv,) * 9)
    end = (rows - 1) * len(xs_local)
    faces.append((end + 4, end + 3, end + 2, end + 1, end, left_top[-1], left_bottom[-1], right_bottom[-1], right_top[-1])); mids.append(2); face_uvs.append((flat_uv,) * 9)
    faces.append((left_bottom[0], left_bottom[-1], right_bottom[-1], right_bottom[0])); mids.append(1); face_uvs.append((flat_uv,) * 4)
    rotation_euler = (roll + rng.uniform(-.02, .02), pitch + rng.uniform(-.02, .02), rotation)
    obj = mesh_object(name, verts, faces, [atlas_mat, side_mat, edge_mat], mids, face_uvs)
    obj.location = (x, y, center_z)
    obj.rotation_euler = rotation_euler
    return obj, rotation_euler, end_jitter


def tube_object(name, components, materials, sides=6):
    verts, faces, mids = [], [], []
    for points, radius, mi in components:
        if len(points) < 2: continue
        start = len(verts)
        vectors = [Vector(p) for p in points]
        for i, p in enumerate(vectors):
            tangent = (vectors[min(i + 1, len(vectors) - 1)] - vectors[max(i - 1, 0)]).normalized()
            side = tangent.cross(Vector((0, 0, 1)))
            if side.length < .01: side = tangent.cross(Vector((0, 1, 0)))
            side.normalize(); up = tangent.cross(side).normalized()
            for k in range(sides):
                a = 2 * math.pi * k / sides
                q = p + radius * (math.cos(a) * side + math.sin(a) * up)
                verts.append(tuple(q))
        for i in range(len(vectors) - 1):
            for k in range(sides):
                a = start + i * sides + k; b = start + i * sides + (k + 1) % sides
                faces.append((a, b, b + sides, a + sides)); mids.append(mi)
        faces.append(tuple(start + k for k in reversed(range(sides)))); mids.append(mi)
        last = start + (len(vectors) - 1) * sides
        faces.append(tuple(last + k for k in range(sides))); mids.append(mi)
    return mesh_object(name, verts, faces, materials, mids)


def make_puddles(task, xs, ys, z, rng, look):
    puddle_count = task.get("puddles", 6)
    water_color = (.025, .038, .030) if look == "w05" else (.030, .032, .028)
    water = material("Turbid water | dark murky olive", water_color, .35)
    glint = material("Water specular reflection highlight", (.24, .28, .26), .20)
    wet = material("Dark wet mud rim | soaked", (.012, .010, .008), .70)
    chip = material("Waterlogged splinter", (.105, .082, .049), .96)

    made = []
    puddles = []
    # Distribute across left flank (X < -1.2) and right flank (X > 1.2), safe Y in [-2.0, 2.0]
    flanks = [(-1, -4.5, -1.35), (1, 1.35, 4.5)]
    attempts = 0
    while len(puddles) < puddle_count and attempts < 100:
        attempts += 1
        side, min_x, max_x = flanks[len(puddles) % 2]
        cx = rng.uniform(min_x, max_x)
        cy = rng.uniform(-2.05, 2.05)
        rx = rng.uniform(.35, .62)
        ry = rng.uniform(.24, .42)
        if any((cx - ox)**2 + (cy - oy)**2 < (rx + orx)**2 * .80 for ox, oy, orx, ory in puddles):
            continue
        puddles.append((cx, cy, rx, ry))

    n = 32
    for pi, (cx, cy, rx, ry) in enumerate(puddles):
        center = sample_height(xs, ys, z, cx, cy) + .0022
        rings = [.25, .55, .82, .96]
        verts = [(cx, cy, center)]; faces = []
        for ri, radius in enumerate(rings):
            for k in range(n):
                a = 2 * math.pi * k / n
                wobble = 1 + .025 * math.sin(3 * a + pi) + .018 * math.sin(7 * a + pi * .3)
                px = cx + rx * .88 * radius * wobble * math.cos(a)
                py = cy + ry * .88 * radius * wobble * math.sin(a)
                ripple = .0004 * math.sin(radius * 8 * math.pi + pi)
                verts.append((px, py, center + ripple))
        for k in range(n):
            faces.append((0, 1 + k, 1 + (k + 1) % n))
        for ri in range(len(rings) - 1):
            start = 1 + ri * n; nxt = start + n
            for k in range(n):
                a = start + k; b = start + (k + 1) % n
                faces.append((a, nxt + k, nxt + (k + 1) % n, b))
        obj = mesh_object("Puddle water %02d" % (pi + 1), verts, faces, [water], smooth=True)
        made.append(obj)

        # Specular glint highlight patch
        glint_rx = rx * rng.uniform(0.18, 0.28)
        glint_ry = ry * rng.uniform(0.14, 0.22)
        gx = cx - rx * 0.16 + rng.uniform(-0.03, 0.03)
        gy = cy - ry * 0.12 + rng.uniform(-0.03, 0.03)
        gz = center + 0.0016
        gv = [(gx, gy, gz)]
        gf = []
        gn = 12
        for k in range(gn):
            ga = 2 * math.pi * k / gn
            gv.append((gx + glint_rx * math.cos(ga), gy + glint_ry * math.sin(ga), gz))
            gf.append((0, 1 + k, 1 + (k + 1) % gn))
        made.append(mesh_object("Puddle specular glint %02d" % (pi + 1), gv, gf, [glint], smooth=True))

        # Raised dark wet mud rim
        rv = []; rf = []
        for radius in (.90, 1.20):
            for k in range(n):
                a = 2 * math.pi * k / n
                px = cx + rx * radius * math.cos(a); py = cy + ry * radius * math.sin(a)
                rv.append((px, py, sample_height(xs, ys, z, px, py) + .0030))
        for k in range(n): rf.append((k, k + n, (k + 1) % n + n, (k + 1) % n))
        made.append(mesh_object("Humid raised puddle rim %02d" % (pi + 1), rv, rf, [wet], smooth=True))

        if pi % 2 == 0:
            a = rng.uniform(0, math.tau); fx = cx + rx * .25 * math.cos(a); fy = cy + ry * .25 * math.sin(a)
            spl = add_bevelled_box("Floating splinter", (fx, fy, center + .004), (.018, .11, .008), (0, 0, a), chip, .002)
            made.append(spl)
    return made, puddles


def make_wire(task, xs, ys, z, rng, look):
    if look == "v04":
        rust = material("Barbed wire | intense orange rust", (.16, .07, .02), .78)
        steel = material("Barbed wire | bright steel", (.45, .45, .45), .25)
        steel.node_tree.nodes.get("Principled BSDF").inputs["Metallic"].default_value = .90
        barbmat = material("Barb tips | orange rust", (.17, .08, .02), .75)
        strand_rad = .024
        barb_len = .052
    else:
        # w05: intermediate reddish-brown rust, visible at 40 px/m without being radioactive
        rust = material("Barbed wire | intermediate reddish rust", (.095, .055, .035), .80)
        steel = material("Barbed wire | subtle steel glints", (.26, .26, .26), .35)
        steel.node_tree.nodes.get("Principled BSDF").inputs["Metallic"].default_value = .70
        barbmat = material("Barb tips | dark iron oxide", (.085, .048, .032), .78)
        strand_rad = .018
        barb_len = .040

    wire_count = task.get("wire", 5)
    made = []
    wire_zones = [
        (-3.8, -1.2), (-2.0, 1.1), (2.0, -1.0), (3.9, 1.2),
        (-4.2, 0.4), (3.6, -0.4)
    ]
    for wi in range(min(wire_count, len(wire_zones))):
        base_x, base_y = wire_zones[wi]
        cx = base_x + rng.uniform(-.35, .35)
        cy = np.clip(base_y + rng.uniform(-.30, .30), -2.2, 2.2)
        phase = rng.uniform(0, math.tau); angle = rng.uniform(-math.pi, math.pi)
        points = []
        if wi % 2 == 0:
            turns = rng.randint(4, 6); count = turns * 36
            for i in range(count + 1):
                t = math.tau * turns * i / count; f = i / count
                rad = (.24 + .12 * f) * (1.15 if look == "v04" else 1.0)
                lx = (f - .5) * .70 + rad * math.cos(t + phase)
                ly = .78 * rad * math.sin(t + phase)
                wx = cx + lx * math.cos(angle) - ly * math.sin(angle)
                wy = np.clip(cy + lx * math.sin(angle) + ly * math.cos(angle), -2.40, 2.40)
                points.append((wx, wy, sample_height(xs, ys, z, wx, wy) + .028 + .020 * math.sin(t * 1.4 + phase)))
        else:
            count = 120; span = rng.uniform(1.2, 1.6); waves = rng.uniform(2.5, 4.0)
            for i in range(count + 1):
                f = i / count; lx = (f - .5) * span
                ly = .20 * math.sin(f * math.tau * waves + phase)
                wx = cx + lx * math.cos(angle) - ly * math.sin(angle)
                wy = np.clip(cy + lx * math.sin(angle) + ly * math.cos(angle), -2.40, 2.40)
                points.append((wx, wy, sample_height(xs, ys, z, wx, wy) + .024 + .014 * math.sin(f * 15 + phase)))

        components = []
        chunk = max(8, len(points) // 8)
        for start in range(0, len(points) - 1, chunk):
            part = points[start:min(len(points), start + chunk + 1)]
            components.append((part, strand_rad, 1 if (start // chunk) % 5 == 2 else 0))
        made.append(tube_object("Rusty barbed wire strand %02d" % (wi + 1), components, [rust, steel], 6))

        barb_components = []; walked = 0.0; next_at = .09
        for i in range(2, len(points) - 2):
            a, b = Vector(points[i - 1]), Vector(points[i + 1]); delta = b - a
            walked += delta.length
            if walked < next_at: continue
            next_at += rng.uniform(.09, .14)
            p = Vector(points[i]); planar = Vector((-delta.y, delta.x, 0))
            if planar.length < 1e-5: continue
            planar.normalize()
            forward = Vector((delta.x, delta.y, 0)).normalized()
            for side in (-1, 1):
                vec = (planar * .82 + forward * (side * .40)).normalized()
                tip = p + vec * barb_len + Vector((0, 0, .008))
                root = p - vec * .006
                barb_components.append(([tuple(root), tuple(tip)], .0055, 0 if rng.random() < .75 else 1))
        if barb_components:
            made.append(tube_object("Oversized wire barbs %02d" % (wi + 1), barb_components, [barbmat, steel], 5))
    return made


def make_rag(name, x, y, xs, ys, z, rng, mats):
    length, width = rng.uniform(.20, .28), rng.uniform(.095, .15)
    angle = rng.uniform(-math.pi, math.pi)
    verts = []; faces = []; mids = []; nx, ny = 5, 3
    for j in range(ny + 1):
        v = j / ny
        for i in range(nx + 1):
            u = i / nx
            edge = (.012 * math.sin(i * 3.4 + j * 1.7) if j in (0, ny) else 0)
            lx = (u - .5) * length + edge
            ly = (v - .5) * width
            fold = .003 * math.sin(u * math.pi * 5) * math.sin(v * math.pi * 3)
            wx = x + lx * math.cos(angle) - ly * math.sin(angle)
            wy = y + lx * math.sin(angle) + ly * math.cos(angle)
            verts.append((wx, wy, sample_height(xs, ys, z, wx, wy) + .003 + fold))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1)); mids.append(1 if (i + j) % 5 == 0 else 0)
    return mesh_object(name, verts, faces, mats, mids)


def make_details(task, xs, ys, z):
    rng = random.Random(task["seed"])
    look = task.get("look", "w05")
    variant = task.get("variant", 0)

    # Materials
    wood_top = image_material("Rotten wood atlas", Path(task["wood_texture"]), .88, (.92, .94, .98))
    wood_side = material("Rotten wood dark end grain", (.030, .032, .036), .96)
    if look == "v04":
        wood_edge = material("Worn wood bevel highlight", (.20, .22, .24), .58)
        bone = material("Old bone", (.48, .44, .35), .65)
        stone_light = material("Chalk pebble", (.38, .36, .30), .75)
    else:
        # w05: darker bevel highlight (less blue-gray) and muted ivory bones
        wood_edge = material("Worn wood bevel highlight", (.26, .28, .30), .65)
        bone = material("Old bone | muted ivory", (.38, .35, .28), .70)
        stone_light = material("Chalk pebble | weathered", (.28, .27, .23), .80)

    contact_shadow = material("Walkway contact shadow", (.014, .014, .016), .96)
    stone_dark = material("Basalt stone", (.045, .048, .042), .92)
    brass = material("Spent brass glint", (.65, .50, .16), .18)
    brass.node_tree.nodes.get("Principled BSDF").inputs["Metallic"].default_value = .96
    rust = material("Oxide scrap", (.095, .045, .025), .82)
    ochre = material("Old ochre stains", (.13, .090, .038), .95)
    nail = material("Dark nail iron", (.26, .26, .26), .25)
    nail.node_tree.nodes.get("Principled BSDF").inputs["Metallic"].default_value = .95
    ragmat = material("Faded burgundy cloth", (.085, .027, .024), .98)
    ragedge = material("Cloth shadow and worn edge", (.052, .023, .021), .98)

    created = []
    wood_variants = task.get("wood_variants", 4)

    # Walkway: 5 panels along Y.
    # HARD REQUIREMENT: Panel 0 (entrance) and Panel 4 (exit) enter/leave at X=0, angle=0.
    count = 5
    slot_len = HEIGHT / count
    length = 1.20
    boards = 5
    walk_w = 1.22
    board_pitch = walk_w / boards
    board_width = 0.20
    thick = 0.052

    # Wander and variation across internal panels 1, 2, 3
    wander_profiles = [
        # (dx1, dx2, dx3, broken_panel, broken_board, sunken_panel, tilt_panel)
        (-0.10, -0.16, -0.06, 3, 1, 1, 2),  # v0
        (0.10, 0.16, 0.06, 2, 3, 3, 1),    # v1
        (0.00, 0.04, -0.02, 1, 0, 2, 3),    # v2
        (-0.12, 0.00, 0.12, 3, 2, 1, 2),    # v3
        (0.12, 0.00, -0.12, 2, 1, 3, 1),    # v4
        (0.02, -0.06, 0.02, 1, 3, 2, 3),    # v5
    ]
    prof = wander_profiles[variant % len(wander_profiles)]
    dx_map = {0: 0.0, 1: prof[0], 2: prof[1], 3: prof[2], 4: 0.0}
    ang_map = {
        0: 0.0,
        1: (prof[1] - 0.0) / (slot_len * 2),
        2: (prof[2] - prof[0]) / (slot_len * 2),
        3: (0.0 - prof[1]) / (slot_len * 2),
        4: 0.0,
    }

    base_variant = (variant * 2) % wood_variants

    for panel in range(count):
        cy = -HEIGHT / 2 + (panel + .5) * slot_len
        cx = dx_map[panel]
        angle = ang_map[panel]
        center_h = sample_height(xs, ys, z, cx, cy)

        pan_roll = 0.0
        pan_pitch = 0.0
        base_z = center_h + 0.024

        # Internal panel degradations
        if panel == prof[5]:  # Sunken
            base_z = center_h + 0.008
            pan_roll = 0.025
        elif panel == prof[6]:  # Tilted
            cx += 0.025
            pan_roll = -0.050
            pan_pitch = 0.015
            base_z = center_h + 0.028

        # Ground contact shadow pad
        sw = walk_w * 0.5 + 0.02
        sl = length * 0.5 + 0.015
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        corners = [(-sw, -sl), (sw, -sl), (sw, sl), (-sw, sl)]
        shadow_verts = []
        for lx, ly in corners:
            wx = cx + lx * cos_a - ly * sin_a
            wy = cy + lx * sin_a + ly * cos_a
            shadow_verts.append((wx, wy, sample_height(xs, ys, z, wx, wy) + 0.0010))
        created.append(mesh_object("Walkway panel %02d contact shadow" % panel,
                                   shadow_verts, [(0, 1, 2, 3)], [contact_shadow]))

        for j in range(boards):
            is_broken = (panel == prof[3] and j == prof[4])
            offset = (j - (boards - 1) / 2) * board_pitch
            x = cx + offset * math.cos(angle)
            y = cy + offset * math.sin(angle)
            board_len = length * (0.50 if is_broken else rng.uniform(0.97, 1.0))
            bj_z = base_z + offset * math.sin(pan_roll)
            board_variant = (base_variant + j) % wood_variants
            obj, rot, _ = make_wood_board("Walkway panel %02d board %02d" % (panel, j),
                x, y, bj_z, board_width, board_len, thick,
                angle + rng.uniform(-0.010, 0.010), board_variant,
                wood_top, wood_side, wood_edge, rng, is_broken,
                roll=pan_roll, pitch=pan_pitch)
            created.append(obj)
            for sign in (-1, 1):
                yy = y + sign * board_len * 0.38
                bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.011, depth=0.006,
                                                    location=(x, yy, bj_z + thick * 0.5 + 0.003))
                head = bpy.context.object; head.name = "Panel nail"; head.data.materials.append(nail); created.append(head)

        for sign in (-1, 1):
            yy_b = cy + sign * length * 0.36
            batten_z = base_z + thick * 0.5 + 0.006
            batten, _, _ = make_wood_board("Panel transverse batten", cx, yy_b, batten_z,
                0.09, walk_w, 0.024, math.pi / 2 + angle, (base_variant + 1) % wood_variants,
                wood_top, wood_side, wood_edge, rng, False, roll=pan_pitch, pitch=pan_roll)
            created.append(batten)

    # Branch walkway on some variants (contained strictly within |y| <= 1.5m)
    if variant in (0, 1, 3, 4):
        branch_sign = -1 if variant in (0, 3) else 1
        br_x = branch_sign * 1.05
        br_y = -0.30 if variant in (0, 4) else 0.40
        br_ang = branch_sign * 0.50
        br_len = 0.90
        br_boards = 4
        br_bw = 0.18
        br_h = sample_height(xs, ys, z, br_x, br_y) + 0.024
        bsw = 0.80 * 0.5 + 0.03
        bsl = br_len * 0.5 + 0.02
        bcos, bsin = math.cos(br_ang), math.sin(br_ang)
        b_shadow_verts = [
            (br_x + lx * bcos - ly * bsin, br_y + lx * bsin + ly * bcos,
             sample_height(xs, ys, z, br_x + lx * bcos - ly * bsin, br_y + lx * bsin + ly * bcos) + 0.0014)
            for lx, ly in [(-bsw, -bsl), (bsw, -bsl), (bsw, bsl), (-bsw, bsl)]
        ]
        created.append(mesh_object("Branch walkway contact shadow", b_shadow_verts, [(0, 1, 2, 3)], [contact_shadow]))
        for bj in range(br_boards):
            boff = (bj - (br_boards - 1) / 2) * 0.19
            bx = br_x + boff * math.cos(br_ang)
            by = br_y + boff * math.sin(br_ang)
            b_obj, _, _ = make_wood_board("Branch board %02d" % bj, bx, by, br_h, br_bw, br_len * 0.95, thick,
                                          br_ang + rng.uniform(-0.015, 0.015), (base_variant + bj) % wood_variants,
                                          wood_top, wood_side, wood_edge, rng, (bj == 0))
            created.append(b_obj)

    # Water puddles on wide flanks
    water_objs, puddles = make_puddles(task, xs, ys, z, rng, look)
    created.extend(water_objs)

    # Barbed wire
    created.extend(make_wire(task, xs, ys, z, rng, look))

    # Loose planks (kept within |y| <= 2.2m)
    loose_count = task.get("loose_planks", 8)
    for i in range(loose_count):
        side = -1 if i % 2 == 0 else 1
        x = side * rng.uniform(1.3, 4.5)
        y = rng.uniform(-2.15, 2.15)
        obj, _, _ = make_wood_board("Loose plank %02d" % i, x, y, sample_height(xs, ys, z, x, y) + .020 + (i % 3) * .015,
            .14, rng.uniform(.45, .80), .045, (math.pi / 2 if i % 3 == 0 else 0) + rng.uniform(-.12, .12),
            rng.randrange(wood_variants), wood_top, wood_side, wood_edge, rng, i % 3 == 0)
        created.append(obj)

    # Debris clustering with narrative nests and calm breathing zones
    nests = [(-3.6, -1.2), (-2.0, 1.1), (2.0, -1.0), (3.6, 1.2), (-1.2, 0.2), (1.2, -0.4)]
    for px, py, rx, ry in puddles:
        nests.append((px + rx * 0.90, py + ry * 0.90))

    calm_zones = [
        (-4.0, 1.5, 0.85), (4.0, -1.5, 0.85),
        (-2.5, -1.8, 0.75), (2.5, 1.8, 0.75)
    ]

    debris_count = task.get("debris", 550)
    for i in range(debris_count):
        if rng.random() < 0.86:
            nx_c, ny_c = nests[rng.randrange(len(nests))]
            x = rng.gauss(nx_c, 0.30)
            y = np.clip(rng.gauss(ny_c, 0.28), -2.50, 2.50)
        else:
            x = rng.uniform(-WIDTH * .47, WIDTH * .47)
            y = rng.uniform(-2.50, 2.50)

        # Skip calm breathing zones and inside walkway corridor / inside puddles
        if any((x - cx)**2 + (y - cy)**2 < cr**2 for cx, cy, cr in calm_zones):
            continue
        if abs(x) < 0.75:  # Keep main walkway clean
            continue
        if any(((x - px) / rx)**2 + ((y - py) / ry)**2 < 0.85 for px, py, rx, ry in puddles):
            continue

        h = sample_height(xs, ys, z, x, y)
        pick = rng.random()
        if pick < .52:
            sx, sy, sz = rng.uniform(.035, .075), rng.uniform(.025, .055), rng.uniform(.015, .040)
            s_mat = stone_dark if (rng.random() < (0.85 if look == "w05" else 0.60)) else stone_light
            obj = add_ico("Mudstone %03d" % (i + 1), (x, y, h + sz * .35), (sx, sy, sz), s_mat, rng)
        elif pick < .70:
            length_b, rad = rng.uniform(.07, .14), rng.uniform(.008, .013)
            obj = add_cylinder("Bone fragment %03d" % (i + 1), (x, y, h + length_b * .26), rad, length_b, bone, rng, 6)
        elif pick < .87:
            length_c, rad = rng.uniform(.022, .036), rng.uniform(.006, .010)
            obj = add_cylinder("Brass casing %03d" % (i + 1), (x, y, h + length_c * .35), rad, length_c, brass, rng, 8)
        elif pick < .96:
            sx, sy, sz = rng.uniform(.045, .09), rng.uniform(.035, .07), rng.uniform(.006, .016)
            obj = add_bevelled_box("Rust plate %03d" % (i + 1), (x, y, h + sz * .4), (sx, sy, sz),
                (rng.uniform(-.15, .15), rng.uniform(-.15, .15), rng.uniform(0, math.pi)), rust, .003)
        else:
            obj = add_bevelled_box("Old ochre shard %03d" % (i + 1), (x, y, h + .004), (.055, .032, .008),
                (0, 0, rng.uniform(0, math.pi)), ochre, .003)
        created.append(obj)

    # Rags
    rags_count = task.get("rags", 2)
    for i in range(rags_count):
        side = -1 if i % 2 == 0 else 1
        rx = side * rng.uniform(1.8, 4.2)
        ry = rng.uniform(-2.2, 2.2)
        created.append(make_rag("Faded burgundy rag %02d" % (i + 1), rx, ry, xs, ys, z, rng, [ragmat, ragedge]))

    return created


def setup_lab_preview(path):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 480; scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = .3
    for obj in list(scene.objects):
        if obj.type in {"LIGHT", "CAMERA"}: bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.object.light_add(type="SUN", location=(-4, -5, 8))
    light = bpy.context.object; light.data.energy = 3
    light.rotation_euler = (Vector((0, 0, 0)) - light.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.object.camera_add(location=(8, -12, 8))
    camera = bpy.context.object; camera.data.type = "ORTHO"; camera.data.ortho_scale = 12.0
    camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = camera; scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def setup_preview(path):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "Medium High Contrast"
    world = bpy.data.worlds.new("Overcast trench light")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (.20, .21, .18, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .8
    bpy.ops.object.light_add(type="AREA", location=(0, 0, 6.0))
    light = bpy.context.object
    light.data.energy = 550
    light.data.shape = "DISK"
    light.data.size = 6
    bpy.ops.object.camera_add(location=(0, 0, 8.5))
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = WIDTH
    scene.camera = camera
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    task = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    global WIDTH, HEIGHT, SPACING
    WIDTH = float(task.get("lane_width_m", task.get("patch_tiles_x", 15) * 0.792))
    HEIGHT = float(task.get("band_depth_m", task.get("patch_tiles_y", 8) * 0.792))
    SPACING = float(task.get("spacing", 0.024))
    look = task.get("look", "w05")
    variant = task.get("variant", 0)
    mud_seed = int(task.get("mud_seed", 32026))

    clear_scene()
    nx = math.ceil(WIDTH / SPACING)
    ny = math.ceil(HEIGHT / SPACING)
    xs, ys, z = make_height(mud_seed, nx, ny)

    make_wood_atlas(Path(task["wood_texture"]), task["seed"], task.get("wood_variants", 4), look=look)
    base = build_base(xs, ys, z, Path(task["mud_texture"]), task.get("tex_span", 3.168), task.get("mud_source", "image"))
    details = make_details(task, xs, ys, z)

    output = Path(task["output"])
    bpy.ops.object.select_all(action="DESELECT")
    for obj in [base] + details:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.export_scene.gltf(filepath=str(output), export_format="GLB", use_selection=True,
                              export_apply=True, export_yup=True, export_texcoords=True,
                              export_normals=True, export_materials="EXPORT")

    edge_error = float(np.max(np.abs(z[0, :] - z[-1, :])))
    base_triangles = 2 * nx * ny
    detail_polys = sum(len(o.data.polygons) for o in details)
    print("BASE_GRID: %dx%d quads, %d triangles" % (nx, ny, base_triangles))
    print("TOTAL_TRIANGLES_ESTIMATE: %d (base: %d, details: %d)" % (base_triangles + detail_polys, base_triangles, detail_polys))
    print("PERIODIC_HEIGHT_EDGE_MAX_ERROR: %.12g m" % edge_error)
    print("BAND_METERS: %.3f x %.3f; look=%s; variant=%d; objects=%d" %
          (WIDTH, HEIGHT, look, variant, len(details)))
    if task.get("preview"):
        setup_preview(Path(task["preview"]))
    if task.get("lab_preview"):
        setup_lab_preview(Path(task["lab_preview"]))


if __name__ == "__main__":
    main()
