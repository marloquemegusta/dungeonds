import bpy, math
from mathutils import Vector

def setup_render(res=(400,400)):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'TEXTURE'
    sc.display.shading.show_cavity = False
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    w = bpy.data.worlds.new('w') if not sc.world else sc.world
    sc.world = w
    w.color = (0.35, 0.37, 0.42)
    return sc

def make_cam(center, ortho_scale, view):
    cam_d = bpy.data.cameras.new('cam'); cam_d.type = 'ORTHO'; cam_d.ortho_scale = ortho_scale
    cam = bpy.data.objects.new('cam', cam_d); bpy.context.scene.collection.objects.link(cam)
    d = 3.0
    # character faces -Y; "front" camera at -Y looking +Y; side camera at +X looking -X
    if view == 'front':
        cam.location = center + Vector((0, -d, 0)); cam.rotation_euler = (math.radians(90), 0, 0)
    elif view == 'side':
        cam.location = center + Vector((d, 0, 0)); cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    elif view == 'top':
        cam.location = center + Vector((0, 0, d)); cam.rotation_euler = (0, 0, 0)
    elif view == 'back':
        cam.location = center + Vector((0, d, 0)); cam.rotation_euler = (math.radians(90), 0, math.radians(180))
    bpy.context.scene.camera = cam
    return cam

def render_to(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
