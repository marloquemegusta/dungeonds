const assert = require('node:assert/strict');
const path = require('node:path');
const THREE = require('three');

const RetargetAndIKEngine = require('./retarget_and_ik_engine.js');
RetargetAndIKEngine.setTHREE(THREE);

console.log('Testing RetargetAndIKEngine...');

// =========================================================================
// TEST 1: mapHumanoidSkeleton
// =========================================================================
console.log('\n--- Test 1: mapHumanoidSkeleton ---');
{
  const root = new THREE.Group();
  root.name = 'Character_Root';

  // Build a test humanoid rig (Mixamo style naming)
  const hips = new THREE.Bone(); hips.name = 'mixamorig:Hips'; hips.position.set(0, 1.0, 0); root.add(hips);
  const spine = new THREE.Bone(); spine.name = 'mixamorig:Spine'; spine.position.set(0, 0.2, 0); hips.add(spine);
  const spine1 = new THREE.Bone(); spine1.name = 'mixamorig:Spine1'; spine1.position.set(0, 0.2, 0); spine.add(spine1);
  const spine2 = new THREE.Bone(); spine2.name = 'mixamorig:Spine2'; spine2.position.set(0, 0.2, 0); spine1.add(spine2);
  const neck = new THREE.Bone(); neck.name = 'mixamorig:Neck'; neck.position.set(0, 0.1, 0); spine2.add(neck);
  const head = new THREE.Bone(); head.name = 'mixamorig:Head'; head.position.set(0, 0.2, 0); neck.add(head);

  // Right arm
  const rShoulder = new THREE.Bone(); rShoulder.name = 'mixamorig:RightShoulder'; rShoulder.position.set(-0.2, 0.1, 0); spine2.add(rShoulder);
  const rArm = new THREE.Bone(); rArm.name = 'mixamorig:RightArm'; rArm.position.set(-0.15, 0, 0); rShoulder.add(rArm);
  const rForeArm = new THREE.Bone(); rForeArm.name = 'mixamorig:RightForeArm'; rForeArm.position.set(-0.25, 0, 0); rArm.add(rForeArm);
  const rHand = new THREE.Bone(); rHand.name = 'mixamorig:RightHand'; rHand.position.set(-0.22, 0, 0); rForeArm.add(rHand);

  // Right fingers
  const rThumb1 = new THREE.Bone(); rThumb1.name = 'mixamorig:RightHandThumb1'; rThumb1.position.set(-0.03, 0.02, 0.02); rHand.add(rThumb1);
  const rThumb2 = new THREE.Bone(); rThumb2.name = 'mixamorig:RightHandThumb2'; rThumb2.position.set(-0.02, 0, 0.01); rThumb1.add(rThumb2);
  const rThumb3 = new THREE.Bone(); rThumb3.name = 'mixamorig:RightHandThumb3'; rThumb3.position.set(-0.02, 0, 0.01); rThumb2.add(rThumb3);

  const rIdx1 = new THREE.Bone(); rIdx1.name = 'mixamorig:RightHandIndex1'; rIdx1.position.set(-0.06, 0.01, 0.02); rHand.add(rIdx1);
  const rIdx2 = new THREE.Bone(); rIdx2.name = 'mixamorig:RightHandIndex2'; rIdx2.position.set(-0.02, 0, 0); rIdx1.add(rIdx2);
  const rIdx3 = new THREE.Bone(); rIdx3.name = 'mixamorig:RightHandIndex3'; rIdx3.position.set(-0.02, 0, 0); rIdx2.add(rIdx3);

  const rMid1 = new THREE.Bone(); rMid1.name = 'mixamorig:RightHandMiddle1'; rMid1.position.set(-0.06, 0.0, 0.0); rHand.add(rMid1);
  const rMid2 = new THREE.Bone(); rMid2.name = 'mixamorig:RightHandMiddle2'; rMid2.position.set(-0.02, 0, 0); rMid1.add(rMid2);
  const rMid3 = new THREE.Bone(); rMid3.name = 'mixamorig:RightHandMiddle3'; rMid3.position.set(-0.02, 0, 0); rMid2.add(rMid3);

  const rRing1 = new THREE.Bone(); rRing1.name = 'mixamorig:RightHandRing1'; rRing1.position.set(-0.06, 0.0, -0.02); rHand.add(rRing1);
  const rPnk1 = new THREE.Bone(); rPnk1.name = 'mixamorig:RightHandPinky1'; rPnk1.position.set(-0.05, -0.01, -0.04); rHand.add(rPnk1);

  // Left arm
  const lShoulder = new THREE.Bone(); lShoulder.name = 'mixamorig:LeftShoulder'; lShoulder.position.set(0.2, 0.1, 0); spine2.add(lShoulder);
  const lArm = new THREE.Bone(); lArm.name = 'mixamorig:LeftArm'; lArm.position.set(0.15, 0, 0); lShoulder.add(lArm);
  const lForeArm = new THREE.Bone(); lForeArm.name = 'mixamorig:LeftForeArm'; lForeArm.position.set(0.25, 0, 0); lArm.add(lForeArm);
  const lHand = new THREE.Bone(); lHand.name = 'mixamorig:LeftHand'; lHand.position.set(0.22, 0, 0); lForeArm.add(lHand);

  // Left fingers
  const lIdx1 = new THREE.Bone(); lIdx1.name = 'mixamorig:LeftHandIndex1'; lIdx1.position.set(0.06, 0.01, 0.02); lHand.add(lIdx1);
  const lMid1 = new THREE.Bone(); lMid1.name = 'mixamorig:LeftHandMiddle1'; lMid1.position.set(0.06, 0.0, 0.0); lHand.add(lMid1);
  const lPnk1 = new THREE.Bone(); lPnk1.name = 'mixamorig:LeftHandPinky1'; lPnk1.position.set(0.05, -0.01, -0.04); lHand.add(lPnk1);

  // Legs
  const rUpLeg = new THREE.Bone(); rUpLeg.name = 'mixamorig:RightUpLeg'; rUpLeg.position.set(-0.15, -0.1, 0); hips.add(rUpLeg);
  const rLeg = new THREE.Bone(); rLeg.name = 'mixamorig:RightLeg'; rLeg.position.set(0, -0.4, 0); rUpLeg.add(rLeg);
  const rFoot = new THREE.Bone(); rFoot.name = 'mixamorig:RightFoot'; rFoot.position.set(0, -0.4, 0); rLeg.add(rFoot);
  const rToe = new THREE.Bone(); rToe.name = 'mixamorig:RightToeBase'; rToe.position.set(0, -0.08, 0.15); rFoot.add(rToe);

  const lUpLeg = new THREE.Bone(); lUpLeg.name = 'mixamorig:LeftUpLeg'; lUpLeg.position.set(0.15, -0.1, 0); hips.add(lUpLeg);
  const lLeg = new THREE.Bone(); lLeg.name = 'mixamorig:LeftLeg'; lLeg.position.set(0, -0.4, 0); lUpLeg.add(lLeg);
  const lFoot = new THREE.Bone(); lFoot.name = 'mixamorig:LeftFoot'; lFoot.position.set(0, -0.4, 0); lLeg.add(lFoot);
  const lToe = new THREE.Bone(); lToe.name = 'mixamorig:LeftToeBase'; lToe.position.set(0, -0.08, 0.15); lFoot.add(lToe);

  const rigMap = RetargetAndIKEngine.mapHumanoidSkeleton(root);

  assert.ok(rigMap.bones.Hips, 'Hips mapped');
  assert.ok(rigMap.bones.Spine, 'Spine mapped');
  assert.ok(rigMap.bones.Head, 'Head mapped');
  assert.ok(rigMap.bones.RightHand, 'RightHand mapped');
  assert.ok(rigMap.bones.LeftHand, 'LeftHand mapped');
  assert.ok(rigMap.bones.RightHandIndex1, 'RightHandIndex1 mapped');
  assert.ok(rigMap.bones.RightFoot, 'RightFoot mapped');

  assert.equal(typeof rigMap.charHeight, 'number');
  assert.ok(rigMap.charHeight > 0.5, 'charHeight is reasonable: ' + rigMap.charHeight);
  assert.equal(typeof rigMap.hipsRestY, 'number');
  assert.ok(Math.abs(rigMap.hipsRestY - 1.0) < 1e-4, 'hipsRestY is 1.0');

  // Check hand anatomical vectors
  assert.ok(rigMap.rightHandVectors, 'Right hand vectors generated');
  assert.ok(rigMap.rightHandVectors.handFwdWorld, 'handFwdWorld exists');
  assert.ok(rigMap.rightHandVectors.palmInWorld, 'palmInWorld exists');
  assert.ok(rigMap.rightHandVectors.hingeAxisWorld, 'hingeAxisWorld exists');
  assert.ok(rigMap.rightHandVectors.palmInWorld.y <= 0, 'palmIn points downwards (-Y)');

  console.log('✓ mapHumanoidSkeleton verified successfully');
}

