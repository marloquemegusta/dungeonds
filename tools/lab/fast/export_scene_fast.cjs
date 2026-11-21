// Exportador rapido de SECUENCIAS GLB (escenas ya horneadas por Blender, sin piel ni armadura): los remates.
// Mismo paquete que el lab lento para un directorio de fNN.glb (frames/<d>_<DIR>/<f>.png, shadow.png,
// settings.json, dirs/*.gif, collage.gif, spritesheet.png), sin navegador: parsea cada GLB con
// tools/lab/glb_loader_minimal.js y rasteriza con raster.cjs (el mismo que los personajes).
//
// usage: node export_scene_fast.cjs <glbDir> <outDir> [--template settings.json] [--dirs 0,1,...]
//          [--resolution N] [--ppm N] [--fitExtent M] [--legibility anterior|c2] [--tone neutral]
//          [--noCHeader] [--timing] [--doubleSided]
// Los fotogramas se ordenan por el numero de fNN.glb. Todos los fotogramas deben compartir la misma
// topologia (mismo numero de mallas/materiales por grupo): el rasterizador comparte una sola malla.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const { Pool } = require('./pool.cjs');
const GLB = require('../glb_loader_minimal.js');

const argv = process.argv.slice(2);
const opt = n => { const i = argv.indexOf(n); return i >= 0 ? argv[i + 1] : undefined; };
const has = n => argv.includes(n);

const VALUE_FLAGS = new Set(['--template', '--dirs', '--resolution', '--ppm', '--fitExtent', '--legibility', '--tone', '--limit', '--only-material', '--shadow-skip-materials']);
const BOOL_FLAGS = new Set(['--noCHeader', '--timing', '--doubleSided']);
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (!a.startsWith('--')) continue;
  if (!VALUE_FLAGS.has(a) && !BOOL_FLAGS.has(a)) {
    console.error(`unsupported flag ${a}`); process.exit(2);
  }
  if (VALUE_FLAGS.has(a)) i++;
}
const pos = argv.filter((a, i) => !a.startsWith('--') && !(i > 0 && VALUE_FLAGS.has(argv[i - 1])));
const glbDir = pos[0] && path.resolve(pos[0]);
const outDir = pos[1] && path.resolve(pos[1]);
if (!glbDir || !outDir) {
  console.error('usage: node export_scene_fast.cjs <glbDir> <outDir> [--template settings.json] [--dirs 0,1,...] [--resolution N] [--ppm N] [--fitExtent M]');
  process.exit(2);
}

const DIR_NAMES = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE'];
const DIR0_YAW = 3 * Math.PI / 4, DIR_STEP = Math.PI / 4;
// El lab lento gira cada grupo GLB -90 grados en Y (glTF Y arriba -> ejes del lab).
const LAB_RY = -Math.PI / 2;
const CR = Math.cos(LAB_RY), SR = Math.sin(LAB_RY);

const timing = has('--timing');
const T = {};
let tStart = process.hrtime.bigint();
const mark = (label) => { const now = process.hrtime.bigint(); T[label] = Number(now - tStart) / 1e6; tStart = now; if (process.env.SCENE_VERBOSE) console.log(`LOG [scene] ${label} ${T[label].toFixed(0)}ms`); };

let dirFilter = null;
if (opt('--dirs') !== undefined) {
  dirFilter = [...new Set(opt('--dirs').split(',').map(x => parseInt(x.trim(), 10)))];
  if (!dirFilter.length || dirFilter.some(d => !(d >= 0 && d <= 7))) { console.error('--dirs: use 0..7'); process.exit(2); }
  dirFilter.sort((a, b) => a - b);
  if (dirFilter.length === 8) dirFilter = null;
}

