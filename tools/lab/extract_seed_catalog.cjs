/**
 * Extract compact seed catalog of weapons and animations.
 * Generates tools/lab/seed_catalog_data.js (< 2.5 MB)
 */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const MinimalGLBLoader = require('./glb_loader_minimal.js');

const ROOT_DIR = path.resolve(__dirname, '../../');
const LAB_DIR = __dirname;
const OUT_FILE = path.join(LAB_DIR, 'seed_catalog_data.js');

// 1. Procedural Gothic Sword Generator
function generateGothicSword() {
  const positions = [];
  const normals = [];
  const uvs = [];
  const indices = [];

  function addQuad(p0, p1, p2, p3, u0, u1, u2, u3) {
    const baseIdx = positions.length / 3;
    const e1 = [p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]];
    const e2 = [p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]];
    let nx = e1[1] * e2[2] - e1[2] * e2[1];
    let ny = e1[2] * e2[0] - e1[0] * e2[2];
    let nz = e1[0] * e2[1] - e1[1] * e2[0];
    const len = Math.hypot(nx, ny, nz) || 1;
    nx /= len; ny /= len; nz /= len;

    positions.push(...p0, ...p1, ...p2, ...p3);
    for (let i = 0; i < 4; i++) normals.push(nx, ny, nz);
    uvs.push(...u0, ...u1, ...u2, ...u3);

    indices.push(baseIdx, baseIdx + 1, baseIdx + 2, baseIdx, baseIdx + 2, baseIdx + 3);
  }

  function addTri(p0, p1, p2, u0, u1, u2) {
    const baseIdx = positions.length / 3;
    const e1 = [p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]];
    const e2 = [p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]];
    let nx = e1[1] * e2[2] - e1[2] * e2[1];
    let ny = e1[2] * e2[0] - e1[0] * e2[2];
    let nz = e1[0] * e2[1] - e1[1] * e2[0];
    const len = Math.hypot(nx, ny, nz) || 1;
    nx /= len; ny /= len; nz /= len;

    positions.push(...p0, ...p1, ...p2);
    for (let i = 0; i < 3; i++) normals.push(nx, ny, nz);
    uvs.push(...u0, ...u1, ...u2);

    indices.push(baseIdx, baseIdx + 1, baseIdx + 2);
  }

  // Blade with diamond cross-section bevel
  const bladeZ = [0.025, 0.20, 0.50, 0.75, 0.90];
  const bladeW = [0.045, 0.042, 0.038, 0.030, 0.020];
  const bladeT = [0.012, 0.010, 0.008, 0.006, 0.004];

  for (let s = 0; s < bladeZ.length - 1; s++) {
    const z0 = bladeZ[s], z1 = bladeZ[s + 1];
    const w0 = bladeW[s] / 2, w1 = bladeW[s + 1] / 2;
    const t0 = bladeT[s] / 2, t1 = bladeT[s + 1] / 2;

    const ring0 = [
      [w0, 0, z0],
      [0, t0, z0],
      [-w0, 0, z0],
      [0, -t0, z0]
    ];
    const ring1 = [
      [w1, 0, z1],
      [0, t1, z1],
      [-w1, 0, z1],
      [0, -t1, z1]
    ];

    addQuad(ring0[0], ring1[0], ring1[1], ring0[1], [0.8, z0], [0.8, z1], [0.5, z1], [0.5, z0]);
    addQuad(ring0[1], ring1[1], ring1[2], ring0[2], [0.5, z0], [0.5, z1], [0.2, z1], [0.2, z0]);
    addQuad(ring0[2], ring1[2], ring1[3], ring0[3], [0.2, z0], [0.2, z1], [0.5, z1], [0.5, z0]);
    addQuad(ring0[3], ring1[3], ring1[0], ring0[0], [0.5, z0], [0.5, z1], [0.8, z1], [0.8, z0]);
  }

  // Blade Tip
  const lastZ = bladeZ[bladeZ.length - 1];
  const lastW = bladeW[bladeW.length - 1] / 2;
  const lastT = bladeT[bladeT.length - 1] / 2;
  const tip = [0, 0, 0.98];
  const lastRing = [
    [lastW, 0, lastZ],
    [0, lastT, lastZ],
    [-lastW, 0, lastZ],
    [0, -lastT, lastZ]
  ];
  addTri(lastRing[0], tip, lastRing[1], [0.8, lastZ], [0.5, 0.98], [0.5, lastZ]);
  addTri(lastRing[1], tip, lastRing[2], [0.5, lastZ], [0.5, 0.98], [0.2, lastZ]);
  addTri(lastRing[2], tip, lastRing[3], [0.2, lastZ], [0.5, 0.98], [0.5, lastZ]);
  addTri(lastRing[3], tip, lastRing[0], [0.5, lastZ], [0.5, 0.98], [0.8, lastZ]);

  // Crossguard
  const gW = 0.11, gY = 0.012, gZ0 = 0.00, gZ1 = 0.025;
  const cP = [
    [-gW, -gY, gZ0], [gW, -gY, gZ0], [gW, gY, gZ0], [-gW, gY, gZ0],
    [-gW, -gY, gZ1], [gW, -gY, gZ1], [gW, gY, gZ1], [-gW, gY, gZ1]
  ];
  addQuad(cP[4], cP[5], cP[6], cP[7], [0, 0], [1, 0], [1, 1], [0, 1]);
  addQuad(cP[1], cP[0], cP[3], cP[2], [0, 0], [1, 0], [1, 1], [0, 1]);
  addQuad(cP[3], cP[2], cP[6], cP[7], [0, 0], [1, 0], [1, 1], [0, 1]);
  addQuad(cP[0], cP[1], cP[5], cP[4], [0, 0], [1, 0], [1, 1], [0, 1]);
  addQuad(cP[1], cP[2], cP[6], cP[5], [0, 0], [1, 0], [1, 1], [0, 1]);
  addQuad(cP[0], cP[4], cP[7], cP[3], [0, 0], [1, 0], [1, 1], [0, 1]);

  // Grip
  const gripSegs = 8;
  const gripR = 0.013;
  const gripZ0 = -0.10, gripZ1 = 0.00;
  for (let i = 0; i < gripSegs; i++) {
    const a0 = (i / gripSegs) * Math.PI * 2;
    const a1 = ((i + 1) / gripSegs) * Math.PI * 2;
    const x0 = Math.cos(a0) * gripR, y0 = Math.sin(a0) * gripR;
    const x1 = Math.cos(a1) * gripR, y1 = Math.sin(a1) * gripR;

    const p0 = [x0, y0, gripZ0];
    const p1 = [x1, y1, gripZ0];
    const p2 = [x1, y1, gripZ1];
    const p3 = [x0, y0, gripZ1];
    addQuad(p0, p1, p2, p3, [i / gripSegs, 0], [(i + 1) / gripSegs, 0], [(i + 1) / gripSegs, 1], [i / gripSegs, 1]);
  }

  // Pommel
  const pommelZ0 = -0.135, pommelZ1 = -0.10, pommelR = 0.022;
  for (let i = 0; i < gripSegs; i++) {
    const a0 = (i / gripSegs) * Math.PI * 2;
    const a1 = ((i + 1) / gripSegs) * Math.PI * 2;
    const x0 = Math.cos(a0) * pommelR, y0 = Math.sin(a0) * pommelR;
    const x1 = Math.cos(a1) * pommelR, y1 = Math.sin(a1) * pommelR;

    addQuad([x0, y0, pommelZ0], [x1, y1, pommelZ0], [x1, y1, pommelZ1], [x0, y0, pommelZ1], [0, 0], [1, 0], [1, 1], [0, 1]);
    addTri([x1, y1, pommelZ0], [x0, y0, pommelZ0], [0, 0, pommelZ0], [0, 0], [1, 0], [0.5, 1]);
    addTri([x0, y0, pommelZ1], [x1, y1, pommelZ1], [0, 0, pommelZ1], [0, 0], [1, 0], [0.5, 1]);
  }

  return {
    positions: new Float32Array(positions),
    normals: new Float32Array(normals),
    uvs: new Float32Array(uvs),
    indices: new Uint32Array(indices),
    color: [0.85, 0.88, 0.92],
    imageBytes: null,
    mimeType: null
  };
}

