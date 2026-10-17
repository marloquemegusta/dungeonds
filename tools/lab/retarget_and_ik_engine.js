/**
 * RetargetAndIKEngine
 * 
 * Mathematical engine for humanoid skeleton mapping, procedural weapon geometry alignment,
 * animation retargeting, 2-bone analytical IK, finger curling, foot auto-grounding,
 * and FBX animation track baking.
 * 
 * Compatible with browser (window.RetargetAndIKEngine) and CommonJS (module.exports).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    let threeModule = null;
    try {
      threeModule = require('three');
    } catch (e) {
      // Three will be provided via init or parameter
    }
    module.exports = factory(threeModule);
  } else {
    root.RetargetAndIKEngine = factory(root.THREE);
  }
}(typeof self !== 'undefined' ? self : this, function (injectedTHREE) {
  'use strict';

  let _THREE = injectedTHREE || (typeof THREE !== 'undefined' ? THREE : null);

  function getTHREE(optionalTHREE) {
    const t = optionalTHREE || _THREE || (typeof THREE !== 'undefined' ? THREE : null);
    if (!t) {
      throw new Error("RetargetAndIKEngine: THREE is required. Provide it via RetargetAndIKEngine.setTHREE(THREE) or pass it directly.");
    }
    return t;
  }

  // =========================================================================
  // 1. CANONICAL BONE DEFINITIONS & MAPPING
  // =========================================================================

  const CANONICAL_BONES = [
    // Trunk & Head
    'Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head',
    // Left Arm
    'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand',
    // Right Arm
    'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand',
    // Left Leg
    'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase',
    // Right Leg
    'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase'
  ];

  const FINGER_NAMES = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky'];
  ['LeftHand', 'RightHand'].forEach(hand => {
    FINGER_NAMES.forEach(f => {
      for (let j = 1; j <= 3; j++) {
        CANONICAL_BONES.push(`${hand}${f}${j}`);
      }
    });
  });

  const LIMB_KEYWORDS = ['Shoulder', 'Arm', 'ForeArm', 'Hand', 'UpLeg', 'Leg', 'Foot'];

  function normalizeCanonicalBoneName(rawName) {
    if (!rawName || typeof rawName !== 'string') return null;
    let s = rawName.trim();

    // Remove common namespaces / prefixes
    s = s.replace(/^(mixamorig2?|bip01|character1?|root|bone|rig)[_:\s]+/i, '');
    s = s.replace(/^mixamorig2?:?/i, '');

    // Canonical direct match check (case-insensitive)
    for (const b of CANONICAL_BONES) {
      if (s.toLowerCase() === b.toLowerCase()) return b;
    }

    const lower = s.toLowerCase().replace(/[\s_\-\.]+/g, '');

    // Trunk & Head mappings
    if (lower === 'hips' || lower === 'pelvis' || lower === 'hip') return 'Hips';
    if (lower === 'spine' || lower === 'spine0' || lower === 'spine01') return 'Spine';
    if (lower === 'spine1' || lower === 'chest' || lower === 'spine02') return 'Spine1';
    if (lower === 'spine2' || lower === 'upperchest' || lower === 'spine03') return 'Spine2';
    if (lower === 'neck' || lower === 'neck01') return 'Neck';
    if (lower === 'head' || lower === 'head01') return 'Head';

    // Left Arm
    if (/^(l|left)(shoulder|clavicle)$/i.test(lower) || /^(shoulder|clavicle)l$/i.test(lower)) return 'LeftShoulder';
    if (/^(l|left)(arm|upperarm)$/i.test(lower) || /^(arm|upperarm)l$/i.test(lower)) return 'LeftArm';
    if (/^(l|left)(forearm|lowerarm)$/i.test(lower) || /^(forearm|lowerarm)l$/i.test(lower)) return 'LeftForeArm';
    if (/^(l|left)(hand|wrist)$/i.test(lower) || /^(hand|wrist)l$/i.test(lower)) return 'LeftHand';

    // Right Arm
    if (/^(r|right)(shoulder|clavicle)$/i.test(lower) || /^(shoulder|clavicle)r$/i.test(lower)) return 'RightShoulder';
    if (/^(r|right)(arm|upperarm)$/i.test(lower) || /^(arm|upperarm)r$/i.test(lower)) return 'RightArm';
    if (/^(r|right)(forearm|lowerarm)$/i.test(lower) || /^(forearm|lowerarm)r$/i.test(lower)) return 'RightForeArm';
    if (/^(r|right)(hand|wrist)$/i.test(lower) || /^(hand|wrist)r$/i.test(lower)) return 'RightHand';

    // Left Leg
    if (/^(l|left)(upleg|upperleg|thigh)$/i.test(lower) || /^(upleg|upperleg|thigh)l$/i.test(lower)) return 'LeftUpLeg';
    if (/^(l|left)(leg|lowerleg|calf)$/i.test(lower) || /^(leg|lowerleg|calf)l$/i.test(lower)) return 'LeftLeg';
    if (/^(l|left)(foot|ankle)$/i.test(lower) || /^(foot|ankle)l$/i.test(lower)) return 'LeftFoot';
    if (/^(l|left)(toebase|toes?)$/i.test(lower) || /^(toebase|toes?)l$/i.test(lower)) return 'LeftToeBase';

    // Right Leg
    if (/^(r|right)(upleg|upperleg|thigh)$/i.test(lower) || /^(upleg|upperleg|thigh)r$/i.test(lower)) return 'RightUpLeg';
    if (/^(r|right)(leg|lowerleg|calf)$/i.test(lower) || /^(leg|lowerleg|calf)r$/i.test(lower)) return 'RightLeg';
    if (/^(r|right)(foot|ankle)$/i.test(lower) || /^(foot|ankle)r$/i.test(lower)) return 'RightFoot';
    if (/^(r|right)(toebase|toes?)$/i.test(lower) || /^(toebase|toes?)r$/i.test(lower)) return 'RightToeBase';

    // Fingers
    const isLeft = /^(l|left)/i.test(lower) || /l$/i.test(lower);
    const isRight = /^(r|right)/i.test(lower) || /r$/i.test(lower);
    if (isLeft || isRight) {
      const side = isLeft ? 'LeftHand' : 'RightHand';
      for (const f of FINGER_NAMES) {
        const fingerRegex = new RegExp(f === 'Pinky' ? '(pinky|little)' : f, 'i');
        if (!fingerRegex.test(lower)) continue;

        const terminalNumber = lower.match(/(\d+)$/);
        if (terminalNumber) {
          const segment = Number(terminalNumber[1]);
          return segment >= 1 && segment <= 3 ? `${side}${f}${segment}` : null;
        }
        if (/distal/i.test(lower)) return `${side}${f}3`;
        if (/intermediate/i.test(lower)) return `${side}${f}2`;
        if (/proximal/i.test(lower)) return `${side}${f}1`;
        if (/middle/i.test(lower)) return `${side}${f}2`;
      }
    }

    return null;
  }

  /**
   * 1. mapHumanoidSkeleton(rootObject, optionalTHREE)
   */
  function collectHumanoidBones(rootObject, optionalClip) {
    const bones = {};
    const addCandidate = (node, key) => {
      if (bones[key] && bones[key] !== node) {
        const existing = bones[key];
        const nodeId = node.ID ?? node.userData?.id ?? node.userData?.transformData?.id;
        const existingId = existing.ID ?? existing.userData?.id ?? existing.userData?.transformData?.id;
        if (nodeId !== undefined && existingId !== undefined && String(nodeId) === String(existingId)) {
          return; // FBXLoader identity shims repeat one model ID below the real binding node.
        }
        throw new Error(`Duplicate humanoid node ${key}; conflicting FBX model IDs ${existingId ?? 'unknown'} and ${nodeId ?? 'unknown'}`);
      }
      bones[key] = node;
    };
    rootObject.traverse(node => {
      if (!node.isBone) return;
      const key = normalizeCanonicalBoneName(node.name);
      if (key) addCandidate(node, key);
    });
    if (Object.keys(bones).length) return bones;

    // Some legacy Mixamo death FBXs encode each animated humanoid transform as
    // a flat Mesh proxy. Only use proxies when the model has no mapped Bones,
    // and only when the clip explicitly animates that node.
    const animatedNames = new Set();
    for (const track of optionalClip?.tracks || []) {
      const match = String(track.name || '').match(/^(.+?)\.(position|quaternion)$/i);
      if (match) animatedNames.add(match[1]);
    }
    if (!animatedNames.size) return bones;
    rootObject.traverse(node => {
      if (node.isBone || !animatedNames.has(node.name)) return;
      const key = normalizeCanonicalBoneName(node.name);
      if (key) addCandidate(node, key);
    });
    return bones;
  }

  // Both seed generation and user imports must sample one real bone per track.
  function extractAnimationClip(model, clip, id, category = 'Custom', optionalTHREE) {
    const THREE = getTHREE(optionalTHREE);
    if (!clip) return null;
    const bones = collectHumanoidBones(model, clip);
    if (!bones.Hips) throw new Error('Animation has no humanoid Hips bone');
    const fps = 24;
    const duration = Math.max(0.05, clip.duration || 1);
    const numFrames = Math.max(2, Math.ceil(duration * fps) + 1);
    const saved = [];
    model.traverse(n => saved.push([n, n.position.clone(), n.quaternion.clone(), n.scale.clone()]));
    const boneParents = {}, boneRestPose = {}, boneRestPositions = {}, boneTracks = {};
    const canonicalByNode = new Map(Object.entries(bones).map(([key, bone]) => [bone, key]));
    model.updateWorldMatrix(true, true);
    function relativeQuat(key) {
      const q = bones[key].getWorldQuaternion(new THREE.Quaternion());
      const parentKey = boneParents[key];
      return parentKey ? bones[parentKey].getWorldQuaternion(new THREE.Quaternion()).invert().multiply(q).normalize() : q.normalize();
    }
    for (const [key, bone] of Object.entries(bones)) {
      let parent = bone.parent;
      while (parent && !canonicalByNode.has(parent)) parent = parent.parent;
      boneParents[key] = key === 'Hips' ? null : (canonicalByNode.get(parent) || null);
    }
    for (const [key, bone] of Object.entries(bones)) {
      boneRestPose[key] = relativeQuat(key).toArray();
      boneRestPositions[key] = bone.getWorldPosition(new THREE.Vector3()).toArray();
      boneTracks[key] = { bone: key, rawBone: bone.name, type: 'quaternion', values: [] };
    }
    const hipsRestPosition = boneRestPositions.Hips.slice();
    const positions = [];
    const mixer = new THREE.AnimationMixer(model);
    try {
      const action = mixer.clipAction(clip);
      action.setLoop(2200, 1); // THREE.LoopOnce: retain the actual last sample, never wrap to frame 0.
      action.clampWhenFinished = true;
      action.play();
      for (let f = 0; f < numFrames; f++) {
        mixer.setTime((f / (numFrames - 1)) * duration);
        model.updateWorldMatrix(true, true);
        for (const key of Object.keys(bones)) {
          const q = relativeQuat(key);
          boneTracks[key].values.push(...q.toArray().map(v => Number(v.toFixed(6))));
        }
        positions.push(...bones.Hips.getWorldPosition(new THREE.Vector3()).toArray().map(v => Number(v.toFixed(6))));
      }
    } finally {
      mixer.stopAllAction();
      mixer.uncacheRoot(model);
      for (const [n, p, q, s] of saved) { n.position.copy(p); n.quaternion.copy(q); n.scale.copy(s); }
      model.updateWorldMatrix(true, true);
    }
    const tracks = Object.values(boneTracks);
    for (const tr of tracks) {
      const base = tr.values.slice(0, 4);
      if (tr.values.every((v, i) => Math.abs(v - base[i % 4]) < 0.000005)) tr.values = base;
    }
    tracks.push({ bone: 'Hips', rawBone: bones.Hips.name, type: 'position', values: positions });
    return { id, name: clip.name && clip.name !== 'mixamo.com' ? clip.name : id, category,
      duration, fps, numFrames, hipsRestPosition, boneRestPose, boneRestPositions, boneParents, tracks };
  }

  function mapHumanoidSkeleton(rootObject, optionalTHREE) {
    const THREE = getTHREE(optionalTHREE);
    if (!rootObject) throw new Error("mapHumanoidSkeleton: rootObject is required");

    rootObject.updateWorldMatrix(true, true);

    const bones = collectHumanoidBones(rootObject);
    const boneToCanonical = {};
    const canonicalToOriginalName = {};

    for (const [canonical, node] of Object.entries(bones)) {
      boneToCanonical[node.uuid] = canonical;
      canonicalToOriginalName[canonical] = node.name;
    }

    // Capture Rest Pose
    const restLocalPos = {};
    const restLocalQuat = {};
    const restLocalMatrix = {};
    const restWorldPos = {};
    const restWorldQuat = {};
    const restWorldMatrix = {};

    const tempV = new THREE.Vector3();
    const tempQ = new THREE.Quaternion();
    const tempS = new THREE.Vector3();

    for (const [canonical, bone] of Object.entries(bones)) {
      restLocalPos[canonical] = bone.position.clone();
      restLocalQuat[canonical] = bone.quaternion.clone();
      restLocalMatrix[canonical] = bone.matrix.clone();

      bone.matrixWorld.decompose(tempV, tempQ, tempS);
      restWorldPos[canonical] = tempV.clone();
      restWorldQuat[canonical] = tempQ.clone();
      restWorldMatrix[canonical] = bone.matrixWorld.clone();
    }

    // Helper to calculate hand anatomical vectors
    function computeHandVectors(handKey) {
      const handBone = bones[handKey];
      if (!handBone) return null;

      const handWorldPos = restWorldPos[handKey];
      const handWorldQuat = restWorldQuat[handKey];
      const handWorldQuatInv = handWorldQuat.clone().invert();

      const mid1 = bones[`${handKey}Middle1`];
      const idx1 = bones[`${handKey}Index1`];
      const pnk1 = bones[`${handKey}Pinky1`];

      let handFwdWorld, bladeDirWorld, palmInWorld, hingeAxisWorld;

      if (mid1 && idx1 && pnk1) {
        const midPos = restWorldPos[`${handKey}Middle1`];
        const idxPos = restWorldPos[`${handKey}Index1`];
        const pnkPos = restWorldPos[`${handKey}Pinky1`];

        handFwdWorld = midPos.clone().sub(handWorldPos).normalize();
        bladeDirWorld = idxPos.clone().sub(pnkPos).normalize();
        palmInWorld = bladeDirWorld.clone().cross(handFwdWorld).normalize();

        // In Three.js Y-up, in standard rest pose palms face downward (-Y).
        if (palmInWorld.y > 0) {
          palmInWorld.negate();
        }
        hingeAxisWorld = handFwdWorld.clone().cross(palmInWorld).normalize();
      } else {
        // Fallback when finger bones do not exist
        const armKey = handKey === 'RightHand' ? 'RightForeArm' : 'LeftForeArm';
        const forearmPos = restWorldPos[armKey];
        if (forearmPos) {
          handFwdWorld = handWorldPos.clone().sub(forearmPos).normalize();
        } else {
          handFwdWorld = new THREE.Vector3(0, 1, 0).applyQuaternion(handWorldQuat).normalize();
        }
        bladeDirWorld = new THREE.Vector3(1, 0, 0).applyQuaternion(handWorldQuat).normalize();
        palmInWorld = bladeDirWorld.clone().cross(handFwdWorld).normalize();
        if (palmInWorld.y > 0) palmInWorld.negate();
        hingeAxisWorld = handFwdWorld.clone().cross(palmInWorld).normalize();
      }

      // Convert to hand local space
      const handFwdLocal = handFwdWorld.clone().applyQuaternion(handWorldQuatInv).normalize();
      const bladeDirLocal = bladeDirWorld.clone().applyQuaternion(handWorldQuatInv).normalize();
      const palmInLocal = palmInWorld.clone().applyQuaternion(handWorldQuatInv).normalize();
      const hingeAxisLocal = hingeAxisWorld.clone().applyQuaternion(handWorldQuatInv).normalize();

      return {
        handFwdWorld,
        bladeDirWorld,
        palmInWorld,
        hingeAxisWorld,
        handFwdLocal,
        bladeDirLocal,
        palmInLocal,
        hingeAxisLocal
      };
    }

    const rightHandVectors = computeHandVectors('RightHand');
    const leftHandVectors = computeHandVectors('LeftHand');

    // Height and Hips rest Y
    const hipsRestY = restWorldPos.Hips ? restWorldPos.Hips.y : 1.0;

    let hipsParentWorldMatrixInv = new THREE.Matrix4();
    let hipsParentWorldQuatInv = new THREE.Quaternion();
    if (bones.Hips && bones.Hips.parent) {
      bones.Hips.parent.updateWorldMatrix(true, false);
      hipsParentWorldMatrixInv.copy(bones.Hips.parent.matrixWorld).invert();
      bones.Hips.parent.getWorldQuaternion(hipsParentWorldQuatInv);
      hipsParentWorldQuatInv.invert();
    }

    const bbox = new THREE.Box3().setFromObject(rootObject);
    const bSize = new THREE.Vector3();
    bbox.getSize(bSize);

    let minBoneY = Infinity;
    let maxBoneY = -Infinity;
    for (const wp of Object.values(restWorldPos)) {
      if (wp && isFinite(wp.y)) {
        if (wp.y < minBoneY) minBoneY = wp.y;
        if (wp.y > maxBoneY) maxBoneY = wp.y;
      }
    }
    const boneSpanY = (isFinite(minBoneY) && isFinite(maxBoneY) && maxBoneY > minBoneY)
      ? (maxBoneY - minBoneY) * 1.18
      : 0;
    const headY = restWorldPos.Head ? restWorldPos.Head.y : hipsRestY * 1.65;
    const headHeightEst = headY * 1.12;

    let charHeight = Math.max(bSize.y || 0, bSize.z || 0, boneSpanY, headHeightEst);
    if (!isFinite(charHeight) || charHeight <= 0.05) {
      charHeight = Math.max(1.8, hipsRestY * 1.85);
    }

    return {
      rootObject,
      bones,
      boneToCanonical,
      canonicalToOriginalName,
      restLocalPos,
      restLocalQuat,
      restLocalMatrix,
      restWorldPos,
      restWorldQuat,
      restWorldMatrix,
      hipsParentWorldMatrixInv,
      hipsParentWorldQuatInv,
      rightHandVectors,
      leftHandVectors,
      charHeight,
      hipsRestY,
      bbox
    };
  }

  // =========================================================================
  // 2. WEAPON GEOMETRY & AUTO-ALIGNMENT
  // =========================================================================

  /**
   * Solve 3x3 eigenvalues and eigenvectors for symmetric covariance matrix using Jacobi method.
   */
  function solveEigen3x3(cov) {
    // cov is 3x3 array [[c00, c01, c02], [c01, c11, c12], [c02, c12, c22]]
    let V = [
      [1, 0, 0],
      [0, 1, 0],
      [0, 0, 1]
    ];
    let A = [
      [cov[0][0], cov[0][1], cov[0][2]],
      [cov[1][0], cov[1][1], cov[1][2]],
      [cov[2][0], cov[2][1], cov[2][2]]
    ];

    for (let iter = 0; iter < 15; iter++) {
      let maxOff = 0;
      let p = 0, q = 1;
      for (let i = 0; i < 3; i++) {
        for (let j = i + 1; j < 3; j++) {
          if (Math.abs(A[i][j]) > maxOff) {
            maxOff = Math.abs(A[i][j]);
            p = i;
            q = j;
          }
        }
      }
      if (maxOff < 1e-8) break;

      const app = A[p][p], aqq = A[q][q], apq = A[p][q];
      const theta = 0.5 * Math.atan2(2 * apq, aqq - app);
      const c = Math.cos(theta);
      const s = Math.sin(theta);

      for (let i = 0; i < 3; i++) {
        const vip = V[i][p];
        const viq = V[i][q];
        V[i][p] = c * vip - s * viq;
        V[i][q] = s * vip + c * viq;
      }

      const newApp = c * c * app - 2 * s * c * apq + s * s * aqq;
      const newAqq = s * s * app + 2 * s * c * apq + c * c * aqq;
      A[p][p] = newApp;
      A[q][q] = newAqq;
      A[p][q] = 0;
      A[q][p] = 0;

      for (let i = 0; i < 3; i++) {
        if (i !== p && i !== q) {
          const aip = A[i][p];
          const aiq = A[i][q];
          A[i][p] = c * aip - s * aiq;
          A[p][i] = A[i][p];
          A[i][q] = s * aip + c * aiq;
          A[q][i] = A[i][q];
        }
      }
    }

    const eigen = [
      { val: A[0][0], vec: [V[0][0], V[1][0], V[2][0]] },
      { val: A[1][1], vec: [V[0][1], V[1][1], V[2][1]] },
      { val: A[2][2], vec: [V[0][2], V[1][2], V[2][2]] }
    ];
    eigen.sort((a, b) => b.val - a.val);
    return eigen;
  }

  /**
   * 2. autoAlignWeaponGeometry(meshDataOrGeometry, charRigMap, options)
   */
  function autoAlignWeaponGeometry(meshDataOrGeometry, charRigMap, options = {}, optionalTHREE) {
    const THREE = getTHREE(optionalTHREE);
    if (!meshDataOrGeometry) throw new Error("autoAlignWeaponGeometry: meshDataOrGeometry required");
    if (!charRigMap) throw new Error("autoAlignWeaponGeometry: charRigMap required");

    const weaponType = options.type || 'rifle'; // 'rifle' or 'sword'
    const scaleMultiplier = options.scaleMultiplier || 1.0;
    const attachBoneName = options.attachBoneName || 'RightHand';
    if (!['LeftHand', 'RightHand'].includes(attachBoneName) || !charRigMap.bones[attachBoneName]) {
      throw new Error(`autoAlignWeaponGeometry: attachment hand ${attachBoneName} is not mapped`);
    }
    const attachHandKey = attachBoneName === 'RightHand' ? 'rightHandVectors' : 'leftHandVectors';

    // Collect all vertex positions
    let positions = [];
    if (meshDataOrGeometry.isBufferGeometry) {
      positions.push(meshDataOrGeometry.attributes.position.array);
    } else if (meshDataOrGeometry.isMesh) {
      positions.push(meshDataOrGeometry.geometry.attributes.position.array);
    } else if (meshDataOrGeometry.positions) {
      positions.push(meshDataOrGeometry.positions);
    } else if (meshDataOrGeometry.traverse) {
      meshDataOrGeometry.traverse(node => {
        if (node.isMesh && node.geometry && node.geometry.attributes && node.geometry.attributes.position) {
          positions.push(node.geometry.attributes.position.array);
        }
      });
    }

    let totalPoints = 0;
    for (const arr of positions) totalPoints += arr.length / 3;
    if (totalPoints === 0) {
      throw new Error("autoAlignWeaponGeometry: No vertex positions found in geometry");
    }

    // Centroid
    let meanX = 0, meanY = 0, meanZ = 0;
    for (const arr of positions) {
      for (let i = 0; i < arr.length; i += 3) {
        meanX += arr[i];
        meanY += arr[i + 1];
        meanZ += arr[i + 2];
      }
    }
    meanX /= totalPoints;
    meanY /= totalPoints;
    meanZ /= totalPoints;
    const centroid = new THREE.Vector3(meanX, meanY, meanZ);

    // Covariance matrix 3x3
    let c00 = 0, c01 = 0, c02 = 0;
    let c11 = 0, c12 = 0, c22 = 0;
    for (const arr of positions) {
      for (let i = 0; i < arr.length; i += 3) {
        const dx = arr[i] - meanX;
        const dy = arr[i + 1] - meanY;
        const dz = arr[i + 2] - meanZ;
        c00 += dx * dx;
        c01 += dx * dy;
        c02 += dx * dz;
        c11 += dy * dy;
        c12 += dy * dz;
        c22 += dz * dz;
      }
    }
    c00 /= totalPoints;
    c01 /= totalPoints;
    c02 /= totalPoints;
    c11 /= totalPoints;
    c12 /= totalPoints;
    c22 /= totalPoints;

    const cov = [
      [c00, c01, c02],
      [c01, c11, c12],
      [c02, c12, c22]
    ];

    const eigen = solveEigen3x3(cov);

    let axisBarrel = new THREE.Vector3(eigen[0].vec[0], eigen[0].vec[1], eigen[0].vec[2]).normalize();
    let axisUp = new THREE.Vector3(eigen[1].vec[0], eigen[1].vec[1], eigen[1].vec[2]).normalize();
    let axisRight = new THREE.Vector3().crossVectors(axisBarrel, axisUp).normalize();
    axisUp.crossVectors(axisRight, axisBarrel).normalize();

    // Project points onto axes
    let minU = Infinity, maxU = -Infinity;
    let minV = Infinity, maxV = -Infinity;
    let minW = Infinity, maxW = -Infinity;

    for (const arr of positions) {
      for (let i = 0; i < arr.length; i += 3) {
        const d = new THREE.Vector3(arr[i] - meanX, arr[i + 1] - meanY, arr[i + 2] - meanZ);
        const u = d.dot(axisBarrel);
        const v = d.dot(axisUp);
        const w = d.dot(axisRight);
        if (u < minU) minU = u; if (u > maxU) maxU = u;
        if (v < minV) minV = v; if (v > maxV) maxV = v;
        if (w < minW) minW = w; if (w > maxW) maxW = w;
      }
    }

    const Lmax = maxU - minU;
    const Lmid = maxV - minV;
    const Lmin = maxW - minW;

    // Polarity: Barrel vs Stock (Muzzle is narrower, stock/butt is bulkier)
    const quarter = Lmax * 0.25;
    let countPos = 0, countNeg = 0;
    let spreadPosV = 0, spreadNegV = 0;
    let minPosV = Infinity, maxPosV = -Infinity;
    let minNegV = Infinity, maxNegV = -Infinity;

    for (const arr of positions) {
      for (let i = 0; i < arr.length; i += 3) {
        const d = new THREE.Vector3(arr[i] - meanX, arr[i + 1] - meanY, arr[i + 2] - meanZ);
        const u = d.dot(axisBarrel);
        const v = d.dot(axisUp);
        if (u > maxU - quarter) {
          countPos++;
          if (v < minPosV) minPosV = v;
          if (v > maxPosV) maxPosV = v;
        } else if (u < minU + quarter) {
          countNeg++;
          if (v < minNegV) minNegV = v;
          if (v > maxNegV) maxNegV = v;
        }
      }
    }
    spreadPosV = countPos > 0 ? (maxPosV - minPosV) : 0;
    spreadNegV = countNeg > 0 ? (maxNegV - minNegV) : 0;

    // Narrower vertical spread indicates the barrel tip
    let muzzleAtPositive = true;
    if (spreadNegV < spreadPosV) {
      axisBarrel.negate();
      muzzleAtPositive = false;
      const oldMinU = minU;
      minU = -maxU;
      maxU = -oldMinU;
    }

    // Polarity: Up (Sight/Rail) vs Down (Grip/Magazine protrusion)
    // Measure the barrel line center at the front quarter (muzzle region)
    let frontVMin = Infinity, frontVMax = -Infinity;
    for (const arr of positions) {
      for (let i = 0; i < arr.length; i += 3) {
        const d = new THREE.Vector3(arr[i] - meanX, arr[i + 1] - meanY, arr[i + 2] - meanZ);
        const u = d.dot(axisBarrel);
        const v = d.dot(axisUp);
        if (u > maxU - 0.25 * Lmax) {
          if (v < frontVMin) frontVMin = v;
          if (v > frontVMax) frontVMax = v;
        }
      }
    }
    const vBarrel = (frontVMin + frontVMax) * 0.5;
    const dTop = maxV - vBarrel;
    const dBottom = vBarrel - minV;

    // The grip/magazine protrudes downwards (-axisUp), so dBottom should be > dTop
    if (dTop > dBottom) {
      axisUp.negate();
      const oldMinV = minV;
      minV = -maxV;
      maxV = -oldMinV;
    }
    axisRight.crossVectors(axisBarrel, axisUp).normalize();

    // User overrides
    if (options.flipBarrel) {
      axisBarrel.negate();
      const oldMinU = minU;
      minU = -maxU;
      maxU = -oldMinU;
    }
    if (options.flipUp) {
      axisUp.negate();
      const oldMinV = minV;
      minV = -maxV;
      maxV = -oldMinV;
    }
    axisRight.crossVectors(axisBarrel, axisUp).normalize();
    const sourceLateral = new THREE.Vector3().crossVectors(axisUp, axisBarrel).normalize();

    // roll90 is applied as a semantic rotation below so the grip pivot stays fixed.

    // Account for the selected attachment hand's world scale.
    let handWorldScale = 1.0;
    const handRestMatrix = charRigMap.restWorldMatrix && charRigMap.restWorldMatrix[attachBoneName];
    if (handRestMatrix) {
      const ws = new THREE.Vector3().setFromMatrixScale(handRestMatrix);
      if (isFinite(ws.x) && ws.x > 1e-4) handWorldScale = ws.x;
    }

    // Auto-scale in RightHand local space so world length matches target proportion of charHeight
    const targetWorldLength = charRigMap.charHeight * (weaponType === 'sword' ? 0.62 : 0.52) * scaleMultiplier;
    const scaleFactor = (targetWorldLength / handWorldScale) / Math.max(0.001, Lmax);

    // Grip Pivot and Foregrip Point
    let gripUFraction, foregripUFraction;
    let gripVOffset, foregripVOffset;

    if (weaponType === 'sword') {
      gripUFraction = 0.16; // from pommel
      foregripUFraction = 0.10;
      gripVOffset = 0.0;
      foregripVOffset = 0.0;
    } else {
      // Rifle
      gripUFraction = 0.28; // from stock
      foregripUFraction = 0.62; // on handguard
      gripVOffset = -0.06 * Lmax; // slightly down into pistol grip
      foregripVOffset = -0.02 * Lmax;
    }

    const uGrip = minU + gripUFraction * Lmax;
    const vGrip = ((minV + maxV) * 0.5) + gripVOffset;
    const wGrip = (minW + maxW) * 0.5;

    const uForegrip = minU + foregripUFraction * Lmax;
    const vForegrip = ((minV + maxV) * 0.5) + foregripVOffset;
    const wForegrip = (minW + maxW) * 0.5;

    // In weapon mesh local coordinates
    const gripPivotLocal = centroid.clone()
      .add(axisBarrel.clone().multiplyScalar(uGrip))
      .add(axisUp.clone().multiplyScalar(vGrip))
      .add(axisRight.clone().multiplyScalar(wGrip));

    const foregripLocalPos = centroid.clone()
      .add(axisBarrel.clone().multiplyScalar(uForegrip))
      .add(axisUp.clone().multiplyScalar(vForegrip))
      .add(axisRight.clone().multiplyScalar(wForegrip));
    const foregripOffset = options.foregripOffset;
    if (Array.isArray(foregripOffset)) {
      const unitScale = (charRigMap.charHeight / 1.8) / (handWorldScale * scaleFactor);
      foregripLocalPos
        .add(axisBarrel.clone().multiplyScalar((foregripOffset[0] || 0) * unitScale))
        .add(axisUp.clone().multiplyScalar((foregripOffset[1] || 0) * unitScale))
        .add(sourceLateral.clone().multiplyScalar((foregripOffset[2] || 0) * unitScale));
    }

    // Construct localMatrix4 in the selected hand's local space.
    const handVecs = charRigMap[attachHandKey] || {
      handFwdLocal: new THREE.Vector3(0, 1, 0),
      palmInLocal: new THREE.Vector3(0, 0, -1),
      hingeAxisLocal: new THREE.Vector3(1, 0, 0)
    };

    // Target basis in hand local coordinates:
    let targetBarrel, targetUp, targetRight;
    if (weaponType === 'sword') {
      // Sword hilt passes through the closed fist along the thumb-index hinge axis (handFwd x palmIn)
      targetBarrel = handVecs.hingeAxisLocal.clone().normalize();
      // Cutting edge / crossguard aligns with knuckles forward (handFwd)
      targetUp = handVecs.handFwdLocal.clone().normalize();
      targetRight = new THREE.Vector3().crossVectors(targetBarrel, targetUp).normalize();
      targetUp.crossVectors(targetRight, targetBarrel).normalize();
    } else {
      // Rifle: barrel points along handFwd (pitched slightly down for pistol grip rake and yawed inward toward left hand)
      const baseFwd = handVecs.handFwdLocal.clone().normalize();
      const baseUp = handVecs.hingeAxisLocal.clone().normalize(); // thumb/index side points UP (+Y) in aiming pose
      const baseRight = new THREE.Vector3().crossVectors(baseFwd, baseUp).normalize(); // -palmIn points RIGHT (-X)

      const inwardYaw = attachBoneName === 'LeftHand' ? -14 : 14;
      targetBarrel = baseFwd.clone()
        .applyAxisAngle(baseRight, THREE.MathUtils.degToRad(-12))
        .applyAxisAngle(baseUp, THREE.MathUtils.degToRad(inwardYaw))
        .normalize();
      targetUp = baseUp.clone();
      targetRight = new THREE.Vector3().crossVectors(targetBarrel, targetUp).normalize();
      targetUp.crossVectors(targetRight, targetBarrel).normalize();
    }

    // Semantic weapon basis is right-handed: X=lateral, Y=up, Z=barrel.
    const targetLateral = new THREE.Vector3().crossVectors(targetUp, targetBarrel).normalize();
    const mSrc = new THREE.Matrix4().makeBasis(sourceLateral, axisUp, axisBarrel);
    const mDst = new THREE.Matrix4().makeBasis(targetLateral, targetUp, targetBarrel);
    const autoRotQuat = new THREE.Quaternion().setFromRotationMatrix(
      new THREE.Matrix4().multiplyMatrices(mDst, mSrc.clone().invert())
    );

    // Manual XYZ means lateral/up/barrel and rotates around those axes in hand space.
    const semanticHandQuat = new THREE.Quaternion().setFromRotationMatrix(mDst);
    const manualEuler = new THREE.Euler(
      THREE.MathUtils.degToRad(options.offsetRotDeg?.[0] || 0),
      THREE.MathUtils.degToRad(options.offsetRotDeg?.[1] || 0),
      THREE.MathUtils.degToRad((options.offsetRotDeg?.[2] || 0) + (options.roll90 || 0) * 90),
      'XYZ'
    );
    const manualHandQuat = semanticHandQuat.clone()
      .multiply(new THREE.Quaternion().setFromEuler(manualEuler))
      .multiply(semanticHandQuat.clone().invert());
    const rotQuat = manualHandQuat.clone().multiply(autoRotQuat);

    // Hand grip center in hand local space
    const handBone = charRigMap.bones[attachBoneName];
    const midKnuckle = charRigMap.bones[`${attachBoneName}Middle1`];
    let handGripCenterLocal;

    if (midKnuckle && handBone) {
      // Wrist to middle knuckle center, displaced slightly into the palm
      const wristLocal = new THREE.Vector3(0, 0, 0);
      const midPosInHand = midKnuckle.getWorldPosition(new THREE.Vector3())
        .applyMatrix4(handBone.matrixWorld.clone().invert());
      handGripCenterLocal = wristLocal.clone().lerp(midPosInHand, 0.60)
        .add(handVecs.palmInLocal.clone().multiplyScalar(midPosInHand.length() * 0.25));
    } else {
      const fallbackDist = (charRigMap.charHeight * 0.03) / handWorldScale;
      handGripCenterLocal = handVecs.handFwdLocal.clone().multiplyScalar(fallbackDist);
    }

    if (options.offsetPos && Array.isArray(options.offsetPos)) {
      const unitScale = (charRigMap.charHeight / 1.8) / handWorldScale;
      handGripCenterLocal.add(new THREE.Vector3(
        (options.offsetPos[0] || 0) * unitScale,
        (options.offsetPos[1] || 0) * unitScale,
        (options.offsetPos[2] || 0) * unitScale
      ));
    }

    // Position weapon so gripPivotLocal lands at handGripCenterLocal:
    // P_hand = Pos + R * (Scale * P_weapon)  =>  Pos = P_hand - R * (Scale * gripPivotLocal)
    const scaledGrip = gripPivotLocal.clone().multiplyScalar(scaleFactor);
    scaledGrip.applyQuaternion(rotQuat);
    const finalPos = handGripCenterLocal.clone().sub(scaledGrip);

    const localMatrix4 = new THREE.Matrix4().compose(
      finalPos,
      rotQuat,
      new THREE.Vector3(scaleFactor, scaleFactor, scaleFactor)
    );

    return {
      localMatrix4,
      foregripLocalPos,
      gripPivotLocal,
      length: Lmax * scaleFactor,
      rawLength: Lmax,
      scaleFactor,
      bbox: { min: [minU, minV, minW], max: [maxU, maxV, maxW] },
      attachBoneName,
      autoDetectedAxes: {
        axisBarrel: axisBarrel.toArray(),
        axisUp: axisUp.toArray(),
        axisRight: axisRight.toArray(),
        muzzleAtPositive
      },
      finalLocalAxes: {
        axisBarrel: targetBarrel.clone().applyQuaternion(manualHandQuat).normalize().toArray(),
        axisUp: targetUp.clone().applyQuaternion(manualHandQuat).normalize().toArray(),
        axisRight: targetLateral.clone().applyQuaternion(manualHandQuat).normalize().toArray()
      }
    };
  }

  // =========================================================================
  // 3. ANIMATION RETARGET PREPARATION
  // =========================================================================

  /**
   * Helper to sample keyframe tracks with binary search and lerp/slerp.
   */
  function sampleTrack(times, values, stride, timeSec, isQuat, THREE) {
    if (!times || times.length === 0) return null;
    if (timeSec <= times[0]) {
      return isQuat
        ? new THREE.Quaternion(values[0], values[1], values[2], values[3])
        : new THREE.Vector3(values[0], values[1], values[2]);
    }
    const lastIdx = times.length - 1;
    if (timeSec >= times[lastIdx]) {
      const o = lastIdx * stride;
      return isQuat
        ? new THREE.Quaternion(values[o], values[o + 1], values[o + 2], values[o + 3])
        : new THREE.Vector3(values[o], values[o + 1], values[o + 2]);
    }

    // Binary search
    let low = 0, high = lastIdx;
    while (low <= high) {
      const mid = (low + high) >> 1;
      if (times[mid] < timeSec) low = mid + 1;
      else high = mid - 1;
    }
    const idx0 = Math.max(0, low - 1);
    const idx1 = Math.min(lastIdx, idx0 + 1);
    const t0 = times[idx0], t1 = times[idx1];
    const alpha = (t1 > t0) ? (timeSec - t0) / (t1 - t0) : 0;

    const o0 = idx0 * stride;
    const o1 = idx1 * stride;

    if (isQuat) {
      const q0 = new THREE.Quaternion(values[o0], values[o0 + 1], values[o0 + 2], values[o0 + 3]);
      const q1 = new THREE.Quaternion(values[o1], values[o1 + 1], values[o1 + 2], values[o1 + 3]);
      return q0.slerp(q1, alpha);
    } else {
      const v0 = new THREE.Vector3(values[o0], values[o0 + 1], values[o0 + 2]);
      const v1 = new THREE.Vector3(values[o1], values[o1 + 1], values[o1 + 2]);
      return v0.lerp(v1, alpha);
    }
  }

  /**
   * 3. prepareAnimationRetarget(charRigMap, animClipData)
   */
  function prepareAnimationRetarget(charRigMap, animClipData, optionalTHREE) {
    const THREE = getTHREE(optionalTHREE);
    if (!charRigMap || !animClipData) throw new Error("prepareAnimationRetarget: charRigMap and animClipData required");
    const hybrid = animClipData.hybrid || animClipData.layers;
    if (hybrid) {
      const lowerData = hybrid.lower || hybrid.lowerAnimation;
      const upperData = hybrid.upper || hybrid.upperAnimation;
      if (!lowerData || !upperData || typeof lowerData !== 'object' || typeof upperData !== 'object') throw new Error("prepareAnimationRetarget: hybrid requires resolved lower and upper animation objects");
      if (lowerData.hybrid || lowerData.layers || upperData.hybrid || upperData.layers) throw new Error("prepareAnimationRetarget: nested hybrid layers are not supported");
      const lower = prepareAnimationRetarget(charRigMap, lowerData, THREE);
      const upper = prepareAnimationRetarget(charRigMap, upperData, THREE);
      const roots = (hybrid.upperCanonicalRoots || ['Spine','Neck','Head','LeftShoulder','LeftArm','LeftForeArm','LeftHand','RightShoulder','RightArm','RightForeArm','RightHand']).map(normalizeCanonicalBoneName).filter(Boolean);
      return { animClip:animClipData, duration:animClipData.duration || lower.duration,
        sourceTracksByCanonical:lower.sourceTracksByCanonical, sourceLocalQuat:lower.sourceLocalQuat,
        restSourceWorldQuat:lower.restSourceWorldQuat, alignQuat:lower.alignQuat,
        sourceHipsRestPos:lower.sourceHipsRestPos, sourceHipsRestY:lower.sourceHipsRestY,
        hipsScaleRatio:lower.hipsScaleRatio,
        layers:{lower,upper,upperRoots:new Set(roots),upperTimeMode:hybrid.upperTimeMode || 'normalized'} };
    }

    const tracks = animClipData.tracks || [];
    const duration = Number.isFinite(animClipData.duration) && animClipData.duration > 0 ? animClipData.duration : 1;
    const frameCount = Number.isInteger(animClipData.numFrames) && animClipData.numFrames > 0 ? animClipData.numFrames : null;
    const sourceTracksByCanonical = {};
    const quatValues = (src,label) => {
      const out = new Float32Array(src.length);
      for (let i=0;i<src.length;i+=4) {
        const q=[Number(src[i]),Number(src[i+1]),Number(src[i+2]),Number(src[i+3])], len=Math.hypot(...q);
        if (!q.every(Number.isFinite) || !Number.isFinite(len) || len<1e-8) throw new Error(`prepareAnimationRetarget: invalid quaternion in ${label} sample ${i/4}`);
        for (let j=0;j<4;j++) out[i+j]=q[j]/len;
      }
      return out;
    };
    for (const track of tracks) {
      let rawName='', prop='';
      if (track.name) { const dot=track.name.lastIndexOf('.'); rawName=dot<0?track.name:track.name.slice(0,dot); prop=dot<0?'':track.name.slice(dot+1); }
      else if (track.bone) { rawName=track.bone; prop=track.type || 'quaternion'; }
      const canonical=normalizeCanonicalBoneName(rawName);
      if (!canonical) continue;
      if (prop.startsWith('rotation') || prop==='euler') throw new Error(`prepareAnimationRetarget: Euler rotation track ${rawName} must be converted to quaternion`);
      const isQuat=prop.startsWith('quaternion'), isPos=prop.startsWith('position');
      if (!isQuat && !isPos) continue;
      const kind=isQuat?'quaternion':'position', stride=isQuat?4:3;
      if (sourceTracksByCanonical[canonical]?.[kind]) throw new Error(`prepareAnimationRetarget: duplicate ${kind} track for ${canonical}`);
      const rawValues=track.values;
      if (!rawValues || typeof rawValues.length!=='number' || rawValues.length===0 || rawValues.length%stride) throw new Error(`prepareAnimationRetarget: malformed ${kind} values for ${canonical}`);
      const n=rawValues.length/stride;
      if (!track.times && frameCount && n!==1 && n!==frameCount) throw new Error(`prepareAnimationRetarget: ${canonical} sample count ${n} must be 1 or numFrames ${frameCount}`);
      let times;
      if (track.times) {
        if (track.times.length!==n) throw new Error(`prepareAnimationRetarget: ${canonical} times/value count mismatch`);
        times=new Float32Array(track.times);
        for (let i=0;i<n;i++) if (!Number.isFinite(times[i]) || (i && times[i]<times[i-1])) throw new Error(`prepareAnimationRetarget: invalid times for ${canonical} ${kind}`);
      } else if (n===1) times=new Float32Array([0,duration]);
      else { times=new Float32Array(n); for (let i=0;i<n;i++) times[i]=i*duration/(n-1); }
      let values=new Float32Array(rawValues);
      if (isQuat) { if (n===1 && !track.times) values=new Float32Array([...values,...values]); values=quatValues(values,canonical); }
      else {
        for (const v of values) if (!Number.isFinite(v)) throw new Error(`prepareAnimationRetarget: non-finite position for ${canonical}`);
        if (n===1 && !track.times) values=new Float32Array([...values,...values]);
      }
      sourceTracksByCanonical[canonical] ||= {};
      sourceTracksByCanonical[canonical][kind]={times,values};
    }

    const sourceParentMap={};
    if (animClipData.boneParents && typeof animClipData.boneParents==='object') {
      for (const [rawChild,rawParent] of Object.entries(animClipData.boneParents)) {
        const child=normalizeCanonicalBoneName(rawChild)||rawChild;
        sourceParentMap[child]=rawParent==null?null:(normalizeCanonicalBoneName(rawParent)||rawParent);
      }
    } else {
      Object.assign(sourceParentMap,{Spine:'Hips',Spine1:'Spine',Spine2:'Spine1',Neck:'Spine2',Head:'Neck',
        LeftShoulder:'Spine2',LeftArm:'LeftShoulder',LeftForeArm:'LeftArm',LeftHand:'LeftForeArm',
        RightShoulder:'Spine2',RightArm:'RightShoulder',RightForeArm:'RightArm',RightHand:'RightForeArm',
        LeftUpLeg:'Hips',LeftLeg:'LeftUpLeg',LeftFoot:'LeftLeg',LeftToeBase:'LeftFoot',
        RightUpLeg:'Hips',RightLeg:'RightUpLeg',RightFoot:'RightLeg',RightToeBase:'RightFoot'});
      for (const hand of ['LeftHand','RightHand']) for (const finger of FINGER_NAMES) {
        sourceParentMap[`${hand}${finger}1`]=hand;
        sourceParentMap[`${hand}${finger}2`]=`${hand}${finger}1`;
        sourceParentMap[`${hand}${finger}3`]=`${hand}${finger}2`;
      }
    }
    const sourceLocalQuat={};
    for (const [rawKey,values] of Object.entries(animClipData.boneRestPose || {})) {
      const key=normalizeCanonicalBoneName(rawKey)||rawKey;
      if (Array.isArray(values) && values.length===4) { const q=quatValues(values,`rest pose ${key}`); sourceLocalQuat[key]=new THREE.Quaternion(q[0],q[1],q[2],q[3]); }
    }
    for (const [key,obj] of Object.entries(sourceTracksByCanonical)) if (!sourceLocalQuat[key] && obj.quaternion) sourceLocalQuat[key]=sampleTrack(obj.quaternion.times,obj.quaternion.values,4,0,true,THREE);
    const restSourceWorldQuat={}, resolving=new Set();
    function sourceWorld(key) {
      if (restSourceWorldQuat[key]) return restSourceWorldQuat[key];
      if (resolving.has(key)) throw new Error(`prepareAnimationRetarget: cyclic boneParents at ${key}`);
      resolving.add(key);
      const local=sourceLocalQuat[key] || new THREE.Quaternion();
      const parent=Object.prototype.hasOwnProperty.call(sourceParentMap,key)?sourceParentMap[key]:null;
      const world=parent?sourceWorld(parent).clone().multiply(local).normalize():local.clone().normalize();
      resolving.delete(key); return restSourceWorldQuat[key]=world;
    }
    for (const key of new Set([...Object.keys(sourceLocalQuat),...Object.keys(sourceTracksByCanonical),...Object.keys(sourceParentMap)])) sourceWorld(key);

    let sourceHipsRestPos=sourceTracksByCanonical.Hips?.position
      ? sampleTrack(sourceTracksByCanonical.Hips.position.times,sourceTracksByCanonical.Hips.position.values,3,0,false,THREE)
      : new THREE.Vector3(0,1,0);
    if (Array.isArray(animClipData.hipsRestPosition) && animClipData.hipsRestPosition.length===3) sourceHipsRestPos=new THREE.Vector3(...animClipData.hipsRestPosition);
    const sourceHipsRestY=Math.max(0.01,Math.abs(sourceHipsRestPos.y)), hipsScaleRatio=(charRigMap.hipsRestY || 1)/sourceHipsRestY;
    const alignQuat={}, childMap={LeftShoulder:'LeftArm',LeftArm:'LeftForeArm',LeftForeArm:'LeftHand',
      RightShoulder:'RightArm',RightArm:'RightForeArm',RightForeArm:'RightHand',
      LeftUpLeg:'LeftLeg',LeftLeg:'LeftFoot',RightUpLeg:'RightLeg',RightLeg:'RightFoot'};
    const sourceRestPositions=animClipData.boneRestPositions || {};
    for (const canonical of Object.keys(charRigMap.bones || {})) {
      const child=childMap[canonical], dest=child && charRigMap.restWorldPos[child]
        ? charRigMap.restWorldPos[child].clone().sub(charRigMap.restWorldPos[canonical]).normalize()
        : new THREE.Vector3(0,1,0).applyQuaternion(charRigMap.restWorldQuat[canonical]).normalize();
      const srcChild=child && sourceRestPositions[child], srcBone=sourceRestPositions[canonical];
      const srcDir=srcChild && srcBone
        ? new THREE.Vector3().fromArray(srcChild).sub(new THREE.Vector3().fromArray(srcBone)).normalize()
        : new THREE.Vector3(0,1,0).applyQuaternion(restSourceWorldQuat[canonical] || new THREE.Quaternion()).normalize();
      alignQuat[canonical]=LIMB_KEYWORDS.some(k=>canonical.includes(k))
        ? new THREE.Quaternion().setFromUnitVectors(dest,srcDir)
        : new THREE.Quaternion();
    }
    return {animClip:animClipData,duration,sourceTracksByCanonical,sourceLocalQuat,sourceParentMap,
      restSourceWorldQuat,alignQuat,sourceHipsRestPos,sourceHipsRestY,hipsScaleRatio,layers:null};
  }

  // =========================================================================
  // 4. RETARGET FRAME EVALUATOR & PROCEDURAL IK
  // =========================================================================

  /**
   * 4. evaluateRetargetFrame(charRigMap, retargetCtx, timeSec, params, weaponContext)
   */
  function evaluateRetargetFrame(charRigMap, retargetCtx, timeSec, params = {}, weaponContext = null, optionalTHREE) {
    const THREE = getTHREE(optionalTHREE);
    if (!charRigMap || !retargetCtx) throw new Error("evaluateRetargetFrame: charRigMap and retargetCtx required");
    const bones = charRigMap.bones;
    const baseCtx = retargetCtx.layers ? retargetCtx.layers.lower : retargetCtx;
    const upperCtx = retargetCtx.layers && retargetCtx.layers.upper;
    const inPlaceLock = params.inPlaceLock !== undefined ? params.inPlaceLock : 1;
    const groundFeet = params.groundFeet !== undefined ? params.groundFeet : true;
    const armSpreadDeg = params.armSpreadDeg || 0;
    const spineTwistDeg = params.spineTwistDeg || 0;
    const spinePitchDeg = params.spinePitchDeg || 0;
    const ikWeight = params.leftHandIkWeight !== undefined ? params.leftHandIkWeight : (weaponContext ? 1 : 0);
    const elbowPoleAngleDeg = params.elbowPoleAngleDeg || 0;
    const rightHandGrip = params.rightHandGrip !== undefined ? params.rightHandGrip : (weaponContext ? 1 : 0);
    const leftHandGrip = params.leftHandGrip !== undefined ? params.leftHandGrip : (weaponContext ? 1 : 0);
    const root = charRigMap.rootObject;

    // Every evaluation starts from authored target rest transforms; repeated scrubbing cannot accumulate.
    for (const [key,bone] of Object.entries(bones)) {
      if (charRigMap.restLocalPos[key]) bone.position.copy(charRigMap.restLocalPos[key]);
      if (charRigMap.restLocalQuat[key]) bone.quaternion.copy(charRigMap.restLocalQuat[key]);
    }
    root.updateWorldMatrix(true,true);

    function isInUpperLayer(key,bone) {
      if (!upperCtx) return false;
      for (let node=bone; node; node=node.parent) {
        const canonical=charRigMap.boneToCanonical[node.uuid];
        if (canonical && retargetCtx.layers.upperRoots.has(canonical)) return true;
      }
      return false;
    }
    function contextFor(key,bone) {
      return key!=='Hips' && isInUpperLayer(key,bone) ? upperCtx : baseCtx;
    }
    function sampleTime(ctx) {
      if (retargetCtx.layers && ctx===upperCtx && retargetCtx.layers.upperTimeMode==='normalized') {
        return (timeSec / Math.max(retargetCtx.duration,1e-8)) * ctx.duration;
      }
      return timeSec;
    }
    const sourceWorldCaches=new Map();
    function sourceCurrentWorld(ctx,key,tSec) {
      let cache=sourceWorldCaches.get(ctx);
      if (!cache) { cache={}; sourceWorldCaches.set(ctx,cache); }
      if (cache[key]) return cache[key];
      const track=ctx.sourceTracksByCanonical[key]?.quaternion;
      const local=track ? sampleTrack(track.times,track.values,4,tSec,true,THREE)
        : (ctx.sourceLocalQuat[key]?.clone() || new THREE.Quaternion());
      const parent=Object.prototype.hasOwnProperty.call(ctx.sourceParentMap || {},key) ? ctx.sourceParentMap[key] : null;
      const world=parent ? sourceCurrentWorld(ctx,parent,tSec).clone().multiply(local).normalize() : local.normalize();
      return cache[key]=world;
    }

    const hipsTrack=baseCtx.sourceTracksByCanonical.Hips?.position;
    if (hipsTrack && bones.Hips && charRigMap.restWorldPos.Hips) {
      const cur=sampleTrack(hipsTrack.times,hipsTrack.values,3,timeSec,false,THREE);
      const delta=cur.clone().sub(baseCtx.sourceHipsRestPos).multiplyScalar(baseCtx.hipsScaleRatio);
      delta.x *= 1-inPlaceLock; delta.z *= 1-inPlaceLock;
      const target=charRigMap.restWorldPos.Hips.clone().add(delta);
      if (charRigMap.hipsParentWorldMatrixInv) bones.Hips.position.copy(target).applyMatrix4(charRigMap.hipsParentWorldMatrixInv);
      else bones.Hips.position.copy(charRigMap.restLocalPos.Hips).add(delta);
    }

    const depth=bone=>{let n=0;for(let p=bone.parent;p;p=p.parent)n++;return n;};
    const ordered=Object.entries(bones).sort((a,b)=>depth(a[1])-depth(b[1]));
    function contextPose(ctx) {
      const t=sampleTime(ctx), worlds=new Map(), locals={};
      function worldOf(node) {
        if (!node) return new THREE.Quaternion();
        if (worlds.has(node)) return worlds.get(node);
        const key=charRigMap.boneToCanonical[node.uuid];
        if (key && bones[key]===node) {
          const sourceNow=sourceCurrentWorld(ctx,key,t);
          const sourceRest=ctx.restSourceWorldQuat[key] || new THREE.Quaternion();
          const delta=sourceNow.clone().multiply(sourceRest.clone().invert()).normalize();
          const desired=delta.multiply(ctx.alignQuat[key] || new THREE.Quaternion())
            .multiply(charRigMap.restWorldQuat[key] || new THREE.Quaternion()).normalize();
          worlds.set(node,desired);
          return desired;
        }
        if (!node.parent) {
          const q=node.getWorldQuaternion(new THREE.Quaternion());
          worlds.set(node,q);
          return q;
        }
        const q=worldOf(node.parent).clone().multiply(node.quaternion).normalize();
        worlds.set(node,q);
        return q;
      }
      for (const [key,bone] of ordered) {
        const now=sourceCurrentWorld(ctx,key,t), rest=ctx.restSourceWorldQuat[key] || new THREE.Quaternion();
        const delta=now.clone().multiply(rest.clone().invert()).normalize();
        const desired=delta.multiply(ctx.alignQuat[key] || new THREE.Quaternion())
          .multiply(charRigMap.restWorldQuat[key] || new THREE.Quaternion()).normalize();
        worlds.set(bone,desired);
        locals[key]=worldOf(bone.parent).clone().invert().multiply(desired).normalize();
      }
      return locals;
    }
    const baseLocals=contextPose(baseCtx);
    const upperLocals=upperCtx ? contextPose(upperCtx) : null;
    for (const [key,bone] of ordered) {
      const ctx=contextFor(key,bone);
      const local=ctx===upperCtx ? upperLocals[key] : baseLocals[key];
      if (local) bone.quaternion.copy(local);
    }
    root.updateWorldMatrix(true,true);

    if (spineTwistDeg || spinePitchDeg || armSpreadDeg) {
      const axisQ=(axis,deg)=>new THREE.Quaternion().setFromAxisAngle(axis,THREE.MathUtils.degToRad(deg));
      if (spineTwistDeg) {
        const q=axisQ(new THREE.Vector3(0,1,0),spineTwistDeg*0.5);
        if (bones.Spine1) bones.Spine1.quaternion.multiply(q);
        if (bones.Spine2) bones.Spine2.quaternion.multiply(q);
      }
      if (spinePitchDeg) {
        const q=axisQ(new THREE.Vector3(1,0,0),spinePitchDeg*0.5);
        if (bones.Spine1) bones.Spine1.quaternion.multiply(q);
        if (bones.Spine2) bones.Spine2.quaternion.multiply(q);
      }
      if (armSpreadDeg) {
        const r=axisQ(new THREE.Vector3(0,0,-1),armSpreadDeg), l=axisQ(new THREE.Vector3(0,0,1),armSpreadDeg);
        if (bones.RightArm) bones.RightArm.quaternion.multiply(r);
        if (bones.LeftArm) bones.LeftArm.quaternion.multiply(l);
      }
    }
    root.updateWorldMatrix(true,true);

    function applyFingerGrip(side,weight) {
      if (weight<=0) return;
      const vecs=side==='RightHand'?charRigMap.rightHandVectors:charRigMap.leftHandVectors;
      if (!vecs) return;
      for (const finger of FINGER_NAMES) {
        const maxDeg=side==='RightHand'
          ? (finger==='Thumb'?45:(finger==='Index'?35:80))
          : (finger==='Thumb'?30:40);
        for (let j=1;j<=3;j++) {
          const key=`${side}${finger}${j}`, bone=bones[key];
          if (!bone) continue;
          const ctx=contextFor(key,bone);
          if (ctx.sourceTracksByCanonical[key]?.quaternion) continue; // preserve authored finger motion
          let axis=vecs.hingeAxisWorld.clone();
          if (finger==='Thumb') axis=vecs.palmInWorld.clone().sub(vecs.handFwdWorld.clone().multiplyScalar(0.4)).normalize();
          const restWorld=charRigMap.restWorldQuat[key] || new THREE.Quaternion();
          axis.applyQuaternion(restWorld.clone().invert()).normalize();
          const fraction=j===1?0.9:(j===2?0.9:0.7);
          const curl=new THREE.Quaternion().setFromAxisAngle(axis,THREE.MathUtils.degToRad(maxDeg*fraction*weight));
          bone.quaternion.copy(charRigMap.restLocalQuat[key] || new THREE.Quaternion()).multiply(curl);
        }
      }
    }
    applyFingerGrip('RightHand',rightHandGrip);
    applyFingerGrip('LeftHand',leftHandGrip);
    root.updateWorldMatrix(true,true);

    // Two-bone support IK targets the hand opposite the selected weapon attachment hand.
    const attach=weaponContext?.attachBoneName || 'RightHand';
    const support=attach==='LeftHand'?'Right':'Left';
    const upperKey=`${support}Arm`, lowerKey=`${support}ForeArm`, handKey=`${support}Hand`;
    const upper=bones[upperKey], lower=bones[lowerKey], hand=bones[handKey];
    if (ikWeight>0 && weaponContext?.localMatrix4 && weaponContext?.foregripLocalPos && bones[attach] && upper && lower && hand) {
      const weaponWorld=bones[attach].matrixWorld.clone().multiply(weaponContext.localMatrix4);
      const gripTarget=weaponContext.foregripLocalPos.clone().applyMatrix4(weaponWorld);
      const posA=upper.getWorldPosition(new THREE.Vector3());
      const posB=lower.getWorldPosition(new THREE.Vector3());
      const posC=hand.getWorldPosition(new THREE.Vector3());
      const L1=charRigMap.restWorldPos[lowerKey] && charRigMap.restWorldPos[upperKey]
        ? charRigMap.restWorldPos[lowerKey].distanceTo(charRigMap.restWorldPos[upperKey]) : posB.distanceTo(posA);
      const L2=charRigMap.restWorldPos[handKey] && charRigMap.restWorldPos[lowerKey]
        ? charRigMap.restWorldPos[handKey].distanceTo(charRigMap.restWorldPos[lowerKey]) : posC.distanceTo(posB);
      if (L1>1e-6 && L2>1e-6) {
        const fkUpperLocal=upper.quaternion.clone(), fkLowerLocal=lower.quaternion.clone(), fkHandLocal=hand.quaternion.clone();
        root.updateWorldMatrix(true,true);
        const fkUpperWorld=upper.getWorldQuaternion(new THREE.Quaternion());
        const fkLowerWorld=lower.getWorldQuaternion(new THREE.Quaternion());
        const fkUpperAxis=posB.clone().sub(posA).normalize(), fkLowerAxis=posC.clone().sub(posB).normalize();
        let wristTarget=gripTarget.clone(), ikHandWorld=null;

        const axes=weaponContext.finalLocalAxes;
        if (axes?.axisBarrel && axes?.axisUp && axes?.axisRight) {
          const handWorld=bones[attach].matrixWorld;
          const direction=arr=>new THREE.Vector3(...arr).transformDirection(handWorld);
          const fwd=direction(axes.axisBarrel).normalize();
          const palm=direction(axes.axisRight).multiplyScalar(support==='Left'?1:-1).normalize();
          const hinge=new THREE.Vector3().crossVectors(fwd,palm).normalize();
          const vecs=support==='Right'?charRigMap.rightHandVectors:charRigMap.leftHandVectors;
          if (vecs) {
            const src=new THREE.Matrix4().makeBasis(vecs.handFwdLocal,vecs.palmInLocal,vecs.hingeAxisLocal);
            const dst=new THREE.Matrix4().makeBasis(fwd,palm,hinge);
            ikHandWorld=new THREE.Quaternion().setFromRotationMatrix(dst.multiply(src.invert()));
            const mid=bones[`${handKey}Middle1`];
            if (mid) {
              const handInv=hand.matrixWorld.clone().invert();
              const midLocal=mid.getWorldPosition(new THREE.Vector3()).applyMatrix4(handInv);
              const centerOffset=midLocal.clone().multiplyScalar(0.6)
                .add(vecs.palmInLocal.clone().multiplyScalar(midLocal.length()*0.25));
              const scale=new THREE.Vector3().setFromMatrixScale(hand.matrixWorld);
              const offsetWorld=centerOffset.multiply(scale).applyQuaternion(ikHandWorld);
              wristTarget.copy(gripTarget).sub(offsetWorld);
            }
          }
        }

        const rawTarget=wristTarget.clone().sub(posA), rawDist=rawTarget.length();
        const targetDir=rawDist>1e-8?rawTarget.multiplyScalar(1/rawDist):new THREE.Vector3(0,1,0);
        const minReach=Math.abs(L1-L2)+1e-5, maxReach=L1+L2-1e-5;
        const dist=THREE.MathUtils.clamp(rawDist,minReach,maxReach);
        const reachableWrist=posA.clone().add(targetDir.clone().multiplyScalar(dist));
        const cosA=THREE.MathUtils.clamp((L1*L1+dist*dist-L2*L2)/(2*L1*dist),-1,1);
        const alpha=Math.acos(cosA);
        const chest=(bones.Spine2 || bones.Spine1 || bones.Hips)?.getWorldPosition(new THREE.Vector3()) || posA.clone();
        const poleDir=chest.sub(posA).add(new THREE.Vector3(0,-0.4,0)).normalize();
        if (elbowPoleAngleDeg) poleDir.applyAxisAngle(targetDir,THREE.MathUtils.degToRad(elbowPoleAngleDeg));
        let planeNormal=new THREE.Vector3().crossVectors(targetDir,poleDir).normalize();
        if (planeNormal.lengthSq()<1e-8) planeNormal=new THREE.Vector3(1,0,0);
        const elbowDir=targetDir.clone().applyAxisAngle(planeNormal,alpha).normalize();
        const elbowTarget=posA.clone().add(elbowDir.multiplyScalar(L1));
        const upperTargetDir=elbowTarget.clone().sub(posA).normalize();
        const lowerTargetDir=reachableWrist.clone().sub(elbowTarget).normalize();
        const solvedUpperWorld=new THREE.Quaternion().setFromUnitVectors(fkUpperAxis,upperTargetDir).multiply(fkUpperWorld);

        const parentUpperQ=upper.parent?.getWorldQuaternion(new THREE.Quaternion()) || new THREE.Quaternion();
        upper.quaternion.copy(fkUpperLocal).slerp(parentUpperQ.invert().multiply(solvedUpperWorld),ikWeight);
        root.updateWorldMatrix(true,true);

        const parentLowerQ=lower.parent?.getWorldQuaternion(new THREE.Quaternion()) || new THREE.Quaternion();
        const solvedLowerWorld=new THREE.Quaternion().setFromUnitVectors(fkLowerAxis,lowerTargetDir).multiply(fkLowerWorld);
        lower.quaternion.copy(fkLowerLocal).slerp(parentLowerQ.invert().multiply(solvedLowerWorld),ikWeight);
        root.updateWorldMatrix(true,true);

        if (ikHandWorld) {
          const parentHandQ=hand.parent?.getWorldQuaternion(new THREE.Quaternion()) || new THREE.Quaternion();
          hand.quaternion.copy(fkHandLocal).slerp(parentHandQ.invert().multiply(ikHandWorld),ikWeight);
          root.updateWorldMatrix(true,true);
        }
      }
    }

    if (groundFeet && bones.Hips) {
      root.updateWorldMatrix(true,true);
      let minY=Infinity;
      for (const key of ['LeftFoot','RightFoot','LeftToeBase','RightToeBase']) {
        const bone=bones[key];
        if (bone) minY=Math.min(minY,bone.getWorldPosition(new THREE.Vector3()).y);
      }
      if (Number.isFinite(minY)) {
        const hipWorld=bones.Hips.getWorldPosition(new THREE.Vector3()); hipWorld.y-=minY;
        if (charRigMap.hipsParentWorldMatrixInv) bones.Hips.position.copy(hipWorld).applyMatrix4(charRigMap.hipsParentWorldMatrixInv);
        else bones.Hips.position.y-=minY;
        root.updateWorldMatrix(true,true);
      }
    }
    return true;
  }

  function unwrapAngleDeg(current, previous) {
    let diff = current - previous;
    while (diff > 180) { current -= 360; diff -= 360; }
    while (diff < -180) { current += 360; diff += 360; }
    return current;
  }

  /**
   * 5. bakeClipToFBXTracks(charRigMap, retargetCtx, params, weaponContext, fbxBoneMetaMap)
   */
  function bakeClipToFBXTracks(charRigMap, retargetCtx, params = {}, weaponContext = null, fbxBoneMetaMap = {}, optionalTHREE) {
    const THREE = getTHREE(optionalTHREE);
    if (!charRigMap || !retargetCtx) throw new Error("bakeClipToFBXTracks: charRigMap and retargetCtx required");

    const fps = params.bakeFps || 30;
    const duration = retargetCtx.duration || 1.0;
    const frameCount = Math.max(2, Math.ceil(duration * fps) + 1);
    const times = new Float32Array(frameCount);

    for (let i = 0; i < frameCount; i++) {
      times[i] = duration * i / (frameCount - 1);
    }

    const tracks = {};
    const tracksList = [];

    // Initialize track arrays for each canonical bone
    for (const [canonical, bone] of Object.entries(charRigMap.bones)) {
      const origName = charRigMap.canonicalToOriginalName[canonical] || bone.userData?.originalName || bone.name;
      const meta = fbxBoneMetaMap[origName] || fbxBoneMetaMap[canonical] || {};
      const nodeId = meta.nodeId !== undefined ? meta.nodeId : (meta.id !== undefined ? meta.id : (bone.ID !== undefined ? bone.ID : null));

      const trackObj = {
        canonicalName: canonical,
        boneName: origName,
        nodeId,
        times: times,
        rotation: {
          x: new Float32Array(frameCount),
          y: new Float32Array(frameCount),
          z: new Float32Array(frameCount)
        },
        position: {
          x: new Float32Array(frameCount),
          y: new Float32Array(frameCount),
          z: new Float32Array(frameCount)
        }
      };

      tracks[canonical] = trackObj;
      tracksList.push(trackObj);
    }

    const prevRot = {};
    const euler = new THREE.Euler(0, 0, 0, 'ZYX');

    // Evaluation mutates preview transforms; always restore the user's current pose.
    const savedTransforms = Object.values(charRigMap.bones).map(bone => [bone, bone.position.clone(), bone.quaternion.clone()]);
    try {
    // Evaluate each frame and record tracks
    for (let f = 0; f < frameCount; f++) {
      const t = times[f];
      evaluateRetargetFrame(charRigMap, retargetCtx, t, params, weaponContext, THREE);

      for (const [canonical, bone] of Object.entries(charRigMap.bones)) {
        const track = tracks[canonical];
        const origName = track.boneName;
        const meta = fbxBoneMetaMap[origName] || fbxBoneMetaMap[canonical] || {};
        const td = bone.userData?.transformData || {};

        // 1. Position
        track.position.x[f] = bone.position.x;
        track.position.y[f] = bone.position.y;
        track.position.z[f] = bone.position.z;

        // 2. Rotation with FBX PreRotation and PostRotation discounted:
        // In Three.js FBXLoader: Tf(0) = 'ZYX', and q_local = q_pre * q_euler * q_post^-1
        // Therefore: q_euler = (q_pre)^-1 * q_local * q_post
        let qLocal = bone.quaternion.clone();

        const preRot = meta.preRotation || td.preRotation;
        let qPreInv = new THREE.Quaternion();
        if (preRot && Array.isArray(preRot)) {
          const preEul = new THREE.Euler(
            THREE.MathUtils.degToRad(preRot[0] || 0),
            THREE.MathUtils.degToRad(preRot[1] || 0),
            THREE.MathUtils.degToRad(preRot[2] || 0),
            'ZYX'
          );
          qPreInv.setFromEuler(preEul).invert();
        }

        const postRot = meta.postRotation || td.postRotation;
        let qPost = new THREE.Quaternion();
        if (postRot && Array.isArray(postRot)) {
          const postEul = new THREE.Euler(
            THREE.MathUtils.degToRad(postRot[0] || 0),
            THREE.MathUtils.degToRad(postRot[1] || 0),
            THREE.MathUtils.degToRad(postRot[2] || 0),
            'ZYX'
          );
          qPost.setFromEuler(postEul);
        }

        const eulerOrder = meta.eulerOrder || td.eulerOrder || 'ZYX';
        const qFbx = qPreInv.clone().multiply(qLocal).multiply(qPost);
        euler.setFromQuaternion(qFbx, eulerOrder);

        let rx = THREE.MathUtils.radToDeg(euler.x);
        let ry = THREE.MathUtils.radToDeg(euler.y);
        let rz = THREE.MathUtils.radToDeg(euler.z);

        // Continuous Euler Unwrapping
        if (f > 0 && prevRot[canonical]) {
          rx = unwrapAngleDeg(rx, prevRot[canonical].x);
          ry = unwrapAngleDeg(ry, prevRot[canonical].y);
          rz = unwrapAngleDeg(rz, prevRot[canonical].z);
        }

        prevRot[canonical] = { x: rx, y: ry, z: rz };

        track.rotation.x[f] = rx;
        track.rotation.y[f] = ry;
        track.rotation.z[f] = rz;
      }
    }
    } finally {
      for (const [bone,position,quaternion] of savedTransforms) {
        bone.position.copy(position);
        bone.quaternion.copy(quaternion);
      }
      charRigMap.rootObject.updateWorldMatrix(true,true);
    }

    // Build splicerTracks array ready for FBXBinarySplicer.spliceAndExportFBX
    const splicerTracks = [];
    for (const track of tracksList) {
      if (track.nodeId === null || track.nodeId === undefined) continue;
      const R = new Array(frameCount);
      for (let f = 0; f < frameCount; f++) {
        R[f] = [track.rotation.x[f], track.rotation.y[f], track.rotation.z[f]];
      }
      const entry = { modelId: track.nodeId, R };
      if (track.canonicalName === 'Hips') {
        const T = new Array(frameCount);
        for (let f = 0; f < frameCount; f++) {
          T[f] = [track.position.x[f], track.position.y[f], track.position.z[f]];
        }
        entry.T = T;
      }
      splicerTracks.push(entry);
    }

    return {
      name: retargetCtx.animClip?.name || 'baked_animation',
      duration,
      fps,
      frameCount,
      times,
      tracks,
      tracksList,
      splicerTracks
    };
  }

  // =========================================================================
  // EXPORT ENGINE
  // =========================================================================

  const api = {
    CANONICAL_BONES,
    normalizeCanonicalBoneName,
    extractAnimationClip,
    setTHREE: function (t) { _THREE = t; },
    mapHumanoidSkeleton,
    autoAlignWeaponGeometry,
    prepareAnimationRetarget,
    evaluateRetargetFrame,
    bakeClipToFBXTracks
  };

  // Allow invoking as factory: RetargetAndIKEngine(THREE)
  function EngineFactory(optionalTHREE) {
    if (optionalTHREE) {
      _THREE = optionalTHREE;
    }
    return api;
  }
  Object.assign(EngineFactory, api);

  return EngineFactory;
}));
