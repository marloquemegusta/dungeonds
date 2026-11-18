"""Libreria comun de los prototipos del remate sobre el Cireneo (heroe + Cireneo + su cruz, un solo sprite).
La importa tools/characters/proto_remate_cireneo.py (corre dentro de Blender, no usar directamente).

Escala REAL de cada personaje (calibrada contra los sprites de la ROM, ver CALIB en proto_remate_cireneo.py):
  Cireneo = PPM_CIR px/m, heroe = PPM_HERO px/m. La escena se renderiza a PPM_CIR y el heroe se escala por HERO_K.
Mundo: Cireneo en el origen mirando a -X (rz=-90); el heroe llega desde +X (por la espalda, el lado de la cruz).
Camara diagonal ortografica a 30 grados de elevacion (la del juego): a la derecha de pantalla va (+X,+Y).
"""
import bpy, sys, os, math, random
import bmesh
from mathutils import Vector, Matrix, Euler

MAIN = 'C:/codexlocal/dungeonds'
P = 'mixamorig:'
V = Vector

PPM_CIR = 56.4            # px/m del Cireneo en su sprite de andar (fitZoom 0.88, extent 1.872, celda 60)
PPM_HERO = 38.0           # px/m del heroe en su sprite de andar (fitZoom 0.86, extent 1.8116, celda 40)
HERO_K = PPM_HERO / PPM_CIR
SS = 4


def update():
    bpy.context.view_layer.update()


