// Character loading and posing for the fast exporter (no browser).
// Uses the exact Three r186 + FBXLoader shipped in FBX-Web-Renderer-offline.html, evaluated in Node,
// and replicates the parity layer (FBX-Web-Renderer-parity.js): Lf normalization, applyInPlaceMotion,
// neck pitch hooks on AnimationMixer, posed points, material conversion and lighting presets.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { resolveObjectURL } = require('node:buffer');
const { decodePng } = require('./png.cjs');

const HTML = path.join(__dirname, '..', 'FBX-Web-Renderer-offline.html');

// Raised when a request needs the slow browser exporter (GLB sequences, JPEG textures, unsupported flags).
class DelegateError extends Error {
  constructor(reason) { super(reason); this.name = 'DelegateError'; }
}

const ENV = { pending: [], jpegSeen: null, decoder: null, byUrl: new Map() };

// Image stub: the FBX loader assigns blob URLs; we decode the embedded bytes ourselves (PNG only).
function makeImage() {
  const handlers = {};
  const img = {
    width: 1, height: 1, crossOrigin: '', decoded: null, _src: '',
    addEventListener(t, fn) { handlers[t] = fn; },
    removeEventListener() {},
    get src() { return this._src; },
    set src(url) {
      this._src = url;
      const sync = typeof url === 'string' ? ENV.byUrl.get(url) : null;
      if (sync && sync[0] === 0x89 && sync[1] === 0x50) {
        // PNG bytes are known now; decoded after the parse, only for the textures the materials use
        img._syncBytes = sync;
      } else if (typeof url === 'string' && url.startsWith('blob:') ? resolveObjectURL(url) : null) {
        const blob = resolveObjectURL(url);
        ENV.pending.push(blob.arrayBuffer().then(ab => decodeAsync(img, new Uint8Array(ab))));
      } else if (typeof url === 'string' && url.startsWith('data:')) {
        const b64 = url.slice(url.indexOf(',') + 1);
        ENV.pending.push(Promise.resolve().then(() => decodeInto(img, Buffer.from(b64, 'base64'))));
      }
      if (handlers.load) handlers.load.call(img);
      if (typeof img.onload === 'function') img.onload();
    },
  };
  return img;
}

// PNG bytes go to ENV.decoder when set (worker threads, in parallel); other formats are only flagged.
async function decodeAsync(img, bytes) {
  if (bytes[0] === 0x89 && bytes[1] === 0x50 && ENV.decoder) {
    const d = await ENV.decoder(bytes);
    img.width = d.width; img.height = d.height; img.decoded = d;
    return;
  }
  decodeInto(img, Buffer.from(bytes.buffer, bytes.byteOffset, bytes.byteLength));
}

function decodeInto(img, bytes) {
  if (bytes[0] === 0x89 && bytes[1] === 0x50) {
    const p = decodePng(bytes);
    img.width = p.width; img.height = p.height; img.decoded = p;
  } else {
    img.decoded = null;
    img.jpeg = bytes[0] === 0xff && bytes[1] === 0xd8;
    ENV.jpegSeen = ENV.jpegSeen || (img.jpeg ? 'jpeg' : 'unknown');
  }
}

let BUNDLE = null;
let BUNDLE_CTX = null;

// Blob/URL seen by the bundle: keep the bytes of every object URL so PNG textures can be decoded at once.
class SpyBlob extends Blob {
  constructor(parts, opts) { super(parts, opts); this.__first = parts && parts[0]; }
}
const SpyURL = class extends URL {};
SpyURL.createObjectURL = (blob) => {
  const u = URL.createObjectURL(blob);
  const first = blob && blob.__first;
  if (first) ENV.byUrl.set(u, first instanceof Uint8Array ? first : new Uint8Array(first));
  return u;
};
SpyURL.revokeObjectURL = (u) => { ENV.byUrl.delete(u); URL.revokeObjectURL(u); };
function loadBundle() {
  if (BUNDLE) return BUNDLE;
  const html = fs.readFileSync(HTML, 'utf8');
  const script = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));
  const boundary = script.indexOf('var tp=8');
  if (boundary < 0) throw new Error('Offline Three.js bundle boundary missing');
  const ctx = {
    console, URL: SpyURL, Blob: SpyBlob, TextDecoder, TextEncoder, Buffer, setTimeout, clearTimeout, performance,
    document: {
      createElement: () => ({ relList: { supports: () => true } }),
      createElementNS: () => makeImage(),
    },
    window: { URL }, self: {}, require,
  };
  BUNDLE_CTX = ctx;
  BUNDLE = vm.runInNewContext(script.slice(0, boundary) + `;({
    Vector2:G, Vector3:K, Vector4:mn, Quaternion:Xt, Euler:On, Matrix3:q, Matrix4:Y,
    Box3:hr, Color:X, Object3D:Gn, Group:Kn, Scene:er, Bone:ji, Skeleton:Fi,
    Mesh:vi, SkinnedMesh:Ai, BufferGeometry:Jr, BufferAttribute:Nr,
    MeshStandardMaterial:Xa, MeshPhongMaterial:Za, MeshBasicMaterial:oi,
    AnimationMixer:Ts, FBXLoader:cf, MathUtils:Yt, PropertyBinding:Ss,
    SRGBColorSpace:ot, Mf, Ff, Vf
  })`, ctx);
  return BUNDLE;
}

