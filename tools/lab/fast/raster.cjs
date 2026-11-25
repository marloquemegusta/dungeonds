// Rasterizador por software que reproduce el render WebGL del lab (Three.js r186, MeshStandardMaterial,
// luces direccionales + ambiente, sombra PCF de la luz key, tone mapping Neutral, sRGB) sin navegador.
//
// API (la consume el pipeline de P):
//   const r = await createRenderer({ size, ss, meshes, materials, lighting, toneMapping, exposure, workers });
//   r.setFrames(frames);                     // frames[f] = { positions:[Float32Array per mesh], normals:[...] } en mundo, raiz identidad
//   const bufs = await r.render(jobs, cam);  // jobs:[{frame,yaw,yOffset}] -> [Uint8ClampedArray RGBA (size*ss)^2, alfa recto, fila 0 arriba]
//   await r.close();
// meshes[m] = { indices:Uint32Array, uvs:Float32Array|null, materialIndex, doubleSided }  (indices locales a positions[m])
// materials[k] = { color:[r,g,b] lineal, roughness, metalness, emissive:[r,g,b], emissiveIntensity, normalScale, map, normalMap, emissiveMap }
//   Tex = { width, height, data:Uint8Array RGBA, colorSpace:'srgb'|'linear', flipY, wrapS, wrapT }
// lighting = { key:{color,intensity,position}, fill:{..}, rim:{..}, ambient:{color,intensity}, castShadow }
// cam = { left,right,top,bottom,near,far, viewMatrix:number[16] (column-major, como Three.matrixWorldInverse), projectionMatrix?:number[16] }
//
// Estado de la v1 (ver tools/lab/fast/README de la sesion): sin normal map, sin MSAA, sin workers todavia.
'use strict';

const DFG = require('./dfg_lut.cjs');
const DEBUG = {}; // diagnosticos de desarrollo (lodBias, noMip, noTone), no se usan en la ruta de produccion
module.exports_debug = DEBUG;

