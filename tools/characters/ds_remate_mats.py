import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ds_remate_exvoto_lib import *

A = sys.argv[sys.argv.index('--') + 1:]
ROOT = A[0]
bpy.ops.wm.read_factory_settings(use_empty=True)
ch = make_char(ROOT + '/assets/models/characters/exvoto/source/tripo_convert_45adc30a-3543-42ac-8d24-84872f68cfb7.fbx', -90, 1.0, (0, 0, 0))
update()
me = ch.mesh.data
print('VERTS', len(me.vertices), 'POLYS', len(me.polygons), 'MATS', [m.name if m else None for m in me.materials])
dg = bpy.context.evaluated_depsgraph_get()
ev = ch.mesh.evaluated_get(dg)
m2 = ev.to_mesh()
from collections import defaultdict
cnt = defaultdict(int)
zs = defaultdict(list)
ys = defaultdict(list)
for p in m2.polygons:
    cnt[p.material_index] += 1
for v in m2.vertices:
    zs['all'].append(v.co.z)
for k in sorted(cnt):
    print('MAT', k, 'faces', cnt[k])
# bounds per material via polygons
for k in sorted(cnt):
    vs = set()
    for p in m2.polygons:
        if p.material_index == k:
            vs.update(p.vertices)
    if vs:
        co = [m2.vertices[i].co for i in vs]
        print('BOUNDS mat', k, 'x', round(min(c.x for c in co), 3), round(max(c.x for c in co), 3),
              'y', round(min(c.y for c in co), 3), round(max(c.y for c in co), 3),
              'z', round(min(c.z for c in co), 3), round(max(c.z for c in co), 3))
ev.to_mesh_clear()