const templatePath = path.resolve(opt('--template') || path.join(__dirname, '..', '..', '..', 'assets', 'sprites', 'characters', 'exvoto', 'settings.json'));
const s = JSON.parse(fs.readFileSync(templatePath, 'utf8'));
const size = opt('--resolution') !== undefined ? parseInt(opt('--resolution'), 10) : parseInt(String(s.frameSize).split('x')[0], 10);
const elevation = s.cameraElevationDegrees ?? 30;
// px/m vertical de la camara ortografica. Los bins del remate (generate_remate_sprites.py) asumen 38 px/m:
// la celda de 96 px cubre 2,5263 m y el packer convierte los pies del heroe con esa escala.
const ppm = opt('--ppm') !== undefined ? parseFloat(opt('--ppm')) : 38;
const fitExtent = opt('--fitExtent') !== undefined ? parseFloat(opt('--fitExtent')) : size / ppm;
const outlineMode = opt('--outline') || s.outlineMode || 'none';
const outline = outlineMode !== 'none';
const targetPixels = size - (outline ? 2 : 0);
const ss = Math.max(1, Math.round(s.supersample || 1));
const legibility = opt('--legibility') || s.legibility || 'c2';
const tone = opt('--tone') || (legibility === 'c2' ? 'neutral' : (s.toneMapping || 'neutral'));
if (tone !== 'neutral') { console.error('raster: solo tone neutral (AgX no implementado)'); process.exit(2); }
const lightPreset = s.lightPreset || 'neutral';
const noCHeader = has('--noCHeader');
const doubleSided = has('--doubleSided');
const mirrorX = has('--mirror-x');
const dirList = dirFilter || [0, 1, 2, 3, 4, 5, 6, 7];

function readGlbFrames(dir) {
  const files = fs.readdirSync(dir).filter(f => /^f\d+\.glb$/i.test(f))
    .sort((a, b) => parseInt(a.match(/\d+/)[0], 10) - parseInt(b.match(/\d+/)[0], 10));
  if (!files.length) throw new Error('No fNN.glb files found in ' + dir);
  const out = [];
  for (const f of files) {
    const buf = fs.readFileSync(path.join(dir, f));
    const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
    out.push({ file: f, raw: GLB.parseGLBToMeshData(ab) });
  }
  return out;
}

// Rotacion del lab (-90 grados en Y) sobre posiciones y normales, ya en mundo.
function labRotate(raw) {
  const p = raw.positions, n = raw.normals;
  for (let i = 0; i < p.length; i += 3) {
    const x = p[i], z = p[i + 2];
    p[i] = x * CR + z * SR;
    p[i + 2] = -x * SR + z * CR;
    const nx = n[i], nz = n[i + 2];
    n[i] = nx * CR + nz * SR;
    n[i + 2] = -nx * SR + nz * CR;
  }
}

// Grupo (malla+material) -> malla compacta {positions, normals, uvs, indices, materialIndex}.
function splitGroup(raw, g) {
  const map = new Map();
  const idx = new Uint32Array(g.count);
  for (let k = 0; k < g.count; k++) {
    const gi = raw.indices[g.start + k];
    let li = map.get(gi);
    if (li === undefined) { li = map.size; map.set(gi, li); }
    idx[k] = li;
  }
  const n = map.size;
  const positions = new Float32Array(n * 3), normals = new Float32Array(n * 3), uvs = new Float32Array(n * 2);
  let li = 0;
  for (const gi of map.keys()) {
    positions[li * 3] = raw.positions[gi * 3];
    positions[li * 3 + 1] = raw.positions[gi * 3 + 1];
    positions[li * 3 + 2] = raw.positions[gi * 3 + 2];
    normals[li * 3] = raw.normals[gi * 3];
    normals[li * 3 + 1] = raw.normals[gi * 3 + 1];
    normals[li * 3 + 2] = raw.normals[gi * 3 + 2];
    uvs[li * 2] = raw.uvs[gi * 2];
    uvs[li * 2 + 1] = raw.uvs[gi * 2 + 1];
    li++;
  }
  return { positions, normals, uvs, indices: idx, materialIndex: g.materialIndex };
}

