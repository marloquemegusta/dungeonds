// Headless character export: loads a character FBX into the offline lab, applies the render
// parameters of a template settings.json (default: the charger's), renders 8 directions x N
// frames and writes the same package as the "Exportar paquete completo" button
// (spritesheet.png, shadow.png, settings.json, nds_shadow_anchor.h, dirs/, frames/, shadows/).
// Chromium runs HEADLESS (AGENTS.md rule 4).
//
// usage: node export_character_headless.cjs <model.fbx> <outDir> [--template settings.json]
//          [--anim "<clip name>"] [--rigScale N] [--light <preset>] [--outline <pixel|sobel|none>]
//          [--saturation N] [--muzzleBone <bone name>] [--muzzleForward F] [--fitZoom Z] [--resolution N] [--list]
//   --muzzleBone  no weapon: the muzzle (projected into dirMuzzle) is taken from this bone, pushed F model
//                 heights along the model front (+Z). Without it the muzzle is the weapon tip (or none).
//   --fitZoom Z   camera zoom-out factor: 1 fills the cell with the model extent; < 1 shrinks the sprite.
//   --resolution N override frameSize (e.g. 60 for 60x60).
//   --legibility L  anterior (default: today's look, AgX tone mapping) or c2 (DESIGN.md 6.9.1b: supersample 4,
//                   THREE.NeutralToneMapping, lab contrast 1.0, then soft S-curve + alpha-aware sharpen on all frames).
//   --tone T        tone mapping override: agx or neutral. Default follows --legibility (c2 -> neutral).
//   --supersample N / --contrast N  explicit overrides of the template's supersample / lab contrast
//                   (c2 implies 4 / 1.0 unless given).
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
const flagVals = new Set(['--template', '--anim', '--rigScale', '--light', '--outline', '--saturation', '--muzzleBone', '--muzzleForward', '--fitZoom', '--resolution', '--tone', '--supersample', '--contrast', '--legibility']);
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

    const anim = opt('--anim') || s.animation || anims[0];
    const rigScale = opt('--rigScale') !== undefined ? parseFloat(opt('--rigScale')) : s.rigScale;
    const lightPreset = opt('--light') || s.lightPreset || (s.lighting && s.lighting.preset);
    const outlineMode = opt('--outline') || s.outlineMode;
    const saturation = opt('--saturation') !== undefined ? parseFloat(opt('--saturation')) : s.saturation;
    const muzzleBone = opt('--muzzleBone') || (s.muzzleSource && s.muzzleSource.bone) || undefined;
    const muzzleForward = opt('--muzzleForward') !== undefined ? parseFloat(opt('--muzzleForward')) : (s.muzzleSource && s.muzzleSource.forward !== undefined ? s.muzzleSource.forward : undefined);
    const fitZoom = opt('--fitZoom') !== undefined ? parseFloat(opt('--fitZoom')) : (s.fitZoom !== undefined ? s.fitZoom : 1);
    const resolution = opt('--resolution') !== undefined ? parseInt(opt('--resolution'), 10) : undefined;
    const legibility = opt('--legibility') || 'anterior';
    if (!['anterior', 'c2'].includes(legibility)) { console.error('--legibility must be anterior or c2'); process.exit(2); }
    const toneOpt = opt('--tone');
    if (toneOpt !== undefined && !['agx', 'neutral'].includes(toneOpt)) { console.error('--tone must be agx or neutral'); process.exit(2); }
    const tone = toneOpt || (legibility === 'c2' ? 'neutral' : 'agx');
    const supersampleOpt = opt('--supersample') !== undefined ? parseInt(opt('--supersample'), 10) : undefined;
    const contrastOpt = opt('--contrast') !== undefined ? parseFloat(opt('--contrast')) : undefined;
    if (legibility === 'c2') { s.supersample = 4; s.contrast = 1.0; }
    if (supersampleOpt !== undefined) s.supersample = supersampleOpt;
    if (contrastOpt !== undefined) s.contrast = contrastOpt;

    const setup = await page.evaluate(async ({ s, anim, rigScale, lightPreset, outlineMode, saturation, muzzleBone, muzzleForward, fitZoom, resolution, tone, toneOpt, legibility }) => {
      const set = (id, v) => {
        const el = document.getElementById(id);
        if (!el || v === undefined || v === null) return;
        el.value = String(v);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
      };
      // Preset de legibilidad primero (C2 fuerza supersample/contraste); los valores efectivos se fijan justo despues.
      set('labLegibility', legibility);
      set('resolution', resolution !== undefined ? resolution : parseInt(String(s.frameSize).split('x')[0], 10));
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
      lab.muzzleBone = muzzleBone || null;
      if (typeof muzzleForward === 'number') lab.muzzleForward = muzzleForward;
      lab.toneMapping = toneOpt || null; // null: el preset decide (c2 -> neutral, anterior -> agx)
      lab.fitZoom = typeof fitZoom === 'number' ? fitZoom : 1;
      const sel = document.getElementById('animSelect');
      let idx = Array.from(sel.options).findIndex(o => o.textContent === anim);
      if (idx < 0) {
        const clean = (t) => (t || '').replace(/\s*\(\s*\d+(?:\.\d+)?s\s*\)\s*$/, '').trim();
        const target = clean(anim);
        idx = Array.from(sel.options).findIndex(o => clean(o.textContent) === target);
      }
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
    }, { s, anim, rigScale, lightPreset, outlineMode, saturation, muzzleBone, muzzleForward, fitZoom, resolution, tone, toneOpt, legibility });
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
        if (muzzleBone) outData.muzzleSource = { bone: muzzleBone, forward: muzzleForward ?? 0.05 };
        if (fitZoom !== undefined) outData.fitZoom = fitZoom;
        outData.toneMapping = tone;
        outData.legibility = legibility;
        if (s.speedFixed8_8 !== undefined) outData.speedFixed8_8 = s.speedFixed8_8;
        if (s.ticksPerFrame !== undefined) outData.ticksPerFrame = s.ticksPerFrame;
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
