/**
 * FBX Weapon & Animation Assembler Lab — Main Browser Application
 * Connects Three.js, RetargetAndIKEngine, MinimalGLBLoader, SEED_CATALOG, and FBXBinarySplicer.
 */
(function () {
  if (typeof document === 'undefined' || !document.getElementById('viewportCanvas')) return;

  // 1. Bridge minified Three.js classes from the embedded offline bundle
  const THREE = window.THREE_LAB = {
    Vector2: G,
    Vector3: K,
    Vector4: mn,
    Quaternion: Xt,
    Euler: On,
    Matrix3: q,
    Matrix4: Y,
    Box3: hr,
    Plane: Qr,
    Color: X,
    Object3D: Gn,
    Group: Kn,
    Scene: er,
    Bone: ji,
    Skeleton: Fi,
    Mesh: vi,
    SkinnedMesh: Ai,
    BufferGeometry: Jr,
    BufferAttribute: Nr,
    Float32BufferAttribute: Ir,
    Uint16BufferAttribute: Pr,
    Uint32BufferAttribute: Fr,
    MeshStandardMaterial: Xa,
    MeshPhongMaterial: Za,
    MeshBasicMaterial: oi,
    LineBasicMaterial: Bi,
    Line: Ji,
    Texture: pn,
    AnimationMixer: Ts,
    AnimationClip: wo,
    VectorKeyframeTrack: Co,
    QuaternionKeyframeTrack: xo,
    NumberKeyframeTrack: yo,
    PerspectiveCamera: Xo,
    WebGLRenderer: Ju,
    AmbientLight: is,
    DirectionalLight: rs,
    Clock: Es,
    OrbitControls: ad,
    FBXLoader: cf,
    MathUtils: Yt,
    JSZip: Nf.default
  };

  const engine = window.RetargetAndIKEngine(THREE);
  const splicer = window.FBXBinarySplicer;
  const glbLoader = window.MinimalGLBLoader;
  const catalog = window.SEED_CATALOG;

  // 2. Application State
  const state = window.__weaponAnimLab = {
    THREE,
    engine,
    splicer,
    glbLoader,
    catalog,
    scene: null,
    camera: null,
    renderer: null,
    controls: null,
    clock: null,

    // Character state
    charName: 'mannequin',
    charFbxBuffer: null,
    charModel: null,
    charWrapper: null,
    charRigMap: null,
    charUnitScale: 1.0,
    fbxBoneMetaMap: {},

    // Animation catalog & playback
    animations: [],
    selectedAnimIds: new Set(),
    activeAnimId: null,
    retargetCtx: null,
    playing: true,
    currentTime: 0,
    duration: 1.0,
    playbackSpeed: 1.0,

    // Weapon state
    weapons: [],
    activeWeaponId: null,
    activeWeaponData: null, // { id, name, type, positions, normals, uvs, indices, color, textureDataUrl, pngBytes }
    weaponMesh: null,
    weaponAlignResult: null,
    weaponPresets: {},

    // Gizmo & Visual Helpers
    gizmoMode: 'orbit', // 'orbit' | 'translate' | 'rotate' | 'foregrip'
    showSkeleton: true,
    showMarkers: true,
    skeletonLines: null,
    gripMarker: null,
    foregripMarker: null,
    ikChainLine: null,
    weaponAxesLine: null,

    // Weapon alignment manual parameters
    weaponParams: {
      handTarget: 'RightHand',
      gripMode: 'rifle',
      flipBarrel: false,
      flipUp: false,
      roll90: 0,
      yaw90: 0,
      scaleMultiplier: 1.0,
      offsetPos: [0, 0, 0],
      offsetRotDeg: [0, 0, 0],
      foregripOffset: [0, 0, 0]
    },

    // Retarget & IK parameters
    retargetParams: {
      inPlaceLock: 1.0,
      groundFeet: true,
      armSpreadDeg: 0,
      spineTwistDeg: 0,
      spinePitchDeg: 0,
      leftHandIkWeight: 1.0,
      elbowPoleAngleDeg: 0,
      rightHandGrip: 1.0,
      leftHandGrip: 1.0,
      bakeFps: 30
    }
  };

  const el = id => document.getElementById(id);
  let toastTimer = null;
  function showToast(msg, isError = false) {
    const t = el('toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.toggle('error', !!isError);
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('show'), 3600);
  }

  // 3. IndexedDB Persistence for Custom Animations & Weapon Presets
  const DB_NAME = 'DungeonDS_WeaponAnimLab_DB';
  const DB_VERSION = 1;
  function openLabDB() {
    return new Promise((resolve, reject) => {
      if (typeof indexedDB === 'undefined') return resolve(null);
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = e => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains('animations')) db.createObjectStore('animations', { keyPath: 'id' });
        if (!db.objectStoreNames.contains('weapons')) db.createObjectStore('weapons', { keyPath: 'id' });
        if (!db.objectStoreNames.contains('presets')) db.createObjectStore('presets', { keyPath: 'id' });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
    });
  }

  async function saveToDB(storeName, item) {
    const db = await openLabDB();
    if (!db) return;
    return new Promise(resolve => {
      const tx = db.transaction(storeName, 'readwrite');
      tx.objectStore(storeName).put(item);
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => resolve(false);
    });
  }

  async function loadAllFromDB(storeName) {
    const db = await openLabDB();
    if (!db) return [];
    return new Promise(resolve => {
      const tx = db.transaction(storeName, 'readonly');
      const req = tx.objectStore(storeName).getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });
  }

  // 4. Initialize Three.js Viewport
  function initViewport() {
    const canvas = el('viewportCanvas');
    const wrap = el('canvasWrap');
    const w = wrap.clientWidth || 800;
    const h = wrap.clientHeight || 600;

    state.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
      preserveDrawingBuffer: true
    });
    state.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    state.renderer.setSize(w, h, false);
    state.renderer.setClearColor(0x090b10, 1);
    state.renderer.shadowMap.enabled = true;
    state.renderer.shadowMap.type = 2;
    state.renderer.outputColorSpace = ot;
    state.renderer.toneMapping = 6;
    state.renderer.toneMappingExposure = 1.05;

    state.scene = new THREE.Scene();
    state.camera = new THREE.PerspectiveCamera(35, w / h, 0.05, 500);
    state.camera.position.set(2.4, 1.8, 2.6);

    state.controls = new THREE.OrbitControls(state.camera, canvas);
    state.controls.enableDamping = true;
    state.controls.dampingFactor = 0.1;
    state.controls.target.set(0, 0.9, 0);
    state.controls.update();

    state.clock = new THREE.Clock();

    // Lighting (DungeonDS warm key + cool fill + rim)
    const amb = new THREE.AmbientLight(0xffffff, 0.65);
    state.scene.add(amb);

    const key = new THREE.DirectionalLight(0xffe2b5, 3.8);
    key.position.set(4, 7, 5);
    key.castShadow = true;
    state.scene.add(key);

    const fill = new THREE.DirectionalLight(0x9bb8ff, 1.4);
    fill.position.set(-5, 4, -3);
    state.scene.add(fill);

    const rim = new THREE.DirectionalLight(0xcce7ff, 1.1);
    rim.position.set(0, 5, -6);
    state.scene.add(rim);

    // Floor Grid at Y = 0
    buildFloorGrid();
    buildVisualMarkers();
    setupDirectViewportGizmo(canvas);

    window.addEventListener('resize', onResize);
  }

  function buildFloorGrid() {
    state.floorGridGroup = new THREE.Group();
    const pts = [];
    const size = 3.0;
    const step = 0.25;
    for (let i = -size; i <= size + 0.001; i += step) {
      pts.push(i, 0, -size, i, 0, size);
      pts.push(-size, 0, i, size, 0, i);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    const mat = new THREE.LineBasicMaterial({ color: 0x222b3d, transparent: true, opacity: 0.7 });
    const grid = new THREE.Line(geo, mat);
    state.floorGridGroup.add(grid);

    // Origin cross X (Red) and Z (Blue) at Y = 0.002
    const xGeo = new THREE.BufferGeometry();
    xGeo.setAttribute('position', new THREE.Float32BufferAttribute([-size, 0.002, 0, size, 0.002, 0], 3));
    state.floorGridGroup.add(new THREE.Line(xGeo, new THREE.LineBasicMaterial({ color: 0x993333 })));

    const zGeo = new THREE.BufferGeometry();
    zGeo.setAttribute('position', new THREE.Float32BufferAttribute([0, 0.002, -size, 0, 0.002, size], 3));
    state.floorGridGroup.add(new THREE.Line(zGeo, new THREE.LineBasicMaterial({ color: 0x335599 })));
    state.scene.add(state.floorGridGroup);
  }

  function createOctaMarker(radius, colorHex) {
    const r = radius;
    const pos = [
       r,0,0,  0,r,0,  0,0,r,
       0,r,0, -r,0,0,  0,0,r,
      -r,0,0,  0,-r,0, 0,0,r,
       0,-r,0, r,0,0,  0,0,r,
       0,r,0,  r,0,0,  0,0,-r,
      -r,0,0,  0,r,0,  0,0,-r,
       0,-r,0,-r,0,0,  0,0,-r,
       r,0,0,  0,-r,0, 0,0,-r
    ];
    const norms = new Float32Array(pos.length);
    for (let i = 0; i < pos.length; i += 3) {
      const l = Math.hypot(pos[i], pos[i + 1], pos[i + 2]) || 1;
      norms[i] = pos[i] / l; norms[i + 1] = pos[i + 1] / l; norms[i + 2] = pos[i + 2] / l;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute('normal', new THREE.Float32BufferAttribute(norms, 3));
    const mat = new THREE.MeshBasicMaterial({ color: colorHex, depthTest: false, transparent: true, opacity: 0.9 });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.renderOrder = 999;
    return mesh;
  }

  function buildVisualMarkers() {
    state.gripMarker = createOctaMarker(0.035, 0xf5a623); // Orange right-hand grip pivot
    state.foregripMarker = createOctaMarker(0.04, 0x2ecc71); // Green left-hand IK target
    state.scene.add(state.gripMarker);
    state.scene.add(state.foregripMarker);

    const ikGeo = new THREE.BufferGeometry();
    ikGeo.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(12), 3));
    state.ikChainLine = new THREE.Line(
      ikGeo,
      new THREE.LineBasicMaterial({ color: 0x2ecc71, depthTest: false, transparent: true, opacity: 0.85 })
    );
    state.ikChainLine.renderOrder = 998;
    state.scene.add(state.ikChainLine);

    const skelGeo = new THREE.BufferGeometry();
    skelGeo.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(300 * 3), 3));
    state.skeletonLines = new THREE.Line(
      skelGeo,
      new THREE.LineBasicMaterial({ color: 0x4c8dff, depthTest: false, transparent: true, opacity: 0.45 })
    );
    state.skeletonLines.renderOrder = 990;
    state.scene.add(state.skeletonLines);
  }

  function onResize() {
    if (!state.renderer || !state.camera) return;
    const wrap = el('canvasWrap');
    const w = wrap.clientWidth || 800;
    const h = wrap.clientHeight || 600;
    state.camera.aspect = w / h;
    state.camera.updateProjectionMatrix();
    state.renderer.setSize(w, h, false);
  }

  // 5. Direct 3D Viewport Manipulation (Translate Weapon / Rotate Weapon / Move Foregrip IK)
  function setupDirectViewportGizmo(canvas) {
    let dragging = false;
    let lastX = 0, lastY = 0;

    canvas.addEventListener('pointerdown', e => {
      if (state.gizmoMode === 'orbit' || e.button !== 0) return;
      dragging = true;
      lastX = e.clientX;
      lastY = e.clientY;
      state.controls.enabled = false;
      canvas.setPointerCapture(e.pointerId);
    });

    canvas.addEventListener('pointermove', e => {
      if (!dragging) return;
      const dx = e.clientX - lastX;
      const dy = e.clientY - lastY;
      lastX = e.clientX;
      lastY = e.clientY;

      const scaleRef = 0.002;

      if (state.gizmoMode === 'translate') {
        state.weaponParams.offsetPos[0] = clamp(state.weaponParams.offsetPos[0] + dx * scaleRef, -0.5, 0.5);
        state.weaponParams.offsetPos[1] = clamp(state.weaponParams.offsetPos[1] - dy * scaleRef, -0.5, 0.5);
        syncWeaponControlsUI();
        updateWeaponAttachment();
      } else if (state.gizmoMode === 'rotate') {
        state.weaponParams.offsetRotDeg[1] = clampAngle(state.weaponParams.offsetRotDeg[1] + dx * 0.6);
        state.weaponParams.offsetRotDeg[0] = clampAngle(state.weaponParams.offsetRotDeg[0] + dy * 0.6);
        syncWeaponControlsUI();
        updateWeaponAttachment();
      } else if (state.gizmoMode === 'foregrip') {
        state.weaponParams.foregripOffset[0] = clamp(state.weaponParams.foregripOffset[0] + dx * scaleRef, -0.4, 0.4);
        state.weaponParams.foregripOffset[1] = clamp(state.weaponParams.foregripOffset[1] - dy * scaleRef, -0.3, 0.3);
        syncIkControlsUI();
        updateWeaponAttachment();
      }
      evaluateCurrentFrame();
    });

    const stopDrag = e => {
      if (!dragging) return;
      dragging = false;
      state.controls.enabled = true;
      try { canvas.releasePointerCapture(e.pointerId); } catch (_) {}
    };
    canvas.addEventListener('pointerup', stopDrag);
    canvas.addEventListener('pointercancel', stopDrag);

    window.addEventListener('keydown', e => {
      if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT')) return;
      const k = e.key.toLowerCase();
      if (k === 'g') setGizmoMode('translate');
      else if (k === 'r') setGizmoMode('rotate');
      else if (k === 'f') setGizmoMode('foregrip');
      else if (k === 'escape') setGizmoMode('orbit');
      else if (k === ' ') {
        e.preventDefault();
        togglePlayPause();
      }
    });
  }

  function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }
  function clampAngle(a) {
    while (a > 180) a -= 360;
    while (a < -180) a += 360;
    return Math.round(a);
  }

  function setGizmoMode(mode) {
    state.gizmoMode = mode;
    document.querySelectorAll('[data-gizmo]').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-gizmo') === mode);
    });
  }

  // 6. Character Loading & Rig Mapping
  async function loadCharacterFromBuffer(arrayBuffer, fileName = 'character.fbx') {
    try {
      const model = new THREE.FBXLoader().parse(arrayBuffer.slice(0), '');
      const parsedFbx = splicer.parseFBXBinary(arrayBuffer);

      if (state.charWrapper) {
        state.scene.remove(state.charWrapper);
        state.charWrapper = null;
      }

      // Normalize display wrapper in scene while keeping internal model coordinates intact for accurate FBX baking
      model.updateWorldMatrix(true, true);
      const rawBox = new THREE.Box3().setFromObject(model);
      const rawSize = new THREE.Vector3();
      rawBox.getSize(rawSize);
      const rawHeight = rawSize.y || 1.8;

      // Map humanoid skeleton on the character model
      const rigMap = engine.mapHumanoidSkeleton(model);

      // Build FBX bone metadata map from parsedFbx + Three.js Bone userData
      const fbxBoneMetaMap = {};
      model.traverse(node => {
        if (node.isBone) {
          const origName = node.userData?.originalName || node.name;
          const td = node.userData?.transformData || {};
          const fbxBone = parsedFbx.bonesByName.get(origName) || parsedFbx.modelsById.get(BigInt(node.ID || 0));
          fbxBoneMetaMap[origName] = {
            nodeId: fbxBone ? fbxBone.id : (node.ID !== undefined ? BigInt(node.ID) : null),
            preRotation: td.preRotation || (fbxBone ? fbxBone.preRotation : null),
            postRotation: td.postRotation || (fbxBone ? fbxBone.postRotation : null),
            eulerOrder: td.eulerOrder || 'ZYX'
          };
        }
        if (node.isMesh) {
          node.frustumCulled = false;
          node.castShadow = true;
          node.receiveShadow = true;
          const mats = Array.isArray(node.material) ? node.material : [node.material];
          mats.forEach(m => {
            if (!m) return;
            m.side = 0;
            if (m.map) m.map.colorSpace = ot;
            if (m.normalMap && m.normalScale) m.normalScale.setScalar(0.35);
          });
        }
      });

      const wrapper = new THREE.Group();
      wrapper.scale.setScalar(1.0);
      wrapper.add(model);
      state.scene.add(wrapper);

      const envScale = Math.max(0.05, (rigMap.charHeight || rawHeight) / 1.8);
      if (state.floorGridGroup) state.floorGridGroup.scale.setScalar(envScale);
      if (state.gripMarker) state.gripMarker.scale.setScalar(envScale);
      if (state.foregripMarker) state.foregripMarker.scale.setScalar(envScale);

      state.charName = fileName.replace(/\.fbx$/i, '').replace(/[^a-z0-9_-]+/gi, '_');
      state.charFbxBuffer = arrayBuffer;
      state.charModel = model;
      state.charWrapper = wrapper;
      state.charRigMap = rigMap;
      state.charUnitScale = 1.0;
      state.fbxBoneMetaMap = fbxBoneMetaMap;

      const prefixInput = el('exportPrefixInput');
      if (prefixInput) prefixInput.value = state.charName;

      // Extract any animations embedded inside the character FBX itself
      state.animations = state.animations.filter(a => a.category !== 'Character');
      if (model.animations && model.animations.length > 0) {
        model.animations.forEach((clip, idx) => {
          const embeddedAnim = extractCompactAnimFromLoadedModel(model, clip, `char_anim_${idx}`, 'Character');
          if (embeddedAnim) state.animations.unshift(embeddedAnim);
        });
      }

      // Update UI badges & metadata
      const boneCount = Object.keys(rigMap.bones).length;
      const hasFingers = !!(rigMap.bones.RightHandIndex1 || rigMap.bones.LeftHandIndex1);
      el('charBoneCountBadge').textContent = `${boneCount} huesos mapeados`;
      el('statusRig').textContent = `Personaje: ${fileName} (${boneCount} huesos)`;
      el('charMetaBox').innerHTML =
        `<b>Archivo:</b> ${fileName} (${(arrayBuffer.byteLength / 1048576).toFixed(2)} MB)<br>` +
        `<b>Mano Der:</b> ${rigMap.canonicalToOriginalName.RightHand || '—'} · <b>Mano Izq:</b> ${rigMap.canonicalToOriginalName.LeftHand || '—'}<br>` +
        `<b>Dedos:</b> ${hasFingers ? 'Sí (Grip activo)' : 'No (Sin falanges)'} · <b>Altura:</b> ${rigMap.charHeight.toFixed(2)} u`;

      el('btnExportCurrentFbx').disabled = false;
      el('btnExportMultiClipFbx').disabled = false;
      el('btnExportBatchZip').disabled = false;

      // Re-attach weapon and re-prepare active animation
      if (state.activeWeaponData) {
        attachWeaponDataToCharacter(state.activeWeaponData, false);
      } else if (state.weapons.length > 0) {
        selectWeaponById(state.weapons[0].id);
      }

      renderAnimCatalogUI();
      if (state.activeAnimId) {
        selectAnimationById(state.activeAnimId);
      } else if (state.animations.length > 0) {
        selectAnimationById(state.animations[0].id);
      }

      fitCameraToCharacter();
      showToast(`Personaje cargado: ${fileName} (${boneCount} huesos)`);
      return true;
    } catch (err) {
      console.error(err);
      showToast(`Error cargando personaje FBX: ${err.message}`, true);
      return false;
    }
  }

  window.__labLoadCharacterFromBuffer = loadCharacterFromBuffer;

  function fitCameraToCharacter() {
    if (!state.charWrapper || !state.camera || !state.controls) return;
    const H = state.charRigMap ? Math.max(0.2, state.charRigMap.charHeight) : 1.8;
    state.camera.near = Math.max(0.01, H * 0.005);
    state.camera.far = Math.max(500, H * 60);
    state.camera.updateProjectionMatrix();
    state.controls.target.set(0, H * 0.48, 0);
    state.camera.position.set(H * 1.15, H * 0.78, H * 1.30);
    state.camera.lookAt(state.controls.target);
    state.controls.update();
  }

  // 7. Extract Compact Animation from Any Mixamo / Character FBX
  function extractCompactAnimFromLoadedModel(model, clip, id, category = 'Custom') {
    if (!clip) return null;
    const fps = 24;
    const duration = Math.max(0.05, clip.duration || 1.0);
    const numFrames = Math.max(2, Math.round(duration * fps));

    // Save current pose
    const savedPos = new Map();
    const savedQuat = new Map();
    const bones = [];
    const boneRestPose = {};
    let hipsRestPosition = [0, 1, 0];
    const tmpQ = new THREE.Quaternion();
    const tmpV = new THREE.Vector3();

    model.updateWorldMatrix(true, true);
    model.traverse(node => {
      if (node.isBone) {
        bones.push(node);
        savedPos.set(node, node.position.clone());
        savedQuat.set(node, node.quaternion.clone());
        const canon = engine.normalizeCanonicalBoneName(node.name);
        if (!canon) return;
        const isRoot = canon === 'Hips' || !node.parent?.isBone;
        if (isRoot) {
          node.getWorldQuaternion(tmpQ);
          node.getWorldPosition(tmpV);
          boneRestPose[canon] = [tmpQ.x, tmpQ.y, tmpQ.z, tmpQ.w];
          hipsRestPosition = [tmpV.x, tmpV.y, tmpV.z];
        } else {
          boneRestPose[canon] = [node.quaternion.x, node.quaternion.y, node.quaternion.z, node.quaternion.w];
        }
      }
    });

    const mixer = new THREE.AnimationMixer(model);
    const action = mixer.clipAction(clip);
    action.play();

    const boneTracks = {};
    for (const b of bones) {
      const canon = engine.normalizeCanonicalBoneName(b.name);
      if (!canon) continue;
      const isRoot = canon === 'Hips' || !b.parent?.isBone;
      boneTracks[canon] = {
        canon,
        rawName: b.name,
        isRoot,
        rot: [],
        pos: isRoot ? [] : null
      };
    }

    for (let f = 0; f < numFrames; f++) {
      const t = (f / (numFrames - 1)) * duration;
      mixer.setTime(t);
      model.updateWorldMatrix(true, true);
      for (const b of bones) {
        const canon = engine.normalizeCanonicalBoneName(b.name);
        const trk = canon ? boneTracks[canon] : null;
        if (!trk) continue;
        if (trk.isRoot) {
          b.getWorldQuaternion(tmpQ);
          b.getWorldPosition(tmpV);
          trk.rot.push(Number(tmpQ.x.toFixed(4)), Number(tmpQ.y.toFixed(4)), Number(tmpQ.z.toFixed(4)), Number(tmpQ.w.toFixed(4)));
          trk.pos.push(Number(tmpV.x.toFixed(4)), Number(tmpV.y.toFixed(4)), Number(tmpV.z.toFixed(4)));
        } else {
          const q = b.quaternion;
          trk.rot.push(Number(q.x.toFixed(4)), Number(q.y.toFixed(4)), Number(q.z.toFixed(4)), Number(q.w.toFixed(4)));
        }
      }
    }

    mixer.stopAllAction();
    mixer.uncacheRoot(model);

    // Restore rest pose
    for (const b of bones) {
      if (savedPos.has(b)) b.position.copy(savedPos.get(b));
      if (savedQuat.has(b)) b.quaternion.copy(savedQuat.get(b));
    }
    model.updateWorldMatrix(true, true);

    const tracks = [];
    for (const tr of Object.values(boneTracks)) {
      tracks.push({ bone: tr.canon, rawBone: tr.rawName, type: 'quaternion', values: tr.rot });
      if (tr.pos) tracks.push({ bone: tr.canon, rawBone: tr.rawName, type: 'position', values: tr.pos });
    }

    return {
      id,
      name: clip.name && clip.name !== 'mixamo.com' ? clip.name : id,
      category,
      duration: Number(duration.toFixed(3)),
      fps,
      numFrames,
      hipsRestPosition,
      boneRestPose,
      tracks
    };
  }

  // 8. Weapon Attachment, PCA Auto-Alignment & Live Update
  function selectWeaponById(weaponId) {
    if (!weaponId) {
      removeWeapon();
      return;
    }
    const wEntry = state.weapons.find(w => w.id === weaponId);
    if (!wEntry) return;

    let meshData;
    if (wEntry.positions && wEntry.normals) {
      meshData = wEntry;
    } else {
      meshData = catalog.getWeaponMeshData(weaponId);
    }

    let pngBytes = wEntry.pngBytes || null;
    if (!pngBytes && meshData.texture && meshData.texture.includes('base64,')) {
      const b64 = meshData.texture.split('base64,')[1];
      const bin = atob(b64);
      pngBytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) pngBytes[i] = bin.charCodeAt(i);
    }

    const weaponData = {
      id: wEntry.id,
      name: wEntry.name,
      type: wEntry.type || 'rifle',
      positions: meshData.positions,
      normals: meshData.normals,
      uvs: meshData.uvs,
      indices: new Uint32Array(meshData.indices),
      color: meshData.color || [0.75, 0.78, 0.82],
      textureDataUrl: meshData.texture || wEntry.texture || null,
      pngBytes
    };

    state.activeWeaponId = weaponId;
    state.weaponParams.gripMode = weaponData.type === 'sword' ? 'sword' : 'rifle';
    el('weaponGripMode').value = state.weaponParams.gripMode;

    // Load saved preset for this weapon if available, else reset to auto-PCA defaults
    const preset = state.weaponPresets[weaponId];
    if (preset) {
      Object.assign(state.weaponParams, JSON.parse(JSON.stringify(preset)));
    } else {
      resetWeaponManualOffsets(weaponData.type);
    }

    attachWeaponDataToCharacter(weaponData, true);
    renderWeaponCatalogUI();
  }

  function resetWeaponManualOffsets(weaponType = 'rifle') {
    state.weaponParams.flipBarrel = false;
    state.weaponParams.flipUp = false;
    state.weaponParams.roll90 = 0;
    state.weaponParams.yaw90 = 0;
    state.weaponParams.scaleMultiplier = 1.0;
    state.weaponParams.offsetPos = [0, 0, 0];
    state.weaponParams.offsetRotDeg = [0, 0, 0];
    state.weaponParams.foregripOffset = [0, 0, 0];

    const isTwoHanded = weaponType === 'rifle' || weaponType === 'heavy2h';
    state.retargetParams.leftHandIkWeight = isTwoHanded ? 1.0 : 0.0;
    el('leftHandIkWeight').value = String(state.retargetParams.leftHandIkWeight);
    syncWeaponControlsUI();
    syncIkControlsUI();
  }

  function attachWeaponDataToCharacter(weaponData, rebuildMesh = true) {
    state.activeWeaponData = weaponData;
    el('statusWeapon').textContent = `Arma: ${weaponData.name}`;
    el('weaponTypeBadge').textContent = weaponData.type === 'sword' ? 'Melee 1H/2H' : 'Rifle 2H';

    if (rebuildMesh || !state.weaponMesh) {
      if (state.weaponMesh && state.weaponMesh.parent) {
        state.weaponMesh.parent.remove(state.weaponMesh);
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.Float32BufferAttribute(weaponData.positions, 3));
      geo.setAttribute('normal', new THREE.Float32BufferAttribute(weaponData.normals, 3));
      if (weaponData.uvs && weaponData.uvs.length > 0) {
        geo.setAttribute('uv', new THREE.Float32BufferAttribute(weaponData.uvs, 2));
      }
      geo.setIndex(new THREE.Uint32BufferAttribute(weaponData.indices, 1));
      geo.computeBoundingBox();

      const mat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(weaponData.color[0], weaponData.color[1], weaponData.color[2]),
        roughness: 0.6,
        metalness: 0.25
      });

      if (weaponData.textureDataUrl) {
        const img = new Image();
        img.onload = () => {
          const tex = new THREE.Texture(img);
          tex.colorSpace = ot;
          tex.flipY = false;
          tex.needsUpdate = true;
          mat.map = tex;
          mat.color.setHex(0xffffff);
          mat.needsUpdate = true;
        };
        img.src = weaponData.textureDataUrl;
      }

      state.weaponMesh = new THREE.Mesh(geo, mat);
      state.weaponMesh.name = weaponData.name;
      state.weaponMesh.castShadow = true;
      state.weaponMesh.receiveShadow = true;
      state.weaponMesh.frustumCulled = false;
    }

    updateWeaponAttachment();
    evaluateCurrentFrame();
  }

  function updateWeaponAttachment() {
    if (!state.charRigMap || !state.activeWeaponData || !state.weaponMesh) return;
    const handKey = state.weaponParams.handTarget || 'RightHand';
    const handBone = state.charRigMap.bones[handKey] || state.charRigMap.bones.RightHand;
    if (!handBone) return;

    if (state.weaponMesh.parent !== handBone) {
      if (state.weaponMesh.parent) state.weaponMesh.parent.remove(state.weaponMesh);
      handBone.add(state.weaponMesh);
    }

    const rotDeg = [
      state.weaponParams.offsetRotDeg[0],
      state.weaponParams.offsetRotDeg[1] + (state.weaponParams.yaw90 || 0) * 90,
      state.weaponParams.offsetRotDeg[2]
    ];

    const alignRes = engine.autoAlignWeaponGeometry(state.activeWeaponData, state.charRigMap, {
      type: state.weaponParams.gripMode === 'sword' ? 'sword' : 'rifle',
      scaleMultiplier: state.weaponParams.scaleMultiplier,
      flipBarrel: state.weaponParams.flipBarrel,
      flipUp: state.weaponParams.flipUp,
      roll90: state.weaponParams.roll90,
      offsetPos: state.weaponParams.offsetPos,
      offsetRotDeg: rotDeg
    });

    // Apply foregrip user adjustment in weapon local space
    const fg = alignRes.foregripLocalPos.clone();
    const rawScale = alignRes.scaleFactor || 1.0;
    const unitScale = ((state.charRigMap.charHeight || 1.8) / 1.8) / rawScale;
    fg.x += (state.weaponParams.foregripOffset[2] || 0) * unitScale;
    fg.y += (state.weaponParams.foregripOffset[1] || 0) * unitScale;
    fg.z += (state.weaponParams.foregripOffset[0] || 0) * unitScale;
    alignRes.adjustedForegripLocalPos = fg;

    state.weaponAlignResult = alignRes;

    state.weaponMesh.matrixAutoUpdate = true;
    alignRes.localMatrix4.decompose(state.weaponMesh.position, state.weaponMesh.quaternion, state.weaponMesh.scale);
    state.weaponMesh.updateMatrix();
  }

  function removeWeapon() {
    if (state.weaponMesh && state.weaponMesh.parent) {
      state.weaponMesh.parent.remove(state.weaponMesh);
    }
    state.activeWeaponId = null;
    state.activeWeaponData = null;
    state.weaponAlignResult = null;
    el('statusWeapon').textContent = 'Arma: Ninguna';
    renderWeaponCatalogUI();
    evaluateCurrentFrame();
  }

  // 9. Animation Selection & Frame Evaluation
  function selectAnimationById(animId) {
    const anim = state.animations.find(a => a.id === animId);
    if (!anim) return;
    state.activeAnimId = animId;
    if (!state.selectedAnimIds.has(animId)) {
      state.selectedAnimIds.add(animId);
    }
    state.duration = anim.duration || 1.0;
    state.currentTime = 0;

    el('statusAnim').textContent = `Animación: ${anim.name} (${state.duration.toFixed(2)}s)`;
    el('timelineScrubber').max = String(state.duration);
    el('timelineScrubber').value = '0';

    if (state.charRigMap) {
      state.retargetCtx = engine.prepareAnimationRetarget(state.charRigMap, anim);
      evaluateCurrentFrame();
    }
    renderAnimCatalogUI();
  }

  function buildWeaponContext() {
    if (!state.activeWeaponData || !state.weaponAlignResult) return null;
    return {
      localMatrix4: state.weaponAlignResult.localMatrix4,
      foregripLocalPos: state.weaponAlignResult.adjustedForegripLocalPos || state.weaponAlignResult.foregripLocalPos,
      attachBoneName: state.weaponParams.handTarget || 'RightHand'
    };
  }

  function evaluateCurrentFrame() {
    if (!state.charRigMap || !state.retargetCtx) return;
    const weaponCtx = buildWeaponContext();
    engine.evaluateRetargetFrame(
      state.charRigMap,
      state.retargetCtx,
      state.currentTime,
      state.retargetParams,
      weaponCtx
    );
    if (state.charWrapper) state.charWrapper.updateWorldMatrix(true, true);
    updateVisualHelpers();
  }

  function updateVisualHelpers() {
    if (!state.charRigMap) return;
    const bones = state.charRigMap.bones;

    // 1. Skeleton lines
    state.skeletonLines.visible = state.showSkeleton;
    if (state.showSkeleton) {
      const posAttr = state.skeletonLines.geometry.attributes.position;
      const arr = posAttr.array;
      let ptr = 0;
      const vA = new THREE.Vector3();
      const vB = new THREE.Vector3();
      state.charModel.traverse(node => {
        if (node.isBone && node.parent && node.parent.isBone && ptr + 6 <= arr.length) {
          node.parent.getWorldPosition(vA);
          node.getWorldPosition(vB);
          arr[ptr++] = vA.x; arr[ptr++] = vA.y; arr[ptr++] = vA.z;
          arr[ptr++] = vB.x; arr[ptr++] = vB.y; arr[ptr++] = vB.z;
        }
      });
      for (let i = ptr; i < arr.length; i++) arr[i] = 0;
      posAttr.needsUpdate = true;
    }

    // 2. Grip & Foregrip IK Markers
    const showM = state.showMarkers && !!state.activeWeaponData && !!state.weaponAlignResult;
    state.gripMarker.visible = showM;
    state.foregripMarker.visible = showM;
    state.ikChainLine.visible = showM && state.retargetParams.leftHandIkWeight > 0.01;

    if (showM) {
      const handBone = bones[state.weaponParams.handTarget || 'RightHand'] || bones.RightHand;
      if (handBone) {
        const wMat = new THREE.Matrix4().multiplyMatrices(handBone.matrixWorld, state.weaponAlignResult.localMatrix4);
        const gripWorld = state.weaponAlignResult.gripPivotLocal.clone().applyMatrix4(wMat);
        const fgLocal = state.weaponAlignResult.adjustedForegripLocalPos || state.weaponAlignResult.foregripLocalPos;
        const fgWorld = fgLocal.clone().applyMatrix4(wMat);

        state.gripMarker.position.copy(gripWorld);
        state.foregripMarker.position.copy(fgWorld);

        if (bones.LeftArm && bones.LeftForeArm && bones.LeftHand) {
          const p0 = new THREE.Vector3(), p1 = new THREE.Vector3(), p2 = new THREE.Vector3();
          bones.LeftArm.getWorldPosition(p0);
          bones.LeftForeArm.getWorldPosition(p1);
          bones.LeftHand.getWorldPosition(p2);
          const ikArr = state.ikChainLine.geometry.attributes.position.array;
          ikArr[0] = p0.x; ikArr[1] = p0.y; ikArr[2] = p0.z;
          ikArr[3] = p1.x; ikArr[4] = p1.y; ikArr[5] = p1.z;
          ikArr[6] = p2.x; ikArr[7] = p2.y; ikArr[8] = p2.z;
          ikArr[9] = fgWorld.x; ikArr[10] = fgWorld.y; ikArr[11] = fgWorld.z;
          state.ikChainLine.geometry.attributes.position.needsUpdate = true;
        }
      }
    }
  }

  // 10. FBX Binary 7400 Baking & Splicing Exporter
  function buildWeaponSplicerPayload() {
    if (!state.activeWeaponData || !state.weaponAlignResult) return null;
    const w = state.activeWeaponData;
    const mat4 = state.weaponAlignResult.localMatrix4;
    const normMat = new THREE.Matrix3().getNormalMatrix(mat4);

    const posOut = new Float32Array(w.positions.length);
    const normOut = new Float32Array(w.normals.length);
    const v = new THREE.Vector3();

    for (let i = 0; i < w.positions.length; i += 3) {
      v.set(w.positions[i], w.positions[i + 1], w.positions[i + 2]).applyMatrix4(mat4);
      posOut[i] = v.x; posOut[i + 1] = v.y; posOut[i + 2] = v.z;

      v.set(w.normals[i], w.normals[i + 1], w.normals[i + 2]).applyMatrix3(normMat).normalize();
      normOut[i] = v.x; normOut[i + 1] = v.y; normOut[i + 2] = v.z;
    }

    return {
      name: w.name.replace(/[^a-zA-Z0-9_]/g, '_'),
      positions: posOut,
      normals: normOut,
      uvs: w.uvs,
      indices: new Uint32Array(w.indices),
      color: w.color,
      pngBytes: w.pngBytes
    };
  }

  function bakeSingleAnimForExport(animObj) {
    // Temporarily reset wrapper scale to 1.0 during baking so world positions match native character FBX units
    const prevScale = state.charWrapper ? state.charWrapper.scale.x : 1.0;
    if (state.charWrapper) {
      state.charWrapper.scale.setScalar(1.0);
      state.charWrapper.updateWorldMatrix(true, true);
    }

    // Re-capture rig map in unscaled model space for exact native unit baking
    const savedTime = state.currentTime;
    const retargetCtx = engine.prepareAnimationRetarget(state.charRigMap, animObj);
    const weaponCtx = buildWeaponContext();

    const baked = engine.bakeClipToFBXTracks(
      state.charRigMap,
      retargetCtx,
      state.retargetParams,
      weaponCtx,
      state.fbxBoneMetaMap
    );

    if (state.charWrapper) {
      state.charWrapper.scale.setScalar(prevScale);
      state.charWrapper.updateWorldMatrix(true, true);
    }
    state.currentTime = savedTime;
    evaluateCurrentFrame();

    return {
      name: animObj.name || animObj.id,
      duration: baked.duration,
      times: Array.from(baked.times),
      tracks: baked.splicerTracks
    };
  }

  function exportFbxWithAnimations(animList, downloadFileName) {
    if (!state.charFbxBuffer || !state.charRigMap) {
      showToast('Carga un personaje .FBX primero', true);
      return null;
    }

    const handKey = state.weaponParams.handTarget || 'RightHand';
    const handBone = state.charRigMap.bones[handKey] || state.charRigMap.bones.RightHand;
    const origHandName = state.charRigMap.canonicalToOriginalName[handKey] || handBone?.userData?.originalName || handBone?.name;
    const handMeta = state.fbxBoneMetaMap[origHandName] || {};
    const parentBoneId = handMeta.nodeId !== undefined && handMeta.nodeId !== null
      ? BigInt(handMeta.nodeId)
      : (handBone && handBone.ID !== undefined ? BigInt(handBone.ID) : null);

    const weaponPayload = buildWeaponSplicerPayload();
    const bakedClips = animList.map(a => bakeSingleAnimForExport(a));

    const exportedBuffer = splicer.spliceAndExportFBX(state.charFbxBuffer, {
      parentBoneId,
      weapon: weaponPayload,
      clips: bakedClips
    });

    window.__lastExportedFbxBuffer = exportedBuffer;
    window.__lastExportedFbxName = downloadFileName;

    if (downloadFileName) {
      const blob = new Blob([exportedBuffer], { type: 'application/octet-stream' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = downloadFileName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    }

    return exportedBuffer;
  }

  window.__labExportCurrentFbxBuffer = function () {
    const activeAnim = state.animations.find(a => a.id === state.activeAnimId) || state.animations[0];
    if (!activeAnim) return null;
    const prefix = (el('exportPrefixInput').value || state.charName || 'character').trim();
    const wTag = state.activeWeaponData ? `_${state.activeWeaponData.id}` : '';
    const fileName = `${prefix}${wTag}_${activeAnim.id}.fbx`;
    return exportFbxWithAnimations([activeAnim], fileName);
  };

  // 11. UI Rendering & Event Wiring
  function renderAnimCatalogUI() {
    const listEl = el('animCatalogList');
    const filter = el('animCategoryFilter').value;
    listEl.innerHTML = '';

    const visible = state.animations.filter(a => filter === 'ALL' || a.category === filter);
    el('animCountBadge').textContent = `${visible.length} clips`;

    visible.forEach(anim => {
      const row = document.createElement('div');
      row.className = 'catalog-item' + (anim.id === state.activeAnimId ? ' active' : '');

      const left = document.createElement('div');
      left.className = 'catalog-item-left';

      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = state.selectedAnimIds.has(anim.id);
      cb.addEventListener('click', e => {
        e.stopPropagation();
        if (cb.checked) state.selectedAnimIds.add(anim.id);
        else state.selectedAnimIds.delete(anim.id);
      });

      const title = document.createElement('span');
      title.className = 'catalog-item-name';
      title.textContent = anim.name;

      left.appendChild(cb);
      left.appendChild(title);

      const tag = document.createElement('span');
      tag.className = 'catalog-tag';
      tag.textContent = `${anim.category} · ${Number(anim.duration).toFixed(1)}s`;

      row.appendChild(left);
      row.appendChild(tag);

      row.addEventListener('click', () => selectAnimationById(anim.id));
      listEl.appendChild(row);
    });
  }

  function renderWeaponCatalogUI() {
    const listEl = el('weaponCatalogList');
    listEl.innerHTML = '';

    state.weapons.forEach(w => {
      const row = document.createElement('div');
      row.className = 'catalog-item' + (w.id === state.activeWeaponId ? ' active' : '');

      const left = document.createElement('div');
      left.className = 'catalog-item-left';
      const title = document.createElement('span');
      title.className = 'catalog-item-name';
      title.textContent = w.name;
      left.appendChild(title);

      const tag = document.createElement('span');
      tag.className = 'catalog-tag';
      tag.textContent = w.type === 'sword' ? 'Melee' : 'Rifle';

      row.appendChild(left);
      row.appendChild(tag);
      row.addEventListener('click', () => selectWeaponById(w.id));
      listEl.appendChild(row);
    });
  }

  function syncWeaponControlsUI() {
    el('weaponScale').value = String(state.weaponParams.scaleMultiplier);
    el('valWeaponScale').textContent = state.weaponParams.scaleMultiplier.toFixed(2) + '×';

    el('weaponPosX').value = String(state.weaponParams.offsetPos[0]);
    el('valWPosX').textContent = state.weaponParams.offsetPos[0].toFixed(2);
    el('weaponPosY').value = String(state.weaponParams.offsetPos[1]);
    el('valWPosY').textContent = state.weaponParams.offsetPos[1].toFixed(2);
    el('weaponPosZ').value = String(state.weaponParams.offsetPos[2]);
    el('valWPosZ').textContent = state.weaponParams.offsetPos[2].toFixed(2);

    el('weaponRotX').value = String(state.weaponParams.offsetRotDeg[0]);
    el('valWRotX').textContent = Math.round(state.weaponParams.offsetRotDeg[0]) + '°';
    el('weaponRotY').value = String(state.weaponParams.offsetRotDeg[1]);
    el('valWRotY').textContent = Math.round(state.weaponParams.offsetRotDeg[1]) + '°';
    el('weaponRotZ').value = String(state.weaponParams.offsetRotDeg[2]);
    el('valWRotZ').textContent = Math.round(state.weaponParams.offsetRotDeg[2]) + '°';
  }

  function syncIkControlsUI() {
    const ikW = state.retargetParams.leftHandIkWeight;
    el('leftHandIkWeight').value = String(ikW);
    el('valLeftIk').textContent = Math.round(ikW * 100) + '%';
    el('ikStatusBadge').textContent = ikW > 0.01 ? 'IK Activo' : 'FK Puro';

    el('foregripX').value = String(state.weaponParams.foregripOffset[0]);
    el('valFgX').textContent = state.weaponParams.foregripOffset[0].toFixed(2);
    el('foregripY').value = String(state.weaponParams.foregripOffset[1]);
    el('valFgY').textContent = state.weaponParams.foregripOffset[1].toFixed(2);
    el('foregripZ').value = String(state.weaponParams.foregripOffset[2]);
    el('valFgZ').textContent = state.weaponParams.foregripOffset[2].toFixed(2);
  }

  function togglePlayPause() {
    state.playing = !state.playing;
    el('btnPlayPause').textContent = state.playing ? '⏸ Pausa' : '▶ Play';
  }

  function wireUIEvents() {
    // Character Dropzone & File Input
    const charDrop = el('charDropzone');
    const charInput = el('charFileInput');
    charDrop.addEventListener('click', () => charInput.click());
    ['dragover', 'dragenter'].forEach(ev => charDrop.addEventListener(ev, e => {
      e.preventDefault();
      charDrop.classList.add('dragover');
    }));
    ['dragleave', 'drop'].forEach(ev => charDrop.addEventListener(ev, e => {
      e.preventDefault();
      charDrop.classList.remove('dragover');
    }));
    charDrop.addEventListener('drop', async e => {
      const f = e.dataTransfer?.files?.[0];
      if (f) {
        const buf = await f.arrayBuffer();
        await loadCharacterFromBuffer(buf, f.name);
      }
    });
    charInput.addEventListener('change', async () => {
      const f = charInput.files?.[0];
      if (f) {
        const buf = await f.arrayBuffer();
        await loadCharacterFromBuffer(buf, f.name);
      }
    });

    // Animation filter & multi-selection
    el('animCategoryFilter').addEventListener('change', renderAnimCatalogUI);
    el('btnSelectAllAnims').addEventListener('click', () => {
      const filter = el('animCategoryFilter').value;
      state.animations.forEach(a => {
        if (filter === 'ALL' || a.category === filter) state.selectedAnimIds.add(a.id);
      });
      renderAnimCatalogUI();
    });
    el('btnClearAnims').addEventListener('click', () => {
      state.selectedAnimIds.clear();
      renderAnimCatalogUI();
    });

    // Batch import Mixamo FBX animations
    const mixamoInput = el('mixamoFilesInput');
    el('btnImportMixamoFbx').addEventListener('click', () => mixamoInput.click());
    mixamoInput.addEventListener('change', async () => {
      const files = Array.from(mixamoInput.files || []);
      let added = 0;
      for (const f of files) {
        try {
          const buf = await f.arrayBuffer();
          const m = new THREE.FBXLoader().parse(buf, '');
          if (m.animations && m.animations.length > 0) {
            const baseName = f.name.replace(/\.fbx$/i, '');
            const id = 'mixamo_' + baseName.toLowerCase().replace(/[^a-z0-9]+/g, '_') + '_' + Date.now().toString(36).slice(-3);
            const extracted = extractCompactAnimFromLoadedModel(m, m.animations[0], id, 'Custom');
            if (extracted) {
              extracted.name = baseName;
              state.animations.push(extracted);
              state.selectedAnimIds.add(extracted.id);
              await saveToDB('animations', extracted);
              added++;
            }
          }
        } catch (err) {
          console.warn('Error importando FBX de animación:', f.name, err);
        }
      }
      renderAnimCatalogUI();
      if (added > 0) {
        selectAnimationById(state.animations[state.animations.length - 1].id);
        showToast(`${added} animación(es) Mixamo añadidas a la librería local`);
      }
    });

    // Export / Import Animation Library Pack JSON
    el('btnExportAnimLibrary').addEventListener('click', () => {
      const customAnims = state.animations.filter(a => a.category === 'Custom');
      const payload = {
        version: 1,
        exportedAt: new Date().toISOString(),
        animations: customAnims.length ? customAnims : state.animations,
        weaponPresets: state.weaponPresets
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'dungeonds_anim_weapon_library_pack.json';
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 3000);
      showToast('Pack de librería JSON exportado');
    });

    const packInput = el('animPackInput');
    el('btnImportAnimLibrary').addEventListener('click', () => packInput.click());
    packInput.addEventListener('change', async () => {
      const f = packInput.files?.[0];
      if (!f) return;
      try {
        const data = JSON.parse(await f.text());
        if (Array.isArray(data.animations)) {
          for (const anim of data.animations) {
            if (!state.animations.some(x => x.id === anim.id)) {
              state.animations.push(anim);
              await saveToDB('animations', anim);
            }
          }
        }
        if (data.weaponPresets) {
          Object.assign(state.weaponPresets, data.weaponPresets);
        }
        renderAnimCatalogUI();
        showToast('Pack de librería cargado correctamente');
      } catch (err) {
        showToast('Error al leer el pack JSON: ' + err.message, true);
      }
    });

    // Weapon upload (.FBX / .GLB) & removal
    const weaponInput = el('weaponFileInput');
    el('btnUploadWeapon').addEventListener('click', () => weaponInput.click());
    el('btnRemoveWeapon').addEventListener('click', removeWeapon);

    weaponInput.addEventListener('change', async () => {
      const f = weaponInput.files?.[0];
      if (!f) return;
      try {
        const buf = await f.arrayBuffer();
        const ext = f.name.split('.').pop().toLowerCase();
        const wId = 'custom_' + f.name.replace(/\.[^.]+$/, '').toLowerCase().replace(/[^a-z0-9]+/g, '_');
        let meshData;
        let pngBytes = null;
        let textureDataUrl = null;

        if (ext === 'glb' || ext === 'gltf') {
          meshData = glbLoader.parseGLBToMeshData(buf);
          if (meshData.imageBytes) {
            pngBytes = meshData.imageBytes;
            const b64 = btoa(String.fromCharCode(...new Uint8Array(pngBytes)));
            textureDataUrl = `data:${meshData.mimeType || 'image/png'};base64,${b64}`;
          }
        } else if (ext === 'fbx') {
          const wModel = new THREE.FBXLoader().parse(buf, '');
          wModel.updateWorldMatrix(true, true);
          const posArr = [], normArr = [], uvArr = [], idxArr = [];
          let vOffset = 0;
          let color = [0.75, 0.78, 0.82];
          wModel.traverse(n => {
            if (n.isMesh && n.geometry?.attributes?.position) {
              const g = n.geometry;
              const p = g.attributes.position;
              const nm = g.attributes.normal;
              const uv = g.attributes.uv;
              const v = new THREE.Vector3();
              const normalMat = new THREE.Matrix3().getNormalMatrix(n.matrixWorld);
              for (let i = 0; i < p.count; i++) {
                v.fromBufferAttribute(p, i).applyMatrix4(n.matrixWorld);
                posArr.push(v.x, v.y, v.z);
                if (nm) {
                  v.fromBufferAttribute(nm, i).applyMatrix3(normalMat).normalize();
                  normArr.push(v.x, v.y, v.z);
                } else {
                  normArr.push(0, 1, 0);
                }
                if (uv) {
                  uvArr.push(uv.getX(i), uv.getY(i));
                } else {
                  uvArr.push(0, 0);
                }
                idxArr.push(vOffset + i);
              }
              vOffset += p.count;
              const mat = Array.isArray(n.material) ? n.material[0] : n.material;
              if (mat && mat.color) color = [mat.color.r, mat.color.g, mat.color.b];
            }
          });
          meshData = {
            positions: new Float32Array(posArr),
            normals: new Float32Array(normArr),
            uvs: new Float32Array(uvArr),
            indices: new Uint32Array(idxArr),
            color
          };
        }

        const newW = {
          id: wId,
          name: f.name.replace(/\.[^.]+$/, ''),
          type: state.weaponParams.gripMode === 'sword' ? 'sword' : 'rifle',
          positions: meshData.positions,
          normals: meshData.normals,
          uvs: meshData.uvs,
          indices: meshData.indices,
          color: meshData.color || [0.75, 0.78, 0.82],
          texture: textureDataUrl,
          pngBytes
        };

        state.weapons = state.weapons.filter(x => x.id !== wId);
        state.weapons.unshift(newW);
        selectWeaponById(wId);
        showToast(`Arma cargada y auto-alineada: ${newW.name}`);
      } catch (err) {
        console.error(err);
        showToast(`Error al cargar arma: ${err.message}`, true);
      }
    });

    // Weapon Hand & Grip Mode
    el('weaponHandTarget').addEventListener('change', e => {
      state.weaponParams.handTarget = e.target.value;
      updateWeaponAttachment();
      evaluateCurrentFrame();
    });
    el('weaponGripMode').addEventListener('change', e => {
      state.weaponParams.gripMode = e.target.value;
      const is2H = e.target.value === 'rifle' || e.target.value === 'heavy2h';
      state.retargetParams.leftHandIkWeight = is2H ? 1.0 : 0.0;
      syncIkControlsUI();
      updateWeaponAttachment();
      evaluateCurrentFrame();
    });

    // Toolbar Gizmo Buttons
    document.querySelectorAll('[data-gizmo]').forEach(btn => {
      btn.addEventListener('click', () => setGizmoMode(btn.getAttribute('data-gizmo')));
    });
    el('btnToggleSkeleton').addEventListener('click', e => {
      state.showSkeleton = !state.showSkeleton;
      e.currentTarget.classList.toggle('active', state.showSkeleton);
      updateVisualHelpers();
    });
    el('btnToggleMarkers').addEventListener('click', e => {
      state.showMarkers = !state.showMarkers;
      e.currentTarget.classList.toggle('active', state.showMarkers);
      updateVisualHelpers();
    });
    el('cameraFacingSelect').addEventListener('change', e => {
      const val = e.target.value;
      if (val === 'free') return;
      const dirIdx = parseInt(val, 10);
      const angle = dirIdx * (Math.PI / 4);
      const H = state.charRigMap ? Math.max(0.2, state.charRigMap.charHeight) : 1.8;
      const dist = H * 1.65;
      const elev = 30 * (Math.PI / 180);
      state.controls.target.set(0, H * 0.48, 0);
      state.camera.position.set(
        Math.sin(angle) * Math.cos(elev) * dist,
        H * 0.48 + Math.sin(elev) * dist,
        Math.cos(angle) * Math.cos(elev) * dist
      );
      state.camera.lookAt(state.controls.target);
      state.controls.update();
    });
    el('btnResetCamera').addEventListener('click', fitCameraToCharacter);

    // Timeline Controls
    el('btnPlayPause').addEventListener('click', togglePlayPause);
    el('timelineScrubber').addEventListener('input', e => {
      state.playing = false;
      el('btnPlayPause').textContent = '▶ Play';
      state.currentTime = parseFloat(e.target.value) || 0;
      evaluateCurrentFrame();
    });
    el('playbackSpeed').addEventListener('change', e => {
      state.playbackSpeed = parseFloat(e.target.value) || 1.0;
    });

    // Weapon Alignment Quick Buttons & Sliders
    el('btnAutoAlignWeapon').addEventListener('click', () => {
      resetWeaponManualOffsets(state.weaponParams.gripMode);
      updateWeaponAttachment();
      evaluateCurrentFrame();
      showToast('Arma auto-alineada por PCA y base palmar');
    });
    el('btnResetWeaponTransform').addEventListener('click', () => {
      resetWeaponManualOffsets(state.weaponParams.gripMode);
      updateWeaponAttachment();
      evaluateCurrentFrame();
    });
    el('btnFlipBarrel').addEventListener('click', () => {
      state.weaponParams.flipBarrel = !state.weaponParams.flipBarrel;
      updateWeaponAttachment();
      evaluateCurrentFrame();
    });
    el('btnFlipUp').addEventListener('click', () => {
      state.weaponParams.flipUp = !state.weaponParams.flipUp;
      updateWeaponAttachment();
      evaluateCurrentFrame();
    });
    el('btnRoll90').addEventListener('click', () => {
      state.weaponParams.roll90 = (state.weaponParams.roll90 + 1) % 4;
      updateWeaponAttachment();
      evaluateCurrentFrame();
    });
    el('btnYaw90').addEventListener('click', () => {
      state.weaponParams.yaw90 = ((state.weaponParams.yaw90 || 0) + 1) % 4;
      updateWeaponAttachment();
      evaluateCurrentFrame();
    });

    const bindWeaponSlider = (id, fn) => {
      el(id).addEventListener('input', e => {
        fn(parseFloat(e.target.value) || 0);
        syncWeaponControlsUI();
        updateWeaponAttachment();
        evaluateCurrentFrame();
      });
    };
    bindWeaponSlider('weaponScale', v => { state.weaponParams.scaleMultiplier = v; });
    bindWeaponSlider('weaponPosX', v => { state.weaponParams.offsetPos[0] = v; });
    bindWeaponSlider('weaponPosY', v => { state.weaponParams.offsetPos[1] = v; });
    bindWeaponSlider('weaponPosZ', v => { state.weaponParams.offsetPos[2] = v; });
    bindWeaponSlider('weaponRotX', v => { state.weaponParams.offsetRotDeg[0] = v; });
    bindWeaponSlider('weaponRotY', v => { state.weaponParams.offsetRotDeg[1] = v; });
    bindWeaponSlider('weaponRotZ', v => { state.weaponParams.offsetRotDeg[2] = v; });

    el('btnSaveWeaponPreset').addEventListener('click', async () => {
      if (!state.activeWeaponId) return;
      const presetCopy = JSON.parse(JSON.stringify(state.weaponParams));
      state.weaponPresets[state.activeWeaponId] = presetCopy;
      await saveToDB('presets', { id: state.activeWeaponId, params: presetCopy });
      showToast(`Preset guardado para ${state.activeWeaponData?.name || state.activeWeaponId}`);
    });

    // IK & Finger Grip Sliders
    el('leftHandIkWeight').addEventListener('input', e => {
      state.retargetParams.leftHandIkWeight = parseFloat(e.target.value) || 0;
      syncIkControlsUI();
      evaluateCurrentFrame();
    });
    ['foregripX', 'foregripY', 'foregripZ'].forEach((id, idx) => {
      el(id).addEventListener('input', e => {
        state.weaponParams.foregripOffset[idx] = parseFloat(e.target.value) || 0;
        syncIkControlsUI();
        updateWeaponAttachment();
        evaluateCurrentFrame();
      });
    });
    el('elbowPoleDeg').addEventListener('input', e => {
      const v = parseFloat(e.target.value) || 0;
      state.retargetParams.elbowPoleAngleDeg = v;
      el('valElbowPole').textContent = Math.round(v) + '°';
      evaluateCurrentFrame();
    });
    el('rightHandGrip').addEventListener('input', e => {
      const v = parseFloat(e.target.value) || 0;
      state.retargetParams.rightHandGrip = v;
      el('valRightGrip').textContent = Math.round(v * 100) + '%';
      evaluateCurrentFrame();
    });
    el('leftHandGrip').addEventListener('input', e => {
      const v = parseFloat(e.target.value) || 0;
      state.retargetParams.leftHandGrip = v;
      el('valLeftGrip').textContent = Math.round(v * 100) + '%';
      evaluateCurrentFrame();
    });

    // Locomotion & Posture Sliders
    el('inPlaceLock').addEventListener('input', e => {
      const v = parseFloat(e.target.value) || 0;
      state.retargetParams.inPlaceLock = v;
      el('valInPlace').textContent = Math.round(v * 100) + '%';
      evaluateCurrentFrame();
    });
    el('groundFeetToggle').addEventListener('change', e => {
      state.retargetParams.groundFeet = e.target.checked;
      evaluateCurrentFrame();
    });
    el('armSpreadDeg').addEventListener('input', e => {
      const v = parseFloat(e.target.value) || 0;
      state.retargetParams.armSpreadDeg = v;
      el('valArmSpread').textContent = Math.round(v) + '°';
      evaluateCurrentFrame();
    });
    el('spineTwistDeg').addEventListener('input', e => {
      const v = parseFloat(e.target.value) || 0;
      state.retargetParams.spineTwistDeg = v;
      el('valSpineTwist').textContent = Math.round(v) + '°';
      evaluateCurrentFrame();
    });
    el('spinePitchDeg').addEventListener('input', e => {
      const v = parseFloat(e.target.value) || 0;
      state.retargetParams.spinePitchDeg = v;
      el('valSpinePitch').textContent = Math.round(v) + '°';
      evaluateCurrentFrame();
    });
    el('bakeFpsSelect').addEventListener('change', e => {
      state.retargetParams.bakeFps = parseInt(e.target.value, 10) || 30;
    });

    // Export Buttons
    el('btnExportCurrentFbx').addEventListener('click', () => {
      const buf = window.__labExportCurrentFbxBuffer();
      if (buf) {
        showToast(`FBX exportado (${(buf.byteLength / 1048576).toFixed(2)} MB) listo para FBX-Web-Renderer`);
      }
    });

    el('btnExportMultiClipFbx').addEventListener('click', () => {
      const chosen = state.animations.filter(a => state.selectedAnimIds.has(a.id));
      if (!chosen.length) {
        showToast('Selecciona al menos 1 animación con el checkbox ☑', true);
        return;
      }
      const prefix = (el('exportPrefixInput').value || state.charName || 'character').trim();
      const wTag = state.activeWeaponData ? `_${state.activeWeaponData.id}` : '';
      const fileName = `${prefix}${wTag}_multiclip_${chosen.length}anims.fbx`;
      const buf = exportFbxWithAnimations(chosen, fileName);
      if (buf) {
        showToast(`FBX Multi-Clip exportado con ${chosen.length} animaciones (${(buf.byteLength / 1048576).toFixed(2)} MB)`);
      }
    });

    el('btnExportBatchZip').addEventListener('click', async () => {
      const chosen = state.animations.filter(a => state.selectedAnimIds.has(a.id));
      if (!chosen.length) {
        showToast('Selecciona al menos 1 animación con el checkbox ☑', true);
        return;
      }
      const prefix = (el('exportPrefixInput').value || state.charName || 'character').trim();
      const wTag = state.activeWeaponData ? `_${state.activeWeaponData.id}` : '';
      const zip = new THREE.JSZip();
      const folder = zip.folder(`${prefix}${wTag}_fbx_batch`);

      for (const anim of chosen) {
        const fbxBuf = exportFbxWithAnimations([anim], null);
        if (fbxBuf) {
          folder.file(`${prefix}${wTag}_${anim.id}.fbx`, fbxBuf);
        }
      }
      const blob = await zip.generateAsync({ type: 'blob' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${prefix}${wTag}_${chosen.length}_fbx_pack.zip`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
      showToast(`Lote ZIP exportado con ${chosen.length} archivos .FBX`);
    });
  }

  // 12. Seed Catalog Initialization & Main Render Loop
  async function initCatalogAndLoop() {
    initViewport();
    wireUIEvents();

    // Load seed animations + custom IndexedDB animations
    state.animations = [...(catalog.animations || [])];
    const savedAnims = await loadAllFromDB('animations');
    for (const a of savedAnims) {
      if (!state.animations.some(x => x.id === a.id)) state.animations.push(a);
    }
    state.animations.forEach(a => state.selectedAnimIds.add(a.id));

    // Load seed weapons + presets
    state.weapons = [...(catalog.weapons || [])];
    const savedPresets = await loadAllFromDB('presets');
    for (const p of savedPresets) {
      if (p.id && p.params) state.weaponPresets[p.id] = p.params;
    }

    renderAnimCatalogUI();
    renderWeaponCatalogUI();

    if (state.animations.length > 0) {
      state.activeAnimId = state.animations[0].id;
    }
    if (state.weapons.length > 0) {
      state.activeWeaponId = state.weapons[0].id;
    }

    // Start animation loop
    const fps = 30;
    function animate() {
      requestAnimationFrame(animate);
      const dt = Math.min(0.1, state.clock.getDelta());

      if (state.playing && state.charRigMap && state.retargetCtx) {
        state.currentTime = (state.currentTime + dt * state.playbackSpeed) % Math.max(0.05, state.duration);
        el('timelineScrubber').value = String(state.currentTime);
        evaluateCurrentFrame();
      }

      const fIdx = Math.floor(state.currentTime * fps);
      const totalF = Math.max(1, Math.floor(state.duration * fps));
      el('timelineLabel').textContent = `${state.currentTime.toFixed(2)}s / ${state.duration.toFixed(2)}s (F${fIdx}/${totalF})`;

      if (state.controls) state.controls.update();
      if (state.renderer && state.scene && state.camera) {
        state.renderer.render(state.scene, state.camera);
      }
    }
    animate();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCatalogAndLoop);
  } else {
    initCatalogAndLoop();
  }
})();