// ---------- utilidades matematicas (columna mayor, como Three) ----------
function mul4(a, b) {
  const o = new Float64Array(16);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++) {
    let t = 0; for (let k = 0; k < 4; k++) t += a[k * 4 + r] * b[c * 4 + k];
    o[c * 4 + r] = t;
  }
  return o;
}
function orthoMatrix(l, r, b, t, n, f) {
  // THREE.Matrix4.makeOrthographic (sin inversion de Y: la camara de Three ya la aplica en proyeccion)
  const o = new Float64Array(16);
  o[0] = 2 / (r - l); o[5] = 2 / (t - b); o[10] = -2 / (f - n);
  o[12] = -(r + l) / (r - l); o[13] = -(t + b) / (t - b); o[14] = -(f + n) / (f - n); o[15] = 1;
  return o;
}
// lookAt de Three para una camara en eye mirando a target (up = Y). Devuelve matriz de vista (world->view).
function lookAtView(eye, target, up) {
  let zx = eye[0] - target[0], zy = eye[1] - target[1], zz = eye[2] - target[2];
  let l = Math.hypot(zx, zy, zz) || 1; zx /= l; zy /= l; zz /= l;
  let xx = up[1] * zz - up[2] * zy, xy = up[2] * zx - up[0] * zz, xz = up[0] * zy - up[1] * zx;
  l = Math.hypot(xx, xy, xz) || 1; xx /= l; xy /= l; xz /= l;
  const yx = zy * xz - zz * xy, yy = zz * xx - zx * xz, yz = zx * xy - zy * xx;
  const v = new Float64Array(16);
  // matriz de rotacion (camara->mundo) transpuesta = mundo->vista, luego traslacion
  v[0] = xx; v[1] = yx; v[2] = zx; v[3] = 0;
  v[4] = xy; v[5] = yy; v[6] = zy; v[7] = 0;
  v[8] = xz; v[9] = yz; v[10] = zz; v[11] = 0;
  v[12] = -(xx * eye[0] + xy * eye[1] + xz * eye[2]);
  v[13] = -(yx * eye[0] + yy * eye[1] + yz * eye[2]);
  v[14] = -(zx * eye[0] + zy * eye[1] + zz * eye[2]);
  v[15] = 1;
  return v;
}
// Half float -> float (LUT DFG).
function SRGB_F(c) { return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
function half2float(h) {
  const s = (h & 0x8000) ? -1 : 1, e = (h >> 10) & 0x1f, f = h & 0x3ff;
  if (e === 0) return s * Math.pow(2, -14) * (f / 1024);
  if (e === 31) return f ? NaN : s * Infinity;
  return s * Math.pow(2, e - 15) * (1 + f / 1024);
}
const DFG_F = new Float64Array(512);
for (let i = 0; i < 512; i++) DFG_F[i] = half2float(DFG[i]);

// LUT sRGB -> lineal (8 bits), como GL con SRGB8_ALPHA8.
const SRGB8_LIN = new Float64Array(256);
for (let i = 0; i < 256; i++) {
  const c = i / 255;
  SRGB8_LIN[i] = c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

// ---------- texturas: mipmaps trilineales en lineal (Float32 RGBA) ----------
function buildTexture(tex) {
  const w0 = tex.width, h0 = tex.height, src = tex.data;
  const srgb = tex.colorSpace === 'srgb';
  const levels = [];
  let w = w0, h = h0;
  let cur = new Float32Array(new SharedArrayBuffer(w * h * 4 * 4));
  for (let i = 0; i < w * h * 4; i += 4) {
    for (let c = 0; c < 3; c++) cur[i + c] = srgb ? SRGB8_LIN[src[i + c]] : src[i + c] / 255;
    cur[i + 3] = src[i + 3] / 255;
  }
  levels.push({ w, h, data: cur });
  // Variante de prueba: promediar los mips en espacio sRGB codificado (en vez de lineal).
  let enc = null;
  if (DEBUG.mipSrgb && srgb) { enc = new Float32Array(w * h * 4); for (let i = 0; i < w * h * 4; i++) enc[i] = src[i] / 255; }
  while (w > 1 || h > 1) {
    if (enc) {
      const nw = Math.max(1, w >> 1), nh = Math.max(1, h >> 1);
      const ne = new Float32Array(nw * nh * 4);
      for (let y = 0; y < nh; y++) for (let x = 0; x < nw; x++) {
        const x0 = Math.min(w - 1, 2 * x), x1 = Math.min(w - 1, 2 * x + 1), y0 = Math.min(h - 1, 2 * y), y1 = Math.min(h - 1, 2 * y + 1);
        for (let c = 0; c < 4; c++) ne[(y * nw + x) * 4 + c] = 0.25 * (enc[(y0 * w + x0) * 4 + c] + enc[(y0 * w + x1) * 4 + c] + enc[(y1 * w + x0) * 4 + c] + enc[(y1 * w + x1) * 4 + c]);
      }
      enc = ne; w = nw; h = nh;
      const lin = new Float32Array(w * h * 4);
      for (let i = 0; i < w * h * 4; i++) lin[i] = (i & 3) === 3 ? enc[i] : SRGB_F(enc[i]);
      levels.push({ w, h, data: lin });
      continue;
    }
    const nw = Math.max(1, w >> 1), nh = Math.max(1, h >> 1);
    const nd = new Float32Array(new SharedArrayBuffer(nw * nh * 4 * 4));
    for (let y = 0; y < nh; y++) for (let x = 0; x < nw; x++) {
      const x0 = Math.min(w - 1, 2 * x), x1 = Math.min(w - 1, 2 * x + 1);
      const y0 = Math.min(h - 1, 2 * y), y1 = Math.min(h - 1, 2 * y + 1);
      for (let c = 0; c < 4; c++) {
        nd[(y * nw + x) * 4 + c] = 0.25 * (cur[(y0 * w + x0) * 4 + c] + cur[(y0 * w + x1) * 4 + c] + cur[(y1 * w + x0) * 4 + c] + cur[(y1 * w + x1) * 4 + c]);
      }
    }
    cur = nd; w = nw; h = nh;
    levels.push({ w, h, data: cur });
  }
  return { levels, flipY: tex.flipY !== false, repeat: tex.wrapS !== 1001 };
}

// Muestra bilineal en un nivel. u,v en coordenadas de textura (GL: v=0 abajo si flipY, aqui ya resuelto).
function sampleLevel(lv, u, v, wrapRepeat, out, o) {
  const W = lv.w, H = lv.h, d = lv.data;
  let x = u * W - 0.5, y = v * H - 0.5;
  let x0 = Math.floor(x), y0 = Math.floor(y);
  const fx = x - x0, fy = y - y0;
  let xa = x0, xb = x0 + 1, ya = y0, yb = y0 + 1;
  if (wrapRepeat) {
    xa = ((xa % W) + W) % W; xb = ((xb % W) + W) % W; ya = ((ya % H) + H) % H; yb = ((yb % H) + H) % H;
  } else {
    xa = Math.min(W - 1, Math.max(0, xa)); xb = Math.min(W - 1, Math.max(0, xb));
    ya = Math.min(H - 1, Math.max(0, ya)); yb = Math.min(H - 1, Math.max(0, yb));
  }
  const i00 = (ya * W + xa) * 4, i10 = (ya * W + xb) * 4, i01 = (yb * W + xa) * 4, i11 = (yb * W + xb) * 4;
  for (let c = 0; c < 4; c++) {
    const top = d[i00 + c] * (1 - fx) + d[i10 + c] * fx;
    const bot = d[i01 + c] * (1 - fx) + d[i11 + c] * fx;
    out[o + c] = top * (1 - fy) + bot * fy;
  }
}
// Trilineal con LOD isotropo: rho en texels por pixel.
function sampleTex(tex, u, v, dudx, dvdx, dudy, dvdy, out) {
  const L = tex.levels, base = L[0];
  if (!tex.flipY) { /* sin volteo: v directo */ } else v = 1 - v;
  const rx = Math.hypot(dudx * base.w, dvdx * base.h);
  const ry = Math.hypot(dudy * base.w, dvdy * base.h);
  const rho = Math.max(rx, ry);
  let lod = rho > 1 ? Math.log2(rho) : 0;
  if (DEBUG.lodBias) lod = Math.max(0, lod + DEBUG.lodBias);
  if (DEBUG.noMip) lod = 0;
  if (DEBUG.nearestMip) lod = Math.round(lod);
  const maxLod = L.length - 1;
  if (lod > maxLod) lod = maxLod;
  const l0 = Math.floor(lod), f = lod - l0;
  const a = SCR.a4, b = SCR.b4;
  sampleLevel(L[l0], u, v, tex.repeat, a, 0);
  if (f > 1e-6 && l0 + 1 <= maxLod) sampleLevel(L[l0 + 1], u, v, tex.repeat, b, 0);
  else { b[0] = a[0]; b[1] = a[1]; b[2] = a[2]; b[3] = a[3]; }
  for (let c = 0; c < 4; c++) out[c] = a[c] * (1 - f) + b[c] * f;
}

// ---------- rasterizacion ----------
// Recorre triangulos en pixeles de salida (x,y) con centro (x+0.5,y+0.5). cb(triIdx, x, y, w0,w1,w2, z) por pixel cubierto.
function rasterTri(ax, ay, az, bx, by, bz, cx, cy, cz, W, H, cullFront, cullBack, cb, tri) {
  // area con y hacia arriba (NDC) para decidir caras: la pantalla tiene y hacia abajo => signo invertido
  const area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay);
  if (area === 0) return;
  // Orientacion NDC: area de (ax,ay)-(bx,by)-(cx,cy) con y=-sy; se pasa ya como flag desde el llamador.
  const ndcArea = -area;
  if (ndcArea > 0 ? cullFront : cullBack) return;
  const minx = Math.max(0, Math.floor(Math.min(ax, bx, cx) - 0.5)), maxx = Math.min(W - 1, Math.ceil(Math.max(ax, bx, cx) - 0.5));
  const miny = Math.max(0, Math.floor(Math.min(ay, by, cy) - 0.5)), maxy = Math.min(H - 1, Math.ceil(Math.max(ay, by, cy) - 0.5));
  const inv = 1 / area;
  for (let y = miny; y <= maxy; y++) {
    const py = y + 0.5;
    for (let x = minx; x <= maxx; x++) {
      const px = x + 0.5;
      const w0 = ((bx - px) * (cy - py) - (cx - px) * (by - py)) * inv;
      const w1 = ((cx - px) * (ay - py) - (ax - px) * (cy - py)) * inv;
      const w2 = 1 - w0 - w1;
      if (w0 < -1e-9 || w1 < -1e-9 || w2 < -1e-9) continue;
      const z = w0 * az + w1 * bz + w2 * cz;
      cb(tri, x, y, w0, w1, w2, z);
    }
  }
}


// Patron de muestras MSAA 4x (fracciones de pixel). Por defecto, rejilla rotada tipica de GL.
// Medido: el patron C (rejilla rotada 0.125/0.375/0.625/0.875) iguala la cobertura del alfa del lab (IoU ~0.998).
const MSAA4 = [[0.125, 0.375], [0.375, 0.875], [0.625, 0.125], [0.875, 0.625]];
// Rasterizador por muestras: cb(x, y, sampleIdx, z) por cada muestra cubierta.
function rasterTriMS(ax, ay, az, bx, by, bz, cx, cy, cz, W, cullFront, cullBack, pattern, cb, H = W) {
  const area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay);
  if (area === 0) return;
  const ndcArea = -area;
  if (ndcArea > 0 ? cullFront : cullBack) return;
  const minx = Math.max(0, Math.floor(Math.min(ax, bx, cx) - 0.5)), maxx = Math.min(W - 1, Math.ceil(Math.max(ax, bx, cx) - 0.5));
  const miny = Math.max(0, Math.floor(Math.min(ay, by, cy) - 0.5)), maxy = Math.min(H - 1, Math.ceil(Math.max(ay, by, cy) - 0.5));
  const inv = 1 / area;
  for (let y = miny; y <= maxy; y++) for (let x = minx; x <= maxx; x++) {
    for (let si = 0; si < pattern.length; si++) {
      const px = x + pattern[si][0], py = y + pattern[si][1];
      const w0 = ((bx - px) * (cy - py) - (cx - px) * (by - py)) * inv;
      const w1 = ((cx - px) * (ay - py) - (ax - px) * (cy - py)) * inv;
      const w2 = 1 - w0 - w1;
      if (w0 < -1e-9 || w1 < -1e-9 || w2 < -1e-9) continue;
      cb(x, y, si, w0 * az + w1 * bz + w2 * cz);
    }
  }
}

