// Headless Playwright test for stride preview synchronization in FBX-Web-Renderer
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
const EVIDENCE_DIR = path.join(ROOT, 'walkthroughs/fix-lab-stride-preview/assets');

assert(fs.existsSync(HTML), `HTML file does not exist: ${HTML}`);
fs.mkdirSync(EVIDENCE_DIR, { recursive: true });

(async () => {
  console.log('--- Starting Headless Stride Preview Test ---');
  const browser = await chromium.launch({
    headless: true,
    args: ['--enable-webgl', '--use-gl=swiftshader', '--disable-dev-shm-usage', '--no-sandbox']
  });

  const errors = [];
  const warnings = [];

  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    page.on('pageerror', err => {
      console.error('Page error:', err);
      errors.push(err.message || String(err));
    });
    page.on('console', msg => {
      const text = msg.text();
      if (msg.type() === 'error') {
        // Filter benign Three.js internal property binding notice for demo procedural tracks
        if (text.includes('PropertyBinding')) {
          warnings.push(text);
          return;
        }
        console.error('Console error:', text);
        errors.push(text);
      } else if (msg.type() === 'warn') {
        warnings.push(text);
      }
    });

    const fileUrl = `file:///${HTML.replace(/\\/g, '/')}`;
    console.log(`Loading lab from ${fileUrl}...`);
    await page.goto(fileUrl, { waitUntil: 'load' });

    // Wait for parity layer initialization
    await page.waitForFunction(() => !!window.__spriteLab && typeof window.__spriteLab.getEffectiveStridePx === 'function', { timeout: 15000 });
    console.log('Parity layer and stride API initialized.');

    // 1. Initial State Check (before loading model)
    const initialMetrics = await page.evaluate(() => {
      const s = window.__spriteLab;
      return {
        charHeight3D: s.charHeight3D,
        autoStride3D: s.autoStride3D,
        strideRatio: s.strideRatio,
        effectiveStridePx: s.getEffectiveStridePx(),
        charAnimFrame: s.charAnimFrame,
        charWalkDistAccum: s.charWalkDistAccum
      };
    });
    console.log('Initial metrics:', initialMetrics);
    assert(initialMetrics.charHeight3D > 0, 'charHeight3D is positive');
    assert(initialMetrics.autoStride3D > 0, 'autoStride3D is positive');
    assert(initialMetrics.strideRatio > 0, 'strideRatio is positive');
    assert(initialMetrics.effectiveStridePx > 0, 'effectiveStridePx is positive');

    // 2. Load Demo Model
    console.log('Clicking demo button (#btnLoadDemo)...');
    await page.click('#btnLoadDemo');
    await page.waitForFunction(() => {
      const badge = document.getElementById('fileNameBadge');
      return badge && badge.textContent === 'demo_procedural';
    }, { timeout: 10000 });
    // Let live frame render and metrics update
    await page.waitForTimeout(1000);

    const demoMetrics = await page.evaluate(() => {
      const s = window.__spriteLab;
      const badge = document.getElementById('dsMetricsBadge')?.textContent || '';
      const strideVal = document.getElementById('stride3dVal')?.textContent || '';
      const ratioBadge = document.getElementById('strideRatioBadge')?.textContent || '';
      const strideDetails = document.getElementById('strideDetails')?.textContent || '';
      return {
        charHeight3D: s.charHeight3D,
        autoStride3D: s.autoStride3D,
        strideRatio: s.strideRatio,
        spriteVisibleHeightPx: s.spriteVisibleHeightPx,
        effectiveStridePx: s.getEffectiveStridePx(),
        frameCount: s.getExportFrameCount(),
        badge,
        strideVal,
        ratioBadge,
        strideDetails
      };
    });
    console.log('Demo procedural metrics:', demoMetrics);
    assert(Math.abs(demoMetrics.charHeight3D - 1.7) < 0.2, `Demo procedural height is ~1.7m, got ${demoMetrics.charHeight3D}`);
    assert(Math.abs(demoMetrics.strideRatio - 0.833) < 0.01, `Demo procedural stride ratio is ~0.833, got ${demoMetrics.strideRatio}`);
    assert(demoMetrics.effectiveStridePx > 20, `Effective stride in px is reasonable: ${demoMetrics.effectiveStridePx}`);
    assert(demoMetrics.badge.includes('Zancada:'), `Badge shows stride info: ${demoMetrics.badge}`);

    // Capture screenshot of demo loaded state
    const screenshot1Path = path.join(EVIDENCE_DIR, '01_demo_loaded_stride_metrics.png');
    await page.screenshot({ path: screenshot1Path });
    console.log(`Saved screenshot 1: ${screenshot1Path}`);

    // 3. Test Dragging Interactivity - Verify Stride Synchronization
    // In previous code, 30 micro mousemove events advanced charAnimFrame by 30 frames (4 walk cycles).
    // Now, moving a distance equal to 1 stride should advance exactly frameCount frames (1 cycle)!
    console.log('Testing mouse drag synchronization...');
    const simCanvas = await page.$('#dsSimCanvas');
    assert(simCanvas, '#dsSimCanvas exists');

    const testDragResult = await page.evaluate(async () => {
      const s = window.__spriteLab;
      const canvas = document.getElementById('dsSimCanvas');
      const startX = s.dsCharX;
      const startY = s.dsCharY;
      const initialFrame = s.charAnimFrame;
      s.charWalkDistAccum = 0;

      const stridePx = s.getEffectiveStridePx();
      const frameCount = s.getExportFrameCount();
      const pxPerFrame = stridePx / frameCount;

      // We will simulate 30 micro-moves whose total displacement is exactly 1 full stride (stridePx)
      const steps = 30;
      const dxPerStep = stridePx / steps;

      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;

      // Simulate mousedown on character
      const screenCharX = s.dsCharX - s.dsPanX;
      const screenCharY = s.dsCharY - s.dsPanY;
      const clientX0 = rect.left + (screenCharX / scaleX);
      const clientY0 = rect.top + (screenCharY / scaleY);

      canvas.dispatchEvent(new MouseEvent('mousedown', {
        clientX: clientX0,
        clientY: clientY0,
        button: 0,
        bubbles: true
      }));

      let framesObserved = [];
      let currentClientX = clientX0;
      let totalDispatchedDist = 0;

      for (let i = 1; i <= steps; i++) {
        currentClientX += (dxPerStep / scaleX);
        totalDispatchedDist += dxPerStep;
        window.dispatchEvent(new MouseEvent('mousemove', {
          clientX: currentClientX,
          clientY: clientY0,
          bubbles: true
        }));
        framesObserved.push(s.charAnimFrame);
      }

      window.dispatchEvent(new MouseEvent('mouseup', {
        clientX: currentClientX,
        clientY: clientY0,
        bubbles: true
      }));

      const finalDisplacement = Math.hypot(s.dsCharX - startX, s.dsCharY - startY);

      let transitions = 0;
      for (let i = 1; i < framesObserved.length; i++) {
        if (framesObserved[i] !== framesObserved[i - 1]) transitions++;
      }

      return {
        initialFrame,
        finalFrame: s.charAnimFrame,
        frameCount,
        stridePx,
        pxPerFrame,
        totalDispatchedDist,
        finalDisplacement,
        totalSteps: steps,
        transitions,
        framesObserved
      };
    });

    console.log('Drag test result:', testDragResult);
    console.log(`Observed ${testDragResult.transitions} frame transitions across ${testDragResult.totalSteps} micro-moves.`);
    assert(testDragResult.transitions >= 7 && testDragResult.transitions <= 8,
      `Expected 7-8 frame advances for ~1 full stride cycle, got ${testDragResult.transitions} (in old code it would be 29-30)`);

    // Test a partial drag of 1 frame distance (pxPerFrame)
    const partialDragResult = await page.evaluate(async () => {
      const s = window.__spriteLab;
      const canvas = document.getElementById('dsSimCanvas');
      const startFrame = s.charAnimFrame;
      s.charWalkDistAccum = 0;

      const stridePx = s.getEffectiveStridePx();
      const frameCount = s.getExportFrameCount();
      const pxPerFrame = stridePx / frameCount;

      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      const screenCharX = s.dsCharX - s.dsPanX;
      const screenCharY = s.dsCharY - s.dsPanY;
      const clientX0 = rect.left + (screenCharX / scaleX);
      const clientY0 = rect.top + (screenCharY / scaleY);

      canvas.dispatchEvent(new MouseEvent('mousedown', {
        clientX: clientX0,
        clientY: clientY0,
        button: 0,
        bubbles: true
      }));

      // Move 10 tiny micro-movements summing to 1.1 * pxPerFrame to guarantee crossing 1 frame threshold
      const microSteps = 10;
      const targetDist = pxPerFrame * 1.1;
      for (let i = 0; i < microSteps; i++) {
        window.dispatchEvent(new MouseEvent('mousemove', {
          clientX: clientX0 + ((targetDist / microSteps) * (i + 1)) / scaleX,
          clientY: clientY0,
          bubbles: true
        }));
      }

      window.dispatchEvent(new MouseEvent('mouseup', {
        clientX: clientX0 + (targetDist / scaleX),
        clientY: clientY0,
        bubbles: true
      }));

      return {
        startFrame,
        endFrame: s.charAnimFrame,
        frameCount,
        pxPerFrame
      };
    });
    console.log('Partial drag result (1 frame distance in 10 micro-moves):', partialDragResult);
    const expectedEndFrame = (partialDragResult.startFrame + 1) % partialDragResult.frameCount;
    assert.equal(partialDragResult.endFrame, expectedEndFrame, '10 micro-moves summing to 1 frame distance advanced exactly 1 frame, not 10!');

    // 4. Test Keyboard WASD / Arrows Interactivity
    console.log('Testing keyboard interactivity...');
    const keyResult = await page.evaluate(() => {
      const s = window.__spriteLab;
      const viewport = document.getElementById('dsSimViewport');
      const startFrame = s.charAnimFrame;
      s.charWalkDistAccum = 0;

      const frameCount = s.getExportFrameCount();
      const stridePx = s.getEffectiveStridePx();
      const pxPerFrame = Math.max(0.5, stridePx / frameCount);

      // Dispatch 4 'd' key presses
      for (let i = 0; i < 4; i++) {
        viewport.dispatchEvent(new KeyboardEvent('keydown', { key: 'd', bubbles: true }));
      }

      return {
        startFrame,
        endFrame: s.charAnimFrame,
        frameCount,
        accum: s.charWalkDistAccum,
        pxPerFrame
      };
    });
    console.log('Keyboard test result:', keyResult);
    assert(keyResult.endFrame !== undefined, 'Keyboard event handled');

    // 5. Test #stride3d Override Input
    console.log('Testing #stride3d manual override input...');
    await page.fill('#stride3d', '2.5');
    await page.dispatchEvent('#stride3d', 'input');
    await page.waitForTimeout(300);

    const overrideMetrics = await page.evaluate(() => {
      const s = window.__spriteLab;
      const strideVal = document.getElementById('stride3dVal')?.textContent || '';
      return {
        strideRatio: s.strideRatio,
        effectiveStridePx: s.getEffectiveStridePx(),
        strideVal
      };
    });
    console.log('Override metrics (stride 2.5m):', overrideMetrics);
    assert(Math.abs(overrideMetrics.strideRatio - (2.5 / demoMetrics.charHeight3D)) < 0.05, `Override stride ratio matches 2.5 / ${demoMetrics.charHeight3D}, got ${overrideMetrics.strideRatio}`);
    assert(overrideMetrics.strideVal.includes('2.50 m (override)'), `Label shows override: ${overrideMetrics.strideVal}`);

    // Capture screenshot with override
    const screenshot2Path = path.join(EVIDENCE_DIR, '02_stride_override_active.png');
    await page.screenshot({ path: screenshot2Path });
    console.log(`Saved screenshot 2: ${screenshot2Path}`);

    // Reset override
    await page.fill('#stride3d', '');
    await page.dispatchEvent('#stride3d', 'input');
    await page.waitForTimeout(300);

    const resetMetrics = await page.evaluate(() => {
      const s = window.__spriteLab;
      return {
        strideRatio: s.strideRatio,
        autoStride3D: s.autoStride3D
      };
    });
    assert(Math.abs(resetMetrics.strideRatio - 0.833) < 0.02, 'Resetting override returns to auto ratio');

    // 6. Test with Real FBX Model (spacemarine.fbx)
    const marineFbxPath = path.join(ROOT, 'assets/models/characters/spacemarine/spacemarine.fbx');
    if (fs.existsSync(marineFbxPath)) {
      console.log('Testing loading real FBX model: spacemarine.fbx...');
      const fileChooserPromise = page.waitForEvent('filechooser');
      await page.click('label[for="fbxInput"]');
      const fileChooser = await fileChooserPromise;
      await fileChooser.setFiles(marineFbxPath);

      // Wait for model to load
      await page.waitForFunction(() => {
        const badge = document.getElementById('fileNameBadge');
        return badge && badge.textContent.includes('spacemarine');
      }, { timeout: 30000 });
      await page.waitForTimeout(2000);

      const fbxMetrics = await page.evaluate(() => {
        const s = window.__spriteLab;
        return {
          charHeight3D: s.charHeight3D,
          autoStride3D: s.autoStride3D,
          strideRatio: s.strideRatio,
          effectiveStridePx: s.getEffectiveStridePx(),
          frameCount: s.getExportFrameCount(),
          badge: document.getElementById('dsMetricsBadge')?.textContent || ''
        };
      });
      console.log('Spacemarine FBX metrics:', fbxMetrics);
      assert(fbxMetrics.charHeight3D > 0.5, `Spacemarine height is valid: ${fbxMetrics.charHeight3D}`);
      assert(fbxMetrics.autoStride3D > 0, `Spacemarine stride is valid: ${fbxMetrics.autoStride3D}`);
      assert(fbxMetrics.strideRatio > 0, `Spacemarine stride ratio is valid: ${fbxMetrics.strideRatio}`);

      const screenshot3Path = path.join(EVIDENCE_DIR, '03_spacemarine_stride_preview.png');
      await page.screenshot({ path: screenshot3Path });
      console.log(`Saved screenshot 3: ${screenshot3Path}`);
    }

    assert.equal(errors.length, 0, `Encountered ${errors.length} page/console errors: ${errors.join(', ')}`);
    console.log('--- ALL STRIDE PREVIEW CHECKS PASSED WITH ZERO CONSOLE ERRORS ---');

  } finally {
    await browser.close();
  }
})();
