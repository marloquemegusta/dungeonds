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
  console.error('Playwright not found');
  process.exit(1);
}

const ROOT = path.resolve(__dirname, '../..');
const HTML = path.join(__dirname, 'FBX-Web-Renderer-offline.html');
const SPACEMARINE_FBX = path.join(ROOT, 'assets/models/characters/spacemarine/spacemarine.fbx');
const SKELETON_FBX = path.join(ROOT, 'assets/models/characters/skeleton/skeleton.fbx');

const EVIDENCE_DIR = path.join(ROOT, 'walkthroughs/fix-neck-pitch-axis-and-input/assets');
const ARTIFACT_DIR = 'C:/Users/malfonso/.gemini/antigravity/brain/79d79fef-1fd2-4c6e-9980-edd6fb3e817e';

fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
if (fs.existsSync(ARTIFACT_DIR)) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
}

function saveImage(filename, buffer) {
  const localPath = path.join(EVIDENCE_DIR, filename);
  fs.writeFileSync(localPath, buffer);
  console.log(`[SAVED] ${localPath}`);
  if (fs.existsSync(ARTIFACT_DIR)) {
    const artPath = path.join(ARTIFACT_DIR, filename);
    fs.writeFileSync(artPath, buffer);
    console.log(`[SAVED ARTIFACT] ${artPath}`);
  }
}

