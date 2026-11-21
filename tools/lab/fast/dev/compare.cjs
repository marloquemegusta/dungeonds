// Banco de pruebas de desarrollo: rasteriza un fixture volcado por ref_dump.cjs y lo compara con el RGBA crudo del lab.
// uso: node compare.cjs <fixtureDir> [--frames 0,1,..] [--out <dir>] [--tex tex_0.rgba]
// Metricas: IoU del alfa (binarizado en 128), error medio abs RGB en pixeles opacos (ambos alfa>=128), p99, y tiempo.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { createRenderer, DEBUG } = require('../raster.cjs');
for (const a of process.argv) { const m = /^--dbg-(\w+)=(.*)$/.exec(a); if (m) DEBUG[m[1]] = isNaN(+m[2]) ? m[2] : +m[2]; }
if (process.argv.includes('--dbg-noMip')) DEBUG.noMip = true;
const PATS = { A: [[0.375, 0.125], [0.875, 0.375], [0.125, 0.625], [0.625, 0.875]], B: [[0.25, 0.25], [0.75, 0.25], [0.25, 0.75], [0.75, 0.75]], C: [[0.125, 0.375], [0.375, 0.875], [0.625, 0.125], [0.875, 0.625]], D: [[0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5]] };
const pArg = process.argv.find(a => a.startsWith('--pattern='));
if (pArg) DEBUG.msaaPattern = PATS[pArg.split('=')[1]];
if (process.argv.includes('--dbg-noTone')) DEBUG.noTone = true;

const dir = process.argv[2];
const arg = (n) => { const i = process.argv.indexOf(n); return i >= 0 ? process.argv[i + 1] : undefined; };
const meta = JSON.parse(fs.readFileSync(path.join(dir, 'meta.json'), 'utf8'));
const F = meta.frameCount, nv = meta.totalVerts, W = meta.size * meta.ss;
const frameList = arg('--frames') ? arg('--frames').split(',').map(Number) : Array.from({ length: F }, (_, i) => i);
const outDir = arg('--out');
const texFile = arg('--tex') || 'tex_0.rgba';

function f32(buf, off, n) { return new Float32Array(buf.buffer, buf.byteOffset + off, n); }
const posAll = fs.readFileSync(path.join(dir, 'frames_pos.bin'));
const norAll = fs.readFileSync(path.join(dir, 'frames_nor.bin'));
const posF = new Float32Array(posAll.buffer, posAll.byteOffset, posAll.length / 4);
const norF = new Float32Array(norAll.buffer, norAll.byteOffset, norAll.length / 4);

// Mallas: una por parte; las posiciones de la parte son el rango [vbase, vbase+vcount) de la geometria global.
const meshes = meta.parts.map(p => {
  // Geometria sin indice: los triangulos son consecutivos (rango start..start+icount).
  let indices;
  if (p.index) {
    const idxAll = Buffer.from(p.index, 'base64');
    const all = new Uint32Array(idxAll.buffer, idxAll.byteOffset, idxAll.length / 4);
    indices = Uint32Array.from(all.subarray(p.start, p.start + p.icount));
  } else {
    indices = Uint32Array.from({ length: p.icount }, (_, i) => p.start + i);
  }
  let uvs = null;
  if (p.uv) { const u = Buffer.from(p.uv, 'base64'); uvs = new Float32Array(u.buffer.slice(u.byteOffset, u.byteOffset + u.length)); }
  return { indices, uvs, materialIndex: p.mat, doubleSided: p.side === 2, vbase: p.vbase, vcount: p.vcount };
});
// Texturas: RGBA ya decodificados (Python/PIL -> *.rgba, tamanos en texinfo.json), una por material y tipo de mapa.
const texInfo = fs.existsSync(path.join(dir, 'texinfo.json')) ? JSON.parse(fs.readFileSync(path.join(dir, 'texinfo.json'), 'utf8')) : {};
const texCache = new Map();
function loadTex(t) {
  if (!t || !t.file) return null;
  if (texCache.has(t.file)) return texCache.get(t.file);
  const rgba = t.file.replace(/\.bin$/, '.rgba');
  const [w, h] = texInfo[t.file] || [2048, 2048];
  const data = fs.readFileSync(path.join(dir, rgba));
  const obj = { width: w, height: h, data: new Uint8Array(data.buffer, data.byteOffset, data.length), colorSpace: t.colorSpace || '', flipY: t.flipY, wrapS: t.wrapS, wrapT: t.wrapT };
  texCache.set(t.file, obj);
  return obj;
}
const materials = meta.mats.map(m => ({ color: m.color, roughness: m.roughness, metalness: m.metalness, emissive: m.emissive, emissiveIntensity: m.emissiveIntensity, normalScale: m.normalScale, map: loadTex(m.map), normalMap: loadTex(m.normalMap), emissiveMap: loadTex(m.emissiveMap) }));
const frames = [];
for (let f = 0; f < F; f++) {
  const positions = [], normals = [];
  for (const m of meshes) {
    const base = (f * nv + m.vbase) * 3;
    positions.push(posF.slice(base, base + m.vcount * 3));
    normals.push(norF.slice(base, base + m.vcount * 3));
  }
  frames.push({ positions, normals });
}
const L = meta.lights;
const lighting = { key: { color: L.key.color, intensity: L.key.intensity, position: L.key.position },
  fill: { color: L.fill.color, intensity: L.fill.intensity, position: L.fill.position },
  rim: { color: L.rim.color, intensity: L.rim.intensity, position: L.rim.position },
  ambient: { color: L.world.color, intensity: L.world.intensity }, castShadow: true };
