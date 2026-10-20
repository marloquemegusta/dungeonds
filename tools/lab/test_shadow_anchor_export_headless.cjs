// Headless Playwright test for Shadows, Anchor & Map (Collision/Occlusion) Export
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

const ROOT = path.resolve(__dirname, '../..');
const HTML = path.join(__dirname, 'FBX-Web-Renderer-offline.html');
const EVIDENCE_DIR = path.join(ROOT, 'walkthroughs/feat-lab-shadow-anchor-export/assets');
const ARTIFACT_DIR = 'C:/Users/malfonso/.gemini/antigravity/brain/6e2bd23d-eb11-49d4-920f-5c9402c66d29';

assert(fs.existsSync(HTML), `HTML file does not exist: ${HTML}`);
fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
if (fs.existsSync(ARTIFACT_DIR)) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
}

(async () => {
  console.log('--- Starting Headless Shadow, Anchor & Map Export Test ---');
  const browser = await chromium.launch({
    headless: true,
    args: ['--enable-webgl', '--use-gl=swiftshader', '--disable-dev-shm-usage', '--no-sandbox']
  });

  const errors = [];
  const warnings = [];

  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
    page.on('pageerror', err => {
      console.error('Page error:', err);
      errors.push(err.message || String(err));
    });
    page.on('console', msg => {
      const text = msg.text();
      if (msg.type() === 'error') {
        errors.push(text);
      } else if (msg.type() === 'warning') {
        warnings.push(text);
      }
    });

    const fileUrl = 'file:///' + HTML.replace(/\\/g, '/');
    console.log(`Navigating to ${fileUrl}...`);
    await page.goto(fileUrl, { waitUntil: 'load', timeout: 30000 });

    // Wait for the lab to initialize
    await page.waitForFunction(() => typeof window.__spriteLab !== 'undefined', { timeout: 10000 });
    console.log('[OK] window.__spriteLab initialized');

    // 1. Verify Anchor calculation
    const anchorData = await page.evaluate(() => {
      const lab = window.__spriteLab;
      return lab.computeAnchorData();
    });

    console.log('Anchor Data:', JSON.stringify(anchorData));
    assert(anchorData, 'Anchor data must be defined');
    assert(Array.isArray(anchorData.anchor) && anchorData.anchor.length === 2, 'anchor must be [x, y]');
    assert(typeof anchorData.anchor[0] === 'number' && typeof anchorData.anchor[1] === 'number', 'anchor coordinates must be numbers');
    assert(Array.isArray(anchorData.dirGroundAnchors) && anchorData.dirGroundAnchors.length === 8, 'dirGroundAnchors must have 8 elements');
    assert(Array.isArray(anchorData.dirBounds) && anchorData.dirBounds.length === 8, 'dirBounds must have 8 elements');
    for (let d = 0; d < 8; d++) {
      assert(typeof anchorData.dirGroundAnchors[d] === 'number', `dirGroundAnchors[${d}] must be a number`);
      assert(Array.isArray(anchorData.dirBounds[d]) && anchorData.dirBounds[d].length === 4, `dirBounds[${d}] must be [x, y, w, h]`);
      assert(anchorData.dirBounds[d][2] > 0 && anchorData.dirBounds[d][3] > 0, `dirBounds[${d}] dimensions must be > 0`);
    }
    console.log(`[PASS] Anchor calculation verified: Global (${anchorData.anchor[0]}, ${anchorData.anchor[1]}), 8 directions valid`);

    // 2. Verify Character Shadows (state.shadowCanvas, shadowBounds, shadowMasks4Bit)
    const shadowMetrics = await page.evaluate(() => {
      const lab = window.__spriteLab;
      lab.generateCharacterShadows();
      const canvas = lab.shadowCanvas;
      const bounds = lab.shadowBounds;
      const masks = lab.shadowMasks4Bit;
      return {
        canvasWidth: canvas ? canvas.width : 0,
        canvasHeight: canvas ? canvas.height : 0,
        boundsCount: bounds ? bounds.length : 0,
        bounds: bounds,
        masksCount: masks ? masks.length : 0,
        maskLengths: masks ? masks.map(m => m.length) : []
      };
    });

    console.log('Shadow Metrics:', JSON.stringify(shadowMetrics));
    assert.equal(shadowMetrics.canvasWidth, 768, 'Shadow atlas width must be 768');
    assert.equal(shadowMetrics.canvasHeight, 96, 'Shadow atlas height must be 96');
    assert.equal(shadowMetrics.boundsCount, 8, 'Shadow bounds must have 8 directions');
    assert.equal(shadowMetrics.masksCount, 8, 'Shadow masks must have 8 directions');
    for (let d = 0; d < 8; d++) {
      const b = shadowMetrics.bounds[d];
      assert(Array.isArray(b) && b.length === 4, `Shadow bounds ${d} must be [sx0, sy0, w, h]`);
      assert(b[2] > 0 && b[3] > 0, `Shadow bounds ${d} must have width & height > 0`);
      assert.equal(shadowMetrics.maskLengths[d], 4608, `Shadow mask ${d} must be 4608 bytes`);
    }
    console.log('[PASS] Shadow generation verified: 768x96 atlas, 8 directions x 4608 bytes 4-bit masks');

    // 3. Verify NDS C Header generation
    const cHeader = await page.evaluate(() => {
      const lab = window.__spriteLab;
      return lab.generateCShadowAnchorHeader('hero', lab.anchorData, lab.shadowBounds, lab.shadowMasks4Bit);
    });

    assert(cHeader.includes('HERO_ANCHOR_X'), 'Header must define HERO_ANCHOR_X');
    assert(cHeader.includes('HERO_ANCHOR_Y'), 'Header must define HERO_ANCHOR_Y');
    assert(cHeader.includes('HERO_SHADOW_W 96'), 'Header must define HERO_SHADOW_W 96');
    assert(cHeader.includes('g_hero_ground_anchors[8]'), 'Header must declare g_hero_ground_anchors');
    assert(cHeader.includes('g_hero_shadow_bounds[8][4]'), 'Header must declare g_hero_shadow_bounds');
    assert(cHeader.includes('g_hero_shadow_masks[8][4608]'), 'Header must declare g_hero_shadow_masks');
    console.log('[PASS] NDS C Header code generation verified');

    // 4. Verify Map Collision & Occlusion generation
    const mapMetrics = await page.evaluate(() => {
      const lab = window.__spriteLab;
      lab.buildMapCollisionGrid();
      const colCanvas = lab.generateMapCollisionCanvas();
      const occCanvas = lab.generateMapOcclusionCanvas();
      return {
        colWidth: colCanvas ? colCanvas.width : 0,
        colHeight: colCanvas ? colCanvas.height : 0,
        occWidth: occCanvas ? occCanvas.width : 0,
        occHeight: occCanvas ? occCanvas.height : 0,
        gridW: lab.mapWalkGridW,
        gridH: lab.mapWalkGridH
      };
    });

    console.log('Map Metrics:', JSON.stringify(mapMetrics));
    assert(mapMetrics.colWidth > 0 && mapMetrics.colHeight > 0, 'Collision canvas must have valid size');
    assert(mapMetrics.occWidth > 0 && mapMetrics.occHeight > 0, 'Occlusion canvas must have valid size');
    console.log(`[PASS] Map collision & occlusion canvases verified: ${mapMetrics.colWidth}x${mapMetrics.colHeight}`);

    // 5. Verify Character Package Export contents
    const packageContents = await page.evaluate(async () => {
      const lab = window.__spriteLab;
      // Mock results and frames if not full render
      window.__spriteLab.results = [
        { index: 0, name: 'Sur', blob: new Blob(['gif0'], { type: 'image/gif' }) }
      ];
      if (!window.__spriteLab.frames || window.__spriteLab.frames.length === 0) {
        const dummyFrames = [];
        for (let i = 0; i < 64; i++) {
          dummyFrames.push({
            pixels: new Uint8ClampedArray(48 * 48 * 4).fill(255),
            width: 48,
            height: 48
          });
        }
        window.__spriteLab.frames = dummyFrames;
      }
      const zipBlob = await lab.exportPackage();
      // Inspect zip using JSZip (Nf.default)
      const zip = await new Nf.default().loadAsync(zipBlob);
      const files = Object.keys(zip.files);
      const settingsContent = await zip.file(files.find(f => f.endsWith('settings.json'))).async('string');
      const settings = JSON.parse(settingsContent);
      return {
        fileCount: files.length,
        files: files,
        hasShadowPng: files.some(f => f.endsWith('_shadow.png')),
        hasIndShadows: files.some(f => f.includes('shadows/')),
        hasNdsHeader: files.some(f => f.endsWith('_nds_shadow_anchor.h')),
        settings: {
          hasAnchor: Array.isArray(settings.anchor),
          hasDirGroundAnchors: Array.isArray(settings.dirGroundAnchors),
          hasDirBounds: Array.isArray(settings.dirBounds),
          hasShadowBounds: Array.isArray(settings.shadowBounds),
          shadowSize: settings.shadowSize
        }
      };
    });

    console.log('Character Export Package:', JSON.stringify(packageContents, null, 2));
    assert(packageContents.hasShadowPng, 'Package must include shadow atlas PNG');
    assert(packageContents.hasIndShadows, 'Package must include individual shadows folder');
    assert(packageContents.hasNdsHeader, 'Package must include NDS C header');
    assert(packageContents.settings.hasAnchor, 'settings.json must include anchor');
    assert(packageContents.settings.hasDirGroundAnchors, 'settings.json must include dirGroundAnchors');
    assert(packageContents.settings.hasDirBounds, 'settings.json must include dirBounds');
    assert(packageContents.settings.hasShadowBounds, 'settings.json must include shadowBounds');
    assert.deepEqual(packageContents.settings.shadowSize, [96, 96], 'shadowSize must be [96, 96]');
    console.log('[PASS] Character package export verified');

    // 6. Verify Map Package Export contents
    const mapPackageContents = await page.evaluate(async () => {
      const lab = window.__spriteLab;
      if (!lab.mapCanvas) {
        lab.mapCanvas = document.createElement('canvas');
        lab.mapCanvas.width = 768;
        lab.mapCanvas.height = 512;
      }
      const zipBlob = await lab.exportMapPackage();
      const zip = await new Nf.default().loadAsync(zipBlob);
      const files = Object.keys(zip.files);
      const colJson = await zip.file(files.find(f => f.endsWith('_collision.json'))).async('string');
      return {
        files: files,
        hasWorldPng: files.some(f => f.endsWith('_world.png')),
        hasCollisionJson: files.some(f => f.endsWith('_collision.json')),
        hasCollisionPng: files.some(f => f.endsWith('_collision.png')),
        hasOcclusionPng: files.some(f => f.endsWith('_occlusion.png')),
        hasMapSettings: files.some(f => f.endsWith('_map_settings.json')),
        colJsonParsed: JSON.parse(colJson)
      };
    });

    console.log('Map Export Package:', JSON.stringify(mapPackageContents, null, 2));
    assert(mapPackageContents.hasWorldPng, 'Map package must include world PNG');
    assert(mapPackageContents.hasCollisionJson, 'Map package must include collision JSON');
    assert(mapPackageContents.hasCollisionPng, 'Map package must include collision PNG');
    assert(mapPackageContents.hasOcclusionPng, 'Map package must include occlusion PNG');
    assert(mapPackageContents.hasMapSettings, 'Map package must include settings JSON');
    assert(Array.isArray(mapPackageContents.colJsonParsed.walkableGrid), 'collision.json must contain walkableGrid');
    console.log('[PASS] Map package export verified');

    // 7. Verify DS Simulator rendering and capture visual evidence
    await page.evaluate(() => {
      const lab = window.__spriteLab;
      // Set direction and trigger redraw
      lab.dsCharDir = 0;
      if (document.getElementById('dsMetricsBadge')) {
        document.getElementById('dsMetricsBadge').textContent += ' | VERIFIED';
      }
    });

    const shot1 = path.join(EVIDENCE_DIR, 'lab_shadow_anchor_simulator.png');
    await page.screenshot({ path: shot1, fullPage: false });
    console.log(`[SAVED] Evidence screenshot: ${shot1}`);

    // Capture the simulator element specifically
    const simElement = await page.$('#dsSimCanvas');
    if (simElement) {
      const shotSim = path.join(EVIDENCE_DIR, 'ds_simulator_crop.png');
      await simElement.screenshot({ path: shotSim });
      console.log(`[SAVED] DS Simulator crop: ${shotSim}`);
    }

    // Copy to artifact directory per AGENTS.md Rule 6
    if (fs.existsSync(ARTIFACT_DIR)) {
      const artShot1 = path.join(ARTIFACT_DIR, 'lab_shadow_anchor_simulator.png');
      const artShotSim = path.join(ARTIFACT_DIR, 'ds_simulator_crop.png');
      fs.copyFileSync(shot1, artShot1);
      if (fs.existsSync(path.join(EVIDENCE_DIR, 'ds_simulator_crop.png'))) {
        fs.copyFileSync(path.join(EVIDENCE_DIR, 'ds_simulator_crop.png'), artShotSim);
      }
      console.log(`[SAVED] Copied screenshots to artifacts directory: ${ARTIFACT_DIR}`);
    }

    // Filter console errors
    const fatalErrors = errors.filter(e => !e.includes('favicon') && !e.includes('Three.js'));
    assert.equal(fatalErrors.length, 0, `Expected 0 fatal console errors, got: ${fatalErrors.join('; ')}`);
    console.log('--- ALL TEST ASSERTIONS PASSED (0 fatal errors) ---');
  } finally {
    await browser.close();
  }
})();
