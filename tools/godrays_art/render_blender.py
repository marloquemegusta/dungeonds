import bpy, math, os, sys
from mathutils import Vector

def setup_and_render_variant(mode="lancet_vitral", super_scale=4):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    # 1. Cycles Setup with OptiX
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    cprefs = bpy.context.preferences.addons['cycles'].preferences
    cprefs.compute_device_type = 'OPTIX'
    for d in cprefs.devices:
        d.use = (d.type == 'OPTIX')

    scene.cycles.samples = 128
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 256 * super_scale
    scene.render.resolution_y = 128 * super_scale
    scene.view_settings.view_transform = 'Standard'

    # 2. World setup (pitch black)
    world = bpy.data.worlds.new("BlackWorld")
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    scene.world = world

    # 3. Game Orthographic Camera (Elevation 30 deg, looking along +Y)
    cam_data = bpy.data.cameras.new("DSCam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 256.0 / 17.9  # 14.301676 m horizontal field
    cam_obj = bpy.data.objects.new("DSCam", cam_data)

    dist = 30.0
    cam_x = 7.150838
    cam_y = 1.0 - dist * math.cos(math.radians(30))
    cam_z = 2.8 + dist * math.sin(math.radians(30))
    cam_obj.location = (cam_x, cam_y, cam_z)
    cam_obj.rotation_euler = (math.radians(60.0), 0.0, 0.0)
    bpy.context.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # 4. Materials
    # Floor: Neutral diffuse receiver (albedo 0.50, roughness 1.0)
    fmat = bpy.data.materials.new("FloorMat")
    fbsdf = fmat.node_tree.nodes["Principled BSDF"]
    fbsdf.inputs["Base Color"].default_value = (0.50, 0.50, 0.50, 1.0)
    fbsdf.inputs["Roughness"].default_value = 1.0

    bmat = bpy.data.materials.new("BlackMat")
    bbsdf = bmat.node_tree.nodes["Principled BSDF"]
    bbsdf.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    bbsdf.inputs["Roughness"].default_value = 1.0

    # 5. Cathedral Geometry
    # Floor plane at Z = 0
    bpy.ops.mesh.primitive_plane_add(size=40.0, location=(10.0, 2.0, 0.0))
    floor = bpy.context.active_object
    floor.name = "Floor"
    floor.data.materials.append(fmat)

    script_dir = os.path.abspath("tools/godrays_art")
    if mode == "rose_vitral":
        win_w = 3.0
        win_h = 3.0
        win_z_c = 5.6
        win_y_c = 0.0
        tex_file = "tex_rose.png"
        vol_loc = (4.25, 1.0, 2.8)
        vol_scale = (9.5, 5.0, 6.5)
        vol_density = 0.18
        sun_energy = 42.0
    elif mode == "lancet_amber":
        win_w = 1.5
        win_h = 3.5
        win_z_c = 5.6
        win_y_c = 0.0
        tex_file = "tex_amber.png"
        vol_loc = (4.25, 1.0, 2.8)
        vol_scale = (9.5, 4.0, 6.0)
        vol_density = 0.20
        sun_energy = 45.0
    else: # lancet_vitral
        win_w = 1.5
        win_h = 3.5
        win_z_c = 5.6
        win_y_c = 0.0
        tex_file = "tex_vitral.png"
        vol_loc = (4.25, 1.0, 2.8)
        vol_scale = (9.5, 4.0, 6.0)
        vol_density = 0.20
        sun_energy = 50.0

    tex_path = os.path.join(script_dir, tex_file)

    h_min_y = win_y_c - win_w / 2.0
    h_max_y = win_y_c + win_w / 2.0
    h_min_z = win_z_c - win_h / 2.0
    h_max_z = win_z_c + win_h / 2.0

    # Left Wall at X = 0 with window opening
    import bmesh
    bm = bmesh.new()
    w_min_y, w_max_y = -30.0, 30.0
    w_min_z, w_max_z = 0.0, 25.0

    v1 = bm.verts.new((0.0, w_min_y, w_min_z))
    v2 = bm.verts.new((0.0,  w_max_y, w_min_z))
    v3 = bm.verts.new((0.0,  w_max_y, w_max_z))
    v4 = bm.verts.new((0.0, w_min_y, w_max_z))

    h1 = bm.verts.new((0.0, h_min_y, h_min_z))
    h2 = bm.verts.new((0.0, h_max_y, h_min_z))
    h3 = bm.verts.new((0.0, h_max_y, h_max_z))
    h4 = bm.verts.new((0.0, h_min_y, h_max_z))
    bm.verts.ensure_lookup_table()

    bm.faces.new([v1, v2, h2, h1])
    bm.faces.new([v2, v3, h3, h2])
    bm.faces.new([v3, v4, h4, h3])
    bm.faces.new([v4, v1, h1, h4])

    wmesh = bpy.data.meshes.new("WallMesh")
    bm.to_mesh(wmesh)
    bm.free()
    wall_obj = bpy.data.objects.new("WallObj", wmesh)
    wall_obj.data.materials.append(bmat)
    bpy.context.collection.objects.link(wall_obj)

    # Roof covering cathedral interior (blocks skylight, invisible to camera)
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(10.0, 0.0, 14.0))
    roof = bpy.context.active_object
    roof.scale = (20.0, 60.0, 1.0)
    roof.data.materials.append(bmat)
    roof.visible_camera = False

    # Back Wall at Y = 16.0
    bpy.ops.mesh.primitive_plane_add(size=40.0, location=(10.0, 16.0, 7.0))
    bwall = bpy.context.active_object
    bwall.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    bwall.data.materials.append(bmat)
    bwall.visible_camera = False

    # Stained Glass Window Plane at X = 0.005
    bm = bmesh.new()
    g1 = bm.verts.new((0.005, h_min_y, h_min_z))
    g2 = bm.verts.new((0.005, h_max_y, h_min_z))
    g3 = bm.verts.new((0.005, h_max_y, h_max_z))
    g4 = bm.verts.new((0.005, h_min_y, h_max_z))
    f = bm.faces.new([g1, g2, g3, g4])
    uv_layer = bm.loops.layers.uv.new()
    f.loops[0][uv_layer].uv = (0.0, 0.0)
    f.loops[1][uv_layer].uv = (1.0, 0.0)
    f.loops[2][uv_layer].uv = (1.0, 1.0)
    f.loops[3][uv_layer].uv = (0.0, 1.0)

    gmesh = bpy.data.meshes.new("GlassMesh")
    bm.to_mesh(gmesh)
    bm.free()
    glass_obj = bpy.data.objects.new("GlassObj", gmesh)

    gmat = bpy.data.materials.new("GlassMat")
    gnodes = gmat.node_tree.nodes
    gnodes.clear()
    gout = gnodes.new("ShaderNodeOutputMaterial")
    tc = gnodes.new("ShaderNodeTexCoord")
    tex_node = gnodes.new("ShaderNodeTexImage")
    b_img = bpy.data.images.load(tex_path)
    tex_node.image = b_img
    trans = gnodes.new("ShaderNodeBsdfTransparent")

    gmat.node_tree.links.new(tc.outputs["UV"], tex_node.inputs["Vector"])
    gmat.node_tree.links.new(tex_node.outputs["Color"], trans.inputs["Color"])
    gmat.node_tree.links.new(trans.outputs["BSDF"], gout.inputs["Surface"])
    glass_obj.data.materials.append(gmat)
    bpy.context.collection.objects.link(glass_obj)

    # 6. Volume Box along the beam path
    bpy.ops.mesh.primitive_cube_add(size=1, location=vol_loc)
    vol_box = bpy.context.active_object
    vol_box.name = "VolumeBox"
    vol_box.scale = vol_scale
    vmat = bpy.data.materials.new("VolumeMat")
    vnodes = vmat.node_tree.nodes
    vnodes.clear()
    vout = vnodes.new("ShaderNodeOutputMaterial")
    vp = vnodes.new("ShaderNodeVolumePrincipled")
    vp.inputs["Density"].default_value = vol_density
    vp.inputs["Anisotropy"].default_value = 0.15
    vmat.node_tree.links.new(vp.outputs["Volume"], vout.inputs["Volume"])
    vol_box.data.materials.append(vmat)

    # 7. Sun Light (strictly parallel rays)
    dir_vec = Vector((8.5, 2.0, -5.6)).normalized()
    sun_data = bpy.data.lights.new("Sun", type='SUN')
    sun_data.energy = sun_energy
    sun_data.angle = 0.0 # Zero divergence -> strictly parallel beam
    sun_obj = bpy.data.objects.new("Sun", sun_data)
    rot_quat = Vector((0, 0, -1)).rotation_difference(dir_vec)
    sun_obj.rotation_mode = 'QUATERNION'
    sun_obj.rotation_quaternion = rot_quat
    bpy.context.collection.objects.link(sun_obj)

    # 8. Render A (Sun ON)
    raw_a_path = os.path.join(script_dir, f"raw_{mode}_a.png")
    scene.render.filepath = raw_a_path
    print(f"Rendering {mode} (A: Sun ON) to {raw_a_path}...")
    bpy.ops.render.render(write_still=True)

    # 9. Render B (Sun OFF)
    sun_data.energy = 0.0
    raw_b_path = os.path.join(script_dir, f"raw_{mode}_b.png")
    scene.render.filepath = raw_b_path
    print(f"Rendering {mode} (B: Sun OFF) to {raw_b_path}...")
    bpy.ops.render.render(write_still=True)
    print(f"Renders for {mode} complete!")

if __name__ == "__main__":
    args = sys.argv
    mode = "lancet_vitral"
    if "--" in args:
        user_args = args[args.index("--") + 1:]
        if len(user_args) >= 1:
            mode = user_args[0]
    elif len(args) > 1 and not args[-1].endswith(".py"):
        mode = args[-1]
    setup_and_render_variant(mode=mode, super_scale=4)
