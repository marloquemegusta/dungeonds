// Headless map export: loads a map model into the offline lab with the render
// settings stored in an existing map_settings.json and writes the lab's map
// package (world.png, collision.png/json, occlusion.png, occlusion_depth.png).
//
// usage: node export_map_package_headless.cjs <model.glb|fbx> <settings.json> <out_dir>
const fs = require('node:fs');
const path = require('node:path');

let chromium;
for (const p of ['playwright',
  'C:/Users/malfonso/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright']) {
  try { chromium = require(p).chromium; if (chromium) break; } catch (e) {}
}
if (!chromium) { console.error('Playwright not found'); process.exit(1); }

const argv = process.argv.slice(2);
const legIdx = argv.indexOf('--legibility');
const legOpt = legIdx >= 0 ? argv[legIdx + 1] : undefined;
const pos = argv.filter((a, i) => !a.startsWith('--') && !(i > 0 && argv[i - 1] === '--legibility'));
const [model, settingsPath, outDir] = pos.map(p => p && path.resolve(p));
if (!model || !settingsPath || !outDir) {
  console.error('usage: node export_map_package_headless.cjs <model> <map_settings.json> <out_dir> [--legibility anterior|c2]');
  process.exit(2);
}
const settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
if (legOpt) settings.legibility = legOpt;
if (settings.legibility === 'c2') settings.contrast = 1.0;
const HTML = path.join(__dirname, 'FBX-Web-Renderer-offline.html');

function s_waitTextures(s) { return s.waitTextures === true; }

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'] });
  const errors = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1680, height: 1050 }, deviceScaleFactor: 1 });
    page.on('pageerror', e => errors.push(e.stack || e.message));
    await page.goto(`file:///${HTML.replace(/\\/g, '/')}`, { waitUntil: 'load' });
    await page.waitForFunction(() => !!window.__spriteLab, { timeout: 30000 });

    await page.evaluate(s => {
      const set = (id, value) => {
        const el = document.getElementById(id);
        if (!el || value === undefined) return;
        el.value = String(value);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
      };
      // The lab slider stops at 1536 px; a rotated 768 px dungeon needs a wider render.
      const sizeInput = document.getElementById('mapPixelSize');
      if (sizeInput && s.width > Number(sizeInput.max)) sizeInput.max = String(s.width);
      if (sizeInput && s.width < Number(sizeInput.min)) sizeInput.min = String(s.width); // small tile renders
      if (s.legibility) set('labLegibility', s.legibility);
      set('mapPixelSize', s.width);
      set('elevation', s.cameraElevationDegrees);
      set('contrast', s.contrast);
      set('saturation', s.saturation);
      set('labBrightness', s.brightness);
      set('lightPreset', s.lighting?.preset);
      set('keyLight', s.lighting?.key);
      set('fillLight', s.lighting?.fill);
      set('rimLight', s.lighting?.rim);
      set('worldLight', s.lighting?.world);
      if (s.orthoScaleMeters) window.__spriteLab.mapOrthoScale = s.orthoScaleMeters;
      // Optional: s.shadows === false turns the key-light shadow map off (the old
      // package settings do not carry the key, so their behaviour is unchanged).
      // s.shadows === true (large maps): the key light's shadow camera defaults to +-5 m, which
      // covers only the middle of a 768 px dungeon. Widen it to the whole model.
      if (s.shadows === true && typeof $ !== 'undefined' && $.lights && $.lights.key) {
        const key = $.lights.key;
        key.shadow.mapSize.set(4096, 4096);
        const c = key.shadow.camera;
        c.left = -45; c.right = 45; c.top = 45; c.bottom = -45; c.near = 0.5; c.far = 150;
        c.updateProjectionMatrix();
        key.shadow.bias = -0.0004;
        if (key.shadow.map) { key.shadow.map.dispose(); key.shadow.map = null; }
      }
      if (s.shadows === false) {
        const sh = document.getElementById('shadowToggle');
        if (sh) { sh.checked = false; sh.dispatchEvent(new Event('change', { bubbles: true })); }
      }
    }, settings);

    const before = await page.evaluate(() => window.__spriteLab.mapRenderCount || 0);
    await page.locator('#mapFileInput').setInputFiles(model);
    await page.waitForFunction(n => (window.__spriteLab.mapRenderCount || 0) > n && window.__spriteLab.mapGroundDepth,
      before, { timeout: 180000 });

    // Optional (s.waitTextures): the lab's GLB loader creates textures with the async
    // TextureLoader, so the first render can run before they decode. Wait, then force
    // one more render by re-sending the brightness input and wait for it to finish.
    if (s_waitTextures(settings)) {
      await page.waitForTimeout(Number(settings.waitTexturesMs) || 2500);
      const n2 = await page.evaluate(() => window.__spriteLab.mapRenderCount || 0);
      await page.evaluate(v => {
        const el = document.getElementById('labBrightness');
        el.value = String(v); el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
      }, settings.brightness ?? 1);
      await page.waitForFunction(n => (window.__spriteLab.mapRenderCount || 0) > n, n2, { timeout: 180000 });
    }

    // Loading the model triggers renderMap with the settings applied above.
    const files = await page.evaluate(async () => {
      const lab = window.__spriteLab;
      const blob = await lab.exportMapPackage();
      const zip = await Nf.default.loadAsync(blob);
      const out = {};
      for (const name of Object.keys(zip.files)) out[name] = await zip.files[name].async('base64');
      return { out, w: lab.mapWidth, h: lab.mapHeight };
    });
    fs.mkdirSync(outDir, { recursive: true });
    for (const [name, b64] of Object.entries(files.out)) fs.writeFileSync(path.join(outDir, name), Buffer.from(b64, 'base64'));
    console.log(`exported ${Object.keys(files.out).join(', ')} at ${files.w}x${files.h} -> ${outDir}`);
    if (errors.length) console.error('page errors:\n' + errors.join('\n'));
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exit(1); });
