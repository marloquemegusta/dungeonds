// Fast headless character export (replacement for ../export_character_headless.cjs, no browser).
// Same CLI, same package (spritesheet.png, shadow.png, shadows/, settings.json, nds_shadow_anchor.h,
// dirs/, frames/, collage.gif, README.md), same "FIT {json}" and "WARNING [fit] ..." lines.
//
// usage: node export_character_fast.cjs <model.fbx> <outDir> [--template settings.json]
//          [--anim "<clip name>"] [--rigScale N] [--light <preset>] [--outline <pixel|sobel|none>]
//          [--saturation N] [--muzzleBone <bone>] [--muzzleForward F] [--fitZoom Z] [--fitExtent E]
//          [--normScale S] [--resolution N] [--legibility anterior|c2] [--tone agx|neutral]
//          [--lightAzimuth 0..7 (world-fixed light from the bonfire; use with --light camp-fire)] [--shadowElevation DEG]
//          [--supersample N] [--contrast N] [--frames N] [--pivot P] [--dirs S,SE,...]
//          [--fixedGround] [--doubleSided] [--noCHeader] [--timing]
// Delegated to the slow exporter (with a warning): a directory of fNN.glb, --list, JPEG textures, unknown flags.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { spawnSync } = require('node:child_process');
const { Pool } = require('./pool.cjs');

const SLOW = path.join(__dirname, '..', 'export_character_headless.cjs');
const VALUE_FLAGS = new Set(['--template', '--anim', '--rigScale', '--light', '--outline', '--saturation', '--muzzleBone',
  '--muzzleForward', '--fitZoom', '--fitExtent', '--normScale', '--resolution', '--tone', '--supersample', '--contrast',
  '--legibility', '--frames', '--dirs', '--pivot', '--lightAzimuth', '--shadowElevation']);
const BOOL_FLAGS = new Set(['--fixedGround', '--doubleSided', '--noCHeader', '--timing']);
const DELEGATE_FLAGS = new Set(['--list']);

const argv = process.argv.slice(2);
const opt = n => { const i = argv.indexOf(n); return i >= 0 ? argv[i + 1] : undefined; };
const has = n => argv.includes(n);

function delegate(reason) {
  console.warn(`WARNING [fast] delegated to export_character_headless.cjs: ${reason}`);
  const r = spawnSync(process.execPath, [SLOW, ...argv], { stdio: 'inherit' });
  process.exit(r.status === null ? 1 : r.status);
}

// Unknown flags or flags that need the browser: delegate instead of guessing.
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (!a.startsWith('--')) continue;
  if (DELEGATE_FLAGS.has(a)) delegate(`flag ${a}`);
  if (!VALUE_FLAGS.has(a) && !BOOL_FLAGS.has(a)) delegate(`unsupported flag ${a}`);
  if (VALUE_FLAGS.has(a)) i++;
}
const flagVals = new Set([...VALUE_FLAGS]);
const pos = argv.filter((a, i) => !a.startsWith('--') && !(i > 0 && flagVals.has(argv[i - 1])));
const modelArg = pos[0] && path.resolve(pos[0]);
const outDir = pos[1] && path.resolve(pos[1]);
if (!modelArg || !outDir) {
  console.error('usage: node export_character_fast.cjs <model.fbx> <outDir> [--template settings.json] [--anim name] [--rigScale N] [--light preset] [--outline mode] [--saturation N]');
  process.exit(2);
}
if (fs.statSync(modelArg).isDirectory()) delegate('GLB sequence directory');

const timing = has('--timing');
const T = {};
let tStart = process.hrtime.bigint();
const mark = (label) => { const now = process.hrtime.bigint(); T[label] = Number(now - tStart) / 1e6; tStart = now; };

const DIR_NAMES = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE'];
const DIR0_YAW = 3 * Math.PI / 4, DIR_STEP = Math.PI / 4;

