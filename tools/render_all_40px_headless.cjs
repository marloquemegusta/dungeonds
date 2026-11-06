// Headless Playwright batch renderer for 40x40 character sprites & 80x80 crisp animated 3D shadows
//
// usage: node tools/render_all_40px_headless.cjs [--only marine|charger|necron] [--out <dir>] [--profile <json>]
//   Lighting and grade come from the shared profile assets/lighting/dungeon_lighting.json (DESIGN.md 6);
//   --profile overrides the file. --out writes to <dir>/<id>/ instead of assets/sprites/characters/<id>/.
//   A character's own contrast/saturation (below) is optional and, when set, replaces the profile grade.
const { labGlArgs } = require('./lab/chromium_gl_args.cjs');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const playwrightPaths = [
  'playwright',
  'C:/Users/malfonso/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
];

let chromium;
for (const p of playwrightPaths) {
  try {
    chromium = require(p).chromium;
    if (chromium) break;
  } catch (e) {}
}

if (!chromium) {
  console.error('Playwright not found in candidate paths');
  process.exit(1);
}

const WT = path.resolve(__dirname, '..');
const HTML = path.join(WT, 'tools/lab/FBX-Web-Renderer-offline.html');

const argv = process.argv.slice(2);
const argOf = name => { const i = argv.indexOf(name); return i >= 0 ? argv[i + 1] : null; };
const ONLY = argOf('--only');
// --fast: tuning preview only (no shadow atlas); never use it for committed sprites.
const FAST = argv.includes('--fast');
const FRAMES = 8;
const OUT_ROOT = argOf('--out') ? path.resolve(argOf('--out')) : null;
const PROFILE_PATH = path.resolve(argOf('--profile') || path.join(WT, 'assets/lighting/dungeon_lighting.json'));
const PROFILE = JSON.parse(fs.readFileSync(PROFILE_PATH, 'utf8'));
// assets/inbox is untracked; the same FBX live under assets/models/characters (inbox kept as read-only fallback).
const INBOX_FALLBACK = 'C:/codexlocal/dungeonds/assets/inbox';
const firstExisting = (...paths) => paths.find(p => fs.existsSync(p)) || paths[0];

function log(...args) {
  const line = args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' ') + '\n';
  fs.writeSync(1, line);
}

const CHARACTERS = [
  {
    id: 'marine',
    exportName: 'space_marine_running',
    fbxPath: firstExisting(path.join(WT, 'assets/models/characters/spacemarine/spacemarine_running.fbx'), path.join(WT, 'assets/inbox/space_marine_running_weapon.fbx'), INBOX_FALLBACK + '/space_marine_running_weapon.fbx'),
    outDir: path.join(WT, 'assets/sprites/characters/marine'),
    resolution: 40,
    neckPitch: -35,
    contrast: null,
    saturation: null,
    normalStrength: 0.5,
    ticks: 4,
    supersample: 2
  },
  {
    id: 'charger',
    exportName: 'charger_run',
    fbxPath: path.join(WT, 'assets/models/characters/charger/Run.fbx'),
    outDir: path.join(WT, 'assets/sprites/characters/charger'),
    resolution: 40,
    neckPitch: 0,
    contrast: null,
    saturation: null,
    normalStrength: 0.5,
    ticks: 5,
    supersample: 2
  },
  {
    id: 'necron',
    exportName: 'necron_running_rifle',
    fbxPath: firstExisting(path.join(WT, 'assets/models/characters/necron/necron_running_rifle.fbx'), path.join(WT, 'assets/inbox/necron_running_rifle.fbx'), INBOX_FALLBACK + '/necron_running_rifle.fbx'),
    outDir: path.join(WT, 'assets/sprites/characters/necron'),
    resolution: 40,
    neckPitch: -25,
    contrast: null,
    saturation: null,
    normalStrength: 0.5,
    ticks: 4,
    supersample: 2
  }
];