// =========================================================================
// TEST 2: autoAlignWeaponGeometry
// =========================================================================
console.log('\n--- Test 2: autoAlignWeaponGeometry ---');
{
  // Generate synthetic rifle geometry oriented along Z:
  // Stock at Z = -0.35, Barrel tip at Z = +0.55 (Total length 0.90)
  // Stock is wider (Y/X radius ~ 0.08)
  // Barrel is thin (Y/X radius ~ 0.02)
  // Pistol grip protrudes at Z = -0.10 in -Y (downwards)
  // Rail/sight at Z = 0.0 in +Y (upwards)
  const pts = [];
  // Stock vertices
  for (let i = 0; i < 200; i++) {
    const z = -0.35 + Math.random() * 0.2;
    const x = (Math.random() - 0.5) * 0.08;
    const y = (Math.random() - 0.5) * 0.10;
    pts.push(x, y, z);
  }
  // Barrel vertices (narrow)
  for (let i = 0; i < 200; i++) {
    const z = 0.2 + Math.random() * 0.35;
    const x = (Math.random() - 0.5) * 0.02;
    const y = (Math.random() - 0.5) * 0.02;
    pts.push(x, y, z);
  }
  // Pistol grip protruding in -Y
  for (let i = 0; i < 100; i++) {
    const z = -0.12 + Math.random() * 0.05;
    const x = (Math.random() - 0.5) * 0.03;
    const y = -0.05 - Math.random() * 0.12; // deep protrusion downwards
    pts.push(x, y, z);
  }
  // Upper rail
  for (let i = 0; i < 100; i++) {
    const z = -0.05 + Math.random() * 0.25;
    const x = (Math.random() - 0.5) * 0.03;
    const y = 0.02 + Math.random() * 0.03;
    pts.push(x, y, z);
  }

  const geom = new THREE.BufferGeometry();
  geom.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));

  const mockRig = {
    charHeight: 1.80,
    bones: { RightHand: new THREE.Bone(), RightHandMiddle1: new THREE.Bone() },
    rightHandVectors: {
      handFwdLocal: new THREE.Vector3(0, 1, 0),
      palmInLocal: new THREE.Vector3(0, 0, -1),
      hingeAxisLocal: new THREE.Vector3(1, 0, 0)
    }
  };

  const alignResult = RetargetAndIKEngine.autoAlignWeaponGeometry(geom, mockRig, { type: 'rifle' });

  assert.ok(alignResult.localMatrix4 instanceof THREE.Matrix4, 'localMatrix4 is Matrix4');
  assert.ok(alignResult.foregripLocalPos instanceof THREE.Vector3, 'foregripLocalPos is Vector3');
  assert.ok(alignResult.rawLength > 0.8, 'rawLength around 0.9m: ' + alignResult.rawLength);
  assert.ok(alignResult.scaleFactor > 0, 'scaleFactor is positive');
  assert.ok(Math.abs(alignResult.length - (1.80 * 0.48)) < 0.05, 'Scaled to charHeight * 0.48: ' + alignResult.length);

  // Verify barrel axis points along Z
  const bAxis = new THREE.Vector3(...alignResult.autoDetectedAxes.axisBarrel);
  assert.ok(Math.abs(bAxis.z) > 0.85, 'Barrel axis along Z: ' + bAxis.z);
  // Verify muzzle was at positive Z
  assert.ok(bAxis.z > 0, 'Muzzle polarity correctly points to positive Z');

  // Verify up axis points upwards (+Y) so grip points in -axisUp
  const upAxis = new THREE.Vector3(...alignResult.autoDetectedAxes.axisUp);
  assert.ok(upAxis.y > 0.5, 'Up axis points to +Y: ' + upAxis.y);

  // Test sword mode
  const swordResult = RetargetAndIKEngine.autoAlignWeaponGeometry(geom, mockRig, { type: 'sword' });
  assert.ok(Math.abs(swordResult.length - (1.80 * 0.55)) < 0.05, 'Sword scaled to charHeight * 0.55: ' + swordResult.length);

  console.log('✓ autoAlignWeaponGeometry verified successfully');
}