let dirFilter = null;
if (opt('--dirs') !== undefined) {
  dirFilter = [];
  for (const raw of opt('--dirs').split(',').map(x => x.trim()).filter(Boolean)) {
    const m = /^(?:([0-7])_)?([A-Za-z]+)?$/.exec(raw);
    let idx = -1;
    if (/^[0-7]$/.test(raw)) idx = parseInt(raw, 10);
    else if (m) {
      const byName = m[2] ? DIR_NAMES.indexOf(m[2].toUpperCase()) : -1;
      idx = m[1] !== undefined ? parseInt(m[1], 10) : byName;
      if (m[1] !== undefined && m[2] && byName !== idx) idx = -1;
    }
    if (idx < 0) { console.error(`--dirs: unknown direction "${raw}" (valid: ${DIR_NAMES.join(', ')})`); process.exit(2); }
    if (!dirFilter.includes(idx)) dirFilter.push(idx);
  }
  if (!dirFilter.length) { console.error('--dirs: empty list'); process.exit(2); }
  dirFilter.sort((a, b) => a - b);
  if (dirFilter.length === 8) dirFilter = null;
}

const templatePath = path.resolve(opt('--template') || path.join(__dirname, '..', '..', '..', 'assets', 'sprites', 'characters', 'charger', 'settings.json'));
const s = JSON.parse(fs.readFileSync(templatePath, 'utf8'));
mark('args');

const pose = require('./pose.cjs');
const post = require('./post.cjs');
const pkg = require('./package.cjs');
const { encodePng } = require('./png.cjs');

function sanitizeExportName(raw, fallback = 'asset') {
  if (!raw || typeof raw !== 'string') return fallback;
  let t = raw.replace(/\.[^/.]+$/, '');
  t = t.replace(/[^a-zA-Z0-9_]+/g, '_').toLowerCase();
  t = t.replace(/_+/g, '_').replace(/^_+|_+$/g, '');
  if (!t) t = fallback;
  if (t.length > 20) t = t.slice(0, 20).replace(/_+$/, '');
  return t || fallback;
}

