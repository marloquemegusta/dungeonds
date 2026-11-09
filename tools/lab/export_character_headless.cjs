// Headless character export: loads a character FBX into the offline lab, applies the render
// parameters of a template settings.json (default: the charger's), renders 8 directions x N
// frames and writes the same package as the "Exportar paquete completo" button
// (spritesheet.png, shadow.png, settings.json, nds_shadow_anchor.h, dirs/, frames/, shadows/).
// Chromium runs HEADLESS (AGENTS.md rule 4).
//
// usage: node export_character_headless.cjs <model.fbx> <outDir> [--template settings.json]
//          [--anim "<clip name>"] [--rigScale N] [--light <preset>] [--outline <pixel|sobel|none>]
//          [--saturation N] [--list]
//   --list  prints the animation clips and exits without rendering.
const fs = require('node:fs');
const path = require('node:path');

let chromium;
for (const p of ['playwright',
  'C:/Users/malfonso/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright']) {
  try { chromium = require(p).chromium; if (chromium) break; } catch (e) {}
}
if (!chromium) { console.error('Playwright not found'); process.exit(1); }

const argv = process.argv.slice(2);
const opt = (n) => { const i = argv.indexOf(n); return i >= 0 ? argv[i + 1] : undefined; };
const flagVals = new Set(['--template', '--anim', '--rigScale', '--light', '--outline', '--saturation']);
const pos = argv.filter((a, i) => !a.startsWith('--') && !(i > 0 && flagVals.has(argv[i - 1])));
const listOnly = argv.includes('--list');
const model = pos[0] && path.resolve(pos[0]);
const outDir = pos[1] && path.resolve(pos[1]);
if (!model || (!outDir && !listOnly)) {
  console.error('usage: node export_character_headless.cjs <model.fbx> <outDir> [--template settings.json] [--anim name] [--rigScale N] [--light preset] [--outline mode] [--saturation N] [--list]');
  process.exit(2);
}
const templatePath = path.resolve(opt('--template') ||
  path.join(__dirname, '../../assets/sprites/characters/charger/settings.json'));
const s = JSON.parse(fs.readFileSync(templatePath, 'utf8'));
const HTML = path.join(__dirname, 'FBX-Web-Renderer-offline.html');

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--enable-webgl', '--use-gl=swiftshader', '--disable-dev-shm-usage', '--no-sandbox'] });
  const errors = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 });
    page.on('pageerror', e => errors.push(e.stack || e.message));
    await page.goto(`file:///${HTML.split(path.sep).join('/')}`, { waitUntil: 'load' });
    await page.waitForFunction(() => !!window.__spriteLab, { timeout: 30000 });
    await page.locator('#fbxInput').setInputFiles(model);
    await page.waitForFunction(() => {
      const sel = document.getElementById('animSelect');
      return window.$ && window.$.loaded === true && sel && sel.options.length > 0;
    }, null, { timeout: 900000 });
    await page.waitForTimeout(1500);

    const anims = await page.evaluate(() => Array.from(document.getElementById('animSelect').options).map(o => o.textContent));
    console.log('animations: ' + JSON.stringify(anims));
    if (listOnly) return;

    const anim = opt('--anim') || anims[0];
    const rigScale = opt('--rigScale') !== undefined ? parseFloat(opt('--rigScale')) : s.rigScale;
    const lightPreset = opt('--light') || s.lightPreset || (s.lighting && s.lighting.preset);
    const outlineMode = opt('--outline') || s.outlineMode;
    const saturation = opt('--saturation') !== undefined ? parseFloat(opt('--saturation')) : s.saturation;

    const setup = await page.evaluate(async ({ s, anim, rigScale, lightPreset, outlineMode, saturation }) => {
      const set = (id, v) => {
        const el = document.getElementById(id);
        if (!el || v === undefined || v === null) return;
        el.value = String(v);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
      };
      set('resolution', parseInt(String(s.frameSize).split('x')[0], 10));
      set('frameCount', s.framesPerDirection);
      set('elevation', s.cameraElevationDegrees);
      set('labBrightness', s.brightness);
      set('neckPitch', s.neckPitchDegrees);
      set('animTicks', s.ticksPerFrame);
      set('labNormal', s.normalStrength);
      set('labShadow', s.shadowSoftness);
      set('labSamples', s.webglShadowQuality);
      set('labSupersample', s.supersample);
      set('meshDisplace', s.displace);

      if (lightPreset !== undefined && lightPreset !== null) {
        set('lightPreset', lightPreset);
        if (typeof window.applyDungeonLighting === 'function') {
          window.applyDungeonLighting(lightPreset);
        }
      }
      if (outlineMode !== undefined && outlineMode !== null) {
        set('outlineMode', outlineMode);
      }

      set('contrast', s.contrast);
      set('saturation', saturation !== undefined && saturation !== null ? saturation : s.saturation);

      const inPlace = document.getElementById('inPlaceMotion');
      if (inPlace) { inPlace.checked = !!s.inPlace; inPlace.dispatchEvent(new Event('change', { bubbles: true })); }
      const lab = window.__spriteLab;
      lab.supersample = s.supersample || lab.supersample;
      if (typeof rigScale === 'number') lab.rigScale = rigScale;
      const sel = document.getElementById('animSelect');
      const idx = Array.from(sel.options).findIndex(o => o.textContent === anim);
      if (idx < 0) return { ok: false };
      sel.selectedIndex = idx; sel.dispatchEvent(new Event('change', { bubbles: true }));
      return {
        ok: true,
        rigScale: lab.rigScale,
        lightPreset: document.getElementById('lightPreset')?.value,
        outlineMode: document.getElementById('outlineMode')?.value,
        contrast: document.getElementById('contrast')?.value,
        saturation: document.getElementById('saturation')?.value,
        keyLight: document.getElementById('keyLight')?.value,
        keyColor: document.getElementById('keyColor')?.value
      };
    }, { s, anim, rigScale, lightPreset, outlineMode, saturation });
    if (!setup.ok) { console.error(`animation "${anim}" not found`); process.exitCode = 1; return; }
    console.log('Setup applied: ' + JSON.stringify(setup));
    await page.waitForTimeout(1000);

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
    if (errors.length) console.error('page errors:\n' + errors.join('\n'));
    const zipPath = path.join(require('node:os').tmpdir(), `dungeonds_char_export_${Date.now()}_${process.pid}.zip`);
    fs.writeFileSync(zipPath, Buffer.from(b64, 'base64'));
    fs.mkdirSync(outDir, { recursive: true });
    require('node:child_process').execFileSync(process.platform === 'win32' ? 'C:/Windows/System32/tar.exe' : 'tar', ['-xf', zipPath, '-C', outDir]);
    fs.unlinkSync(zipPath);

    const outSettings = path.join(outDir, 'settings.json');
    if (fs.existsSync(outSettings)) {
      try {
        const outData = JSON.parse(fs.readFileSync(outSettings, 'utf8'));
        if (lightPreset) outData.lightPreset = lightPreset;
        if (outlineMode) outData.outlineMode = outlineMode;
        fs.writeFileSync(outSettings, JSON.stringify(outData, null, 2) + '\n');
      } catch (e) {
        console.warn('Could not update exported settings.json with light/outline:', e.message);
      }
    }

    console.log('package written to ' + outDir);
  } finally {
    await browser.close();
  }
})().then(() => process.exit(process.exitCode || 0)).catch(e => { console.error(e); process.exit(1); });
