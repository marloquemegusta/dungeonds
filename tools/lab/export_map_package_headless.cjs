// Headless map export: loads a map model into the offline lab with the render
// settings stored in an existing map_settings.json and writes the lab's map
// package (world.png, collision.png/json, occlusion.png, occlusion_depth.png).
//
// usage: node export_map_package_headless.cjs <model.glb|fbx> <settings.json> <out_dir>
//
// Lighting: by default the shared dungeon profile assets/lighting/dungeon_lighting.json is applied
// (DESIGN.md 6) and the settings' own lighting/contrast/saturation/brightness are ignored. Optional
// settings keys: "lightingProfile": false (legacy lab lighting from the settings), or a path to
// another profile; "shadowExtent" (metres, half-size of the key light shadow camera, default 45) and
// "shadowMapSize" (px, default 4096), both used when "shadows" is true.
const { labGlArgs } = require('./chromium_gl_args.cjs');
const fs = require('node:fs');
const path = require('node:path');

let chromium;
for (const p of ['playwright',
  'C:/Users/malfonso/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright']) {
  try { chromium = require(p).chromium; if (chromium) break; } catch (e) {}
}
if (!chromium) { console.error('Playwright not found'); process.exit(1); }

const [model, settingsPath, outDir] = process.argv.slice(2).map(p => p && path.resolve(p));
if (!model || !settingsPath || !outDir) {
  console.error('usage: node export_map_package_headless.cjs <model> <map_settings.json> <out_dir>');
  process.exit(2);
}
const settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
let profile = null;
if (settings.lightingProfile !== false) {
  const profilePath = path.resolve(typeof settings.lightingProfile === 'string'
    ? settings.lightingProfile : path.join(__dirname, '../../assets/lighting/dungeon_lighting.json'));
  profile = JSON.parse(fs.readFileSync(profilePath, 'utf8'));
  console.log(`lighting profile: ${profilePath}`);
}
const HTML = path.join(__dirname, 'FBX-Web-Renderer-offline.html');

(async () => {
  const browser = await chromium.launch({ headless: true, args: labGlArgs() });
  const errors = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1680, height: 1050 }, deviceScaleFactor: 1 });
    page.on('pageerror', e => errors.push(e.stack || e.message));
    await page.goto(`file:///${HTML.replace(/\\/g, '/')}`, { waitUntil: 'load' });
    await page.waitForFunction(() => !!window.__spriteLab, { timeout: 30000 });

    await page.evaluate(({ s, profile }) => {
      if (profile) window.__spriteLab.setLightingProfile(profile);
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
      set('mapPixelSize', s.width);
      set('elevation', s.cameraElevationDegrees);
      if (!profile) {
        set('contrast', s.contrast);
        set('saturation', s.saturation);
        set('labBrightness', s.brightness);
        set('lightPreset', s.lighting?.preset);
        set('keyLight', s.lighting?.key);
        set('fillLight', s.lighting?.fill);
        set('rimLight', s.lighting?.rim);
        set('worldLight', s.lighting?.world);
      }
      if (s.orthoScaleMeters) window.__spriteLab.mapOrthoScale = s.orthoScaleMeters;
      // Optional: s.shadows === false turns the key-light shadow map off (the old
      // package settings do not carry the key, so their behaviour is unchanged).
      // s.shadows === true (large maps): the key light's shadow camera defaults to +-5 m, which
      // covers only the middle of a 768 px dungeon. Widen it to the whole model.
      if (s.shadows === true && typeof $ !== 'undefined' && $.lights && $.lights.key) {
        const key = $.lights.key;
        const mapSize = s.shadowMapSize || 4096, extent = s.shadowExtent || 45;
        key.shadow.mapSize.set(mapSize, mapSize);
        const c = key.shadow.camera;
        c.left = -extent; c.right = extent; c.top = extent; c.bottom = -extent; c.near = 0.5; c.far = 150 + Math.max(0, extent - 45) * 2;
        c.updateProjectionMatrix();
        key.shadow.bias = -0.0004;
        if (key.shadow.map) { key.shadow.map.dispose(); key.shadow.map = null; }
      }
      if (s.shadows === false) {
        const sh = document.getElementById('shadowToggle');
        if (sh) { sh.checked = false; sh.dispatchEvent(new Event('change', { bubbles: true })); }
      }
    }, { s: settings, profile });

    const before = await page.evaluate(() => window.__spriteLab.mapRenderCount || 0);
    await page.locator('#mapFileInput').setInputFiles(model);
    await page.waitForFunction(n => (window.__spriteLab.mapRenderCount || 0) > n && window.__spriteLab.mapGroundDepth,
      before, { timeout: 180000 });

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
