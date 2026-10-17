const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const splicer = require('./fbx_binary_splicer.js');
const SEED_CATALOG = require('./seed_catalog_data.js');
const RetargetAndIKEngine = require('./retarget_and_ik_engine.js');

const html = fs.readFileSync(path.join(__dirname, 'FBX-Web-Renderer-offline.html'), 'utf8');
const bundle = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));
const idx = bundle.indexOf('var tp=8');
const lib = bundle.slice(0, idx);

function imageStub() {
  const handlers = {};
  return {
    addEventListener: (t, fn) => { handlers[t] = fn; },
    removeEventListener() {},
    set src(v) { if (handlers.load) handlers.load.call(this); },
    width: 1, height: 1
  };
}

const context = {
  console, URL, Blob, TextDecoder, TextEncoder, Buffer, setTimeout, clearTimeout, performance,
  document: { createElement: () => ({ relList: { supports: () => true } }), createElementNS: () => imageStub() },
  window: { URL }, self: {}, require
};

const exportExpr = `({
  Vector2: G, Vector3: K, Vector4: mn, Quaternion: Xt, Euler: On, Matrix3: q, Matrix4: Y,
  Box3: hr, Color: X, Object3D: Gn, Group: Kn, Scene: er, Bone: ji, Skeleton: Fi,
  Mesh: vi, SkinnedMesh: Ai, BufferGeometry: Jr, BufferAttribute: Mr,
  Float32BufferAttribute: Ir, Uint16BufferAttribute: Pr, Uint32BufferAttribute: Fr,
  MeshStandardMaterial: Xa, MeshPhongMaterial: Za, MeshBasicMaterial: oi,
  LineBasicMaterial: Bi, Line: Ji, Texture: pn,
  AnimationMixer: Ts, AnimationClip: wo, VectorKeyframeTrack: Co, QuaternionKeyframeTrack: xo, NumberKeyframeTrack: yo,
  PerspectiveCamera: Xo, WebGLRenderer: Ju, AmbientLight: is, DirectionalLight: rs,
  Clock: Es, OrbitControls: ad, FBXLoader: cf, MathUtils: Yt, JSZip: Nf.default
})`;

const THREE = vm.runInNewContext(lib + '\n;' + exportExpr, context);
const engine = RetargetAndIKEngine(THREE);

// 1. Load spacemarine.fbx
const charPath = path.resolve(__dirname, '../../assets/characters/spacemarine/spacemarine.fbx');
const charBytes = fs.readFileSync(charPath);
const charAb = charBytes.buffer.slice(charBytes.byteOffset, charBytes.byteOffset + charBytes.byteLength);

const parsedFbx = splicer.parseFBXBinary(charAb);
const charModel = new THREE.FBXLoader().parse(charAb.slice(0), '');
const rigMap = engine.mapHumanoidSkeleton(charModel);

// 2. Auto-align AK47 to RightHand
const akData = SEED_CATALOG.getWeaponMeshData('ak47');
const alignRes = engine.autoAlignWeaponGeometry(akData, rigMap, { type: 'rifle', scaleMultiplier: 1.0 });

// Transform AK47 positions & normals by alignRes.localMatrix4 into RightHand local space
const posOut = new Float32Array(akData.positions.length);
const normOut = new Float32Array(akData.normals.length);
const v = new THREE.Vector3();
const normalMat = new THREE.Matrix3().getNormalMatrix(alignRes.localMatrix4);
for (let i = 0; i < akData.positions.length; i += 3) {
  v.set(akData.positions[i], akData.positions[i + 1], akData.positions[i + 2]).applyMatrix4(alignRes.localMatrix4);
  posOut[i] = v.x; posOut[i + 1] = v.y; posOut[i + 2] = v.z;
  v.set(akData.normals[i], akData.normals[i + 1], akData.normals[i + 2]).applyMatrix3(normalMat).normalize();
  normOut[i] = v.x; normOut[i + 1] = v.y; normOut[i + 2] = v.z;
}

// 3. Prepare & Bake rifle_run animation with Left-Hand IK + Finger Grip + Grounding
const animEntry = SEED_CATALOG.getAnimation('rifle_run');
const retargetCtx = engine.prepareAnimationRetarget(rigMap, animEntry);
const weaponCtx = {
  localMatrix4: alignRes.localMatrix4,
  foregripLocalPos: alignRes.foregripLocalPos,
  attachBoneName: 'RightHand'
};
const baked = engine.bakeClipToFBXTracks(rigMap, retargetCtx, {
  bakeFps: 24,
  inPlaceLock: 1.0,
  groundFeet: true,
  leftHandIkWeight: 1.0,
  rightHandGrip: 1.0,
  leftHandGrip: 1.0
}, weaponCtx);
assert(Math.abs(baked.times.at(-1) - baked.duration) < 1e-7, 'baked clip includes the exact terminal sample');
assert.equal(baked.frameCount, baked.times.length, 'reported bake frame count matches time samples');
for (const track of baked.tracksList) {
  for (const axis of ['x', 'y', 'z']) {
    const values = track.rotation[axis];
    assert.equal(values.length, baked.frameCount, `${track.canonicalName}.${axis} rotation has every sample`);
    for (let i = 1; i < values.length; i++) {
      assert(Math.abs(values[i] - values[i - 1]) <= 180.001,
        `${track.canonicalName}.${axis} has no wrapped Euler jump at frame ${i}`);
    }
  }
}

// 4. Splice & Export FBX Binary 7400
const rightHandBone = rigMap.bones.RightHand;
const rightHandId = BigInt(rightHandBone.ID);
let pngBytes = null;
const akMeta = SEED_CATALOG.getWeapon('ak47');
if (akMeta.texture && akMeta.texture.includes('base64,')) {
  pngBytes = new Uint8Array(Buffer.from(akMeta.texture.split('base64,')[1], 'base64'));
}

const exportedAb = splicer.spliceAndExportFBX(charAb, {
  parentBoneId: rightHandId,
  weapon: {
    name: 'AK47_Rifle',
    positions: posOut,
    normals: normOut,
    uvs: akData.uvs,
    indices: new Uint32Array(akData.indices),
    color: akData.color,
    pngBytes
  },
  clips: [{
    name: baked.name,
    duration: baked.duration,
    times: Array.from(baked.times),
    tracks: baked.splicerTracks
  }]
});

// 5. Verify exported FBX loads cleanly in FBX-Web-Renderer-offline.html's FBXLoader
const reloaded = new THREE.FBXLoader().parse(exportedAb, '');
let foundWeapon = null;
reloaded.traverse(n => { if (n.isMesh && n.name.includes('AK47')) foundWeapon = n; });
assert(foundWeapon, 'Exported FBX must contain AK47_Rifle mesh');
assert(reloaded.animations.length === 1, 'Exported FBX must contain 1 baked animation clip');
assert(Math.abs(reloaded.animations[0].duration - baked.duration) < 1 / 24,
  `reimported clip retains terminal duration ${baked.duration}s (got ${reloaded.animations[0].duration}s)`);
console.log(`E2E PASS | Exported ${(exportedAb.byteLength / 1048576).toFixed(2)} MB | Weapon parent: ${foundWeapon.parent?.name} | Clip: ${reloaded.animations[0].name} (${reloaded.animations[0].tracks.length} tracks)`);
