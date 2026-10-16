/**
 * Comprehensive verification test for glb_loader_minimal.js and seed_catalog_data.js
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const LAB_DIR = __dirname;
const MinimalGLBLoader = require('./glb_loader_minimal.js');
const SEED_CATALOG = require('./seed_catalog_data.js');

console.log('--- 1. Testing glb_loader_minimal.js ---');
assert(typeof MinimalGLBLoader.parseGLBContainer === 'function', 'parseGLBContainer should be function');
assert(typeof MinimalGLBLoader.parseGLBToMeshData === 'function', 'parseGLBToMeshData should be function');
assert(typeof MinimalGLBLoader.buildThreeMeshFromGLB === 'function', 'buildThreeMeshFromGLB should be function');

const testGlbPath = path.resolve(__dirname, '../../assets/blender_combat_demo/weapons/carbine.glb');
const carbineBuf = fs.readFileSync(testGlbPath);
const carbineData = MinimalGLBLoader.parseGLBToMeshData(carbineBuf);
assert(carbineData.positions instanceof Float32Array, 'positions should be Float32Array');
assert(carbineData.normals instanceof Float32Array, 'normals should be Float32Array');
assert(carbineData.uvs instanceof Float32Array, 'uvs should be Float32Array');
assert(carbineData.indices instanceof Uint32Array, 'indices should be Uint32Array');
assert(carbineData.positions.length > 0, 'positions should not be empty');
assert.equal(carbineData.positions.length, carbineData.normals.length, 'pos and norm length match');
assert.equal(carbineData.positions.length / 3, carbineData.uvs.length / 2, 'pos and uv count match');
console.log('✓ MinimalGLBLoader verified with carbine.glb');

console.log('\n--- 2. Testing seed_catalog_data.js File Size ---');
const catalogPath = path.join(LAB_DIR, 'seed_catalog_data.js');
const stats = fs.statSync(catalogPath);
const sizeMb = stats.size / (1024 * 1024);
console.log(`Catalog file size: ${stats.size} bytes (${sizeMb.toFixed(2)} MB)`);
assert(stats.size < 2.5 * 1024 * 1024, `Catalog must be < 2.5 MB, got ${sizeMb.toFixed(2)} MB`);
console.log('✓ File size is under 2.5 MB budget');

console.log('\n--- 3. Testing Weapons in SEED_CATALOG ---');
const expectedWeapons = [
  { id: 'ak47', name: 'AK-47 Assault Rifle', type: 'rifle' },
  { id: 'carbine', name: 'M4 Carbine', type: 'rifle' },
  { id: 'battle_rifle', name: 'Battle Rifle', type: 'rifle' },
  { id: 'smg', name: 'Tactical SMG', type: 'rifle' },
  { id: 'gothic_sword', name: 'Gothic Broadsword', type: 'sword' }
];

assert.equal(SEED_CATALOG.weapons.length, 5, 'Should have exactly 5 weapons');
for (const exp of expectedWeapons) {
  const w = SEED_CATALOG.getWeapon(exp.id);
  assert(w, `Weapon ${exp.id} must exist`);
  assert.equal(w.name, exp.name, `Weapon ${exp.id} name mismatch`);
  assert.equal(w.type, exp.type, `Weapon ${exp.id} type mismatch`);
  assert(w.positionsB64 && w.normalsB64 && w.uvsB64 && w.indicesB64, `Weapon ${exp.id} missing b64 buffers`);

  const meshData = SEED_CATALOG.getWeaponMeshData(exp.id);
  assert(meshData.positions instanceof Float32Array, 'positions Float32Array');
  assert(meshData.normals instanceof Float32Array, 'normals Float32Array');
  assert(meshData.uvs instanceof Float32Array, 'uvs Float32Array');
  assert(meshData.indices instanceof Uint16Array, 'indices Uint16Array');

  const vertCount = meshData.positions.length / 3;
  assert.equal(vertCount, w.vertexCount, 'vertexCount matches');
  assert.equal(meshData.indices.length / 3, w.triangleCount, 'triangleCount matches');

  // Verify normal vectors are valid unit vectors
  for (let i = 0; i < vertCount; i++) {
    const nx = meshData.normals[i * 3 + 0];
    const ny = meshData.normals[i * 3 + 1];
    const nz = meshData.normals[i * 3 + 2];
    const len = Math.hypot(nx, ny, nz);
    assert(Math.abs(len - 1.0) < 0.1, `Normal at vert ${i} not normalized: ${len}`);
  }

  // Verify indices are within bounds
  for (let i = 0; i < meshData.indices.length; i++) {
    assert(meshData.indices[i] < vertCount, `Index ${i} (${meshData.indices[i]}) out of bounds (max ${vertCount})`);
  }

  console.log(`✓ Weapon: ${w.id} (${w.name}) - ${vertCount} verts, ${w.triangleCount} tris, bounds checked`);
}

console.log('\n--- 4. Testing Animations in SEED_CATALOG ---');
const expectedAnims = [
  { id: 'rifle_idle', cat: 'Rifle', name: 'Rifle Aiming Idle' },
  { id: 'rifle_aim', cat: 'Rifle', name: 'Rifle Aim Fire' },
  { id: 'rifle_walk', cat: 'Rifle', name: 'Rifle Walk' },
  { id: 'rifle_run', cat: 'Rifle', name: 'Rifle Run Forward' },
  { id: 'rifle_crouch_walk', cat: 'Rifle', name: 'Rifle Crouch Walk' },
  { id: 'melee_slash', cat: 'Melee', name: 'Sword Slash' },
  { id: 'melee_crouch_slash', cat: 'Melee', name: 'Crouch Slash' },
  { id: 'melee_jump_hit', cat: 'Melee', name: 'Jump Attack' },
  { id: 'locomotion_run', cat: 'Locomotion', name: 'Heavy Run' },
  { id: 'combat_death', cat: 'Combat', name: 'Death Fall' }
];

assert.equal(SEED_CATALOG.animations.length, 10, 'Should have exactly 10 animations');
for (const exp of expectedAnims) {
  const a = SEED_CATALOG.getAnimation(exp.id);
  assert(a, `Animation ${exp.id} must exist`);
  assert.equal(a.category, exp.cat, `Animation ${exp.id} category mismatch`);
  assert.equal(a.name, exp.name, `Animation ${exp.id} name mismatch`);
  assert(a.duration > 0, `Animation ${exp.id} duration must be positive`);
  assert(a.fps >= 24, `Animation ${exp.id} fps must be >= 24`);
  assert(a.hipsRestPosition && a.hipsRestPosition.length === 3, `Animation ${exp.id} missing hipsRestPosition`);
  assert(a.boneRestPose && Object.keys(a.boneRestPose).length > 0, `Animation ${exp.id} missing boneRestPose`);
  assert(a.tracks.length > 0, `Animation ${exp.id} must have tracks`);

  // Verify track integrity
  for (const tr of a.tracks) {
    assert(tr.bone, `Track missing bone in ${exp.id}`);
    assert(tr.type === 'quaternion' || tr.type === 'position', `Unknown track type: ${tr.type}`);
    assert(Array.isArray(tr.values) && tr.values.length > 0, `Track values empty in ${exp.id}`);
    for (const val of tr.values) {
      assert(!isNaN(val) && isFinite(val), `NaN/Inf track value in ${exp.id}`);
    }
  }

  console.log(`✓ Animation: ${a.id} [${a.category}] "${a.name}" - ${a.duration}s, ${a.numFrames} frames, ${a.tracks.length} tracks, Hips rest: [${a.hipsRestPosition.join(', ')}]`);
}

console.log('\n--- 5. Testing Three.js Integration (buildWeaponMesh & createAnimationClip) ---');
const html = fs.readFileSync(path.join(LAB_DIR, 'FBX-Web-Renderer-offline.html'), 'utf8');
const bundle = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));

function imageStub() {
  const handlers = {};
  return {
    addEventListener: (type, fn) => handlers[type] = fn,
    removeEventListener() {},
    set src(value) { if (handlers.load) handlers.load.call(this); },
    width: 1, height: 1
  };
}

const context = {
  console: { log: () => {}, warn: () => {}, error: () => {} },
  URL: { createObjectURL: () => 'blob:mock' }, Blob: function() {},
  TextDecoder, TextEncoder, Buffer, setTimeout, clearTimeout, performance,
  document: { createElement: () => ({ relList: { supports: () => true } }), createElementNS: () => imageStub() },
  window: { URL: { createObjectURL: () => 'blob:mock' } }, self: {}, require
};

const threeMock = vm.runInNewContext(
  bundle.slice(0, bundle.indexOf('var tp=8')) +
  '\n({BufferGeometry:Jr, BufferAttribute:Nr, MeshStandardMaterial:Xa, Color:X, Mesh:vi, AnimationClip:wo, QuaternionKeyframeTrack:xo, VectorKeyframeTrack:Co, TextureLoader:function(){return {load:()=>({})};}});',
  context
);

// Test buildWeaponMesh for all 5 weapons
for (const exp of expectedWeapons) {
  const mesh = SEED_CATALOG.buildWeaponMesh(exp.id, threeMock);
  assert(mesh, `Mesh for ${exp.id} should be created`);
  assert(mesh.isMesh, `Mesh for ${exp.id} should have isMesh = true`);
  assert(mesh.geometry.attributes.position.count > 0, 'position count > 0');
  assert(mesh.geometry.attributes.normal.count > 0, 'normal count > 0');
  assert(mesh.geometry.attributes.uv.count > 0, 'uv count > 0');
  assert(mesh.geometry.index.count > 0, 'index count > 0');
  console.log(`✓ THREE.Mesh built: ${exp.id} (geom verts: ${mesh.geometry.attributes.position.count}, tris: ${mesh.geometry.index.count / 3})`);
}

// Test createAnimationClip for all 10 animations
for (const exp of expectedAnims) {
  const clip = SEED_CATALOG.createAnimationClip(exp.id, threeMock, 'mixamorig');
  assert(clip, `Clip for ${exp.id} should be created`);
  assert(clip.duration > 0, `Clip duration must be positive`);
  assert(clip.tracks.length > 0, `Clip tracks must not be empty`);
  assert(clip.tracks[0].name.startsWith('mixamorig'), `Clip track should have rigPrefix applied`);
  console.log(`✓ THREE.AnimationClip created: ${exp.id} ("${clip.name}", duration: ${clip.duration.toFixed(2)}s, tracks: ${clip.tracks.length})`);
}

console.log('\n========================================');
console.log('ALL VERIFICATION CHECKS PASSED PERFECTLY!');
console.log('========================================');
