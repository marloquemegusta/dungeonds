"""Calibracion: tamano y brillo de Corazon y Exvoto frente a los sprites reales del juego (vista diagonal)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from proto_remate_exvoto_common import *
A = sys.argv[sys.argv.index('--') + 1:]
ROOT, OUT = A[0], A[1]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
hero = make_char(ROOT + '/assets/models/characters/corazon/source/corazon.fbx', 90, 1.0, (0, 0, 0))
exv = make_char(ROOT + '/assets/models/characters/exvoto/source/tripo_convert_45adc30a-3543-42ac-8d24-84872f68cfb7.fbx', -90, EX_K, (5, 0, 0))
load_acts(ROOT)
update()
cam = setup_render()
for nm, ch, key, fr, c in (('hero', hero, 'hero_walk', 9, V((0, 0, 0.9))), ('exv', exv, 'ex_walk', 8, V((5, 0, 0.9)))):
    apply_basis(ch, capture(ch, key, fr))
    ch.mesh.hide_render = False
    other = exv if ch is hero else hero
    other.mesh.hide_render = True
    place_cam(cam, c)
    render_to(os.path.join(OUT, 'calib_%s.png' % nm))
    print('DIMS', nm, tuple(ch.mesh.dimensions))
for nm, ch, key, fr in (('hero', hero, 'hero_walk', 1), ('exv', exv, 'ex_pray', 10)):
    apply_basis(ch, capture(ch, key, fr))
    print('ROOT', nm, tuple(ch.root.location), 'arm scale', tuple(ch.arm.scale), 'parent scale', tuple(ch.root.scale))
    for b in ('Hips', 'Spine', 'Spine2', 'Head', 'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand', 'RightArm', 'RightHand', 'LeftUpLeg', 'LeftFoot', 'RightFoot'):
        print('BONE', nm, b, tuple(round(x, 3) for x in head_world(ch, b)), 'tail', tuple(round(x, 3) for x in tail_world(ch, b)))
# rest pose
for nm, ch in (('hero', hero), ('exv', exv)):
    for pb in ch.arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    update()
    for b in ('Hips', 'Spine', 'Head', 'LeftArm', 'LeftForeArm', 'LeftHand', 'RightArm', 'RightHand', 'LeftFoot'):
        print('REST', nm, b, tuple(round(x, 3) for x in head_world(ch, b)))
