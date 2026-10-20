// Headless Playwright test for short ZIP names, internal path limits (<35 chars), and neck/head tilt reactivity
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
const EVIDENCE_DIR = path.join(ROOT, 'walkthroughs/fix-lab-zip-names-and-neck-tilt/assets');
const ARTIFACT_DIR = 'C:/Users/malfonso/.gemini/antigravity/brain/e5c8e8b9-3a9a-4cbb-9ccc-ef7ce4d0214f';

assert(fs.existsSync(HTML), `HTML file does not exist: ${HTML}`);
fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
if (fs.existsSync(ARTIFACT_DIR)) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
}

function saveScreenshot(filename, buffer) {
  const localPath = path.join(EVIDENCE_DIR, filename);
  fs.writeFileSync(localPath, buffer);
  console.log(`[SAVED] ${localPath}`);
  if (fs.existsSync(ARTIFACT_DIR)) {
    const artifactPath = path.join(ARTIFACT_DIR, filename);
    fs.writeFileSync(artifactPath, buffer);
    console.log(`[SAVED ARTIFACT] ${artifactPath}`);
  }
}

(async () => {
  console.log('=== Starting Test: Short ZIP Names & Neck Tilt Reactivity ===');
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
        console.error('Console error:', text);
        errors.push(text);
      } else if (msg.type() === 'warning') {
        warnings.push(text);
      }
    });

    const fileUrl = 'file:///' + HTML.replace(/\\/g, '/');
    console.log(`Navigating to ${fileUrl}...`);
    await page.goto(fileUrl, { waitUntil: 'load', timeout: 30000 });

    // Wait for lab initialization
    await page.waitForFunction(() => typeof window.__spriteLab !== 'undefined', { timeout: 10000 });
    console.log('[OK] window.__spriteLab loaded successfully');

    // -------------------------------------------------------------
    // Test 1: DOM Elements exist and defaults are correct
    // -------------------------------------------------------------
    console.log('--- Test 1: Checking DOM elements and inputs ---');
    const domCheck = await page.evaluate(() => {
      const charName = document.querySelector('#exportCharName');
      const mapName = document.querySelector('#exportMapName');
      const neckPitch = document.querySelector('#neckPitch');
      const neckTilt = document.querySelector('#neckTilt');
      const neckVal = document.querySelector('#neckPitchValue');
      const zipBtn = document.querySelector('#downloadPackageBtn');
      const mapZipBtn = document.querySelector('#btnExportMapZip');

      return {
        hasCharName: !!charName,
        charNameVal: charName ? charName.value : null,
        charNameMax: charName ? charName.maxLength : null,
        hasMapName: !!mapName,
        mapNameVal: mapName ? mapName.value : null,
        mapNameMax: mapName ? mapName.maxLength : null,
        hasNeckPitch: !!neckPitch,
        neckPitchVal: neckPitch ? neckPitch.value : null,
        hasNeckTilt: !!neckTilt,
        neckTiltVal: neckTilt ? neckTilt.value : null,
        neckValText: neckVal ? neckVal.textContent : null,
        hasZipBtn: !!zipBtn,
        zipBtnVisible: zipBtn && !zipBtn.hidden && zipBtn.style.display !== 'none',
        hasMapZipBtn: !!mapZipBtn
      };
    });

    console.log('DOM Elements State:', JSON.stringify(domCheck, null, 2));
    assert(domCheck.hasCharName, '#exportCharName must exist');
    assert.equal(domCheck.charNameVal, 'hero', '#exportCharName default must be "hero"');
    assert.equal(domCheck.charNameMax, 20, '#exportCharName maxLength must be 20');
    assert(domCheck.hasMapName, '#exportMapName must exist');
    assert.equal(domCheck.mapNameVal, 'dungeon', '#exportMapName default must be "dungeon"');
    assert.equal(domCheck.mapNameMax, 20, '#exportMapName maxLength must be 20');
    assert(domCheck.hasNeckPitch, '#neckPitch slider must exist');
    assert(domCheck.hasNeckTilt, '#neckTilt number input must exist');
    assert.equal(domCheck.neckValText, '0°', '#neckPitchValue must display 0°');
    assert(domCheck.hasZipBtn, '#downloadPackageBtn must exist');
    assert(domCheck.zipBtnVisible, '#downloadPackageBtn must be visible');
    assert(domCheck.hasMapZipBtn, '#btnExportMapZip must exist');
    console.log('[PASS] Test 1: All required DOM elements and initial attributes verified');

    // Capture UI initial screenshot
    const uiInitBuf = await page.screenshot();
    saveScreenshot('ui_short_zip_names.png', uiInitBuf);

    // -------------------------------------------------------------
    // Test 2: Input sanitization & short name enforcement
    // -------------------------------------------------------------
    console.log('--- Test 2: Name sanitization and length limits ---');
    const sanitizationResult = await page.evaluate(() => {
      const lab = window.__spriteLab;
      const testNames = [
        ['VeryLongCharacterName_With_Many_Suffixes_Walk_Cycle.fbx', lab.sanitizeExportName('VeryLongCharacterName_With_Many_Suffixes_Walk_Cycle.fbx', 'hero')],
        ['Hero-Warrior!@#$Special_123', lab.sanitizeExportName('Hero-Warrior!@#$Special_123', 'hero')],
        ['___Multiple__Underscores___', lab.sanitizeExportName('___Multiple__Underscores___', 'hero')],
        ['', lab.sanitizeExportName('', 'fallback')],
        ['skeleton.fbx', lab.sanitizeExportName('skeleton.fbx', 'hero')]
      ];
      return testNames;
    });

    console.log('Sanitization tests:', sanitizationResult);
    for (const [raw, sanitized] of sanitizationResult) {
      assert(sanitized.length <= 20, `Sanitized name "${sanitized}" exceeds 20 characters`);
      assert(/^[a-z0-9_]+$/.test(sanitized), `Sanitized name "${sanitized}" contains invalid characters`);
      assert(!sanitized.startsWith('_') && !sanitized.endsWith('_'), `Sanitized name "${sanitized}" has leading/trailing underscores`);
    }
    console.log('[PASS] Test 2: Name sanitization logic verified (all <= 20 chars, a-z0-9_)');

    // -------------------------------------------------------------
    // Test 3: Demo procedural model loading & neck tilt detection
    // -------------------------------------------------------------
    console.log('--- Test 3: Demo model loading & neck tilt sync ---');
    await page.click('#btnLoadDemo');
    await page.waitForTimeout(500);

    const demoLoaded = await page.evaluate(() => {
      const charName = document.querySelector('#exportCharName')?.value;
      const targets = window.__spriteLab.getNeckTiltTargets(window.$.model);
      return {
        charName,
        targetCount: targets.length,
        targetName: targets[0]?.name || null
      };
    });

    console.log('Demo Loaded Info:', demoLoaded);
    assert.equal(demoLoaded.charName, 'demo_procedural', 'Loading demo model must update #exportCharName to "demo_procedural"');
    assert(demoLoaded.targetCount >= 1, 'getNeckTiltTargets must detect at least 1 target on demo model');
    console.log('[PASS] Test 3: Demo model loaded with neck/head target detected');

    // -------------------------------------------------------------
    // Test 4: Real Skinned Mesh FBX model & Neck Tilt Reactivity
    // -------------------------------------------------------------
    console.log('--- Test 4: Loading FBX model (skeleton.fbx) & testing neck tilt reactivity ---');
    const skeletonFbx = path.join(ROOT, 'assets/models/characters/skeleton/skeleton.fbx');
    assert(fs.existsSync(skeletonFbx), `Skeleton FBX not found: ${skeletonFbx}`);

    // Set file in #fbxInput
    await page.locator('#fbxInput').setInputFiles(skeletonFbx);
    await page.waitForFunction(() => window.$.loaded === true && window.document.getElementById('fileName')?.textContent.includes('skeleton'), { timeout: 15000 });
    await page.waitForTimeout(600);

    const fbxLoaded = await page.evaluate(() => {
      const charName = document.querySelector('#exportCharName')?.value;
      const targets = window.__spriteLab.getNeckTiltTargets(window.$.model);
      return {
        charName,
        modelLoaded: window.$.loaded,
        targetNames: targets.map(t => t.name)
      };
    });

    console.log('FBX Loaded Info:', fbxLoaded);
    assert.equal(fbxLoaded.charName, 'skeleton', '#exportCharName must be "skeleton" for skeleton.fbx');
    assert(fbxLoaded.targetNames.length >= 1, 'FBX model must have neck/head targets found');
    console.log('[PASS] FBX skeleton loaded, targets:', fbxLoaded.targetNames);

    // 4.1 Measure initial world rotation of neck target at 0°
    const rot0 = await page.evaluate(() => {
      window.__spriteLab.syncNeckTilt(0, true);
      const targets = window.__spriteLab.getNeckTiltTargets(window.$.model);
      const bone = targets[0];
      const q = bone.quaternion.clone();
      const worldQ = new (q.constructor)();
      bone.getWorldQuaternion(worldQ);
      return {
        local: { x: q.x, y: q.y, z: q.z, w: q.w },
        world: { x: worldQ.x, y: worldQ.y, z: worldQ.z, w: worldQ.w }
      };
    });
    console.log('Rotation at 0°:', rot0);

    // Snapshot at 0°
    const snap0 = await page.evaluate(() => {
      const canvas = document.querySelector('#canvasArea canvas');
      return canvas ? canvas.toDataURL('image/png') : null;
    });

    // 4.2 Set neck tilt to +25°
    console.log('Testing neck tilt at +25°...');
    const rotPlus25 = await page.evaluate(() => {
      const slider = document.querySelector('#neckPitch');
      slider.value = '25';
      slider.dispatchEvent(new Event('input', { bubbles: true }));
      slider.dispatchEvent(new Event('change', { bubbles: true }));

      // Tick mixer to simulate animation step
      if (window.$.mixer) {
        window.$.mixer.update(0.016);
      }

      const targets = window.__spriteLab.getNeckTiltTargets(window.$.model);
      const bone = targets[0];
      const q = bone.quaternion.clone();
      const worldQ = new (q.constructor)();
      bone.getWorldQuaternion(worldQ);

      return {
        pitchVal: document.querySelector('#neckPitch')?.value,
        tiltVal: document.querySelector('#neckTilt')?.value,
        pitchLabel: document.querySelector('#neckPitchValue')?.textContent,
        local: { x: q.x, y: q.y, z: q.z, w: q.w },
        world: { x: worldQ.x, y: worldQ.y, z: worldQ.z, w: worldQ.w }
      };
    });

    console.log('Rotation at +25° (after mixer.update):', rotPlus25);
    assert.equal(rotPlus25.pitchVal, '25');
    assert.equal(rotPlus25.tiltVal, '25');
    assert.equal(rotPlus25.pitchLabel, '25°');
    // Verify world rotation changed from 0°
    const diffWorldPlus = Math.abs(rotPlus25.world.x - rot0.world.x) + Math.abs(rotPlus25.world.y - rot0.world.y) + Math.abs(rotPlus25.world.z - rot0.world.z) + Math.abs(rotPlus25.world.w - rot0.world.w);
    console.log('Delta world quaternion (|q25 - q0|):', diffWorldPlus);
    assert(diffWorldPlus > 0.01, 'Bone world rotation must change when tilted +25°');

    await page.waitForTimeout(300);
    const bufPlus25 = await page.screenshot();
    saveScreenshot('neck_tilt_plus25.png', bufPlus25);

    const snapPlus25 = await page.evaluate(() => {
      const canvas = document.querySelector('#canvasArea canvas');
      return canvas ? canvas.toDataURL('image/png') : null;
    });
    assert(snapPlus25 !== snap0, 'Rendered canvas pixels must differ between tilt=0° and tilt=+25°');
    console.log('[PASS] +25° neck tilt changes bone world rotation and rendered frame pixels');

    // 4.3 Set neck tilt to -25°
    console.log('Testing neck tilt at -25°...');
    const rotMinus25 = await page.evaluate(() => {
      const tiltInput = document.querySelector('#neckTilt');
      tiltInput.value = '-25';
      tiltInput.dispatchEvent(new Event('input', { bubbles: true }));
      tiltInput.dispatchEvent(new Event('change', { bubbles: true }));

      // Tick mixer to simulate animation step
      if (window.$.mixer) {
        window.$.mixer.update(0.016);
      }

      const targets = window.__spriteLab.getNeckTiltTargets(window.$.model);
      const bone = targets[0];
      const q = bone.quaternion.clone();
      const worldQ = new (q.constructor)();
      bone.getWorldQuaternion(worldQ);

      return {
        pitchVal: document.querySelector('#neckPitch')?.value,
        tiltVal: document.querySelector('#neckTilt')?.value,
        pitchLabel: document.querySelector('#neckPitchValue')?.textContent,
        local: { x: q.x, y: q.y, z: q.z, w: q.w },
        world: { x: worldQ.x, y: worldQ.y, z: worldQ.z, w: worldQ.w }
      };
    });

    console.log('Rotation at -25° (after mixer.update):', rotMinus25);
    assert.equal(rotMinus25.pitchVal, '-25');
    assert.equal(rotMinus25.tiltVal, '-25');
    assert.equal(rotMinus25.pitchLabel, '-25°');
    const diffWorldMinus = Math.abs(rotMinus25.world.x - rotPlus25.world.x) + Math.abs(rotMinus25.world.y - rotPlus25.world.y) + Math.abs(rotMinus25.world.z - rotPlus25.world.z) + Math.abs(rotMinus25.world.w - rotPlus25.world.w);
    console.log('Delta world quaternion (|q(-25) - q(+25)|):', diffWorldMinus);
    assert(diffWorldMinus > 0.01, 'Bone world rotation must change between +25° and -25°');

    await page.waitForTimeout(300);
    const bufMinus25 = await page.screenshot();
    saveScreenshot('neck_tilt_minus25.png', bufMinus25);

    const snapMinus25 = await page.evaluate(() => {
      const canvas = document.querySelector('#canvasArea canvas');
      return canvas ? canvas.toDataURL('image/png') : null;
    });
    assert(snapMinus25 !== snapPlus25, 'Rendered canvas pixels must differ between tilt=+25° and tilt=-25°');
    console.log('[PASS] -25° neck tilt verified (distinct world rotation and distinct pixel render)');

    // -------------------------------------------------------------
    // Test 5: Character ZIP Package Export & Internal Path Limits (< 35 chars)
    // -------------------------------------------------------------
    console.log('--- Test 5: Character ZIP Package structure & path length limits ---');
    // Set custom short name
    await page.evaluate(() => {
      const input = document.querySelector('#exportCharName');
      input.value = 'hero_skel';
      // Low resolution and frameCount for instant render
      document.querySelector('#resolution').value = '32';
      document.querySelector('#frameCount').value = '4';
    });

    // Render animation frames
    console.log('Rendering 8 directions (32x32, 4 frames)...');
    await page.click('#renderBtn');
    await page.waitForFunction(() => !document.querySelector('#renderBtn').disabled, { timeout: 30000 });
    console.log('[OK] Render complete');

    // Generate package and inspect entries inside browser
    const charZipReport = await page.evaluate(async () => {
      const blob = await window.__spriteLab.exportPackage();
      const zip = await new window.__spriteLab.JSZip().loadAsync(blob);
      const paths = Object.keys(zip.files);
      const settingsContent = await zip.file('settings.json')?.async('text');
      const settings = settingsContent ? JSON.parse(settingsContent) : null;

      return {
        byteSize: blob.size,
        paths,
        maxPathLength: Math.max(...paths.map(p => p.length)),
        longestPath: paths.reduce((a, b) => a.length >= b.length ? a : b, ''),
        settingsName: settings?.name,
        settingsNeckPitch: settings?.neckPitchDegrees,
        hasSpritesheet: paths.includes('spritesheet.png'),
        hasShadow: paths.includes('shadow.png'),
        hasCollage: paths.includes('collage.gif'),
        hasHeader: paths.includes('nds_shadow_anchor.h'),
        hasSettings: paths.includes('settings.json'),
        hasReadme: paths.includes('README.md')
      };
    });

    console.log('Character ZIP Report:', JSON.stringify(charZipReport, null, 2));
    assert(charZipReport.byteSize > 1000, 'Character ZIP blob must not be empty');
    assert.equal(charZipReport.settingsName, 'hero_skel', 'settings.name must match chosen short name "hero_skel"');
    assert.equal(charZipReport.settingsNeckPitch, -25, 'settings.neckPitchDegrees must record -25°');
    assert(charZipReport.hasSpritesheet, 'ZIP must contain spritesheet.png');
    assert(charZipReport.hasShadow, 'ZIP must contain shadow.png');
    assert(charZipReport.hasCollage, 'ZIP must contain collage.gif');
    assert(charZipReport.hasHeader, 'ZIP must contain nds_shadow_anchor.h');
    assert(charZipReport.hasSettings, 'ZIP must contain settings.json');
    assert(charZipReport.hasReadme, 'ZIP must contain README.md');

    // Strict internal path length check (< 35 characters)
    console.log(`Checking internal path lengths (longest: "${charZipReport.longestPath}", length: ${charZipReport.maxPathLength})...`);
    for (const p of charZipReport.paths) {
      assert(p.length < 35, `Internal ZIP path "${p}" exceeds 35 characters (${p.length} chars)`);
    }
    assert(charZipReport.maxPathLength < 35, `Max path length (${charZipReport.maxPathLength}) must be < 35`);
    console.log(`[PASS] Test 5: Character ZIP paths strictly < 35 chars (max was ${charZipReport.maxPathLength})`);

    // -------------------------------------------------------------
    // Test 6: Map ZIP Package Export & Internal Path Limits (< 35 chars)
    // -------------------------------------------------------------
    console.log('--- Test 6: Map ZIP Package structure & path length limits ---');
    const mapZipReport = await page.evaluate(async () => {
      const mapNameInput = document.querySelector('#exportMapName');
      mapNameInput.value = 'crypt_dungeon';

      // Ensure mock map canvas exists for export test
      if (!window.__spriteLab.mapCanvas) {
        const c = document.createElement('canvas');
        c.width = 256;
        c.height = 192;
        window.__spriteLab.mapCanvas = c;
      }

      const blob = await window.__spriteLab.exportMapPackage();
      const zip = await new window.__spriteLab.JSZip().loadAsync(blob);
      const paths = Object.keys(zip.files);
      const settingsContent = await zip.file('map_settings.json')?.async('text');
      const settings = settingsContent ? JSON.parse(settingsContent) : null;

      return {
        byteSize: blob.size,
        paths,
        maxPathLength: Math.max(...paths.map(p => p.length)),
        longestPath: paths.reduce((a, b) => a.length >= b.length ? a : b, ''),
        mapName: settings?.mapName,
        hasWorld: paths.includes('world.png'),
        hasCollisionJson: paths.includes('collision.json'),
        hasCollisionPng: paths.includes('collision.png'),
        hasOcclusionPng: paths.includes('occlusion.png'),
        hasSettings: paths.includes('map_settings.json')
      };
    });

    console.log('Map ZIP Report:', JSON.stringify(mapZipReport, null, 2));
    assert(mapZipReport.byteSize > 500, 'Map ZIP blob must not be empty');
    assert.equal(mapZipReport.mapName, 'crypt_dungeon', 'map_settings.mapName must match chosen short name "crypt_dungeon"');
    assert(mapZipReport.hasWorld, 'Map ZIP must contain world.png');
    assert(mapZipReport.hasCollisionJson, 'Map ZIP must contain collision.json');
    assert(mapZipReport.hasCollisionPng, 'Map ZIP must contain collision.png');
    assert(mapZipReport.hasOcclusionPng, 'Map ZIP must contain occlusion.png');
    assert(mapZipReport.hasSettings, 'Map ZIP must contain map_settings.json');

    // Strict internal path length check (< 35 characters)
    console.log(`Checking map internal path lengths (longest: "${mapZipReport.longestPath}", length: ${mapZipReport.maxPathLength})...`);
    for (const p of mapZipReport.paths) {
      assert(p.length < 35, `Internal map ZIP path "${p}" exceeds 35 characters (${p.length} chars)`);
    }
    assert(mapZipReport.maxPathLength < 35, `Max path length (${mapZipReport.maxPathLength}) must be < 35`);
    console.log(`[PASS] Test 6: Map ZIP paths strictly < 35 chars (max was ${mapZipReport.maxPathLength})`);

    // -------------------------------------------------------------
    // Test 7: Console errors assertion
    // -------------------------------------------------------------
    console.log('--- Test 7: Console errors audit ---');
    console.log(`Total captured errors: ${errors.length}, warnings: ${warnings.length}`);
    if (errors.length > 0) {
      console.error('Captured errors:', errors);
    }
    assert.equal(errors.length, 0, `Expected 0 console errors, but got ${errors.length}: ${errors.join('; ')}`);
    console.log('[PASS] Test 7: 0 console errors confirmed');

    console.log('\n======================================================');
    console.log(' ALL TESTS PASSED: SHORT ZIP NAMES & NECK TILT PARITY ');
    console.log('======================================================\n');
  } finally {
    await browser.close();
  }
})();