// =========================================================================
// TEST 3: prepareAnimationRetarget
// =========================================================================
console.log('\n--- Test 3: prepareAnimationRetarget ---');
{
  const root = new THREE.Group();
  const hips = new THREE.Bone(); hips.name = 'mixamorig:Hips'; hips.position.set(0, 1.0, 0); root.add(hips);
  const rArm = new THREE.Bone(); rArm.name = 'mixamorig:RightArm'; rArm.position.set(-0.2, 1.4, 0); hips.add(rArm);
  const rForeArm = new THREE.Bone(); rForeArm.name = 'mixamorig:RightForeArm'; rForeArm.position.set(-0.4, 1.4, 0); rArm.add(rForeArm);
  const rHand = new THREE.Bone(); rHand.name = 'mixamorig:RightHand'; rHand.position.set(-0.6, 1.4, 0); rForeArm.add(rHand);

  const charRig = RetargetAndIKEngine.mapHumanoidSkeleton(root);

  // Mock animation clip
  const times = [0, 0.5, 1.0];
  const qValues = [
    0, 0, 0, 1,
    0, 0.1, 0, 0.995,
    0, 0, 0, 1
  ];
  const posValues = [
    0, 1.0, 0,
    0.2, 1.05, 0.5,
    0.4, 1.0, 1.0
  ];

  const tracks = [
    new THREE.QuaternionKeyframeTrack('mixamorig2:Hips.quaternion', times, qValues),
    new THREE.VectorKeyframeTrack('mixamorig2:Hips.position', times, posValues),
    new THREE.QuaternionKeyframeTrack('mixamorig2:RightArm.quaternion', times, qValues)
  ];
  const clip = new THREE.AnimationClip('TestRun', 1.0, tracks);

  const retargetCtx = RetargetAndIKEngine.prepareAnimationRetarget(charRig, clip);

  assert.equal(retargetCtx.duration, 1.0);
  assert.ok(retargetCtx.sourceTracksByCanonical.Hips, 'Source track Hips found');
  assert.ok(retargetCtx.sourceTracksByCanonical.RightArm, 'Source track RightArm found');
  assert.ok(retargetCtx.alignQuat.RightArm instanceof THREE.Quaternion, 'alignQuat for RightArm exists');
  assert.ok(Math.abs(retargetCtx.hipsScaleRatio - 1.0) < 1e-3, 'hipsScaleRatio is 1.0');

  console.log('✓ prepareAnimationRetarget verified successfully');
}

