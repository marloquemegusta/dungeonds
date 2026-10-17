// Regression tests for the checked-in compact catalog and real bundled Three.js.
// Run from any cwd: node tools/lab/test_lab_regressions.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const THREE = require('./offline_three.cjs');
const Engine = require('./retarget_and_ik_engine.js');
const Catalog = require('./seed_catalog_data.js');

Engine.setTHREE(THREE);

function stride(type) {
  if (type === 'quaternion') return 4;
  if (type === 'position') return 3;
  throw new Error(`Unexpected catalog track type: ${type}`);
}
function finiteUnitQuat(values, offset) {
  const q = values.slice(offset, offset + 4);
  assert.equal(q.length, 4);
  assert(q.every(Number.isFinite), 'quaternion components are finite');
  assert(Math.abs(Math.hypot(...q) - 1) < 2e-3, `quaternion is unit length: ${Math.hypot(...q)}`);
}

assert.equal(Catalog.animations.length, 11, 'catalog contains nine unique base clips and two hybrid clips');
assert.equal(Catalog.getAnimation('melee_jump_hit'), null, 'duplicate JumpHit source is not exposed as a separate catalog row');
assert(Catalog.getAnimation('melee_slash'), 'canonical Sword Slash clip remains available');
assert(Catalog.getAnimation('rifle_walk') && Catalog.getAnimation('rifle_run'), 'walk and run remain separate semantic clips');
const hybrid = Catalog.animations.filter(a => a.hybrid);
assert.equal(hybrid.length, 2, 'two explicitly named rifle hybrid clips are present');
assert.deepEqual(hybrid.map(a => a.id).sort(), ['rifle_run_ready', 'rifle_walk_ready']);
assert.deepEqual(hybrid.map(a => a.name).sort(), ['Caminar en ristre', 'Correr en ristre']);
for (const clip of hybrid) {
  assert.equal(clip.hybrid.upperAnimationId, 'rifle_aim');
  assert.match(clip.hybrid.lowerAnimationId, /^rifle_(walk|run)$/);
  assert.equal(clip.hybrid.upperTimeMode, 'normalized');
  assert(clip.hybrid.upperCanonicalRoots.includes('Spine2'), `${clip.id} overlays the upper body`);
  assert.equal(clip.category, 'Rifle');
}

// Slash.fbx and JumpHit.fbx carry the same complete sampled humanoid motion;
// fail this regression if JumpHit later becomes a distinct action worth listing.
function extractMeleeSource(relativePath, id) {
  const sourcePath = path.resolve(__dirname, '../../', relativePath);
  const sourceBytes = fs.readFileSync(sourcePath);
  const sourceAb = sourceBytes.buffer.slice(sourceBytes.byteOffset, sourceBytes.byteOffset + sourceBytes.byteLength);
  const sourceModel = new THREE.FBXLoader().parse(sourceAb, '');
  assert(sourceModel.animations[0], `${relativePath} contains an animation`);
  return Engine.extractAnimationClip(sourceModel, sourceModel.animations[0], id, 'Melee');
}
const slashSource = extractMeleeSource('assets/blender_combat_demo/Slash.fbx', 'slash_source');
const jumpSource = extractMeleeSource('assets/blender_combat_demo/JumpHit.fbx', 'jump_source');
assert.equal(slashSource.duration, jumpSource.duration);
assert.equal(slashSource.numFrames, jumpSource.numFrames);
const tracksByKey = clip => new Map(clip.tracks.map(track => [`${track.bone}.${track.type}`, track.values]));
const slashTracks = tracksByKey(slashSource), jumpTracks = tracksByKey(jumpSource);
assert.deepEqual([...slashTracks.keys()].sort(), [...jumpTracks.keys()].sort(), 'duplicate sources cover the same canonical tracks');
for (const [key, values] of slashTracks) assert.deepEqual(values, jumpTracks.get(key), `${key} samples are exactly identical`);