// 2. Texture compression helper
function compressImageBytes(imageBytes) {
  if (!imageBytes || imageBytes.length === 0) return null;
  const tmpIn = path.join(LAB_DIR, `_tmp_in_${Date.now()}_${Math.random().toString(36).slice(2)}.png`);
  const tmpOut = path.join(LAB_DIR, `_tmp_out_${Date.now()}_${Math.random().toString(36).slice(2)}.jpg`);
  const pyScript = path.join(LAB_DIR, 'compress_image.py');

  try {
    fs.writeFileSync(tmpIn, imageBytes);
    execFileSync('python', [pyScript, tmpIn, tmpOut, '256', '82']);
    if (fs.existsSync(tmpOut)) {
      const outBytes = fs.readFileSync(tmpOut);
      const isPng = outBytes[0] === 0x89 && outBytes[1] === 0x50;
      const mime = isPng ? 'image/png' : 'image/jpeg';
      return `data:${mime};base64,` + outBytes.toString('base64');
    }
  } catch (err) {
    console.warn('Image compression warning, using fallback base64:', err.message);
  } finally {
    if (fs.existsSync(tmpIn)) fs.unlinkSync(tmpIn);
    if (fs.existsSync(tmpOut)) fs.unlinkSync(tmpOut);
  }

  // Fallback to raw base64
  return 'data:image/png;base64,' + Buffer.from(imageBytes).toString('base64');
}