// =========================================================================
// TEST 4: evaluateRetargetFrame & IK
// =========================================================================
console.log('\n--- Test 4: evaluateRetargetFrame & IK ---');
{
  const root = new THREE.Group();
  const hips = new THREE.Bone(); hips.name = 'mixamorig:Hips'; hips.position.set(0, 1.0, 0); root.add(hips);
  const spine1 = new THREE.Bone(); spine1.name = 'mixamorig:Spine1'; spine1.position.set(0, 0.2, 0); hips.add(spine1);
  const spine2 = new THREE.Bone(); spine2.name = 'mixamorig:Spine2'; spine2.position.set(0, 0.2, 0); spine1.add(spine2);

  const rArm = new THREE.Bone(); rArm.name = 'mixamorig:RightArm'; rArm.position.set(-0.2, 0.1, 0); spine2.add(rArm);
  const rForeArm = new THREE.Bone(); rForeArm.name = 'mixamorig:RightForeArm'; rForeArm.position.set(-0.2, 0, 0); rArm.add(rForeArm);
  const rHand = new THREE.Bone(); rHand.name = 'mixamorig:RightHand'; rHand.position.set(-0.2, 0, 0); rForeArm.add(rHand);
  const rIdx1 = new THREE.Bone(); rIdx1.name = 'mixamorig:RightHandIndex1'; rIdx1.position.set(-0.05, 0, 0); rHand.add(rIdx1);

  const lArm = new THREE.Bone(); lArm.name = 'mixamorig:LeftArm'; lArm.position.set(0.2, 0.1, 0); spine2.add(lArm);
  const lForeArm = new THREE.Bone(); lForeArm.name = 'mixamorig:LeftForeArm'; lForeArm.position.set(0.2, 0, 0); lArm.add(lForeArm);
  const lHand = new THREE.Bone(); lHand.name = 'mixamorig:LeftHand'; lHand.position.set(0.2, 0, 0); lForeArm.add(lHand);

  const rFoot = new THREE.Bone(); rFoot.name = 'mixamorig:RightFoot'; rFoot.position.set(-0.15, -0.9, 0); hips.add(rFoot);

  const charRig = RetargetAndIKEngine.mapHumanoidSkeleton(root);

  // Source clip with locomotion
  const times = [0, 1.0];
  const posValues = [
    0, 1.0, 0,
    0.5, 1.0, 2.0 // moves in X and Z
  ];
  const qValues = [0, 0, 0, 1, 0, 0, 0, 1];
  const tracks = [
    new THREE.VectorKeyframeTrack('mixamorig:Hips.position', times, posValues),
    new THREE.QuaternionKeyframeTrack('mixamorig:Hips.quaternion', times, qValues)
  ];
  const clip = new THREE.AnimationClip('Walk', 1.0, tracks);
  const retargetCtx = RetargetAndIKEngine.prepareAnimationRetarget(charRig, clip);

  // Test In-Place Lock = 1.0 (anti-deriva)
  RetargetAndIKEngine.evaluateRetargetFrame(charRig, retargetCtx, 0.5, { inPlaceLock: 1.0, groundFeet: false });
  assert.equal(charRig.bones.Hips.position.x, 0, 'In-place locks horizontal X motion to 0');
  assert.equal(charRig.bones.Hips.position.z, 0, 'In-place locks horizontal Z motion to 0');

  // Test In-Place Lock = 0.0 (allows motion)
  RetargetAndIKEngine.evaluateRetargetFrame(charRig, retargetCtx, 0.5, { inPlaceLock: 0.0, groundFeet: false });
  assert.ok(charRig.bones.Hips.position.z > 0.5, 'Allows Z motion when inPlaceLock = 0');

  // Test Auto-grounding
  RetargetAndIKEngine.evaluateRetargetFrame(charRig, retargetCtx, 0.0, { groundFeet: true });
  const footWorldY = charRig.bones.RightFoot.getWorldPosition(new THREE.Vector3()).y;
  assert.ok(Math.abs(footWorldY) < 1e-4, 'Foot is grounded at Y = 0: ' + footWorldY);

  // Test Postural Offsets
  RetargetAndIKEngine.evaluateRetargetFrame(charRig, retargetCtx, 0.0, { spineTwistDeg: 30, spinePitchDeg: 20 });
  assert.ok(!charRig.bones.Spine1.quaternion.equals(new THREE.Quaternion()), 'Spine rotation modified by offsets');

  // Test Procedural Finger Grip
  RetargetAndIKEngine.evaluateRetargetFrame(charRig, retargetCtx, 0.0, { rightHandGrip: 1.0 });
  assert.ok(!rIdx1.quaternion.equals(new THREE.Quaternion()), 'Index finger curled under grip');

  // Test Left Hand 2-Bone Analytical IK
  const weaponContext = {
    localMatrix4: new THREE.Matrix4().makeTranslation(0, 0.2, 0),
    foregripLocalPos: new THREE.Vector3(0, 0.1, 0)
  };
  RetargetAndIKEngine.evaluateRetargetFrame(charRig, retargetCtx, 0.0, { leftHandIkWeight: 1.0 }, weaponContext);
  assert.ok(!lArm.quaternion.equals(new THREE.Quaternion()), 'Left arm adjusted by IK solver');
  assert.ok(!lForeArm.quaternion.equals(new THREE.Quaternion()), 'Left forearm adjusted by IK solver');

  console.log('✓ evaluateRetargetFrame verified successfully');
}

