# Muro lateral izquierdo con un hueco de dos modulos (abertura lateral de las salas): mismos modulos, yaw y luz que muro_izq_128.
# Uso: blender -b -P wall_gap_glb.py -- <gothic_arch.fbx> <salida.glb> [yaw=-45]
# Los huecos miden 24 px de nave (2,68 m); el lab (width 928, ver wall_end_glb.py) los pinta con la cara de corte del tramo
# siguiente. La nave va hacia +y en la escena, como en wall_end_glb.py (la camara mira hacia -y).
import bpy, sys, math, os, bmesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arco_pasante as ap
a = sys.argv[sys.argv.index('--')+1:]
fbx, out = a[0], a[1]
YAW = float(a[2]) if len(a) > 2 else -45
PXM = 17.9
LAT_T = float(os.environ.get('LAT_T', '0.5'))
FLOOR_W = 208/PXM; DEPTH = 48/PXM; DEPTH_L = DEPTH*LAT_T; HEIGHT = 8.0; BAY = 2*128/PXM
GAP = 24/(PXM/2)                                     # 24 px de nave
W, D, H = 0.407, 0.253, 1.0
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
blind = ap.load_module(fbx)
lat = []
HOLE = [int(v) for v in (os.environ.get('HOLE_BAYS') or '2,3').split(',')]   # modulos quitados (2 = 256 px de nave)
for i in range(6):
    if i in HOLE: continue
    o = blind.copy(); sc.collection.objects.link(o)
    o.rotation_euler = (0, 0, math.radians(-90)); o.scale = (BAY/W, DEPTH_L/D, HEIGHT/H)
    o.location = (FLOOR_W/2 + DEPTH_L/2, -(BAY*(0.5 - i) + DEPTH), 0); lat.append(o)
sc.collection.objects.unlink(blind)
bpy.ops.object.select_all(action='DESELECT')
for o in lat: o.select_set(True)
bpy.context.view_layer.objects.active = lat[0]
bpy.ops.object.make_single_user(object=True, obdata=True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.join()
j = bpy.context.view_layer.objects.active
j.rotation_euler = (0, 0, math.radians(YAW)); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
import ghost; ghost.apply(j)
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_yup=True, export_image_format='AUTO', export_materials='EXPORT', use_selection=True)
print("EXPORTED", out, "DIMX", j.dimensions.x)
