# Remate de sala: muro del fondo (5 modulos gothic_arch de cara a la camara, el central ciego o pasante) + el muro
# izquierdo que llega hasta el, en una sola escena para el lab (mismo yaw -45, misma luz y escala que muro_izq_128).
# Uso: blender -b -P wall_end_glb.py -- <gothic_arch.fbx> <salida.glb> <ciego|pasante> [yaw=-45]
# Unidades: 17,9 px/m en horizontal de pantalla, 8,95 px/m a lo largo de la nave.
#   x = ancho de la nave, y = largo (la camara mira hacia -y: el fondo esta en y=0..-DEPTH, la nave hacia +y), z = alto.
import bpy, sys, math, os, bmesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arco_pasante as ap
a = sys.argv[sys.argv.index('--')+1:]
fbx, out, mode = a[0], a[1], a[2]
YAW = float(a[3]) if len(a) > 3 else -45
SIDE = float(a[4]) if len(a) > 4 else -1   # lado del muro lateral en x (-1 = izquierdo de la escena)
PXM = 17.9
FLOOR_W = 208/PXM            # ancho del suelo entre muros laterales
DEPTH = 48/PXM               # grosor de los muros laterales (y referencia de fase del lateral)
LAT_T = float(os.environ.get('LAT_T', '0.5'))   # grosor del lateral respecto a 48 px (cara interior fija)
DEPTH_L = DEPTH*LAT_T
DEPTH_B = DEPTH*float(os.environ.get('BACK_T', '0.5'))           # grosor del muro del fondo (mitad)
HEIGHT = 8.0
BAY = 2*128/PXM              # modulo del muro lateral (128 px de nave)
N_BACK = 5
BACK_W = 48/PXM              # ancho de cada modulo del fondo (6 tiles)
W, D, H = 0.407, 0.253, 1.0  # medidas del modulo original
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
blind = ap.load_module(fbx)
if mode == 'pasante':
    centre = blind.copy(); centre.data = blind.data.copy(); sc.collection.objects.link(centre)
    ap.cut_arch(centre, half_w=0.112)
else:
    centre = blind
objs = []
def put(src, rot, scale, loc):
    o = src.copy(); o.data = src.data   # comparten malla; make_single_user mas abajo
    sc.collection.objects.link(o); o.rotation_euler = (0, 0, math.radians(rot)); o.scale = scale; o.location = loc
    return o
Y0 = 0.0
lat = []
for i in range(4):           # muro lateral: juntas en Y0 - k*BAY, termina en el plano trasero del fondo
    lat.append(put(blind, -90*SIDE, (BAY/W, DEPTH_L/D, HEIGHT/H), (SIDE*(FLOOR_W/2 + DEPTH_L/2), -(BAY*(0.5 - i) + DEPTH), 0)))
back = []
for k in range(N_BACK):
    src = centre if k == N_BACK//2 else blind
    back.append(put(src, 180, (BACK_W/W, DEPTH_B/D, HEIGHT/H), ((k-(N_BACK-1)/2)*BACK_W, -DEPTH_B/2, 0)))
for o in (blind, centre):
    if o.name in sc.collection.objects: sc.collection.objects.unlink(o)
# Rellenos de junta: los modulos son tangentes y entre ellos se ve el vacio (1-2 px); una losa estrecha de piedra en cada
# junta, dentro del grosor del muro, lo cierra sin solapar caras coplanares (que parpadean al rasterizar).
stone = bpy.data.materials.new('relleno'); stone.use_nodes = True
pb = [n for n in stone.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]
pb.inputs['Base Color'].default_value = tuple(ap.srgb_to_lin(c) for c in ap.STONE_SRGB) + (1,)
pb.inputs['Roughness'].default_value = 0.9
for k in range(N_BACK - 1):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((k - (N_BACK - 2)/2)*BACK_W, -DEPTH_B*0.5, HEIGHT*0.49))
    f = bpy.context.active_object; f.scale = (0.30, DEPTH_B*0.7, HEIGHT*0.98); f.data.materials.append(stone)
    back.append(f)
def join(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.make_single_user(object=True, obdata=True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.join()
    return bpy.context.view_layer.objects.active
L = join(lat)
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
bm = bmesh.new(); bm.from_mesh(L.data)
bmesh.ops.bisect_plane(bm, geom=bm.verts[:]+bm.edges[:]+bm.faces[:], plane_co=(0, -DEPTH_B, 0), plane_no=(0, -1, 0), clear_outer=True)
bm.to_mesh(L.data); bm.free()
B = join(back)
bpy.ops.object.select_all(action='DESELECT'); L.select_set(True); B.select_set(True)
bpy.context.view_layer.objects.active = L; bpy.ops.object.join()
j = bpy.context.view_layer.objects.active
j.rotation_euler = (0, 0, math.radians(YAW)); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
import ghost; ghost.apply(j)
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_yup=True, export_image_format='AUTO', export_materials='EXPORT', use_selection=True)
print("EXPORTED", out, "DIMX", j.dimensions.x)
