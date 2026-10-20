// Headless Playwright test for Auto AnimTicks and Character ZIP Export Button Parity
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
const EVIDENCE_DIR = path.join(ROOT, 'walkthroughs/fix-lab-autoticks-and-zip-btn/assets');
const ARTIFACT_DIR = 'C:/Users/malfonso/.gemini/antigravity/brain/7288fbac-294b-48c0-b805-e2790ea21fee';

assert(fs.existsSync(HTML), `HTML file does not exist: ${HTML}`);
fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
if (fs.existsSync(ARTIFACT_DIR)) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
}

(async () => {
  console.log('--- Starting Headless AutoAnimTicks & Zip Button Test ---');
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
        console.error('Captured Console error:', text);
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

    // -------------------------------------------------------------
    // Test 1: Verify elements exist and IDs match expectations
    // -------------------------------------------------------------
    const initialElements = await page.evaluate(() => {
      const renderBtn = document.querySelector('#renderBtn');
      const zipBtn = document.querySelector('#downloadPackageBtn');
      const animTicks = document.querySelector('#animTicks');
      const hint = document.querySelector('#strideMetricsHint');
      return {
        hasRenderBtn: !!renderBtn,
        hasZipBtn: !!zipBtn,
        zipBtnVisible: zipBtn && zipBtn.offsetParent !== null && !zipBtn.hidden && zipBtn.style.display !== 'none',
        hasAnimTicks: !!animTicks,
        hasHint: !!hint,
        initialTicks: animTicks ? animTicks.value : null
      };
    });

    console.log('Initial Elements State:', JSON.stringify(initialElements));
    assert(initialElements.hasRenderBtn, '#renderBtn must exist');
    assert(initialElements.hasZipBtn, '#downloadPackageBtn must exist');
    assert(initialElements.zipBtnVisible, '#downloadPackageBtn must be visible initially');
    assert(initialElements.hasAnimTicks, '#animTicks must exist');
    assert(initialElements.hasHint, '#strideMetricsHint must exist');
    console.log('[PASS] DOM Elements and initial visibility verified');

    // -------------------------------------------------------------
    // Test 2: Auto AnimTicks Calculation with Demo Model
    // -------------------------------------------------------------
    console.log('Loading demo model...');
    await page.click('#btnLoadDemo');
    await page.waitForTimeout(500);

    const demoAnimState = await page.evaluate(() => {
      const lab = window.__spriteLab;
      const animTicks = document.getElementById('animTicks');
      const hint = document.getElementById('strideMetricsHint');
      const frameCount = lab.getExportFrameCount();
      const clip = window.$?.clips?.[0];
      const duration = clip ? clip.duration : 0;
      return {
        clipDuration: duration,
        frameCount,
        autoAnimTicks: lab.autoAnimTicks,
        inputTicks: animTicks.value,
        userEdited: animTicks.dataset.userEdited,
        hintText: hint ? hint.textContent : ''
      };
    });

    console.log('Demo Model AnimTicks State:', JSON.stringify(demoAnimState));
    // Demo walk has duration = 1.0s. At frameCount = 8: Math.round(1.0 * 60 / 8) = 8.
    assert.equal(demoAnimState.clipDuration, 1.0, 'Demo walk clip duration must be 1.0s');
    assert.equal(demoAnimState.autoAnimTicks, 8, 'autoAnimTicks must be 8 for 1.0s @ 8 frames');
    assert.equal(demoAnimState.inputTicks, '8', '#animTicks input must be set to 8');
    assert(demoAnimState.hintText.includes('8t/f @60Hz'), `Hint text must show 8t/f: got "${demoAnimState.hintText}"`);
    console.log('[PASS] Auto AnimTicks verified on demo model (1.0s -> 8 ticks)');

    // Test changing frameCount slider to 16
    console.log('Testing frameCount slider change to 16...');
    await page.evaluate(() => {
      const frameCountSlider = document.getElementById('frameCount');
      frameCountSlider.value = '16';
      frameCountSlider.dispatchEvent(new Event('input', { bubbles: true }));
      frameCountSlider.dispatchEvent(new Event('change', { bubbles: true }));
    });

    const frameCount16State = await page.evaluate(() => {
      const lab = window.__spriteLab;
      const animTicks = document.getElementById('animTicks');
      return {
        frameCount: lab.getExportFrameCount(),
        autoAnimTicks: lab.autoAnimTicks,
        inputTicks: animTicks.value
      };
    });

    console.log('FrameCount 16 State:', JSON.stringify(frameCount16State));
    // 1.0s * 60 / 16 = 3.75 -> Math.round = 4
    assert.equal(frameCount16State.frameCount, 16, 'frameCount must be 16');
    assert.equal(frameCount16State.autoAnimTicks, 4, 'autoAnimTicks must be 4 for 1.0s @ 16 frames');
    assert.equal(frameCount16State.inputTicks, '4', '#animTicks input must be 4');
    console.log('[PASS] Slider reactivity verified (16 frames -> 4 ticks)');

    // Test custom clip durations (0.40s and 0.80s)
    console.log('Testing clip duration 0.40s and 0.80s at 8 frames...');
    await page.evaluate(() => {
      const frameCountSlider = document.getElementById('frameCount');
      frameCountSlider.value = '8';
      frameCountSlider.dispatchEvent(new Event('input', { bubbles: true }));
      frameCountSlider.dispatchEvent(new Event('change', { bubbles: true }));
    });

    const customClipsState = await page.evaluate(() => {
      const lab = window.__spriteLab;
      const animTicks = document.getElementById('animTicks');
      const clip = window.$?.clips?.[0];

      // 0.40s: 0.40 * 60 / 8 = 3.0 -> 3 ticks
      clip.duration = 0.40;
      lab.updateCharacterStrideMetrics();
      const state040 = {
        autoAnimTicks: lab.autoAnimTicks,
        inputTicks: animTicks.value
      };

      // 0.80s: 0.80 * 60 / 8 = 6.0 -> 6 ticks
      clip.duration = 0.80;
      lab.updateCharacterStrideMetrics();
      const state080 = {
        autoAnimTicks: lab.autoAnimTicks,
        inputTicks: animTicks.value
      };

      // Reset to 0.40s
      clip.duration = 0.40;
      lab.updateCharacterStrideMetrics();

      return { state040, state080 };
    });

    console.log('Custom Clips State:', JSON.stringify(customClipsState));
    assert.equal(customClipsState.state040.autoAnimTicks, 3, '0.40s @ 8 frames -> 3 ticks');
    assert.equal(customClipsState.state040.inputTicks, '3', '#animTicks must be 3');
    assert.equal(customClipsState.state080.autoAnimTicks, 6, '0.80s @ 8 frames -> 6 ticks');
    assert.equal(customClipsState.state080.inputTicks, '6', '#animTicks must be 6');
    console.log('[PASS] Custom clip durations (0.40s -> 3t, 0.80s -> 6t) verified');

    // Test user edit override (`dataset.userEdited`)
    console.log('Testing user override on #animTicks...');
    await page.evaluate(() => {
      const animTicks = document.getElementById('animTicks');
      animTicks.value = '12';
      animTicks.dispatchEvent(new Event('input', { bubbles: true }));
      animTicks.dispatchEvent(new Event('change', { bubbles: true }));
    });

    const userEditedState = await page.evaluate(() => {
      const animTicks = document.getElementById('animTicks');
      const hint = document.getElementById('strideMetricsHint');
      const lab = window.__spriteLab;
      // Trigger updateCharacterStrideMetrics with userEdited flag active
      lab.updateCharacterStrideMetrics();
      return {
        userEdited: animTicks.dataset.userEdited,
        inputTicks: animTicks.value,
        autoAnimTicks: lab.autoAnimTicks,
        hintText: hint ? hint.textContent : ''
      };
    });

    console.log('User Edited State:', JSON.stringify(userEditedState));
    assert.equal(userEditedState.userEdited, 'true', 'dataset.userEdited must be "true"');
    assert.equal(userEditedState.inputTicks, '12', '#animTicks must keep user value 12');
    assert.equal(userEditedState.autoAnimTicks, 3, 'autoAnimTicks remains 3');
    assert(userEditedState.hintText.includes('12t/f @60Hz'), 'Hint text must show overridden 12t/f');
    console.log('[PASS] User override preserved during metric updates');

    // Test clearing input resets userEdited
    console.log('Testing clearing #animTicks reverts to auto...');
    await page.evaluate(() => {
      const animTicks = document.getElementById('animTicks');
      animTicks.value = '';
      animTicks.dispatchEvent(new Event('input', { bubbles: true }));
      animTicks.dispatchEvent(new Event('change', { bubbles: true }));
    });

    const clearedState = await page.evaluate(() => {
      const animTicks = document.getElementById('animTicks');
      return {
        userEdited: animTicks.dataset.userEdited,
        inputTicks: animTicks.value
      };
    });

    console.log('Cleared Input State:', JSON.stringify(clearedState));
    assert(!clearedState.userEdited, 'userEdited flag must be removed when cleared');
    assert.equal(clearedState.inputTicks, '3', '#animTicks must revert to auto ticks 3');
    console.log('[PASS] Clearing input successfully reverts to auto ticks');

    // -------------------------------------------------------------
    // Test 3: Screenshots and Button Visibility Before & After Render
    // -------------------------------------------------------------
    const shotBefore = path.join(EVIDENCE_DIR, 'lab_before_render.png');
    const shotBeforeArtifact = path.join(ARTIFACT_DIR, 'lab_before_render.png');
    await page.screenshot({ path: shotBefore });
    if (fs.existsSync(ARTIFACT_DIR)) {
      fs.copyFileSync(shotBefore, shotBeforeArtifact);
    }
    console.log(`[SAVED] Screenshot before render: ${shotBefore}`);

    // Verify #downloadPackageBtn before render
    const btnBeforeRender = await page.evaluate(() => {
      const btn = document.querySelector('#downloadPackageBtn');
      return {
        exists: !!btn,
        offsetParent: btn ? btn.offsetParent !== null : false,
        hidden: btn ? btn.hidden : true,
        display: btn ? window.getComputedStyle(btn).display : 'none'
      };
    });
    assert(btnBeforeRender.exists, '#downloadPackageBtn must exist before render');
    assert(btnBeforeRender.offsetParent, '#downloadPackageBtn must be visible in layout before render');
    assert(!btnBeforeRender.hidden, '#downloadPackageBtn hidden property must be false');
    assert.notEqual(btnBeforeRender.display, 'none', '#downloadPackageBtn display must not be none');
    console.log('[PASS] #downloadPackageBtn is visible before render');

    // Click Red Render Button (#renderBtn)
    console.log('Clicking #renderBtn to render all 8 directions...');
    await page.click('#renderBtn');

    // Wait for render to complete (results populated and progress done)
    await page.waitForFunction(() => {
      const lab = window.__spriteLab;
      return window.$ && window.$.loaded && !window.$.rendering && lab.frames && lab.frames.length >= 64;
    }, { timeout: 30000 });
    console.log('[OK] 8 directions rendering completed successfully');

    // Wait brief delay for DOM callbacks to finish
    await page.waitForTimeout(300);

    const shotAfter = path.join(EVIDENCE_DIR, 'lab_after_render.png');
    const shotAfterArtifact = path.join(ARTIFACT_DIR, 'lab_after_render.png');
    await page.screenshot({ path: shotAfter });
    if (fs.existsSync(ARTIFACT_DIR)) {
      fs.copyFileSync(shotAfter, shotAfterArtifact);
    }
    console.log(`[SAVED] Screenshot after render: ${shotAfter}`);

    // Verify #downloadPackageBtn AFTER render
    const btnAfterRender = await page.evaluate(() => {
      const btn = document.querySelector('#downloadPackageBtn');
      return {
        exists: !!btn,
        offsetParent: btn ? btn.offsetParent !== null : false,
        hidden: btn ? btn.hidden : true,
        disabled: btn ? btn.disabled : true,
        display: btn ? window.getComputedStyle(btn).display : 'none',
        textContent: btn ? btn.textContent.trim() : ''
      };
    });

    console.log('Button State After Render:', JSON.stringify(btnAfterRender));
    assert(btnAfterRender.exists, '#downloadPackageBtn must exist after render');
    assert(btnAfterRender.offsetParent, '#downloadPackageBtn MUST be visible in layout (offsetParent !== null) after render');
    assert.equal(btnAfterRender.hidden, false, '#downloadPackageBtn hidden MUST be false after render');
    assert.equal(btnAfterRender.disabled, false, '#downloadPackageBtn disabled MUST be false after render');
    assert.notEqual(btnAfterRender.display, 'none', '#downloadPackageBtn display MUST NOT be none after render');
    console.log('[PASS] #downloadPackageBtn remains fully visible and enabled after render');

    // -------------------------------------------------------------
    // Test 4: Verify Character Package ZIP Generation & Settings
    // -------------------------------------------------------------
    console.log('Testing Character Package ZIP generation...');
    const zipMetrics = await page.evaluate(async () => {
      const lab = window.__spriteLab;
      const zipBlob = await lab.exportPackage();
      const zip = await new Nf.default().loadAsync(zipBlob);
      const files = Object.keys(zip.files);
      const settingsContent = await zip.file(files.find(f => f.endsWith('settings.json'))).async('string');
      const settings = JSON.parse(settingsContent);
      return {
        blobSize: zipBlob.size,
        fileCount: files.length,
        hasSpritesheet: files.some(f => f.endsWith('_spritesheet.png')),
        hasShadowAtlas: files.some(f => f.endsWith('_shadow.png')),
        hasHeader: files.some(f => f.endsWith('_nds_shadow_anchor.h')),
        ticksPerFrame: settings.ticksPerFrame,
        speedFixed8_8: settings.speedFixed8_8,
        stride3dMeters: settings.stride3dMeters
      };
    });

    console.log('Character Package ZIP Metrics:', JSON.stringify(zipMetrics, null, 2));
    assert(zipMetrics.blobSize > 0, 'ZIP blob size must be > 0');
    assert(zipMetrics.hasSpritesheet, 'ZIP must include spritesheet');
    assert(zipMetrics.hasShadowAtlas, 'ZIP must include shadow atlas');
    assert(zipMetrics.hasHeader, 'ZIP must include NDS header');
    assert.equal(zipMetrics.ticksPerFrame, 3, 'settings.json ticksPerFrame must match calculated ticks');
    assert(zipMetrics.speedFixed8_8 > 0, 'settings.json speedFixed8_8 must be > 0');
    console.log('[PASS] Character Package ZIP generation and settings verified');

    // -------------------------------------------------------------
    // Test 5: Verify 0 Console Errors
    // -------------------------------------------------------------
    console.log('Total console errors caught:', errors.length);
    if (errors.length > 0) {
      console.error('Console errors:', errors);
    }
    assert.equal(errors.length, 0, 'There must be 0 console errors');
    console.log('[PASS] 0 console errors verified');

  } finally {
    await browser.close();
  }

  console.log('--- ALL TEST ASSERTIONS PASSED (0 fatal errors) ---');
})();