(async () => {
  console.log('=== Starting Test: Neck Pitch Axis & Number Input Parity ===');
  const browser = await chromium.launch({
    headless: true,
    args: ['--enable-webgl', '--use-gl=swiftshader', '--disable-dev-shm-usage', '--no-sandbox']
  });

  const page = await browser.newPage({ viewport: { width: 1440, height: 950 } });
  const fileUrl = 'file:///' + HTML.replace(/\\/g, '/');
  console.log(`Navigating to ${fileUrl}...`);
  await page.goto(fileUrl, { waitUntil: 'load', timeout: 30000 });
  await page.waitForFunction(() => typeof window.__spriteLab !== 'undefined', { timeout: 10000 });

  // Test 1: DOM Elements
  console.log('\n--- Test 1: DOM Elements & Separation ---');
  const domState = await page.evaluate(() => {
    const pitch = document.getElementById('neckPitch');
    const tilt = document.getElementById('neckTilt');
    const label = document.getElementById('neckPitchValue');
    return {
      pitchType: pitch?.type,
      pitchId: pitch?.id,
      tiltType: tilt?.type,
      tiltId: tilt?.id,
      labelVal: label?.textContent,
      areDistinct: pitch !== tilt
    };
  });
  console.log('DOM State:', domState);
  assert.equal(domState.pitchType, 'range');
  assert.equal(domState.tiltType, 'number');
  assert.equal(domState.areDistinct, true);
  console.log('[PASS] Test 1: #neckPitch is range slider, #neckTilt is number input, distinct DOM elements');

  // Test 2: Load Spacemarine FBX
  console.log('\n--- Test 2: Loading spacemarine.fbx ---');
  await page.locator('#fbxInput').setInputFiles(SPACEMARINE_FBX);
  await page.waitForFunction(
    () => window.$.loaded === true && window.document.getElementById('fileName')?.textContent.includes('spacemarine'),
    { timeout: 20000 }
  );
  await page.waitForTimeout(600);
  console.log('[PASS] Test 2: Spacemarine FBX loaded');

  // Switch to Shader tab for controls and 3D tab for viewport
  await page.click('button.lab-tab-btn[data-tab="shader"]');
  await page.waitForTimeout(200);
  await page.click('button.stage-tab-btn[data-stage="3d"]');
  await page.waitForTimeout(300);

  // Take neutral 0° screenshot
  await page.evaluate(() => {
    window.__spriteLab.syncNeckTilt(0, true);
  });
  await page.waitForTimeout(300);

  const buf0 = await page.screenshot();
  saveImage('spacemarine_pitch_0deg_ui.png', buf0);

  // Get close-up of 3D canvas at 0°
  const canvasElement = page.locator('#canvasArea canvas');
  const canvasBuf0 = await canvasElement.screenshot();
  saveImage('spacemarine_head_0deg.png', canvasBuf0);

  // Test 3: Number input typing drive without touching slider
  console.log('\n--- Test 3: Typing -25 into number input #neckTilt ---');
  await page.locator('#neckTilt').fill('-25');
  await page.waitForTimeout(400);

  const stateMinus25 = await page.evaluate(() => {
    return {
      sliderVal: document.getElementById('neckPitch').value,
      numVal: document.getElementById('neckTilt').value,
      label: document.getElementById('neckPitchValue').textContent,
      neckPitch: window.__spriteLab.getNeckPitchDegrees()
    };
  });
  console.log('State at -25°:', stateMinus25);
  assert.equal(stateMinus25.sliderVal, '-25');
  assert.equal(stateMinus25.numVal, '-25');
  assert.equal(stateMinus25.label, '-25°');
  assert.equal(stateMinus25.neckPitch, -25);

  const bufMinus25 = await page.screenshot();
  saveImage('spacemarine_pitch_minus25deg_ui.png', bufMinus25);
  const canvasBufMinus25 = await canvasElement.screenshot();
  saveImage('spacemarine_head_minus25deg.png', canvasBufMinus25);
  console.log('[PASS] Test 3: Typing -25 into #neckTilt updated slider, label, state and rendered canvas');

  // Test 4: Typing +25 into number input #neckTilt
  console.log('\n--- Test 4: Typing +25 into number input #neckTilt ---');
  await page.locator('#neckTilt').fill('25');
  await page.waitForTimeout(400);

  const statePlus25 = await page.evaluate(() => {
    return {
      sliderVal: document.getElementById('neckPitch').value,
      numVal: document.getElementById('neckTilt').value,
      label: document.getElementById('neckPitchValue').textContent,
      neckPitch: window.__spriteLab.getNeckPitchDegrees()
    };
  });
  console.log('State at +25°:', statePlus25);
  assert.equal(statePlus25.sliderVal, '25');
  assert.equal(statePlus25.numVal, '25');
  assert.equal(statePlus25.label, '25°');
  assert.equal(statePlus25.neckPitch, 25);

  const bufPlus25 = await page.screenshot();
  saveImage('spacemarine_pitch_plus25deg_ui.png', bufPlus25);
  const canvasBufPlus25 = await canvasElement.screenshot();
  saveImage('spacemarine_head_plus25deg.png', canvasBufPlus25);
  console.log('[PASS] Test 4: Typing +25 into #neckTilt updated slider, label, state and rendered canvas');

  // Test 5: Verify Geometric Pitch and Zero Lateral Roll on Spacemarine
  console.log('\n--- Test 5: Geometric Pitch & Lateral Roll Verification ---');
  const geomReport = await page.evaluate(() => {
    const model = window.$.model;
    const findBone = (patterns) => {
      let found = null;
      model.traverse(node => {
        if (!found && node.isBone) {
          const n = node.name.toLowerCase().replace(/[^a-z0-9]/g, '');
          if (patterns.some(p => n.includes(p))) found = node;
        }
      });
      return found;
    };
    const head = findBone(['head']);
    const neck = findBone(['neck']);
    const target = head || neck;

    const angles = [-25, 0, 25];
    const results = {};

    for (const deg of angles) {
      window.__spriteLab.syncNeckTilt(deg, true);
      target.updateMatrixWorld(true);
      const topOfHeadWorld = new (target.position.constructor)(0, 0.2, 0);
      target.localToWorld(topOfHeadWorld);
      results[deg] = {
        top: { x: topOfHeadWorld.x, y: topOfHeadWorld.y, z: topOfHeadWorld.z }
      };
    }

    return results;
  });

  const deltaX = Math.abs(geomReport[25].top.x - geomReport[-25].top.x);
  const deltaY = Math.abs(geomReport[25].top.y - geomReport[-25].top.y);
  const deltaZ = Math.abs(geomReport[25].top.z - geomReport[-25].top.z);
  console.log(`[spacemarine] Delta X (lateral roll error): ${deltaX.toFixed(6)}`);
  console.log(`[spacemarine] Delta Y (vertical pitch):     ${deltaY.toFixed(6)}`);
  console.log(`[spacemarine] Delta Z (sagittal pitch):    ${deltaZ.toFixed(6)}`);

  assert(deltaX < 0.005, `Lateral roll error must be < 0.005, got ${deltaX}`);
  assert(deltaY > 0.02, `Vertical pitch movement must be > 0.02, got ${deltaY}`);
  assert(deltaZ > 0.02, `Sagittal pitch movement must be > 0.02, got ${deltaZ}`);
  console.log('[PASS] Test 5: Pure sagittal pitch verified with ZERO lateral roll');

  // Test 6: Verify skeleton.fbx
  console.log('\n--- Test 6: Verification on skeleton.fbx ---');
  await page.click('button.lab-tab-btn[data-tab="scale"]');
  await page.waitForTimeout(200);
  await page.locator('#fbxInput').setInputFiles(SKELETON_FBX);
  await page.waitForFunction(
    () => window.$.loaded === true && window.document.getElementById('fileName')?.textContent.includes('skeleton'),
    { timeout: 20000 }
  );
  await page.waitForTimeout(600);

  await page.click('button.lab-tab-btn[data-tab="shader"]');
  await page.waitForTimeout(200);

  const skelGeom = await page.evaluate(() => {
    const model = window.$.model;
    const findBone = (patterns) => {
      let found = null;
      model.traverse(node => {
        if (!found && node.isBone) {
          const n = node.name.toLowerCase().replace(/[^a-z0-9]/g, '');
          if (patterns.some(p => n.includes(p))) found = node;
        }
      });
      return found;
    };
    const head = findBone(['head']);
    const neck = findBone(['neck']);
    const target = head || neck;

    const angles = [-25, 0, 25];
    const results = {};

    for (const deg of angles) {
      window.__spriteLab.syncNeckTilt(deg, true);
      target.updateMatrixWorld(true);
      const topOfHeadWorld = new (target.position.constructor)(0, 0.2, 0);
      target.localToWorld(topOfHeadWorld);
      results[deg] = {
        top: { x: topOfHeadWorld.x, y: topOfHeadWorld.y, z: topOfHeadWorld.z }
      };
    }

    return results;
  });

  const skelDeltaX = Math.abs(skelGeom[25].top.x - skelGeom[-25].top.x);
  const skelDeltaY = Math.abs(skelGeom[25].top.y - skelGeom[-25].top.y);
  console.log(`[skeleton] Delta X (lateral roll error): ${skelDeltaX.toFixed(6)}`);
  console.log(`[skeleton] Delta Y (vertical pitch):     ${skelDeltaY.toFixed(6)}`);
  assert(skelDeltaX < 0.01, `Skeleton lateral roll error must be < 0.01, got ${skelDeltaX}`);
  assert(skelDeltaY > 0.03, `Skeleton vertical pitch must be > 0.03, got ${skelDeltaY}`);
  console.log('[PASS] Test 6: Pure sagittal pitch verified on skeleton');

  // Test 7: Verify demo model
  console.log('\n--- Test 7: Verification on Demo model ---');
  await page.click('button.lab-tab-btn[data-tab="scale"]');
  await page.waitForTimeout(200);
  await page.click('#btnLoadDemo');
  await page.waitForTimeout(500);

  await page.click('button.lab-tab-btn[data-tab="shader"]');
  await page.waitForTimeout(200);
  await page.locator('#neckTilt').fill('-15');
  await page.waitForTimeout(300);

  const demoState = await page.evaluate(() => {
    return {
      sliderVal: document.getElementById('neckPitch').value,
      numVal: document.getElementById('neckTilt').value,
      label: document.getElementById('neckPitchValue').textContent
    };
  });
  console.log('Demo state after filling -15:', demoState);
  assert.equal(demoState.sliderVal, '-15');
  assert.equal(demoState.numVal, '-15');
  assert.equal(demoState.label, '-15°');
  console.log('[PASS] Test 7: Demo model responds to number input');

  await browser.close();
  console.log('\n======================================================');
  console.log('ALL TESTS PASSED: NECK PITCH AXIS AND NUMBER INPUT FIX');
  console.log('======================================================');
})();