// Hex sRGB -> linear RGB, the same conversion Three.Color.set() performs with color management on.
function hexToLinear(hex) {
  const v = parseInt(String(hex).replace('#', ''), 16);
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255].map(c => {
    const x = c / 255;
    return x <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
  });
}

// Light presets (FBX-Web-Renderer-offline.html applyDungeonLighting) and positions (parity applyBlenderLighting).
const LIGHT_PRESETS = {
  dungeon: { key: 4.5, fill: 0.85, rim: 0, world: 0.35, keyColor: '#ffe2b5', fillColor: '#b3c4e1', rimColor: '#cce7ff' },
  neutral: { key: 3.2, fill: 0.65, rim: 0.4, world: 0.25, keyColor: '#fff0d9', fillColor: '#cbd8ff', rimColor: '#dce8ff' },
  warm: { key: 4.5, fill: 0.25, rim: 0.35, world: 0.14, keyColor: '#ffc276', fillColor: '#875c3b', rimColor: '#ffdda8' },
};

function lightingFor(preset, overrides = {}) {
  const p = Object.assign({}, LIGHT_PRESETS[preset] || LIGHT_PRESETS.neutral, overrides);
  const PI = Math.PI;
  return {
    key: { color: hexToLinear(p.keyColor), intensity: p.key * PI, position: [0.4096 * 30, 0.5736 * 30, -0.7094 * 30] },
    fill: { color: hexToLinear(p.fillColor), intensity: p.fill * PI, position: [-0.5318 * 30, 0.3746 * 30, 0.7595 * 30] },
    rim: { color: hexToLinear(p.rimColor), intensity: p.rim * PI, position: [0, 30, 0] },
    ambient: { color: [1, 1, 1], intensity: p.world * PI },
    castShadow: true,
  };
}

// ---- Parity helpers (ported from FBX-Web-Renderer-parity.js) ----

function isHorizontalRootPosition(track) {
  if (!track || !track.name || !/\.position(?:$|\[)/i.test(track.name)) return false;
  const raw = track.name.replace(/\.position.*$/i, '');
  const bone = raw.match(/bones\[([^\]]+)\]/i);
  const name = (bone ? bone[1] : raw.split(/[.\[\]/:]/).pop()).replace(/[^a-z0-9]/gi, '').toLowerCase();
  return /^(mixamorig)?(hips|pelvis|root|rootmotion|rootnode|rootnodel|motionroot|armature)$/.test(name) || /^rootnode[a-z0-9]*$/.test(name);
}

// Port of applyInPlaceMotion (bundle). Keeps the root's horizontal position at the first key.
function applyInPlaceMotion(B, clips, enabled, model) {
  let count = 0;
  model && model.updateWorldMatrix(true, true);
  for (const clip of clips || []) for (const track of clip.tracks || []) {
    if (!isHorizontalRootPosition(track) || !track.values || !track.times || !track.times.length) continue;
    const size = track.values.length / track.times.length;
    const parsed = B.PropertyBinding.parseTrackName(track.name);
    let node = model ? B.PropertyBinding.findNode(model, parsed.nodeName) : null;
    if (node && parsed.objectName === 'bones') node = node.skeleton && node.skeleton.getBoneByName(parsed.objectIndex);
    const matrix = node && node.parent ? node.parent.matrixWorld : null;
    const component = track.name.match(/\.position\[(x|y|z|0|1|2)\]$/i);
    const axis = component ? ({ x: 0, y: 1, z: 2, 0: 0, 1: 1, 2: 2 })[component[1].toLowerCase()] : null;
    const horizontalScalar = size === 1 && axis !== null && (matrix ? Math.abs(matrix.elements[axis * 4 + 1]) < 1e-8 : axis !== 1);
    if (size !== 3 && !horizontalScalar) continue;
    track.__dungeonOriginalValues = track.__dungeonOriginalValues || track.values.slice();
    const original = track.__dungeonOriginalValues;
    if (enabled && size === 3) {
      const base = new B.Vector3().fromArray(original), point = new B.Vector3();
      const inverse = matrix && matrix.clone().invert();
      if (matrix) base.applyMatrix4(matrix);
      for (let i = 0; i < track.times.length; i++) {
        point.fromArray(original, i * 3);
        if (matrix) point.applyMatrix4(matrix);
        point.x = base.x; point.z = base.z;
        if (inverse) point.applyMatrix4(inverse);
        point.toArray(track.values, i * 3);
      }
    } else if (enabled) {
      const initial = original[0];
      for (let i = 0; i < track.values.length; i++) track.values[i] = initial;
    } else {
      track.values.set(original);
    }
    count++;
  }
  return count;
}