// 3. Process Weapons
console.log('Extracting weapons...');
const weaponDefinitions = [
  { id: 'ak47', name: 'AK-47 Assault Rifle', type: 'rifle', file: 'assets/blender_combat_demo/weapons/ak47.glb' },
  { id: 'carbine', name: 'M4 Carbine', type: 'rifle', file: 'assets/blender_combat_demo/weapons/carbine.glb' },
  { id: 'battle_rifle', name: 'Battle Rifle', type: 'rifle', file: 'assets/blender_combat_demo/weapons/rifle.glb' },
  { id: 'smg', name: 'Tactical SMG', type: 'rifle', file: 'assets/blender_combat_demo/weapons/smg.glb' },
  { id: 'gothic_sword', name: 'Gothic Broadsword', type: 'sword', procedural: true }
];

const processedWeapons = [];
for (const w of weaponDefinitions) {
  let meshData;
  if (w.procedural) {
    meshData = generateGothicSword();
  } else {
    const fullPath = path.resolve(ROOT_DIR, w.file);
    const buf = fs.readFileSync(fullPath);
    meshData = MinimalGLBLoader.parseGLBToMeshData(buf);
  }

  const vertCount = meshData.positions.length / 3;
  const triCount = meshData.indices.length / 3;

  // Convert to base64
  const posBuf = Buffer.from(meshData.positions.buffer, meshData.positions.byteOffset, meshData.positions.byteLength);
  const normBuf = Buffer.from(meshData.normals.buffer, meshData.normals.byteOffset, meshData.normals.byteLength);
  const uvBuf = Buffer.from(meshData.uvs.buffer, meshData.uvs.byteOffset, meshData.uvs.byteLength);

  // All weapons have < 65536 vertices, use Uint16Array for 50% index compression
  const idx16 = new Uint16Array(meshData.indices);
  const idxBuf = Buffer.from(idx16.buffer, idx16.byteOffset, idx16.byteLength);

  const textureDataUrl = compressImageBytes(meshData.imageBytes);

  processedWeapons.push({
    id: w.id,
    name: w.name,
    type: w.type,
    vertexCount: vertCount,
    triangleCount: triCount,
    color: [
      Number(meshData.color[0].toFixed(3)),
      Number(meshData.color[1].toFixed(3)),
      Number(meshData.color[2].toFixed(3))
    ],
    texture: textureDataUrl,
    positionsB64: posBuf.toString('base64'),
    normalsB64: normBuf.toString('base64'),
    uvsB64: uvBuf.toString('base64'),
    indicesB64: idxBuf.toString('base64')
  });

  console.log(`  ✓ Weapon: ${w.id} (${w.name}) - ${vertCount} verts, ${triCount} tris, texture: ${textureDataUrl ? 'yes' : 'no'}`);
}

// 4. Process Animations using FBXLoader from offline bundle
console.log('\nExtracting animations via FBXLoader...');
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
  URL, Blob, TextDecoder, TextEncoder, Buffer, setTimeout, clearTimeout, performance,
  document: {
    createElement: () => ({ relList: { supports: () => true } }),
    createElementNS: () => imageStub()
  },
  window: { URL }, self: {}, require
};

const api = vm.runInNewContext(
  bundle.slice(0, bundle.indexOf('var tp=8')) +
  '\n({Loader:cf,Mixer:Ts,Box:hr,Vector:K,Quaternion:Xt,Group:Kn,Scene:er,normalize:Lf});',
  context
);