async function main() {
  const threads = process.env.DS_FAST_THREADS !== undefined ? parseInt(process.env.DS_FAST_THREADS, 10) : Math.min(8, os.cpus().length);
  const pool = new Pool(threads);
  const warn = msg => console.warn(`WARNING [fit] ${msg}`);

  // 1. Leer y rotar los fotogramas; materiales unicos por nombre y texturas baseColor (PNG) deducidas por hash.
  const seq = readGlbFrames(glbDir);
  const limit = opt('--limit') !== undefined ? parseInt(opt('--limit'), 10) : 0;
  if (limit > 0) seq.length = Math.min(seq.length, limit);
  const frameCount = seq.length;
  const matByName = new Map();
  for (const { raw } of seq) {
    labRotate(raw);
    for (const m of raw.materials) {
      if (!matByName.has(m.name)) {
        matByName.set(m.name, {
          color: (m.color || [0.8, 0.8, 0.8]).slice(0, 3),
          emissive: m.emissive ? m.emissive.slice(0, 3) : null,
          imageBytes: m.imageBytes ? Uint8Array.from(m.imageBytes) : null,
          mimeType: m.mimeType || null,
        });
      }
      m.imageBytes = null;       // el buffer GLB (24 MB) no se retiene por fotograma
    }
  }
  mark('read');

  // 2. Decodificar texturas (una por hash) en los workers.
  const texByHash = new Map();
  const texJobs = [];
  for (const [name, m] of matByName) {
    if (!m.imageBytes) continue;
    if (!/png/i.test(m.mimeType || 'image/png')) throw new Error(`material ${name}: textura ${m.mimeType} (solo PNG en el lab rapido)`);
    const hash = crypto.createHash('sha1').update(m.imageBytes).digest('hex');
    if (!texByHash.has(hash)) { texByHash.set(hash, null); texJobs.push({ hash, bytes: m.imageBytes }); }
  }
  await Promise.all(texJobs.map(async j => { texByHash.set(j.hash, await pool.run('png', j.bytes)); }));
  for (const [name, m] of matByName) {
    if (!m.imageBytes) continue;
    const hash = crypto.createHash('sha1').update(m.imageBytes).digest('hex');
    m.tex = texByHash.get(hash);
    m.imageBytes = null;
  }
  mark('textures');

  // 3. Materiales del rasterizador (equivalente a buildThreeMeshFromGLB + setupModelMaterials del lab lento).
  const matNames = [...matByName.keys()];
  const matIndexByName = new Map(matNames.map((n, i) => [n, i]));
  const materials = matNames.map(n => {
    const m = matByName.get(n);
    return {
      color: m.tex ? [1, 1, 1] : m.color,
      roughness: 0.85, metalness: 0.05,
      emissive: m.emissive || [0, 0, 0],
      emissiveIntensity: m.emissive ? 1.0 : 0.0,
      normalScale: s.normalStrength ?? 0.5,
      map: m.tex ? { width: m.tex.width, height: m.tex.height, data: m.tex.data, colorSpace: 'srgb', flipY: false, wrapS: 1000, wrapT: 1000 } : null,
    };
  });

  // 4. Mallas de cada fotograma; mismo numero y tamano de grupos en todos (topologia fija).
  const frames = seq.map(({ file, raw }) => {
    if (mirrorX) { for (let i = 0; i < raw.positions.length; i += 3) raw.positions[i] = -raw.positions[i]; }
    const meshes = raw.groups.map(g => splitGroup(raw, g));
    for (const mesh of meshes) mesh.materialIndex = matIndexByName.get(raw.materials[mesh.materialIndex].name);
    return { file, meshes };
  });
  let ref = frames[0].meshes;
  const onlyMaterial = opt('--only-material');
  if (onlyMaterial) {                 // depuracion: deja solo las mallas cuyo material contiene el texto
    for (const fr of frames) fr.meshes = fr.meshes.filter(m => (matNames[m.materialIndex] || '').includes(onlyMaterial));
    ref = frames[0].meshes;
  }
  for (const fr of frames) {
    if (fr.meshes.length !== ref.length) throw new Error(`topologia distinta en ${fr.file}: ${fr.meshes.length} grupos vs ${ref.length}`);
    for (let i = 0; i < ref.length; i++) {
      if (fr.meshes[i].positions.length !== ref[i].positions.length || fr.meshes[i].indices.length !== ref[i].indices.length) {
        throw new Error(`topologia distinta en ${fr.file} grupo ${i}: ${fr.meshes[i].positions.length / 3} verts vs ${ref[i].positions.length / 3}`);
      }
    }
  }
  // Actores ocultos (encogidos a 1e-5 en Blender): se colapsan en el origen del mundo para que no estiren el
  // encuadre ni dejen sombra. Conservan su malla (la topologia debe ser la misma en todos los fotogramas).
  let collapsed = 0;
  for (const fr of frames) {
    for (const m of fr.meshes) {
      const p = m.positions;
      let mnx = Infinity, mxx = -Infinity, mny = Infinity, mxy = -Infinity, mnz = Infinity, mxz = -Infinity;
      for (let i = 0; i < p.length; i += 3) {
        if (p[i] < mnx) mnx = p[i]; if (p[i] > mxx) mxx = p[i];
        if (p[i + 1] < mny) mny = p[i + 1]; if (p[i + 1] > mxy) mxy = p[i + 1];
        if (p[i + 2] < mnz) mnz = p[i + 2]; if (p[i + 2] > mxz) mxz = p[i + 2];
      }
      if (Math.max(mxx - mnx, mxy - mny, mxz - mnz) < 1e-4) {
        p.fill(0);
        m.normals.fill(0);
        for (let i = 1; i < m.normals.length; i += 3) m.normals[i] = 1;
        collapsed++;
      }
    }
  }
  if (collapsed) console.log(`LOG [fit] actores ocultos colapsados: ${collapsed} mallas`);
  if (seq.length) seq.length = 0;
  mark('split');

  // 5. Camara fija de la celda: fitExtent = size/ppm (la escala que asume el packer del remate) y ancla = origen.
  const pkg = require('./package.cjs');
  const pose = require('./pose.cjs');
  const post = require('./post.cjs');
  const { encodePng } = require('./png.cjs');
  const samples = frames.map(fr => ({ meshes: fr.meshes, minY: 0 }));
  const cam = pkg.frameCamera(samples, { size, targetPixels, elevation, fitZoom: 1, fitExtent, warn });
  const camera = cam.camera;
  const origin = pkg.toPixel(camera, [0, 0, 0], size);
  const anchorX = Math.max(0, Math.min(size - 1, Math.round(origin[0])));
  const anchorY = Math.max(0, Math.min(size - 1, Math.round(origin[1])));
  if (process.env.SCENE_VERBOSE) {
    const yaw = DIR0_YAW, cs = Math.cos(yaw), sn = Math.sin(yaw);
    for (let mi = 0; mi < samples[0].meshes.length; mi++) {
      if (mi < 6 === false && !(matNames[samples[0].meshes[mi].materialIndex] || '').includes('f25681c0')) continue;
      const p = samples[0].meshes[mi].positions;
      let mnx = 1e9, mxx = -1e9, mny = 1e9, mxy = -1e9;
      let wmn = 1e9, wmx = -1e9, wmnY = 1e9, wmxY = -1e9, wmnZ = 1e9, wmxZ = -1e9;
      for (let i = 0; i < p.length; i += 3) {
        if (p[i] < wmn) wmn = p[i]; if (p[i] > wmx) wmx = p[i];
        if (p[i + 1] < wmnY) wmnY = p[i + 1]; if (p[i + 1] > wmxY) wmxY = p[i + 1];
        if (p[i + 2] < wmnZ) wmnZ = p[i + 2]; if (p[i + 2] > wmxZ) wmxZ = p[i + 2];
        const rx = p[i] * cs + p[i + 2] * sn, rz = -p[i] * sn + p[i + 2] * cs;
        const px = pkg.toPixel(camera, [rx, p[i + 1], rz], size);
        if (px[0] < mnx) mnx = px[0]; if (px[0] > mxx) mxx = px[0];
        if (px[1] < mny) mny = px[1]; if (px[1] > mxy) mxy = px[1];
      }
      console.log(`LOG [scene] mesh ${mi} mat ${matNames[samples[0].meshes[mi].materialIndex]} screen x ${mnx.toFixed(1)}..${mxx.toFixed(1)} y ${mny.toFixed(1)}..${mxy.toFixed(1)} world x ${wmn.toFixed(2)}..${wmx.toFixed(2)} y ${wmnY.toFixed(2)}..${wmxY.toFixed(2)} z ${wmnZ.toFixed(2)}..${wmxZ.toFixed(2)}`);
    }
  }
  mark('frame');

  // 6. Raster: una malla por grupo, con el render del lab (supersample + downsample + grade).
  const { createRenderer } = require('./raster.cjs');
  const meshSpec = ref.map(m => ({ indices: m.indices, uvs: m.uvs, materialIndex: m.materialIndex, doubleSided }));
  const renderer = await createRenderer({
    size, ss, meshes: meshSpec, materials,
    lighting: pose.lightingFor(lightPreset, {}),
    toneMapping: tone, exposure: 1, workers: 8,
  });
  renderer.setFrames(frames.map(fr => ({ positions: fr.meshes.map(m => m.positions), normals: fr.meshes.map(m => m.normals) })));
  const params = {
    contrast: s.contrast ?? 1, saturation: s.saturation ?? 1, brightness: s.brightness ?? 1,
    outlineMode, filterWidth: 1.5,
  };
  // Chispas y demas particulas fuera de la sombra: su proyeccion se desplaza por la altura y ensancha el lienzo
  // (el lab proyecta 1 m de altura como ~1,7 m de desplazamiento), y la mascara del juego admite 64 px.
  const shadowSkip = (opt('--shadow-skip-materials') || '').split(',').map(x => x.trim()).filter(Boolean);
  const shadowMeshes = sm => sm.meshes
    .filter(m => !shadowSkip.includes(matNames[m.materialIndex] || ''))
    .map(m => ({ positions: m.positions, index: m.indices }));
  const shadowPromise = Promise.all(samples.map(sm => pool.run('shadow', {
    size, minY: 0, fixedGround: true, anchor: [anchorX, anchorY],
    cam: { eye: camera.eye, right: camera.basis.right, up: camera.basis.up, half: camera.right },
    meshes: shadowMeshes(sm),
    dirs: [0, 1, 2, 3, 4, 5, 6, 7],
  })));
  const jobs = [];
  for (const d of dirList) for (let f = 0; f < frameCount; f++) {
    jobs.push({ frame: f, yaw: DIR0_YAW - d * DIR_STEP, yOffset: 0, dir: d, f });
  }
  const camCall = { left: camera.left, right: camera.right, top: camera.top, bottom: camera.bottom, near: camera.near, far: camera.far, viewMatrix: camera.viewMatrix };
  const procPromises = [];
  for (let r = 0; r < dirList.length; r++) {
    const bufs = await renderer.render(jobs.slice(r * frameCount, (r + 1) * frameCount), camCall);
    procPromises.push(pool.run('proc', { bufs, size, ss, params }));
  }
  await renderer.close();
  mark('raster');

  // 7. Post: legibilidad C2 (un solo pivote sobre todos los fotogramas), GIF y PNG por fotograma.
  const procs = await Promise.all(procPromises);
  let framesOut = [].concat(...procs);
  let legPivot = null;
  if (legibility === 'c2') {
    legPivot = post.legibilityPivot(framesOut);
    console.log(`LOG [fit] legibility pivot ${legPivot}`);
  }
  const delay = Math.max(20, Math.round(1000 / frameCount));
  const gifRes = await Promise.all(dirList.map((d, r) => pool.run('gifC2', {
    frames: framesOut.slice(r * frameCount, (r + 1) * frameCount), size, delay,
    pivot: legPivot === null ? undefined : legPivot,
  })));
  framesOut = [].concat(...gifRes.map(g => g.frames));
  const results = dirList.map((d, r) => ({ name: DIR_NAMES[d], index: d, buf: Buffer.from(gifRes[r].gif.buffer, gifRes[r].gif.byteOffset, gifRes[r].gif.byteLength) }));
  const firstFrames = dirList.map((d, r) => post.composite(framesOut[r * frameCount].pixels, size, size));
  const collageBuf = post.collage(firstFrames, size);
  mark('post');

  // 8. Anclas, sombras, settings y paquete.
  const renderedDirs = dirFilter;
  const anchorData = pkg.anchorData(camera, framesOut, size, frameCount, renderedDirs);
  const shadow = pkg.assembleShadows(await shadowPromise, size, frameCount);
  const shadowSize = size * 2;
  const name = path.basename(glbDir).replace(/[^a-zA-Z0-9_]+/g, '_').toLowerCase().slice(0, 20) || 'scene';
  const cHeaderText = noCHeader ? '// omitido' : pkg.cHeader(name, anchorData.anchor, anchorData.dirGroundAnchors, anchorData.dirBounds,
    shadow.shadowBounds, shadow.masks, shadowSize, size, frameCount);
  const settings = {
    name,
    model: path.basename(glbDir),
    animation: `${frameCount} GLB frames`,
    directions: DIR_NAMES,
    dirsRendered: dirList.map(d => DIR_NAMES[d]),
    framesPerDirection: frameCount,
    frameSize: `${size}x${size}`,
    spritesheet: renderedDirs ? null : { columns: frameCount, rows: 8, width: frameCount * size, height: 8 * size, alpha: true },
    anchor: anchorData.anchor,
    dirGroundAnchors: anchorData.dirGroundAnchors,
    dirBounds: anchorData.dirBounds,
    ...(renderedDirs ? {} : { shadowSize: [shadowSize, shadowSize], shadowBounds: shadow.shadowBounds }),
    ticksPerFrame: s.ticksPerFrame,
    inPlace: false,
    cameraElevationDegrees: elevation,
    contrast: s.contrast ?? 1,
    saturation: s.saturation ?? 1,
    brightness: s.brightness ?? 1,
    normalStrength: s.normalStrength ?? 0.5,
    shadowSoftness: s.shadowSoftness ?? 2,
    supersample: ss,
    legibility,
    toneMapping: tone,
    lightPreset,
    outlineMode,
    fitExtent,
    ppm,
    renderEngine: 'lab rapido (Node, software)',
  };
  const frameBufs = [].concat(...gifRes.map(g => g.pngs));
  const sheetP = renderedDirs ? Promise.resolve(null) : pool.run('pngImage', { pixels: pkg.atlasPixels(framesOut, size, frameCount), width: frameCount * size, height: 8 * size });
  const shadowP = renderedDirs ? Promise.resolve(null) : pool.run('pngImage', { pixels: shadow.atlas, width: shadow.atlasW, height: shadow.atlasH });
  const [sheetBuf, shadowBuf] = await Promise.all([sheetP, shadowP]);
  pkg.writePackage(outDir, {
    frames: framesOut, frameBufs, sheetBuf, shadowBuf, frameCount, size, results, collageBuf,
    renderedDirs, shadow: renderedDirs ? null : { shadowSize, atlas: shadow.atlas, atlasW: shadow.atlasW, atlasH: shadow.atlasH },
    cHeaderText, settings,
  });
  mark('write');
  await pool.close();

  console.log(`FIT ${JSON.stringify({ extent: cam.fit.extent, fitExtent: cam.fit.fitExtent, half: cam.fit.half, anchor: [anchorX, anchorY] })}`);
  console.log(`package written to ${outDir}`);
  if (timing) {
    const total = Object.values(T).reduce((a, b) => a + b, 0);
    console.log('TIMING ' + Object.entries(T).map(([k, v]) => `${k}=${v.toFixed(0)}ms`).join(' ') + ` total=${total.toFixed(0)}ms`);
  }
}

main().catch(e => { console.error(e); process.exit(1); });
