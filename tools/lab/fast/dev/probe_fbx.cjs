const fs = require('node:fs');
const T = require('../../offline_three.cjs');
const file = process.argv[2];
const buf = fs.readFileSync(file);
const t0 = Date.now();
const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
const loader = new T.FBXLoader();
let obj;
try { obj = loader.parse(ab, ''); } catch (e) { console.log('parse error', e.message); process.exit(1); }
console.log('parse ms', Date.now() - t0, 'animations', obj.animations.map(a => a.name + ' ' + a.duration.toFixed(3) + ' tracks ' + a.tracks.length));
const meshes = []; const bones = []; let skinned = 0;
obj.traverse(n => { if (n.isMesh) meshes.push(n.name + (n.isSkinnedMesh ? '[skin]' : '') + ' v=' + n.geometry.attributes.position.count + ' mat=' + (Array.isArray(n.material) ? n.material.map(m => m.type).join(',') : n.material.type)); if (n.isBone) bones.push(n.name); });
console.log('meshes', meshes.length, meshes.slice(0, 8));
console.log('bones', bones.length, bones.slice(0, 5));
const mats = new Set(); obj.traverse(n => { if (n.isMesh) (Array.isArray(n.material) ? n.material : [n.material]).forEach(m => mats.add(m)); });
for (const m of mats) console.log('mat', m.name, m.type, 'map', !!m.map, 'nmap', !!m.normalMap, 'emMap', !!m.emissiveMap, 'color', m.color && m.color.getHexString && m.color.getHexString(), 'rough', m.roughness, 'metal', m.metalness, 'emI', m.emissiveIntensity, m.map && m.map.image ? ('img ' + (m.map.image.width) + 'x' + m.map.image.height + ' ' + Object.keys(m.map.image).join('|')) : '');