const cam = Object.assign({}, meta.camera, { projectionMatrix: meta.camera.proj, viewMatrix: meta.camera.view });

(async () => {
  const r = await createRenderer({ size: meta.size, ss: meta.ss, meshes: meshes.map(({ indices, uvs, materialIndex, doubleSided }) => ({ indices, uvs, materialIndex, doubleSided })),
    materials, lighting, toneMapping: meta.toneMapping === 6 ? 'agx' : 'neutral', exposure: meta.exposure, workers: 1,
    workers: Number((process.argv.find(a => a.startsWith('--workers=')) || '--workers=1').split('=')[1]),
    debug: { noShadow: process.argv.includes('--noshadow'), noMap: process.argv.includes('--nomap'), noNormalMap: process.argv.includes('--nonormal'), shadowFront: process.argv.includes('--shadowfront') } });
  r.setFrames(frames);
  let jobs = frameList.map(f => { const c = meta.calls[f]; return { frame: f % F, yaw: c.yaw, yOffset: c.offY }; });
  if (process.argv.includes('--bench')) { // 64 imagenes: 8 direcciones x 8 fotogramas (rotacion sintetica de 45 grados por direccion)
    jobs = []; for (let d = 0; d < 8; d++) for (let f = 0; f < F; f++) jobs.push({ frame: f, yaw: 2.356 - d * Math.PI / 4, yOffset: meta.calls[f].offY }); }
  const t0 = process.hrtime.bigint();
  const imgs = await r.render(jobs, cam);
  if (process.argv.includes('--bench')) { console.log(JSON.stringify({ bench_images: jobs.length, ms: +(Number(process.hrtime.bigint() - t0) / 1e6).toFixed(0) })); await r.close(); return; }
  const ms = Number(process.hrtime.bigint() - t0) / 1e6;
  await r.close();
  let report = [];
  for (let k = 0; k < frameList.length; k++) {
    const ref = new Uint8Array(fs.readFileSync(path.join(dir, `raw_${frameList[k]}.bin`)).buffer);
    const refBuf = fs.readFileSync(path.join(dir, `raw_${frameList[k]}.bin`));
    const R = new Uint8Array(refBuf.buffer, refBuf.byteOffset, refBuf.length);
    const O = imgs[k];
    let inter = 0, uni = 0, sumErr = 0, nOp = 0; const errs = [];
    for (let p = 0; p < W * W; p++) {
      const ra = R[p * 4 + 3] >= 128, oa = O[p * 4 + 3] >= 128;
      if (ra && oa) inter++;
      if (ra || oa) uni++;
      if (ra && oa) {
        for (let c = 0; c < 3; c++) { const e = Math.abs(R[p * 4 + c] - O[p * 4 + c]); sumErr += e; errs.push(e); }
        nOp++;
      }
    }
    errs.sort((a, b) => a - b);
    const p99 = errs.length ? errs[Math.floor(errs.length * 0.99)] : 0;
    // Desplazamiento: mejor IoU del alfa con la imagen movida (dx,dy) px (diagnostico de alineacion).
    let best = { d: null, iou: -1 };
    for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
      let it = 0, un = 0;
      for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) {
        const xs = x - dx, ys = y - dy; const oa = (xs >= 0 && xs < W && ys >= 0 && ys < W) ? O[(ys * W + xs) * 4 + 3] >= 128 : false;
        const ra = R[(y * W + x) * 4 + 3] >= 128;
        if (ra && oa) it++; if (ra || oa) un++;
      }
      const iou = it / Math.max(1, un); if (iou > best.iou) best = { d: [dx, dy], iou: +iou.toFixed(4) };
    }
    report.push({ best_shift: best, frame: frameList[k], iouAlpha: +(inter / Math.max(1, uni)).toFixed(4), meanAbsRGB: +(sumErr / Math.max(1, nOp * 3)).toFixed(3), p99 });
    if (outDir) {
      fs.mkdirSync(outDir, { recursive: true });
      // Lado a lado: referencia | nuestro (4x NEAREST via escritura de RGBA crudo en PPM-like binario); aqui solo se guarda el crudo.
      fs.writeFileSync(path.join(outDir, `ours_${frameList[k]}.bin`), Buffer.from(O.buffer, O.byteOffset, O.length));
    }
  }
  console.log(JSON.stringify({ size: W, frames: report, renderMs: +ms.toFixed(1), perImageMs: +(ms / frameList.length).toFixed(1) }));
})().catch(e => { console.error(e); process.exit(1); });
