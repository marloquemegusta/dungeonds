const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

// 1. Load splicer module
const splicer = require('./fbx_binary_splicer.js');

// 2. Load Three.js FBXLoader from FBX-Web-Renderer-offline.html
const html = fs.readFileSync(path.join(__dirname, 'FBX-Web-Renderer-offline.html'), 'utf8');
const bundle = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));

function imageStub() {
  const handlers = {};
  return {
    addEventListener: (t, fn) => { handlers[t] = fn; },
    removeEventListener() {},
    set src(v) {
      if (handlers.load) {
        // Run synchronously to avoid dangling async timers
        handlers.load.call(this);
      }
    },
    width: 1,
    height: 1
  };
}

const context = {
  console, URL, Blob, TextDecoder, TextEncoder, Buffer, setTimeout, clearTimeout, performance,
  document: { createElement: () => ({ relList: { supports: () => true } }), createElementNS: () => imageStub() },
  window: { URL }, self: {}, require
};

const api = vm.runInNewContext(
  bundle.slice(0, bundle.indexOf('var tp=8')) +
  '\n({Loader:cf,Mixer:Ts,Box:hr,Vector:K,Group:Kn,Scene:er,normalize:Lf});',
  context
);

console.log('=== FBX Binary Splicer Test & Verification ===');

// 3. Load spacemarine.fbx
const fbxPath = path.resolve('assets/characters/spacemarine/spacemarine.fbx');
const originalBuf = fs.readFileSync(fbxPath);
console.log(`Loaded ${fbxPath} (${(originalBuf.length / (1024 * 1024)).toFixed(2)} MB)`);

// 4. Test parseFBXBinary
const parsed = splicer.parseFBXBinary(originalBuf);
console.log(`Parsed FBX v${parsed.version}, root nodes: ${parsed.nodes.length}`);
console.log(`Indexed models: ${parsed.modelsById.size}, bones: ${parsed.bonesByName.size}`);

// Verify right hand bone exists
const rightHand = parsed.bonesByName.get('mixamorig:RightHand');
assert(rightHand, 'Could not find mixamorig:RightHand bone in FBX index');
console.log(`Found mixamorig:RightHand (ID: ${rightHand.id}, parentId: ${rightHand.parentId})`);

// 5. Test spliceAndExportFBX with Weapon & Baked Animation
console.log('\n--- Splicing Weapon Mesh and Baked Animation ---');

const positions = new Float32Array([
  -2.0,  0.0, -1.0,
   2.0,  0.0, -1.0,
   0.0,  0.0,  2.0,
  -0.5, 30.0, -0.2,
   0.5, 30.0, -0.2,
   0.0, 35.0,  0.5
]);

const indices = new Uint32Array([
  0, 1, 2,
  0, 3, 4,  0, 4, 1,
  1, 4, 5,  1, 5, 2,
  2, 5, 3,  2, 3, 0,
  3, 5, 4
]);

const normals = new Float32Array(positions.length);
for (let i = 0; i < normals.length; i += 3) {
  normals[i] = positions[i] * 0.1;
  normals[i + 1] = 1.0;
  normals[i + 2] = positions[i + 2] * 0.1;
}

const uvs = new Float32Array([
  0.0, 0.0,
  1.0, 0.0,
  0.5, 0.2,
  0.1, 0.8,
  0.9, 0.8,
  0.5, 1.0
]);

const dummyPng = new Uint8Array([
  0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
  0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
  0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
  0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89,
  0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41, 0x54,
  0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00, 0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4,
  0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,
  0xAE, 0x42, 0x60, 0x82
]);

const clipDuration = 1.0;
const times = [0.0, 0.25, 0.5, 0.75, 1.0];

const rightHandTrack = {
  modelId: rightHand.id,
  T: [
    [0.0, 0.0, 0.0],
    [5.0, 2.0, 1.0],
    [10.0, 4.0, 2.0],
    [5.0, 2.0, 1.0],
    [0.0, 0.0, 0.0]
  ],
  R: [
    [0.0, 0.0, 0.0],
    [15.0, 30.0, 0.0],
    [30.0, 60.0, 10.0],
    [15.0, 30.0, 0.0],
    [0.0, 0.0, 0.0]
  ]
};

const hips = parsed.bonesByName.get('mixamorig:Hips');
const hipsTrack = {
  modelId: hips ? hips.id : 0n,
  T: [
    [0.0, 95.0, 0.0],
    [0.0, 96.0, 5.0],
    [0.0, 97.0, 10.0],
    [0.0, 96.0, 5.0],
    [0.0, 95.0, 0.0]
  ]
};

