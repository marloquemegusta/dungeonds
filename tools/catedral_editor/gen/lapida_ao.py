# Oscurece los surcos: hornea oclusion ambiental (Cycles) y la multiplica sobre la textura base del GLB.
import bpy, sys, numpy as np
a=sys.argv[sys.argv.index('--')+1:]; src,dst=a[0],a[1]; STRENGTH=float(a[2]) if len(a)>2 else 0.85
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
ob=[o for o in bpy.context.scene.objects if o.type=='MESH'][0]
bpy.context.view_layer.objects.active=ob; ob.select_set(True)
mat=ob.active_material; nt=mat.node_tree
bsdf=[n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'][0]
tex=bsdf.inputs['Base Color'].links[0].from_node; base=tex.image
W,H=base.size; print("textura",W,H)
ao=bpy.data.images.new("ao",W,H,alpha=False,float_buffer=True)
n_ao=nt.nodes.new('ShaderNodeTexImage'); n_ao.image=ao; nt.nodes.active=n_ao
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.samples=64
try:
    sc.cycles.device='GPU'
except Exception: pass
sc.world=bpy.data.worlds.new('w')
# distancia corta: solo las ranuras de la talla (el modelo mide 1 m de alto, la talla es poco profunda)
sc.world.light_settings.distance=0.05
bpy.ops.object.bake(type='AO', margin=4)
A=np.array(ao.pixels[:]).reshape(H,W,4)[:,:,0]
A=np.clip((A-0.35)/0.65,0,1)**1.5           # mas contraste: casi todo blanco, surcos oscuros
B=np.array(base.pixels[:]).reshape(H,W,4)
f=1-STRENGTH*(1-A)
B[:,:,:3]*=f[:,:,None]
out=bpy.data.images.new("base_ao",W,H,alpha=True); out.pixels[:]=B.ravel(); out.file_format='PNG'
out.filepath_raw=dst.replace('.glb','_basecolor.png'); out.save()
tex.image=out; nt.nodes.remove(n_ao)
print("AO media",float(A.mean()),"min",float(A.min()))
bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', export_image_format='AUTO')
print("AO_OK",dst)
