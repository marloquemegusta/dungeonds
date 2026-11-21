// Referencia de desarrollo (Playwright headless). NO forma parte de la ruta rapida.
// Ejecuta el lab lento para un personaje y vuelca, por cada llamada a Gf del bucle de render:
//   - el RGBA crudo (size*ss)^2 (straight, fila 0 arriba: Gf ya voltea);
//   - la transformacion de raiz (yaw, yOffset) de esa llamada.
// Estatico (una vez): mallas (vertices, indices por grupo, uvs, material), materiales, texturas (bytes
// codificados, se decodifican luego en Python), luces y camara ortografica del lab.
// Por fotograma: posiciones y normales del mundo con raiz identidad (skinning manual).
// uso: node ref_dump.cjs <model.fbx> <outDir> <settings.json> [dirsCsv]
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('C:/Users/malfonso/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

const [model, outDir, settingsPath, dirsArg] = process.argv.slice(2);
const s = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
const dirs = dirsArg ? dirsArg.split(',').map(Number) : [0, 1, 2, 3, 4, 5, 6, 7];
const HTML = path.resolve(__dirname, '../../FBX-Web-Renderer-offline.html');
fs.mkdirSync(outDir, { recursive: true });

// Codigo que se ejecuta dentro de la pagina: captura de Gf + pose + estatico.
function pageHook(dirs) {
  const cap = window.__cap = { calls: [], statics: null, tex: {}, pose: {} };
  const b64 = (u8) => { let bin = ''; for (let i = 0; i < u8.length; i += 0x8000) bin += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(bin); };
  const mul = (a, b) => { const o = new Float64Array(16); for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) { let t = 0; for (let k = 0; k < 4; k++) t += a[k * 4 + r] * b[c * 4 + k]; o[c * 4 + r] = t; } return o; };
  // Pose con raiz identidad: posiciones y normales del mundo por vertice, en el orden de root.traverse.
  function posePoints(root) {
    root.updateMatrixWorld(true);
    const P = [], N = [];
    root.traverse(n => {
      if (!n.isMesh || !n.visible || !n.geometry || !n.geometry.attributes.position) return;
      const pos = n.geometry.attributes.position, nor = n.geometry.attributes.normal;
      const mw = n.matrixWorld.elements;
      const sk = n.isSkinnedMesh && n.skeleton;
      if (sk) sk.update();
      const bm = sk ? sk.boneMatrices : null;
      const bind = sk ? n.bindMatrix.elements : null, bindInv = sk ? n.bindMatrixInverse.elements : null;
      const si = n.geometry.attributes.skinIndex, sw = n.geometry.attributes.skinWeight;
      for (let i = 0; i < pos.count; i++) {
        let x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
        let nx = nor ? nor.getX(i) : 0, ny = nor ? nor.getY(i) : 1, nz = nor ? nor.getZ(i) : 0;
        let T = null;
        if (bm) {
          const S = new Float64Array(16);
          for (let k = 0; k < 4; k++) { const w = sw.getComponent(i, k); if (!w) continue; const b = si.getComponent(i, k) * 16; for (let e = 0; e < 16; e++) S[e] += w * bm[b + e]; }
          T = mul(mul(bindInv, S), bind);
        } else { T = new Float64Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]); }
        // Posicion: T * p (columna mayor), luego mundo.
        const px = T[0] * x + T[4] * y + T[8] * z + T[12], py = T[1] * x + T[5] * y + T[9] * z + T[13], pz = T[2] * x + T[6] * y + T[10] * z + T[14];
        const wx = mw[0] * px + mw[4] * py + mw[8] * pz + mw[12], wy = mw[1] * px + mw[5] * py + mw[9] * pz + mw[13], wz = mw[2] * px + mw[6] * py + mw[10] * pz + mw[14];
        // Normal: mat3(T) * n, luego mat3(mundo) * n', normalizada.
        const qx = T[0] * nx + T[4] * ny + T[8] * nz, qy = T[1] * nx + T[5] * ny + T[9] * nz, qz = T[2] * nx + T[6] * ny + T[10] * nz;
        let ux = mw[0] * qx + mw[4] * qy + mw[8] * qz, uy = mw[1] * qx + mw[5] * qy + mw[9] * qz, uz = mw[2] * qx + mw[6] * qy + mw[10] * qz;
        const L = Math.hypot(ux, uy, uz) || 1;
        P.push(wx, wy, wz); N.push(ux / L, uy / L, uz / L);
      }
    });
    return { P, N };
  }
  function statics(root, cam) {
    const parts = [], mats = []; const matIndex = new Map(); let vbase = 0;
    const matOf = (m) => {
      if (!matIndex.has(m)) {
        matIndex.set(m, mats.length);
        const c = m.color || { r: 1, g: 1, b: 1 };
        const tex = (t) => t ? { src: t.image ? t.image.src : null, flipY: t.flipY, wrapS: t.wrapS, wrapT: t.wrapT, repeat: [t.repeat.x, t.repeat.y], offset: [t.offset.x, t.offset.y], rotation: t.rotation, colorSpace: t.colorSpace } : null;
        mats.push({ type: m.type, color: [c.r, c.g, c.b], roughness: m.roughness, metalness: m.metalness,
          emissive: [m.emissive ? m.emissive.r : 0, m.emissive ? m.emissive.g : 0, m.emissive ? m.emissive.b : 0],
          emissiveIntensity: m.emissiveIntensity ?? 0, normalScale: m.normalScale ? [m.normalScale.x, m.normalScale.y] : [1, 1],
          side: m.side, map: tex(m.map), normalMap: tex(m.normalMap), emissiveMap: tex(m.emissiveMap) });
      }
      return matIndex.get(m);
    };
    root.traverse(n => {
      if (!n.isMesh || !n.visible || !n.geometry || !n.geometry.attributes.position) return;
      const g = n.geometry, count = g.attributes.position.count;
      const idx = g.index ? Array.from(g.index.array) : null;
      const uv = g.attributes.uv ? Array.from(g.attributes.uv.array) : null;
      const mats_ = Array.isArray(n.material) ? n.material : [n.material];
      const groups = (g.groups && g.groups.length) ? g.groups : [{ start: 0, count: idx ? idx.length : count, materialIndex: 0 }];
      for (const gr of groups) {
        parts.push({ name: n.name, vbase: vbase, vcount: count, index: idx, uv: uv, start: gr.start, icount: gr.count, mat: matOf(mats_[gr.materialIndex || 0]), side: mats_[gr.materialIndex || 0].side });
      }
      vbase += count;
    });
    const L = window.$.lights;
    const lt = (o) => ({ color: [o.color.r, o.color.g, o.color.b], intensity: o.intensity, position: [o.position.x, o.position.y, o.position.z] });
    return { parts, mats, totalVerts: vbase,
      lights: { key: lt(L.key), fill: lt(L.fill), rim: lt(L.rim), world: { color: [L.world.color.r, L.world.color.g, L.world.color.b], intensity: L.world.intensity } },
      camera: { left: cam.left, right: cam.right, top: cam.top, bottom: cam.bottom, near: cam.near, far: cam.far, view: Array.from(cam.matrixWorldInverse.elements), proj: Array.from(cam.projectionMatrix.elements), pos: cam.position.toArray() },
      toneMapping: window.$.renderer.toneMapping, exposure: window.$.renderer.toneMappingExposure, shadowType: window.$.renderer.shadowMap.type };
  }
  const origGf = window.Gf;
  window.Gf = function (renderer, w, h) {
    const out = origGf(renderer, w, h);
    const root = window.$.modelRoot;
    const cam = window.__spriteLab.lastFit.camera;
    if (!cap.statics) cap.statics = statics(root, cam);
    // Textura: guardar bytes codificados (una vez por src).
    const callIdx = cap.calls.length;
    const yaw = root.rotation.y, offY = root.position.y;
    // Pose con raiz identidad en el instante de esta llamada (el mixer ya esta en el fotograma).
    const sy = root.rotation.y, sp = root.position.y;
    root.rotation.y = 0; root.position.y = 0;
    const pose = posePoints(root);
    root.rotation.y = sy; root.position.y = sp; root.updateMatrixWorld(true);
    cap.calls.push({ yaw, offY, w, h, raw: b64(out), P: pose.P, N: pose.N });
    return out;
  };
  // Texturas: el lab las carga como blob: URL; se toman al terminar (ver texFetch).
  cap.texSrcs = () => {
    const set = new Set();
    for (const p of cap.statics.parts) {}
    window.$.model.traverse(n => { if (!n.isMesh) return; [].concat(n.material).forEach(m => { ['map', 'normalMap', 'emissiveMap'].forEach(k => { if (m[k] && m[k].image && m[k].image.src) set.add(m[k].image.src); }); }); });
    return [...set];
  };
  cap.dirs = dirs;
  return true;
}

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--enable-webgl', '--use-gl=swiftshader', '--disable-dev-shm-usage', '--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  page.on('pageerror', e => console.error('PAGEERROR', e.message));
  await page.goto('file:///' + HTML.split(path.sep).join('/'), { waitUntil: 'load' });
  await page.waitForFunction(() => !!window.__spriteLab, null, { timeout: 30000 });
  await page.locator('#fbxInput').setInputFiles(path.resolve(model));
  await page.waitForFunction(() => window.$ && window.$.loaded === true && document.getElementById('animSelect').options.length > 0, null, { timeout: 900000 });
  await page.waitForTimeout(1200);
  await page.evaluate((s) => {
    const set = (id, v) => { const el = document.getElementById(id); if (!el || v == null) return; if (el.type === 'range' && Number(v) > Number(el.max || 0)) el.max = String(v); el.value = String(v); el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); };
    set('labLegibility', 'c2');
    set('resolution', parseInt(String(s.frameSize).split('x')[0], 10));
    set('frameCount', s.framesPerDirection); set('elevation', s.cameraElevationDegrees);
    set('labBrightness', s.brightness); set('neckPitch', s.neckPitchDegrees); set('animTicks', s.ticksPerFrame);
    set('labNormal', s.normalStrength); set('labShadow', s.shadowSoftness); set('labSamples', s.webglShadowQuality);
    set('labSupersample', s.supersample); set('meshDisplace', s.displace);
    set('lightPreset', s.lightPreset); if (window.applyDungeonLighting) window.applyDungeonLighting(s.lightPreset);
    set('contrast', s.contrast); set('saturation', s.saturation);
    const ip = document.getElementById('inPlaceMotion'); if (ip) { ip.checked = !!s.inPlace; ip.dispatchEvent(new Event('change', { bubbles: true })); }
    const lab = window.__spriteLab; lab.supersample = s.supersample; lab.rigScale = s.rigScale; lab.muzzleBone = null;
    lab.toneMapping = null; lab.fitZoom = s.fitZoom; lab.fitExtent = s.fitExtent || 0; lab.normScale = s.normScale || 0;
    const sel = document.getElementById('animSelect'); const idx = Array.from(sel.options).findIndex(o => o.textContent === s.animation);
    sel.selectedIndex = Math.max(0, idx); sel.dispatchEvent(new Event('change', { bubbles: true }));
  }, s);
  await page.waitForTimeout(1000);
  await page.evaluate((d) => { window.__spriteLab.dirFilter = d; }, dirs);
  await page.evaluate(pageHook, dirs);
  await page.evaluate(() => { window.$.results = null; document.getElementById('renderBtn').click(); });
  // El bucle termina cuando hay resultados y no se esta renderizando (la fase de sombras/atlas puede seguir despues).
  await page.waitForFunction(() => window.$.results && !window.$.rendering, null, { timeout: 900000 });
  const data = await page.evaluate(() => {
    const cap = window.__cap;
    return { calls: cap.calls.map(c => ({ yaw: c.yaw, offY: c.offY, w: c.w, h: c.h, raw: c.raw, P: c.P, N: c.N })), statics: cap.statics, texSrcs: cap.texSrcs() };
  });
  // Texturas: bytes codificados del blob src.
  const tex = {};
  for (const src of data.texSrcs) {
    tex[src] = await page.evaluate(async (u) => { const b = new Uint8Array(await (await fetch(u)).arrayBuffer()); let bin = ''; for (let i = 0; i < b.length; i += 0x8000) bin += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000)); return btoa(bin); }, src);
  }
  await browser.close();
  // Escritura: estatico en JSON (con indices/uvs en base64 Uint32/Float32) y bloques binarios.
  const toB64 = (arr, T) => Buffer.from(new T(arr).buffer).toString('base64');
  const st = data.statics;
  const texFiles = {}; let ti = 0;
  for (const [src, b64] of Object.entries(tex)) { const f = `tex_${ti++}.bin`; fs.writeFileSync(path.join(outDir, f), Buffer.from(b64, 'base64')); texFiles[src] = f; }
  const parts = st.parts.map(p => ({ name: p.name, vbase: p.vbase, vcount: p.vcount, start: p.start, icount: p.icount, mat: p.mat, side: p.side,
    index: p.index ? toB64(p.index, Uint32Array) : null, uv: p.uv ? toB64(p.uv, Float32Array) : null }));
  const mats = st.mats.map(m => ({ ...m, map: m.map ? { ...m.map, file: texFiles[m.map.src] } : null, normalMap: m.normalMap ? { ...m.normalMap, file: texFiles[m.normalMap.src] } : null, emissiveMap: m.emissiveMap ? { ...m.emissiveMap, file: texFiles[m.emissiveMap.src] } : null }));
  const calls = data.calls.map((c, i) => ({ i, yaw: c.yaw, offY: c.offY, w: c.w, h: c.h }));
  // Pose por fotograma: se toma la primera llamada de cada fotograma (orden: direccion, luego fotograma).
  const F = s.framesPerDirection, nv = st.totalVerts;
  const posBuf = new Float32Array(F * nv * 3), norBuf = new Float32Array(F * nv * 3);
  for (let i = 0; i < data.calls.length; i++) {
    const f = i % F;
    if (i >= F) break;
    posBuf.set(new Float32Array(data.calls[i].P), f * nv * 3);
    norBuf.set(new Float32Array(data.calls[i].N), f * nv * 3);
  }
  fs.writeFileSync(path.join(outDir, 'frames_pos.bin'), Buffer.from(posBuf.buffer));
  fs.writeFileSync(path.join(outDir, 'frames_nor.bin'), Buffer.from(norBuf.buffer));
  for (let i = 0; i < data.calls.length; i++) fs.writeFileSync(path.join(outDir, `raw_${i}.bin`), Buffer.from(data.calls[i].raw, 'base64'));
  fs.writeFileSync(path.join(outDir, 'meta.json'), JSON.stringify({ frameCount: F, dirs, ss: s.supersample, size: parseInt(String(s.frameSize), 10), totalVerts: nv,
    parts, mats, lights: st.lights, camera: st.camera, toneMapping: st.toneMapping, exposure: st.exposure, shadowType: st.shadowType, calls }, null, 1));
  console.log('calls', data.calls.length, 'verts', nv, 'parts', parts.length, 'tex', Object.keys(tex).length);
})().catch(e => { console.error(e); process.exit(1); });
