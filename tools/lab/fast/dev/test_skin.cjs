// Checks the linear skinning against SkinnedMesh.getVertexPosition (three.js) on frame 0 and a mid frame.
const { loadCharacter } = require('../pose.cjs');
(async () => {
  const c = await loadCharacter(process.argv[2], { anim: process.argv[3], inPlace: true, neckPitch: -35, normalStrength: 0.5 });
  const B = c.B;
  for (const t of [0, 0.4]) {
    const f = c.poseAt(t);
    const m = f.meshes[0];
    const v = new B.Vector3(); let maxd = 0;
    const mesh = m.mesh; const pos = mesh.geometry.attributes.position;
    for (let i = 0; i < pos.count; i += 37) {
      mesh.getVertexPosition(i, v); v.applyMatrix4(mesh.matrixWorld);
      maxd = Math.max(maxd, Math.abs(v.x - m.positions[i * 3]), Math.abs(v.y - m.positions[i * 3 + 1]), Math.abs(v.z - m.positions[i * 3 + 2]));
    }
    console.log('t', t, 'max abs diff vs getVertexPosition', maxd.toExponential(2), 'minY', f.minY.toFixed(5));
  }
  let t0 = Date.now(); for (let k = 0; k < 8; k++) c.poseAt(k * c.duration / 8); console.log('8 poses ms', Date.now() - t0);
})().catch(e => { console.error('ERR', e.stack.split('\n').slice(0, 4).join('\n')); process.exit(1); });
