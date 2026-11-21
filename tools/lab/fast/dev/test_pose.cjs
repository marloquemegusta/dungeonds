const { loadCharacter } = require('../pose.cjs');
const fbx = process.argv[2], anim = process.argv[3], normScale = process.argv[4] ? parseFloat(process.argv[4]) : 0;
(async () => {
  const t0 = Date.now();
  const c = await loadCharacter(fbx, { anim, inPlace: true, neckPitch: -35, normScale: 0, normalStrength: 0.5 });
  console.log('load ms', Date.now() - t0, 'clip', c.clipLabel, 'dur', c.duration, 'normScale', c.normScale, 'clips', c.clips);
  console.log('meshes', c.meshes.length, 'mats', c.renderMaterials.length, c.renderMaterials.map(m => ({ c: m.color.map(x => +x.toFixed(3)), map: m.map && [m.map.width, m.map.height], nmap: !!m.normalMap })));
  const t1 = Date.now();
  const f = c.poseAt(0);
  console.log('pose ms', Date.now() - t1, 'minY', f.minY, 'verts', f.meshes[0].positions.length / 3);
  const p = f.meshes[0].positions;
  let mn = [Infinity, Infinity, Infinity], mx = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < p.length; i += 3) for (let a = 0; a < 3; a++) { mn[a] = Math.min(mn[a], p[i + a]); mx[a] = Math.max(mx[a], p[i + a]); }
  console.log('bbox', mn.map(v => v.toFixed(3)), mx.map(v => v.toFixed(3)));
  const n = f.meshes[0].normals; let bad = 0; for (let i = 0; i < n.length; i += 3) { const l = Math.hypot(n[i], n[i + 1], n[i + 2]); if (Math.abs(l - 1) > 1e-3) bad++; }
  console.log('normals not unit', bad);
})().catch(e => { console.error('ERR', e.name, e.message); console.error(e.stack.split('\n').slice(0, 5).join('\n')); process.exit(1); });