const cleanName = s => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');

function getNeckTiltTargets(model) {
  if (!model) return [];
  const targets = [];
  let neck = null, head = null;
  model.traverse(node => {
    if (!node.isBone && !node.isMesh && !node.isObject3D) return;
    const n = cleanName(node.name);
    if (!neck) {
      if (n.endsWith('neck') || n.endsWith('neck1') || n.endsWith('neck01') || n === 'neck') neck = node;
      else if (n.includes('neck') && !n.includes('twist') && !n.includes('cloth')) neck = node;
    }
    if (!head) {
      if (n.endsWith('head') || n.endsWith('head1') || n.endsWith('head01') || n === 'head') head = node;
      else if (n.includes('head') && !n.includes('twist') && !n.includes('cloth') && !n.includes('hair') && !n.includes('eye')) head = node;
    }
  });
  if (!neck && !head) {
    let highest = null, maxY = -Infinity;
    model.traverse(node => {
      if (node !== model && (node.isMesh || node.isBone) && node.position && node.position.y > maxY) { maxY = node.position.y; highest = node; }
    });
    if (highest) { head = highest; if (!head.name) head.name = 'Head'; }
  }
  if (neck) {
    targets.push(neck);
    if (head) {
      let isDescendant = false, curr = head.parent;
      while (curr) { if (curr === neck) { isDescendant = true; break; } curr = curr.parent; }
      if (!isDescendant) targets.push(head);
    }
  } else if (head) targets.push(head);
  return targets;
}

function getCharacterLateralAxis(B, model) {
  if (!model) return new B.Vector3(1, 0, 0);
  let left = null, right = null;
  model.traverse(node => {
    if (!node.isBone) return;
    const n = cleanName(node.name);
    if (!left && (n.includes('leftshoulder') || n.includes('shoulderl') || n.includes('leftarm') || n.includes('arml') || n.includes('leftupperarm'))) left = node;
    if (!right && (n.includes('rightshoulder') || n.includes('shoulderr') || n.includes('rightarm') || n.includes('armr') || n.includes('rightupperarm'))) right = node;
  });
  if (!left || !right) {
    model.traverse(node => {
      if (!node.isBone) return;
      const n = cleanName(node.name);
      if (!left && (n.includes('leftupleg') || n.includes('thighl') || n.includes('leftleg'))) left = node;
      if (!right && (n.includes('rightupleg') || n.includes('thighr') || n.includes('rightleg'))) right = node;
    });
  }
  const lateralWorld = new B.Vector3(1, 0, 0);
  if (left && right) {
    left.updateMatrixWorld(true); right.updateMatrixWorld(true);
    const pL = new B.Vector3(), pR = new B.Vector3();
    left.getWorldPosition(pL); right.getWorldPosition(pR);
    lateralWorld.subVectors(pL, pR);
    lateralWorld.y = 0;
    if (lateralWorld.lengthSq() > 1e-6) return lateralWorld.normalize();
  }
  model.updateMatrixWorld(true);
  const qModel = new B.Quaternion();
  model.getWorldQuaternion(qModel);
  lateralWorld.set(1, 0, 0).applyQuaternion(qModel);
  lateralWorld.y = 0;
  return lateralWorld.lengthSq() > 1e-6 ? lateralWorld.normalize() : lateralWorld.set(1, 0, 0);
}