const animDefinitions = [
  { id: 'rifle_idle', categoria: 'Rifle', nombre: 'Rifle Aiming Idle', file: 'assets/blender_combat_demo/weapons/Rifle_Aiming_Idle.fbx' },
  { id: 'rifle_aim', categoria: 'Rifle', nombre: 'Rifle Aim Fire', file: 'assets/blender_combat_demo/weapons/aim.fbx' },
  { id: 'rifle_walk', categoria: 'Rifle', nombre: 'Rifle Walk', file: 'assets/blender_combat_demo/weapons/walk_rifle.fbx' },
  { id: 'rifle_run', categoria: 'Rifle', nombre: 'Rifle Run Forward', file: 'assets/blender_combat_demo/weapons/run_forward_rifle.fbx' },
  { id: 'rifle_crouch_walk', categoria: 'Rifle', nombre: 'Rifle Crouch Walk', file: 'assets/blender_combat_demo/weapons/walk_crouch.fbx' },
  { id: 'melee_slash', categoria: 'Melee', nombre: 'Sword Slash', file: 'assets/blender_combat_demo/Slash.fbx' },
  { id: 'melee_crouch_slash', categoria: 'Melee', nombre: 'Crouch Slash', file: 'assets/blender_combat_demo/Crouchslash.fbx' },
  { id: 'melee_jump_hit', categoria: 'Melee', nombre: 'Jump Attack', file: 'assets/blender_combat_demo/JumpHit.fbx' },
  { id: 'locomotion_run', categoria: 'Locomotion', nombre: 'Heavy Run', file: 'assets/characters/charger/Run.fbx' },
  { id: 'combat_death', categoria: 'Combat', nombre: 'Death Fall', file: 'assets/characters/skeleton/skeleton_death.fbx' }
];

function canonicalBoneName(rawName) {
  return rawName
    .replace(/^Bone_/, '')
    .replace(/^mixamorig\d*[:_]?/, '');
}

const processedAnims = [];
const FPS = 24;

