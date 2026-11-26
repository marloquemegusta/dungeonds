// Exportador rapido de PROPS: sustituye a tools/lab/export_map_package_headless.cjs (lab web + Playwright) para las
// piezas de tools/props/prerender_props.py. Misma entrada y mismos ficheros de salida que consume el prerender:
//   world.png, occlusion.png, occlusion_depth.png, collision.png, map_settings.json
// sin navegador: GLB con tools/lab/glb_loader_minimal.js y color con raster.cjs (el rasterizador de los personajes).
//
// usage: node export_prop_fast.cjs <model.glb> <settings.json> <out_dir> [--legibility anterior|c2] [--tone agx|neutral|none] [--timing]
//
// Reproduce loadMapFile + renderMap + renderMapGroundDepth + buildMapCollisionGrid del lab web:
//   * eje Z arriba (rotacion X -90), suelo = franja de 5 cm con mas area horizontal, modelo centrado en X/Z;
//   * el grupo del mapa se escala para que el ancho proyectado valga (mapW / 48) * 1,8 m (sync3DRelativeScale con el
//     heroe de 1,8 m y la resolucion por defecto 48): fija el frustum de sombra de +-5 m, la altura minima de oclusor
//     (0,25) y la losa de colision (0,30..1,20), que el lab mide en unidades del mundo ya escaladas;
//   * camara ortografica que enmarca la caja del modelo (mapW px de ancho, alto segun la proyeccion), luces del preset,
//     sin supersample; con c2 contraste 1.0; el tone mapping del lab en este camino lo fija --tone (ver abajo);
//   * profundidad: pasada sin multimuestreo con la superficie mas cercana de cada pixel (R,G = Y de suelo en pixeles
//     del mapa, B = 255 si la superficie esta a mas de 0,25 de altura);
//   * colision: rejilla de 4 px (suelo / losa de cuerpo / mayor region caminable).
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const GLB = require('../glb_loader_minimal.js');
const { decodePng, encodePng } = require('./png.cjs');
// zf del lab: contraste alrededor de 128 y saturacion alrededor de la luma Rec.709 (alfa intacto).
function gradeContrastSaturation(e, contrast, saturation) {
  const r = new Uint8ClampedArray(e.length);
  for (let i = 0; i < e.length; i += 4) {
    if (e[i + 3] === 0) { r[i + 3] = 0; continue; }
    let a = e[i], o = e[i + 1], s = e[i + 2];
    a = (a - 128) * contrast + 128; o = (o - 128) * contrast + 128; s = (s - 128) * contrast + 128;
    const c = 0.2126 * a + 0.7152 * o + 0.0722 * s;
    a = c + (a - c) * saturation; o = c + (o - c) * saturation; s = c + (s - c) * saturation;
    r[i] = a; r[i + 1] = o; r[i + 2] = s; r[i + 3] = e[i + 3];
  }
  return r;
}

const argv = process.argv.slice(2);
const opt = n => { const i = argv.indexOf(n); return i >= 0 ? argv[i + 1] : undefined; };
const VALUE_FLAGS = new Set(['--legibility', '--tone']);
const pos = argv.filter((a, i) => !a.startsWith('--') && !(i > 0 && VALUE_FLAGS.has(argv[i - 1])));
const [modelPath, settingsPath, outDir] = pos.map(p => p && path.resolve(p));
if (!modelPath || !settingsPath || !outDir) {
  console.error('usage: node export_prop_fast.cjs <model.glb> <settings.json> <out_dir> [--legibility anterior|c2] [--tone agx|neutral|none]');
  process.exit(2);
}
if (!/\.glb$/i.test(modelPath)) { console.error('export_prop_fast: solo GLB (usa DS_FAST_RENDER=0 para FBX)'); process.exit(2); }

const settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
if (opt('--legibility')) settings.legibility = opt('--legibility');
if (settings.legibility === 'c2') settings.contrast = 1.0;
const MAP_W = parseInt(settings.width, 10) || 768;
const ELEV = ((Math.max(1, parseFloat(settings.cameraElevationDegrees) || 30)) * Math.PI) / 180;
const CONTRAST = parseFloat(settings.contrast) || 1.5;
const SATURATION = parseFloat(settings.saturation) || 1.15;
const BRIGHTNESS = parseFloat(settings.brightness) || 1.0;
const lightPreset = settings.lighting?.preset || 'neutral';
const lightOverrides = {};
for (const k of ['key', 'fill', 'rim', 'world']) if (settings.lighting?.[k] !== undefined) lightOverrides[k] = settings.lighting[k];
// Luz de sala del ARPG (tools/arpg_light_rooms.json): colores, direccion (fromDeg) y elevacion tal cual las entiende pose.lightingFor.
for (const k of ['keyColor', 'fillColor', 'rimColor', 'worldColor', 'fromDeg', 'elevation', 'shadowElevation']) if (settings.lighting?.[k] !== undefined) lightOverrides[k] = settings.lighting[k];
const toneOpt = opt('--tone') || 'agx';   // el lab de mapas no aplica el tone mapping de c2: queda el AgX inicial del renderer
const AZIMUTH = Math.PI / 4;
const MIN_OCCLUDER = 0.25;            // MAP_OCCLUDER_MIN_HEIGHT
const SLAB_MIN = 0.30, SLAB_MAX = 1.20;   // MAP_BODY_SLAB_*
const NONE = 0xFFFF;
const timing = process.argv.includes('--timing');
const T = {}; let t0 = process.hrtime.bigint();
const mark = l => { const n = process.hrtime.bigint(); T[l] = Number(n - t0) / 1e6; t0 = n; };

const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = a => { const l = Math.hypot(a[0], a[1], a[2]); return [a[0] / l, a[1] / l, a[2] / l]; };
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];

function bbox(p) {
  let mnx = Infinity, mny = Infinity, mnz = Infinity, mxx = -Infinity, mxy = -Infinity, mxz = -Infinity;
  for (let i = 0; i < p.length; i += 3) {
    if (p[i] < mnx) mnx = p[i]; if (p[i] > mxx) mxx = p[i];
    if (p[i + 1] < mny) mny = p[i + 1]; if (p[i + 1] > mxy) mxy = p[i + 1];
    if (p[i + 2] < mnz) mnz = p[i + 2]; if (p[i + 2] > mxz) mxz = p[i + 2];
  }
  return { min: [mnx, mny, mnz], max: [mxx, mxy, mxz] };
}
function corners(b) {
  const out = [];
  for (const x of [b.min[0], b.max[0]]) for (const y of [b.min[1], b.max[1]]) for (const z of [b.min[2], b.max[2]]) out.push([x, y, z]);
  return out;
}

// JPEG embebido -> PNG con Pillow (el rasterizador solo decodifica PNG); mismos pixeles que el navegador salvo +-1.
function jpegToPng(bytes) {
  const tmp = path.join(require('node:os').tmpdir(), `prop_fast_${process.pid}_${bytes.length}`);
  fs.writeFileSync(tmp + '.jpg', bytes);
  const py = process.env.DS_PYTHON || 'python';
  const r = require('node:child_process').spawnSync(py, ['-c', 'import sys;from PIL import Image;Image.open(sys.argv[1]).convert("RGBA").save(sys.argv[2])', tmp + '.jpg', tmp + '.png']);
  if (r.status !== 0) throw new Error('no se pudo decodificar el JPEG con Pillow: ' + String(r.stderr));
  const out = fs.readFileSync(tmp + '.png');
  fs.unlinkSync(tmp + '.jpg'); fs.unlinkSync(tmp + '.png');
  return out;
}