// Matches applyNeckPitch in parity.js (pitch in degrees, applied after every mixer update).
function applyNeckPitch(B, model, pitchDeg) {
  if (!model) return;
  const targets = getNeckTiltTargets(model);
  if (!targets.length) return;
  const pitchRad = (pitchDeg * Math.PI) / 180.0;
  const lateralWorld = getCharacterLateralAxis(B, model);
  for (const bone of targets) {
    if (bone._currentPitchQuat) {
      bone.quaternion.premultiply(bone._currentPitchQuat.clone().invert());
      bone._currentPitchQuat = null;
    }
    if (Math.abs(pitchRad) > 1e-5) {
      const parentWorldQ = new B.Quaternion();
      if (bone.parent) { bone.parent.updateMatrixWorld(true); bone.parent.getWorldQuaternion(parentWorldQ); }
      const lateralParent = lateralWorld.clone().applyQuaternion(parentWorldQ.clone().invert()).normalize();
      const qPitch = new B.Quaternion();
      qPitch.setFromAxisAngle(lateralParent, pitchRad);
      bone.quaternion.premultiply(qPitch);
      bone._currentPitchQuat = qPitch.clone();
    }
    bone.updateMatrix();
    bone.updateMatrixWorld(true);
  }
  model.traverse(node => { if (node.isSkinnedMesh && node.skeleton) node.skeleton.update(); });
}


// ---- Stride metrics (parity.js detectRootMotionStride, detectFootStride, findFootBones) ----
function rootMotionStride(B, clip, model) {
  if (!clip || !clip.tracks) return 0;
  if (clip.userData && clip.userData.rootMotionStride) return clip.userData.rootMotionStride;
  let maxDist = 0;
  for (const track of clip.tracks) {
    if (!isHorizontalRootPosition(track)) continue;
    if (!track.values || !track.times || track.times.length < 2) continue;
    const vals = track.__dungeonOriginalValues || track.values;
    const size = track.values.length / track.times.length;
    if (size !== 3) continue;
    const v0 = new B.Vector3(vals[0], vals[1], vals[2]);
    const vEnd = new B.Vector3(vals[vals.length - 3], vals[vals.length - 2], vals[vals.length - 1]);
    let matrix = null;
    try {
      if (track.name && !track.name.startsWith('.')) {
        const parsed = B.PropertyBinding.parseTrackName(track.name);
        let node = (model && parsed && parsed.nodeName) ? B.PropertyBinding.findNode(model, parsed.nodeName) : null;
        if (node && parsed.objectName === 'bones') node = node.skeleton && node.skeleton.getBoneByName(parsed.objectIndex);
        matrix = node && node.parent ? node.parent.matrixWorld : (model ? model.matrixWorld : null);
      }
    } catch (e) { /* as in the lab: fall back to the model matrix */ }
    if (!matrix && model) matrix = model.matrixWorld;
    if (matrix) { v0.applyMatrix4(matrix); vEnd.applyMatrix4(matrix); }
    const d = Math.hypot(vEnd.x - v0.x, vEnd.z - v0.z);
    if (d > maxDist) maxDist = d;
  }
  if (maxDist > 0.05) {
    clip.userData = clip.userData || {};
    clip.userData.rootMotionStride = maxDist;
    return maxDist;
  }
  return 0;
}

function findFootBones(model) {
  let leftFoot = null, rightFoot = null, leftToe = null, rightToe = null;
  const normalize = name => (name || '').replace(/[^a-z0-9]/gi, '').toLowerCase();
  model.traverse(node => {
    const name = normalize(node.name);
    if (/^(mixamorig)?(lefttoebase|toel|ltoe|lefttoe)$/.test(name)) leftToe = node;
    else if (/^(mixamorig)?(righttoebase|toer|rtoe|righttoe)$/.test(name)) rightToe = node;
    else if (/^(mixamorig)?(leftfoot|footl|lfoot|leftankle|anklel|lankle)$/.test(name)) leftFoot = node;
    else if (/^(mixamorig)?(rightfoot|footr|rfoot|rightankle|ankler|rankle)$/.test(name)) rightFoot = node;
  });
  const left = leftFoot || leftToe, right = rightFoot || rightToe;
  return left && right ? { left, right } : null;
}

function footStride(B, clip, model, mixer, wrapper) {
  const feet = findFootBones(model);
  if (!feet || !clip || !clip.duration || !mixer) return 0;
  const duration = clip.duration;
  const savedTime = mixer.time || 0;
  let maxFootDist = 0;
  const pL = new B.Vector3(), pR = new B.Vector3();
  for (let i = 0; i < 16; i++) {
    mixer.setTime((i / 16) * duration);
    wrapper.updateMatrixWorld(true);
    feet.left.getWorldPosition(pL); feet.right.getWorldPosition(pR);
    const d = Math.hypot(pL.x - pR.x, pL.z - pR.z);
    if (d > maxFootDist) maxFootDist = d;
  }
  mixer.setTime(savedTime);
  wrapper.updateMatrixWorld(true);
  return maxFootDist > 0.05 ? 2.0 * maxFootDist : 0;
}

