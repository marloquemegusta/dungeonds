// A/B de legibilidad: renderiza un personaje en el lab offline (headless) con overrides
// sin tocar el lab. usage: node ab_render.cjs <model> <outDir> <template.json> '<variantJSON>'
// variant: { ss, rim: {intensity, elevDeg} | null, tone: 6|7|null, contrast, saturation }
const fs = require('node:fs');
const path = require('node:path');
let chromium;
for (const p of ['playwright', 'C:/Users/malfonso/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright']) {
  try { chromium = require(p).chromium; if (chromium) break; } catch (e) {}
}
const [model, outDir, templatePath, variantJson] = process.argv.slice(2);
const s = JSON.parse(fs.readFileSync(templatePath, 'utf8'));
const v = JSON.parse(variantJson);
const HTML = 'C:/codexlocal/dungeonds/tools/lab/FBX-Web-Renderer-offline.html';

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--enable-webgl', '--use-gl=swiftshader', '--disable-dev-shm-usage', '--no-sandbox'] });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 });
    page.on('pageerror', e => console.error('pageerror', e.message));
    await page.goto('file:///' + HTML, { waitUntil: 'load' });
    await page.waitForFunction(() => !!window.__spriteLab, { timeout: 30000 });
    await page.locator('#fbxInput').setInputFiles(path.resolve(model));
    await page.waitForFunction(() => window.$ && window.$.loaded === true && document.getElementById('animSelect')?.options.length > 0, null, { timeout: 900000 });
    await page.waitForTimeout(1500);
    const info = await page.evaluate(async ({ s, v }) => {
      const set = (id, val) => { const el = document.getElementById(id); if (!el || val == null) return; el.value = String(val); el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); };
      set('resolution', v.resolution ?? parseInt(String(s.frameSize).split('x')[0], 10));
      set('frameCount', s.framesPerDirection);
      set('elevation', s.cameraElevationDegrees);
      set('labBrightness', s.brightness);
      set('neckPitch', s.neckPitchDegrees);
      set('animTicks', s.ticksPerFrame);
      document.getElementById('labNormal').min = '0';
      set('labNormal', v.normal ?? s.normalStrength);
      set('labShadow', s.shadowSoftness);
      set('labSamples', s.webglShadowQuality);
      set('labSupersample', v.ss);
      set('meshDisplace', s.displace);
      set('lightPreset', s.lightPreset);
      window.applyDungeonLighting && window.applyDungeonLighting(s.lightPreset);
      set('outlineMode', s.outlineMode);
      set('contrast', v.contrast ?? s.contrast);
      set('saturation', v.saturation ?? s.saturation);
      const inPlace = document.getElementById('inPlaceMotion');
      if (inPlace) { inPlace.checked = !!s.inPlace; inPlace.dispatchEvent(new Event('change', { bubbles: true })); }
      const lab = window.__spriteLab;
      lab.supersample = v.ss; lab.rigScale = s.rigScale || 1; lab.fitZoom = v.fitZoom ?? 1;
      for (const [id, val] of Object.entries(v.sliders || {})) { const el = document.getElementById(id); if (el) el.max = '10'; set(id, val); }
      const rim = window.$.lights.rim;
      if (v.rim) {
        // Contraluz real: detrás del personaje respecto a la cámara (azimut de cámara 45°), elevada.
        document.getElementById('rimLight').max = '10';
        set('rimLight', v.rim.intensity);
        if (v.rim.color) set('rimColor', v.rim.color);
        const az = Math.PI / 4 + (v.rim.azOffDeg ?? 0) * Math.PI / 180, e = (v.rim.elevDeg ?? 35) * Math.PI / 180, d = 30;
        rim.position.x = -Math.cos(e) * Math.cos(az) * d;
        rim.position.y = Math.sin(e) * d;
        rim.position.z = Math.cos(e) * Math.sin(az) * d;
        rim.position.set = function () { return this; };   // el render no la vuelve a poner cenital
      }
      if (v.fresnel) {
        // Brillo de borde dependiente de la vista, sesgado hacia arriba (luz que "rodea" la silueta desde atrás-arriba).
        const f = v.fresnel, col = f.color || [1.0, 0.95, 0.85];
        const hook = m => {
          if (!m || m.__fres || !m.isMeshStandardMaterial && !m.isMeshPhongMaterial && !m.isMeshLambertMaterial) return;
          m.__fres = true;
          m.onBeforeCompile = sh => {
            sh.fragmentShader = sh.fragmentShader.replace('#include <emissivemap_fragment>',
              `#include <emissivemap_fragment>
               { float fr = pow(1.0 - clamp(dot(normal, normalize(vViewPosition)), 0.0, 1.0), ${f.power.toFixed(2)});
                 float up = clamp(normal.y * 0.5 + 0.5 + ${(f.upBias ?? 0.0).toFixed(2)}, 0.0, 1.0);
                 totalEmissiveRadiance += vec3(${col.map(c => c.toFixed(3)).join(',')}) * fr * up * ${f.strength.toFixed(3)}; }`);
          };
          m.customProgramCacheKey = () => 'fres' + f.strength + f.power;
          m.needsUpdate = true;
        };
        const r = window.$.renderer, orig = r.render.bind(r);
        r.render = (scene, cam) => { scene.traverse(o => { if (o.isMesh) [].concat(o.material).forEach(hook); }); return orig(scene, cam); };
      }
      if (v.tone != null) {
        window.$.renderer.toneMapping = v.tone;
        window.$.scene.traverse(o => { if (o.material) [].concat(o.material).forEach(m => { m.needsUpdate = true; }); });
      }
      const mats = []; window.$.scene.traverse(o => { if (o.isMesh) [].concat(o.material).forEach(m => mats.push({ t: m.type, map: !!m.map, nrm: !!m.normalMap, rough: !!m.roughnessMap, metal: m.metalness, r: m.roughness })); });
      return { mats: mats.slice(0, 4), rim: [rim.position.x, rim.position.y, rim.position.z], rimSlider: document.getElementById('rimLight')?.value, tone: window.$.renderer.toneMapping, ss: lab.supersample, contrast: document.getElementById('contrast').value };
    }, { s, v });
    console.log('setup', JSON.stringify(info));
    await page.waitForTimeout(800);
    const b64 = await page.evaluate(async () => {
      const lab = window.__spriteLab;
      window.$.results = null;
      document.getElementById('renderBtn').click();
      const t0 = performance.now();
      while (!(window.$.results && window.$.results.length === 8 && !window.$.rendering && lab.anchorData)) {
        if (performance.now() - t0 > 900000) throw new Error('render timeout');
        await new Promise(r => setTimeout(r, 200));
      }
      const blob = await lab.exportPackage();
      const buf = new Uint8Array(await blob.arrayBuffer());
      let bin = ''; for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
      return btoa(bin);
    });
    const zip = path.join(require('node:os').tmpdir(), `ab_${Date.now()}_${process.pid}.zip`);
    fs.writeFileSync(zip, Buffer.from(b64, 'base64'));
    fs.mkdirSync(outDir, { recursive: true });
    require('node:child_process').execFileSync('C:/Windows/System32/tar.exe', ['-xf', zip, '-C', outDir]);
    fs.unlinkSync(zip);
    console.log('ok', outDir);
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