(async () => {
  log('=== Starting Headless 40x40 Character & Animated Crisp Shadow Batch Render ===');
  const browser = await chromium.launch({
    headless: true,
    args: labGlArgs()
  });

  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
    page.on('console', msg => {
      const t = msg.type();
      if (t === 'error' || t === 'warning') {
        log(`[PAGE ${t}] ${msg.text()}`);
      }
    });
    page.on('pageerror', err => log('[PAGE ERROR] ' + (err.stack || err.message || err)));

    const fileUrl = 'file:///' + HTML.replace(/\\/g, '/');

    for (const ch of CHARACTERS.filter(c => !ONLY || c.id === ONLY)) {
      if (OUT_ROOT) ch.outDir = path.join(OUT_ROOT, ch.id);
      assert(fs.existsSync(ch.fbxPath), `Missing FBX: ${ch.fbxPath}`);
      log(`\n======================================================`);
      log(`--- Rendering ${ch.id} (${path.basename(ch.fbxPath)}) at ${ch.resolution}x${ch.resolution}px ---`);
      log(`======================================================`);

      // Fresh page navigation for clean isolation
      await page.goto(fileUrl, { waitUntil: 'load', timeout: 30000 });
      await page.waitForTimeout(1000);
      await page.evaluate(p => window.__spriteLab.setLightingProfile(p), PROFILE);
      log(`[LIGHT] profile ${PROFILE.name} v${PROFILE.version} from ${PROFILE_PATH}`);

      log(`[FBX] Loading FBX file for ${ch.id}: ${path.basename(ch.fbxPath)}...`);
      await page.setInputFiles('#fbxInput', ch.fbxPath);

      // Poll until model is loaded
      let loaded = false;
      for (let t = 0; t < 60; t++) {
        await page.waitForTimeout(2000);
        loaded = await page.evaluate(() => {
          const btn = document.getElementById('renderBtn') || document.getElementById('btnRender');
          return window.$ && window.$.loaded && !window.$.rendering && btn && !btn.disabled;
        });
        if (loaded) {
          log(`[FBX] Loaded ${ch.id} successfully after ${(t + 1) * 2}s.`);
          break;
        }
      }
      if (!loaded) throw new Error(`Timeout loading FBX for ${ch.id}`);

      // Apply settings
      log(`[SETTINGS] Applying settings for ${ch.id}...`);
      await page.evaluate(({ cfg, profile }) => {
        const setVal = (id, val) => {
          const el = document.getElementById(id);
          if (el) {
            el.value = String(val);
            el.dispatchEvent(new Event('change', { bubbles: true }));
          }
        };
        setVal('exportCharName', cfg.exportName);
        setVal('resolution', cfg.resolution);
        setVal('frameCount', cfg.frames);
        setVal('elevation', 30);
        if (cfg.contrast != null) setVal('contrast', cfg.contrast);
        if (cfg.saturation != null) setVal('saturation', cfg.saturation);
        setVal('labNormal', cfg.normalStrength);
        setVal('animTicks', cfg.ticks);
        setVal('labSupersample', cfg.supersample);
        setVal('neckPitch', cfg.neckPitch);
        setVal('neckTilt', cfg.neckPitch);
        const inPlace = document.getElementById('inPlaceMotion');
        if (inPlace && !inPlace.checked) {
          inPlace.checked = true;
          inPlace.dispatchEvent(new Event('change', { bubbles: true }));
        }
        window.__spriteLab.setLightingProfile(profile);
        window.__spriteLab.supersample = cfg.supersample;
        window.__spriteLab.applyNeckPitch();
        window.__spriteLab.frames = [];
        window.__lastReportedFrames = 0;
      }, { cfg: { ...ch, frames: FRAMES }, profile: PROFILE });
      log(`[SETTINGS] Applied settings for ${ch.id}. Triggering render via DOM...`);

      // Trigger full 8-direction x 8-frame render via DOM click
      await page.evaluate(() => {
        const btn = document.getElementById('renderBtn') || document.getElementById('btnRender');
        if (!btn) throw new Error('renderBtn not found');
        btn.click();
      });

      // Poll until 64 frames are rendered
      let rendered = false;
      for (let t = 0; t < 120; t++) {
        await page.waitForTimeout(2000);
        const status = await page.evaluate(() => {
          const lab = window.__spriteLab;
          const btn = document.getElementById('downloadPackageBtn') || document.getElementById('btnExportZip');
          const count = lab && lab.frames ? lab.frames.length : 0;
          return {
            count,
            capturing: lab ? lab.capturing : null,
            btnDisabled: btn ? btn.disabled : null,
            appRendering: window.$ ? window.$.rendering : null
          };
        });
        if (status.count > 0 && status.count % 16 === 0 && !FAST) {
          log(`[PROGRESS] Rendered ${status.count}/64 frames (capturing=${status.capturing})`);
        }
        if (status.count === 8 * FRAMES && !status.capturing && !status.btnDisabled && !status.appRendering) {
          rendered = true;
          log(`[RENDER] Completed 64 frames for ${ch.id}!`);
          break;
        }
      }
      if (!rendered) throw new Error(`Timeout waiting for render completion for ${ch.id}`);

      // Export package
      log(`[EXPORT] Generating and extracting character package for ${ch.id}...`);
      const exportedFiles = await page.evaluate(async (fast) => {
        const lab = window.__spriteLab;
        lab.computeAnchorData();
        if (!fast) lab.generateCharacterShadows();
        const zipBlob = await lab.exportPackage();
        const JSZip = lab.JSZip || window.JSZip || window.Nf?.default;
        const zip = await new JSZip().loadAsync(zipBlob);
        const out = {};
        for (const [relPath, fileObj] of Object.entries(zip.files)) {
          if (fileObj.dir) continue;
          const b64 = await fileObj.async('base64');
          out[relPath] = b64;
        }
        return {
          anchor: lab.anchorData.anchor,
          shadowSize: lab.shadowSize,
          files: out
        };
      }, FAST);

      log(`[OK] ${ch.id}: anchor=(${exportedFiles.anchor[0]}, ${exportedFiles.anchor[1]}), shadowSize=${exportedFiles.shadowSize}x${exportedFiles.shadowSize}`);

      // Gameplay-facing stride/speed metrics and the model label come from the committed settings.json,
      // not from the re-render (re-rendering must not change character speed or the contract).
      const KEEP = ['model', 'stride3dMeters', 'strideRatio', 'stridePixels', 'speedFixed8_8'];
      const prevSettingsPath = path.join(ch.outDir, 'settings.json');
      if (fs.existsSync(prevSettingsPath) && exportedFiles.files['settings.json']) {
        const prev = JSON.parse(fs.readFileSync(prevSettingsPath, 'utf8'));
        const next = JSON.parse(Buffer.from(exportedFiles.files['settings.json'], 'base64').toString('utf8'));
        for (const k of KEEP) if (prev[k] !== undefined) next[k] = prev[k];
        exportedFiles.files['settings.json'] = Buffer.from(JSON.stringify(next, null, 2)).toString('base64');
      }
      // Write all exported files to ch.outDir
      fs.mkdirSync(ch.outDir, { recursive: true });
      for (const [relPath, b64] of Object.entries(exportedFiles.files)) {
        const dest = path.join(ch.outDir, relPath);
        fs.mkdirSync(path.dirname(dest), { recursive: true });
        fs.writeFileSync(dest, Buffer.from(b64, 'base64'));
      }
      log(`[SAVED] Wrote ${Object.keys(exportedFiles.files).length} files to ${ch.outDir}`);
    }

    log('\n=== ALL 3 CHARACTERS RENDERED AT 40x40 WITH 80x80 ANIMATED CRISP SHADOWS ===');
  } finally {
    await browser.close();
  }
})();