for (const a of animDefinitions) {
  const fbxPath = path.resolve(ROOT_DIR, a.file);
  const bytes = fs.readFileSync(fbxPath);
  const model = new api.Loader().parse(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
  const clip = model.animations && model.animations[0];
  if (!clip) {
    console.error(`  ✕ No animation clip in ${a.file}`);
    continue;
  }

  // Collect rest pose of bones
  const bones = [];
  const boneRestPose = {};
  let hipsRestPosition = [0, 0, 0];
  const tmpQ = new api.Quaternion();
  const tmpV = new api.Vector();

  model.updateWorldMatrix(true, true);

  model.traverse(node => {
    if (node.isBone || node.name.startsWith('Bone_') || node.name.includes('mixamo')) {
      bones.push(node);
      const canon = canonicalBoneName(node.name);
      const isRootBone = canon.toLowerCase() === 'hips' || (!node.parent?.isBone && bones.length === 1);
      if (isRootBone) {
        node.getWorldQuaternion(tmpQ);
        node.getWorldPosition(tmpV);
        boneRestPose[canon] = [
          Number(tmpQ.x.toFixed(4)),
          Number(tmpQ.y.toFixed(4)),
          Number(tmpQ.z.toFixed(4)),
          Number(tmpQ.w.toFixed(4))
        ];
        hipsRestPosition = [
          Number(tmpV.x.toFixed(4)),
          Number(tmpV.y.toFixed(4)),
          Number(tmpV.z.toFixed(4))
        ];
      } else {
        boneRestPose[canon] = [
          Number(node.quaternion.x.toFixed(4)),
          Number(node.quaternion.y.toFixed(4)),
          Number(node.quaternion.z.toFixed(4)),
          Number(node.quaternion.w.toFixed(4))
        ];
      }
    }
  });

  const numFrames = Math.max(2, Math.round(clip.duration * FPS));
  const mixer = new api.Mixer(model);
  const action = mixer.clipAction(clip);
  action.play();

  const boneTracks = {};
  for (const b of bones) {
    const canon = canonicalBoneName(b.name);
    const isRootBone = canon.toLowerCase() === 'hips' || !b.parent?.isBone;
    boneTracks[b.name] = {
      canon,
      rawName: b.name,
      isRootBone,
      rot: [],
      pos: isRootBone ? [] : null
    };
  }

  for (let f = 0; f < numFrames; f++) {
    const t = (f / (numFrames - 1)) * clip.duration;
    mixer.setTime(t);
    model.updateWorldMatrix(true, true);

    for (const b of bones) {
      const trk = boneTracks[b.name];
      if (trk.isRootBone) {
        b.getWorldQuaternion(tmpQ);
        b.getWorldPosition(tmpV);
        trk.rot.push(
          Number(tmpQ.x.toFixed(4)),
          Number(tmpQ.y.toFixed(4)),
          Number(tmpQ.z.toFixed(4)),
          Number(tmpQ.w.toFixed(4))
        );
        trk.pos.push(
          Number(tmpV.x.toFixed(4)),
          Number(tmpV.y.toFixed(4)),
          Number(tmpV.z.toFixed(4))
        );
      } else {
        const q = b.quaternion;
        trk.rot.push(
          Number(q.x.toFixed(4)),
          Number(q.y.toFixed(4)),
          Number(q.z.toFixed(4)),
          Number(q.w.toFixed(4))
        );
      }
    }
  }

  mixer.stopAllAction();
  mixer.uncacheRoot(model);

  const compactTracks = [];
  for (const [rawName, tr] of Object.entries(boneTracks)) {
    // Check if rotation varies from first frame
    let rotVaries = false;
    const baseRot = tr.rot.slice(0, 4);
    for (let i = 4; i < tr.rot.length; i += 4) {
      if (
        Math.abs(tr.rot[i] - baseRot[0]) > 0.0005 ||
        Math.abs(tr.rot[i + 1] - baseRot[1]) > 0.0005 ||
        Math.abs(tr.rot[i + 2] - baseRot[2]) > 0.0005 ||
        Math.abs(tr.rot[i + 3] - baseRot[3]) > 0.0005
      ) {
        rotVaries = true;
        break;
      }
    }

    if (rotVaries) {
      compactTracks.push({
        bone: tr.canon,
        rawBone: tr.rawName,
        type: 'quaternion',
        values: tr.rot
      });
    } else {
      // Single keyframe if static
      compactTracks.push({
        bone: tr.canon,
        rawBone: tr.rawName,
        type: 'quaternion',
        values: baseRot
      });
    }

    if (tr.pos) {
      compactTracks.push({
        bone: tr.canon,
        rawBone: tr.rawName,
        type: 'position',
        values: tr.pos
      });
    }
  }

  processedAnims.push({
    id: a.id,
    name: a.nombre,
    category: a.categoria,
    duration: Number(clip.duration.toFixed(3)),
    fps: FPS,
    numFrames,
    hipsRestPosition,
    boneRestPose,
    tracks: compactTracks
  });

  console.log(`  ✓ Anim: ${a.id} [${a.categoria}] "${a.nombre}" - ${clip.duration.toFixed(2)}s, ${numFrames} frames, ${compactTracks.length} tracks`);
}

// 5. Generate seed_catalog_data.js
console.log('\nGenerating seed_catalog_data.js...');

const jsCode = `/**
 * SEED_CATALOG - Compact Seed Catalog of Weapons & Humanoid Animations.
 * Auto-generated by extract_seed_catalog.cjs.
 */
(function (global) {
  'use strict';

  function decodeBase64ToTypedArray(b64, TypedArrayClass) {
    if (typeof Buffer !== 'undefined') {
      const buf = Buffer.from(b64, 'base64');
      return new TypedArrayClass(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
    } else {
      const binary = atob(b64);
      const len = binary.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) bytes[i] = binary.charCodeAt(i);
      return new TypedArrayClass(bytes.buffer);
    }
  }

  const catalog = {
    weapons: ${JSON.stringify(processedWeapons)},
    animations: ${JSON.stringify(processedAnims)},

    getWeapon(id) {
      return this.weapons.find(w => w.id === id) || null;
    },

    getAnimation(id) {
      return this.animations.find(a => a.id === id) || null;
    },

    getWeaponMeshData(id) {
      const w = this.getWeapon(id);
      if (!w) return null;
      if (!w._decodedMesh) {
        w._decodedMesh = {
          positions: decodeBase64ToTypedArray(w.positionsB64, Float32Array),
          normals: decodeBase64ToTypedArray(w.normalsB64, Float32Array),
          uvs: decodeBase64ToTypedArray(w.uvsB64, Float32Array),
          indices: decodeBase64ToTypedArray(w.indicesB64, Uint16Array),
          color: w.color,
          texture: w.texture
        };
      }
      return w._decodedMesh;
    },

    buildWeaponMesh(id, THREE) {
      if (!THREE) throw new Error('THREE must be supplied to buildWeaponMesh');
      const meshData = this.getWeaponMeshData(id);
      if (!meshData) return null;

      const geom = new THREE.BufferGeometry();
      geom.setAttribute('position', new THREE.BufferAttribute(meshData.positions, 3));
      geom.setAttribute('normal', new THREE.BufferAttribute(meshData.normals, 3));
      geom.setAttribute('uv', new THREE.BufferAttribute(meshData.uvs, 2));
      geom.setIndex(new THREE.BufferAttribute(meshData.indices, 1));

      let mat;
      if (meshData.texture && THREE.TextureLoader) {
        try {
          const map = new THREE.TextureLoader().load(meshData.texture);
          if (THREE.SRGBColorSpace) map.colorSpace = THREE.SRGBColorSpace;
          mat = new THREE.MeshStandardMaterial({
            map: map,
            roughness: 0.65,
            metalness: 0.2
          });
        } catch (e) {
          mat = new THREE.MeshStandardMaterial({
            color: new THREE.Color(meshData.color[0], meshData.color[1], meshData.color[2]),
            roughness: 0.65,
            metalness: 0.2
          });
        }
      } else {
        mat = new THREE.MeshStandardMaterial({
          color: new THREE.Color(meshData.color[0], meshData.color[1], meshData.color[2]),
          roughness: 0.5,
          metalness: 0.35
        });
      }

      const mesh = new THREE.Mesh(geom, mat);
      mesh.name = id;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      return mesh;
    },

    createAnimationClip(id, THREE, rigPrefix = '') {
      if (!THREE) throw new Error('THREE must be supplied to createAnimationClip');
      const anim = this.getAnimation(id);
      if (!anim) return null;

      const tracks = [];
      const numFrames = anim.numFrames;
      const duration = anim.duration;

      for (const tr of anim.tracks) {
        const boneName = rigPrefix ? (rigPrefix + tr.bone) : (tr.rawBone || tr.bone);

        if (tr.type === 'quaternion') {
          let times, values;
          if (tr.values.length === 4) {
            times = new Float32Array([0, duration]);
            values = new Float32Array([
              tr.values[0], tr.values[1], tr.values[2], tr.values[3],
              tr.values[0], tr.values[1], tr.values[2], tr.values[3]
            ]);
          } else {
            const count = tr.values.length / 4;
            times = new Float32Array(count);
            for (let i = 0; i < count; i++) {
              times[i] = (i / (count - 1)) * duration;
            }
            values = new Float32Array(tr.values);
          }
          tracks.push(new THREE.QuaternionKeyframeTrack(boneName + '.quaternion', times, values));
        } else if (tr.type === 'position') {
          let times, values;
          if (tr.values.length === 3) {
            times = new Float32Array([0, duration]);
            values = new Float32Array([
              tr.values[0], tr.values[1], tr.values[2],
              tr.values[0], tr.values[1], tr.values[2]
            ]);
          } else {
            const count = tr.values.length / 3;
            times = new Float32Array(count);
            for (let i = 0; i < count; i++) {
              times[i] = (i / (count - 1)) * duration;
            }
            values = new Float32Array(tr.values);
          }
          tracks.push(new THREE.VectorKeyframeTrack(boneName + '.position', times, values));
        }
      }

      return new THREE.AnimationClip(anim.name || id, duration, tracks);
    }
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = catalog;
  }
  if (typeof window !== 'undefined') {
    window.SEED_CATALOG = catalog;
  }
})(typeof globalThis !== 'undefined' ? globalThis : typeof window !== 'undefined' ? window : this);
`;

fs.writeFileSync(OUT_FILE, jsCode, 'utf8');
const stats = fs.statSync(OUT_FILE);
const mb = (stats.size / (1024 * 1024)).toFixed(2);
console.log(`\n========================================`);
console.log(`Output: ${OUT_FILE}`);
console.log(`File size: ${stats.size} bytes (${mb} MB)`);
if (stats.size < 2.5 * 1024 * 1024) {
  console.log(`STATUS: SUCCESS (Within < 2.5 MB budget!)`);
} else {
  console.log(`STATUS: WARNING (Exceeds 2.5 MB budget)`);
}
console.log(`========================================`);
