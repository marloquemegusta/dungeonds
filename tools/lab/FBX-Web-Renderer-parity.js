/* Browser-only parity layer for FBX-Web-Renderer-offline.html. */
(() => {
  // The repository's headless FBX probe evaluates inline payloads without the full page.
  if (typeof Qf !== 'function' || typeof Kf !== 'function' || typeof document === 'undefined') return;

  const state = window.__spriteLab = {
    frames: [],
    captures: [],
    rigScale: 1,
    boneMode: false,
    displace: 0,
    supersample: 4,
    filterWidth: 1.5,
    // Map state
    map: null,
    mapCanvas: null,
    mapWidth: 768,
    mapHeight: 512,
    mapOrthoScale: 38.0,
    mapMeshScale: 24.0,
    mapAutoLevel: true,
    mapProjection: null,
    mapWalkGrid: null,
    mapWalkGridW: 0,
    mapWalkGridH: 0,
    mapHasFloorData: false,
    // DS Simulator state
    dsMode: '1', // '1' = 256x192, '2' = 256x384
    dsZoom: 'fit', // 'fit', '1x', '2x'
    dsCharX: 384,
    dsCharY: 256,
    dsCharDir: 0, // 0..7
    dsPanX: 384 - 128,
    dsPanY: 256 - 96,
    charAnimFrame: 0,
    liveDirCanvases: [],
    activeTab: 'scale'
  };

  // Match the Blender lab's 45-degree camera azimuth.
  Wf = Math.PI / 4;

  // Blender fits the evaluated mesh pose for every animation frame and direction.
  const originalSetFromObject = hr.prototype.setFromObject;
  hr.prototype.setFromObject = function (object) {
    if (!object) return this;
    object.updateWorldMatrix(true, true);
    object.traverse(node => {
      if (node.isSkinnedMesh && node.skeleton) node.skeleton.update();
    });
    return originalSetFromObject.call(this, object, true);
  };

  // Keep the same graded/outlined pixel data used by GIFs, while preserving alpha for PNG exports.
  Kf = function (pixels, width, height, params) {
    const graded = zf(pixels, params.contrast, params.saturation);
    const brightness = params.brightness ?? 1;
    if (brightness !== 1) {
      for (let index = 0; index < graded.length; index += 4) {
        graded[index] *= brightness;
        graded[index + 1] *= brightness;
        graded[index + 2] *= brightness;
      }
    }
    let processed = Rf(graded, width, height, params.outlineMode);
    if (!(processed instanceof Uint8ClampedArray)) processed = new Uint8ClampedArray(processed);
    if (state.capturing) state.frames.push({ pixels: new Uint8ClampedArray(processed), width, height });
    return Bf(processed, width, height, Vf);
  };

  // Posed (skinned) vertices of the model in world space, flat [x, y, z, ...].
  function posedPoints(root) {
    root.updateMatrixWorld(true);
    const out = [];
    const v = new K();
    root.traverse(node => {
      if (!node.isMesh || !node.visible || !node.geometry?.attributes?.position) return;
      if (node.isSkinnedMesh && node.skeleton) node.skeleton.update();
      const position = node.geometry.attributes.position;
      for (let index = 0; index < position.count; index++) {
        if (node.isSkinnedMesh) node.getVertexPosition(index, v);
        else v.fromBufferAttribute(position, index);
        v.applyMatrix4(node.matrixWorld);
        out.push(v.x, v.y, v.z);
      }
    });
    return out;
  }

  // Override Lf (model loader placement & wrapper creation) to avoid unskinned Box3 corruption.
  const originalLf = typeof Lf === 'function' ? Lf : null;
  if (originalLf) {
    Lf = function (model, parentScene, scaleMultiplier) {
      model.traverse(node => {
        if (node.isMesh) {
          node.frustumCulled = false;
          node.castShadow = true;
          node.receiveShadow = true;
          if (node.material) {
            const mats = Array.isArray(node.material) ? node.material : [node.material];
            mats.forEach(mat => {
              mat.side = 0;
              if (mat.map) mat.map.colorSpace = ot;
            });
          }
        }
      });

      let hasBones = false;
      model.traverse(node => { if (node.isBone) hasBones = true; });

      model.position.set(0, 0, 0);
      model.updateMatrixWorld(true);

      const pts = posedPoints(model);
      let minX = Infinity, maxX = -Infinity;
      let minY = Infinity, maxY = -Infinity;
      let minZ = Infinity, maxZ = -Infinity;
      for (let i = 0; i < pts.length; i += 3) {
        const x = pts[i], y = pts[i + 1], z = pts[i + 2];
        if (x < minX) minX = x; if (x > maxX) maxX = x;
        if (y < minY) minY = y; if (y > maxY) maxY = y;
        if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;
      }
      if (!isFinite(minY)) { minY = 0; maxY = 1.8; minX = -0.5; maxX = 0.5; minZ = -0.5; maxZ = 0.5; }

      const height = (maxY - minY) || 1.8;
      const width = (maxX - minX) || 1.0;
      const depth = (maxZ - minZ) || 1.0;

      const wrapper = new Kn();
      if (hasBones) {
        model.position.set(0, -minY, 0);
      } else {
        model.position.set(-(minX + maxX) / 2, -minY, -(minZ + maxZ) / 2);
      }
      wrapper.add(model);

      const scale = 1.8 / Math.max(height, width, depth);
      wrapper.scale.setScalar(scale * (scaleMultiplier || 1));
      parentScene.add(wrapper);

      return {
        wrapper,
        height: height * scale,
        radius: Math.max(width, depth) * scale / 2
      };
    };
  }

  // ---- Blender-equivalent lighting & materials ----
  function applyBlenderLighting() {
    if (!$.lights) return;
    const value = id => parseFloat(document.getElementById(id)?.value) || 0;
    const keyIntensity = value('keyLight') * Math.PI;
    const fillIntensity = value('fillLight') * Math.PI;
    const rimIntensity = value('rimLight') * Math.PI;
    const worldIntensity = value('worldLight') * Math.PI;

    $.lights.key.intensity = keyIntensity;
    $.lights.fill.intensity = fillIntensity;
    $.lights.rim.intensity = rimIntensity;
    $.lights.world.intensity = worldIntensity;

    const keyColorHex = document.getElementById('keyColor')?.value || '#ffe2b5';
    const fillColorHex = document.getElementById('fillColor')?.value || '#b3c4e1';
    const rimColorHex = document.getElementById('rimColor')?.value || '#cce7ff';

    if ($.lights.key.color?.set) $.lights.key.color.set(keyColorHex);
    if ($.lights.fill.color?.set) $.lights.fill.color.set(fillColorHex);
    if ($.lights.rim?.color?.set) $.lights.rim.color.set(rimColorHex);
    if ($.lights.world?.color?.setRGB) $.lights.world.color.setRGB(1.0, 1.0, 1.0);

    $.lights.key.position.set(0.4096 * 30, 0.5736 * 30, -0.7094 * 30);
    $.lights.fill.position.set(-0.5318 * 30, 0.3746 * 30, 0.7595 * 30);
    if ($.lights.rim) $.lights.rim.position.set(0, 30, 0);
  }

  function setupModelMaterials(model) {
    if (!model) return;
    const normalStrength = parseFloat(document.getElementById('labNormal')?.value) || 0.35;
    model.traverse(object => {
      if (!object.isMesh) return;
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      const converted = materials.map(mat => {
        if (!mat || state.boneMode) return mat;
        if (mat.isMeshStandardMaterial && mat.userData.__dungeonPBR) {
          if (mat.normalMap) mat.normalScale.setScalar(normalStrength);
          return mat;
        }
        const diffuseMap = mat.map || null;
        const normMap = mat.normalMap || null;
        const emMap = mat.emissiveMap || null;
        if (diffuseMap) diffuseMap.colorSpace = ot;
        if (emMap) emMap.colorSpace = ot;

        const baseColor = diffuseMap ? 0xffffff : (mat.color ? mat.color.clone() : 0xd0d0d0);
        const emColor = emMap ? 0xffffff : (mat.emissive ? mat.emissive.clone() : 0x000000);
        const emIntensity = emMap ? 1.0 : (mat.emissiveIntensity ?? 0.35);

        const std = new Xa({
          color: baseColor,
          roughness: mat.roughness ?? 0.85,
          metalness: mat.metalness ?? 0.05,
          map: diffuseMap,
          normalMap: normMap,
          emissiveMap: emMap,
          emissive: emColor,
          emissiveIntensity: emIntensity,
        });
        std.userData.__dungeonPBR = true;
        std.userData.__originalMaterial = mat;
        if (std.normalMap) std.normalScale.setScalar(normalStrength);
        return std;
      });
      object.material = Array.isArray(object.material) ? converted : converted[0];
    });
  }

  const originalSetCustomLighting = setCustomLighting;
  setCustomLighting = function () {
    if (originalSetCustomLighting) originalSetCustomLighting();
    applyBlenderLighting();
  };

  const originalApplyDungeonLighting = applyDungeonLighting;
  applyDungeonLighting = function (preset) {
    if (originalApplyDungeonLighting) originalApplyDungeonLighting(preset);
    applyBlenderLighting();
  };

  // Synthetic THREE environment for glb_loader_minimal.js
  const THREE_ENV = {
    BufferGeometry: Jr,
    BufferAttribute: Nr,
    MeshStandardMaterial: Xa,
    Mesh: vi,
    Color: ($.lights?.world?.color?.constructor) || class {
      constructor(r = 1, g = 1, b = 1) { this.r = r; this.g = g; this.b = b; }
      setRGB(r, g, b) { this.r = r; this.g = g; this.b = b; return this; }
      set(val) { return this; }
    },
    SRGBColorSpace: ot,
    TextureLoader: class {
      load(url, onLoad) {
        const img = new Image();
        const texture = new pn(img);
        img.onload = () => {
          texture.needsUpdate = true;
          if (onLoad) onLoad(texture);
        };
        img.src = url;
        return texture;
      }
    }
  };

  const AZIMUTH = Math.PI / 4;
  const DIR0_YAW = 3 * Math.PI / 4;
  const DIR_STEP = Math.PI / 4;

  // Cycles-like Blackman-Harris pixel filter
  function blackmanHarris(distance, width) {
    const t = distance / width + 0.5;
    if (t < 0 || t > 1) return 0;
    const phase = 2 * Math.PI * t;
    return 0.35875 - 0.48829 * Math.cos(phase) + 0.14128 * Math.cos(2 * phase) - 0.01168 * Math.cos(3 * phase);
  }

  // Alpha-weighted downsample
  function downsample(source, size, ss, filterWidth) {
    if (ss === 1) return source;
    const wide = size * ss;
    const out = new Uint8ClampedArray(size * size * 4);
    const radius = filterWidth / 2;
    for (let oy = 0; oy < size; oy++) {
      for (let ox = 0; ox < size; ox++) {
        const cx = (ox + 0.5) * ss, cy = (oy + 0.5) * ss;
        let r = 0, g = 0, b = 0, a = 0, weight = 0;
        for (let sy = Math.max(0, Math.floor(cy - radius * ss)); sy <= Math.min(wide - 1, Math.ceil(cy + radius * ss)); sy++) {
          const wy = blackmanHarris((sy + 0.5 - cy) / ss, filterWidth);
          if (!wy) continue;
          for (let sx = Math.max(0, Math.floor(cx - radius * ss)); sx <= Math.min(wide - 1, Math.ceil(cx + radius * ss)); sx++) {
            const w = wy * blackmanHarris((sx + 0.5 - cx) / ss, filterWidth);
            if (!w) continue;
            const i = (sy * wide + sx) * 4;
            const alpha = source[i + 3] / 255;
            r += source[i] * alpha * w; g += source[i + 1] * alpha * w; b += source[i + 2] * alpha * w;
            a += alpha * w; weight += w;
          }
        }
        const o = (oy * size + ox) * 4;
        if (a > 1e-6) { out[o] = r / a; out[o + 1] = g / a; out[o + 2] = b / a; }
        out[o + 3] = weight ? Math.round(255 * a / weight) : 0;
      }
    }
    return out;
  }

  // Compute camera fit for character
  function computeCharacterFit(size, targetPixels) {
    const root = $.modelRoot || null;
    const scene = $.scene;
    if (root) {
      root.position.set(0, 0, 0);
      root.rotation.y = 0;
      root.updateMatrixWorld(true);
    }
    const elevation = Yt.degToRad(Math.max(1, parseFloat(document.getElementById('elevation')?.value) || 30));
    const toCamera = new K(Math.cos(elevation) * Math.cos(AZIMUTH), Math.sin(elevation), -Math.cos(elevation) * Math.sin(AZIMUTH)).normalize();
    const right = new K().crossVectors(new K(0, 1, 0), toCamera).normalize();
    const upAxis = new K().crossVectors(toCamera, right).normalize();

    const pts = posedPoints(root || scene);
    let minY = Infinity;
    for (let i = 1; i < pts.length; i += 3) minY = Math.min(minY, pts[i]);

    let minX = Infinity, maxX = -Infinity, minV = Infinity, maxV = -Infinity;
    for (let direction = 0; direction < Ff.length; direction++) {
      const yaw = DIR0_YAW - direction * DIR_STEP, cos = Math.cos(yaw), sin = Math.sin(yaw);
      for (let i = 0; i < pts.length; i += 3) {
        const px = pts[i] * cos + pts[i + 2] * sin;
        const pz = -pts[i] * sin + pts[i + 2] * cos;
        const py = pts[i + 1] - minY;
        const u = px * right.x + py * right.y + pz * right.z;
        const w = px * upAxis.x + py * upAxis.y + pz * upAxis.z;
        if (u < minX) minX = u; if (u > maxX) maxX = u;
        if (w < minV) minV = w; if (w > maxV) maxV = w;
      }
    }
    const extent = Math.max(maxX - minX, maxV - minV);
    state.lastCharExtent = extent;
    state.lastCharMinY = minY;
    const half = (extent * size / targetPixels) / 2;
    const center = new K()
      .addScaledVector(right, (minX + maxX) / 2)
      .addScaledVector(upAxis, (minV + maxV) / 2);
    const camera = new ts(-half, half, half, -half, 0.1, 100);
    camera.position.copy(center).addScaledVector(toCamera, 30);
    camera.lookAt(center);
    camera.updateMatrixWorld(true);

    return { camera, minY, center, toCamera, half };
  }

  // Full animation render loop
  Qf = async function ({ renderer, scene, controls, state: app, params, onProgress, onStatus }) {
    params.brightness = parseFloat(document.getElementById('labBrightness')?.value) || 1;
    const size = params.resolution;
    const frameCount = params.frameCount;
    const outline = params.outlineMode !== 'none';
    const targetPixels = size - (outline ? 2 : 0);
    const ss = Math.max(1, Math.round(state.supersample || 1));
    const delay = Math.max(20, Math.round(1000 / frameCount));
    const started = performance.now();
    const root = app.modelRoot || null;
    const previousYaw = root ? root.rotation.y : 0;
    const previousY = root ? root.position.y : 0;
    const previousSize = new G();
    renderer.getSize(previousSize);
    app.rendering = true;
    state.frames = [];
    state.capturing = true;

    if (state.mapGroup) state.mapGroup.visible = false;
    if (root) {
      root.visible = true;
      root.position.set(0, 0, 0);
      root.rotation.y = 0;
      root.updateMatrixWorld(true);
    }

    try {
      for (let waited = 0; renderer.getContext().isContextLost() && waited < 15000; waited += 100) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      applyBlenderLighting();
      setupModelMaterials(app.model);
      let duration = 0;
      if (app.currentAction?.getClip) duration = app.currentAction.getClip().duration || 0;
      else if (app.clips?.length) duration = app.clips[0].duration || 0;
      const times = duration > 0 ? Array.from({ length: frameCount }, (_, index) => duration * index / frameCount) : [0];

      const elevation = Yt.degToRad(Math.max(1, params.elevation));
      const toCamera = new K(Math.cos(elevation) * Math.cos(AZIMUTH), Math.sin(elevation), -Math.cos(elevation) * Math.sin(AZIMUTH)).normalize();
      const right = new K().crossVectors(new K(0, 1, 0), toCamera).normalize();
      const upAxis = new K().crossVectors(toCamera, right).normalize();

      if (root) { root.rotation.y = 0; root.position.y = 0; }
      if (app.model) {
        let hasBones = false;
        app.model.traverse(node => { if (node.isBone) hasBones = true; });
        if (hasBones) {
          app.model.position.x = 0;
          app.model.position.z = 0;
          app.model.updateMatrixWorld(true);
        }
      }
      const samples = [];
      for (const time of times) {
        app.mixer?.setTime(time);
        const pts = posedPoints(root || scene);
        let minY = Infinity;
        for (let i = 1; i < pts.length; i += 3) minY = Math.min(minY, pts[i]);
        samples.push({ pts, minY });
        await new Promise(resolve => setTimeout(resolve, 0));
      }
      let minX = Infinity, maxX = -Infinity, minV = Infinity, maxV = -Infinity;
      for (let direction = 0; direction < Ff.length; direction++) {
        await new Promise(resolve => setTimeout(resolve, 0));
        const yaw = DIR0_YAW - direction * DIR_STEP, cos = Math.cos(yaw), sin = Math.sin(yaw);
        for (const sample of samples) for (let i = 0; i < sample.pts.length; i += 3) {
          const px = sample.pts[i] * cos + sample.pts[i + 2] * sin;
          const pz = -sample.pts[i] * sin + sample.pts[i + 2] * cos;
          const py = sample.pts[i + 1] - sample.minY;
          const u = px * right.x + py * right.y + pz * right.z;
          const w = px * upAxis.x + py * upAxis.y + pz * upAxis.z;
          if (u < minX) minX = u; if (u > maxX) maxX = u;
          if (w < minV) minV = w; if (w > maxV) maxV = w;
        }
      }
      const extent = Math.max(maxX - minX, maxV - minV);
      const half = extent * size / targetPixels / 2;
      const center = new K()
        .addScaledVector(right, (minX + maxX) / 2)
        .addScaledVector(upAxis, (minV + maxV) / 2);
      const camera = new ts(-half, half, half, -half, 0.1, 100);
      camera.position.copy(center).addScaledVector(toCamera, 30);
      camera.lookAt(center);
      camera.updateMatrixWorld(true);
      state.lastFit = { extent, half, center: center.toArray(), minX, maxX, minV, maxV, pts: samples[0].pts, minY0: samples[0].minY, camera };

      renderer.setClearColor(0x000000, 0);
      renderer.setSize(size * ss, size * ss, false);
      const results = [], firstFrames = [];
      for (let direction = 0; direction < Ff.length; direction++) {
        const name = Ff[direction];
        const gifFrames = [];
        for (let index = 0; index < frameCount; index++) {
          if (root) {
            root.rotation.y = DIR0_YAW - direction * DIR_STEP;
            root.position.y = -samples[index % samples.length].minY;
          }
          app.mixer?.setTime(times[index % times.length]);
          if (root) root.updateMatrixWorld(true);
          renderer.render(scene, camera);
          let pixels = Gf(renderer, size * ss, size * ss);
          if (!(pixels instanceof Uint8ClampedArray)) pixels = new Uint8ClampedArray(pixels.buffer);
          pixels = downsample(pixels, size, ss, state.filterWidth);
          const frame = Kf(pixels, size, size, params);
          gifFrames.push(frame);
          if (index === 0) firstFrames.push(frame);
          onStatus && onStatus(name, index + 1, (performance.now() - started) / 1e3);
          onProgress && onProgress((direction * frameCount + index + 1) / (Ff.length * frameCount));
          if (index % 2 === 1) await new Promise(resolve => setTimeout(resolve, 0));
        }
        const blob = qf(gifFrames, size, size, delay);
        results.push({ name, index: direction, blob, url: URL.createObjectURL(blob), width: size, height: size });
        await new Promise(resolve => setTimeout(resolve, 0));
      }
      const collage = $f(firstFrames, size);
      const result = { results, collage, width: size, height: size, delay, frames: state.frames };
      onStatus && onStatus('\u2713', frameCount, (performance.now() - started) / 1e3);

      updateTopStripGifs(results);
      drawDsSimulator();
      return result;
    } finally {
      state.capturing = false;
      if (root) {
        root.rotation.y = previousYaw;
        root.position.y = previousY;
        root.updateMatrixWorld(true);
      }
      app.mixer?.setTime(0);
      syncViewportRendererSize();
      if (controls) controls.update();
      app.rendering = false;
      update3DViewMode();
      if (onProgress) onProgress(1);
    }
  };

  const encodePng = async (frame) => {
    const canvas = document.createElement('canvas');
    canvas.width = frame.width;
    canvas.height = frame.height;
    canvas.getContext('2d').putImageData(new ImageData(frame.pixels, frame.width, frame.height), 0, 0);
    return new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error('No se pudo codificar PNG')), 'image/png'));
  };

  function getFrames() { return state.frames || []; }

  async function makeAtlas() {
    const frames = getFrames();
    const columns = parseInt(_p.frameCount.value, 10);
    const rows = Ff.length;
    const size = parseInt(_p.resolution.value, 10);
    if (frames.length !== rows * columns) throw new Error(`Frames incompletos: ${frames.length}/${rows * columns}`);
    const canvas = document.createElement('canvas');
    canvas.width = columns * size;
    canvas.height = rows * size;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let index = 0; index < frames.length; index++) {
      const frame = frames[index];
      ctx.putImageData(new ImageData(frame.pixels, size, size), (index % columns) * size, Math.floor(index / columns) * size);
    }
    return new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve({ blob, width: canvas.width, height: canvas.height }) : reject(new Error('No se pudo crear el spritesheet')), 'image/png'));
  }

  async function exportPackage() {
    if (!$.results?.length || getFrames().length === 0) throw new Error('Renderiza el modelo antes de exportar');
    const name = (cp.textContent || 'modelo').replace(/\.fbx$/i, '').replace(/[^a-z0-9_-]+/gi, '_');
    const zip = new Nf.default();
    const folder = zip.folder(name);
    const framesFolder = folder.folder('frames');
    const atlas = await makeAtlas();
    folder.file(`${name}_spritesheet.png`, atlas.blob);
    folder.file(`${name}_collage.gif`, $.collage.blob);
    const frameCount = parseInt(_p.frameCount.value, 10);
    const size = parseInt(_p.resolution.value, 10);
    for (const direction of $.results) {
      folder.file(`${name}_${String(direction.index).padStart(2, '0')}_${direction.name}.gif`, direction.blob);
    }
    for (let index = 0; index < getFrames().length; index++) {
      const directionIndex = Math.floor(index / frameCount);
      const frameIndex = index % frameCount;
      const frame = getFrames()[index];
      const blob = await encodePng(frame);
      framesFolder.file(`${String(directionIndex).padStart(2, '0')}_${Ff[directionIndex]}/${String(frameIndex).padStart(3, '0')}.png`, blob);
    }
    const stride = parseFloat(document.getElementById('stride3d')?.value || 1.5);
    const ticks = parseInt(document.getElementById('animTicks')?.value || 3, 10);
    const stridePx = stride * (32 / (2 * Math.sqrt(2))) * state.rigScale;
    const speedFixed88 = Math.round((stridePx * 256) / Math.max(1, frameCount * ticks));
    const cameraElevation = document.getElementById('elevation');
    const settings = {
      model: cp.textContent,
      animation: _p.animSelect.selectedOptions[0]?.textContent || 'Pose estática',
      directions: Ff,
      framesPerDirection: frameCount,
      frameSize: `${size}x${size}`,
      spritesheet: { columns: frameCount, rows: Ff.length, width: atlas.width, height: atlas.height, alpha: true },
      stride3dMeters: stride,
      ticksPerFrame: ticks,
      stridePixels: Number(stridePx.toFixed(2)),
      speedFixed8_8: speedFixed88,
      inPlace: document.getElementById('inPlaceMotion').checked,
      rigScale: state.rigScale,
      cameraElevationDegrees: cameraElevation ? parseFloat(cameraElevation.value) : null,
      contrast: parseFloat(_p.contrast.value),
      saturation: parseFloat(_p.saturation.value),
      neckPitchDegrees: parseFloat(document.getElementById('neckPitch')?.value || 0),
      displace: parseFloat(document.getElementById('meshDisplace')?.value || 0),
      brightness: parseFloat(document.getElementById('labBrightness')?.value || 1.0),
      webglShadowQuality: parseInt(document.getElementById('labSamples')?.value || 16, 10),
      normalStrength: parseFloat(document.getElementById('labNormal')?.value || 0.35),
      shadowSoftness: parseFloat(document.getElementById('labShadow')?.value || 2.0),
      supersample: state.supersample || 4,
      boneShader: state.boneMode,
      renderEngine: 'Three.js WebGL (browser)'
    };
    folder.file('settings.json', JSON.stringify(settings, null, 2));
    folder.file('README.md', `# ${name}\n\nSpritesheet PNG: ${frameCount} columnas (frames), ${Ff.length} filas (direcciones), ${size}x${size}px por celda, RGBA transparente.\n\nIncluye GIF por direccion, collage GIF, PNG por frame y settings.json. Orden: ${Ff.join(', ')}.\n`);
    return zip.generateAsync({ type: 'blob' });
  }

  // ---- 3D Map Loader & Renderer ----

  function initMapScene() {
    if (state.mapGroup) return;
    state.mapGroup = new Kn();
    $.scene.add(state.mapGroup);
  }

  async function waitForModelTextures(root) {
    if (!root) return;
    const promises = [];
    const texProps = ['map', 'normalMap', 'emissiveMap', 'roughnessMap', 'metalnessMap'];

    root.traverse(node => {
      if (!node.isMesh || !node.material) return;
      const mats = Array.isArray(node.material) ? node.material : [node.material];
      mats.forEach(mat => {
        texProps.forEach(prop => {
          const tex = mat[prop];
          if (tex && tex.image) {
            const img = tex.image;
            if (typeof Image !== 'undefined' && (img instanceof Image || img.tagName === 'IMG' || img.src)) {
              if (img.complete && img.naturalWidth > 0) {
                tex.needsUpdate = true;
              } else {
                promises.push(new Promise(resolve => {
                  let settled = false;
                  const finish = () => {
                    if (settled) return;
                    settled = true;
                    tex.needsUpdate = true;
                    resolve();
                  };
                  if (img.complete && img.naturalWidth > 0) {
                    finish();
                    return;
                  }
                  img.addEventListener('load', finish, { once: true });
                  img.addEventListener('error', finish, { once: true });
                  setTimeout(finish, 3000);
                }));
              }
            }
          }
        });
      });
    });

    if (promises.length > 0) {
      await Promise.all(promises);
    }
  }

  function groundCharacterIn3D() {
    if (!$.modelRoot || !$.model) return;

    if (state.mapProjection && isFinite(state.dsCharX) && isFinite(state.dsCharY)) {
      const worldXZ = mapPixelToWorldXZ(state.dsCharX, state.dsCharY);
      if (isFinite(worldXZ.x) && isFinite(worldXZ.z)) {
        $.modelRoot.position.x = worldXZ.x;
        $.modelRoot.position.z = worldXZ.z;
      }
    } else {
      // Check if at (0, 0) there is geometry above Y = 0.2 (e.g. cover_mid block)
      let obstacleAtOrigin = false;
      if (state.map?.model) {
        state.map.model.updateMatrixWorld(true);
        state.map.model.traverse(node => {
          if (!obstacleAtOrigin && node.isMesh && node.geometry?.attributes?.position) {
            const pos = node.geometry.attributes.position;
            const v = new K();
            for (let i = 0; i < pos.count; i++) {
              v.fromBufferAttribute(pos, i).applyMatrix4(node.matrixWorld);
              if (Math.hypot(v.x, v.z) < 1.4 && v.y > 0.2) {
                obstacleAtOrigin = true;
                break;
              }
            }
          }
        });
      }

      if (obstacleAtOrigin) {
        // Place character in open corridor in front of central cover block
        $.modelRoot.position.x = 0;
        $.modelRoot.position.z = 3.0;
      } else {
        $.modelRoot.position.x = 0;
        $.modelRoot.position.z = 0;
      }
    }

    $.modelRoot.updateMatrixWorld(true);
    const pts = posedPoints($.model);
    let minY = Infinity;
    for (let i = 1; i < pts.length; i += 3) {
      if (pts[i] < minY) minY = pts[i];
    }
    if (isFinite(minY)) {
      state.lastCharMinY = minY;
      $.modelRoot.position.y -= minY;
      $.modelRoot.updateMatrixWorld(true);
    }
  }

  function sync3DRelativeScale() {
    if (!state.mapGroup || !state.map?.model) return;
    const charPx = parseInt(document.getElementById('resolution')?.value, 10) || 48;
    const mapW = parseInt(document.getElementById('mapPixelSize')?.value, 10) || 768;

    let charExtent = 1.8;
    if ($.model) {
      $.model.updateMatrixWorld(true);
      const charBox = new hr().setFromObject($.model);
      const rawH = charBox.max.y - charBox.min.y;
      const rootScale = ($.modelRoot && $.modelRoot.scale) ? $.modelRoot.scale.y : 1.0;
      charExtent = (rawH > 10) ? (rawH * rootScale) : rawH;
      if (!isFinite(charExtent) || charExtent < 0.5 || charExtent > 5.0) {
        charExtent = 1.8;
      }
    }
    state.lastCharExtent = charExtent;

    const baseProjW = state.mapUnscaledProjW || 24;
    const desiredWorldWidth = (mapW / charPx) * charExtent;
    const scaleRatio = desiredWorldWidth / baseProjW;

    state.mapGroup.scale.setScalar(scaleRatio);
    state.mapGroup.position.set(0, 0, 0);
    state.mapGroup.updateMatrixWorld(true);

    groundCharacterIn3D();
  }

  async function loadMapFile(file) {
    initMapScene();
    bp(true, `Cargando mapa 3D (${file.name})...`);
    try {
      while (state.mapGroup.children.length > 0) {
        state.mapGroup.remove(state.mapGroup.children[0]);
      }
      const ext = file.name.split('.').pop().toLowerCase();
      let mapModel = null;
      const arrayBuffer = await file.arrayBuffer();

      if (ext === 'glb') {
        if (!window.MinimalGLBLoader) throw new Error('Cargador MinimalGLBLoader no encontrado');
        mapModel = window.MinimalGLBLoader.buildThreeMeshFromGLB(THREE_ENV, arrayBuffer);
      } else if (ext === 'fbx') {
        const loader = new cf();
        mapModel = loader.parse(arrayBuffer, '');
      } else {
        throw new Error('Formato no compatible. Selecciona .FBX o .GLB');
      }

      if (!mapModel) throw new Error('No se pudo instanciar la geometría del mapa');

      // Filter giant ground/backdrop meshes that dwarf the playable room (> 2.5x span of others)
      const childMeshes = [];
      mapModel.traverse(c => { if (c.isMesh) childMeshes.push(c); });
      if (childMeshes.length > 1) {
        const otherBox = new hr();
        let otherCount = 0;
        childMeshes.forEach(c => {
          const name = (c.name || '').toLowerCase();
          if (!name.includes('ground') && !name.includes('backdrop')) {
            otherBox.expandByObject(c);
            otherCount++;
          }
        });
        if (otherCount > 0) {
          const oSize = new K();
          otherBox.getSize(oSize);
          const oSpan = Math.max(oSize.x, oSize.z);
          childMeshes.forEach(c => {
            const name = (c.name || '').toLowerCase();
            if (name.includes('ground') || name.includes('backdrop')) {
              const cBox = new hr().setFromObject(c);
              const cSize = new K();
              cBox.getSize(cSize);
              const cSpan = Math.max(cSize.x, cSize.z);
              if (cSpan > oSpan * 2.5) {
                c.visible = false;
                if (c.parent) c.parent.remove(c);
              }
            }
          });
        }
      }

      mapModel.position.set(0, 0, 0);
      mapModel.scale.set(1, 1, 1);
      mapModel.updateMatrixWorld(true);
      let box = new hr().setFromObject(mapModel);
      let sizeVec = new K();
      box.getSize(sizeVec);

      // Detect Z-up coordinate system (wall height in Z instead of Y)
      if (sizeVec.z < Math.min(sizeVec.x, sizeVec.y) * 0.8) {
        mapModel.rotation.x = -Math.PI / 2;
        mapModel.updateMatrixWorld(true);
        box = new hr().setFromObject(mapModel);
        box.getSize(sizeVec);
      }

      const rawSpan = Math.max(sizeVec.x, sizeVec.z) || 1.0;
      state.mapRawSpan = rawSpan;

      setupModelMaterials(mapModel);
      mapModel.traverse(node => {
        if (node.isMesh) {
          node.castShadow = true;
          node.receiveShadow = true;
          if (node.material) {
            const mats = Array.isArray(node.material) ? node.material : [node.material];
            mats.forEach(m => {
              m.normalMap = null;
              if (m.roughness !== undefined) m.roughness = 0.85;
              if (m.metalness !== undefined) m.metalness = 0.05;
              if (m.map && m.color?.setHex) m.color.setHex(0xffffff);
              if (m.map) m.map.colorSpace = ot;
            });
          }
        }
      });

      const autoLevel = document.getElementById('mapAutoLevel')?.checked ?? true;
      if (autoLevel) {
        const scaledBox = new hr().setFromObject(mapModel);
        const midY = scaledBox.min.y + (scaledBox.max.y - scaledBox.min.y) * 0.55;
        const heightAreaMap = new Map();
        const v0 = new K(), v1 = new K(), v2 = new K();
        const edge1 = new K(), edge2 = new K(), cross = new K();

        mapModel.traverse(node => {
          if (!node.isMesh || !node.visible || !node.geometry?.attributes?.position) return;
          const geom = node.geometry;
          const posAttr = geom.attributes.position;
          const index = geom.index;
          const numTriangles = index ? Math.floor(index.count / 3) : Math.floor(posAttr.count / 3);

          for (let t = 0; t < numTriangles; t++) {
            const i0 = index ? index.getX(t * 3 + 0) : t * 3 + 0;
            const i1 = index ? index.getX(t * 3 + 1) : t * 3 + 1;
            const i2 = index ? index.getX(t * 3 + 2) : t * 3 + 2;

            v0.fromBufferAttribute(posAttr, i0).applyMatrix4(node.matrixWorld);
            v1.fromBufferAttribute(posAttr, i1).applyMatrix4(node.matrixWorld);
            v2.fromBufferAttribute(posAttr, i2).applyMatrix4(node.matrixWorld);

            edge1.subVectors(v1, v0);
            edge2.subVectors(v2, v0);
            cross.crossVectors(edge1, edge2);
            const area = 0.5 * cross.length();
            if (area <= 1e-6) continue;
            cross.normalize();

            const triY = (v0.y + v1.y + v2.y) / 3;
            if (Math.abs(cross.y) > 0.8 && triY <= midY) {
              const bucket = Math.round(triY * 20) / 20; // 5cm bin
              heightAreaMap.set(bucket, (heightAreaMap.get(bucket) || 0) + area);
            }
          }
        });

        let floorY = scaledBox.min.y;
        let maxArea = -1;
        for (const [bucket, totalArea] of heightAreaMap.entries()) {
          if (totalArea > maxArea) {
            maxArea = totalArea;
            floorY = bucket;
          }
        }
        const centerVec = new K();
        scaledBox.getCenter(centerVec);
        mapModel.position.set(-centerVec.x, -floorY, -centerVec.z);
      }
      mapModel.updateMatrixWorld(true);

      // Record unscaled projected width for 3D scale sync
      const elev = Yt.degToRad(30);
      const toCam = new K(Math.cos(elev) * Math.cos(AZIMUTH), Math.sin(elev), -Math.cos(elev) * Math.sin(AZIMUTH)).normalize();
      const r = new K().crossVectors(new K(0, 1, 0), toCam).normalize();
      const b = new hr().setFromObject(mapModel);
      let minU = Infinity, maxU = -Infinity;
      [
        new K(b.min.x, b.min.y, b.min.z), new K(b.min.x, b.min.y, b.max.z),
        new K(b.min.x, b.max.y, b.min.z), new K(b.min.x, b.max.y, b.max.z),
        new K(b.max.x, b.min.y, b.min.z), new K(b.max.x, b.min.y, b.max.z),
        new K(b.max.x, b.max.y, b.min.z), new K(b.max.x, b.max.y, b.max.z)
      ].forEach(pt => {
        const u = pt.dot(r);
        if (u < minU) minU = u;
        if (u > maxU) maxU = u;
      });
      state.mapUnscaledProjW = Math.max(0.1, maxU - minU);

      state.mapGroup.add(mapModel);
      state.map = { model: mapModel, name: file.name, loaded: true, rawSpan };
      const mapNameLabel = document.getElementById('mapFileName');
      if (mapNameLabel) mapNameLabel.textContent = file.name;

      sync3DRelativeScale();
      groundCharacterIn3D();

      yp(`Esperando texturas del mapa 3D...`);
      await waitForModelTextures(mapModel);

      yp(`Mapa 3D cargado: ${file.name}`);
      update3DViewMode();
      await renderMap(true);
    } catch (err) {
      console.error(err);
      yp(`Error al cargar mapa: ${err.message}`, true);
    } finally {
      bp(false);
    }
  }

  async function renderMap(highQuality = false) {
    if (!state.map?.model || !$.renderer) return;

    const elevation = Yt.degToRad(Math.max(1, parseFloat(document.getElementById('elevation')?.value) || 30));
    const toCamera = new K(Math.cos(elevation) * Math.cos(AZIMUTH), Math.sin(elevation), -Math.cos(elevation) * Math.sin(AZIMUTH)).normalize();
    const right = new K().crossVectors(new K(0, 1, 0), toCamera).normalize();
    const upAxis = new K().crossVectors(toCamera, right).normalize();

    // Auto-frame map geometry based on camera-space bounds
    state.map.model.updateMatrixWorld(true);
    const mapBox = new hr().setFromObject(state.map.model);
    const corners = [
      new K(mapBox.min.x, mapBox.min.y, mapBox.min.z),
      new K(mapBox.min.x, mapBox.min.y, mapBox.max.z),
      new K(mapBox.min.x, mapBox.max.y, mapBox.min.z),
      new K(mapBox.min.x, mapBox.max.y, mapBox.max.z),
      new K(mapBox.max.x, mapBox.min.y, mapBox.min.z),
      new K(mapBox.max.x, mapBox.min.y, mapBox.max.z),
      new K(mapBox.max.x, mapBox.max.y, mapBox.min.z),
      new K(mapBox.max.x, mapBox.max.y, mapBox.max.z)
    ];

    let minU = Infinity, maxU = -Infinity;
    let minV = Infinity, maxV = -Infinity;
    for (let i = 0; i < corners.length; i++) {
      const c = corners[i];
      const u = c.dot(right);
      const v = c.dot(upAxis);
      if (u < minU) minU = u;
      if (u > maxU) maxU = u;
      if (v < minV) minV = v;
      if (v > maxV) maxV = v;
    }

    const projW = Math.max(0.1, maxU - minU);
    const projH = Math.max(0.1, maxV - minV);
    state.lastMapProjW = projW;
    state.lastMapProjH = projH;

    const mapW = parseInt(document.getElementById('mapPixelSize')?.value, 10) || 768;
    const mapH = Math.max(128, Math.round(mapW * (projH / projW)));
    state.mapWidth = mapW;
    state.mapHeight = mapH;

    const midU = (minU + maxU) / 2;
    const midV = (minV + maxV) / 2;
    const projCenter = new K()
      .addScaledVector(right, midU)
      .addScaledVector(upAxis, midV);

    const mapCamera = new ts(-projW / 2, projW / 2, projH / 2, -projH / 2, 0.1, 1000);
    mapCamera.position.copy(projCenter).addScaledVector(toCamera, 300);
    mapCamera.lookAt(projCenter);
    mapCamera.updateMatrixWorld(true);

    updateMapDensityLabel();

    state.mapProjection = {
      minU,
      maxU,
      minV,
      maxV,
      projW,
      projH,
      mapW,
      mapH,
      right: right.clone(),
      upAxis: upAxis.clone(),
      det: right.x * upAxis.z - right.z * upAxis.x
    };
    buildMapCollisionGrid();
    ensureCharacterOnWalkableFloor(true);

    const previousSize = new G();
    $.renderer.getSize(previousSize);
    const charRoot = $.modelRoot;
    const prevCharVis = charRoot ? charRoot.visible : true;
    if (charRoot) charRoot.visible = false;
    state.mapGroup.visible = true;

    try {
      applyBlenderLighting();
      $.renderer.setClearColor(0x000000, 1);
      $.renderer.setSize(mapW, mapH, false);
      $.renderer.render($.scene, mapCamera);

      let pixels = Gf($.renderer, mapW, mapH);
      if (!(pixels instanceof Uint8ClampedArray)) pixels = new Uint8ClampedArray(pixels.buffer);

      const contrast = parseFloat(_p.contrast?.value) || 1.5;
      const saturation = parseFloat(_p.saturation?.value) || 1.15;
      const brightness = parseFloat(document.getElementById('labBrightness')?.value) || 1.0;

      let graded = zf(pixels, contrast, saturation);
      if (brightness !== 1.0) {
        for (let i = 0; i < graded.length; i += 4) {
          graded[i] *= brightness;
          graded[i + 1] *= brightness;
          graded[i + 2] *= brightness;
        }
      }

      if (!state.mapCanvas) {
        state.mapCanvas = document.createElement('canvas');
      }
      state.mapCanvas.width = mapW;
      state.mapCanvas.height = mapH;
      const mCtx = state.mapCanvas.getContext('2d');
      mCtx.putImageData(new ImageData(graded, mapW, mapH), 0, 0);

      const btnExportMap = document.getElementById('btnExportMapZip');
      if (btnExportMap) btnExportMap.disabled = false;

      updateDsMetricsBadge();
      state.mapRenderedName = state.map?.name;
      state.mapRenderCount = (state.mapRenderCount || 0) + 1;
      ensureCharacterOnWalkableFloor(false);
      drawDsSimulator();
    } finally {
      $.renderer.setClearColor(0x000000, 0);
      if (charRoot) charRoot.visible = prevCharVis;
      update3DViewMode();
      syncViewportRendererSize();
    }
  }

  // ---- 2D Walkability & Collision Engine derived from 3D Geometry ----

  function worldToMapPixel(x, y, z) {
    if (!state.mapProjection) return { mx: 0, my: 0 };
    const p = state.mapProjection;
    const u = x * p.right.x + y * p.right.y + z * p.right.z;
    const v = x * p.upAxis.x + y * p.upAxis.y + z * p.upAxis.z;
    const mx = ((u - p.minU) / p.projW) * p.mapW;
    const my = ((p.maxV - v) / p.projH) * p.mapH;
    return { mx, my };
  }

  function worldXZToMapPixel(x, z) {
    return worldToMapPixel(x, 0, z);
  }

  function mapPixelToWorldXZ(mx, my) {
    if (!state.mapProjection || Math.abs(state.mapProjection.det) < 1e-7) return { x: 0, z: 0 };
    const p = state.mapProjection;
    const u = p.minU + (mx / p.mapW) * p.projW;
    const v = p.maxV - (my / p.mapH) * p.projH;
    const x = (u * p.upAxis.z - p.right.z * v) / p.det;
    const z = (p.right.x * v - u * p.upAxis.x) / p.det;
    return { x, z };
  }

  function rasterizeTriangleToGrid(grid, gw, gh, p0, p1, p2, flag) {
    const minX = Math.max(0, Math.floor(Math.min(p0.gx, p1.gx, p2.gx)));
    const maxX = Math.min(gw - 1, Math.ceil(Math.max(p0.gx, p1.gx, p2.gx)));
    const minY = Math.max(0, Math.floor(Math.min(p0.gy, p1.gy, p2.gy)));
    const maxY = Math.min(gh - 1, Math.ceil(Math.max(p0.gy, p1.gy, p2.gy)));

    const denom = (p1.gy - p2.gy) * (p0.gx - p2.gx) + (p2.gx - p1.gx) * (p0.gy - p2.gy);
    if (Math.abs(denom) < 1e-5) return;

    const invDenom = 1.0 / denom;
    for (let y = minY; y <= maxY; y++) {
      for (let x = minX; x <= maxX; x++) {
        const w0 = ((p1.gy - p2.gy) * (x - p2.gx) + (p2.gx - p1.gx) * (y - p2.gy)) * invDenom;
        const w1 = ((p2.gy - p0.gy) * (x - p2.gx) + (p0.gx - p2.gx) * (y - p2.gy)) * invDenom;
        const w2 = 1.0 - w0 - w1;
        if (w0 >= -0.05 && w1 >= -0.05 && w2 >= -0.05) {
          grid[y * gw + x] |= flag;
        }
      }
    }
  }

  function buildMapCollisionGrid() {
    if (!state.map?.model || !state.mapProjection) return;
    const p = state.mapProjection;
    const CELL = 4;
    const gw = Math.ceil(p.mapW / CELL);
    const gh = Math.ceil(p.mapH / CELL);
    const grid = new Uint8Array(gw * gh);
    state.mapWalkGrid = grid;
    state.mapWalkGridW = gw;
    state.mapWalkGridH = gh;
    state.mapHasFloorData = false;

    const v0 = new K(), v1 = new K(), v2 = new K();
    const e1 = new K(), e2 = new K(), norm = new K();

    state.map.model.updateMatrixWorld(true);
    state.map.model.traverse(node => {
      if (!node.isMesh || !node.visible || !node.geometry?.attributes?.position) return;
      const geom = node.geometry;
      const posAttr = geom.attributes.position;
      const index = geom.index;
      const numTriangles = index ? Math.floor(index.count / 3) : Math.floor(posAttr.count / 3);

      for (let t = 0; t < numTriangles; t++) {
        const i0 = index ? index.getX(t * 3 + 0) : t * 3 + 0;
        const i1 = index ? index.getX(t * 3 + 1) : t * 3 + 1;
        const i2 = index ? index.getX(t * 3 + 2) : t * 3 + 2;

        v0.fromBufferAttribute(posAttr, i0).applyMatrix4(node.matrixWorld);
        v1.fromBufferAttribute(posAttr, i1).applyMatrix4(node.matrixWorld);
        v2.fromBufferAttribute(posAttr, i2).applyMatrix4(node.matrixWorld);

        e1.subVectors(v1, v0);
        e2.subVectors(v2, v0);
        norm.crossVectors(e1, e2);
        const area = 0.5 * norm.length();
        if (area <= 1e-6) continue;
        norm.normalize();

        const midY = (v0.y + v1.y + v2.y) / 3;
        const minY = Math.min(v0.y, v1.y, v2.y);
        const maxY = Math.max(v0.y, v1.y, v2.y);

        // Floor: horizontal, normal pointing up, height near 0
        if (Math.abs(norm.y) > 0.70 && Math.abs(midY) <= 0.28 && maxY < 0.35) {
          state.mapHasFloorData = true;
          const p0 = worldXZToMapPixel(v0.x, v0.z);
          const p1 = worldXZToMapPixel(v1.x, v1.z);
          const p2 = worldXZToMapPixel(v2.x, v2.z);
          rasterizeTriangleToGrid(grid, gw, gh,
            { gx: p0.mx / CELL, gy: p0.my / CELL },
            { gx: p1.mx / CELL, gy: p1.my / CELL },
            { gx: p2.mx / CELL, gy: p2.my / CELL },
            1 // 1 = FLOOR
          );
        }
        // Obstacle/Wall/Cover: reaches above 0.30m and touches ground or is low cover top
        else if ((maxY > 0.30 && minY < 1.0) || (norm.y > 0.70 && midY > 0.30 && minY < 2.0)) {
          const g0 = worldXZToMapPixel(v0.x, v0.z);
          const g1 = worldXZToMapPixel(v1.x, v1.z);
          const g2 = worldXZToMapPixel(v2.x, v2.z);
          rasterizeTriangleToGrid(grid, gw, gh,
            { gx: g0.mx / CELL, gy: g0.my / CELL },
            { gx: g1.mx / CELL, gy: g1.my / CELL },
            { gx: g2.mx / CELL, gy: g2.my / CELL },
            2 // 2 = BLOCKED
          );
        }
      }
    });
  }

  function isMapPixelWalkable(mx, my) {
    const mapW = state.mapWidth || 768;
    const mapH = state.mapHeight || 512;
    if (mx < 16 || mx > mapW - 16 || my < 16 || my > mapH - 16) return false;

    if (!state.mapWalkGrid) return true;
    const CELL = 4;
    const gx = Math.floor(mx / CELL);
    const gy = Math.floor(my / CELL);
    const gw = state.mapWalkGridW;
    const gh = state.mapWalkGridH;
    if (gx < 1 || gx >= gw - 1 || gy < 1 || gy >= gh - 1) return false;

    const val = state.mapWalkGrid[gy * gw + gx];
    // Obstacle bit set -> cannot walk
    if ((val & 2) !== 0) return false;

    // If map has detected floor polygons, require floor bit
    if (state.mapHasFloorData) {
      return (val & 1) !== 0;
    }
    return true;
  }

  function ensureCharacterOnWalkableFloor(force = false) {
    const mapW = state.mapWidth || 768;
    const mapH = state.mapHeight || 512;
    const isDual = state.dsMode === '2';
    const dsH = isDual ? 384 : 192;

    const hasClearance = (x, y, r = 12) => {
      if (x < 24 || x > mapW - 24 || y < 24 || y > mapH - 24) return false;
      if (!isMapPixelWalkable(x, y)) return false;
      const step = 4;
      for (let dx = -r; dx <= r; dx += step) {
        for (let dy = -r; dy <= r; dy += step) {
          if (dx * dx + dy * dy <= r * r) {
            if (!isMapPixelWalkable(x + dx, y + dy)) return false;
          }
        }
      }
      return true;
    };

    // If current position is already firmly walkable with 12px clearance and not forced
    if (!force && hasClearance(state.dsCharX, state.dsCharY, 12)) {
      syncCharacter3DPositionFrom2D();
      return;
    }

    let bestX = null;
    let bestY = null;

    // Candidate open corridors in world coords
    const candidateWorlds = [
      { x: 0, z: 4.0 },
      { x: 0, z: 3.5 },
      { x: -4.0, z: -7.0 },
      { x: 3.5, z: 2.0 },
      { x: -3.5, z: 2.0 }
    ];

    if (state.mapProjection) {
      for (const cand of candidateWorlds) {
        const p = worldXZToMapPixel(cand.x, cand.z);
        if (hasClearance(p.mx, p.my, 12)) {
          bestX = Math.round(p.mx);
          bestY = Math.round(p.my);
          break;
        }
      }
    }

    // Radial search from center for an open floor position with clearance
    if (bestX === null) {
      const startX = Math.round(mapW / 2);
      const startY = Math.round(mapH / 2);
      const step = 8;
      outer: for (let r = step; r < Math.max(mapW, mapH) / 2; r += step) {
        for (let angleDeg = 0; angleDeg < 360; angleDeg += 15) {
          const rad = (angleDeg * Math.PI) / 180;
          const testX = Math.round(startX + r * Math.cos(rad));
          const testY = Math.round(startY + r * Math.sin(rad));
          if (hasClearance(testX, testY, 12)) {
            bestX = testX;
            bestY = testY;
            break outer;
          }
        }
      }
    }

    // Fallback: search with basic walkable check
    if (bestX === null) {
      const startX = Math.round(mapW / 2);
      const startY = Math.round(mapH / 2);
      outer2: for (let r = 4; r < Math.max(mapW, mapH) / 2; r += 4) {
        for (let angleDeg = 0; angleDeg < 360; angleDeg += 15) {
          const rad = (angleDeg * Math.PI) / 180;
          const testX = Math.round(startX + r * Math.cos(rad));
          const testY = Math.round(startY + r * Math.sin(rad));
          if (isMapPixelWalkable(testX, testY)) {
            bestX = testX;
            bestY = testY;
            break outer2;
          }
        }
      }
    }

    // Ultimate fallback: exhaustive scan of grid for closest walkable cell to center
    if (bestX === null && state.mapWalkGrid) {
      const gw = state.mapWalkGridW;
      const gh = state.mapWalkGridH;
      const cGx = Math.floor(mapW / (2 * 4));
      const cGy = Math.floor(mapH / (2 * 4));
      let minDistSq = Infinity;
      for (let gy = 1; gy < gh - 1; gy++) {
        for (let gx = 1; gx < gw - 1; gx++) {
          const px = gx * 4 + 2;
          const py = gy * 4 + 2;
          if (isMapPixelWalkable(px, py)) {
            const dSq = (gx - cGx) * (gx - cGx) + (gy - cGy) * (gy - cGy);
            if (dSq < minDistSq) {
              minDistSq = dSq;
              bestX = px;
              bestY = py;
            }
          }
        }
      }
    }

    if (bestX !== null && bestY !== null) {
      state.dsCharX = bestX;
      state.dsCharY = bestY;
      state.dsPanX = Math.round(state.dsCharX - 128);
      state.dsPanY = Math.round(state.dsCharY - (dsH / 2));
      syncCharacter3DPositionFrom2D();
    }
  }

  function syncCharacter3DPositionFrom2D() {
    if (!$.modelRoot || !state.mapProjection) return;
    const worldXZ = mapPixelToWorldXZ(state.dsCharX, state.dsCharY);
    if (isFinite(worldXZ.x) && isFinite(worldXZ.z)) {
      $.modelRoot.position.x = worldXZ.x;
      $.modelRoot.position.z = worldXZ.z;
      $.modelRoot.updateMatrixWorld(true);
      const pts = posedPoints($.model);
      let minY = Infinity;
      for (let i = 1; i < pts.length; i += 3) {
        if (pts[i] < minY) minY = pts[i];
      }
      if (isFinite(minY)) {
        state.lastCharMinY = minY;
        $.modelRoot.position.y -= minY;
        $.modelRoot.updateMatrixWorld(true);
      }
    }
  }

  function tryMoveCharacter(targetX, targetY) {
    const curX = state.dsCharX;
    const curY = state.dsCharY;

    if (!state.map?.loaded || !state.mapWalkGrid) {
      state.dsCharX = targetX;
      state.dsCharY = targetY;
      return true;
    }

    // Direct movement if target is walkable
    if (isMapPixelWalkable(targetX, targetY)) {
      state.dsCharX = targetX;
      state.dsCharY = targetY;
      syncCharacter3DPositionFrom2D();
      return true;
    }

    // Target is obstructed/unwalkable!
    // Try sliding along axes or stopping at obstacle boundary
    let moved = false;
    if (isMapPixelWalkable(targetX, curY)) {
      state.dsCharX = targetX;
      moved = true;
    } else if (isMapPixelWalkable(curX, targetY)) {
      state.dsCharY = targetY;
      moved = true;
    } else {
      // Bisection along movement vector to stop right outside wall
      let low = 0.0;
      let high = 1.0;
      for (let i = 0; i < 6; i++) {
        const mid = (low + high) / 2;
        const testX = curX + (targetX - curX) * mid;
        const testY = curY + (targetY - curY) * mid;
        if (isMapPixelWalkable(testX, testY)) {
          low = mid;
        } else {
          high = mid;
        }
      }
      if (low > 0.05) {
        state.dsCharX = curX + (targetX - curX) * low;
        state.dsCharY = curY + (targetY - curY) * low;
        moved = true;
      }
    }

    if (moved) {
      syncCharacter3DPositionFrom2D();
    }

    // Target itself was blocked/unwalkable, so return false
    return false;
  }

  async function exportMapPackage() {
    if (!state.mapCanvas) throw new Error('Renderiza el mapa antes de exportar');
    const name = (state.map?.name || 'mapa_dungeon').replace(/\.[^/.]+$/, '').replace(/[^a-z0-9_-]+/gi, '_');
    const zip = new Nf.default();

    const pngBlob = await new Promise((resolve, reject) => {
      state.mapCanvas.toBlob(b => b ? resolve(b) : reject(new Error('Fallo al crear PNG de mapa')), 'image/png');
    });
    zip.file(`${name}_world.png`, pngBlob);

    const mapW = state.mapWidth;
    const mapH = state.mapHeight;
    const orthoScale = state.mapOrthoScale;
    const settings = {
      mapName: name,
      width: mapW,
      height: mapH,
      orthoScaleMeters: orthoScale,
      pixelsPerMeter: Number((mapW / orthoScale).toFixed(2)),
      meshScale: parseFloat(document.getElementById('mapMeshScale')?.value) || 24.0,
      cameraElevationDegrees: parseFloat(document.getElementById('elevation')?.value) || 30.0,
      contrast: parseFloat(_p.contrast?.value) || 1.5,
      saturation: parseFloat(_p.saturation?.value) || 1.15,
      brightness: parseFloat(document.getElementById('labBrightness')?.value) || 1.0,
      lighting: {
        preset: document.getElementById('lightPreset')?.value || 'warm',
        key: parseFloat(document.getElementById('keyLight')?.value || 4.2),
        fill: parseFloat(document.getElementById('fillLight')?.value || 1.2),
        rim: parseFloat(document.getElementById('rimLight')?.value || 0.0),
        world: parseFloat(document.getElementById('worldLight')?.value || 0.35)
      }
    };
    zip.file(`${name}_map_settings.json`, JSON.stringify(settings, null, 2));
    return zip.generateAsync({ type: 'blob' });
  }

  // ---- Real-Time Live Preview & Reactivity ----

  let livePreviewRaf = null;

  function scheduleLivePreview(highQuality = false, updateMap = false) {
    if (livePreviewRaf) cancelAnimationFrame(livePreviewRaf);
    livePreviewRaf = requestAnimationFrame(async () => {
      livePreviewRaf = null;
      renderLiveFrame(highQuality);
      if (updateMap && state.map?.loaded) {
        await renderMap(highQuality);
      }
    });
  }

  function renderLiveFrame(highQuality = false) {
    if (!$.modelRoot || !$.renderer || $.rendering) {
      drawDsSimulator();
      return;
    }
    const size = parseInt(_p.resolution.value, 10) || 48;
    const ss = highQuality ? (state.supersample || 4) : 1;
    const outline = _p.outlineMode.value !== 'none';
    const targetPixels = size - (outline ? 2 : 0);

    const prevSize = new G();
    $.renderer.getSize(prevSize);
    const root = $.modelRoot;
    const prevYaw = root.rotation.y;
    const prevY = root.position.y;
    const prevMapVis = state.mapGroup ? state.mapGroup.visible : false;
    if (state.mapGroup) state.mapGroup.visible = false;
    root.visible = true;

    applyBlenderLighting();
    setupModelMaterials($.model);

    try {
      const fit = computeCharacterFit(size, targetPixels);
      const camera = fit.camera;
      $.renderer.setClearColor(0x000000, 0);
      $.renderer.setSize(size * ss, size * ss, false);

      const params = {
        resolution: size,
        contrast: parseFloat(_p.contrast.value) || 1.5,
        saturation: parseFloat(_p.saturation.value) || 1.15,
        brightness: parseFloat(document.getElementById('labBrightness')?.value) || 1.0,
        outlineMode: _p.outlineMode.value
      };

      state.liveDirCanvases = [];

      for (let direction = 0; direction < Ff.length; direction++) {
        root.rotation.y = DIR0_YAW - direction * DIR_STEP;
        root.position.y = -fit.minY;
        root.updateMatrixWorld(true);
        $.renderer.render($.scene, camera);

        let pixels = Gf($.renderer, size * ss, size * ss);
        if (!(pixels instanceof Uint8ClampedArray)) pixels = new Uint8ClampedArray(pixels.buffer);
        if (ss > 1) pixels = downsample(pixels, size, ss, state.filterWidth);
        const graded = zf(pixels, params.contrast, params.saturation);
        if (params.brightness !== 1.0) {
          for (let i = 0; i < graded.length; i += 4) {
            graded[i] *= params.brightness;
            graded[i + 1] *= params.brightness;
            graded[i + 2] *= params.brightness;
          }
        }
        let processed = Rf(graded, size, size, params.outlineMode);
        if (!(processed instanceof Uint8ClampedArray)) processed = new Uint8ClampedArray(processed);

        const cardCanvas = document.querySelector(`.dir-live-canvas[data-dir="${direction}"]`);
        if (cardCanvas) {
          cardCanvas.width = size;
          cardCanvas.height = size;
          const ctx = cardCanvas.getContext('2d');
          ctx.putImageData(new ImageData(processed, size, size), 0, 0);
          cardCanvas.style.display = 'block';
          const cardImg = document.querySelector(`.dir-gif-img[data-dir="${direction}"]`);
          if (cardImg) cardImg.style.display = 'none';
        }
        const cardLabel = document.querySelector(`.dir-card[data-dir="${direction}"] .dir-card-label`);
        if (cardLabel) {
          cardLabel.textContent = `${Ff[direction]} (${size}×${size})`;
        }
        state.liveDirCanvases[direction] = { pixels: processed, width: size, height: size };
      }
    } finally {
      root.rotation.y = prevYaw;
      root.position.y = prevY;
      root.updateMatrixWorld(true);
      if (state.mapGroup) state.mapGroup.visible = prevMapVis;
      syncViewportRendererSize();
      update3DViewMode();
      groundCharacterIn3D();
    }
    drawDsSimulator();
  }

  // ---- Nintendo DS Simulator Canvas ----

  function drawDsSimulator() {
    const canvas = document.getElementById('dsSimCanvas');
    if (!canvas) return;
    const isDual = state.dsMode === '2';
    const dsW = 256;
    const dsH = isDual ? 384 : 192;
    if (canvas.width !== dsW || canvas.height !== dsH) {
      canvas.width = dsW;
      canvas.height = dsH;
    }
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;

    // Always clear canvas to solid black before drawing background (eliminates ghosting)
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, dsW, dsH);

    // Draw background (Map or procedural dungeon grid)
    if (state.mapCanvas) {
      ctx.drawImage(state.mapCanvas, -state.dsPanX, -state.dsPanY);
    } else {
      ctx.fillStyle = '#0d1017';
      ctx.fillRect(0, 0, dsW, dsH);
      ctx.strokeStyle = '#1b2030';
      ctx.lineWidth = 1;
      const tileW = 32, tileH = 16;
      const offsetX = (-state.dsPanX) % tileW;
      const offsetY = (-state.dsPanY) % tileH;
      for (let x = offsetX - tileW; x < dsW + tileW; x += tileW) {
        for (let y = offsetY - tileH; y < dsH + tileH; y += tileH) {
          ctx.beginPath();
          ctx.moveTo(x, y + tileH / 2);
          ctx.lineTo(x + tileW / 2, y);
          ctx.lineTo(x + tileW, y + tileH / 2);
          ctx.lineTo(x + tileW / 2, y + tileH);
          ctx.closePath();
          ctx.stroke();
        }
      }
      ctx.fillStyle = '#3a445d';
      ctx.font = '9px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('Sin mapa 3D: Carga un .FBX/.GLB o mueve con WASD', dsW / 2, isDual ? 180 : 30);
    }

    // Character drawing
    const spriteSize = parseInt(_p.resolution?.value, 10) || 48;
    const screenX = state.dsCharX - state.dsPanX;
    const screenY = state.dsCharY - state.dsPanY;

    // Shadow ellipse under character
    ctx.fillStyle = 'rgba(0, 0, 0, 0.45)';
    ctx.beginPath();
    ctx.ellipse(screenX, screenY - 2, spriteSize * 0.22, spriteSize * 0.11, 0, 0, Math.PI * 2);
    ctx.fill();

    // Sprite drawing
    const curDir = state.dsCharDir || 0;
    const frameCount = parseInt(_p.frameCount?.value, 10) || 8;
    const frames = getFrames();

    if (frames.length === Ff.length * frameCount) {
      const fIdx = (curDir * frameCount) + (state.charAnimFrame % frameCount);
      const frame = frames[fIdx];
      if (frame) {
        if (!state.tempSpriteCanvas) state.tempSpriteCanvas = document.createElement('canvas');
        state.tempSpriteCanvas.width = frame.width;
        state.tempSpriteCanvas.height = frame.height;
        state.tempSpriteCanvas.getContext('2d').putImageData(new ImageData(frame.pixels, frame.width, frame.height), 0, 0);
        ctx.drawImage(state.tempSpriteCanvas, Math.round(screenX - frame.width / 2), Math.round(screenY - frame.height + 4));
      }
    } else {
      const liveData = state.liveDirCanvases[curDir];
      if (liveData) {
        if (!state.tempSpriteCanvas) state.tempSpriteCanvas = document.createElement('canvas');
        state.tempSpriteCanvas.width = liveData.width;
        state.tempSpriteCanvas.height = liveData.height;
        state.tempSpriteCanvas.getContext('2d').putImageData(new ImageData(liveData.pixels, liveData.width, liveData.height), 0, 0);
        ctx.drawImage(state.tempSpriteCanvas, Math.round(screenX - liveData.width / 2), Math.round(screenY - liveData.height + 4));
      } else {
        ctx.fillStyle = '#00a8ff';
        ctx.beginPath();
        ctx.arc(screenX, screenY - spriteSize / 2, spriteSize / 3, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Dual screen division line
    if (isDual) {
      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 191, dsW, 2);
      ctx.fillStyle = '#ff4757';
      ctx.fillRect(0, 191, 6, 2);
      ctx.fillRect(dsW - 6, 191, 6, 2);
    }

    updateDsMetricsBadge();
  }

  function updateDsMetricsBadge() {
    const badge = document.getElementById('dsMetricsBadge');
    if (!badge) return;
    const spriteSize = parseInt(_p.resolution?.value, 10) || 48;
    const mapW = state.mapWidth || parseInt(document.getElementById('mapPixelSize')?.value, 10) || 768;
    const mapH = state.mapHeight || 512;
    const dsH = state.dsMode === '2' ? 384 : 192;
    badge.textContent = `Sprite: ${spriteSize}×${spriteSize}px | Mapa: ${mapW}×${mapH}px | DS: 256×${dsH}px`;
  }

  function updateMapDensityLabel() {
    const lbl = document.getElementById('mapDensityBadge');
    if (!lbl) return;
    const mapW = state.mapWidth || parseInt(document.getElementById('mapPixelSize')?.value, 10) || 768;
    const mapH = state.mapHeight || 512;
    lbl.textContent = `${mapW} × ${mapH} px`;
  }

  function vectorToDir8(dx, dy) {
    if (Math.abs(dx) < 0.2 && Math.abs(dy) < 0.2) return state.dsCharDir;
    const angle = Math.atan2(dy, dx);
    let deg = angle * (180 / Math.PI);
    let shifted = deg - 90;
    if (shifted < -180) shifted += 360;
    if (shifted > 180) shifted -= 360;
    let dir = Math.round(shifted / 45);
    if (dir < 0) dir += 8;
    return (dir % 8);
  }

  function selectDirection(dirIndex) {
    state.dsCharDir = dirIndex % 8;
    document.querySelectorAll('.dir-card').forEach((card, idx) => {
      card.classList.toggle('active', idx === state.dsCharDir);
    });
    drawDsSimulator();
  }

  function updateTopStripGifs(results) {
    results.forEach(res => {
      const cardCanvas = document.querySelector(`.dir-live-canvas[data-dir="${res.index}"]`);
      const cardImg = document.querySelector(`.dir-gif-img[data-dir="${res.index}"]`);
      if (cardCanvas && cardImg) {
        cardImg.src = res.url;
        cardImg.style.display = 'block';
        cardCanvas.style.display = 'none';
      }
    });
  }

  function syncViewportRendererSize() {
    const area = document.getElementById('canvasArea');
    if (!area || !$.renderer || !$.camera) return;
    const w = Math.max(1, area.clientWidth || 500);
    const h = Math.max(1, area.clientHeight || 500);
    $.renderer.setSize(w, h, false);
    $.camera.aspect = w / h;
    $.camera.updateProjectionMatrix();
  }

  function update3DViewMode() {
    const mode = document.getElementById('viewer3dMode')?.value || 'both';
    if ($.modelRoot) {
      $.modelRoot.visible = (mode === 'char' || mode === 'both');
    }
    if (state.mapGroup) {
      state.mapGroup.visible = (mode === 'map' || mode === 'both');
    }
    syncViewportRendererSize();
    if ($.camera && $.controls) {
      if (mode === 'map' || mode === 'both') {
        $.camera.near = 0.1;
        $.camera.far = 1000;
        $.camera.updateProjectionMatrix();
        $.camera.position.set(16, 14, 16);
        $.controls.target.set(0, 1.0, 0);
        $.controls.update();
      } else if (mode === 'char') {
        $.camera.near = 0.1;
        $.camera.far = 100;
        $.camera.updateProjectionMatrix();
        $.camera.position.set(0, 1.4, 3.2);
        $.controls.target.set(0, 0.9, 0);
        $.controls.update();
      }
    }
  }

  // ---- Build New UI DOM & CSS ----

  function injectStyles() {
    if (document.getElementById('labRedesignStyles')) return;
    const style = document.createElement('style');
    style.id = 'labRedesignStyles';
    style.textContent = `
      :root {
        --bg: #0b0c10;
        --panel: #13161f;
        --card: #1c202d;
        --card-hover: #262c3e;
        --border: #2a3144;
        --accent: #e64a19;
        --accent-hover: #d84315;
        --blue: #00a8ff;
        --blue-hover: #0097e6;
        --green: #22c55e;
        --text: #f5f6fa;
        --muted: #8c92a4;
      }
      html, body {
        height: 100vh !important;
        max-height: 100vh !important;
        min-height: 100vh !important;
        overflow: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
        display: flex !important;
        flex-direction: column !important;
        box-sizing: border-box !important;
      }
      header {
        height: 48px !important;
        min-height: 48px !important;
        max-height: 48px !important;
        padding: 0 16px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        border-bottom: 1px solid var(--border) !important;
        background: var(--panel) !important;
        flex-shrink: 0 !important;
      }
      main {
        height: calc(100vh - 48px) !important;
        max-height: calc(100vh - 48px) !important;
        min-height: 0 !important;
        display: grid !important;
        grid-template-columns: 330px 430px 1fr !important;
        gap: 8px !important;
        padding: 8px !important;
        overflow: hidden !important;
        box-sizing: border-box !important;
      }
      #labLeftSidebar {
        width: 330px !important;
        min-width: 330px !important;
        max-width: 330px !important;
        height: 100% !important;
        background: var(--panel) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        display: flex !important;
        flex-direction: column !important;
        overflow: hidden !important;
        flex-shrink: 0 !important;
      }
      .lab-tabs {
        display: flex !important;
        border-bottom: 1px solid var(--border) !important;
        background: #0f121a !important;
        flex-shrink: 0 !important;
      }
      .lab-tab-btn {
        flex: 1 !important;
        padding: 10px 4px !important;
        background: transparent !important;
        border: none !important;
        color: var(--muted) !important;
        font-size: 0.74rem !important;
        font-weight: 700 !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        text-align: center !important;
        border-bottom: 2px solid transparent !important;
      }
      .lab-tab-btn:hover {
        color: var(--text) !important;
      }
      .lab-tab-btn.active {
        color: var(--blue) !important;
        border-bottom-color: var(--blue) !important;
        background: var(--panel) !important;
      }
      .lab-tab-pane {
        display: none !important;
        flex: 1 !important;
        min-height: 0 !important;
        overflow-y: auto !important;
        padding: 10px !important;
        flex-direction: column !important;
        gap: 10px !important;
      }
      .lab-tab-pane.active {
        display: flex !important;
      }
      .lab-section-card {
        background: var(--card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 6px !important;
        padding: 10px !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 8px !important;
      }
      .lab-section-title {
        color: #a4b0be !important;
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        border-bottom: 1px solid rgba(255,255,255,0.06) !important;
        padding-bottom: 4px !important;
      }
      .lab-control-row {
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 8px !important;
      }
      .lab-control-group {
        display: flex !important;
        flex-direction: column !important;
        gap: 3px !important;
      }
      .lab-control-group label {
        font-size: 0.74rem !important;
        color: #dcdde1 !important;
        display: flex !important;
        justify-content: space-between !important;
      }
      .lab-control-group .val {
        color: var(--blue) !important;
        font-family: monospace !important;
        font-size: 0.72rem !important;
        font-weight: bold !important;
      }
      .lab-actions-bar {
        border-top: 1px solid var(--border) !important;
        background: #10131b !important;
        padding: 8px 10px !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 6px !important;
        flex-shrink: 0 !important;
      }
      .lab-btn-row {
        display: grid !important;
        grid-template-columns: 1fr 1fr !important;
        gap: 6px !important;
      }

      /* Column 2: Dedicated Full-Height 8-Directions Grid */
      #labCenterPanel {
        width: 430px !important;
        min-width: 430px !important;
        max-width: 430px !important;
        height: 100% !important;
        background: var(--panel) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        display: flex !important;
        flex-direction: column !important;
        overflow: hidden !important;
        flex-shrink: 0 !important;
      }
      .lab-col2-header {
        height: 38px !important;
        min-height: 38px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        padding: 0 10px !important;
        background: #0f121a !important;
        border-bottom: 1px solid var(--border) !important;
        flex-shrink: 0 !important;
      }
      #gifsGrid {
        display: grid !important;
        grid-template-columns: repeat(2, 1fr) !important;
        grid-template-rows: repeat(4, 1fr) !important;
        gap: 6px !important;
        flex: 1 !important;
        min-height: 0 !important;
        padding: 6px !important;
        margin: 0 !important;
        box-sizing: border-box !important;
      }
      .dir-card {
        background: var(--card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 6px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: space-between !important;
        padding: 4px !important;
        position: relative !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        user-select: none !important;
        min-height: 0 !important;
        height: 100% !important;
        box-sizing: border-box !important;
      }
      .dir-card:hover {
        background: var(--card-hover) !important;
        border-color: var(--blue) !important;
      }
      .dir-card.active {
        border-color: var(--blue) !important;
        box-shadow: 0 0 0 1px var(--blue) inset !important;
        background: rgba(0, 168, 255, 0.08) !important;
      }
      .dir-canvas-wrap {
        flex: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
        min-height: 0 !important;
        overflow: hidden !important;
      }
      .dir-live-canvas, .dir-gif-img {
        image-rendering: pixelated !important;
        image-rendering: crisp-edges !important;
        width: auto !important;
        height: calc(100% - 24px) !important;
        max-width: 100% !important;
        aspect-ratio: 1 / 1 !important;
        object-fit: contain !important;
      }
      .dir-card-label {
        height: 18px !important;
        line-height: 18px !important;
        font-size: 0.68rem !important;
        color: var(--muted) !important;
        font-family: monospace !important;
        font-weight: 600 !important;
        text-align: center !important;
        background: rgba(0,0,0,0.6) !important;
        border-radius: 3px !important;
        padding: 0 4px !important;
        width: 90% !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        margin-top: 2px !important;
      }
      .dir-card.active .dir-card-label {
        color: var(--blue) !important;
      }

      /* Column 3: Full-Height Main Stage with 2 Top Tabs */
      #labRightStage {
        flex: 1 !important;
        min-width: 0 !important;
        height: 100% !important;
        background: var(--panel) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        display: flex !important;
        flex-direction: column !important;
        overflow: hidden !important;
      }
      .stage-tabs {
        display: flex !important;
        height: 38px !important;
        min-height: 38px !important;
        border-bottom: 1px solid var(--border) !important;
        background: #0f121a !important;
        flex-shrink: 0 !important;
      }
      .stage-tab-btn {
        flex: 1 !important;
        padding: 0 12px !important;
        background: transparent !important;
        border: none !important;
        color: var(--muted) !important;
        font-size: 0.76rem !important;
        font-weight: 700 !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        text-align: center !important;
        border-bottom: 2px solid transparent !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 6px !important;
      }
      .stage-tab-btn:hover {
        color: var(--text) !important;
      }
      .stage-tab-btn.active {
        color: var(--text) !important;
        border-bottom-color: var(--blue) !important;
        background: var(--panel) !important;
      }
      .stage-pane {
        flex: 1 !important;
        min-height: 0 !important;
        overflow: hidden !important;
        display: none !important;
        flex-direction: column !important;
      }
      .stage-pane.active {
        display: flex !important;
      }
      #canvasArea {
        height: 100% !important;
        max-height: none !important;
        min-height: 0 !important;
        flex: 1 !important;
        position: relative !important;
        border-radius: 0 !important;
        background: #090a0f !important;
        overflow: hidden !important;
        border: none !important;
      }
      .viewer3d-toolbar {
        position: absolute !important;
        top: 8px !important;
        left: 8px !important;
        right: 8px !important;
        z-index: 5 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        background: rgba(22, 25, 34, 0.85) !important;
        backdrop-filter: blur(6px) !important;
        border: 1px solid var(--border) !important;
        border-radius: 6px !important;
        padding: 4px 8px !important;
        font-size: 0.72rem !important;
      }
      #dsSimPanel {
        height: 100% !important;
        min-height: 0 !important;
        display: flex !important;
        flex-direction: column !important;
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        overflow: hidden !important;
      }
      .ds-sim-toolbar {
        padding: 6px 10px !important;
        background: #11141c !important;
        border-bottom: 1px solid var(--border) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        flex-shrink: 0 !important;
        gap: 6px !important;
        font-size: 0.72rem !important;
        flex-wrap: wrap !important;
      }
      .ds-sim-viewport {
        flex: 1 !important;
        min-height: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: #050608 !important;
        position: relative !important;
        overflow: hidden !important;
        cursor: grab !important;
      }
      .ds-sim-viewport:active {
        cursor: grabbing !important;
      }
      #dsSimCanvas {
        image-rendering: pixelated !important;
        image-rendering: crisp-edges !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.8) !important;
        border: 1px solid #333 !important;
        display: block !important;
      }
    `;
    document.head.appendChild(style);
  }

  function restructureLayout() {
    injectStyles();

    const main = document.querySelector('main');
    if (!main || main.dataset.restructured) return;
    main.dataset.restructured = 'true';

    // Capture existing DOM nodes
    const fbxInput = document.getElementById('fbxInput');
    const fileName = document.getElementById('fileName');
    const resolution = document.getElementById('resolution');
    const resVal = document.getElementById('resVal');
    const frameCount = document.getElementById('frameCount');
    const framesVal = document.getElementById('framesVal');
    const elevation = document.getElementById('elevation');
    const elevVal = document.getElementById('elevVal');
    const animSelect = document.getElementById('animSelect');
    const inPlaceMotion = document.getElementById('inPlaceMotion');
    const lightPreset = document.getElementById('lightPreset');
    const keyLight = document.getElementById('keyLight');
    const keyLightVal = document.getElementById('keyLightVal');
    const keyColor = document.getElementById('keyColor');
    const fillLight = document.getElementById('fillLight');
    const fillLightVal = document.getElementById('fillLightVal');
    const fillColor = document.getElementById('fillColor');
    const rimLight = document.getElementById('rimLight');
    const rimLightVal = document.getElementById('rimLightVal');
    const rimColor = document.getElementById('rimColor');
    const worldLight = document.getElementById('worldLight');
    const worldLightVal = document.getElementById('worldLightVal');
    const shadowToggle = document.getElementById('shadowToggle');
    const contrast = document.getElementById('contrast');
    const contVal = document.getElementById('contVal');
    const saturation = document.getElementById('saturation');
    const satVal = document.getElementById('satVal');
    const outlineMode = document.getElementById('outlineMode');
    const btnRender = document.getElementById('btnRender');
    const btnExportZip = document.getElementById('btnExportZip');
    const btnLoadDemo = document.getElementById('btnLoadDemo');
    const progressBar = document.getElementById('progressBar');
    const canvasArea = document.getElementById('canvasArea');
    const gifsGrid = document.getElementById('gifsGrid');
    const visibleSize = document.getElementById('visibleSize');

    // Preset desired defaults on inputs
    if (resolution) resolution.value = '48';
    if (resVal) resVal.textContent = '48 × 48 px';
    if (contrast) contrast.value = '1.50';
    if (contVal) contVal.textContent = '1.50';
    if (elevation) elevation.value = '30';
    if (elevVal) elevVal.textContent = '30°';
    if (lightPreset) lightPreset.value = 'warm';

    // Remove legacy containers
    const oldControls = document.querySelector('.controls');
    if (oldControls) oldControls.remove();
    const oldStatusBar = document.querySelector('.status-bar');
    if (oldStatusBar) oldStatusBar.remove();
    const oldDownloadAll = document.getElementById('btnDownloadAll');
    if (oldDownloadAll) oldDownloadAll.remove();

    // Build Left Sidebar
    const sidebar = document.createElement('div');
    sidebar.id = 'labLeftSidebar';
    sidebar.innerHTML = `
      <div class="lab-tabs">
        <button class="lab-tab-btn active" data-tab="scale">Escala y Archivos</button>
        <button class="lab-tab-btn" data-tab="light">Luz y Cámara</button>
        <button class="lab-tab-btn" data-tab="shader">Shader y Post</button>
      </div>

      <div class="lab-tab-pane active" id="pane-scale">
        <div class="lab-section-card" id="card-character">
          <div class="lab-section-title">
            <span>Personaje 3D (.FBX)</span>
            <span class="val" id="fileNameBadge" style="font-size:0.7rem;">Ninguno</span>
          </div>
          <div class="lab-control-group" id="group-fbx-btn">
            <label for="fbxInput" class="btn secondary" style="width:100%; text-align:center; padding:8px; font-size:0.78rem; cursor:pointer;">Seleccionar FBX</label>
          </div>
          <div class="lab-control-row">
            <div class="lab-control-group" id="group-anim">
              <label>Clip Animación <span class="val" id="animVal" style="display:none;"></span></label>
            </div>
            <div class="lab-control-group" id="group-inplace">
              <label for="inPlaceMotion">In-place <span class="val" id="inPlaceStatus" style="display:none;"></span></label>
              <div style="display:flex; align-items:center; height:32px; gap:6px;" id="wrap-inplace">
                <span style="font-size:0.72rem; color:var(--muted);">Fijar raíz</span>
              </div>
            </div>
          </div>
          <div class="lab-control-group" id="group-res">
            <label>Tamaño Personaje (px) <span class="val" id="resVal">48 × 48 px</span></label>
          </div>
          <div class="lab-control-row">
            <div class="lab-control-group" id="group-frames">
              <label>Frames/dir <span class="val" id="framesVal">8</span></label>
            </div>
            <div class="lab-control-group">
              <label>Ticks / frame</label>
              <input id="animTicks" type="number" min="1" max="10" step="1" value="3" style="padding:6px; font-size:0.75rem;">
            </div>
          </div>
          <div class="lab-control-group" id="group-demo-btn" style="margin-top:2px;"></div>
        </div>

        <div class="lab-section-card" id="card-map">
          <div class="lab-section-title">
            <span>Mapa / Entorno 3D (.FBX/.GLB)</span>
            <span class="val" id="mapFileName" style="font-size:0.7rem;">Ninguno</span>
          </div>
          <input type="file" id="mapFileInput" accept=".fbx,.glb" style="display:none;">
          <button class="btn secondary" id="btnTriggerMapFile" style="width:100%; padding:8px; font-size:0.78rem;">Cargar Mapa 3D (.FBX/.GLB)</button>
          <div class="lab-control-group">
            <label>Tamaño Mapa (px) <span class="val" id="mapPixelSizeVal">768 px</span></label>
            <input type="range" id="mapPixelSize" min="256" max="1536" step="16" value="768">
          </div>
          <div class="lab-control-row" style="align-items:center;">
            <div class="lab-control-group">
              <label style="align-items:center; gap:6px; cursor:pointer;">
                <input type="checkbox" id="mapAutoLevel" checked style="accent-color:var(--blue); width:auto;">
                <span>Auto-nivelar suelo Z=0</span>
              </label>
            </div>
            <div class="lab-control-group" style="text-align:right;">
              <span class="val" id="mapDensityBadge" style="font-size:0.72rem; color:var(--blue);">768 × 512 px</span>
            </div>
          </div>
        </div>
      </div>

      <div class="lab-tab-pane" id="pane-light">
        <div class="lab-section-card">
          <div class="lab-section-title">
            <span>Iluminación Compartida</span>
            <span class="val" id="presetLabel">warm</span>
          </div>
          <div class="lab-control-group" id="group-preset">
            <label>Preset Iluminación</label>
          </div>
          <div class="lab-control-group" id="group-elevation">
            <label>Elevación Cámara <span class="val" id="elevVal">30°</span></label>
          </div>
          <div class="lab-control-row">
            <div class="lab-control-group" id="group-keylight">
              <label>Luz Principal <span class="val" id="keyLightVal">4.2</span></label>
            </div>
            <div class="lab-control-group" id="group-filllight">
              <label>Relleno Frío <span class="val" id="fillLightVal">1.20</span></label>
            </div>
          </div>
          <div class="lab-control-row">
            <div class="lab-control-group" id="group-rimlight">
              <label>Contraluz <span class="val" id="rimLightVal">0.00</span></label>
            </div>
            <div class="lab-control-group" id="group-worldlight">
              <label>Luz Ambiente <span class="val" id="worldLightVal">0.35</span></label>
            </div>
          </div>
          <div class="lab-control-row">
            <div class="lab-control-group">
              <label>Suavidad Sombra <span class="val" id="labShadowValue">2°</span></label>
              <input id="labShadow" type="range" min="0.5" max="18" step="0.5" value="2">
            </div>
            <div class="lab-control-group">
              <label>Relieve Normal <span class="val" id="labNormalValue">0.35</span></label>
              <input id="labNormal" type="range" min="0.5" max="0.8" step="0.05" value="0.35">
            </div>
          </div>
        </div>
      </div>

      <div class="lab-tab-pane" id="pane-shader">
        <div class="lab-section-card">
          <div class="lab-section-title">Shader y Post-Procesado</div>
          <div class="lab-control-row">
            <div class="lab-control-group" id="group-contrast">
              <label>Contraste <span class="val" id="contVal">1.50</span></label>
            </div>
            <div class="lab-control-group" id="group-saturation">
              <label>Saturación <span class="val" id="satVal">1.15</span></label>
            </div>
          </div>
          <div class="lab-control-row">
            <div class="lab-control-group">
              <label>Brillo <span class="val" id="labBrightnessValue">1.00</span></label>
              <input id="labBrightness" type="range" min="0.5" max="1.5" step="0.05" value="1.0">
            </div>
            <div class="lab-control-group" id="group-outline">
              <label>Outline (Sprite) <span class="val" id="outlineVal">Pixel-art (1px)</span></label>
            </div>
          </div>
          <div class="lab-control-row">
            <div class="lab-control-group">
              <label>Inclinación cuello (°)</label>
              <input id="neckPitch" type="number" min="-90" max="90" step="1" value="0" style="padding:6px; font-size:0.75rem;">
            </div>
            <div class="lab-control-group">
              <label>Engrosar malla</label>
              <input id="meshDisplace" type="number" min="0" max="0.5" step="0.01" value="0" style="padding:6px; font-size:0.75rem;">
            </div>
          </div>
          <div class="lab-control-row" style="align-items:center;">
            <div class="lab-control-group">
              <label style="align-items:center; gap:6px; cursor:pointer;">
                <input id="boneShader" type="checkbox" style="accent-color:var(--blue); width:auto;">
                <span>Shader óseo</span>
              </label>
            </div>
            <div class="lab-control-group">
              <label>Supersampling</label>
              <select id="labSupersample" style="padding:6px; font-size:0.75rem;">
                <option value="1">1x (rápido)</option>
                <option value="2">2x</option>
                <option value="4" selected>4x (Blender)</option>
              </select>
            </div>
          </div>
          <div class="lab-control-group">
            <label>Muestras Sombras WebGL <span class="val" id="labSamplesValue">16</span></label>
            <input id="labSamples" type="range" min="8" max="32" step="8" value="16">
          </div>
        </div>
      </div>

      <div class="lab-actions-bar" id="labActionsBar">
        <div class="lab-btn-row" id="row-char-exports"></div>
        <div class="lab-btn-row">
          <button class="btn secondary" id="btnRenderMap" style="padding:8px 6px; font-size:0.74rem; background:#1b2336; border-color:#00a8ff;">Renderizar Mapa</button>
          <button class="btn secondary" id="btnExportMapZip" style="padding:8px 6px; font-size:0.74rem;">Exportar Mapa (.ZIP)</button>
        </div>
      </div>
      <div style="display:none;">
        <span id="fileName"></span>
        <b id="dirProgress">0/8</b>
        <b id="frameProgress">0</b>
        <b id="timeElapsed">0s</b>
        <b id="webgpuStatus"></b>
      </div>
    `;

    // Ensure visibleSize is preserved in DOM
    if (visibleSize) {
      sidebar.appendChild(visibleSize);
    } else {
      const vs = document.createElement('input');
      vs.type = 'hidden';
      vs.id = 'visibleSize';
      vs.value = '96';
      sidebar.appendChild(vs);
    }

    // Move existing inputs cleanly into the designated slots
    if (fbxInput) sidebar.querySelector('#group-fbx-btn').appendChild(fbxInput);
    if (animSelect) sidebar.querySelector('#group-anim').appendChild(animSelect);
    if (inPlaceMotion) sidebar.querySelector('#wrap-inplace').insertBefore(inPlaceMotion, sidebar.querySelector('#wrap-inplace').firstChild);
    if (resolution) sidebar.querySelector('#group-res').appendChild(resolution);
    if (frameCount) sidebar.querySelector('#group-frames').appendChild(frameCount);
    if (btnLoadDemo) {
      btnLoadDemo.style.cssText = 'padding:6px; font-size:0.75rem; width:100%;';
      sidebar.querySelector('#group-demo-btn').appendChild(btnLoadDemo);
    }

    if (lightPreset) sidebar.querySelector('#group-preset').appendChild(lightPreset);
    if (elevation) sidebar.querySelector('#group-elevation').appendChild(elevation);
    if (keyLight) sidebar.querySelector('#group-keylight').appendChild(keyLight);
    if (keyColor) {
      keyColor.style.cssText = 'height:24px; padding:0; border:none; border-radius:4px;';
      sidebar.querySelector('#group-keylight').appendChild(keyColor);
    }
    if (fillLight) sidebar.querySelector('#group-filllight').appendChild(fillLight);
    if (fillColor) {
      fillColor.style.cssText = 'height:24px; padding:0; border:none; border-radius:4px;';
      sidebar.querySelector('#group-filllight').appendChild(fillColor);
    }
    if (rimLight) sidebar.querySelector('#group-rimlight').appendChild(rimLight);
    if (rimColor) {
      rimColor.style.cssText = 'height:24px; padding:0; border:none; border-radius:4px;';
      sidebar.querySelector('#group-rimlight').appendChild(rimColor);
    }
    if (worldLight) sidebar.querySelector('#group-worldlight').appendChild(worldLight);
    if (shadowToggle) {
      const shadowWrap = document.createElement('label');
      shadowWrap.style.cssText = 'margin-top:4px; font-size:0.72rem; align-items:center; gap:6px; cursor:pointer;';
      shadowWrap.appendChild(shadowToggle);
      const span = document.createElement('span');
      span.textContent = 'Sombras Key';
      shadowWrap.appendChild(span);
      sidebar.querySelector('#group-worldlight').appendChild(shadowWrap);
    }

    if (contrast) sidebar.querySelector('#group-contrast').appendChild(contrast);
    if (saturation) sidebar.querySelector('#group-saturation').appendChild(saturation);
    if (outlineMode) sidebar.querySelector('#group-outline').appendChild(outlineMode);

    const actionsBar = sidebar.querySelector('#labActionsBar');
    if (btnRender) {
      btnRender.style.cssText = 'padding:10px; font-size:0.85rem; width:100%;';
      btnRender.textContent = 'Renderizar Animación Completa (GIFs)';
      actionsBar.insertBefore(btnRender, actionsBar.firstChild);
    }

    const charExportsRow = sidebar.querySelector('#row-char-exports');
    if (btnExportZip) {
      btnExportZip.style.cssText = 'padding:8px 6px; font-size:0.74rem;';
      btnExportZip.textContent = 'Exportar Personaje (.ZIP)';
      charExportsRow.appendChild(btnExportZip);
    }
    const btnExportAtlas = document.createElement('button');
    btnExportAtlas.className = 'btn secondary';
    btnExportAtlas.id = 'btnExportAtlas';
    btnExportAtlas.textContent = 'Spritesheet PNG';
    btnExportAtlas.style.cssText = 'padding:8px 6px; font-size:0.74rem;';
    charExportsRow.appendChild(btnExportAtlas);

    if (progressBar) {
      progressBar.style.marginTop = '2px';
      actionsBar.appendChild(progressBar);
    }

    // Column 2: Dedicated Full-Height 8-Directions Grid Panel
    const centerPanel = document.createElement('div');
    centerPanel.id = 'labCenterPanel';
    centerPanel.innerHTML = `
      <div class="lab-col2-header">
        <span style="font-size:0.74rem; font-weight:700; color:#a4b0be; letter-spacing:0.5px;">SPRITES / GIFS 8 DIRECCIONES</span>
        <span class="val" id="col2StatusBadge" style="font-size:0.7rem; color:var(--blue);">En vivo</span>
      </div>
    `;

    const grid = gifsGrid || document.createElement('div');
    grid.id = 'gifsGrid';
    grid.innerHTML = '';
    grid.style.display = 'grid';

    for (let i = 0; i < Ff.length; i++) {
      const card = document.createElement('div');
      card.className = `dir-card ${i === 0 ? 'active' : ''}`;
      card.dataset.dir = String(i);
      card.innerHTML = `
        <div class="dir-canvas-wrap">
          <canvas class="dir-live-canvas" data-dir="${i}" width="48" height="48"></canvas>
          <img class="dir-gif-img" data-dir="${i}" alt="${Ff[i]}" style="display:none;">
        </div>
        <div class="dir-card-label">${Ff[i]} (48×48)</div>
      `;
      card.addEventListener('click', () => selectDirection(i));
      grid.appendChild(card);
    }
    centerPanel.appendChild(grid);

    // Column 3: Full-Height Main Stage Panel with 2 Top Tabs
    const rightStage = document.createElement('div');
    rightStage.id = 'labRightStage';
    rightStage.innerHTML = `
      <div class="stage-tabs">
        <button class="stage-tab-btn active" data-stage="ds">🎮 Pantalla Nintendo DS (256×192)</button>
        <button class="stage-tab-btn" data-stage="3d">🧊 Visor 3D Interactivo</button>
      </div>
      <div class="stage-pane active" id="stagePaneDs">
        <div id="dsSimPanel">
          <div class="ds-sim-toolbar">
            <div style="display:flex; align-items:center; gap:6px;">
              <span style="font-weight:700; color:#fff;">Nintendo DS:</span>
              <select id="dsScreenMode" style="background:#10131b; border:1px solid var(--border); color:var(--text); border-radius:4px; padding:2px 6px; font-size:0.72rem;">
                <option value="1" selected>1 Pantalla (256×192)</option>
                <option value="2">Dual Screen (256×384)</option>
              </select>
              <select id="dsZoomMode" style="background:#10131b; border:1px solid var(--border); color:var(--text); border-radius:4px; padding:2px 6px; font-size:0.72rem;">
                <option value="fit" selected>Fit</option>
                <option value="1x">1x</option>
                <option value="2x">2x</option>
                <option value="3x">3x</option>
              </select>
            </div>
            <div style="display:flex; align-items:center; gap:6px;">
              <span id="dsMetricsBadge" style="color:var(--blue); font-family:monospace; font-size:0.7rem;">Sprite: 48×48px | DS: 256×192px</span>
              <button id="btnResetDsPos" class="btn secondary" style="padding:2px 8px; font-size:0.7rem;">Centrar</button>
            </div>
          </div>
          <div class="ds-sim-viewport" id="dsSimViewport" tabindex="0">
            <canvas id="dsSimCanvas" width="256" height="192"></canvas>
          </div>
        </div>
      </div>
      <div class="stage-pane" id="stagePane3d"></div>
    `;

    // 3D Viewport in stagePane3d
    if (canvasArea) {
      const viewerToolbar = document.createElement('div');
      viewerToolbar.className = 'viewer3d-toolbar';
      viewerToolbar.innerHTML = `
        <div style="display:flex; align-items:center; gap:6px;">
          <span style="color:var(--muted); font-weight:700;">Ver 3D:</span>
          <select id="viewer3dMode" style="background:#10131b; border:1px solid var(--border); color:var(--text); border-radius:4px; padding:2px 6px; font-size:0.72rem;">
            <option value="both" selected>Ambos (Personaje + Mapa)</option>
            <option value="char">Solo Personaje</option>
            <option value="map">Solo Mapa</option>
          </select>
        </div>
        <button id="btnResetCamera3d" class="btn secondary" style="padding:2px 8px; font-size:0.7rem;">Centrar 3D</button>
      `;
      canvasArea.insertBefore(viewerToolbar, canvasArea.firstChild);
      rightStage.querySelector('#stagePane3d').appendChild(canvasArea);
    }

    // Assemble 3-column layout inside main
    main.innerHTML = '';
    main.appendChild(sidebar);
    main.appendChild(centerPanel);
    main.appendChild(rightStage);

    setupEventListeners();
    syncViewportRendererSize();
    requestAnimationFrame(syncViewportRendererSize);
    window.addEventListener('resize', syncViewportRendererSize);
  }

  function setupEventListeners() {
    // Left Sidebar Tabs switching
    document.querySelectorAll('.lab-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.lab-tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.lab-tab-pane').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        const tab = btn.dataset.tab;
        state.activeTab = tab;
        const pane = document.getElementById(`pane-${tab}`);
        if (pane) pane.classList.add('active');
      });
    });

    // Right Stage Tabs switching (DS Simulator vs 3D Viewport)
    document.querySelectorAll('.stage-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.stage-tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const stage = btn.dataset.stage;
        const paneDs = document.getElementById('stagePaneDs');
        const pane3d = document.getElementById('stagePane3d');

        if (stage === 'ds') {
          if (paneDs) paneDs.classList.add('active');
          if (pane3d) pane3d.classList.remove('active');
          drawDsSimulator();
        } else if (stage === '3d') {
          if (paneDs) paneDs.classList.remove('active');
          if (pane3d) pane3d.classList.add('active');
          update3DViewMode();
          groundCharacterIn3D();
          sync3DRelativeScale();
          syncViewportRendererSize();
          requestAnimationFrame(syncViewportRendererSize);
        }
      });
    });

    // Map file loading button
    const triggerMapBtn = document.getElementById('btnTriggerMapFile');
    const mapFileInput = document.getElementById('mapFileInput');
    if (triggerMapBtn && mapFileInput) {
      triggerMapBtn.onclick = () => mapFileInput.click();
      mapFileInput.onchange = e => {
        const file = e.target.files?.[0];
        if (file) loadMapFile(file);
      };
    }

    // Connect slider text labels with updateMap reactivity
    const wireSlider = (id, labelId, formatter, updateMap = false) => {
      const el = document.getElementById(id);
      if (!el) return;
      const update = () => {
        const lbl = document.getElementById(labelId);
        if (lbl) lbl.textContent = formatter ? formatter(el.value) : el.value;
      };
      el.addEventListener('input', () => {
        update();
        scheduleLivePreview(false, updateMap);
      });
      el.addEventListener('change', () => {
        update();
        scheduleLivePreview(true, updateMap);
      });
    };

    wireSlider('resolution', 'resVal', v => `${v} × ${v} px`, false);
    wireSlider('mapPixelSize', 'mapPixelSizeVal', v => `${v} px`, true);
    wireSlider('frameCount', 'framesVal', v => v, false);
    wireSlider('elevation', 'elevVal', v => `${v}°`, true);
    wireSlider('contrast', 'contVal', v => parseFloat(v).toFixed(2), true);
    wireSlider('saturation', 'satVal', v => parseFloat(v).toFixed(2), true);
    wireSlider('keyLight', 'keyLightVal', v => parseFloat(v).toFixed(1), true);
    wireSlider('fillLight', 'fillLightVal', v => parseFloat(v).toFixed(2), true);
    wireSlider('rimLight', 'rimLightVal', v => parseFloat(v).toFixed(2), true);
    wireSlider('worldLight', 'worldLightVal', v => parseFloat(v).toFixed(2), true);
    wireSlider('labShadow', 'labShadowValue', v => `${v}°`, false);
    wireSlider('labNormal', 'labNormalValue', v => parseFloat(v).toFixed(2), false);
    wireSlider('labBrightness', 'labBrightnessValue', v => parseFloat(v).toFixed(2), true);
    wireSlider('labSamples', 'labSamplesValue', v => v, false);

    const resSlider = document.getElementById('resolution');
    if (resSlider) {
      const onResChange = () => {
        sync3DRelativeScale();
        updateDsMetricsBadge();
      };
      resSlider.addEventListener('input', onResChange);
      resSlider.addEventListener('change', onResChange);
    }

    const mapPxSlider = document.getElementById('mapPixelSize');
    if (mapPxSlider) {
      const onMapPxChange = () => {
        sync3DRelativeScale();
        updateDsMetricsBadge();
        updateMapDensityLabel();
      };
      mapPxSlider.addEventListener('input', onMapPxChange);
      mapPxSlider.addEventListener('change', onMapPxChange);
    }

    const mapAutoLevel = document.getElementById('mapAutoLevel');
    if (mapAutoLevel) {
      mapAutoLevel.addEventListener('change', () => {
        if (state.map?.loaded) renderMap(true);
      });
    }

    ['animTicks', 'neckPitch', 'meshDisplace'].forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener('input', () => scheduleLivePreview(false));
      el.addEventListener('change', () => scheduleLivePreview(true));
    });

    ['keyColor', 'fillColor', 'rimColor'].forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('input', () => {
          applyBlenderLighting();
          scheduleLivePreview(false, true);
        });
        el.addEventListener('change', () => {
          applyBlenderLighting();
          scheduleLivePreview(true, true);
        });
      }
    });

    const lightPreset = document.getElementById('lightPreset');
    if (lightPreset) {
      lightPreset.addEventListener('change', e => {
        const lbl = document.getElementById('presetLabel');
        if (lbl) lbl.textContent = e.target.value;
        scheduleLivePreview(true, true);
      });
    }

    const outlineMode = document.getElementById('outlineMode');
    if (outlineMode) {
      outlineMode.addEventListener('change', e => {
        const lbl = document.getElementById('outlineVal');
        if (lbl) lbl.textContent = outlineMode.selectedOptions[0]?.textContent || e.target.value;
        scheduleLivePreview(true);
      });
    }

    const boneShader = document.getElementById('boneShader');
    if (boneShader) {
      boneShader.addEventListener('change', e => {
        state.boneMode = e.target.checked;
        if (typeof applyBoneMaterial === 'function') applyBoneMaterial();
        scheduleLivePreview(true);
      });
    }

    const supersample = document.getElementById('labSupersample');
    if (supersample) {
      supersample.addEventListener('change', e => {
        state.supersample = parseInt(e.target.value, 10) || 4;
        scheduleLivePreview(true);
      });
    }

    const btnRenderMap = document.getElementById('btnRenderMap');
    if (btnRenderMap) {
      btnRenderMap.onclick = async () => {
        if (!state.map?.loaded) {
          yp('Carga un mapa 3D (.FBX/.GLB) primero', true);
          return;
        }
        bp(true, 'Renderizando mapa 3D...');
        try {
          await renderMap(true);
          yp('Mapa renderizado correctamente');
        } catch (e) {
          yp(`Error al renderizar mapa: ${e.message}`, true);
        } finally {
          bp(false);
        }
      };
    }

    const btnExportMap = document.getElementById('btnExportMapZip');
    if (btnExportMap) {
      btnExportMap.onclick = async () => {
        bp(true, 'Exportando paquete de mapa...');
        try {
          const blob = await exportMapPackage();
          const name = (state.map?.name || 'mapa_dungeon').replace(/\.[^/.]+$/, '');
          Fp(blob, `${name}_dungeon_lab.zip`);
          yp('Paquete de mapa descargado');
        } catch (e) {
          yp(`Error al exportar mapa: ${e.message}`, true);
        } finally {
          bp(false);
        }
      };
    }

    // 3D Viewport Toolbar
    const viewerMode = document.getElementById('viewer3dMode');
    if (viewerMode) {
      viewerMode.addEventListener('change', update3DViewMode);
    }

    const btnReset3d = document.getElementById('btnResetCamera3d');
    if (btnReset3d) {
      btnReset3d.onclick = () => {
        update3DViewMode();
      };
    }

    // DS Simulator Controls
    const screenMode = document.getElementById('dsScreenMode');
    if (screenMode) {
      screenMode.addEventListener('change', () => {
        state.dsMode = screenMode.value;
        applyDsZoom();
        drawDsSimulator();
      });
    }

    const zoomMode = document.getElementById('dsZoomMode');
    if (zoomMode) {
      zoomMode.addEventListener('change', () => {
        state.dsZoom = zoomMode.value;
        applyDsZoom();
      });
    }

    const btnResetDs = document.getElementById('btnResetDsPos');
    if (btnResetDs) {
      btnResetDs.onclick = () => {
        ensureCharacterOnWalkableFloor();
        groundCharacterIn3D();
        drawDsSimulator();
      };
    }

    // Character export buttons
    const btnAtlas = document.getElementById('btnExportAtlas');
    if (btnAtlas) {
      btnAtlas.onclick = async () => {
        try {
          const atlas = await makeAtlas();
          const name = (cp.textContent || 'modelo').replace(/\.fbx$/i, '');
          Fp(atlas.blob, `${name}_spritesheet.png`);
          yp(`Spritesheet PNG ${atlas.width}x${atlas.height} descargado`);
        } catch (e) {
          yp(e.message, true);
        }
      };
    }

    const btnZip = document.getElementById('btnExportZip');
    if (btnZip) {
      btnZip.onclick = async () => {
        bp(true, 'Empaquetando GIFs, spritesheet y PNGs...');
        try {
          const name = (cp.textContent || 'modelo').replace(/\.fbx$/i, '');
          Fp(await exportPackage(), `${name}_sprite_lab.zip`);
          yp('Paquete completo de personaje descargado');
        } catch (e) {
          yp(`Error al crear paquete: ${e.message}`, true);
        } finally {
          bp(false);
        }
      };
    }

    setupDsSimulatorInteractivity();
    applyDsZoom();
  }

  function applyDsZoom() {
    const canvas = document.getElementById('dsSimCanvas');
    if (!canvas) return;
    const isDual = state.dsMode === '2';
    const baseW = 256;
    const baseH = isDual ? 384 : 192;

    if (state.dsZoom === '1x') {
      canvas.style.width = `${baseW}px`;
      canvas.style.height = `${baseH}px`;
      canvas.style.maxWidth = 'none';
      canvas.style.maxHeight = 'none';
    } else if (state.dsZoom === '2x') {
      canvas.style.width = `${baseW * 2}px`;
      canvas.style.height = `${baseH * 2}px`;
      canvas.style.maxWidth = 'none';
      canvas.style.maxHeight = 'none';
    } else if (state.dsZoom === '3x') {
      canvas.style.width = `${baseW * 3}px`;
      canvas.style.height = `${baseH * 3}px`;
      canvas.style.maxWidth = 'none';
      canvas.style.maxHeight = 'none';
    } else {
      canvas.style.width = '100%';
      canvas.style.height = 'auto';
      canvas.style.maxWidth = '100%';
      canvas.style.maxHeight = '100%';
      canvas.style.aspectRatio = `${baseW} / ${baseH}`;
    }
  }

  function setupDsSimulatorInteractivity() {
    const canvas = document.getElementById('dsSimCanvas');
    const viewport = document.getElementById('dsSimViewport');
    if (!canvas || !viewport) return;

    let isDraggingChar = false;
    let isPanningMap = false;
    let lastMouseX = 0;
    let lastMouseY = 0;

    function getCanvasCoords(e) {
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      return {
        x: (e.clientX - rect.left) * scaleX,
        y: (e.clientY - rect.top) * scaleY
      };
    }

    canvas.addEventListener('mousedown', e => {
      viewport.focus();
      const pt = getCanvasCoords(e);
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;

      const screenCharX = state.dsCharX - state.dsPanX;
      const screenCharY = state.dsCharY - state.dsPanY;
      const spriteSize = parseInt(_p.resolution?.value, 10) || 48;
      const dist = Math.hypot(pt.x - screenCharX, pt.y - (screenCharY - spriteSize / 2));

      if (e.button === 0 && !e.shiftKey && dist < spriteSize * 0.75) {
        isDraggingChar = true;
      } else {
        isPanningMap = true;
      }
      e.preventDefault();
    });

    window.addEventListener('mousemove', e => {
      if (!isDraggingChar && !isPanningMap) return;
      const dx = e.clientX - lastMouseX;
      const dy = e.clientY - lastMouseY;
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;

      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;

      if (isDraggingChar) {
        const moveX = dx * scaleX;
        const moveY = dy * scaleY;
        const targetX = state.dsCharX + moveX;
        const targetY = state.dsCharY + moveY;
        const moved = tryMoveCharacter(targetX, targetY);
        if (moved) {
          const newDir = vectorToDir8(moveX, moveY);
          selectDirection(newDir);
          state.charAnimFrame = (state.charAnimFrame + 1) % 16;
          drawDsSimulator();
        }
      } else if (isPanningMap) {
        state.dsPanX -= dx * scaleX;
        state.dsPanY -= dy * scaleY;
        drawDsSimulator();
      }
    });

    window.addEventListener('mouseup', () => {
      isDraggingChar = false;
      isPanningMap = false;
    });

    viewport.addEventListener('keydown', e => {
      let moveX = 0, moveY = 0;
      const step = e.shiftKey ? 8 : 4;
      if (e.key === 'w' || e.key === 'W' || e.key === 'ArrowUp') moveY -= step;
      if (e.key === 's' || e.key === 'S' || e.key === 'ArrowDown') moveY += step;
      if (e.key === 'a' || e.key === 'A' || e.key === 'ArrowLeft') moveX -= step;
      if (e.key === 'd' || e.key === 'D' || e.key === 'ArrowRight') moveX += step;

      if (moveX !== 0 || moveY !== 0) {
        e.preventDefault();
        const targetX = state.dsCharX + moveX;
        const targetY = state.dsCharY + moveY;
        const moved = tryMoveCharacter(targetX, targetY);
        if (moved) {
          const newDir = vectorToDir8(moveX, moveY);
          selectDirection(newDir);
          state.charAnimFrame = (state.charAnimFrame + 1) % 16;
          drawDsSimulator();
        }
      }
    });
  }

  // Hook model load
  const originalAp = typeof Ap === 'function' ? Ap : null;
  if (originalAp) {
    Ap = async file => {
      await originalAp(file);
      const nameBadge = document.getElementById('fileNameBadge');
      if (nameBadge) nameBadge.textContent = file.name;
      const fn = document.getElementById('fileName');
      if (fn) fn.textContent = file.name;
      setupModelMaterials($.model);
      scheduleLivePreview(true);
    };
  }

  // Hook procedural demo
  if (sp) {
    const origDemoClick = sp.onclick;
    sp.onclick = async (...args) => {
      await origDemoClick(...args);
      const nameBadge = document.getElementById('fileNameBadge');
      if (nameBadge) nameBadge.textContent = 'demo_procedural';
      const fn = document.getElementById('fileName');
      if (fn) fn.textContent = 'demo_procedural';
      setupModelMaterials($.model);
      scheduleLivePreview(true);
    };
  }

  // Expose walkability & collision API
  state.isMapPixelWalkable = isMapPixelWalkable;
  state.worldToMapPixel = worldToMapPixel;
  state.worldXZToMapPixel = worldXZToMapPixel;
  state.mapPixelToWorldXZ = mapPixelToWorldXZ;
  state.ensureCharacterOnWalkableFloor = ensureCharacterOnWalkableFloor;
  state.tryMoveCharacter = tryMoveCharacter;
  state.syncCharacter3DPositionFrom2D = syncCharacter3DPositionFrom2D;
  state.buildMapCollisionGrid = buildMapCollisionGrid;

  // Initialize
  restructureLayout();
  applyBlenderLighting();
  drawDsSimulator();
})();