async function main() {
  // worker threads for shadows, per-direction processing and GIF encoding (DS_FAST_THREADS=0: in-process)
  const threads = process.env.DS_FAST_THREADS !== undefined ? parseInt(process.env.DS_FAST_THREADS, 10) : Math.min(8, os.cpus().length);
  const pool = new Pool(threads);
  const legibility = opt('--legibility') || 'anterior';
  if (!['anterior', 'c2'].includes(legibility)) { console.error('--legibility must be anterior or c2'); process.exit(2); }
  const toneOpt = opt('--tone');
  if (toneOpt !== undefined && !['agx', 'neutral'].includes(toneOpt)) { console.error('--tone must be agx or neutral'); process.exit(2); }
  const tone = toneOpt || (legibility === 'c2' ? 'neutral' : 'agx');
  const supersampleOpt = opt('--supersample') !== undefined ? parseInt(opt('--supersample'), 10) : undefined;
  const contrastOpt = opt('--contrast') !== undefined ? parseFloat(opt('--contrast')) : undefined;
  const framesOpt = opt('--frames') !== undefined ? parseInt(opt('--frames'), 10) : undefined;
  if (framesOpt !== undefined) s.framesPerDirection = framesOpt;
  if (legibility === 'c2') { s.supersample = 4; s.contrast = 1.0; }
  if (supersampleOpt !== undefined) s.supersample = supersampleOpt;
  if (contrastOpt !== undefined) s.contrast = contrastOpt;

  const rigScale = opt('--rigScale') !== undefined ? parseFloat(opt('--rigScale')) : s.rigScale;
  const lightAzOpt = opt('--lightAzimuth') !== undefined ? parseInt(opt('--lightAzimuth'), 10) : undefined;
  if (lightAzOpt !== undefined && !(lightAzOpt >= 0 && lightAzOpt <= 7)) { console.error('--lightAzimuth must be 0..7'); process.exit(2); }
  const shadowElOpt = opt('--shadowElevation') !== undefined ? parseFloat(opt('--shadowElevation')) : undefined;
  const lightPreset = opt('--light') || s.lightPreset || (s.lighting && s.lighting.preset) || 'neutral';
  const outlineMode = opt('--outline') || s.outlineMode || 'none';
  const saturation = opt('--saturation') !== undefined ? parseFloat(opt('--saturation')) : s.saturation;
  const muzzleBone = opt('--muzzleBone') || (s.muzzleSource && s.muzzleSource.bone) || undefined;
  const muzzleForward = opt('--muzzleForward') !== undefined ? parseFloat(opt('--muzzleForward')) : (s.muzzleSource && s.muzzleSource.forward !== undefined ? s.muzzleSource.forward : undefined);
  const fitZoom = opt('--fitZoom') !== undefined ? parseFloat(opt('--fitZoom')) : (s.fitZoom !== undefined ? s.fitZoom : 1);
  const fitExtent = opt('--fitExtent') !== undefined ? parseFloat(opt('--fitExtent')) : 0;
  const normScaleOpt = opt('--normScale') !== undefined ? parseFloat(opt('--normScale')) : 0;
  const resolution = opt('--resolution') !== undefined ? parseInt(opt('--resolution'), 10) : parseInt(String(s.frameSize).split('x')[0], 10);
  const frameCount = s.framesPerDirection;
  const size = resolution;
  const outline = outlineMode !== 'none';
  const targetPixels = size - (outline ? 2 : 0);
  const ss = Math.max(1, Math.round(s.supersample || 1));
  const elevation = s.cameraElevationDegrees;
  const fixedGround = has('--fixedGround');
  const pivotOverride = opt('--pivot') !== undefined ? parseFloat(opt('--pivot')) : undefined;
  const noCHeader = has('--noCHeader');
  const subset = dirFilter;
  const dirList = subset || [0, 1, 2, 3, 4, 5, 6, 7];

  const animOpt = opt('--anim') || s.animation;
  const warn = msg => console.warn(`WARNING [fit] ${msg}`);
  mark('template');

  // 1. Model: normalization, in-place, material conversion, clip selection.
  const character = await pose.loadCharacter(modelArg, {
    anim: animOpt, inPlace: !!s.inPlace, neckPitch: s.neckPitchDegrees ?? 0,
    normScale: normScaleOpt, normalStrength: s.normalStrength ?? 0.35,
    decoder: (bytes) => pool.run('png', bytes),
  });
  if (!animOpt) { /* first clip */ }
  // rigScale and the animation label are reported by the lab; rigScale only feeds the stride metric
  mark('load');

  const { clip, duration } = character;
  const times = duration > 0 ? Array.from({ length: frameCount }, (_, i) => duration * i / frameCount) : [0];

  // 2. Samples: one posed frame per time (the lab's sample loop), root at identity.
  const samples = [];
  for (const t of times) {
    const f = character.poseAt(t);
    const minY = fixedGround ? 0 : f.minY;
    samples.push({ meshes: f.meshes.map(m => ({ mesh: m.mesh, positions: m.positions, normals: m.normals })), minY, t });
  }
  mark('pose');

  // 3. Framing, muzzle setup (bone height taken from the last sample pose, as the lab does).
  const cam = pkg.frameCamera(samples, { size, targetPixels, elevation, fitZoom, fitExtent, warn });
  const camera = cam.camera;
  const fit = cam.fit;
  const origin = pkg.toPixel(camera, [0, 0, 0], size);
  const muzzleAnchorX = Math.max(0, Math.min(size - 1, Math.round(origin[0])));
  const muzzleAnchorY = Math.max(0, Math.min(size - 1, Math.round(origin[1])));
  const box = character.boxOf(character.wrapper);
  const muzzleSetup = pkg.findMuzzle(character, muzzleBone, muzzleForward, box);
  if (muzzleSetup && muzzleSetup.kind === 'bone') {
    // bone position per sample (root identity), recomputed per time like the render loop does
    for (const sm of samples) {
      character.poseOnly(sm.t);
      const p = new character.B.Vector3();
      muzzleSetup.bone.getWorldPosition(p);
      sm.boneP = [p.x, p.y, p.z];
    }
  } else if (muzzleSetup && muzzleSetup.kind === 'mesh') {
    const idxOfMesh = samples[0].meshes.findIndex(m => m.mesh === muzzleSetup.meshNode);
    for (const sm of samples) {
      const p = sm.meshes[idxOfMesh].positions;
      let x = 0, y = 0, z = 0;
      for (const i of muzzleSetup.tip) { x += p[i * 3]; y += p[i * 3 + 1]; z += p[i * 3 + 2]; }
      const n = muzzleSetup.tip.length;
      sm.tipAvg = [x / n, y / n, z / n];
    }
  }
  mark('frame');

  // 4. Render: the renderer gets the posed samples and one job per (direction, frame).
  const rendererPath = fs.existsSync(path.join(__dirname, 'raster.cjs'))
    ? path.join(__dirname, 'raster.cjs') : path.join(__dirname, 'dev', 'flat_raster.cjs');
  const { createRenderer } = require(process.env.DS_FAST_RASTER || rendererPath);
  const meshSpec = samples[0].meshes.map(m => {
    const g = m.mesh.geometry;
    const indices = g.index ? Uint32Array.from(g.index.array) : Uint32Array.from({ length: g.attributes.position.count }, (_, i) => i);
    const uvs = g.attributes.uv ? Float32Array.from(g.attributes.uv.array) : null;
    const materialIndex = character.matIndexOf(Array.isArray(m.mesh.material) ? m.mesh.material[0] : m.mesh.material);
    return { indices, uvs, materialIndex, doubleSided: false };
  });
  const lightOverrides = {};
  if (lightAzOpt !== undefined) lightOverrides.azimuth = lightAzOpt;
  if (shadowElOpt !== undefined) lightOverrides.shadowElevation = shadowElOpt;
  const lighting = pose.lightingFor(lightPreset, lightOverrides);
  const renderer = await createRenderer({
    size, ss, meshes: meshSpec,
    materials: character.renderMaterials,
    lighting,
    toneMapping: tone, exposure: 1, workers: 8,
  });
  renderer.setFrames(samples.map(sm => ({ positions: sm.meshes.map(m => m.positions), normals: sm.meshes.map(m => m.normals) })));
  // Shadows need only the camera and the origin anchor (both known now): they run in the pool while R renders.
  const params = { contrast: s.contrast ?? 1, saturation: saturation ?? 1, brightness: s.brightness ?? 1, outlineMode, filterWidth: 1.5 };
  const shadowPromise = subset ? null : Promise.all(Array.from({ length: frameCount }, (_, f) => {
    const sm = samples[f % samples.length];
    return pool.run('shadow', {
      size, minY: sm.minY, fixedGround, anchor: [muzzleAnchorX, muzzleAnchorY], shadowLight: lighting.shadowLight,
      cam: { eye: camera.eye, right: camera.basis.right, up: camera.basis.up, half: camera.right },
      meshes: sm.meshes.map(m => ({ positions: m.positions, index: m.mesh.geometry.index ? Uint32Array.from(m.mesh.geometry.index.array) : null })),
      dirs: [0, 1, 2, 3, 4, 5, 6, 7],
    });
  }));
  const jobs = [];
  for (const d of dirList) for (let f = 0; f < frameCount; f++) {
    const si = f % samples.length;
    jobs.push({ frame: si, yaw: DIR0_YAW - d * DIR_STEP, yOffset: -samples[si].minY, dir: d, f });
  }
  const camCall = { left: camera.left, right: camera.right, top: camera.top, bottom: camera.bottom, near: camera.near, far: camera.far, viewMatrix: camera.viewMatrix };
  const procPromises = [];
  for (let r = 0; r < dirList.length; r++) {
    const dbufs = await renderer.render(jobs.slice(r * frameCount, (r + 1) * frameCount), camCall);
    // downsample/grade/outline of this direction runs in the pool while the next direction renders
    procPromises.push(pool.run('proc', { bufs: dbufs, size, ss, params }));
  }
  await renderer.close();
  mark('raster');

  // 5. Post (pool): downsample + grade + outline per direction; C2 legibility over all frames; GIF per direction.
  const procs = await Promise.all(procPromises);
  let frames = [].concat(...procs);
  let legPivot = null;
  if (legibility === 'c2') {
    // one pivot over all frames (main thread); the per-frame curve + sharpen run in the GIF workers
    legPivot = typeof pivotOverride === 'number' ? pivotOverride : post.legibilityPivot(frames);
    console.log(`LOG [fit] legibility pivot ${legPivot}`);
  }
  const delay = Math.max(20, Math.round(1000 / frameCount));
  const gifRes = await Promise.all(dirList.map((d, r) => pool.run('gifC2', {
    frames: frames.slice(r * frameCount, (r + 1) * frameCount), size, delay, pivot: legPivot === null ? undefined : legPivot,
  })));
  frames = [].concat(...gifRes.map(g => g.frames));
  const results = dirList.map((d, r) => ({ name: DIR_NAMES[d], index: d, buf: Buffer.from(gifRes[r].gif.buffer, gifRes[r].gif.byteOffset, gifRes[r].gif.byteLength) }));
  const firstFrames = dirList.map((d, r) => post.composite(frames[r * frameCount].pixels, size, size));
  const collageBuf = post.collage(firstFrames, size);
  mark('post');

  // 6. Anchors, shadows, C header, settings.
  const renderedDirs = subset ? subset : null;
  const anchorData = pkg.anchorData(camera, frames, size, frameCount, renderedDirs);
  // muzzle capture per (direction, frame) from the render-time root state
  let muzzleCapture = null;
  if (muzzleSetup) {
    muzzleCapture = Array.from({ length: 8 }, () => Array.from({ length: frameCount }, () => [0, 0, 0]));
    for (const d of dirList) for (let f = 0; f < frameCount; f++) {
      const sm = samples[f % samples.length];
      const yaw = DIR0_YAW - d * DIR_STEP, yOff = -sm.minY;
      const pt = muzzleSetup.kind === 'bone' ? sm.boneP : sm.tipAvg;
      muzzleCapture[d][f] = pkg.muzzleCaptureOf(muzzleSetup, pt, yaw, yOff, camera, size, muzzleAnchorX, muzzleAnchorY);
    }
  }
  anchorData.dirMuzzle = muzzleCapture;
  let shadow = null;
  let shadowBoundsOut = null;
  let masks = null;
  if (!subset) {
    shadow = pkg.assembleShadows(await shadowPromise, size, frameCount);
    shadowBoundsOut = shadow.shadowBounds;
    masks = shadow.masks;
  }
  const name = sanitizeExportName(path.basename(modelArg), 'hero');
  const shadowSize = size * 2;
  const cHeaderText = noCHeader ? '// omitido' : pkg.cHeader(name, anchorData.anchor, anchorData.dirGroundAnchors, anchorData.dirBounds,
    shadowBoundsOut || [], masks || [], shadowSize, size, frameCount);
  mark('shadows');

  // stride metrics as in updateCharacterStrideMetrics / updateStrideUI
  const ratio = character.stride3D / (character.charHeight || 1.8);
  const effPx = Math.max(2, (targetPixels * (rigScale || 1)) * ratio);
  const ticks = s.ticksPerFrame;
  const settings = {
    name,
    model: path.basename(modelArg),
    animation: character.clipLabel,
    directions: DIR_NAMES,
    dirsRendered: subset ? subset.map(d => DIR_NAMES[d]) : DIR_NAMES.slice(),
    framesPerDirection: frameCount,
    frameSize: `${size}x${size}`,
    spritesheet: subset ? null : { columns: frameCount, rows: 8, width: frameCount * size, height: 8 * size, alpha: true },
    anchor: anchorData.anchor,
    dirGroundAnchors: anchorData.dirGroundAnchors,
    dirBounds: anchorData.dirBounds,
    ...(muzzleCapture ? { dirMuzzle: muzzleCapture } : {}),
    ...(subset ? {} : { shadowSize: [shadowSize, shadowSize], shadowBounds: shadowBoundsOut }),
    stride3dMeters: Number(character.stride3D.toFixed(3)),
    strideRatio: Number(ratio.toFixed(3)),
    ticksPerFrame: ticks,
    stridePixels: Number(effPx.toFixed(2)),
    speedFixed8_8: Math.round((effPx * 256) / Math.max(1, frameCount * (ticks || 1))),
    inPlace: !!s.inPlace,
    rigScale,
    cameraElevationDegrees: elevation,
    contrast: s.contrast ?? 1,
    saturation: saturation ?? 1,
    neckPitchDegrees: s.neckPitchDegrees ?? 0,
    displace: s.displace ?? 0,
    brightness: s.brightness ?? 1,
    webglShadowQuality: s.webglShadowQuality ?? 16,
    normalStrength: s.normalStrength ?? 0.35,
    shadowSoftness: s.shadowSoftness ?? 2,
    supersample: ss,
    legibility,
    ...(typeof legPivot === 'number' && legibility === 'c2' ? { legibilityPivot: legPivot } : {}),
    boneShader: false,
    renderEngine: 'Three.js WebGL (browser)',
  };
  // CLI post-patch (same as export_character_headless.cjs)
  if (lightPreset) settings.lightPreset = lightPreset;
  if (outlineMode) settings.outlineMode = outlineMode;
  if (muzzleBone) settings.muzzleSource = { bone: muzzleBone, forward: muzzleForward ?? 0.05 };
  settings.fitZoom = fitZoom;
  settings.measuredExtent = fit.extent;
  settings.fitExtent = fit.fitExtent;
  settings.normScale = character.normScale;
  settings.toneMapping = tone;
  settings.legibility = legibility;
  if (subset) settings.dirsRendered = subset.map(d => DIR_NAMES[d]);
  if (s.speedFixed8_8 !== undefined) settings.speedFixed8_8 = s.speedFixed8_8;
  if (s.ticksPerFrame !== undefined) settings.ticksPerFrame = s.ticksPerFrame;

  const frameBufs = [].concat(...gifRes.map(g => g.pngs));
  const sheetP = subset ? Promise.resolve(null) : pool.run('pngImage', { pixels: pkg.atlasPixels(frames, size, frameCount), width: frameCount * size, height: 8 * size });
  const shadowP = subset ? Promise.resolve(null) : pool.run('pngImage', { pixels: shadow.atlas, width: shadow.atlasW, height: shadow.atlasH });
  const [sheetBuf, shadowBuf] = await Promise.all([sheetP, shadowP]);
  pkg.writePackage(outDir, {
    frames, frameBufs, sheetBuf, shadowBuf, frameCount, size, results, collageBuf, renderedDirs: subset, shadow: shadow && {
      shadowSize, atlas: shadow.atlas, atlasW: shadow.atlasW, atlasH: shadow.atlasH,
    }, cHeaderText, settings,
  });
  mark('write');
  await pool.close();

  console.log('FIT ' + JSON.stringify({ extent: fit.extent, fitExtent: fit.fitExtent, half: fit.half, center: fit.center, normScale: character.normScale }));
  console.log(`package written to ${outDir}`);
  if (timing) {
    const total = Object.values(T).reduce((a, b) => a + b, 0);
    console.log('TIMING ' + Object.entries(T).map(([k, v]) => `${k}=${v.toFixed(0)}ms`).join(' ') + ` total=${total.toFixed(0)}ms renderer=${path.basename(rendererPath)}`);
  }
}

main().catch(e => {
  if (e instanceof pose.DelegateError) delegate(e.message);
  console.error(e);
  process.exit(1);
});
