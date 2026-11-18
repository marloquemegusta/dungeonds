"""Mide la altura de la malla en reposo de Corazon y Exvoto para fijar la escala relativa del remate (solo diagnostico)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ds_remate_exvoto_lib import *

A = sys.argv[sys.argv.index('--') + 1:]
ROOT = A[0]
bpy.ops.wm.read_factory_settings(use_empty=True)


def bbox(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    vs, _ = eval_world_mesh(ob, dg)
    xs = [v.x for v in vs]; ys = [v.y for v in vs]; zs = [v.z for v in vs]
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


for nm, path, rz, sc in (('hero', ROOT + '/assets/models/characters/corazon/source/corazon.fbx', 90, 1.0),
                         ('exv', ROOT + '/assets/models/characters/exvoto/source/tripo_convert_45adc30a-3543-42ac-8d24-84872f68cfb7.fbx', -90, 1.0)):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ch = make_char(path, rz, sc, (0, 0, 0))
    update()
    bx, by, bz = bbox(ch.mesh)
    print('MEAS', nm, 'rest x', tuple(round(v, 3) for v in bx), 'y', tuple(round(v, 3) for v in by),
          'z', tuple(round(v, 3) for v in bz), 'h_rest', round(bz[1] - bz[0], 3))
    for b in ('Hips', 'Head', 'LeftArm', 'LeftForeArm', 'LeftHand', 'RightHand', 'LeftFoot', 'RightFoot'):
        print('B', nm, b, tuple(round(x, 3) for x in head_world(ch, b)))