// ---- Normals of a skinned mesh (position skinning comes from the bundle's getVertexPosition) ----

function mat4FromArray(a, off) { return Array.from(a.subarray(off, off + 16)); }
function mul4(a, b) {
  const o = new Array(16);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) {
    o[c * 4 + r] = a[r] * b[c * 4] + a[4 + r] * b[c * 4 + 1] + a[8 + r] * b[c * 4 + 2] + a[12 + r] * b[c * 4 + 3];
  }
  return o;
}
// Inverse-transpose 3x3 of a column-major 4x4 (normal matrix), returned as 9 numbers column-major.
function normalMatrix3(m) {
  const a = m[0], b = m[1], c = m[2], d = m[4], e = m[5], f = m[6], g = m[8], h = m[9], i = m[10];
  const A = e * i - f * h, B2 = -(d * i - f * g), C = d * h - e * g;
  const det = a * A + b * B2 + c * C;
  if (!det) return [1, 0, 0, 0, 1, 0, 0, 0, 1];
  const inv = 1 / det;
  // inverse (cofactors) transposed = normal matrix; return column-major
  return [A * inv, B2 * inv, C * inv,
    -(b * i - c * h) * inv, (a * i - c * g) * inv, -(a * h - b * g) * inv,
    (b * f - c * e) * inv, -(a * f - c * d) * inv, (a * e - b * d) * inv];
}

// Posed meshes of `root` for the current pose (root must be updated). Returns per visible mesh:
// { mesh, positions: Float32Array (world), normals: Float32Array (world, normalized) }.
// Skinning is linear: per bone Q_k = bindInv * M_k * bind, so p' = sum_k w_k Q_k p (same as SkinnedMesh.boneTransform).
function posedMeshes(root) {
  root.updateMatrixWorld(true);
  const out = [];
  root.traverse(node => {
    if (!node.isMesh || !node.visible || !node.geometry?.attributes?.position) return;
    if (node.isSkinnedMesh && node.skeleton) node.skeleton.update();
    const geo = node.geometry;
    const pos = geo.attributes.position, n = pos.count;
    const px = pos.array, pstride = pos.itemSize;
    const positions = new Float32Array(n * 3), normals = new Float32Array(n * 3);
    const mw = node.matrixWorld.elements;
    const nm = normalMatrix3(mw);
    const nIn = geo.attributes.normal;
    const skin = !!(node.isSkinnedMesh && node.skeleton);
    let Q = null, N = null, sIdx = null, sW = null;
    if (skin) {
      const bones = node.skeleton.boneMatrices;
      const bind = node.bindMatrix.elements, bindInv = node.bindMatrixInverse.elements;
      const nb = bones.length / 16;
      Q = new Float64Array(nb * 16);
      N = new Float64Array(nb * 9);
      for (let b = 0; b < nb; b++) {
        const bm = mat4FromArray(bones, b * 16);
        const q = mul4(mul4(bindInv, bm), bind);
        for (let k = 0; k < 16; k++) Q[b * 16 + k] = q[k];
        // normal part: 3x3 of the same product (column-major)
        for (let k = 0; k < 9; k++) N[b * 9 + k] = q[(k / 3 | 0) * 4 + (k % 3)];
      }
      sIdx = geo.attributes.skinIndex; sW = geo.attributes.skinWeight;
    }
    for (let i = 0; i < n; i++) {
      const x0 = px[i * pstride], y0 = px[i * pstride + 1], z0 = px[i * pstride + 2];
      let x, y, z, nx = 0, ny = 1, nz = 0;
      if (skin) {
        x = y = z = 0;
        const wArr = [sW.getX(i), sW.getY(i), sW.getZ(i), sW.getW(i)];
        const bArr = [sIdx.getX(i), sIdx.getY(i), sIdx.getZ(i), sIdx.getW(i)];
        const nIn3 = nIn ? [nIn.getX(i), nIn.getY(i), nIn.getZ(i)] : null;
        if (nIn3) { nx = ny = nz = 0; }
        for (let k = 0; k < 4; k++) {
          const w = wArr[k];
          if (!w) continue;
          const b = bArr[k], o = b * 16;
          x += w * (Q[o] * x0 + Q[o + 4] * y0 + Q[o + 8] * z0 + Q[o + 12]);
          y += w * (Q[o + 1] * x0 + Q[o + 5] * y0 + Q[o + 9] * z0 + Q[o + 13]);
          z += w * (Q[o + 2] * x0 + Q[o + 6] * y0 + Q[o + 10] * z0 + Q[o + 14]);
          if (nIn3) {
            const q = b * 9, a0 = nIn3[0], a1 = nIn3[1], a2 = nIn3[2];
            nx += w * (N[q] * a0 + N[q + 3] * a1 + N[q + 6] * a2);
            ny += w * (N[q + 1] * a0 + N[q + 4] * a1 + N[q + 7] * a2);
            nz += w * (N[q + 2] * a0 + N[q + 5] * a1 + N[q + 8] * a2);
          }
        }
      } else {
        x = x0; y = y0; z = z0;
        if (nIn) { nx = nIn.getX(i); ny = nIn.getY(i); nz = nIn.getZ(i); }
      }
      positions[i * 3] = mw[0] * x + mw[4] * y + mw[8] * z + mw[12];
      positions[i * 3 + 1] = mw[1] * x + mw[5] * y + mw[9] * z + mw[13];
      positions[i * 3 + 2] = mw[2] * x + mw[6] * y + mw[10] * z + mw[14];
      if (nIn) {
        const wx = nm[0] * nx + nm[3] * ny + nm[6] * nz;
        const wy = nm[1] * nx + nm[4] * ny + nm[7] * nz;
        const wz = nm[2] * nx + nm[5] * ny + nm[8] * nz;
        const len = Math.hypot(wx, wy, wz) || 1;
        normals[i * 3] = wx / len; normals[i * 3 + 1] = wy / len; normals[i * 3 + 2] = wz / len;
      } else {
        normals[i * 3 + 1] = 1;
      }
    }
    out.push({ mesh: node, positions, normals });
  });
  return out;
}

