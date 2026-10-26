// Headless Playwright batch renderer for 40x40 character sprites & 80x80 crisp animated 3D shadows
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

function log(...args) {
  const line = args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' ') + '\n';
  fs.writeSync(1, line);
}

const CHARACTERS = [
  {
    id: 'marine',
    exportName: 'space_marine_running',
    fbxPath: path.join(WT, 'assets/inbox/space_marine_running_weapon.fbx'),
    outDir: path.join(WT, 'assets/sprites/characters/marine'),
    resolution: 40,
    neckPitch: -35,
    contrast: 1.2,
    saturation: 1.5,
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
    contrast: 1.5,
    saturation: 1.15,
    normalStrength: 0.5,
    ticks: 5,
    supersample: 2
  },
  {
    id: 'necron',
    exportName: 'necron_running_rifle',
    fbxPath: path.join(WT, 'assets/inbox/necron_running_rifle.fbx'),
    outDir: path.join(WT, 'assets/sprites/characters/necron'),
    resolution: 40,
    neckPitch: -25,
    contrast: 1.2,
    saturation: 1.5,
    normalStrength: 0.5,
    ticks: 4,
    supersample: 2
  }
];

(async () => {
  log('=== Starting Headless 40x40 Character & Animated Crisp Shadow Batch Render ===');
  const browser = await chromium.launch({
    headless: true,
    args: ['--enable-webgl', '--use-gl=swiftshader', '--disable-dev-shm-usage', '--no-sandbox']
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

    for (const ch of CHARACTERS) {
      assert(fs.existsSync(ch.fbxPath), `Missing FBX: ${ch.fbxPath}`);
      log(`\n======================================================`);
      log(`--- Rendering ${ch.id} (${path.basename(ch.fbxPath)}) at ${ch.resolution}x${ch.resolution}px ---`);
      log(`======================================================`);

      // Fresh page navigation for clean isolation
      await page.goto(fileUrl, { waitUntil: 'load', timeout: 30000 });
      await page.waitForTimeout(1000);

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
      await page.evaluate((cfg) => {
        const setVal = (id, val) => {
          const el = document.getElementById(id);
          if (el) {
            el.value = String(val);
            el.dispatchEvent(new Event('change', { bubbles: true }));
          }
        };
        setVal('exportCharName', cfg.exportName);
        setVal('resolution', cfg.resolution);
        setVal('frameCount', 8);
        setVal('elevation', 30);
        setVal('contrast', cfg.contrast);
        setVal('saturation', cfg.saturation);
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
        window.__spriteLab.supersample = cfg.supersample;
        window.__spriteLab.applyNeckPitch();
        window.__spriteLab.frames = [];
        window.__lastReportedFrames = 0;
      }, ch);
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
        if (status.count > 0 && status.count % 16 === 0) {
          log(`[PROGRESS] Rendered ${status.count}/64 frames (capturing=${status.capturing})`);
        }
        if (status.count === 64 && !status.capturing && !status.btnDisabled && !status.appRendering) {
          rendered = true;
          log(`[RENDER] Completed 64 frames for ${ch.id}!`);
          break;
        }
      }
      if (!rendered) throw new Error(`Timeout waiting for render completion for ${ch.id}`);

      // Export package
      log(`[EXPORT] Generating and extracting character package for ${ch.id}...`);
      const exportedFiles = await page.evaluate(async () => {
        const lab = window.__spriteLab;
        lab.computeAnchorData();
        lab.generateCharacterShadows();
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
      });

      log(`[OK] ${ch.id}: anchor=(${exportedFiles.anchor[0]}, ${exportedFiles.anchor[1]}), shadowSize=${exportedFiles.shadowSize}x${exportedFiles.shadowSize}`);

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