const options = {
  weapon: {
    name: 'PowerSword_Alpha',
    positions,
    normals,
    uvs,
    indices,
    color: [0.1, 0.8, 1.0],
    materials: [
      { name: 'PowerSword_Blade', color: [0.1, 0.8, 1.0], pngBytes: dummyPng, mimeType: 'image/png', fileName: 'Blade.PNG' },
      { name: 'PowerSword_Grip', color: [0.4, 0.3, 0.2], pngBytes: dummyPng, mimeType: 'image/png', fileName: 'Grip.PNG' }
    ],
    groups: [
      { start: 0, count: 3, materialIndex: 0 },
      { start: 3, count: indices.length - 3, materialIndex: 1 }
    ]
  },
  parentBoneId: rightHand.id,
  clips: [
    {
      name: 'Slash_Attack',
      duration: clipDuration,
      times,
      tracks: [rightHandTrack, hipsTrack]
    }
  ]
};

assert.throws(() => splicer.spliceAndExportFBX(originalBuf, {
  parentBoneId: rightHand.id,
  weapon: { ...options.weapon, groups: [{ start: 0, count: 2, materialIndex: 0 }] }
}), /groups/i, 'invalid material groups fail clearly instead of corrupting the FBX');

const splicedBuf = splicer.spliceAndExportFBX(originalBuf, options);
console.log(`Exported spliced FBX size: ${(splicedBuf.byteLength / (1024 * 1024)).toFixed(2)} MB`);

// 6. Parse with Three.js FBXLoader
console.log('\n--- Verifying with Three.js FBXLoader ---');
const splicedModel = new api.Loader().parse(splicedBuf, '');
assert(splicedModel, 'FBXLoader failed to parse spliced FBX');

// Check Animations
console.log(`Animations parsed: ${splicedModel.animations.length}`);
assert.strictEqual(splicedModel.animations.length, 1, 'Expected exactly 1 animation clip');
const clip = splicedModel.animations[0];
console.log(`Clip name: "${clip.name}", duration: ${clip.duration}s, tracks: ${clip.tracks.length}`);
assert.strictEqual(clip.name, 'Slash_Attack', 'Clip name mismatch');
assert(Math.abs(clip.duration - clipDuration) < 0.01, 'Clip duration mismatch');
assert(clip.tracks.length > 0, 'No animation tracks generated in clip');

for (const track of clip.tracks) {
  console.log(`  Track: ${track.name} (type: ${track.constructor.name}, keyframes: ${track.times.length})`);
}

// Check Hierarchy and Weapon Mesh
console.log('\n--- Verifying Scene Hierarchy & Weapon Attachment ---');
let foundWeapon = null;
let foundRightHandBone = null;

splicedModel.traverse(node => {
  if (node.name === 'PowerSword_Alpha') {
    foundWeapon = node;
  }
  if (node.name === 'mixamorigRightHand') {
    foundRightHandBone = node;
  }
});

assert(foundRightHandBone, 'Could not find mixamorigRightHand bone in Three.js hierarchy');
console.log(`Found RightHand bone: "${foundRightHandBone.name}"`);

assert(foundWeapon, 'Could not find injected weapon node in Three.js hierarchy');
console.log(`Found injected weapon: "${foundWeapon.name}" (type: ${foundWeapon.type})`);

// Verify parent relationship
console.log(`Weapon parent: "${foundWeapon.parent ? foundWeapon.parent.name : 'none'}"`);
assert.strictEqual(foundWeapon.parent, foundRightHandBone, 'Weapon parent is NOT RightHand bone!');

// Verify Geometry
assert(foundWeapon.geometry, 'Weapon has no geometry');
const posAttr = foundWeapon.geometry.getAttribute('position');
assert(posAttr, 'Weapon geometry has no position attribute');
console.log(`Weapon vertices count: ${posAttr.count}`);
assert.strictEqual(posAttr.count, indices.length, 'Weapon vertex count should match polygon vertex index');

// Verify per-face materials and embedded maps survive binary FBX round-trip.
assert(foundWeapon.material, 'Weapon has no material');
console.log(`Weapon material type: ${foundWeapon.material.type}`);
assert(Array.isArray(foundWeapon.material), 'Weapon exposes one material for each imported material slot');
assert.equal(foundWeapon.material.length, 2, 'both weapon materials are imported');
assert(foundWeapon.material.every(m => m.map), 'each weapon material retains its embedded texture map');
assert(foundWeapon.geometry.groups.length >= 2, 'geometry retains material groups');
assert(foundWeapon.geometry.groups.every(g => g.materialIndex >= 0 && g.materialIndex < foundWeapon.material.length),
  'each geometry group references a valid material');
const splicedAst = splicer.parseFBXBinary(splicedBuf);
const exportedWeaponMats = splicedAst.nodes.find(n => n.name === 'Objects').children
  .filter(n => n.name === 'Material' && /PowerSword_/.test(String(n.props[1]?.value || '')));
const exportedWeaponTextures = splicedAst.nodes.find(n => n.name === 'Objects').children
  .filter(n => n.name === 'Texture' && /PowerSword_/.test(String(n.props[1]?.value || '')));
assert.equal(exportedWeaponMats.length, 2, 'FBX contains both named weapon material nodes');
assert.equal(exportedWeaponTextures.length, 2, 'FBX contains both named weapon texture nodes');

console.log('\n>>> FBX BINARY SPLICER REGRESSIONS PASSED <<<');
process.exit(0);
