# Fila de modulos gothic_arch (muro izquierdo, cara del arco hacia la nave +X) para renderizar en el lab.
import bpy, sys, math
a=sys.argv[sys.argv.index('--')+1:]; fbx,out=a[0],a[1]; N=int(a[2]) if len(a)>2 else 7; YAW=float(a[3]) if len(a)>3 else 0
PXM=17.9; BAY=2*128/PXM; DEPTH=48/PXM; HEIGHT=8.0
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
bpy.ops.import_scene.fbx(filepath=fbx)
src=[o for o in sc.objects if o.type=='MESH'][0]
for o in list(sc.objects):
    if o is not src: bpy.data.objects.remove(o)
src.parent=None; bpy.context.view_layer.objects.active=src; src.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for m in src.data.materials:
    for n in m.node_tree.nodes:
        if n.type=='BSDF_PRINCIPLED':
            for l in list(m.node_tree.links):
                if l.to_node==n and l.to_socket.name=='Metallic': m.node_tree.links.remove(l)
            n.inputs['Metallic'].default_value=0
W,D,H=0.407,0.253,1.0
objs=[]
for i in range(N):
    o=src.copy(); sc.collection.objects.link(o)
    o.rotation_euler=(0,0,math.radians(90)); o.scale=(BAY/W, DEPTH/D, HEIGHT/H)
    o.location=(DEPTH/2, (i-(N-1)/2)*BAY, 0); objs.append(o)
sc.collection.objects.unlink(src)
bpy.ops.object.select_all(action='DESELECT')
for o in objs: o.select_set(True)
bpy.context.view_layer.objects.active=objs[0]
bpy.ops.object.make_single_user(object=True, obdata=True)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.join()
j=bpy.context.view_layer.objects.active; j.rotation_euler=(0,0,math.radians(YAW)); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_yup=True, export_image_format='AUTO', export_materials='EXPORT', use_selection=True)
print("EXPORTED", out)
