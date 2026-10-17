// Headless Chromium regression matrix for the offline weapon/animation lab.
// Build first: python tools/lab/build_weapon_anim_lab.py
// Run: node tools/lab/test_lab_headless.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { chromium } = require('C:/Users/malfonso/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const splicer = require('./fbx_binary_splicer.js');
const THREE = require('./offline_three.cjs');

const ROOT = path.resolve(__dirname, '../..');
const HTML = path.join(__dirname, 'FBX-Weapon-Anim-Lab-offline.html');
const ASSETS = path.join(ROOT, 'assets');
const EVIDENCE = path.join(ROOT, 'walkthroughs/weapon-anim-lab-fixes/assets');
const characters = [
  ['spacemarine', 'characters/spacemarine/spacemarine.fbx'],
  ['necron', 'characters/necron/tripo_convert_c240e498-85d5-4ccc-a624-798965993caa.fbx'],
  ['henar', 'characters/custom/henar_top_kaki.fbx'],
  ['mario', 'characters/custom/mario_camisa_blanca.fbx'],
  ['wizard', 'characters/custom/wizard.fbx']
];
const tripoWeapons = [
  ['shotgun_marine', 'shotgun_marine'],
  ['sniper_necron', 'sniper_necron']
];

assert(fs.existsSync(HTML), `Build the lab first: ${HTML}`);
fs.mkdirSync(EVIDENCE, { recursive: true });
const errors = [];
const evidence = { browser: 'Chromium headless', characters: [], weapons: [], hybrids: [], screenshots: [] };

function waitFor(predicate, timeout = 45000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => predicate() ? resolve() : Date.now() - start > timeout
      ? reject(new Error(`Timed out after ${timeout} ms`)) : setTimeout(tick, 100);
    tick();
  });
}
function materialSummary() {
  const s = window.__weaponAnimLab;
  const data = s.activeWeaponData;
  const materials = data?.materials || [];
  const geometry = s.weaponMesh?.geometry;
  return {
    weaponId: data?.id,
    name: data?.name,
    vertexCount: data?.positions?.length / 3,
    indexCount: data?.indices?.length,
    materialCount: materials.length,
    texturedMaterialCount: materials.filter(m => (m.material || m).map).length,
    loadedMapCount: materials.filter(m => {
      const tex = (m.material || m).map;
      const image = tex?.image;
      return !!(tex && image && image.complete !== false && (image.naturalWidth || image.width) > 0);
    }).length,
    groups: (data?.groups || []).map(g => ({ start: g.start, count: g.count, materialIndex: g.materialIndex })),
    rendererGroups: (geometry?.groups || []).map(g => ({ start: g.start, count: g.count, materialIndex: g.materialIndex })),
    textureByteCount: materials.reduce((n, m) => n + (m.pngBytes?.byteLength || 0), 0),
    materialNames: materials.map(m => m.name || m.material?.name || '')
  };
}