async function main() {
  // 1. GLB -> una sola malla con grupos por material (como buildThreeMeshFromGLB).
  const buf = fs.readFileSync(modelPath);
  const raw = GLB.parseGLBToMeshData(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength));
  const P = raw.positions, N = raw.normals, IDX = raw.indices;
  const nVert = P.length / 3;

  // Eje Z arriba: rotation.x = -PI/2 => (x, y, z) -> (x, z, -y).
  let box = bbox(P);
  const size = [0, 1, 2].map(i => box.max[i] - box.min[i]);
  if (size[2] < Math.min(size[0], size[1]) * 0.8) {
    for (let i = 0; i < P.length; i += 3) { const y = P[i + 1], z = P[i + 2]; P[i + 1] = z; P[i + 2] = -y; }
    for (let i = 0; i < N.length; i += 3) { const y = N[i + 1], z = N[i + 2]; N[i + 1] = z; N[i + 2] = -y; }
    box = bbox(P);
  }

  // Nivelado: franja de 5 cm (triangulos horizontales por debajo del 55 % de la altura) con mas area.
  const midY = box.min[1] + (box.max[1] - box.min[1]) * 0.55;
  const heightArea = new Map();
  for (let t = 0; t + 2 < IDX.length; t += 3) {
    const a = IDX[t] * 3, b = IDX[t + 1] * 3, c = IDX[t + 2] * 3;
    const e1 = [P[b] - P[a], P[b + 1] - P[a + 1], P[b + 2] - P[a + 2]];
    const e2 = [P[c] - P[a], P[c + 1] - P[a + 1], P[c + 2] - P[a + 2]];
    const cr = cross(e1, e2);
    const len = Math.hypot(cr[0], cr[1], cr[2]);
    const area = 0.5 * len;
    if (area <= 1e-6) continue;
    const triY = (P[a + 1] + P[b + 1] + P[c + 1]) / 3;
    if (Math.abs(cr[1] / len) > 0.8 && triY <= midY) {
      const bucket = Math.round(triY * 20) / 20;
      heightArea.set(bucket, (heightArea.get(bucket) || 0) + area);
    }
  }
  let floorY = box.min[1], maxArea = -1;
  for (const [bucket, a] of heightArea) if (a > maxArea) { maxArea = a; floorY = bucket; }
  const cx = (box.min[0] + box.max[0]) / 2, cz = (box.min[2] + box.max[2]) / 2;
  for (let i = 0; i < P.length; i += 3) { P[i] -= cx; P[i + 1] -= floorY; P[i + 2] -= cz; }
  box = bbox(P);

  // Escala del grupo (sync3DRelativeScale): ancho proyectado a elevacion 30 -> (mapW / 48) * 1,8 m.
  {
    const el = (30 * Math.PI) / 180;
    const toCam = norm([Math.cos(el) * Math.cos(AZIMUTH), Math.sin(el), -Math.cos(el) * Math.sin(AZIMUTH)]);
    const r = norm(cross([0, 1, 0], toCam));
    let mnU = Infinity, mxU = -Infinity;
    for (const c of corners(box)) { const u = dot(c, r); if (u < mnU) mnU = u; if (u > mxU) mxU = u; }
    const baseProjW = Math.max(0.1, mxU - mnU);
    const scale = ((MAP_W / 48) * 1.8) / baseProjW;
    for (let i = 0; i < P.length; i += 3) { P[i] *= scale; P[i + 1] *= scale; P[i + 2] *= scale; }
    box = bbox(P);
  }
  mark('load');

  // 2. Camara ortografica de renderMap.
  const toCamera = norm([Math.cos(ELEV) * Math.cos(AZIMUTH), Math.sin(ELEV), -Math.cos(ELEV) * Math.sin(AZIMUTH)]);
  const right = norm(cross([0, 1, 0], toCamera));
  const up = norm(cross(toCamera, right));
  let minU = Infinity, maxU = -Infinity, minV = Infinity, maxV = -Infinity;
  for (const c of corners(box)) {
    const u = dot(c, right), v = dot(c, up);
    if (u < minU) minU = u; if (u > maxU) maxU = u;
    if (v < minV) minV = v; if (v > maxV) maxV = v;
  }
  const projW = Math.max(0.1, maxU - minU), projH = Math.max(0.1, maxV - minV);
  const mapH = Math.max(128, Math.round(MAP_W * (projH / projW)));
  const midU = (minU + maxU) / 2, midV = (minV + maxV) / 2;
  const center = [right[0] * midU + up[0] * midV, right[1] * midU + up[1] * midV, right[2] * midU + up[2] * midV];
  const eye = [center[0] + toCamera[0] * 300, center[1] + toCamera[1] * 300, center[2] + toCamera[2] * 300];
  const camera = {
    left: -projW / 2, right: projW / 2, top: projH / 2, bottom: -projH / 2, near: 0.1, far: 1000,
    viewMatrix: [
      right[0], up[0], toCamera[0], 0,
      right[1], up[1], toCamera[1], 0,
      right[2], up[2], toCamera[2], 0,
      -dot(right, eye), -dot(up, eye), -dot(toCamera, eye), 1,
    ],
  };

  // 3. Color: un grupo (malla) por material, mismos materiales que setupModelMaterials del lab para mapas.
  const matInfos = raw.materials;
  const materials = matInfos.map(m => {
    let tex = null;
    if (m.imageBytes) {
      let bytes = Buffer.from(m.imageBytes);
      if (bytes[0] === 0xff && bytes[1] === 0xd8) bytes = jpegToPng(bytes);   // el lab rapido solo lee PNG
      const img = decodePng(bytes);
      tex = { width: img.width, height: img.height, data: img.data, colorSpace: 'srgb', flipY: false, wrapS: 1000, wrapT: 1000 };
    }
    return {
      color: tex ? [1, 1, 1] : (m.color || [0.8, 0.8, 0.8]).slice(0, 3),
      roughness: 0.85, metalness: 0.05,
      emissive: m.emissive ? m.emissive.slice(0, 3) : [0, 0, 0], emissiveIntensity: m.emissive ? 1.0 : 0.0,
      normalScale: 0,
      map: tex, normalMap: null,
    };
  });
  const meshes = [], positions = [], normals = [];
  for (const g of raw.groups) {
    const remap = new Map();
    const idx = new Uint32Array(g.count);
    for (let k = 0; k < g.count; k++) {
      const gi = IDX[g.start + k];
      let li = remap.get(gi);
      if (li === undefined) { li = remap.size; remap.set(gi, li); }
      idx[k] = li;
    }
    const n = remap.size;
    const gp = new Float32Array(n * 3), gn = new Float32Array(n * 3), gu = new Float32Array(n * 2);
    let li = 0;
    for (const gi of remap.keys()) {
      gp[li * 3] = P[gi * 3]; gp[li * 3 + 1] = P[gi * 3 + 1]; gp[li * 3 + 2] = P[gi * 3 + 2];
      gn[li * 3] = N[gi * 3]; gn[li * 3 + 1] = N[gi * 3 + 1]; gn[li * 3 + 2] = N[gi * 3 + 2];
      gu[li * 2] = raw.uvs[gi * 2]; gu[li * 2 + 1] = raw.uvs[gi * 2 + 1];
      li++;
    }
    meshes.push({ indices: idx, uvs: gu, materialIndex: g.materialIndex, doubleSided: false });
    positions.push(gp); normals.push(gn);
  }
  const pose = require('./pose.cjs');
  const { createRenderer } = require('./raster.cjs');
  const lighting = pose.lightingFor(lightPreset, lightOverrides);
  if (settings.shadows === false) lighting.castShadow = false;
  const renderer = await createRenderer({
    size: MAP_W, height: mapH, ss: 1, meshes, materials, lighting,
    toneMapping: toneOpt === 'neutral' ? 'neutral' : toneOpt === 'agx' ? 'agx' : 'neutral', allowAgx: true, noTone: toneOpt === 'none', exposure: 1, workers: 1,
  });
  renderer.setFrames([{ positions, normals }]);
  const [img] = await renderer.render([{ frame: 0, yaw: 0, yOffset: 0 }], camera);
  await renderer.close();
  // El lab limpia a negro con alfa 1: el color premultiplicado sobre negro, opaco.
  const rgba = new Uint8ClampedArray(img);
  for (let i = 3; i < rgba.length; i += 4) rgba[i] = 255;
  let graded = gradeContrastSaturation(rgba, CONTRAST, SATURATION);
  if (BRIGHTNESS !== 1.0) {
    for (let i = 0; i < graded.length; i += 4) { graded[i] *= BRIGHTNESS; graded[i + 1] *= BRIGHTNESS; graded[i + 2] *= BRIGHTNESS; }
  }
  mark('color');

  // 4. Profundidad (suelo bajo cada superficie), una muestra por pixel, superficie mas cercana.
  const ppuV = mapH / projH;
  const depth = new Uint16Array(MAP_W * mapH).fill(NONE);
  {
    const zbuf = new Float32Array(MAP_W * mapH).fill(Infinity);
    const val = new Int32Array(MAP_W * mapH).fill(-1);   // codigo (my) o -1 (sin oclusor)
    const proj = (() => {
      const l = camera.left, r = camera.right, b = camera.bottom, t = camera.top, n = camera.near, f = camera.far;
      return { sx: 2 / (r - l), tx: -(r + l) / (r - l), sy: 2 / (t - b), ty: -(t + b) / (t - b), sz: -2 / (f - n), tz: -(f + n) / (f - n) };
    })();
    const vm = camera.viewMatrix;
    for (let m = 0; m < meshes.length; m++) {
      const p = positions[m], idx = meshes[m].indices;
      const nv = p.length / 3;
      const sx = new Float64Array(nv), sy = new Float64Array(nv), sz = new Float64Array(nv), gv = new Float64Array(nv), wy = new Float64Array(nv);
      for (let i = 0; i < nv; i++) {
        const x = p[i * 3], y = p[i * 3 + 1], z = p[i * 3 + 2];
        const vx = vm[0] * x + vm[4] * y + vm[8] * z + vm[12];
        const vy = vm[1] * x + vm[5] * y + vm[9] * z + vm[13];
        const vz = vm[2] * x + vm[6] * y + vm[10] * z + vm[14];
        sx[i] = ((vx * proj.sx + proj.tx) * 0.5 + 0.5) * MAP_W;
        sy[i] = (0.5 - (vy * proj.sy + proj.ty) * 0.5) * mapH;
        sz[i] = vz * proj.sz + proj.tz;
        gv[i] = x * up[0] + z * up[2];
        wy[i] = y;
      }
      for (let t = 0; t + 2 < idx.length; t += 3) {
        const i0 = idx[t], i1 = idx[t + 1], i2 = idx[t + 2];
        const ax = sx[i0], ay = sy[i0], bx = sx[i1], by = sy[i1], cx_ = sx[i2], cy_ = sy[i2];
        const area = (bx - ax) * (cy_ - ay) - (cx_ - ax) * (by - ay);
        if (area === 0) continue;
        if (-area <= 0) continue;                       // FrontSide: cara trasera descartada
        const inv = 1 / area;
        const minx = Math.max(0, Math.floor(Math.min(ax, bx, cx_) - 0.5)), maxx = Math.min(MAP_W - 1, Math.ceil(Math.max(ax, bx, cx_) - 0.5));
        const miny = Math.max(0, Math.floor(Math.min(ay, by, cy_) - 0.5)), maxy = Math.min(mapH - 1, Math.ceil(Math.max(ay, by, cy_) - 0.5));
        for (let y = miny; y <= maxy; y++) {
          const py = y + 0.5;
          for (let x = minx; x <= maxx; x++) {
            const px = x + 0.5;
            const w0 = ((bx - px) * (cy_ - py) - (cx_ - px) * (by - py)) * inv;
            const w1 = ((cx_ - px) * (ay - py) - (ax - px) * (cy_ - py)) * inv;
            const w2 = 1 - w0 - w1;
            if (w0 < -1e-9 || w1 < -1e-9 || w2 < -1e-9) continue;
            const z = w0 * sz[i0] + w1 * sz[i1] + w2 * sz[i2];
            const q = y * MAP_W + x;
            if (z >= zbuf[q]) continue;
            zbuf[q] = z;
            const h = w0 * wy[i0] + w1 * wy[i1] + w2 * wy[i2];
            if (h > MIN_OCCLUDER) {
              const g = w0 * gv[i0] + w1 * gv[i1] + w2 * gv[i2];
              let my = Math.floor((maxV - g) * ppuV + 0.5);
              my = my < 0 ? 0 : my > 65534 ? 65534 : my;
              val[q] = my;
            } else val[q] = -1;
          }
        }
      }
    }
    for (let q = 0; q < val.length; q++) if (val[q] >= 0) depth[q] = val[q];
  }
  mark('depth');

  // 5. Rejilla de colision de 4 px (buildMapCollisionGrid).
  const CELL = 4;
  const gw = Math.ceil(MAP_W / CELL), gh = Math.ceil(mapH / CELL);
  const grid = new Uint8Array(gw * gh);
  let hasFloor = false;
  const toGrid = (x, z) => {
    const u = x * right[0] + z * right[2], v = x * up[0] + z * up[2];
    return { gx: ((u - minU) / projW * MAP_W) / CELL, gy: ((maxV - v) / projH * mapH) / CELL };
  };
  const mark1 = (x, y, flag) => { if (x >= 0 && x < gw && y >= 0 && y < gh) grid[y * gw + x] |= flag; };
  const segment = (a, b, flag) => {
    const steps = Math.max(1, Math.ceil(Math.max(Math.abs(b.gx - a.gx), Math.abs(b.gy - a.gy)) * 2));
    for (let s = 0; s <= steps; s++) { const t = s / steps; mark1(Math.floor(a.gx + (b.gx - a.gx) * t), Math.floor(a.gy + (b.gy - a.gy) * t), flag); }
  };
  const polygon = (pts, flag) => {
    for (let i = 0; i < pts.length; i++) segment(pts[i], pts[(i + 1) % pts.length], flag);
    for (let i = 1; i + 1 < pts.length; i++) {
      const p0 = pts[0], p1 = pts[i], p2 = pts[i + 1];
      const denom = (p1.gy - p2.gy) * (p0.gx - p2.gx) + (p2.gx - p1.gx) * (p0.gy - p2.gy);
      if (Math.abs(denom) < 1e-6) continue;
      const mnx = Math.max(0, Math.floor(Math.min(p0.gx, p1.gx, p2.gx))), mxx = Math.min(gw - 1, Math.floor(Math.max(p0.gx, p1.gx, p2.gx)));
      const mny = Math.max(0, Math.floor(Math.min(p0.gy, p1.gy, p2.gy))), mxy = Math.min(gh - 1, Math.floor(Math.max(p0.gy, p1.gy, p2.gy)));
      for (let y = mny; y <= mxy; y++) {
        const cy = y + 0.5;
        for (let x = mnx; x <= mxx; x++) {
          const cxx = x + 0.5;
          const w0 = ((p1.gy - p2.gy) * (cxx - p2.gx) + (p2.gx - p1.gx) * (cy - p2.gy)) / denom;
          const w1 = ((p2.gy - p0.gy) * (cxx - p2.gx) + (p0.gx - p2.gx) * (cy - p2.gy)) / denom;
          if (w0 >= 0 && w1 >= 0 && 1 - w0 - w1 >= 0) grid[y * gw + x] |= flag;
        }
      }
    }
  };
  const triangle = (p0, p1, p2, flag) => {
    const mnx = Math.max(0, Math.floor(Math.min(p0.gx, p1.gx, p2.gx))), mxx = Math.min(gw - 1, Math.ceil(Math.max(p0.gx, p1.gx, p2.gx)));
    const mny = Math.max(0, Math.floor(Math.min(p0.gy, p1.gy, p2.gy))), mxy = Math.min(gh - 1, Math.ceil(Math.max(p0.gy, p1.gy, p2.gy)));
    const denom = (p1.gy - p2.gy) * (p0.gx - p2.gx) + (p2.gx - p1.gx) * (p0.gy - p2.gy);
    if (Math.abs(denom) < 1e-5) return;
    const invD = 1 / denom;
    for (let y = mny; y <= mxy; y++) for (let x = mnx; x <= mxx; x++) {
      const cxx = x + 0.5, cy = y + 0.5;
      const w0 = ((p1.gy - p2.gy) * (cxx - p2.gx) + (p2.gx - p1.gx) * (cy - p2.gy)) * invD;
      const w1 = ((p2.gy - p0.gy) * (cxx - p2.gx) + (p0.gx - p2.gx) * (cy - p2.gy)) * invD;
      const w2 = 1 - w0 - w1;
      if (w0 >= -1e-4 && w1 >= -1e-4 && w2 >= -1e-4) grid[y * gw + x] |= flag;
    }
  };
  const clipY = (poly, limit, keepAbove) => {
    const out = [];
    for (let i = 0; i < poly.length; i++) {
      const cur = poly[i], prev = poly[(i + poly.length - 1) % poly.length];
      const curIn = keepAbove ? cur[1] >= limit : cur[1] <= limit;
      const prevIn = keepAbove ? prev[1] >= limit : prev[1] <= limit;
      if (curIn !== prevIn) {
        const t = (limit - prev[1]) / (cur[1] - prev[1]);
        out.push([prev[0] + t * (cur[0] - prev[0]), limit, prev[2] + t * (cur[2] - prev[2])]);
      }
      if (curIn) out.push(cur.slice());
    }
    return out;
  };
  for (let t = 0; t + 2 < IDX.length; t += 3) {
    const a = IDX[t] * 3, b = IDX[t + 1] * 3, c = IDX[t + 2] * 3;
    const v0 = [P[a], P[a + 1], P[a + 2]], v1 = [P[b], P[b + 1], P[b + 2]], v2 = [P[c], P[c + 1], P[c + 2]];
    const cr = cross([v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]], [v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]]);
    const len = Math.hypot(cr[0], cr[1], cr[2]);
    if (0.5 * len <= 1e-6) continue;
    const ny = cr[1] / len;
    const midYt = (v0[1] + v1[1] + v2[1]) / 3;
    const mnY = Math.min(v0[1], v1[1], v2[1]), mxY = Math.max(v0[1], v1[1], v2[1]);
    if (Math.abs(ny) > 0.70 && Math.abs(midYt) <= 0.28 && mxY < 0.35) {
      hasFloor = true;
      triangle(toGrid(v0[0], v0[2]), toGrid(v1[0], v1[2]), toGrid(v2[0], v2[2]), 1);
    } else if (mxY > SLAB_MIN && mnY < SLAB_MAX) {
      let poly = clipY([v0, v1, v2], SLAB_MIN, true);
      if (poly.length >= 3) poly = clipY(poly, SLAB_MAX, false);
      if (poly.length >= 2) polygon(poly.map(v => toGrid(v[0], v[2])), 2);
    }
  }
  if (hasFloor) {   // keepLargestWalkableRegion
    const label = new Int32Array(gw * gh).fill(-1);
    const stack = new Int32Array(gw * gh);
    let bestLabel = -1, bestSize = 0, next = 0;
    for (let start = 0; start < gw * gh; start++) {
      if (label[start] !== -1 || grid[start] !== 1) continue;
      let top = 0, sz = 0;
      stack[top++] = start; label[start] = next;
      while (top > 0) {
        const i = stack[--top]; sz++;
        const x = i % gw, y = (i / gw) | 0;
        for (const nb of [x > 0 ? i - 1 : -1, x + 1 < gw ? i + 1 : -1, y > 0 ? i - gw : -1, y + 1 < gh ? i + gw : -1]) {
          if (nb >= 0 && label[nb] === -1 && grid[nb] === 1) { label[nb] = next; stack[top++] = nb; }
        }
      }
      if (sz > bestSize) { bestSize = sz; bestLabel = next; }
      next++;
    }
    for (let i = 0; i < gw * gh; i++) if (grid[i] === 1 && label[i] !== bestLabel) grid[i] |= 2;
  }
  mark('collision');

  // 6. Salida (mismos nombres y modos que el paquete del lab).
  fs.mkdirSync(outDir, { recursive: true });
  const px = MAP_W * mapH;
  const occ = new Uint8Array(px * 4), occDepth = new Uint8Array(px * 4), col = new Uint8Array(px * 4);
  for (let i = 0; i < px; i++) {
    const d = depth[i], occluder = d !== NONE;
    occ[i * 4] = occ[i * 4 + 1] = occ[i * 4 + 2] = occluder ? 255 : 0; occ[i * 4 + 3] = 255;
    occDepth[i * 4] = occluder ? d >> 8 : 0; occDepth[i * 4 + 1] = occluder ? d & 255 : 0; occDepth[i * 4 + 2] = occluder ? 255 : 0; occDepth[i * 4 + 3] = 255;
  }
  for (let gy = 0; gy < gh; gy++) for (let gx = 0; gx < gw; gx++) {
    const v = grid[gy * gw + gx];
    if ((v & 2) !== 0 || (hasFloor && (v & 1) === 0)) continue;
    for (let y = gy * CELL; y < Math.min(mapH, gy * CELL + CELL); y++) for (let x = gx * CELL; x < Math.min(MAP_W, gx * CELL + CELL); x++) {
      const o = (y * MAP_W + x) * 4; col[o] = col[o + 1] = col[o + 2] = 255;
    }
  }
  for (let i = 3; i < col.length; i += 4) col[i] = 255;
  const out = (n, w, h, d) => fs.writeFileSync(path.join(outDir, n), encodePng(w, h, d));
  out('world.png', MAP_W, mapH, Buffer.from(graded.buffer, graded.byteOffset, graded.byteLength));
  out('occlusion.png', MAP_W, mapH, occ);
  out('occlusion_depth.png', MAP_W, mapH, occDepth);
  out('collision.png', MAP_W, mapH, col);
  fs.writeFileSync(path.join(outDir, 'map_settings.json'), JSON.stringify({
    mapName: path.basename(modelPath, path.extname(modelPath)), width: MAP_W, height: mapH, orthoScaleMeters: 38,
    pixelsPerMeter: Number((MAP_W / 38).toFixed(2)), meshScale: 24, cameraElevationDegrees: ELEV * 180 / Math.PI,
    contrast: CONTRAST, saturation: SATURATION, brightness: BRIGHTNESS,
    lighting: { preset: lightPreset }, renderEngine: 'lab rapido (Node, software)',
  }, null, 2));
  mark('write');
  console.log(`exported world.png, occlusion.png, occlusion_depth.png, collision.png at ${MAP_W}x${mapH} -> ${outDir}`);
  if (timing) console.log('TIMING ' + Object.entries(T).map(([k, v]) => `${k}=${v.toFixed(0)}ms`).join(' '));
}

main().catch(e => { console.error(e); process.exit(1); });