// ---------- renderer ----------
// Config compartible (texturas en SharedArrayBuffer) para el nucleo y para los workers.
function texSlot(tex, deferTex) {
  if (!tex) return null;
  return deferTex ? { __tex: tex } : buildTexture(tex);
}
function prepareCfg(opts, deferTex) {
  // La v1 solo implementa NeutralToneMapping (c2): AgX y mapas de emision no estan; fallar es mejor que aproximar en silencio.
  if (opts.toneMapping === 'agx' && !opts.allowAgx) throw new Error('raster: AgX solo con allowAgx (lo usa export_prop_fast, que reproduce el lab de mapas)');
  if (opts.materials.some(m => m.emissiveMap)) throw new Error('raster: emissiveMap no implementado en la v1');
  const L = opts.lighting || {};
  const normLight = (l) => {
    if (!l) return null;
    const p = l.position, n = Math.hypot(p[0], p[1], p[2]) || 1;
    return { dir: [p[0] / n, p[1] / n, p[2] / n], color: [l.color[0] * l.intensity, l.color[1] * l.intensity, l.color[2] * l.intensity] };
  };
  return {
    W: opts.size * (opts.ss || 1),
    // Lienzo rectangular opcional (props: 768 x alto); sin `height` el lienzo es cuadrado como siempre.
    H: (opts.height || opts.size) * (opts.ss || 1),
    noTone: !!opts.noTone,
    meshes: opts.meshes.map(m => ({ indices: m.indices, uvs: m.uvs || null, materialIndex: m.materialIndex || 0, doubleSided: !!m.doubleSided })),
    mats: opts.materials.map(m => ({
      color: m.color || [1, 1, 1], roughness: m.roughness ?? 0.85, metalness: m.metalness ?? 0.05,
      emissive: m.emissive || [0, 0, 0], emissiveIntensity: m.emissiveIntensity ?? 0,
      map: texSlot(m.map, deferTex),
      normalMap: texSlot(m.normalMap, deferTex),
      emissiveMap: texSlot(m.emissiveMap, deferTex),
      // normalScale llega escalar (pose.cjs) o como par: se normaliza a par (un undefined daba normales NaN y RGB 0).
      normalScale: Array.isArray(m.normalScale) ? m.normalScale : [m.normalScale ?? 1, m.normalScale ?? 1],
    })),
    lights: {
      key: normLight(L.key), fill: normLight(L.fill), rim: normLight(L.rim),
      ambient: L.ambient ? [L.ambient.color[0] * L.ambient.intensity, L.ambient.color[1] * L.ambient.intensity, L.ambient.color[2] * L.ambient.intensity] : [0, 0, 0],
    },
    castShadow: L.castShadow !== false && !(DEBUG.noShadow),
    exposure: opts.exposure ?? 1,
    agx: opts.toneMapping === 'agx',
    debug: opts.debug || {},
  };
}

