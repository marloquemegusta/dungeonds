/* Browser-only parity layer for FBX-Web-Renderer-offline.html. */
(() => {
  // The repository's headless FBX probe evaluates inline payloads without the full page.
  if (typeof Qf !== 'function' || typeof Kf !== 'function' || typeof document === 'undefined') return;
  const state = window.__spriteLab = { frames: [], captures: [], rigScale: 1, boneMode: false };
  _p.resolution.min = '22';
  _p.resolution.max = '60';
  _p.resolution.step = '1';
  _p.resolution.value = '48';
  _p.resolution.dispatchEvent(new Event('input', { bubbles: true }));
  const originalQf = Qf;
  // Match the Blender lab's 45-degree camera azimuth.
  Wf = Math.PI / 4;

  // Blender fits the evaluated mesh pose for every animation frame and direction.
  // Three.js' default Box3 path uses the undeformed geometry bounds for skinned meshes,
  // which makes the model itself much smaller than the requested sprite cell.
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
    if (brightness !== 1) for (let index = 0; index < graded.length; index += 4) {
      graded[index] *= brightness;
      graded[index + 1] *= brightness;
      graded[index + 2] *= brightness;
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
        if (node.isSkinnedMesh) node.getVertexPosition(index, v); else v.fromBufferAttribute(position, index);
        v.applyMatrix4(node.matrixWorld);
        out.push(v.x, v.y, v.z);
      }
    });
    return out;
  }

  // Override Lf (model loader placement & wrapper creation) to avoid unskinned Box3 corruption.
  // Rigged humanoid models pivot around their armature origin (0, 0), with feet grounded at Y = 0.
  // Static meshes are grounded and centered horizontally at (0, 0).
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
  // Blender Sun/World strength S gives diffuse = albedo * S * cos; three.js divides by PI
  // (BRDF_Lambert), so light intensities are scaled by PI.
  // Direction vectors transformed from Blender (X, Y, Z-up) to Three (X, Z->Y, -Y->Z):
  // Key: target-to-light (0.4096, 0.5736, -0.7094)
  // Fill: target-to-light (-0.5318, 0.3746, 0.7595)
  function applyBlenderLighting() {
    if (!$.lights) return;
    const value = id => parseFloat(document.getElementById(id).value) || 0;
    $.lights.key.intensity = value('keyLight') * Math.PI;
    $.lights.fill.intensity = value('fillLight') * Math.PI;
    $.lights.rim.intensity = value('rimLight') * Math.PI;
    $.lights.world.intensity = value('worldLight') * Math.PI;

    $.lights.key.color.setRGB(1.0, 0.76, 0.46);
    $.lights.fill.color.setRGB(0.45, 0.55, 0.75);
    $.lights.world.color.setRGB(1.0, 1.0, 1.0);

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

        const std = new Xa({
          color: 0xffffff,
          roughness: 0.5,
          metalness: 0.0,
          map: diffuseMap,
          normalMap: normMap,
          emissiveMap: emMap,
          emissive: emMap ? 0xffffff : 0x000000,
          emissiveIntensity: emMap ? 1.0 : 0.0,
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
  setCustomLighting = function () { originalSetCustomLighting(); applyBlenderLighting(); };
  const originalApplyDungeonLighting = applyDungeonLighting;
  applyDungeonLighting = function (preset) {
    originalApplyDungeonLighting(preset);
    applyBlenderLighting();
  };
  applyDungeonLighting(document.getElementById('lightPreset').value);

  // ---- Blender-equivalent sprite render loop (replaces the minified Qf) ----

  // Mirrors BLENDER_WORKER_TEMPLATE in shader_lab_server.py: orthographic camera at azimuth 45 deg,
  // one shared fit over every pose and direction, feet re-grounded per frame, rig yaw 135 - 45*d.
  state.supersample = 4;
  state.filterWidth = 1.5;
  const AZIMUTH = Math.PI / 4;
  const DIR0_YAW = 3 * Math.PI / 4;
  const DIR_STEP = Math.PI / 4;


  // Cycles-like Blackman-Harris pixel filter: width in output pixels (support is +-width/2).
  function blackmanHarris(distance, width) {
    const t = distance / width + 0.5;
    if (t < 0 || t > 1) return 0;
    const phase = 2 * Math.PI * t;
    return 0.35875 - 0.48829 * Math.cos(phase) + 0.14128 * Math.cos(2 * phase) - 0.01168 * Math.cos(3 * phase);
  }

  // Alpha-weighted (premultiplied) reduction of a (size*ss)^2 RGBA buffer to size^2.
  function downsample(source, size, ss, filterWidth) {
    if (ss === 1) return source;
    const wide = size * ss;
    const out = new Uint8ClampedArray(size * size * 4);
    const radius = filterWidth / 2;
    for (let oy = 0; oy < size; oy++) for (let ox = 0; ox < size; ox++) {
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
    return out;
  }

  Qf = async function ({ renderer, scene, controls, state: app, params, onProgress, onStatus }) {
    params.brightness = parseFloat(document.getElementById('labBrightness').value) || 1;
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
    try {
      // Headless Chromium may report a transiently lost WebGL context right after load.
      for (let waited = 0; renderer.getContext().isContextLost() && waited < 15000; waited += 100) await new Promise(resolve => setTimeout(resolve, 100));
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

      // Pass 1: posed vertices per time at yaw 0, grounded (min Y = 0), shared fit over all directions.
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
      const pixelWorld = (2 * half) / size;
      const center = new K()
        .addScaledVector(right, (minX + maxX) / 2)
        .addScaledVector(upAxis, (minV + maxV) / 2);
      const camera = new ts(-half, half, half, -half, 0.1, 100);
      camera.position.copy(center).addScaledVector(toCamera, 30);
      camera.lookAt(center);
      camera.updateMatrixWorld(true);
      state.lastFit = { extent, half, center: center.toArray(), minX, maxX, minV, maxV, points: samples[0].pts.length / 3, minY0: samples[0].minY, proj: camera.projectionMatrix.elements.slice(), pos: camera.position.toArray(), isOrtho: !!camera.isOrthographicCamera, rootScale: root ? root.scale.toArray() : null, rootPos: root ? root.position.toArray() : null };

      renderer.setSize(size * ss, size * ss, false);
      const results = [], firstFrames = [];
      for (let direction = 0; direction < Ff.length; direction++) {
        const name = Ff[direction];
        const gifFrames = [];
        for (let index = 0; index < frameCount; index++) {
          if (root) { root.rotation.y = DIR0_YAW - direction * DIR_STEP; root.position.y = -samples[index % samples.length].minY; }
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
      return result;
    } finally {
      state.capturing = false;
      if (root) { root.rotation.y = previousYaw; root.position.y = previousY; root.updateMatrixWorld(true); }
      app.mixer?.setTime(0);
      renderer.setSize(previousSize.x, previousSize.y, false);
      app.camera.aspect = previousSize.x / previousSize.y;
      app.camera.updateProjectionMatrix();
      if (controls) controls.update();
      app.rendering = false;
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
    const stride = parseFloat(document.getElementById('stride3d').value);
    const ticks = parseInt(document.getElementById('animTicks').value, 10);
    const stridePx = stride * (32 / (2 * Math.sqrt(2))) * state.rigScale;
    const speedFixed88 = Math.round((stridePx * 256) / Math.max(1, frameCount * ticks));
    const cameraElevation = document.getElementById('elevation');
    const settings = {
      model: cp.textContent, animation: _p.animSelect.selectedOptions[0]?.textContent || 'Pose est\u00e1tica',
      directions: Ff, framesPerDirection: frameCount, frameSize: `${size}x${size}`,
      spritesheet: { columns: frameCount, rows: Ff.length, width: atlas.width, height: atlas.height, alpha: true },
      stride3dMeters: stride, ticksPerFrame: ticks, stridePixels: Number(stridePx.toFixed(2)), speedFixed8_8: speedFixed88,
      inPlace: document.getElementById('inPlaceMotion').checked, rigScale: state.rigScale,
      cameraElevationDegrees: cameraElevation ? parseFloat(cameraElevation.value) : null,
      contrast: parseFloat(_p.contrast.value), saturation: parseFloat(_p.saturation.value),
      neckPitchDegrees: parseFloat(document.getElementById('neckPitch').value), displace: parseFloat(document.getElementById('meshDisplace').value),
      brightness: parseFloat(document.getElementById('labBrightness').value), webglShadowQuality: parseInt(document.getElementById('labSamples').value, 10),
      normalStrength: parseFloat(document.getElementById('labNormal').value), shadowSoftness: parseFloat(document.getElementById('labShadow').value),
      supersample: state.supersample || 4,
      boneShader: state.boneMode, renderEngine: 'Three.js WebGL (browser)'
    };
    folder.file('settings.json', JSON.stringify(settings, null, 2));
    folder.file('README.md', `# ${name}\n\nSpritesheet PNG: ${frameCount} columnas (frames), ${Ff.length} filas (direcciones), ${size}x${size}px por celda, RGBA transparente.\n\nIncluye GIF por direccion, collage GIF, PNG por frame y settings.json. Orden: ${Ff.join(', ')}.\n\nRenderizado con Three.js WebGL; los controles de calidad mapean a WebGL y no reproducen Cycles.\n`);
    return zip.generateAsync({ type: 'blob' });
  }

  function addExportButtons() {
    const header = document.querySelector('header > div');
    const atlasButton = document.createElement('button');
    atlasButton.className = 'btn secondary';
    atlasButton.textContent = 'Spritesheet PNG';
    atlasButton.disabled = true;
    atlasButton.id = 'btnExportAtlas';
    atlasButton.style.cssText = 'padding:8px 12px;font-size:.75rem';
    atlasButton.onclick = async () => {
      try {
        const atlas = await makeAtlas();
        Fp(atlas.blob, `${(cp.textContent || 'modelo').replace(/\.fbx$/i, '')}_spritesheet.png`);
        yp(`Spritesheet PNG ${atlas.width}x${atlas.height} descargado`);
      } catch (error) { yp(error.message, true); }
    };
    header.appendChild(atlasButton);

    const zipButton = document.getElementById('btnExportZip');
    zipButton.textContent = 'Exportar paquete completo';
    zipButton.onclick = async () => {
      bp(true, 'Empaquetando GIFs, spritesheet y PNGs...');
      try {
        const name = (cp.textContent || 'modelo').replace(/\.fbx$/i, '');
        Fp(await exportPackage(), `${name}_sprite_lab.zip`);
        yp('Paquete completo descargado');
      } catch (error) { yp(`Error al crear el paquete: ${error.message}`, true); }
      finally { bp(false); }
    };
    const renderButton = document.getElementById('btnRender');
    renderButton.addEventListener('click', () => { atlasButton.disabled = true; }, true);
    const originalClick = renderButton.onclick;
    renderButton.onclick = async (...args) => {
      await originalClick(...args);
      atlasButton.disabled = getFrames().length !== Ff.length * parseInt(_p.frameCount.value, 10);
      zipButton.style.display = 'flex';
    };
  }

  function addBlenderControls() {
    const controls = document.querySelector('.controls');
    const section = document.createElement('section');
    section.className = 'control-group';
    section.style.cssText = 'border-top:1px solid #2d3345;padding-top:12px;gap:10px';
    section.innerHTML = `
      <strong style="color:#8c92a4;font-size:.75rem;text-transform:uppercase">Controles del Shader Lab</strong>
      <small style="color:#8c92a4">El render usa WebGL. Calidad de sombras y relieve son aproximaciones; no ejecuta Cycles.</small>
      <label>Escala del rig <input id="rigScale" type="number" min=".001" max="5" step=".001" value="1" style="width:90px"></label>
      <label>Inclinaci\u00f3n cuello/cabeza (\u00b0) <input id="neckPitch" type="number" min="-90" max="90" step="1" value="0" style="width:90px"></label>
      <label>Engrosar malla <input id="meshDisplace" type="number" min="0" max=".5" step=".01" value="0" style="width:90px"></label>
      <label>Shader \u00f3seo <input id="boneShader" type="checkbox" style="width:auto"></label>
      <label>Zancada 3D (m) <input id="stride3d" type="number" min=".1" step=".05" value="1.5" style="width:90px"></label>
      <label>Ticks por frame <input id="animTicks" type="number" min="1" max="10" step="1" value="3" style="width:90px"></label>
      <label>Brillo <span><output id="labBrightnessValue">1.00</output><input id="labBrightness" type="range" min="0.8" max="1.2" step="0.05" value="1"></span></label>
      <label>Suavidad de sombra <span><output id="labShadowValue">2\u00b0</output><input id="labShadow" type="range" min="0.5" max="18" step="0.5" value="2"></span></label>
      <label>Relieve normal <span><output id="labNormalValue">0.35</output><input id="labNormal" type="range" min="0" max="0.8" step="0.05" value="0.35"></span></label>
      <label>Calidad sombras WebGL <span><output id="labSamplesValue">16</output><input id="labSamples" type="range" min="8" max="32" step="8" value="16"></span></label>
      <label>Supersampling <select id="labSupersample" style="width:110px"><option value="1">1x (rápido)</option><option value="2">2x</option><option value="4" selected>4x (calidad Blender)</option></select></label>
      <small id="kinematicSummary" style="color:#8c92a4"></small>`;
    const renderButton = document.getElementById('btnRender');
    controls.insertBefore(section, renderButton);
    const labSupersample = document.getElementById('labSupersample');
    if (labSupersample) {
      labSupersample.addEventListener('change', e => {
        state.supersample = parseInt(e.target.value, 10) || 4;
      });
    }
    const cameraElevation = document.getElementById('elevation');
    if (cameraElevation) {
      cameraElevation.min = '20';
      cameraElevation.step = '1';
      cameraElevation.nextElementSibling.querySelector('span').textContent = '20\u00b0';
    }
    document.getElementById('rigScale').addEventListener('input', event => {
      const next = Math.max(.001, parseFloat(event.target.value) || 1);
      if ($.modelRoot) {
        const ratio = next / state.rigScale;
        $.modelRoot.scale.multiplyScalar(ratio);
        refreshPreviewFit();
      }
      state.rigScale = next;
    });
    document.getElementById('neckPitch').addEventListener('input', () => refreshPreviewFit());
    document.getElementById('meshDisplace').addEventListener('input', event => {
      state.displace = Math.max(0, parseFloat(event.target.value) || 0);
      applyMeshDisplace();
    });
    const updateQuality = () => {
      const brightness = parseFloat(document.getElementById('labBrightness').value);
      document.getElementById('labBrightnessValue').value = brightness.toFixed(2);
      document.getElementById('labBrightnessValue').textContent = brightness.toFixed(2);
      document.getElementById('labShadowValue').textContent = `${document.getElementById('labShadow').value}\u00b0`;
      document.getElementById('labNormalValue').textContent = parseFloat(document.getElementById('labNormal').value).toFixed(2);
      document.getElementById('labSamplesValue').textContent = document.getElementById('labSamples').value;
      if ($.renderer) $.renderer.domElement.style.filter = `contrast(${_p.contrast.value}) saturate(${_p.saturation.value}) brightness(${brightness})`;
      if ($.lights?.key) {
        $.lights.key.shadow.radius = parseFloat(document.getElementById('labShadow').value);
        const mapSize = parseInt(document.getElementById('labSamples').value, 10) * 64;
        $.lights.key.shadow.mapSize.set(mapSize, mapSize);
        $.lights.key.shadow.map?.dispose();
        $.lights.key.shadow.map = null;
        $.lights.key.shadow.needsUpdate = true;
      }
      if ($.model) $.model.traverse(object => {
        if (!object.isMesh) return;
        const materials = Array.isArray(object.material) ? object.material : [object.material];
        for (const material of materials) if (material?.normalMap) material.normalScale.setScalar(parseFloat(document.getElementById('labNormal').value));
      });
    };
    ['labBrightness', 'labShadow', 'labNormal', 'labSamples'].forEach(id => document.getElementById(id).addEventListener('input', updateQuality));
    _p.contrast.addEventListener('input', updateQuality);
    _p.saturation.addEventListener('input', updateQuality);
    document.getElementById('boneShader').addEventListener('change', event => {
      state.boneMode = event.target.checked;
      applyBoneMaterial();
    });
    const mixerHook = () => {
      if (!$.mixer || $.mixer.__neckHooked) return;
      $.mixer.__neckHooked = true;
      const mixer = $.mixer;
      const originalSetTime = mixer.setTime.bind(mixer);
      mixer.setTime = time => {
        const result = originalSetTime(time);
        const pitch = (parseFloat(document.getElementById('neckPitch').value) || 0) * Math.PI / 180;
        if (pitch && $.model) {
          const bones = new Set();
          $.model.traverse(object => {
            if (!object.isSkinnedMesh || !object.skeleton) return;
            const named = object.skeleton.bones.filter(bone => !/twist|end/i.test(bone.name));
            const target = named.find(bone => /neck$/i.test(bone.name)) || named.find(bone => /head$/i.test(bone.name));
            if (target) bones.add(target);
          });
          for (const bone of bones) bone.quaternion.multiply(new K().setFromAxisAngle(new K(1, 0, 0), pitch));
        }
        return result;
      };
    };
    const status = document.createElement('small');
    status.style.display = 'none';
    section.appendChild(status);
    const render = document.getElementById('btnRender');
    render.addEventListener('click', () => { mixerHook(); }, true);
    document.getElementById('btnRender').addEventListener('click', () => {
      const stride = parseFloat(document.getElementById('stride3d').value) || 1.5;
      const ticks = parseInt(document.getElementById('animTicks').value, 10) || 3;
      const pixels = stride * (32 / (2 * Math.sqrt(2))) * state.rigScale;
      document.getElementById('kinematicSummary').textContent = `Zancada aprox. ${pixels.toFixed(1)} px | speed 8.8 = ${Math.round(pixels * 256 / (parseInt(_p.frameCount.value, 10) * ticks))}`;
    });
    const originalLoad = Ap;
    Ap = async file => {
      await originalLoad(file);
      if ($.model) {
        let hasBones = false;
        $.model.traverse(node => { if (node.isBone) hasBones = true; });
        if (hasBones) {
          $.model.position.x = 0;
          $.model.position.z = 0;
          $.model.updateMatrixWorld(true);
          if ($.modelRoot) $.modelRoot.updateMatrixWorld(true);
        }
      }
      state.rigScale = 1;
      state.displace = 0;
      document.getElementById('rigScale').value = '1';
      document.getElementById('meshDisplace').value = '0';
      applyMeshDisplace();
      setupModelMaterials($.model);
      if (state.boneMode) applyBoneMaterial();
      updateQuality();
      if (typeof refreshPreviewFit === 'function') refreshPreviewFit();
    };
  }

  function applyBoneMaterial() {
    if (!$.model) return;
    $.model.traverse(object => {
      if (!object.isMesh) return;
      if (state.boneMode) {
        object.userData.__originalMaterial ??= object.material;
        object.material = new Xa({ color: 0xebe0cc, roughness: .5, metalness: 0 });
      } else if (object.userData.__originalMaterial) object.material = object.userData.__originalMaterial;
    });
  }

  function applyMeshDisplace() {
    if (!$.model) return;
    $.model.traverse(object => {
      if (!object.isMesh || !object.geometry?.attributes?.position || !object.geometry?.attributes?.normal) return;
      if (!object.userData.__basePositions) {
        object.geometry = object.geometry.clone();
        object.userData.__basePositions = object.geometry.attributes.position.array.slice();
      }
      const position = object.geometry.attributes.position;
      const normal = object.geometry.attributes.normal;
      const base = object.userData.__basePositions;
      const offset = $.modelHeight ? state.displace / $.modelHeight : state.displace;
      for (let index = 0; index < position.count; index++) {
        position.setXYZ(index, base[index * 3] + normal.getX(index) * offset, base[index * 3 + 1] + normal.getY(index) * offset, base[index * 3 + 2] + normal.getZ(index) * offset);
      }
      position.needsUpdate = true;
      object.geometry.computeBoundingBox();
      object.geometry.computeBoundingSphere();
    });
  }

  addExportButtons();
  addBlenderControls();
})();
