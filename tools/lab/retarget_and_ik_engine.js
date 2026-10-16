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
        if (fingerRegex.test(lower)) {
          for (let j = 1; j <= 3; j++) {
            if (lower.includes(String(j)) || lower.includes(`0${j}`)) {
              return `${side}${f}${j}`;
            }
          }
          if (/distal/i.test(lower)) return `${side}${f}3`;
          if (/intermediate|middle/i.test(lower)) return `${side}${f}2`;
          if (/proximal/i.test(lower)) return `${side}${f}1`;
        }
      }
    }

    return null;
  }

  /**
   * 1. mapHumanoidSkeleton(rootObject, optionalTHREE)
   */
  function mapHumanoidSkeleton(rootObject, optionalTHREE) {
    const THREE = getTHREE(optionalTHREE);
    if (!rootObject) throw new Error("mapHumanoidSkeleton: rootObject is required");

    rootObject.updateWorldMatrix(true, true);

    const bones = {};
    const boneToCanonical = {};
    const canonicalToOriginalName = {};

    rootObject.traverse(node => {
      if (node.isBone || node.type === 'Bone') {
        const canonical = normalizeCanonicalBoneName(node.name);
        if (canonical && !bones[canonical]) {
          bones[canonical] = node;
          boneToCanonical[node.uuid] = canonical;
          boneToCanonical[node.name] = canonical;
          canonicalToOriginalName[canonical] = node.name;
        }
      }
    });

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

    if (options.roll90) {
      const angle = THREE.MathUtils.degToRad(options.roll90 * 90);
      axisUp.applyAxisAngle(axisBarrel, angle).normalize();
      axisRight.crossVectors(axisBarrel, axisUp).normalize();
    }

    // Account for any world scale on RightHand bone
    let handWorldScale = 1.0;
    if (charRigMap.restWorldMatrix && charRigMap.restWorldMatrix.RightHand) {
      const ws = new THREE.Vector3().setFromMatrixScale(charRigMap.restWorldMatrix.RightHand);
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

    // Construct localMatrix4 in RightHand space
    const handVecs = charRigMap.rightHandVectors || {
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

      targetBarrel = baseFwd.clone()
        .applyAxisAngle(baseRight, THREE.MathUtils.degToRad(-12))
        .applyAxisAngle(baseUp, THREE.MathUtils.degToRad(14))
        .normalize();
      targetUp = baseUp.clone();
      targetRight = new THREE.Vector3().crossVectors(targetBarrel, targetUp).normalize();
      targetUp.crossVectors(targetRight, targetBarrel).normalize();
    }

    // Source basis in weapon space
    const srcRight = axisRight.clone().normalize();
    const srcBarrel = axisBarrel.clone().normalize();
    const srcUp = axisUp.clone().normalize();

    // Rotation matrix: R = M_target * M_source^T
    const mSrc = new THREE.Matrix4().makeBasis(srcRight, srcBarrel, srcUp);
    const mDst = new THREE.Matrix4().makeBasis(targetRight, targetBarrel, targetUp);
    const rotMat = new THREE.Matrix4().multiplyMatrices(mDst, mSrc.clone().invert());

    const rotQuat = new THREE.Quaternion().setFromRotationMatrix(rotMat);

    // Apply manual rotation offset (Euler degrees)
    if (options.offsetRotDeg && Array.isArray(options.offsetRotDeg)) {
      const eul = new THREE.Euler(
        THREE.MathUtils.degToRad(options.offsetRotDeg[0] || 0),
        THREE.MathUtils.degToRad(options.offsetRotDeg[1] || 0),
        THREE.MathUtils.degToRad(options.offsetRotDeg[2] || 0),
        'XYZ'
      );
      rotQuat.multiply(new THREE.Quaternion().setFromEuler(eul));
    }

    // Hand grip center in hand local space
    const handBone = charRigMap.bones.RightHand;
    const midKnuckle = charRigMap.bones.RightHandMiddle1;
    let handGripCenterLocal;

    if (midKnuckle && handBone) {
      // Wrist to middle knuckle center, displaced slightly into the palm
      const wristLocal = new THREE.Vector3(0, 0, 0);
      const midPosInHand = midKnuckle.position.clone();
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
      autoDetectedAxes: {
        axisBarrel: axisBarrel.toArray(),
        axisUp: axisUp.toArray(),
        axisRight: axisRight.toArray(),
        muzzleAtPositive
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
    if (!charRigMap) throw new Error("prepareAnimationRetarget: charRigMap required");
    if (!animClipData) throw new Error("prepareAnimationRetarget: animClipData required");

    const tracks = animClipData.tracks || [];
    const duration = animClipData.duration || 1.0;
    const sourceTracksByCanonical = {};

    tracks.forEach(track => {
      let rawBoneName = '';
      let prop = '';
      if (track.name) {
        const dotIdx = track.name.indexOf('.');
        rawBoneName = dotIdx !== -1 ? track.name.slice(0, dotIdx) : track.name;
        prop = dotIdx !== -1 ? track.name.slice(dotIdx + 1) : '';
      } else if (track.bone) {
        rawBoneName = track.bone;
        prop = track.type || 'quaternion';
      }
      const canonical = normalizeCanonicalBoneName(rawBoneName);
      if (canonical) {
        if (!sourceTracksByCanonical[canonical]) sourceTracksByCanonical[canonical] = {};
        const isQuat = prop.startsWith('quaternion') || prop.startsWith('rotation');
        const stride = isQuat ? 4 : 3;
        let normalizedTrack = track;
        if (!track.times && Array.isArray(track.values)) {
          const count = Math.floor(track.values.length / stride);
          if (count <= 1) {
            normalizedTrack = {
              times: new Float32Array([0, duration]),
              values: new Float32Array([...track.values.slice(0, stride), ...track.values.slice(0, stride)])
            };
          } else {
            const times = new Float32Array(count);
            for (let i = 0; i < count; i++) times[i] = (i / (count - 1)) * duration;
            normalizedTrack = { times, values: new Float32Array(track.values) };
          }
        }
        if (isQuat) {
          sourceTracksByCanonical[canonical].quaternion = normalizedTrack;
        } else if (prop.startsWith('position')) {
          sourceTracksByCanonical[canonical].position = normalizedTrack;
        }
      }
    });

    // Sample source rest pose (prefer explicit boneRestPose if provided, else t = 0)
    const restSourceWorldQuat = {};
    const sourceLocalQuat = {};
    const sourceLocalPos = {};

    if (animClipData.boneRestPose) {
      for (const [rawKey, qArr] of Object.entries(animClipData.boneRestPose)) {
        const canonical = normalizeCanonicalBoneName(rawKey) || rawKey;
        if (Array.isArray(qArr) && qArr.length === 4) {
          sourceLocalQuat[canonical] = new THREE.Quaternion(qArr[0], qArr[1], qArr[2], qArr[3]);
        }
      }
    }

    for (const [canonical, tr] of Object.entries(sourceTracksByCanonical)) {
      if (tr.quaternion && !sourceLocalQuat[canonical]) {
        sourceLocalQuat[canonical] = sampleTrack(tr.quaternion.times, tr.quaternion.values, 4, 0, true, THREE);
      }
      if (tr.position) {
        sourceLocalPos[canonical] = sampleTrack(tr.position.times, tr.position.values, 3, 0, false, THREE);
      }
    }

    // Hierarchical world rotation accumulator for source rest pose
    const sourceParentMap = {
      Spine: 'Hips',
      Spine1: 'Spine',
      Spine2: 'Spine1',
      Neck: 'Spine2',
      Head: 'Neck',
      LeftShoulder: 'Spine2',
      LeftArm: 'LeftShoulder',
      LeftForeArm: 'LeftArm',
      LeftHand: 'LeftForeArm',
      RightShoulder: 'Spine2',
      RightArm: 'RightShoulder',
      RightForeArm: 'RightArm',
      RightHand: 'RightForeArm',
      LeftUpLeg: 'Hips',
      LeftLeg: 'LeftUpLeg',
      LeftFoot: 'LeftLeg',
      LeftToeBase: 'LeftFoot',
      RightUpLeg: 'Hips',
      RightLeg: 'RightUpLeg',
      RightFoot: 'RightLeg',
      RightToeBase: 'RightFoot'
    };

    function computeSourceWorldQuat(canonical) {
      if (restSourceWorldQuat[canonical]) return restSourceWorldQuat[canonical];
      const localQ = sourceLocalQuat[canonical] || new THREE.Quaternion();
      const parent = sourceParentMap[canonical];
      if (parent && (sourceLocalQuat[parent] || sourceTracksByCanonical[parent])) {
        const parentWorldQ = computeSourceWorldQuat(parent);
        const wq = parentWorldQ.clone().multiply(localQ);
        restSourceWorldQuat[canonical] = wq;
        return wq;
      }
      restSourceWorldQuat[canonical] = localQ.clone();
      return restSourceWorldQuat[canonical];
    }

    for (const canonical of Object.keys({ ...sourceLocalQuat, ...sourceTracksByCanonical })) {
      computeSourceWorldQuat(canonical);
    }

    // Source Hips Rest Height
    let sourceHipsRestPos = sourceLocalPos.Hips || new THREE.Vector3(0, 1, 0);
    if (animClipData.hipsRestPosition && Array.isArray(animClipData.hipsRestPosition)) {
      sourceHipsRestPos = new THREE.Vector3(
        animClipData.hipsRestPosition[0],
        animClipData.hipsRestPosition[1],
        animClipData.hipsRestPosition[2]
      );
    }
    const sourceHipsRestY = Math.max(0.01, Math.abs(sourceHipsRestPos.y));
    const hipsScaleRatio = charRigMap.hipsRestY / sourceHipsRestY;

    // Alignment quaternions for limb bones (exact equivalent of Blender dir_m.rotation_difference(dir_s))
    const alignQuat = {};
    const childMap = {
      LeftShoulder: 'LeftArm',
      LeftArm: 'LeftForeArm',
      LeftForeArm: 'LeftHand',
      RightShoulder: 'RightArm',
      RightArm: 'RightForeArm',
      RightForeArm: 'RightHand',
      LeftUpLeg: 'LeftLeg',
      LeftLeg: 'LeftFoot',
      RightUpLeg: 'RightLeg',
      RightLeg: 'RightFoot'
    };

    for (const [canonical, bone] of Object.entries(charRigMap.bones)) {
      if (LIMB_KEYWORDS.some(k => canonical.includes(k)) && sourceTracksByCanonical[canonical]) {
        const childKey = childMap[canonical];
        let dirDest = null;
        let dirSrc = null;

        if (childKey && charRigMap.restWorldPos[childKey] && charRigMap.restWorldPos[canonical]) {
          dirDest = charRigMap.restWorldPos[childKey].clone()
            .sub(charRigMap.restWorldPos[canonical]).normalize();
        } else {
          // Primary axis
          dirDest = new THREE.Vector3(0, 1, 0).applyQuaternion(charRigMap.restWorldQuat[canonical]).normalize();
        }

        const srcWorldQ = restSourceWorldQuat[canonical];
        if (srcWorldQ) {
          dirSrc = new THREE.Vector3(0, 1, 0).applyQuaternion(srcWorldQ).normalize();
          alignQuat[canonical] = new THREE.Quaternion().setFromUnitVectors(dirDest, dirSrc);
        } else {
          alignQuat[canonical] = new THREE.Quaternion();
        }
      } else {
        alignQuat[canonical] = new THREE.Quaternion();
      }
    }

    return {
      animClip: animClipData,
      duration,
      sourceTracksByCanonical,
      sourceLocalQuat,
      restSourceWorldQuat,
      alignQuat,
      sourceHipsRestPos,
      sourceHipsRestY,
      hipsScaleRatio
    };
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

    const inPlaceLock = params.inPlaceLock !== undefined ? params.inPlaceLock : 1.0;
    const groundFeet = params.groundFeet !== undefined ? params.groundFeet : true;
    const armSpreadDeg = params.armSpreadDeg || 0;
    const spineTwistDeg = params.spineTwistDeg || 0;
    const spinePitchDeg = params.spinePitchDeg || 0;
    const leftHandIkWeight = params.leftHandIkWeight !== undefined ? params.leftHandIkWeight : (weaponContext ? 1.0 : 0.0);
    const elbowPoleAngleDeg = params.elbowPoleAngleDeg || 0;
    const rightHandGrip = params.rightHandGrip !== undefined ? params.rightHandGrip : (weaponContext ? 1.0 : 0.0);
    const leftHandGrip = params.leftHandGrip !== undefined ? params.leftHandGrip : (weaponContext ? 1.0 : 0.0);

    const bones = charRigMap.bones;
    const tracks = retargetCtx.sourceTracksByCanonical;

    // 1. Hips Translation (computed in Y-up World Space, then transformed into Hips.parent local space)
    const hipsTrack = tracks.Hips ? tracks.Hips.position : null;
    if (hipsTrack && bones.Hips && charRigMap.restWorldPos.Hips) {
      const curHipsPos = sampleTrack(hipsTrack.times, hipsTrack.values, 3, timeSec, false, THREE);
      const deltaWorld = curHipsPos.clone().sub(retargetCtx.sourceHipsRestPos).multiplyScalar(retargetCtx.hipsScaleRatio);

      // In-place lock on horizontal plane X/Z
      deltaWorld.x *= (1.0 - inPlaceLock);
      deltaWorld.z *= (1.0 - inPlaceLock);

      const targetHipsWorld = charRigMap.restWorldPos.Hips.clone().add(deltaWorld);
      if (charRigMap.hipsParentWorldMatrixInv) {
        bones.Hips.position.copy(targetHipsWorld).applyMatrix4(charRigMap.hipsParentWorldMatrixInv);
      } else {
        bones.Hips.position.copy(charRigMap.restLocalPos.Hips).add(deltaWorld);
      }
    }

    // 2. FK World-Delta Rotations
    const boneOrder = [
      'Hips',
      'Spine', 'Spine1', 'Spine2', 'Neck', 'Head',
      'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand',
      'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand',
      'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase',
      'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase'
    ];

    const currentSourceWorldQuat = {};
    const currentTargetWorldQuat = {};

    for (const bname of boneOrder) {
      const bone = bones[bname];
      if (!bone) continue;

      const parentKey = bone.parent ? charRigMap.boneToCanonical[bone.parent.uuid] : null;
      const trackObj = tracks[bname];
      if (trackObj && trackObj.quaternion && retargetCtx.restSourceWorldQuat[bname]) {
        const curSourceLocalQ = sampleTrack(trackObj.quaternion.times, trackObj.quaternion.values, 4, timeSec, true, THREE);
        let curSourceWorldQ;
        if (parentKey && currentSourceWorldQuat[parentKey]) {
          curSourceWorldQ = currentSourceWorldQuat[parentKey].clone().multiply(curSourceLocalQ);
        } else {
          curSourceWorldQ = curSourceLocalQ.clone();
        }
        currentSourceWorldQuat[bname] = curSourceWorldQ;

        // q_world_delta = q_S_cur * (q_S_rest)^-1
        const worldDelta = curSourceWorldQ.clone().multiply(retargetCtx.restSourceWorldQuat[bname].clone().invert());

        // q_M_target_world = worldDelta * alignQuat * q_M_rest_world
        const alignQ = retargetCtx.alignQuat[bname] || new THREE.Quaternion();
        const targetWorldQ = worldDelta.clone().multiply(alignQ).multiply(charRigMap.restWorldQuat[bname]);
        currentTargetWorldQuat[bname] = targetWorldQ;

        // Convert target world rotation to local rotation
        if (parentKey && currentTargetWorldQuat[parentKey]) {
          const parentWorldInv = currentTargetWorldQuat[parentKey].clone().invert();
          bone.quaternion.copy(parentWorldInv.multiply(targetWorldQ));
        } else if (charRigMap.hipsParentWorldQuatInv) {
          bone.quaternion.copy(charRigMap.hipsParentWorldQuatInv.clone().multiply(targetWorldQ));
        } else {
          bone.quaternion.copy(targetWorldQ);
        }
      } else {
        // Keep rest local rotation if not in track
        bone.quaternion.copy(charRigMap.restLocalQuat[bname] || bone.quaternion);
        const restSrcLocal = (retargetCtx.sourceLocalQuat && retargetCtx.sourceLocalQuat[bname]) || new THREE.Quaternion();
        if (parentKey && currentSourceWorldQuat[parentKey]) {
          currentSourceWorldQuat[bname] = currentSourceWorldQuat[parentKey].clone().multiply(restSrcLocal);
        } else {
          currentSourceWorldQuat[bname] = restSrcLocal.clone();
        }
        if (parentKey && currentTargetWorldQuat[parentKey]) {
          currentTargetWorldQuat[bname] = currentTargetWorldQuat[parentKey].clone().multiply(bone.quaternion);
        } else if (charRigMap.restWorldQuat[bname]) {
          currentTargetWorldQuat[bname] = charRigMap.restWorldQuat[bname].clone();
        } else {
          currentTargetWorldQuat[bname] = bone.quaternion.clone();
        }
      }
    }

    // 3. Postural Offsets
    if (spineTwistDeg !== 0) {
      const halfRad = THREE.MathUtils.degToRad(spineTwistDeg * 0.5);
      const twistQ = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), halfRad);
      if (bones.Spine1) bones.Spine1.quaternion.multiply(twistQ);
      if (bones.Spine2) bones.Spine2.quaternion.multiply(twistQ);
    }

    if (spinePitchDeg !== 0) {
      const halfRad = THREE.MathUtils.degToRad(spinePitchDeg * 0.5);
      const pitchQ = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), halfRad);
      if (bones.Spine1) bones.Spine1.quaternion.multiply(pitchQ);
      if (bones.Spine2) bones.Spine2.quaternion.multiply(pitchQ);
    }

    if (armSpreadDeg !== 0) {
      const rad = THREE.MathUtils.degToRad(armSpreadDeg);
      const spreadLeft = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), rad);
      const spreadRight = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, -1), rad);
      if (bones.LeftArm) bones.LeftArm.quaternion.multiply(spreadLeft);
      if (bones.RightArm) bones.RightArm.quaternion.multiply(spreadRight);
    }

    // Update matrices after postural offsets
    charRigMap.rootObject.updateWorldMatrix(true, true);

    // 4. Procedural Finger Grips
    function applyFingerGrip(sidePrefix, gripWeight) {
      if (gripWeight <= 0) return;
      const vecs = sidePrefix === 'RightHand' ? charRigMap.rightHandVectors : charRigMap.leftHandVectors;
      if (!vecs) return;

      FINGER_NAMES.forEach(finger => {
        let maxDeg = 40.0;
        if (sidePrefix === 'RightHand') {
          if (finger === 'Thumb') maxDeg = 45.0;
          else if (finger === 'Index') maxDeg = 35.0; // trigger finger
          else maxDeg = 80.0; // middle, ring, pinky closed tight
        } else {
          maxDeg = finger === 'Thumb' ? 30.0 : 40.0;
        }

        for (let j = 1; j <= 3; j++) {
          const bname = `${sidePrefix}${finger}${j}`;
          const fbone = bones[bname];
          if (!fbone) continue;

          // Hinge axis rotation in local finger bone space
          const restWorldQ = charRigMap.restWorldQuat[bname] || fbone.quaternion;
          let axisWorld = vecs.hingeAxisWorld.clone();
          if (finger === 'Thumb') {
            axisWorld = (vecs.palmInWorld.clone().sub(vecs.handFwdWorld.clone().multiplyScalar(0.4))).normalize();
          }
          const axisLocal = axisWorld.applyQuaternion(restWorldQ.clone().invert()).normalize();

          const fraction = j === 1 ? 0.9 : (j === 2 ? 0.9 : 0.7);
          const angleRad = THREE.MathUtils.degToRad(maxDeg * fraction * gripWeight);
          const curlQ = new THREE.Quaternion().setFromAxisAngle(axisLocal, angleRad);

          const restLocal = charRigMap.restLocalQuat[bname] || new THREE.Quaternion();
          fbone.quaternion.copy(restLocal).multiply(curlQ);
        }
      });
    }

    applyFingerGrip('RightHand', rightHandGrip);
    applyFingerGrip('LeftHand', leftHandGrip);

    charRigMap.rootObject.updateWorldMatrix(true, true);

    // 5. Analytical 2-Bone IK Solver for Left Arm
    if (leftHandIkWeight > 0 && weaponContext && weaponContext.localMatrix4 && weaponContext.foregripLocalPos && bones.LeftArm && bones.LeftForeArm && bones.LeftHand) {
      // Calculate foregrip world position from right hand and weapon local matrix
      const rightHandWorldMatrix = bones.RightHand.matrixWorld;
      const weaponWorldMat = rightHandWorldMatrix.clone().multiply(weaponContext.localMatrix4);
      const foregripWorldPos = weaponContext.foregripLocalPos.clone().applyMatrix4(weaponWorldMat);

      // Current positions
      const posA = bones.LeftArm.getWorldPosition(new THREE.Vector3());
      const posB = bones.LeftForeArm.getWorldPosition(new THREE.Vector3());
      const posC = bones.LeftHand.getWorldPosition(new THREE.Vector3());

      const L1 = charRigMap.restWorldPos.LeftForeArm
        ? charRigMap.restWorldPos.LeftForeArm.distanceTo(charRigMap.restWorldPos.LeftArm)
        : posB.distanceTo(posA);
      const L2 = charRigMap.restWorldPos.LeftHand
        ? charRigMap.restWorldPos.LeftHand.distanceTo(charRigMap.restWorldPos.LeftForeArm)
        : posC.distanceTo(posB);

      const targetVec = foregripWorldPos.clone().sub(posA);
      const dist = Math.min(Math.max(0.01, targetVec.length()), (L1 + L2) * 0.999);
      const targetDir = targetVec.clone().normalize();

      // Law of Cosines
      const cosAlpha = THREE.MathUtils.clamp((L1 * L1 + dist * dist - L2 * L2) / (2 * L1 * dist), -1, 1);
      const alpha = Math.acos(cosAlpha);

      // Elbow pole vector (down and back)
      let poleDir = new THREE.Vector3(0, -1, -0.4).normalize();
      if (elbowPoleAngleDeg !== 0) {
        poleDir.applyAxisAngle(targetDir, THREE.MathUtils.degToRad(elbowPoleAngleDeg));
      }

      // Normal to IK plane
      let planeNormal = new THREE.Vector3().crossVectors(targetDir, poleDir).normalize();
      if (planeNormal.lengthSq() < 1e-4) {
        planeNormal = new THREE.Vector3(1, 0, 0);
      }

      // Upper arm direction
      const upperArmDir = targetDir.clone().applyAxisAngle(planeNormal, alpha).normalize();
      const elbowTargetPos = posA.clone().add(upperArmDir.clone().multiplyScalar(L1));
      const foreArmDir = foregripWorldPos.clone().sub(elbowTargetPos).normalize();

      // Parent inverses for local orientation
      const shoulderWorldQuatInv = (bones.LeftShoulder ? bones.LeftShoulder.getWorldQuaternion(new THREE.Quaternion()) : new THREE.Quaternion()).invert();

      // Desired world quaternion of LeftArm: rotate longitudinal axis to upperArmDir
      const restArmDir = new THREE.Vector3(0, 1, 0).applyQuaternion(charRigMap.restWorldQuat.LeftArm).normalize();
      const rotArmDelta = new THREE.Quaternion().setFromUnitVectors(restArmDir, upperArmDir);
      const ikArmWorldQ = rotArmDelta.multiply(charRigMap.restWorldQuat.LeftArm);
      const ikArmLocalQ = shoulderWorldQuatInv.clone().multiply(ikArmWorldQ);

      // Desired world quaternion of LeftForeArm: rotate longitudinal axis to foreArmDir
      const restForeArmDir = new THREE.Vector3(0, 1, 0).applyQuaternion(charRigMap.restWorldQuat.LeftForeArm).normalize();
      const rotForeArmDelta = new THREE.Quaternion().setFromUnitVectors(restForeArmDir, foreArmDir);
      const ikForeArmWorldQ = rotForeArmDelta.multiply(charRigMap.restWorldQuat.LeftForeArm);
      const ikForeArmLocalQ = ikArmWorldQ.clone().invert().multiply(ikForeArmWorldQ);

      // Slerp FK with IK
      bones.LeftArm.quaternion.slerp(ikArmLocalQ, leftHandIkWeight);
      bones.LeftForeArm.quaternion.slerp(ikForeArmLocalQ, leftHandIkWeight);

      charRigMap.rootObject.updateWorldMatrix(true, true);
    }

    // 6. Foot Auto-Grounding (plant lowest foot/toe on Y = 0)
    if (groundFeet && bones.Hips) {
      charRigMap.rootObject.updateWorldMatrix(true, true);
      const footKeys = ['LeftFoot', 'RightFoot', 'LeftToeBase', 'RightToeBase'];
      let minFootY = Infinity;
      const v = new THREE.Vector3();

      footKeys.forEach(k => {
        if (bones[k]) {
          bones[k].getWorldPosition(v);
          if (v.y < minFootY) minFootY = v.y;
        }
      });

      if (isFinite(minFootY)) {
        const curHipsWorld = new THREE.Vector3();
        bones.Hips.getWorldPosition(curHipsWorld);
        curHipsWorld.y -= minFootY;
        if (charRigMap.hipsParentWorldMatrixInv) {
          bones.Hips.position.copy(curHipsWorld).applyMatrix4(charRigMap.hipsParentWorldMatrixInv);
        } else {
          bones.Hips.position.y -= minFootY;
        }
        charRigMap.rootObject.updateWorldMatrix(true, true);
      }
    }

    return true;
  }

  // =========================================================================
  // 5. FBX TRACK BAKER & CONTINUOUS EULER UNWRAPPING
  // =========================================================================

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
    const frameCount = Math.max(2, Math.floor(duration * fps) + 1);
    const times = new Float32Array(frameCount);

    for (let i = 0; i < frameCount; i++) {
      times[i] = Math.min(duration, i / fps);
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