// Nucleo de render: cfg de prepareCfg -> { setFrames, renderJob(job, cam) }. Funciona en el hilo principal o en un worker.
function makeCore(cfg) {
  const W = cfg.W, H = cfg.H || cfg.W, meshes = cfg.meshes, mats = cfg.mats, lights = cfg.lights, castShadow = cfg.castShadow, exposure = cfg.exposure;
  for (const k of Object.keys(cfg.debug || {})) if (cfg.debug[k]) DEBUG[k] = cfg.debug[k];
  const noMap = !!DEBUG.noMap;
  const state = { frames: null };
  function setFrames(frames) { state.frames = frames; }
  return { setFrames, renderJob };

  function renderJob(job, cam) {
    const frame = state.frames[job.frame];
    const yaw = job.yaw || 0, yOff = job.yOffset || 0;
    const cs = Math.cos(yaw), sn = Math.sin(yaw);
    // Vertices del mundo transformados (rotacion Y + traslacion Y) y normales rotadas.
    const verts = [];
    for (let m = 0; m < meshes.length; m++) {
      const P = frame.positions[m], N = frame.normals[m];
      const n = P.length / 3;
      const wp = new Float64Array(n * 3), wn = new Float64Array(n * 3);
      for (let i = 0; i < n; i++) {
        const x = P[i * 3], y = P[i * 3 + 1], z = P[i * 3 + 2];
        wp[i * 3] = x * cs + z * sn; wp[i * 3 + 1] = y + yOff; wp[i * 3 + 2] = -x * sn + z * cs;
        const nx = N[i * 3], ny = N[i * 3 + 1], nz = N[i * 3 + 2];
        wn[i * 3] = nx * cs + nz * sn; wn[i * 3 + 1] = ny; wn[i * 3 + 2] = -nx * sn + nz * cs;
      }
      verts.push({ wp, wn });
    }
    const view = cam.viewMatrix;
    const proj = cam.projectionMatrix || orthoMatrix(cam.left, cam.right, cam.bottom, cam.top, cam.near, cam.far);
    const mvp = mul4(proj, view);
    // Camara direccional (sombra): origen como target, eye = posicion de la luz key.
    const shadowVP = castShadow && lights.key ? mul4(orthoMatrix(-5, 5, -5, 5, 0.5, 500), lookAtView(lights.key.dir.map(v => v * 30), [0, 0, 0], [0, 1, 0])) : null;
    return shadeFrame(verts, mvp, view, shadowVP, job);
  }

  function shadeFrame(verts, mvp, view, shadowVP, job) {
    // Pasa 1: transformar a pantalla y visibilidad.
    const SH = 512;
    const MS = DEBUG.msaaPattern || MSAA4;
    const zs = new Float32Array(W * H * 4).fill(Infinity);
    const tid = new Int32Array(W * H * 4).fill(-1);
    const screen = [];
    for (let m = 0; m < meshes.length; m++) {
      const { wp } = verts[m];
      const n = wp.length / 3;
      const sx = new Float64Array(n), sy = new Float64Array(n), sz = new Float64Array(n);
      for (let i = 0; i < n; i++) {
        const x = wp[i * 3], y = wp[i * 3 + 1], z = wp[i * 3 + 2];
        const cx = mvp[0] * x + mvp[4] * y + mvp[8] * z + mvp[12];
        const cy = mvp[1] * x + mvp[5] * y + mvp[9] * z + mvp[13];
        const cz = mvp[2] * x + mvp[6] * y + mvp[10] * z + mvp[14];
        sx[i] = (cx * 0.5 + 0.5) * W; sy[i] = (0.5 - cy * 0.5) * H; sz[i] = cz;
      }
      screen.push({ sx, sy, sz });
    }
    for (let m = 0; m < meshes.length; m++) {
      const mesh = meshes[m];
      const S = screen[m];
      const idx = mesh.indices;
      const side2 = !!mesh.doubleSided;
      for (let t = 0; t < idx.length; t += 3) {
        const i0 = idx[t], i1 = idx[t + 1], i2 = idx[t + 2];
        const triId = (m << 20) | (t / 3);
        rasterTriMS(S.sx[i0], S.sy[i0], S.sz[i0], S.sx[i1], S.sy[i1], S.sz[i1], S.sx[i2], S.sy[i2], S.sz[i2], W, false, !side2, MS,
          (x, y, si, z) => {
            const q = (y * W + x) * 4 + si;
            if (z < zs[q]) { zs[q] = z; tid[q] = triId; }
          }, H);
      }
    }
    // Pasa 2: sombra de la luz key (caras traseras para FrontSide).
    let shadowMap = null;
    if (shadowVP) {
      shadowMap = new Float32Array(SH * SH).fill(Infinity);
      if (global.__rstat) global.__rstat.hasShadow = (global.__rstat.hasShadow || 0) + 1;
      for (let m = 0; m < meshes.length; m++) {
        const { wp } = verts[m];
        const n = wp.length / 3;
        const SX = new Float64Array(n), SY = new Float64Array(n), SZ = new Float64Array(n);
        for (let i = 0; i < n; i++) {
          const x = wp[i * 3], y = wp[i * 3 + 1], z = wp[i * 3 + 2];
          const cx = shadowVP[0] * x + shadowVP[4] * y + shadowVP[8] * z + shadowVP[12];
          const cy = shadowVP[1] * x + shadowVP[5] * y + shadowVP[9] * z + shadowVP[13];
          const cz = shadowVP[2] * x + shadowVP[6] * y + shadowVP[10] * z + shadowVP[14];
          SX[i] = (cx * 0.5 + 0.5) * SH; SY[i] = (0.5 - cy * 0.5) * SH; SZ[i] = cz * 0.5 + 0.5;
        }
        const idx = meshes[m].indices;
        const side2 = !!meshes[m].doubleSided;
        for (let t = 0; t < idx.length; t += 3) {
          const i0 = idx[t], i1 = idx[t + 1], i2 = idx[t + 2];
          // FrontSide -> sombra con caras traseras (shadowSide de Three): se descartan las frontales.
          rasterTri(SX[i0], SY[i0], SZ[i0], SX[i1], SY[i1], SZ[i1], SX[i2], SY[i2], SZ[i2], SH, SH,
            /*cullFront*/ DEBUG.shadowFront ? false : !side2, /*cullBack*/ DEBUG.shadowFront ? !side2 : false,
            (tri, x, y, w0, w1, w2, z) => { const p = y * SH + x; if (z < shadowMap[p]) shadowMap[p] = z; }, 0);
        }
      }
    }
    // Pasa 3: sombreado por pixel visible (escalar: sin asignaciones por pixel).
    const img = new Uint8ClampedArray(W * H * 4);
    const T4 = SCR.t4, FAB = SCR.fab, TONE = SCR.tone;
    const vx = view[2], vy = view[6], vz = view[10];
    const ambR = lights.ambient[0], ambG = lights.ambient[1], ambB = lights.ambient[2];
    const ambScale = DEBUG.ambientScale ?? 1;
    const LK = lights.key, LF = lights.fill, LR = lights.rim;
    for (let py = 0; py < H; py++) for (let px = 0; px < W; px++) {
      const p = py * W + px;
      let cov = 0, best = -1, bestZ = Infinity;
      for (let si = 0; si < 4; si++) {
        const q = p * 4 + si;
        if (tid[q] < 0) continue;
        cov++;
        if (zs[q] < bestZ) { bestZ = zs[q]; best = q; }
      }
      if (cov === 0) continue;
      const triId = tid[best];
      const m = triId >>> 20;
      const tIdx = triId & 0xfffff;
      const mesh = meshes[m];
      const i0 = mesh.indices[tIdx * 3], i1 = mesh.indices[tIdx * 3 + 1], i2 = mesh.indices[tIdx * 3 + 2];
      const S = screen[m];
      const sx0 = S.sx[i0], sy0 = S.sy[i0], sx1 = S.sx[i1], sy1 = S.sy[i1], sx2 = S.sx[i2], sy2 = S.sy[i2];
      const det = (sx1 - sx0) * (sy2 - sy0) - (sx2 - sx0) * (sy1 - sy0) || 1e-12;
      const iD = 1 / det;
      const qx = px + 0.5, qy = py + 0.5;
      const w1 = ((sx2 - qx) * (sy0 - qy) - (sx0 - qx) * (sy2 - qy)) / det;
      const w2 = ((sx0 - qx) * (sy1 - qy) - (sx1 - qx) * (sy0 - qy)) / det;
      const w0 = 1 - w1 - w2;
      const coverage = cov / 4;
      const { wp, wn } = verts[m];
      const j0 = i0 * 3, j1 = i1 * 3, j2 = i2 * 3;
      const pX = wp[j0] * w0 + wp[j1] * w1 + wp[j2] * w2;
      const pY = wp[j0 + 1] * w0 + wp[j1 + 1] * w1 + wp[j2 + 1] * w2;
      const pZ = wp[j0 + 2] * w0 + wp[j1 + 2] * w1 + wp[j2 + 2] * w2;
      let nx = wn[j0] * w0 + wn[j1] * w1 + wn[j2] * w2;
      let ny = wn[j0 + 1] * w0 + wn[j1 + 1] * w1 + wn[j2 + 1] * w2;
      let nz = wn[j0 + 2] * w0 + wn[j1 + 2] * w1 + wn[j2 + 2] * w2;
      const nlen = Math.hypot(nx, ny, nz) || 1;
      nx /= nlen; ny /= nlen; nz /= nlen;
      const hasUv = !!mesh.uvs;
      const uv = mesh.uvs;
      const mat = mats[mesh.materialIndex || 0];
      // Gradientes de uv por pixel (triangulo afin en pantalla) y uv del pixel.
      let dudx = 0, dvdx = 0, dudy = 0, dvdy = 0, u = 0, v = 0;
      if (hasUv && (mat.map || mat.normalMap)) {
        const u0 = uv[i0 * 2], v0 = uv[i0 * 2 + 1], u1 = uv[i1 * 2], v1 = uv[i1 * 2 + 1], u2 = uv[i2 * 2], v2 = uv[i2 * 2 + 1];
        dudx = ((u1 - u0) * (sy2 - sy0) - (u2 - u0) * (sy1 - sy0)) * iD;
        dudy = ((u2 - u0) * (sx1 - sx0) - (u1 - u0) * (sx2 - sx0)) * iD;
        dvdx = ((v1 - v0) * (sy2 - sy0) - (v2 - v0) * (sy1 - sy0)) * iD;
        dvdy = ((v2 - v0) * (sx1 - sx0) - (v1 - v0) * (sx2 - sx0)) * iD;
        u = u0 * w0 + u1 * w1 + u2 * w2; v = v0 * w0 + v1 * w1 + v2 * w2;
      }
      // Normal map: getTangentFrame con derivadas analiticas (eye_pos = -vViewPosition => derivadas -dP).
      let lx = nx, ly = ny, lz = nz;
      if (mat.normalMap && hasUv && !DEBUG.noNormalMap) {
        const dpx0 = ((wp[j1] - wp[j0]) * (sy2 - sy0) - (wp[j2] - wp[j0]) * (sy1 - sy0)) * iD;
        const dpx1 = ((wp[j1 + 1] - wp[j0 + 1]) * (sy2 - sy0) - (wp[j2 + 1] - wp[j0 + 1]) * (sy1 - sy0)) * iD;
        const dpx2 = ((wp[j1 + 2] - wp[j0 + 2]) * (sy2 - sy0) - (wp[j2 + 2] - wp[j0 + 2]) * (sy1 - sy0)) * iD;
        const dpy0 = ((wp[j2] - wp[j0]) * (sx1 - sx0) - (wp[j1] - wp[j0]) * (sx2 - sx0)) * iD;
        const dpy1 = ((wp[j2 + 1] - wp[j0 + 1]) * (sx1 - sx0) - (wp[j1 + 1] - wp[j0 + 1]) * (sx2 - sx0)) * iD;
        const dpy2 = ((wp[j2 + 2] - wp[j0 + 2]) * (sx1 - sx0) - (wp[j1 + 2] - wp[j0 + 2]) * (sx2 - sx0)) * iD;
        const q0x = -dpx0, q0y = -dpx1, q0z = -dpx2;
        const q1x = -dpy0, q1y = -dpy1, q1z = -dpy2;
        // q1perp = q1 x N ; q0perp = N x q0
        const a1x = q1y * nz - q1z * ny, a1y = q1z * nx - q1x * nz, a1z = q1x * ny - q1y * nx;
        const b1x = ny * q0z - nz * q0y, b1y = nz * q0x - nx * q0z, b1z = nx * q0y - ny * q0x;
        const Tx = a1x * dudx + b1x * dudy, Ty = a1y * dudx + b1y * dudy, Tz = a1z * dudx + b1z * dudy;
        const Bx = a1x * dvdx + b1x * dvdy, By = a1y * dvdx + b1y * dvdy, Bz = a1z * dvdx + b1z * dvdy;
        const det2 = Math.max(Tx * Tx + Ty * Ty + Tz * Tz, Bx * Bx + By * By + Bz * Bz);
        const scl = det2 === 0 ? 0 : 1 / Math.sqrt(det2);
        sampleTex(mat.normalMap, u, v, dudx, dvdx, dudy, dvdy, T4);
        const ns = mat.normalScale;
        const mx = (T4[0] * 2 - 1) * ns[0], my = (T4[1] * 2 - 1) * ns[1], mz = T4[2] * 2 - 1;
        lx = Tx * scl * mx + Bx * scl * my + nx * mz;
        ly = Ty * scl * mx + By * scl * my + ny * mz;
        lz = Tz * scl * mx + Bz * scl * my + nz * mz;
        const ll = Math.hypot(lx, ly, lz) || 1; lx /= ll; ly /= ll; lz /= ll;
      }
      // Color base (mapa en lineal, trilineal).
      let bR = mat.color[0], bG = mat.color[1], bB = mat.color[2];
      if (mat.map && hasUv && !noMap) {
        sampleTex(mat.map, u, v, dudx, dvdx, dudy, dvdy, T4);
        bR *= T4[0]; bG *= T4[1]; bB *= T4[2];
      }
      // Rugosidad geometrica: derivadas de la normal no perturbada (en pantalla).
      let gN = 0;
      if (!DEBUG.noGeomRough) {
        const ddx0 = ((wn[j1] - wn[j0]) * (sy2 - sy0) - (wn[j2] - wn[j0]) * (sy1 - sy0)) * iD;
        const ddx1 = ((wn[j1 + 1] - wn[j0 + 1]) * (sy2 - sy0) - (wn[j2 + 1] - wn[j0 + 1]) * (sy1 - sy0)) * iD;
        const ddx2 = ((wn[j1 + 2] - wn[j0 + 2]) * (sy2 - sy0) - (wn[j2 + 2] - wn[j0 + 2]) * (sy1 - sy0)) * iD;
        const ddy0 = ((wn[j2] - wn[j0]) * (sx1 - sx0) - (wn[j1] - wn[j0]) * (sx2 - sx0)) * iD;
        const ddy1 = ((wn[j2 + 1] - wn[j0 + 1]) * (sx1 - sx0) - (wn[j1 + 1] - wn[j0 + 1]) * (sx2 - sx0)) * iD;
        const ddy2 = ((wn[j2 + 2] - wn[j0 + 2]) * (sx1 - sx0) - (wn[j1 + 2] - wn[j0 + 2]) * (sx2 - sx0)) * iD;
        const sdx = nx * ddx0 + ny * ddx1 + nz * ddx2, sdy = nx * ddy0 + ny * ddy1 + nz * ddy2;
        const cxx = Math.abs(ddx0 - nx * sdx), cxy = Math.abs(ddx1 - ny * sdx), cxz = Math.abs(ddx2 - nz * sdx);
        const cyx = Math.abs(ddy0 - nx * sdy), cyy = Math.abs(ddy1 - ny * sdy), cyz = Math.abs(ddy2 - nz * sdy);
        gN = Math.max(Math.max(cxx, cyx), Math.max(cxy, cyy), Math.max(cxz, cyz));
      }
      let rough = Math.max(mat.roughness, 0.0525) + gN;
      rough = Math.min(rough, 1);
      const metal = mat.metalness;
      const dR = bR * (1 - metal), dG = bG * (1 - metal), dB = bB * (1 - metal);
      // specularBlended = mix(0.04, base, metal)
      const sbR = 0.04 * (1 - metal) + bR * metal, sbG = 0.04 * (1 - metal) + bG * metal, sbB = 0.04 * (1 - metal) + bB * metal;
      // DFG (LUT 16x16) y compensacion multiscatter
      let dotNVms = lx * vx + ly * vy + lz * vz; dotNVms = dotNVms < 0 ? 0 : dotNVms > 1 ? 1 : dotNVms;
      dfgLookupInto(FAB, rough, dotNVms);
      const f0 = FAB[0], f1 = FAB[1];
      const EssMs = f0 + f1;
      const msC = 1 / EssMs - 1;
      const msR = DEBUG.noMsComp ? 1 : 1 + sbR * msC, msG = DEBUG.noMsComp ? 1 : 1 + sbG * msC, msB = DEBUG.noMsComp ? 1 : 1 + sbB * msC;
      // Sombra de la luz key
      let shadowFac = 1;
      if (shadowMap) shadowFac = shadowAtS(pX, pY, pZ, shadowVP, shadowMap, SH, px, py, H);
      let aR = 0, aG = 0, aB = 0;
      const alpha = rough * rough, a2 = alpha * alpha;
      // Luces direccionales (key con sombra, fill, rim): mismas formulas que la version de referencia.
      for (let li = 0; li < 3; li++) {
        const L_ = li === 0 ? LK : li === 1 ? LF : LR;
        if (!L_) continue;
        const Ld = L_.dir;
        const sf = li === 0 ? shadowFac : 1;
        const cR = L_.color[0] * sf, cG = L_.color[1] * sf, cB = L_.color[2] * sf;
        let dotNL = lx * Ld[0] + ly * Ld[1] + lz * Ld[2]; dotNL = dotNL < 0 ? 0 : dotNL > 1 ? 1 : dotNL;
        const irR = dotNL * cR, irG = dotNL * cG, irB = dotNL * cB;
        let hx = Ld[0] + vx, hy = Ld[1] + vy, hz = Ld[2] + vz;
        const hl = Math.hypot(hx, hy, hz) || 1; hx /= hl; hy /= hl; hz /= hl;
        let dotNH = lx * hx + ly * hy + lz * hz; dotNH = dotNH < 0 ? 0 : dotNH > 1 ? 1 : dotNH;
        let dotVH = vx * hx + vy * hy + vz * hz; dotVH = dotVH < 0 ? 0 : dotVH > 1 ? 1 : dotVH;
        const fres = Math.pow(2, (-5.55473 * dotVH - 6.98316) * dotVH);
        const gv = dotNL * Math.sqrt(a2 + (1 - a2) * dotNVms * dotNVms);
        const gl = dotNVms * Math.sqrt(a2 + (1 - a2) * dotNL * dotNL);
        const Vis = 0.5 / Math.max(gv + gl, 1e-12);
        const denom = dotNH * dotNH * (a2 - 1) + 1;
        const D = (1 / Math.PI) * a2 / (denom * denom);
        const VD = Vis * D;
        // F del difuso: F_Schlick(0.04, 1, dotVH) (specularColor es 0.04 uniforme)
        const dfR = 1 - (0.04 * (1 - fres) + fres);
        // Especular: F_Schlick(specularBlended, 1, dotVH) * Vis*D * msComp
        aR += irR * ((sbR * (1 - fres) + fres) * VD) * msR + irR * (dR / Math.PI) * dfR;
        aG += irG * ((sbG * (1 - fres) + fres) * VD) * msG + irG * (dG / Math.PI) * dfR;
        aB += irB * ((sbB * (1 - fres) + fres) * VD) * msB + irB * (dB / Math.PI) * dfR;
      }
      // Ambiente difuso con compensacion multiscatter (Fr = 0.04 uniforme)
      const FssEss = 0.04 * f0 + f1;
      const Favg = 0.04 + 0.96 * 0.047619;
      const Fms = FssEss * Favg / (1 - (1 - EssMs) * Favg);
      const amb = 1 - FssEss - Fms * (1 - EssMs);
      aR += ambR * ambScale * (dR / Math.PI) * amb;
      aG += ambG * ambScale * (dG / Math.PI) * amb;
      aB += ambB * ambScale * (dB / Math.PI) * amb;
      // Emision (intensidad constante)
      const em = mat.emissiveIntensity;
      aR += mat.emissive[0] * em; aG += mat.emissive[1] * em; aB += mat.emissive[2] * em;
      // Neutral + sRGB, con cobertura MSAA (resolve premultiplicado como GL)
      const o = p * 4;
      if (DEBUG.noTone || cfg.noTone) {
        img[o] = toSRGBf(aR) * coverage; img[o + 1] = toSRGBf(aG) * coverage; img[o + 2] = toSRGBf(aB) * coverage;
      } else {
        if (cfg.agx) agxScalar(aR, aG, aB, exposure, TONE); else neutralScalar(aR, aG, aB, exposure, TONE);
        img[o] = toSRGBf(TONE[0]) * coverage; img[o + 1] = toSRGBf(TONE[1]) * coverage; img[o + 2] = toSRGBf(TONE[2]) * coverage;
      }
      img[o + 3] = 255 * coverage;
    }
    return img;
  }

  // Derivadas en pantalla (por pixel) de la componente k del atributo arr (stride 3) del triangulo.
  function attrGrad(arr, k, i0, i1, i2, m, screen) {
    const S = screen[m];
    const x0 = S.sx[i0], y0 = S.sy[i0], x1 = S.sx[i1], y1 = S.sy[i1], x2 = S.sx[i2], y2 = S.sy[i2];
    const det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0) || 1e-12;
    const a0 = arr[i0 * 3 + k], a1 = arr[i1 * 3 + k], a2 = arr[i2 * 3 + k];
    return [((a1 - a0) * (y2 - y0) - (a2 - a0) * (y1 - y0)) / det, ((a2 - a0) * (x1 - x0) - (a1 - a0) * (x2 - x0)) / det];
  }
  // Muestra de normal map en el pixel (lineal, sin sRGB), trilineal con el mismo LOD que el color.
  function sampleNormalMap(tex, g, mesh, i0, i1, i2, w0, w1, w2) {
    const nmTmp = [0, 0, 0, 0];
    const uv = mesh.uvs;
    const u = uv[i0 * 2] * w0 + uv[i1 * 2] * w1 + uv[i2 * 2] * w2;
    const v = uv[i0 * 2 + 1] * w0 + uv[i1 * 2 + 1] * w1 + uv[i2 * 2 + 1] * w2;
    sampleTex(tex, u, v, g.dudx, g.dvdx, g.dudy, g.dvdy, nmTmp);
    return nmTmp;
  }
  function triGrads(mesh, tIdx, i0, i1, i2, m, screen) {
    const S = screen[m], uv = mesh.uvs;
    const x0 = S.sx[i0], y0 = S.sy[i0], x1 = S.sx[i1], y1 = S.sy[i1], x2 = S.sx[i2], y2 = S.sy[i2];
    const det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0) || 1e-12;
    const u0 = uv[i0 * 2], v0 = uv[i0 * 2 + 1], u1 = uv[i1 * 2], v1 = uv[i1 * 2 + 1], u2 = uv[i2 * 2], v2 = uv[i2 * 2 + 1];
    const dudx = ((u1 - u0) * (y2 - y0) - (u2 - u0) * (y1 - y0)) / det;
    const dudy = ((u2 - u0) * (x1 - x0) - (u1 - u0) * (x2 - x0)) / det;
    const dvdx = ((v1 - v0) * (y2 - y0) - (v2 - v0) * (y1 - y0)) / det;
    const dvdy = ((v2 - v0) * (x1 - x0) - (v1 - v0) * (x2 - x0)) / det;
    return { dudx, dudy, dvdx, dvdy };
  }
  // Derivada de la normal normalizada en pantalla (max componente de |dFdx| y |dFdy|), analitica por triangulo.
  function normalGrad(mesh, tIdx, i0, i1, i2, m, screen, wn, nN) {
    const S = screen[m], wnv = wn;
    const x0 = S.sx[i0], y0 = S.sy[i0], x1 = S.sx[i1], y1 = S.sy[i1], x2 = S.sx[i2], y2 = S.sy[i2];
    const det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0) || 1e-12;
    const dd = [0, 0, 0, 0, 0, 0]; // dNx/dx, dNy/dx, dNz/dx, dNx/dy, dNy/dy, dNz/dy
    for (let k = 0; k < 3; k++) {
      const n0 = wnv[i0 * 3 + k], n1 = wnv[i1 * 3 + k], n2 = wnv[i2 * 3 + k];
      dd[k] = ((n1 - n0) * (y2 - y0) - (n2 - n0) * (y1 - y0)) / det;
      dd[3 + k] = ((n2 - n0) * (x1 - x0) - (n1 - n0) * (x2 - x0)) / det;
    }
    // Normalizada: d(n/|n|) = (dN - n (n.dN)) / |N|
    let mx = 0;
    for (let comp = 0; comp < 3; comp++) {
      const dxc = dd[comp] - nN[comp] * (nN[0] * dd[0] + nN[1] * dd[1] + nN[2] * dd[2]);
      const dyc = dd[3 + comp] - nN[comp] * (nN[0] * dd[3] + nN[1] * dd[4] + nN[2] * dd[5]);
      mx = Math.max(mx, Math.abs(dxc), Math.abs(dyc));
    }
    return mx;
  }

  function shadowAt(pos, svp, map, SH, px, py, W) {
    const x = pos[0], y = pos[1], z = pos[2];
    const cx = svp[0] * x + svp[4] * y + svp[8] * z + svp[12];
    const cy = svp[1] * x + svp[5] * y + svp[9] * z + svp[13];
    const cz = svp[2] * x + svp[6] * y + svp[10] * z + svp[14];
    const u = cx * 0.5 + 0.5, v = cy * 0.5 + 0.5, ref = cz * 0.5 + 0.5;
    if (u < 0 || u > 1 || v < 0 || v > 1 || ref > 1) return 1;
    // getShadow PCF de Three r186: 5 taps vogel, radio 1 texel, phi = IGN(gl_FragCoord.xy).
    const fx = px + 0.5, fy = (W - py) - 0.5;
    const ign = frac(52.9829189 * frac(0.06711056 * fx + 0.00583715 * fy));
    const phi = ign * Math.PI * 2;
    const radius = 1 / SH;
    let sum = 0;
    for (let i = 0; i < 5; i++) {
      const r = Math.sqrt((i + 0.5) / 5), th = i * 2.399963229728653 + phi;
      const su = u + Math.cos(th) * r * radius, sv = v + Math.sin(th) * r * radius;
      sum += compareTap(map, SH, su, sv, ref);
    }
    return sum * 0.2;
  }
  // Muestreo de sombra con comparacion (nearest; ver nota en el informe).
  function compareTap(map, SH, u, v, ref) {
    // El mapa se rasteriza con fila 0 arriba (NDC y hacia arriba invertido): la fila es (1-v)*SH.
    if (!DEBUG.shadowNearest) {
      // Comparacion bilineal de hardware (sampler2DShadow con filtro lineal): 2x2 texels ponderados.
      const fx = u * SH - 0.5, fy = (1 - v) * SH - 0.5;
      const x0 = Math.floor(fx), y0 = Math.floor(fy), ax = fx - x0, ay = fy - y0;
      const at = (x, y) => { const cx = Math.min(SH - 1, Math.max(0, x)), cy = Math.min(SH - 1, Math.max(0, y)); return ref <= map[cy * SH + cx] ? 1 : 0; };
      return (at(x0, y0) * (1 - ax) + at(x0 + 1, y0) * ax) * (1 - ay) + (at(x0, y0 + 1) * (1 - ax) + at(x0 + 1, y0 + 1) * ax) * ay;
    }
    let tx = Math.floor(u * SH), ty = Math.floor((1 - v) * SH);
    tx = Math.min(SH - 1, Math.max(0, tx)); ty = Math.min(SH - 1, Math.max(0, ty));
    return ref <= map[ty * SH + tx] ? 1 : 0;
  }
  function dfgLookup(rough, dotNV) {
    // LUT 16x16 con filtrado lineal, clamp.
    const x = rough * 16 - 0.5, y = dotNV * 16 - 0.5;
    const x0 = Math.floor(x), y0 = Math.floor(y), fx = x - x0, fy = y - y0;
    const cl = (v) => Math.min(15, Math.max(0, v));
    const out = [0, 0];
    for (let c = 0; c < 2; c++) {
      const a = DFG_F[(cl(y0) * 16 + cl(x0)) * 2 + c], b = DFG_F[(cl(y0) * 16 + cl(x0 + 1)) * 2 + c];
      const d = DFG_F[(cl(y0 + 1) * 16 + cl(x0)) * 2 + c], e = DFG_F[(cl(y0 + 1) * 16 + cl(x0 + 1)) * 2 + c];
      out[c] = (a * (1 - fx) + b * fx) * (1 - fy) + (d * (1 - fx) + e * fx) * fy;
    }
    return out;
  }
  function Ess_(fab) { return fab[0] + fab[1]; }
}