// Min Y over all posed positions (parity posedPoints + Qf minY).
function minYOf(meshes) {
  let minY = Infinity;
  for (const m of meshes) for (let i = 1; i < m.positions.length; i += 3) if (m.positions[i] < minY) minY = m.positions[i];
  return minY;
}

// Material conversion as in setupModelMaterials (parity.js ~524) -> renderer material spec.
function materialSpecOf(mat, normalStrength) {
  const diffuse = mat.map || null;
  const normal = mat.normalMap || null;
  const emMap = mat.emissiveMap || null;
  const baseColor = diffuse ? [1, 1, 1] : (mat.color ? [mat.color.r, mat.color.g, mat.color.b] : [0.6, 0.6, 0.6]);
  const emColor = emMap ? [1, 1, 1] : (mat.emissive ? [mat.emissive.r, mat.emissive.g, mat.emissive.b] : [0, 0, 0]);
  return {
    name: mat.name || '',
    color: baseColor,
    roughness: mat.roughness ?? 0.85,
    metalness: mat.metalness ?? 0.05,
    emissive: emColor,
    emissiveIntensity: emMap ? 1.0 : (mat.emissiveIntensity ?? 0.35),
    normalScale: normalStrength,
    map: diffuse ? { src: diffuse, colorSpace: 'srgb' } : null,
    normalMap: normal ? { src: normal, colorSpace: 'linear' } : null,
    emissiveMap: emMap ? { src: emMap, colorSpace: 'srgb' } : null,
    doubleSided: false,
  };
}

function textureOf(tex, colorSpace) {
  const img = tex.image;
  if (!img || !img.decoded) return null;
  return {
    width: img.decoded.width, height: img.decoded.height, data: img.decoded.data,
    colorSpace, flipY: tex.flipY !== false,
    wrapS: tex.wrapS, wrapT: tex.wrapT,
  };
}