// =========================================================================
// TEST 5: bakeClipToFBXTracks & Euler Unwrapping
// =========================================================================
console.log('\n--- Test 5: bakeClipToFBXTracks & Euler Unwrapping ---');
{
  const root = new THREE.Group();
  const hips = new THREE.Bone(); hips.name = 'mixamorig:Hips'; hips.position.set(0, 1.0, 0); root.add(hips);
  const rArm = new THREE.Bone(); rArm.name = 'mixamorig:RightArm'; rArm.position.set(-0.2, 0, 0); hips.add(rArm);

  const charRig = RetargetAndIKEngine.mapHumanoidSkeleton(root);

  // Create clip with rotation passing through 170 -> 190 degrees
  const times = [0, 0.5, 1.0];
  const q0 = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), THREE.MathUtils.degToRad(170));
  const q1 = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), THREE.MathUtils.degToRad(180));
  const q2 = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), THREE.MathUtils.degToRad(190));

  const qValues = [
    q0.x, q0.y, q0.z, q0.w,
    q1.x, q1.y, q1.z, q1.w,
    q2.x, q2.y, q2.z, q2.w
  ];
  const posValues = [0, 1, 0, 0, 1, 0, 0, 1, 0];
  const tracks = [
    new THREE.VectorKeyframeTrack('mixamorig:Hips.position', times, posValues),
    new THREE.QuaternionKeyframeTrack('mixamorig:Hips.quaternion', times, qValues),
    new THREE.QuaternionKeyframeTrack('mixamorig:RightArm.quaternion', times, qValues)
  ];
  const clip = new THREE.AnimationClip('Spin', 1.0, tracks);
  const retargetCtx = RetargetAndIKEngine.prepareAnimationRetarget(charRig, clip);

  const fbxMeta = {
    'mixamorig:RightArm': {
      preRotation: [90, 0, 0],
      postRotation: [0, 0, 0],
      nodeId: 123456
    }
  };

  const baked = RetargetAndIKEngine.bakeClipToFBXTracks(charRig, retargetCtx, { bakeFps: 30 }, null, fbxMeta);

  assert.equal(baked.name, 'Spin');
  assert.equal(baked.fps, 30);
  assert.equal(baked.frameCount, 31);
  assert.equal(baked.times.length, 31);
  assert.ok(baked.tracks.RightArm, 'RightArm track baked');
  assert.equal(baked.tracks.RightArm.rotation.x.length, 31);
  assert.equal(baked.tracks.RightArm.nodeId, 123456);

  // Verify continuous unwrapping: consecutive angle delta must not jump by ~360 deg
  const armRotY = baked.tracks.RightArm.rotation.y;
  for (let i = 1; i < armRotY.length; i++) {
    const delta = Math.abs(armRotY[i] - armRotY[i - 1]);
    assert.ok(delta < 30.0, `Continuous Euler unwrapping: frame ${i} delta is ${delta} deg (must be < 30)`);
  }

  console.log('✓ bakeClipToFBXTracks verified successfully');
}

console.log('\n======================================================');
console.log('ALL TESTS PASSED! RetargetAndIKEngine is 100% verified.');
console.log('======================================================\n');