function cross3(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
function dot3f(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
// Publica el rasterizador. workers > 1: reparte los trabajos en un pool de worker_threads (datos en SharedArrayBuffer).
async function createRenderer(opts) {
  const nWorkers = opts.workers || 1;
  if (nWorkers <= 1) {
    const core = makeCore(prepareCfg(opts));
    return {
      setFrames(frames) { core.setFrames(frames); },
      async render(jobs, cam) { return jobs.map(j => core.renderJob(j, cam)); },
      async close() {},
    };
  }
  const { Worker } = require('node:worker_threads');
  const path = require('node:path');
  const cfg = prepareCfg(opts, true);
  // Pool: cada worker responde por id a sus peticiones (build, init, render).
  const pool = [];
  let reqId = 0;
  const send = (w, msg, transfer) => new Promise((resolve, reject) => {
    const id = ++reqId;
    w.pend.set(id, { resolve, reject });
    w.postMessage(Object.assign({ id }, msg), transfer || []);
  });
  for (let i = 0; i < nWorkers; i++) {
    const w = new Worker(path.join(__dirname, 'raster_worker.cjs'));
    w.pend = new Map();
    w.on('message', (m) => { const r = w.pend.get(m.id); if (r) { w.pend.delete(m.id); r.resolve(m); } });
    w.on('error', (e) => { for (const r of w.pend.values()) r.reject(e); w.pend.clear(); });
    pool.push(w);
  }
  // 1) Mips de todas las texturas en paralelo (SharedArrayBuffer, sin copias de vuelta).
  const slots = [];
  for (const m of cfg.mats) for (const f of ['map', 'normalMap', 'emissiveMap']) if (m[f]) slots.push({ m, f, tex: m[f].__tex });
  const built = await Promise.all(slots.map((sl, i) => send(pool[i % pool.length], { type: 'build', tex: sl.tex })));
  slots.forEach((sl, i) => { sl.m[sl.f] = built[i].res; });
  // 2) Nucleo en cada worker con la config completa (texturas ya compartidas).
  await Promise.all(pool.map(w => send(w, { type: 'init', cfg })));
  return {
    setFrames(frames) {
      // Copia a SharedArrayBuffer una vez y se envia a todos los workers (sin copiar por trabajo).
      const shared = frames.map(f => ({
        positions: f.positions.map(a => shareF32(a)), normals: f.normals.map(a => shareF32(a)),
      }));
      for (const w of pool) w.postMessage({ type: 'frames', frames: shared });
    },
    async render(jobs, cam) {
      const per = pool.map(() => []);
      jobs.forEach((j, i) => per[i % pool.length].push(i));
      const results = new Array(jobs.length);
      const replies = await Promise.all(pool.map((w, wi) => send(w, { type: 'render', jobs: per[wi].map(i => jobs[i]), idx: per[wi], cam })));
      replies.forEach(m => m.idx.forEach((ji, k) => { results[ji] = new Uint8ClampedArray(m.out[k]); }));
      return results;
    },
    async close() { await Promise.all(pool.map(w => w.terminate())); },
  };
}
function shareF32(a) {
  const sab = new SharedArrayBuffer(a.length * 4);
  const out = new Float32Array(sab);
  out.set(a);
  return out;
}

// ---------- escalares compartidos (sin asignaciones en el bucle caliente) ----------
const SCR = { t4: new Float64Array(4), a4: new Float64Array(4), b4: new Float64Array(4), fab: new Float64Array(2), tone: new Float64Array(3) };
function neutralScalar(r0, g0, b0, exposure, out) {
  const StartCompression = 0.8 - 0.04, Desaturation = 0.15;
  let r = r0 * exposure, g = g0 * exposure, b = b0 * exposure;
  const x = Math.min(r, g, b);
  const offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
  r -= offset; g -= offset; b -= offset;
  const peak = Math.max(r, g, b);
  if (peak < StartCompression) { out[0] = r; out[1] = g; out[2] = b; return; }
  const d = 1 - StartCompression;
  const newPeak = 1 - d * d / (peak + d - StartCompression);
  const sc = newPeak / peak; r *= sc; g *= sc; b *= sc;
  const gg = 1 - 1 / (Desaturation * (peak - newPeak) + 1);
  out[0] = r * (1 - gg) + newPeak * gg; out[1] = g * (1 - gg) + newPeak * gg; out[2] = b * (1 - gg) + newPeak * gg;
}
// AgXToneMapping de Three r186 (matrices GLSL en columnas; salida lineal sRGB, el OETF va despues).
function agxScalar(r0, g0, b0, exposure, out) {
  let r = r0 * exposure, g = g0 * exposure, b = b0 * exposure;
  // LINEAR_SRGB_TO_LINEAR_REC2020
  let x = 0.6274 * r + 0.3293 * g + 0.0433 * b, y = 0.0691 * r + 0.9195 * g + 0.0113 * b, z = 0.0164 * r + 0.0880 * g + 0.8956 * b;
  // AgXInsetMatrix
  r = 0.856627153315983 * x + 0.0951212405381588 * y + 0.0482516061458583 * z;
  g = 0.137318972929847 * x + 0.761241990602591 * y + 0.101439036467562 * z;
  b = 0.11189821299995 * x + 0.0767994186031903 * y + 0.811302368396859 * z;
  const MIN_EV = -12.47393, MAX_EV = 4.026069;
  const enc = (c) => {
    c = Math.log2(Math.max(c, 1e-10));
    c = (c - MIN_EV) / (MAX_EV - MIN_EV);
    c = c < 0 ? 0 : c > 1 ? 1 : c;
    const c2 = c * c, c4 = c2 * c2;
    return 15.5 * c4 * c2 - 40.14 * c4 * c + 31.96 * c4 - 6.868 * c2 * c + 0.4298 * c2 + 0.1191 * c - 0.00232;
  };
  r = enc(r); g = enc(g); b = enc(b);
  // AgXOutsetMatrix
  x = 1.1271005818144368 * r - 0.11060664309660323 * g - 0.016493938717834573 * b;
  y = -0.1413297634984383 * r + 1.157823702216272 * g - 0.016493938717834257 * b;
  z = -0.14132976349843826 * r - 0.11060664309660294 * g + 1.2519364065950405 * b;
  x = Math.pow(Math.max(0, x), 2.2); y = Math.pow(Math.max(0, y), 2.2); z = Math.pow(Math.max(0, z), 2.2);
  // LINEAR_REC2020_TO_LINEAR_SRGB
  r = 1.6605 * x - 0.5876 * y - 0.0728 * z;
  g = -0.1246 * x + 1.1329 * y - 0.0083 * z;
  b = -0.0182 * x - 0.1006 * y + 1.1187 * z;
  out[0] = r < 0 ? 0 : r > 1 ? 1 : r; out[1] = g < 0 ? 0 : g > 1 ? 1 : g; out[2] = b < 0 ? 0 : b > 1 ? 1 : b;
}
function dfgLookupInto(out, rough, dotNV) {
  const x = rough * 16 - 0.5, y = dotNV * 16 - 0.5;
  const x0 = Math.floor(x), y0 = Math.floor(y), fx = x - x0, fy = y - y0;
  const cx0 = Math.min(15, Math.max(0, x0)), cx1 = Math.min(15, Math.max(0, x0 + 1));
  const cy0 = Math.min(15, Math.max(0, y0)), cy1 = Math.min(15, Math.max(0, y0 + 1));
  for (let c = 0; c < 2; c++) {
    const a = DFG_F[(cy0 * 16 + cx0) * 2 + c], b = DFG_F[(cy0 * 16 + cx1) * 2 + c];
    const d = DFG_F[(cy1 * 16 + cx0) * 2 + c], e = DFG_F[(cy1 * 16 + cx1) * 2 + c];
    out[c] = (a * (1 - fx) + b * fx) * (1 - fy) + (d * (1 - fx) + e * fx) * fy;
  }
}
function cmpAt(map, SH, x, y, ref) {
  const cx = Math.min(SH - 1, Math.max(0, x)), cy = Math.min(SH - 1, Math.max(0, y));
  return ref <= map[cy * SH + cx] ? 1 : 0;
}
function shadowAtS(x, y, z, svp, map, SH, px, py, W) {
  const cx = svp[0] * x + svp[4] * y + svp[8] * z + svp[12];
  const cy = svp[1] * x + svp[5] * y + svp[9] * z + svp[13];
  const cz = svp[2] * x + svp[6] * y + svp[10] * z + svp[14];
  const u = cx * 0.5 + 0.5, v = cy * 0.5 + 0.5, ref = cz * 0.5 + 0.5;
  if (u < 0 || u > 1 || v < 0 || v > 1 || ref > 1) return 1;
  const fx = px + 0.5, fy = (W - py) - 0.5;
  const phi = frac(52.9829189 * frac(0.06711056 * fx + 0.00583715 * fy)) * Math.PI * 2;
  const radius = 1 / SH;
  let sum = 0;
  for (let i = 0; i < 5; i++) {
    const r = Math.sqrt((i + 0.5) / 5) * radius, th = i * 2.399963229728653 + phi;
    const su = u + Math.cos(th) * r, sv = v + Math.sin(th) * r;
    if (!DEBUG.shadowNearest) {
      const fxx = su * SH - 0.5, fyy = (1 - sv) * SH - 0.5;
      const x0 = Math.floor(fxx), y0 = Math.floor(fyy), ax = fxx - x0, ay = fyy - y0;
      sum += (cmpAt(map, SH, x0, y0, ref) * (1 - ax) + cmpAt(map, SH, x0 + 1, y0, ref) * ax) * (1 - ay)
        + (cmpAt(map, SH, x0, y0 + 1, ref) * (1 - ax) + cmpAt(map, SH, x0 + 1, y0 + 1, ref) * ax) * ay;
    } else {
      sum += cmpAt(map, SH, Math.floor(su * SH), Math.floor((1 - sv) * SH), ref);
    }
  }
  return sum * 0.2;
}
function frac(x) { return x - Math.floor(x); }
function clamp01(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
function dot3(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
const dot3ext = dot3f;
function normalize3(v) { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; }
function schlick(f0, f90, dotVH) {
  const fres = Math.pow(2, (-5.55473 * dotVH - 6.98316) * dotVH);
  return [0, 1, 2].map(k => f0[k] * (1 - fres) + f90 * fres);
}
function schlickScalar(f0, f90, dotVH) {
  const fres = Math.pow(2, (-5.55473 * dotVH - 6.98316) * dotVH);
  return f0 * (1 - fres) + f90 * fres;
}
// NeutralToneMapping de Three r186 (exposicion aplicada dentro).
function neutralToneMap(c0, exposure) {
  const StartCompression = 0.8 - 0.04, Desaturation = 0.15;
  let c = [c0[0] * exposure, c0[1] * exposure, c0[2] * exposure];
  const x = Math.min(c[0], c[1], c[2]);
  const offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
  c = [c[0] - offset, c[1] - offset, c[2] - offset];
  const peak = Math.max(c[0], c[1], c[2]);
  if (peak < StartCompression) return c;
  const d = 1 - StartCompression;
  const newPeak = 1 - d * d / (peak + d - StartCompression);
  c = [c[0] * newPeak / peak, c[1] * newPeak / peak, c[2] * newPeak / peak];
  const g = 1 - 1 / (Desaturation * (peak - newPeak) + 1);
  return [0, 1, 2].map(k => c[k] * (1 - g) + newPeak * g);
}
function toSRGBf(v) {
  const c = v < 0 ? 0 : v > 1 ? 1 : v;
  const s = c <= 0.0031308 ? c * 12.92 : 1.055 * Math.pow(c, 1 / 2.4) - 0.055;
  return Math.min(1, Math.max(0, s)) * 255;
}

module.exports = { createRenderer, makeCore, prepareCfg, buildTexture, orthoMatrix, lookAtView, mul4, DEBUG };