// Loads and prepares a character. opts: { anim, inPlace, neckPitch, rigScale, normScale, normalStrength,
// muzzleBone, muzzleForward, fixedGround, animsOnly }
async function loadCharacter(fbxPath, opts = {}) {
  const B = loadBundle();
  ENV.decoder = opts.decoder || null;
  const marks = {}; let tm = Date.now();
  const mark = k => { const n = Date.now(); marks[k] = n - tm; tm = n; };
  const buf = fs.readFileSync(fbxPath);
  // The loader tests `Content instanceof ArrayBuffer`: the buffer must come from the bundle's realm.
  const ab = vm.runInContext(`new ArrayBuffer(${buf.length})`, BUNDLE_CTX);
  new Uint8Array(ab).set(buf);
  mark('read');
  const fbx = new B.FBXLoader().parse(ab, '');
  mark('parse');
  // decode only the PNGs that materials reference (in worker threads, in parallel)
  const used = new Set();
  fbx.traverse(n => {
    if (!n.isMesh || !n.material) return;
    for (const m of (Array.isArray(n.material) ? n.material : [n.material])) {
      for (const k of ['map', 'normalMap', 'emissiveMap']) if (m[k] && m[k].image) used.add(m[k].image);
    }
  });
  for (const img of used) {
    if (img._syncBytes && ENV.decoder) {
      ENV.pending.push(ENV.decoder(img._syncBytes.slice()).then(d => { img.width = d.width; img.height = d.height; img.decoded = d; }));
    }
  }
  await Promise.all(ENV.pending.splice(0));
  mark('textures');
  if (ENV.jpegSeen) throw new DelegateError('embedded JPEG textures (' + ENV.jpegSeen + ')');
  const clips = fbx.animations || [];
  const clipLabel = c => `${c.name} (${c.duration.toFixed(2)}s)`;

  // Lf: normalization to 1.8 m (or the reference normScale) with the rest pose, then wrapper.
  const model = fbx;
  model.traverse(node => {
    if (node.isMesh) {
      node.frustumCulled = false; node.castShadow = true; node.receiveShadow = true;
      if (node.material) (Array.isArray(node.material) ? node.material : [node.material]).forEach(m => { m.side = 0; });
    }
  });
  model.position.set(0, 0, 0);
  model.updateMatrixWorld(true);
  const pts0 = posedMeshes(model);
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity, minZ = Infinity, maxZ = -Infinity;
  for (const m of pts0) for (let i = 0; i < m.positions.length; i += 3) {
    const x = m.positions[i], y = m.positions[i + 1], z = m.positions[i + 2];
    if (x < minX) minX = x; if (x > maxX) maxX = x;
    if (y < minY) minY = y; if (y > maxY) maxY = y;
    if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;
  }
  if (!isFinite(minY)) { minY = 0; maxY = 1.8; minX = -0.5; maxX = 0.5; minZ = -0.5; maxZ = 0.5; }
  const height = (maxY - minY) || 1.8, width = (maxX - minX) || 1.0, depth = (maxZ - minZ) || 1.0;
  const wrapper = new B.Group();
  model.position.set(0, -minY, 0);
  wrapper.add(model);
  const normScale = opts.normScale > 0 ? opts.normScale : 1.8 / Math.max(height, width, depth);
  wrapper.scale.setScalar(normScale);
  wrapper.updateMatrixWorld(true);

  mark('lf');
  // Stride detection runs before the in-place rewrite (the lab's applyInPlaceMotion hook does the same).
  const inPlace = !!opts.inPlace;
  const charHeight = (height * normScale) > 0.05 ? height * normScale : 1.8;
  for (const c of clips) rootMotionStride(B, c, model);
  for (const c of clips) applyInPlaceMotion(B, [c], inPlace, model);

  const normalStrength = opts.normalStrength ?? 0.35;

  // Pick the clip (exact label match, else cleaned name match like the CLI).
  let clip = null;
  if (clips.length) {
    const want = opts.anim;
    clip = clips.find(c => clipLabel(c) === want) || null;
    if (!clip && want) {
      const clean = t => String(t || '').replace(/\s*\(\s*\d+(?:\.\d+)?s\s*\)\s*$/, '').trim();
      clip = clips.find(c => clean(c.name) === clean(want)) || null;
      if (!clip) throw new Error(`animation "${want}" not found; available: ${clips.map(clipLabel).join(', ')}`);
    }
    clip = clip || clips[0];
  }
  const duration = clip ? (clip.duration || 0) : 0;

  const mixer = clip ? new B.AnimationMixer(fbx) : null;
  const action = clip ? mixer.clipAction(clip) : null;
  if (action) action.play();
  let stride3D = clip ? rootMotionStride(B, clip, model) : 0;
  if (stride3D <= 0.05 && mixer) stride3D = footStride(B, clip, model, mixer, wrapper);
  if (stride3D <= 0.05) stride3D = 0.833 * charHeight;

  // Parity hooks: neck pitch after every mixer update / setTime (FBX-Web-Renderer-parity.js ~370).
  const pitch = opts.neckPitch ?? 0;
  if (mixer) {
    const origUpdate = B.AnimationMixer.prototype.update;
    B.AnimationMixer.prototype.update = function (delta) {
      for (const t of getNeckTiltTargets(model)) t._currentPitchQuat = null;
      const res = origUpdate.call(this, delta);
      applyNeckPitch(B, model, pitch);
      return res;
    };
    const origSetTime = B.AnimationMixer.prototype.setTime;
    B.AnimationMixer.prototype.setTime = function (time) {
      for (const t of getNeckTiltTargets(model)) t._currentPitchQuat = null;
      const res = origSetTime.call(this, time);
      applyNeckPitch(B, model, pitch);
      return res;
    };
  }

  // Materials and textures (converted once; the renderer receives the spec + decoded RGBA).
  const materials = [];
  const matIndex = new Map();
  const meshesInfo = [];
  model.traverse(node => {
    if (!node.isMesh || !node.geometry?.attributes?.position) return;
    const mats = Array.isArray(node.material) ? node.material : [node.material];
    const mi = mats.map(m => {
      if (!matIndex.has(m)) {
        const spec = materialSpecOf(m, normalStrength);
        matIndex.set(m, materials.length);
        materials.push({ spec, orig: m });
      }
      return matIndex.get(m);
    });
    meshesInfo.push({ node, materialIndex: mi[0] });
  });

  // Textures: decode now (flip/wrap from the three.js texture object).
  const texCache = new Map();
  const resolveTex = (tex, colorSpace) => {
    if (!tex) return null;
    if (!texCache.has(tex)) texCache.set(tex, textureOf(tex, colorSpace));
    return texCache.get(tex);
  };

  // Lookup the render-facing material list with textures resolved.
  const renderMaterials = materials.map(({ spec, orig }) => ({
    color: spec.color,
    roughness: spec.roughness,
    metalness: spec.metalness,
    emissive: spec.emissive,
    emissiveIntensity: spec.emissiveIntensity,
    normalScale: spec.normalScale,
    map: resolveTex(orig.map, 'srgb'),
    normalMap: resolveTex(orig.normalMap, 'linear'),
    emissiveMap: resolveTex(orig.emissiveMap, 'srgb'),
    doubleSided: false,
  }));

  const meshes = meshesInfo.map(({ node, materialIndex }) => {
    const geo = node.geometry;
    const idx = geo.index ? Uint32Array.from(geo.index.array) : null;
    const count = geo.attributes.position.count;
    const indices = idx || Uint32Array.from({ length: count }, (_, i) => i);
    const uvAttr = geo.attributes.uv;
    const uvs = uvAttr ? Float32Array.from(uvAttr.array) : null;
    return { node, indices, uvs, materialIndex, doubleSided: false };
  });

  mark('materials');
  // Pose at time t (root identity). Mirrors Qf: setTime + applyNeckPitch.
  function poseAt(t) {
    if (mixer) { mixer.setTime(t); applyNeckPitch(B, model, pitch); }
    else applyNeckPitch(B, model, pitch);
    const pm = posedMeshes(wrapper);
    return { meshes: pm, minY: minY_of(pm) };
  }
  function minY_of(pm) { return minYOf(pm); }
  // pose without the mesh skinning (enough for bone positions)
  function poseOnly(t) {
    if (mixer) mixer.setTime(t);
    applyNeckPitch(B, model, pitch);
    wrapper.updateMatrixWorld(true);
  }

  return {
    B, fbx, model, wrapper, mixer, clip, clipLabel: clip ? clipLabel(clip) : 'Pose estatica',
    clips: clips.map(clipLabel), duration, normScale, height, width, depth,
    meshes, renderMaterials, lighting: null,
    poseAt, poseOnly, lightingFor,
    pitch, inPlace, stride3D, charHeight, loadMarks: marks,
    matIndexOf: m => (matIndex.has(m) ? matIndex.get(m) : 0),
    // Box3.setFromObject as overridden by the parity layer (precise, posed); used for the muzzle height.
    boxOf(root) {
      // Box3.setFromObject (precise, posed): min/max of the posed world vertices; computed from the arrays we already have
      const pm = posedMeshes(root);
      const box = new B.Box3();
      let mnx = Infinity, mny = Infinity, mnz = Infinity, mxx = -Infinity, mxy = -Infinity, mxz = -Infinity;
      for (const m of pm) {
        const p = m.positions;
        for (let i = 0; i < p.length; i += 3) {
          const x = p[i], y = p[i + 1], z = p[i + 2];
          if (x < mnx) mnx = x; if (x > mxx) mxx = x;
          if (y < mny) mny = y; if (y > mxy) mxy = y;
          if (z < mnz) mnz = z; if (z > mxz) mxz = z;
        }
      }
      box.min.set(mnx, mny, mnz); box.max.set(mxx, mxy, mxz);
      return box;
    },
  };
}

// Copy of a byte array into the bundle's realm (gifenc checks `instanceof Uint8Array` of its own realm).
function bundleU8(src) {
  loadBundle();
  const u = vm.runInContext(`new Uint8Array(${src.length})`, BUNDLE_CTX);
  u.set(src);
  return u;
}

module.exports = { bundleU8, loadCharacter, DelegateError, lightingFor, LIGHT_PRESETS, hexToLinear, posedMeshes, applyNeckPitch, applyInPlaceMotion, loadBundle, getNeckTiltTargets };