(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--enable-webgl', '--use-gl=swiftshader', '--disable-dev-shm-usage'] });
  try {
    const page = await browser.newPage({ viewport: { width: 1680, height: 1050 }, deviceScaleFactor: 1 });
    page.on('pageerror', error => errors.push(error.stack || error.message));
    page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
    await page.goto(`file:///${HTML.replace(/\\/g, '/')}`, { waitUntil: 'load' });
    await page.waitForFunction(() => !!window.__weaponAnimLab?.renderer, { timeout: 30000 });
    const stateReady = await page.evaluate(() => !!window.__weaponAnimLab?.catalog && !!window.__weaponAnimLab?.renderer);
    assert(stateReady, 'offline lab initializes in headless Chromium');

    for (const [id, relative] of characters) {
      const file = path.join(ASSETS, relative);
      assert(fs.existsSync(file), `character fixture ${id} exists: ${file}`);
      const previousLabel = await page.locator('#statusRig').textContent();
      await page.locator('#charFileInput').setInputFiles(file);
      await page.waitForFunction(previous => window.__weaponAnimLab?.charRigMap &&
        document.querySelector('#statusRig')?.textContent !== previous, previousLabel, { timeout: 60000 });
      const summary = await page.evaluate(() => {
        const s = window.__weaponAnimLab;
        return { name: s.charName, bones: Object.keys(s.charRigMap?.bones || {}), activeAnimId: s.activeAnimId,
          animationIds: s.animations.map(a => a.id), count: s.animations.length,
          exportEnabled: !document.querySelector('#btnExportCurrentFbx').disabled };
      });
      assert(summary.bones.includes('Hips'), `${id} maps a Hips bone`);
      assert(summary.count >= 11, `${id} sees the unique base+hybrid clips (got ${summary.count})`);
      assert(summary.animationIds.includes('rifle_walk_ready') && summary.animationIds.includes('rifle_run_ready'),
        `${id} exposes both ready-to-fire hybrid modes`);
      assert(summary.exportEnabled, `${id} enables FBX export`);
      evidence.characters.push({ id, boneCount: summary.bones.length, clips: summary.count });
    }

    // Return to the representative Mixamo character for all weapon comparisons.
    await page.locator('#charFileInput').setInputFiles(path.join(ASSETS, 'characters/spacemarine/spacemarine.fbx'));
    await page.waitForFunction(() => window.__weaponAnimLab?.charName?.toLowerCase().includes('spacemarine'), { timeout: 60000 });

    // Death Fall is a real bundled FBX clip and must be reachable through the visible Combat filter.
    await page.locator('#animCategoryFilter').selectOption('Combat');
    const deathRow = page.locator('#animCatalogList .catalog-item').filter({ hasText: 'Death Fall' });
    await deathRow.waitFor({ state: 'visible' });
    const deathListed = await deathRow.evaluate(row => ({
      name: row.querySelector('.catalog-item-name')?.textContent,
      category: row.querySelector('.catalog-tag')?.textContent,
      checked: row.querySelector('input[type="checkbox"]')?.checked
    }));
    assert.equal(deathListed.name, 'Death Fall', 'Combat filter exposes the factual death clip name');
    assert.match(deathListed.category, /^Combat · 1\.2s$/, 'death row shows its category and duration');
    await deathRow.click();
    await page.waitForFunction(() => window.__weaponAnimLab?.activeAnimId === 'combat_death');
    const deathPreview = await page.evaluate(() => {
      const s = window.__weaponAnimLab;
      const row = [...document.querySelectorAll('#animCatalogList .catalog-item')]
        .find(item => item.querySelector('.catalog-item-name')?.textContent === 'Death Fall');
      return {
        activeAnimId: s.activeAnimId,
        selected: s.selectedAnimIds.has('combat_death'),
        rowActive: row?.classList.contains('active'),
        rowChecked: row?.querySelector('input[type="checkbox"]')?.checked,
        duration: s.duration,
        retargetReady: !!s.charRigMap && !!s.retargetCtx,
        status: document.querySelector('#statusAnim')?.textContent
      };
    });
    assert.equal(deathPreview.activeAnimId, 'combat_death');
    assert(deathPreview.selected && deathPreview.rowActive && deathPreview.rowChecked,
      'Death Fall is selected in the catalog and highlighted');
    assert(deathPreview.retargetReady && deathPreview.duration > 1.2,
      'Death Fall starts a retargeted preview on the loaded character');
    assert.match(deathPreview.status, /Death Fall/, 'preview status names the selected death clip');
    evidence.deathAnimation = { ...deathListed, ...deathPreview };
    await page.locator('#animCategoryFilter').selectOption('ALL');

    for (const weaponId of ['ak47', 'carbine']) {
      await page.evaluate(id => {
        const s = window.__weaponAnimLab;
        const row = [...document.querySelectorAll('#weaponCatalogList .catalog-item')]
          .find(el => el.querySelector('.catalog-item-name')?.textContent.toLowerCase().includes(id === 'ak47' ? 'ak-47' : 'carbine'));
        if (!row) throw new Error(`Catalog weapon not found: ${id}`);
        row.click();
      }, weaponId);
      await page.waitForFunction(id => window.__weaponAnimLab?.activeWeaponData?.id === id, weaponId, { timeout: 30000 });
      const item = await page.evaluate(materialSummary);
      assert(item.vertexCount > 0 && item.indexCount > 0, `${weaponId} has geometry`);
      evidence.weapons.push(item);
    }

    for (const [id, folder] of tripoWeapons) {
      const dir = path.join(ASSETS, 'weapons', folder);
      const fbx = fs.readdirSync(dir).find(n => n.toLowerCase().endsWith('.fbx'));
      const weaponStem = fbx.replace(/\.fbx$/i, '').toLowerCase();
      const textureDir = path.join(dir, `${fbx.slice(0, -4)}.fbm`);
      const sourceTextures = fs.readdirSync(textureDir).filter(n => /\.(png|jpe?g)$/i.test(n));
      assert(sourceTextures.length >= (id === 'shotgun_marine' ? 14 : 13), `${id} has its full companion texture set`);
      await page.locator('#weaponFolderInput').setInputFiles(dir);
      await page.waitForFunction(name => window.__weaponAnimLab?.activeWeaponData?.name?.toLowerCase().includes(name), weaponStem, { timeout: 90000 });
      const item = await page.evaluate(materialSummary);
      assert(item.materialCount >= (id === 'shotgun_marine' ? 14 : 13), `${id} retains all source materials (${item.materialCount})`);
      assert(item.texturedMaterialCount >= (id === 'shotgun_marine' ? 14 : 13), `${id} retains each material map`);
      assert(item.loadedMapCount >= (id === 'shotgun_marine' ? 14 : 13), `${id} decoded all companion maps`);
      assert(item.textureByteCount > 100000, `${id} maps have source image bytes`);
      assert(item.groups.length >= 2, `${id} retains mesh material groups`);
      assert(item.groups.every(g => g.count > 0 && g.count % 3 === 0 && g.materialIndex < item.materialCount), `${id} has valid triangle groups`);
      assert.equal(item.groups.reduce((n, g) => n + g.count, 0), item.indexCount, `${id} groups cover the full index stream`);
      evidence.weapons.push({ id, ...item, sourceTextureCount: sourceTextures.length, exportRoundTrips: [] });

      await page.locator('#btnPlayPause').click().catch(() => {});
      await page.screenshot({ path: path.join(EVIDENCE, `${id}-contact.png`), fullPage: false });
      evidence.screenshots.push(`${id}-contact.png`);

      // Select and capture both ready modes; export/reimport one mode per model.
      for (const hybridId of ['rifle_walk_ready', 'rifle_run_ready']) {
        await page.evaluate(id => {
          const state = window.__weaponAnimLab;
          const row = [...document.querySelectorAll('#animCatalogList .catalog-item')]
            .find(el => el.querySelector('.catalog-item-name')?.textContent === state.animations.find(a => a.id === id)?.name);
          if (!row) throw new Error(`Hybrid row not found: ${id}`);
          row.click();
        }, hybridId);
        await page.waitForFunction(id => window.__weaponAnimLab?.activeAnimId === id, hybridId, { timeout: 30000 });
        const hybridData = await page.evaluate(id => {
          const s = window.__weaponAnimLab;
          const clip = s.animations.find(a => a.id === id);
          const h = clip.hybrid;
          s.engine.evaluateRetargetFrame(s.charRigMap, s.retargetCtx, clip.duration * 0.43,
            s.retargetParams, { localMatrix4: s.weaponAlignResult.localMatrix4,
              foregripLocalPos: s.weaponAlignResult.foregripLocalPos,
              attachBoneName: s.weaponAlignResult.attachBoneName,
              finalLocalAxes: s.weaponAlignResult.finalLocalAxes });
          if (s.charWrapper) s.charWrapper.updateWorldMatrix(true, true);
          const attachName = s.weaponAlignResult.attachBoneName || 'RightHand';
          const supportName = attachName === 'LeftHand' ? 'RightHand' : 'LeftHand';
          const support = s.charRigMap.bones[supportName];
          const attach = s.charRigMap.bones[attachName];
          const middle = s.charRigMap.bones[`${supportName}Middle1`];
          const vectors = supportName === 'LeftHand' ? s.charRigMap.leftHandVectors : s.charRigMap.rightHandVectors;
          const middleWorld = middle.getWorldPosition(new s.THREE.Vector3());
          const middleLocal = middleWorld.applyMatrix4(support.matrixWorld.clone().invert());
          const palmOffset = middleLocal.clone().multiplyScalar(0.6)
            .add(vectors.palmInLocal.clone().multiplyScalar(middleLocal.length() * 0.25));
          const palmWorld = palmOffset.applyMatrix4(support.matrixWorld);
          const weaponWorld = attach.matrixWorld.clone().multiply(s.weaponAlignResult.localMatrix4);
          const foregripWorld = s.weaponAlignResult.foregripLocalPos.clone().applyMatrix4(weaponWorld);
          const contactError = palmWorld.distanceTo(foregripWorld) / s.charRigMap.charHeight;
          const handQ = support.getWorldQuaternion(new s.THREE.Quaternion());
          const palmInWorld = vectors.palmInLocal.clone().applyQuaternion(handQ).normalize();
          const handForward = vectors.handFwdLocal.clone().applyQuaternion(handQ).normalize();
          const barrelWorld = new s.THREE.Vector3(...s.weaponAlignResult.finalLocalAxes.axisBarrel).transformDirection(attach.matrixWorld);
          const rightWorld = new s.THREE.Vector3(...s.weaponAlignResult.finalLocalAxes.axisRight).transformDirection(attach.matrixWorld);
          const orientation = { forwardDot: handForward.dot(barrelWorld),
            palmDot: palmInWorld.dot(rightWorld) * (supportName === 'LeftHand' ? 1 : -1) };
          return { id, lower: h.lowerAnimationId, upper: h.upperAnimationId, duration: clip.duration,
            groups: s.activeWeaponData.groups.length, contactError, orientation };
        }, hybridId);
        assert(hybridData.contactError < 1e-4,
          `${id}/${hybridId} support palm reaches foregrip (relative error ${hybridData.contactError})`);
        assert(hybridData.orientation.forwardDot > 0.5 && hybridData.orientation.palmDot > 0.5,
          `${id}/${hybridId} support palm follows the final barrel/right axes`);
        evidence.hybrids.push({ weapon: id, ...hybridData });
        const frameName = `${id}-${hybridId}.png`;
        await page.screenshot({ path: path.join(EVIDENCE, frameName), fullPage: false });
        evidence.screenshots.push(frameName);

        const tempExport = path.join(os.tmpdir(), `${hybridId}-${Date.now()}.fbx`);
        const downloadPromise = page.waitForEvent('download', { timeout: 90000 });
        await page.evaluate(() => window.__labExportCurrentFbxBuffer());
        const download = await downloadPromise;
        await download.saveAs(tempExport);
        const exported = fs.readFileSync(tempExport);
        const ast = splicer.parseFBXBinary(exported);
        const exportedArrayBuffer = exported.buffer.slice(exported.byteOffset, exported.byteOffset + exported.byteLength);
        const reloaded = new THREE.FBXLoader().parse(exportedArrayBuffer, '');
        assert.equal(reloaded.animations.length, 1, `${id}/${hybridId} exported FBX reloads one selected hybrid clip`);
        assert(Math.abs(reloaded.animations[0].duration - hybridData.duration) < 0.08,
          `${id}/${hybridId} exported hybrid retains its selected duration`);
        const reloadedWeapons = [];
        reloaded.traverse(node => {
          if (node.isMesh && node.geometry?.groups?.length >= 2 && Array.isArray(node.material) &&
              node.geometry.attributes?.position?.count === item.indexCount) reloadedWeapons.push(node);
        });
        assert(reloadedWeapons.length > 0, `${id}/${hybridId} exported weapon mesh reloads with grouped geometry`);
        assert(reloadedWeapons.some(node => node.material.length >= item.materialCount),
          `${id}/${hybridId} FBXLoader reloads every weapon material slot`);
        const objects = ast.nodes.find(n => n.name === 'Objects').children;
        const materialNames = item.materialNames.filter(Boolean);
        const expectedTextureCount = id === 'shotgun_marine' ? 14 : 13;
        const exportedTextures = objects.filter(n => n.name === 'Texture');
        const exportedVideos = objects.filter(n => n.name === 'Video');
        assert(exportedTextures.length >= expectedTextureCount,
          `${id}/${hybridId} export retains all ${expectedTextureCount} texture nodes`);
        assert(exportedVideos.length >= expectedTextureCount,
          `${id}/${hybridId} export embeds every companion image`);
        for (const materialName of materialNames) {
          assert(objects.some(n => n.name === 'Material' && String(n.props[1]?.value || '').includes(materialName)),
            `${id}/${hybridId} export retains material ${materialName}`);
        }
        fs.unlinkSync(tempExport);
        const exportedWeapon = evidence.weapons.find(weapon => weapon.id === id);
        exportedWeapon.exportRoundTrips.push({
          hybridId,
          textureNodeCount: exportedTextures.length,
          embeddedImageCount: exportedVideos.length,
          materialCount: objects.filter(n => n.name === 'Material').length
        });
      }
    }

    for (const [id] of tripoWeapons) {
      const weaponEvidence = evidence.weapons.find(weapon => weapon.id === id);
      assert.deepEqual(weaponEvidence.exportRoundTrips.map(result => result.hybridId).sort(),
        ['rifle_run_ready', 'rifle_walk_ready'], `${id} round-trips both hybrid modes`);
    }

    // Fixed idle: freeze playback, scrub to deterministic times, capture a short frame sequence.
    await page.evaluate(() => {
      const state = window.__weaponAnimLab;
      const idle = state.animations.find(a => a.id === 'rifle_idle');
      const row = [...document.querySelectorAll('#animCatalogList .catalog-item')]
        .find(el => el.querySelector('.catalog-item-name')?.textContent === idle.name);
      row.click();
      state.playing = false;
    });
    const idleTimes = [0, 0.25, 0.5, 0.75];
    for (let i = 0; i < idleTimes.length; i++) {
      await page.evaluate(t => {
        const slider = document.querySelector('#timelineScrubber');
        slider.value = String(t);
        slider.dispatchEvent(new Event('input', { bubbles: true }));
      }, idleTimes[i]);
      const name = `rifle-idle-${String(i).padStart(2, '0')}.png`;
      await page.screenshot({ path: path.join(EVIDENCE, name), fullPage: false });
      evidence.screenshots.push(name);
    }

    assert.deepEqual(errors, [], `browser reports no uncaught JS errors: ${errors.join('\n')}`);
    fs.writeFileSync(path.join(EVIDENCE, 'headless-summary.json'), JSON.stringify(evidence, null, 2));
    console.log(JSON.stringify(evidence, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
