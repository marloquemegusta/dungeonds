import bpy, sys, math
from mathutils import Vector
_a=sys.argv[sys.argv.index("--")+1:]; fbx,out=_a[0],_a[1]; PITCH=float(_a[2]) if len(_a)>2 else -90; YAW=float(_a[3]) if len(_a)>3 else 0
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx)
obj=[o for o in bpy.data.objects if o.type=='MESH'][0]
for o in list(bpy.data.objects):
    if o is not obj: bpy.data.objects.remove(o)
bpy.context.view_layer.objects.active=obj; obj.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
obj.rotation_euler=(math.radians(PITCH),0,math.radians(YAW))
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
vs=[obj.matrix_world@v.co for v in obj.data.vertices]
mn=Vector([min(v[i] for v in vs) for i in range(3)]); mx=Vector([max(v[i] for v in vs) for i in range(3)])
obj.location=Vector((-(mn.x+mx.x)/2,-(mn.y+mx.y)/2,-mn.z)); bpy.ops.object.transform_apply(location=True)
print("DIMS",[round(x,3) for x in (mx-mn)])
for m in obj.data.materials:
    nt=m.node_tree
    for n in nt.nodes:
        if n.type=='BSDF_PRINCIPLED':
            for l in list(nt.links):
                if l.to_node==n and l.to_socket.name in ('Metallic','Roughness','Alpha'): nt.links.remove(l)
            n.inputs['Metallic'].default_value=0.0; n.inputs['Roughness'].default_value=0.85
import bmesh
bm=bmesh.new(); bm.from_mesh(obj.data)
before=sum(1 for f in bm.faces if f.normal.z<0)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
after=sum(1 for f in bm.faces if f.normal.z<0)
bm.to_mesh(obj.data); bm.free(); obj.data.update()
for m in obj.data.materials:
    m.use_backface_culling=False
    try: m.surface_render_method='DITHERED'
    except Exception: pass
    m.blend_method='OPAQUE' if hasattr(m,'blend_method') else None
    [setattr(n.inputs['Alpha'],'default_value',1.0) for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED']
print("NORMALES caras hacia abajo antes",before,"despues",after)
print("SIN_METAL")
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_yup=True, export_image_format='AUTO', export_materials='EXPORT')