for (const clip of Catalog.animations) {
  assert(clip.numFrames >= 2, `${clip.id} has at least two samples`);
  if (clip.hybrid) {
    assert.equal(clip.hybrid.upperAnimationId, 'rifle_aim');
    assert.match(clip.hybrid.lowerAnimationId, /^rifle_(walk|run)$/);
    continue;
  }
  const keys = new Set();
  for (const track of clip.tracks) {
    const key = `${track.bone}.${track.type}`;
    assert(!keys.has(key), `${clip.id} has no duplicate canonical/property track: ${key}`);
    keys.add(key);
    const s = stride(track.type);
    assert(track.values.length === s || track.values.length === clip.numFrames * s,
      `${clip.id} ${key} is compact (one sample or numFrames), got ${track.values.length / s}`);
    assert(track.values.every(Number.isFinite), `${clip.id} ${key} has finite values`);
    if (track.type === 'quaternion') {
      for (let i = 0; i < track.values.length; i += 4) finiteUnitQuat(track.values, i);
    }
  }
}

const idle = Catalog.getAnimation('rifle_idle');
assert(idle, 'rifle_idle is in the catalog');
for (const track of idle.tracks.filter(t => t.type === 'quaternion' && /Head|Neck|Spine/.test(t.bone))) {
  const s = 4;
  let maxJump = 0;
  for (let i = s; i < track.values.length; i += s) {
    // q and -q represent the same orientation; use absolute dot product.
    const d = Math.abs(track.values.slice(i - s, i).reduce((sum, x, j) => sum + x * track.values[i + j], 0));
    maxJump = Math.max(maxJump, 2 * Math.acos(Math.min(1, d)));
  }
  assert(maxJump < 0.35, `rifle_idle ${track.bone} has no frame-to-frame rotational spike (${maxJump.toFixed(3)} rad)`);
}

// Exact-asset extraction exercises FBXLoader duplicate IDs, root animation,
// endpoint sampling, compact static tracks, and restoration of preview state.
const idlePath = path.resolve(__dirname, '../../assets/blender_combat_demo/weapons/Rifle_Aiming_Idle.fbx');
assert(fs.existsSync(idlePath), `real idle FBX exists at ${idlePath}`);
const bytes = fs.readFileSync(idlePath);
const ab = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
const model = new THREE.FBXLoader().parse(ab, '');
assert(model.animations.length > 0, 'idle FBX contains an animation clip');
const clip = model.animations[0];
const saved = [];
const idsByCanonical = new Map();
model.traverse(node => {
  saved.push([node, node.position.clone(), node.quaternion.clone(), node.scale.clone()]);
  if (node.isBone) {
    const key = Engine.normalizeCanonicalBoneName(node.name);
    if (key) {
      const id = node.ID == null ? node.uuid : String(node.ID);
      if (!idsByCanonical.has(key)) idsByCanonical.set(key, new Set());
      idsByCanonical.get(key).add(id);
    }
  }
});
const animatedRoot = model;
animatedRoot.position.set(0.31, -0.17, 0.22);
animatedRoot.scale.set(1.1, 0.9, 1.05);
const before = new Map(saved.map(([node]) => [node, [node.position.clone(), node.quaternion.clone(), node.scale.clone()]]));
const extracted = Engine.extractAnimationClip(model, clip, 'regression_rifle_idle', 'Rifle');
assert(extracted && extracted.tracks.length > 0, 'real idle clip extracts');
const seen = new Set();
for (const track of extracted.tracks) {
  const key = `${track.bone}.${track.type}`;
  assert(!seen.has(key), `real idle has one sample stream for ${key}`);
  seen.add(key);
  const s = stride(track.type);
  assert(track.values.length === s || track.values.length === extracted.numFrames * s,
    `${key} stores one value or all ${extracted.numFrames} frame values`);
}
for (const set of idsByCanonical.values()) assert.equal(set.size, 1, 'real FBX clone shims share one source bone ID per canonical name');
for (const [node, [p, q, s]] of before) {
  assert(node.position.distanceTo(p) < 1e-7, `${node.name} position restored`);
  assert(1 - Math.abs(node.quaternion.dot(q)) < 1e-7, `${node.name} rotation restored`);
  assert(node.scale.distanceTo(s) < 1e-7, `${node.name} scale restored`);
}
const hipsPosition = extracted.tracks.find(t => t.bone === 'Hips' && t.type === 'position');
assert(hipsPosition, 'root/hips translation is retained');
assert(hipsPosition.values.length === extracted.numFrames * 3, 'animated root/hips translation keeps every frame');