def load(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


class Char:
    pass


def make_char(fbx, rz_deg, scale, loc, mesh_filter=None):
    c = Char()
    new = load(fbx)
    c.new = new
    c.arm = [o for o in new if o.type == 'ARMATURE'][0]
    meshes = [o for o in new if o.type == 'MESH']
    c.mesh = [o for o in meshes if o.name != 'Cruz'][0]
    cr = [o for o in meshes if o.name == 'Cruz']
    c.cruz = cr[0] if cr else None
    c.root = bpy.data.objects.new('root', None)
    bpy.context.scene.collection.objects.link(c.root)
    c.arm.parent = c.root
    c.root.scale = (scale, scale, scale)
    c.root.rotation_euler = (0, 0, math.radians(rz_deg))
    c.root.location = loc
    if c.arm.animation_data:
        c.arm.animation_data.action = None
    for pb in c.arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return c


def load_action(path, short):
    ab = set(bpy.data.actions)
    new = load(path)
    acts = [a for a in bpy.data.actions if a not in ab]
    a = acts[0]
    a.use_fake_user = True
    a.name = short
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    return a


ACT = {}


def capture(ch, act_key, frame):
    act = ACT[act_key]
    ch.arm.animation_data_create()
    ch.arm.animation_data.action = act
    try:
        ch.arm.animation_data.action_slot = act.slots[0]
    except Exception:
        pass
    bpy.context.scene.frame_set(frame)
    update()
    d = {pb.name: pb.matrix_basis.copy() for pb in ch.arm.pose.bones}
    ch.arm.animation_data.action = None
    return d


def apply_basis(ch, d):
    for pb in ch.arm.pose.bones:
        pb.matrix_basis = d[pb.name]
    update()


# ----------------------------------------------------------------------------------------------- utilidades de pose
def W(ch):
    return ch.arm.matrix_world


def bone_world(ch, name):
    return W(ch) @ ch.arm.pose.bones[P + name].matrix


def set_bone_world(ch, name, Mw):
    ch.arm.pose.bones[P + name].matrix = W(ch).inverted() @ Mw
    update()


def head_world(ch, name):
    return W(ch) @ ch.arm.pose.bones[P + name].head


def tail_world(ch, name):
    return W(ch) @ ch.arm.pose.bones[P + name].tail


def xform_about(pivot, rot_y=0.0, rot_z=0.0, rot_x=0.0, trans=(0, 0, 0)):
    R = Matrix.Rotation(math.radians(rot_z), 4, 'Z') @ Matrix.Rotation(math.radians(rot_y), 4, 'Y') \
        @ Matrix.Rotation(math.radians(rot_x), 4, 'X')
    return Matrix.Translation(Vector(trans)) @ Matrix.Translation(pivot) @ R @ Matrix.Translation(-Vector(pivot))


def bend(ch, name, rot_y=0.0, rot_x=0.0, rot_z=0.0):
    """Gira el hueso (y sus hijos) alrededor de su cabeza, en ejes de MUNDO."""
    Mw = bone_world(ch, name)
    p = Mw.translation.copy()
    set_bone_world(ch, name, xform_about(p, rot_y, rot_z, rot_x) @ Mw)


def add_ik(ch, bone, name, chain=2):
    t = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(t)
    pb = ch.arm.pose.bones[P + bone]
    c = pb.constraints.new('IK')
    c.target = t
    c.chain_count = chain
    c.use_tail = True
    c.use_stretch = False
    c.influence = 0.0
    return t, c


# ----------------------------------------------------------------------------------------------- render
def setup_render(cell, ppm):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'TEXTURE'
    sc.display.shading.show_cavity = False
    sc.display.shading.show_shadows = False
    sc.display.render_aa = '8'
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.render.resolution_x = cell * SS
    sc.render.resolution_y = cell * SS
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    cam_d = bpy.data.cameras.new('cam')
    cam_d.type = 'ORTHO'
    cam_d.ortho_scale = cell / ppm
    cam = bpy.data.objects.new('cam', cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def place_cam(cam, az_deg, center, elev=30.0):
    az, el = math.radians(az_deg), math.radians(elev)
    D = 8.0
    pos = center + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * D
    cam.location = pos
    cam.rotation_euler = (center - pos).to_track_quat('-Z', 'Y').to_euler()


def render_frame(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def flat_mat(name, col):
    m = bpy.data.materials.new(name)
    m.diffuse_color = col
    return m


def new_disc(name, mat):
    bpy.ops.mesh.primitive_circle_add(vertices=24, radius=1.0, fill_type='NGON', location=(0, 0, 0.002))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    o.hide_render = True
    return o


def new_cube(name, size, mat):
    bpy.ops.mesh.primitive_cube_add(size=size, location=(0, 0, -5))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    o.hide_render = True
    return o


def cruz_free(cr, arm, M, parent=None):
    """Suelta la cruz del esqueleto (sin skin) y la coloca como solido rigido en el mundo con la matriz M
    (M es la matriz de mundo completa, escala incluida: la del armature con la pose de reposo, o `cruz_attached(arm)`)."""
    for m in cr.modifiers:
        m.show_viewport = False
        m.show_render = False
    cr.parent = parent
    cr.matrix_parent_inverse = Matrix.Identity(4)
    cr.matrix_world = M


def cruz_skinned(cr, arm):
    for m in cr.modifiers:
        m.show_viewport = True
        m.show_render = True
    cr.parent = arm
    cr.matrix_parent_inverse = Matrix.Identity(4)
    cr.location = (0, 0, 0)
    cr.rotation_euler = (0, 0, 0)
    cr.scale = (1, 1, 1)


def cruz_attached(arm):
    """Matriz de mundo que tendria la cruz si siguiera atada a Spine2 (peso 1) con la pose actual."""
    pb = arm.pose.bones[P + 'Spine2']
    return arm.matrix_world @ (pb.matrix @ pb.bone.matrix_local.inverted())


def gain_textures(objs, k):
    """Multiplica la textura de los objetos por k (el Workbench de Blender sale mucho mas oscuro que los sprites de la
    ROM; k calibrado para igualar la luminosidad media de los sprites reales). Solo en memoria."""
    import numpy as np
    done = set()
    for o in objs:
        for m in o.data.materials:
            if not m or not m.node_tree:
                continue
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image and n.image.name not in done:
                    done.add(n.image.name)
                    im = n.image
                    buf = np.empty(len(im.pixels), dtype=np.float32)
                    im.pixels.foreach_get(buf)
                    px = buf.reshape(-1, 4)
                    px[:, :3] = np.clip(px[:, :3] * k, 0, 1)
                    im.pixels.foreach_set(px.ravel())
                    im.update()
