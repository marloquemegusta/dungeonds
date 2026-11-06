// Headless character muzzle export: loads a character FBX into the offline lab with the
// render parameters stored in its existing settings.json, runs the full render (the same
// code as the "Renderizar Animacion Completa" button) and reads state.muzzleCapture.
// Merges `dirMuzzle` into settings.json ONLY if the freshly computed anchor and dirBounds
// equal the stored ones (so the committed sprites stay valid). Never writes sprite files.
//
// usage: node export_character_muzzle_headless.cjs <model.fbx> <settings.json> [--dry]
const { labGlArgs } = require('./chromium_gl_args.cjs');
const fs = require('node:fs');
const path = require('node:path');

let chromium;
for (const p of ['playwright',
  'C:/Users/malfonso/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright']) {
  try { chromium = require(p).chromium; if (chromium) break; } catch (e) {}
}
if (!chromium) { console.error('Playwright not found'); process.exit(1); }

const args = process.argv.slice(2);
const dry = args.includes('--dry');
const [model, settingsPath] = args.filter(a => !a.startsWith('--')).map(p => path.resolve(p));
if (!model || !settingsPath) {
  console.error('usage: node export_character_muzzle_headless.cjs <model.fbx> <settings.json> [--dry]');
  process.exit(2);
}
const settingsText = fs.readFileSync(settingsPath, 'utf8');
const settings = JSON.parse(settingsText);
const HTML = path.join(__dirname, 'FBX-Web-Renderer-offline.html');

(async () => {
  const browser = await chromium.launch({ headless: true, args: labGlArgs() });
  const errors = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 });
    page.on('pageerror', e => errors.push(e.stack || e.message));
    await page.goto(`file:///${HTML.split(path.sep).join('/')}`, { waitUntil: 'load' });
    await page.waitForFunction(() => !!window.__spriteLab, { timeout: 30000 });

    page.on('console', m => { if (process.env.MUZZLE_DEBUG) console.log('[page]', m.text().slice(0, 200)); });
    const log = m => { if (process.env.MUZZLE_DEBUG) console.log('[step]', m); };
    // The shadow atlas is slow to build and irrelevant here (nothing is exported).
    await page.evaluate(() => { window.__spriteLab.skipShadowGeneration = true; });
    log('lab ready');
    await page.locator('#fbxInput').setInputFiles(model);
    await page.waitForFunction(() => {
      const sel = document.getElementById('animSelect');
      return window.$ && window.$.loaded === true && sel && sel.options.length > 0;
    }, null, { timeout: 900000 });
    log('model loaded');
    await page.waitForTimeout(1500);

    const setup = await page.evaluate(async s => {
      const set = (id, value) => {
        const el = document.getElementById(id);
        if (!el || value === undefined || value === null) return false;
        el.value = String(value);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('set ' + id + ' ' + Math.round(performance.now()));
        return true;
      };
      const size = parseInt(String(s.frameSize).split('x')[0], 10);
      set('resolution', size);
      set('frameCount', s.framesPerDirection);
      set('elevation', s.cameraElevationDegrees);
      set('contrast', s.contrast);
      set('saturation', s.saturation);
      set('labBrightness', s.brightness);
      set('neckPitch', s.neckPitchDegrees);
      set('animTicks', s.ticksPerFrame);
      set('labNormal', s.normalStrength);
      set('labShadow', s.shadowSoftness);
      set('labSamples', s.webglShadowQuality);
      set('labSupersample', s.supersample);
      set('meshDisplace', s.displace);
      const inPlace = document.getElementById('inPlaceMotion');
      if (inPlace && typeof s.inPlace === 'boolean') {
        inPlace.checked = s.inPlace;
        inPlace.dispatchEvent(new Event('change', { bubbles: true }));
      }
      const lab = window.__spriteLab;
      lab.supersample = s.supersample || lab.supersample;
      if (typeof s.rigScale === 'number') lab.rigScale = s.rigScale;
      // pick animation by name
      const sel = document.getElementById('animSelect');
      const opts = Array.from(sel.options).map(o => o.textContent);
      const idx = opts.findIndex(t => t === s.animation);
      if (idx >= 0) { sel.selectedIndex = idx; sel.dispatchEvent(new Event('change', { bubbles: true })); }
      return { opts, idx, outline: document.getElementById('outlineMode')?.value };
    }, settings);
    if (setup.idx < 0) {
      console.error(`animation "${settings.animation}" not found. Available: ${setup.opts.join(' | ')}`);
      process.exitCode = 1;
      return;
    }
    log('settings applied');
    await page.waitForTimeout(1000);

    const res = await page.evaluate(async () => {
      const btn = document.getElementById('renderBtn');
      const lab = window.__spriteLab;
      lab.muzzleCapture = undefined;
      window.$.results = null;
      btn.click();
      const t0 = performance.now();
      while (!(window.$.results && window.$.results.length === 8 && !window.$.rendering && lab.anchorData && lab.muzzleCapture !== undefined)) {
        if (performance.now() - t0 > 600000) throw new Error('render timeout');
        await new Promise(r => setTimeout(r, 200));
      }
      return { muzzle: lab.muzzleCapture, anchor: lab.anchorData.anchor, dirBounds: lab.anchorData.dirBounds, rigScale: lab.rigScale };
    });

    if (errors.length) console.error('page errors:\n' + errors.join('\n'));
    if (!res.muzzle) {
      console.log(`${path.basename(model)}: no weapon mesh found; nothing written.`);
      return;
    }
    const sameJson = (a, b) => JSON.stringify(a) === JSON.stringify(b);
    const diffs = [];
    if (!sameJson(res.anchor, settings.anchor)) diffs.push(`anchor: fresh ${JSON.stringify(res.anchor)} vs stored ${JSON.stringify(settings.anchor)}`);
    for (let d = 0; d < 8; d++) {
      if (!sameJson(res.dirBounds[d], settings.dirBounds[d])) diffs.push(`dirBounds[${d}]: fresh ${JSON.stringify(res.dirBounds[d])} vs stored ${JSON.stringify(settings.dirBounds[d])}`);
    }
    if (diffs.length) {
      console.error('Fresh render does NOT match stored anchor/dirBounds; settings.json not written:\n' + diffs.join('\n'));
      console.error(`(outline=${setup.outline}, rigScale fresh=${res.rigScale} stored=${settings.rigScale})`);
      process.exitCode = 3;
      return;
    }
    console.log(`anchor and dirBounds match stored values (${path.basename(settingsPath)}).`);
    if (dry) { console.log(JSON.stringify(res.muzzle)); return; }
    const merged = { ...settings, dirMuzzle: res.muzzle };
    fs.writeFileSync(settingsPath, JSON.stringify(merged, null, 2) + (settingsText.endsWith('\n') ? '\n' : ''));
    console.log(`dirMuzzle written to ${settingsPath}`);
  } finally {
    await browser.close();
  }
})().then(() => process.exit(process.exitCode || 0)).catch(e => { console.error(e); process.exit(1); });