// The ready-to-fire modes must compose in target-rig local space: lower body
// matches its walk/run source and the upper body matches target-retargeted aim.
const marinePath = path.resolve(__dirname, '../../assets/characters/spacemarine/spacemarine.fbx');
const marineBytes = fs.readFileSync(marinePath);
const marineAb = marineBytes.buffer.slice(marineBytes.byteOffset, marineBytes.byteOffset + marineBytes.byteLength);
const targetModel = new THREE.FBXLoader().parse(marineAb, '');
const targetRig = Engine.mapHumanoidSkeleton(targetModel);
const poseKeys = ['Hips', 'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'RightUpLeg', 'RightLeg', 'RightFoot',
  'Spine2', 'Neck', 'Head', 'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand',
  'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand'];
const pose = () => Object.fromEntries(poseKeys.filter(k => targetRig.bones[k]).map(k => {
  const b = targetRig.bones[k];
  return [k, { position: b.position.clone(), quaternion: b.quaternion.clone() }];
}));
const samePose = (a, b, key) => {
  assert(a[key] && b[key], `${key} is present in both target poses`);
  assert(a[key].position.distanceTo(b[key].position) < 1e-4, `${key} target-local position agrees`);
  assert(1 - Math.abs(a[key].quaternion.dot(b[key].quaternion)) < 1e-5, `${key} target-local rotation agrees`);
};
const plainEvalParams = { leftHandIkWeight: 0, rightHandGrip: 0, leftHandGrip: 0, groundFeet: false,
  inPlaceLock: 0, spineTwistDeg: 0, spinePitchDeg: 0, armSpreadDeg: 0 };
for (const hybridClip of hybrid) {
  const lowerClip = Catalog.getAnimation(hybridClip.hybrid.lowerAnimationId);
  const upperClip = Catalog.getAnimation(hybridClip.hybrid.upperAnimationId);
  const resolvedHybrid = { ...hybridClip, hybrid: { ...hybridClip.hybrid, lower: lowerClip, upper: upperClip } };
  const hctx = Engine.prepareAnimationRetarget(targetRig, resolvedHybrid);
  const lctx = Engine.prepareAnimationRetarget(targetRig, lowerClip);
  const uctx = Engine.prepareAnimationRetarget(targetRig, upperClip);
  const phase = 0.43;
  Engine.evaluateRetargetFrame(targetRig, hctx, phase * hctx.duration, plainEvalParams, null);
  const hybridPose = pose();
  Engine.evaluateRetargetFrame(targetRig, lctx, phase * lctx.duration, plainEvalParams, null);
  const lowerPose = pose();
  for (const key of ['Hips', 'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'RightUpLeg', 'RightLeg', 'RightFoot']) samePose(hybridPose, lowerPose, key);
  Engine.evaluateRetargetFrame(targetRig, uctx, phase * uctx.duration, plainEvalParams, null);
  const upperPose = pose();
  for (const key of ['Spine2', 'Neck', 'Head', 'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand',
    'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand']) samePose(hybridPose, upperPose, key);
}

// A second distinct FBX node claiming one canonical bone is ambiguous and must
// be rejected; repeated FBXLoader shims of the same source ID are valid.
const collisionRoot = new THREE.Group();
const hipsA = new THREE.Bone(); hipsA.name = 'mixamorig:Hips'; hipsA.ID = 101; collisionRoot.add(hipsA);
const hipsShim = new THREE.Bone(); hipsShim.name = 'mixamorig:Hips'; hipsShim.ID = 101; collisionRoot.add(hipsShim);
assert.doesNotThrow(() => Engine.mapHumanoidSkeleton(collisionRoot), 'same-source-ID cloned bone shims are deduplicated');
const hipsB = new THREE.Bone(); hipsB.name = 'Bip01_Pelvis'; hipsB.ID = 202; collisionRoot.add(hipsB);
assert.throws(() => Engine.mapHumanoidSkeleton(collisionRoot), /duplicate|collision|ambiguous/i,
  'different source IDs that claim Hips are rejected');

// Numeric suffix 4 is an FBX end marker, never an alias for finger segment 2.
assert.equal(Engine.normalizeCanonicalBoneName('mixamorig:LeftHandMiddle4'), null);
assert.equal(Engine.normalizeCanonicalBoneName('mixamorig:LeftHandMiddle2'), 'LeftHandMiddle2');

console.log(`PASS lab regressions | ${Catalog.animations.length} clips (${hybrid.length} hybrids) | ${extracted.tracks.length} extracted real-FBX tracks`);
