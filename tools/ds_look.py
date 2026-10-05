#!/usr/bin/env python3
"""
ds_look.py - Single source of truth for the DungeonDS baked art look.

Both the environment baker and the character baker import these values so that
lighting, colour grading and the projection angle always match. Changing the
preset here (or via --preset on the bakers) re-bakes the whole game coherently.

Presets:
    e30 - 30 deg elevation  => 32x16 diamond tiles (classic 2:1 isometric)
    e60 - 60 deg elevation  => 32x28 diamond tiles (steeper, more top-down)
"""

import math

FLOOR_TILE_W = 32
OBJ_CANVAS = 96          # full wall/arch projection within the DS EWRAM budget
CHAR_CANVAS = 64
OBJ_PAD = OBJ_CANVAS // 2  # ground origin sits at the canvas centre
GROUND_ANCHOR_Y = OBJ_CANVAS // 2
GROUND_ANCHOR_Z = 0.0
CHAR_ANCHOR_Y = CHAR_CANVAS // 2
CHAR_ANCHOR_Z = 0.0
PIXELS_PER_METRE = 32.0 / (2.0 * math.sqrt(2.0))  # a 2x2 m tile is 32 px wide

PRESETS = {
    "e30": {"elevation": 30.0},
    "e60": {"elevation": 60.0},
}


def elevation(preset):
    return PRESETS[preset]["elevation"]


def tile_h(preset):
    """Screen height in pixels of a 2x2 m diamond tile at this elevation."""
    return int(round(FLOOR_TILE_W * math.sin(math.radians(elevation(preset)))))


# --- lighting rig (identical for environment and characters) ----------------
# A single key light defines the shadow direction; fill + rim keep the forms
# readable. All lights are world-fixed so every sprite agrees with every other.
LIGHTS = [
    {"name": "Key",  "energy": 4.0, "angle": 12.0, "rot": (55.0, 0.0, 150.0), "shadow": True},
    {"name": "Fill", "energy": 1.7, "angle": 45.0, "rot": (68.0, 0.0, -35.0), "shadow": False},
    {"name": "Rim",  "energy": 0.9, "angle": 30.0, "rot": (72.0, 0.0, 55.0),  "shadow": False},
]

# Soft cool ambient so shadowed faces stay readable instead of going black.
WORLD_COLOR = (0.09, 0.10, 0.13)
WORLD_STRENGTH = 1.0

# --- colour grade applied to every sprite -----------------------------------
GRADE_CONTRAST = 1.08
GRADE_BRIGHTNESS = 1.10
GRADE_SATURATION = 1.15

def blender_lights_snippet():
    out = []
    for L in LIGHTS:
        out.append(
            f"d = bpy.data.lights.new('{L['name']}', 'SUN'); d.energy = {L['energy']}; "
            f"d.angle = math.radians({L['angle']}); d.use_shadow = {L['shadow']}\n"
            f"o = bpy.data.objects.new('{L['name']}', d)\n"
            f"o.rotation_euler = (math.radians({L['rot'][0]}), math.radians({L['rot'][1]}), "
            f"math.radians({L['rot'][2]}))\n"
            f"scene.collection.objects.link(o)"
        )
    return "\n".join(out)


def blender_world_snippet():
    return (
        f"w = bpy.data.worlds.new('DSWorld'); w.use_nodes = True\n"
        f"_bg = w.node_tree.nodes.get('Background')\n"
        f"if _bg:\n"
        f"    _bg.inputs[0].default_value = ({WORLD_COLOR[0]}, {WORLD_COLOR[1]}, {WORLD_COLOR[2]}, 1.0)\n"
        f"    _bg.inputs[1].default_value = {WORLD_STRENGTH}\n"
        f"scene.world = w"
    )


def blender_camera_snippet(res_w, res_h, elevation_deg, target_z=0.0):
    """Orthographic iso camera targeting the world ground origin (0,0,0)."""
    az = 45.0
    dist = 30.0
    return f"""
cam_data = bpy.data.cameras.new('IsoCam')
cam_data.type = 'ORTHO'
# Keep one physical scale across every bake. The render canvas is only a
# viewport around the same ground anchor: a 96 px object canvas must show 96
# pixels at the shared pixels/metre density, not reuse the 32 px floor width.
cam_data.ortho_scale = max({res_w}, {res_h}) / {PIXELS_PER_METRE}
cam = bpy.data.objects.new('IsoCam', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
tt = cam.constraints.new(type='TRACK_TO')
tt.target = target
tt.track_axis = 'TRACK_NEGATIVE_Z'
tt.up_axis = 'UP_Y'
_el = math.radians({elevation_deg})
_az = math.radians({az})
_dist = {dist}
cam.location = (_dist * math.cos(_el) * math.cos(_az),
                _dist * math.cos(_el) * math.sin(_az),
                {target_z} + _dist * math.sin(_el))
"""


# --- image post-processing (PIL) --------------------------------------------

def grade(img):
    """Apply the shared contrast / brightness / saturation grade in-place."""
    from PIL import ImageEnhance
    img = ImageEnhance.Brightness(img).enhance(GRADE_BRIGHTNESS)
    img = ImageEnhance.Contrast(img).enhance(GRADE_CONTRAST)
    img = ImageEnhance.Color(img).enhance(GRADE_SATURATION)
    return img
