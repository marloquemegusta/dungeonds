// Development stand-in for raster.cjs with the same API (see export_character_fast.cjs).
// Software z-buffer, per-vertex Lambert with the key/fill/ambient terms, no shadows, no texture filtering
// beyond the texture average. It exists only to test the pipeline end to end and to check silhouettes/alpha;
// the real renderer (raster.cjs) replaces it for the spritesheet and frames.
'use strict';

function srgb(c) { return c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055; }
function norm3(v) { const l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; }

function avgColor(tex) {
  if (!tex) return null;
  let r = 0, g = 0, b = 0;
  const n = tex.width * tex.height;
  const d = tex.data;
  for (let i = 0; i < n; i++) { r += d[i * 4]; g += d[i * 4 + 1]; b += d[i * 4 + 2]; }
  const k = 1 / (255 * n);
  return [r * k, g * k, b * k];
}

async function createRenderer(opts) {
  const size = opts.size, ss = opts.ss || 1, W = size * ss, H = size * ss;
  const meshes = opts.meshes;
  const mats = opts.materials.map(m => {
    const base = m.map ? (avgColor(m.map) || [1, 1, 1]) : m.color;
    return { base: base.map((c, i) => c * (m.map ? m.color[i] : 1)) };
  });
  const L = opts.lighting;
  const keyDir = norm3(L.key.position), fillDir = norm3(L.fill.position), rimDir = norm3(L.rim.position);
  const keyC = L.key.color.map(c => c * L.key.intensity * 0.5);
  const fillC = L.fill.color.map(c => c * L.fill.intensity * 0.5);
  const rimC = L.rim.color.map(c => c * L.rim.intensity * 0.5);
  const amb = L.ambient.color.map(c => c * L.ambient.intensity * 0.5);
  let frames = null;
  return {
    setFrames(f) { frames = f; },
    async render(jobs, cam) {
      const out = [];
      const m = cam.viewMatrix, half = cam.right; // ortho half span
      const depth = new Float32Array(W * H);
      for (const job of jobs) {
        const fr = frames[job.frame];
        const yaw = job.yaw, c = Math.cos(yaw), s = Math.sin(yaw), yo = job.yOffset;
        depth.fill(-Infinity);
        const buf = new Uint8ClampedArray(W * H * 4);
        for (let mi = 0; mi < meshes.length; mi++) {
          const mesh = meshes[mi], pos = fr.positions[mi], nrm = fr.normals[mi];
          const nv = pos.length / 3;
          const sx = new Float32Array(nv), sy = new Float32Array(nv), sz = new Float32Array(nv), col = new Float32Array(nv * 3);
          const mat = mats[mesh.materialIndex] || { base: [0.6, 0.6, 0.6] };
          for (let i = 0; i < nv; i++) {
            const x = pos[i * 3], y = pos[i * 3 + 1], z = pos[i * 3 + 2];
            const px = x * c + z * s, py = y + yo, pz = -x * s + z * c;
            const vx = m[0] * px + m[4] * py + m[8] * pz + m[12];
            const vy = m[1] * px + m[5] * py + m[9] * pz + m[13];
            const vz = m[2] * px + m[6] * py + m[10] * pz + m[14];
            sx[i] = ((vx / half) * 0.5 + 0.5) * W;
            sy[i] = (-(vy / half) * 0.5 + 0.5) * H;
            sz[i] = vz;
            const nx = nrm[i * 3], ny = nrm[i * 3 + 1], nz = nrm[i * 3 + 2];
            const rnx = nx * c + nz * s, rny = ny, rnz = -nx * s + nz * c;
            const nd = [rnx, rny, rnz];
            const k = Math.max(0, nd[0] * keyDir[0] + nd[1] * keyDir[1] + nd[2] * keyDir[2]);
            const f = Math.max(0, nd[0] * fillDir[0] + nd[1] * fillDir[1] + nd[2] * fillDir[2]);
            const r = Math.max(0, nd[0] * rimDir[0] + nd[1] * rimDir[1] + nd[2] * rimDir[2]);
            for (let ch = 0; ch < 3; ch++) col[i * 3 + ch] = mat.base[ch] * (amb[ch] + keyC[ch] * k + fillC[ch] * f + rimC[ch] * r);
          }
          const idx = mesh.indices;
          for (let t = 0; t + 2 < idx.length; t += 3) {
            const a = idx[t], b = idx[t + 1], d2 = idx[t + 2];
            raster(buf, depth, W, H, sx, sy, sz, col, a, b, d2);
          }
        }
        // tone: clamp + sRGB encode, alpha from coverage
        const outBuf = new Uint8ClampedArray(W * H * 4);
        for (let p = 0; p < W * H; p++) {
          if (buf[p * 4 + 3] === 0) continue;
          for (let ch = 0; ch < 3; ch++) outBuf[p * 4 + ch] = Math.round(255 * srgb(Math.min(1, buf[p * 4 + ch] / 255)));
          outBuf[p * 4 + 3] = 255;
        }
        out.push(outBuf);
      }
      return out;
    },
    async close() {},
  };
}

function raster(buf, depth, W, H, sx, sy, sz, col, a, b, c) {
  const x0 = sx[a], y0 = sy[a], x1 = sx[b], y1 = sy[b], x2 = sx[c], y2 = sy[c];
  const area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0);
  if (Math.abs(area) < 1e-9) return;
  const minx = Math.max(0, Math.floor(Math.min(x0, x1, x2)));
  const maxx = Math.min(W - 1, Math.ceil(Math.max(x0, x1, x2)));
  const miny = Math.max(0, Math.floor(Math.min(y0, y1, y2)));
  const maxy = Math.min(H - 1, Math.ceil(Math.max(y0, y1, y2)));
  const inv = 1 / area;
  for (let py = miny; py <= maxy; py++) {
    const yc = py + 0.5;
    for (let px = minx; px <= maxx; px++) {
      const xc = px + 0.5;
      const w0 = ((x1 - xc) * (y2 - yc) - (x2 - xc) * (y1 - yc)) * inv;
      const w1 = ((x2 - xc) * (y0 - yc) - (x0 - xc) * (y2 - yc)) * inv;
      const w2 = 1 - w0 - w1;
      if (w0 < -1e-6 || w1 < -1e-6 || w2 < -1e-6) continue;
      const z = w0 * sz[a] + w1 * sz[b] + w2 * sz[c];
      const p = py * W + px;
      if (z <= depth[p]) continue;
      depth[p] = z;
      for (let ch = 0; ch < 3; ch++) {
        buf[p * 4 + ch] = Math.min(255, Math.max(0, 255 * (w0 * col[a * 3 + ch] + w1 * col[b * 3 + ch] + w2 * col[c * 3 + ch])));
      }
      buf[p * 4 + 3] = 255;
    }
  }
}

module.exports = { createRenderer };
