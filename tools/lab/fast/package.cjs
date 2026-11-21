// Framing, anchors, muzzle, shadow atlas, C header and package writer (ported from parity.js Qf,
// computeAnchorData, generateCharacterShadows, generateCShadowAnchorHeader, makeAtlas, exportPackage).
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');
const { encodePng } = require('./png.cjs');
const { composite, gif, collage } = require('./post.cjs');

const DIR_NAMES = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE'];
const AZIMUTH = Math.PI / 4;
const DIR0_YAW = 3 * Math.PI / 4;
const DIR_STEP = Math.PI / 4;

function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
function norm(a) { const l = Math.hypot(a[0], a[1], a[2]); return [a[0] / l, a[1] / l, a[2] / l]; }
function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }

// Camera basis of the export view (elevation, azimuth 45 degrees). Ortho camera at center + toCamera * 30.
function viewBasis(elevationDeg) {
  const el = (Math.max(1, elevationDeg) * Math.PI) / 180;
  const toCamera = norm([Math.cos(el) * Math.cos(AZIMUTH), Math.sin(el), -Math.cos(el) * Math.sin(AZIMUTH)]);
  const right = norm(cross([0, 1, 0], toCamera));
  const up = norm(cross(toCamera, right));
  return { toCamera, right, up };
}

// Qf framing: measures the posed extent over the 8 directions and builds the ortho camera.
// samples: [{ meshes: [{positions}], minY }]. Returns the camera and the fit report.
function frameCamera(samples, o) {
  const { size, targetPixels, elevation, fitZoom, fitExtent: fitOpt, warn } = o;
  const { toCamera, right, up } = viewBasis(elevation);
  let minX = Infinity, maxX = -Infinity, minV = Infinity, maxV = -Infinity;
  for (let d = 0; d < 8; d++) {
    const yaw = DIR0_YAW - d * DIR_STEP, c = Math.cos(yaw), s = Math.sin(yaw);
    for (const sm of samples) {
      for (const m of sm.meshes) {
        const p = m.positions;
        for (let i = 0; i < p.length; i += 3) {
          const x = p[i], y = p[i + 1], z = p[i + 2];
          const px = x * c + z * s, pz = -x * s + z * c, py = y - sm.minY;
          const u = px * right[0] + py * right[1] + pz * right[2];
          const w = px * up[0] + py * up[1] + pz * up[2];
          if (u < minX) minX = u; if (u > maxX) maxX = u;
          if (w < minV) minV = w; if (w > maxV) maxV = w;
        }
      }
    }
  }
  const extent = Math.max(maxX - minX, maxV - minV);
  const fitExtent = fitOpt > 0 ? fitOpt : extent;
  const half = fitExtent * size / targetPixels / 2 / (fitZoom || 1);
  if (extent > half * 2 * 1.0005) {
    warn(`CROPPED: extent ${extent.toFixed(4)} m does not fit the camera span ${(half * 2).toFixed(4)} m (fitExtent ${fitExtent.toFixed(4)}, fitZoom ${fitZoom || 1}); the sprite is cut off`);
  }
  const cu = (minX + maxX) / 2, cv = (minV + maxV) / 2;
  const center = [right[0] * cu + up[0] * cv, right[1] * cu + up[1] * cv, right[2] * cu + up[2] * cv];
  const eye = [center[0] + toCamera[0] * 30, center[1] + toCamera[1] * 30, center[2] + toCamera[2] * 30];
  // Column-major view matrix (rows = camera axes), for the renderer contract.
  const viewMatrix = [
    right[0], up[0], toCamera[0], 0,
    right[1], up[1], toCamera[1], 0,
    right[2], up[2], toCamera[2], 0,
    -dot(right, eye), -dot(up, eye), -dot(toCamera, eye), 1,
  ];
  const camera = {
    left: -half, right: half, top: half, bottom: -half, near: 0.1, far: 100, viewMatrix,
    eye, center, basis: { right, up, toCamera },
    // NDC of a world point (ortho: view coordinates divided by the half span).
    ndc(p) {
      const q = [p[0] - eye[0], p[1] - eye[1], p[2] - eye[2]];
      return [dot(q, right) / half, dot(q, up) / half];
    },
  };
  const fit = { extent, fitExtent, half, center, minX, maxX, minV, maxV, camera };
  return { camera, fit, size };
}

// Pixel of a world point in the sprite cell (projection of Qf/ projectMuzzleFrame).
function toPixel(camera, p, size) {
  const n = camera.ndc(p);
  return [(n[0] * 0.5 + 0.5) * size, (-n[1] * 0.5 + 0.5) * size];
}

// computeAnchorData: anchor = projected origin, bounds from alpha >= 25 of the processed frames.
function anchorData(camera, frames, size, frameCount, renderedDirs) {
  const origin = toPixel(camera, [0, 0, 0], size);
  let projAnchorX = Math.round(size / 2), projAnchorY = Math.round(size * 0.85);
  if (isFinite(origin[0]) && isFinite(origin[1])) {
    projAnchorX = Math.max(0, Math.min(size - 1, Math.round(origin[0])));
    projAnchorY = Math.max(0, Math.min(size - 1, Math.round(origin[1])));
  }
  const dirGroundAnchors = new Array(8).fill(projAnchorY);
  const dirBounds = new Array(8);
  const hasFull = !renderedDirs && frames.length === 8 * frameCount;
  const hasSubset = !!renderedDirs && frames.length === renderedDirs.length * frameCount;
  for (let d = 0; d < 8; d++) {
    let dMinX = size, dMaxX = -1, dMinY = size, dMaxY = -1;
    const scan = [];
    if (hasFull) for (let f = 0; f < frameCount; f++) scan.push(frames[d * frameCount + f]);
    else if (hasSubset) {
      const rank = renderedDirs.indexOf(d);
      if (rank >= 0) for (let f = 0; f < frameCount; f++) scan.push(frames[rank * frameCount + f]);
    }
    for (const fr of scan) {
      if (!fr) continue;
      const pix = fr.pixels, w = fr.width || size, h = fr.height || size;
      let fMinX = w, fMaxX = -1, fMinY = h, fMaxY = -1;
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
        if (pix[(y * w + x) * 4 + 3] >= 25) {
          if (x < fMinX) fMinX = x; if (x > fMaxX) fMaxX = x;
          if (y < fMinY) fMinY = y; if (y > fMaxY) fMaxY = y;
        }
      }
      if (fMaxX >= fMinX && fMaxY >= fMinY) {
        if (fMinX < dMinX) dMinX = fMinX; if (fMaxX > dMaxX) dMaxX = fMaxX;
        if (fMinY < dMinY) dMinY = fMinY; if (fMaxY > dMaxY) dMaxY = fMaxY;
      }
    }
    dirBounds[d] = (dMaxX >= dMinX && dMaxY >= dMinY) ? [dMinX, dMinY, dMaxX - dMinX + 1, dMaxY - dMinY + 1] : [0, 0, size, size];
  }
  return { anchor: [projAnchorX, projAnchorY], dirGroundAnchors, dirBounds, projAnchor: [projAnchorX, projAnchorY] };
}

// Muzzle setup (findMuzzleSetup): weapon mesh tip, else a bone pushed forward by forward*height.
function findMuzzle(pose, muzzleBone, muzzleForward, box) {
  const B = pose.B;
  const re = /weapon|rifle|gun/i;
  let best = null, bestScore = -1;
  pose.model.traverse(node => {
    if (!node.isMesh || !node.geometry?.attributes?.position) return;
    const names = `${node.name || ''} ${node.geometry.name || ''}`;
    if (!re.test(names)) return;
    const score = /^WeaponGeo$/i.test(node.name || '') ? 2 : 1;
    if (score > bestScore) { best = node; bestScore = score; }
  });
  if (!best) {
    if (!muzzleBone) return null;
    const norm2 = n => String(n).replace(/[\s\[\]\.:\/]/g, '');
    let bone = null;
    pose.model.traverse(node => { if (!bone && node.isBone && norm2(node.name) === norm2(muzzleBone)) bone = node; });
    if (!bone) return null;
    return { kind: 'bone', bone, forward: muzzleForward ?? 0.05, height: Math.max(1e-6, box.max.y - box.min.y) };
  }
  const pos = best.geometry.attributes.position;
  const n = pos.count;
  if (n < 4) return null;
  const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
  const get = (i, a) => (a === 0 ? pos.getX(i) : a === 1 ? pos.getY(i) : pos.getZ(i));
  for (let i = 0; i < n; i++) for (let a = 0; a < 3; a++) {
    const c = get(i, a);
    if (c < lo[a]) lo[a] = c;
    if (c > hi[a]) hi[a] = c;
  }
  let axis = 0;
  for (let a = 1; a < 3; a++) if (hi[a] - lo[a] > hi[axis] - lo[axis]) axis = a;
  const len = hi[axis] - lo[axis];
  if (!(len > 0)) return null;
  const o1 = (axis + 1) % 3, o2 = (axis + 2) % 3;
  const spread = sign => {
    let a1 = Infinity, b1 = -Infinity, a2 = Infinity, b2 = -Infinity, count = 0;
    for (let i = 0; i < n; i++) {
      const t = (get(i, axis) - lo[axis]) / len;
      if (sign > 0 ? t < 0.9 : t > 0.1) continue;
      const c1 = get(i, o1), c2 = get(i, o2);
      if (c1 < a1) a1 = c1; if (c1 > b1) b1 = c1;
      if (c2 < a2) a2 = c2; if (c2 > b2) b2 = c2;
      count++;
    }
    return count ? (b1 - a1) + (b2 - a2) : Infinity;
  };
  const sign = spread(1) <= spread(-1) ? 1 : -1;
  const tip = [];
  for (let i = 0; i < n; i++) {
    const t = (get(i, axis) - lo[axis]) / len;
    if (sign > 0 ? t >= 0.97 : t <= 0.03) tip.push(i);
  }
  if (!tip.length) return null;
  return { kind: 'mesh', tip, meshNode: best };
}

// One muzzle capture [gx, gy, h] for a root that is yawed and lifted (the render-time root state).
function muzzleCaptureOf(setup, samplePoint, yaw, yOff, camera, size, anchorX, anchorY) {
  const c = Math.cos(yaw), s = Math.sin(yaw);
  // rotate the root-identity point about Y and lift it by yOff
  const m = [samplePoint[0] * c + samplePoint[2] * s, samplePoint[1] + yOff, -samplePoint[0] * s + samplePoint[2] * c];
  if (setup.kind === 'bone') {
    const fwd = [s, 0, c];
    m[0] += fwd[0] * setup.forward * setup.height;
    m[1] += 0;
    m[2] += fwd[2] * setup.forward * setup.height;
  }
  const a = camera.ndc(m);
  const g = camera.ndc([m[0], 0, m[2]]);
  const px = (a[0] * 0.5 + 0.5) * size, py = (-a[1] * 0.5 + 0.5) * size;
  const gpx = (g[0] * 0.5 + 0.5) * size, gpy = (-g[1] * 0.5 + 0.5) * size;
  return [Math.round(gpx - anchorX), Math.round(gpy - anchorY), Math.round(gpy - py)];
}

// Shadow cell (generateCharacterShadows, one frame and one direction): the ground projection of the posed
// mesh with the light offset, filled (nonzero winding) plus the 0.65 px stroke of every edge, sampled on a
// 4x4 grid per shadow pixel. A pixel is kept when the lab's alpha >= 96 threshold is reached (>= 6 of 16 samples).
// Pure function over typed arrays so it can run in a worker: cam = {eye, right, up, half}.
// Stroke radius, calibrated against the lab's shadow masks (corazon: IoU 0.985, count 19887 vs 19880).
// The nominal half-width of the lab's 0.65 px stroke is 0.325; the rendered stroke covers more.
const STROKE_R = 0.8;
const SS = 8;
function shadowFrameCore(job) {
  const { size, minY, fixedGround, anchor, cam, meshes, dirs, shadowLight } = job;
  const shadowSize = size * 2, halfShadow = shadowSize / 2;
  const G = shadowSize * SS;
  const frameMinY = fixedGround ? 0 : minY;
  // horizontal ground offset per metre of height (default: the lab's fixed light; shadowLight overrides it per light azimuth)
  const kx = shadowLight ? shadowLight.kx : -0.4096 / 0.5736, kz = shadowLight ? shadowLight.kz : 0.7094 / 0.5736;
  const { eye, right, up, half } = cam;
  const winding = new Int16Array(G * G);
  const stroke = new Uint8Array(G * G);
  const out = [];
  for (const dir of dirs) {
    const yaw = DIR0_YAW - dir * DIR_STEP;
    const c = Math.cos(yaw), s = Math.sin(yaw);
    winding.fill(0);
    stroke.fill(0);
    let triangleCount = 0;
    for (const m of meshes) {
      const p = m.positions, count = p.length / 3;
      const xs = new Float64Array(count), ys = new Float64Array(count);
      for (let i = 0; i < count; i++) {
        const wx = p[i * 3], wy = p[i * 3 + 1], wz = p[i * 3 + 2];
        const rx = wx * c + wz * s, rz = -wx * s + wz * c;
        const t = Math.max(0, wy - frameMinY);
        const gx = rx + t * kx, gz = rz + t * kz;
        // ortho NDC of the ground point (view basis, half span)
        const qx = gx - eye[0], qy = -eye[1], qz = gz - eye[2];
        const nx = (qx * right[0] + qy * right[1] + qz * right[2]) / half;
        const ny = (qx * up[0] + qy * up[1] + qz * up[2]) / half;
        xs[i] = (nx * 0.5 + 0.5) * size - anchor[0] + halfShadow;
        ys[i] = (-ny * 0.5 + 0.5) * size - anchor[1] + halfShadow;
      }
      const idx = m.index;
      const numTris = idx ? Math.floor(idx.length / 3) : Math.floor(count / 3);
      for (let t = 0; t < numTris; t++) {
        const i0 = idx ? idx[t * 3] : t * 3, i1 = idx ? idx[t * 3 + 1] : t * 3 + 1, i2 = idx ? idx[t * 3 + 2] : t * 3 + 2;
        triangleCount++;
        fillTriangle(winding, G, xs[i0], ys[i0], xs[i1], ys[i1], xs[i2], ys[i2]);
        strokeEdge(stroke, G, xs[i0], ys[i0], xs[i1], ys[i1], STROKE_R);
        strokeEdge(stroke, G, xs[i1], ys[i1], xs[i2], ys[i2], STROKE_R);
        strokeEdge(stroke, G, xs[i2], ys[i2], xs[i0], ys[i0], STROKE_R);
      }
    }
    if (triangleCount === 0) {
      // lab fallback: ellipse(halfShadow - 2, halfShadow + 2, 14, 9, PI / 6), filled
      const cx = halfShadow - 2, cy = halfShadow + 2, rx = 14, ry = 9, th = Math.PI / 6;
      for (let sy = 0; sy < G; sy++) for (let sx = 0; sx < G; sx++) {
        const x = (sx + 0.5) / SS - cx, y = (sy + 0.5) / SS - cy;
        const u = x * Math.cos(th) + y * Math.sin(th), v = -x * Math.sin(th) + y * Math.cos(th);
        if ((u * u) / (rx * rx) + (v * v) / (ry * ry) <= 1) winding[sy * G + sx] = 1;
      }
    }
    const mask = new Uint8Array(shadowSize * shadowSize);
    let minX = shadowSize, maxX = -1, minYp = shadowSize, maxYp = -1;
    for (let y = 0; y < shadowSize; y++) for (let x = 0; x < shadowSize; x++) {
      let nf = 0, ns = 0;
      for (let j = 0; j < SS; j++) {
        const row = (y * SS + j) * G + x * SS;
        for (let i = 0; i < SS; i++) {
          if (winding[row + i] !== 0) nf++;
          if (stroke[row + i]) ns++;
        }
      }
      // Skia composes fill and stroke separately over transparent: a = 1 - (1 - aFill)(1 - aStroke)
      const aF = nf / (SS * SS), aS = ns / (SS * SS);
      const aT = 1 - (1 - aF) * (1 - aS);
      if (Math.round(aT * 255) >= 96) {
        mask[y * shadowSize + x] = 1;
        if (x < minX) minX = x; if (x > maxX) maxX = x;
        if (y < minYp) minYp = y; if (y > maxYp) maxYp = y;
      }
    }
    const bounds = (maxX >= minX && maxYp >= minYp)
      ? [minX, minYp, maxX - minX + 1, maxYp - minYp + 1]
      : [halfShadow - 8, halfShadow - 8, 16, 16];
    out.push({ dir, mask, bounds });
  }
  return out;
}

// Nonzero winding of one triangle on the sub-sample centres (+1 / -1 by orientation).
function fillTriangle(winding, G, ax, ay, bx, by, cx, cy) {
  const area = (bx - ax) * (cy - ay) - (cx - ax) * (by - ay);
  if (Math.abs(area) < 1e-12) return;
  const sgn = area > 0 ? 1 : -1;
  const minx = Math.max(0, Math.floor(Math.min(ax, bx, cx) * SS - 0.5));
  const maxx = Math.min(G - 1, Math.ceil(Math.max(ax, bx, cx) * SS + 0.5));
  const miny = Math.max(0, Math.floor(Math.min(ay, by, cy) * SS - 0.5));
  const maxy = Math.min(G - 1, Math.ceil(Math.max(ay, by, cy) * SS + 0.5));
  const bax = bx - ax, bay = by - ay, cbx = cx - bx, cby = cy - by, cax = ax - cx, cay = ay - cy;
  for (let sy = miny; sy <= maxy; sy++) {
    const py = (sy + 0.5) / SS;
    for (let sx = minx; sx <= maxx; sx++) {
      const px = (sx + 0.5) / SS;
      const e0 = bax * (py - ay) - bay * (px - ax);
      const e1 = cbx * (py - by) - cby * (px - bx);
      const e2 = cax * (py - cy) - cay * (px - cx);
      if (sgn > 0 ? (e0 >= 0 && e1 >= 0 && e2 >= 0) : (e0 <= 0 && e1 <= 0 && e2 <= 0)) {
        winding[sy * G + sx] += sgn;
      }
    }
  }
}

// Marks the sub-samples within r px of the segment a-b (round caps and joins of the lab stroke).
function strokeEdge(stroke, G, ax, ay, bx, by, r) {
  const minx = Math.max(0, Math.floor((Math.min(ax, bx) - r) * SS - 0.5));
  const maxx = Math.min(G - 1, Math.ceil((Math.max(ax, bx) + r) * SS + 0.5));
  const miny = Math.max(0, Math.floor((Math.min(ay, by) - r) * SS - 0.5));
  const maxy = Math.min(G - 1, Math.ceil((Math.max(ay, by) + r) * SS + 0.5));
  const dx = bx - ax, dy = by - ay;
  const l2 = dx * dx + dy * dy;
  const inv = l2 > 0 ? 1 / l2 : 0;
  const r2 = r * r;
  for (let sy = miny; sy <= maxy; sy++) {
    const py = (sy + 0.5) / SS;
    for (let sx = minx; sx <= maxx; sx++) {
      if (stroke[sy * G + sx]) continue;
      const px = (sx + 0.5) / SS;
      let t = ((px - ax) * dx + (py - ay) * dy) * inv;
      t = t < 0 ? 0 : t > 1 ? 1 : t;
      const qx = ax + t * dx - px, qy = ay + t * dy - py;
      if (qx * qx + qy * qy <= r2) stroke[sy * G + sx] = 1;
    }
  }
}

// Assembles the atlas from per-frame results: results[f] = [{dir, mask, bounds}].
function assembleShadows(results, size, frameCount) {
  const shadowSize = size * 2, halfShadow = shadowSize / 2;
  const atlasW = frameCount * shadowSize, atlasH = 8 * shadowSize;
  const atlas = new Uint8Array(atlasW * atlasH * 4);
  const shadowBounds = Array.from({ length: 8 }, () => new Array(frameCount));
  const masks = Array.from({ length: 8 }, () => new Array(frameCount));
  for (let f = 0; f < frameCount; f++) {
    for (const cell of results[f]) {
      const { dir, mask, bounds } = cell;
      shadowBounds[dir][f] = bounds;
      for (let y = 0; y < shadowSize; y++) for (let x = 0; x < shadowSize; x++) {
        if (mask[y * shadowSize + x]) atlas[((dir * shadowSize + y) * atlasW + f * shadowSize + x) * 4 + 3] = 192;
      }
      const packed = new Uint8Array(shadowSize * shadowSize / 2);
      for (let i = 0; i < shadowSize * shadowSize; i += 2) {
        const lo = mask[i] ? 15 : 0, hi = mask[i + 1] ? 15 : 0;
        packed[i / 2] = ((hi & 0x0f) << 4) | (lo & 0x0f);
      }
      masks[dir][f] = packed;
    }
  }
  return { shadowSize, shadowBounds, masks, atlas, atlasW, atlasH, halfShadow };
}

// generateCShadowAnchorHeader (same text as parity.js).
function cHeader(name, anchor, dirGroundAnchors, dirBounds, shadowBounds, masks, shadowSize, size, frameCount) {
  const cleanName = name.replace(/[^a-zA-Z0-9_]/g, '_');
  const guard = `${cleanName.toUpperCase()}_NDS_SHADOW_ANCHOR_H`;
  const U = cleanName.toUpperCase();
  const maskBytes = (shadowSize * shadowSize) / 2;
  let c = `/* Auto-generated by DungeonDS FBX Web Renderer Lab */\n`;
  c += `#ifndef ${guard}\n#define ${guard}\n\n`;
  c += `#include <stdint.h>\n\n`;
  c += `#define ${U}_ANCHOR_X ${anchor[0]}\n`;
  c += `#define ${U}_ANCHOR_Y ${anchor[1]}\n`;
  c += `#define ${U}_SHADOW_W ${shadowSize}\n`;
  c += `#define ${U}_SHADOW_H ${shadowSize}\n`;
  c += `#define ${U}_NUM_DIRS 8\n`;
  c += `#define ${U}_NUM_FRAMES ${frameCount}\n\n`;
  c += `// Ground anchor Y per direction (3D ground origin projected in sprite canvas)\n`;
  c += `static const uint8_t g_${cleanName}_ground_anchors[8] = {\n`;
  c += `    ` + dirGroundAnchors.map(v => `${v}`).join(', ') + `\n`;
  c += `};\n\n`;
  c += `// Sprite bounding boxes [min_x, min_y, w, h] per direction\n`;
  c += `static const uint8_t g_${cleanName}_sprite_bounds[8][4] = {\n`;
  for (let d = 0; d < 8; d++) {
    const b = dirBounds[d] || [0, 0, size, size];
    c += `    { ${b[0]}, ${b[1]}, ${b[2]}, ${b[3]} },\n`;
  }
  c += `};\n\n`;
  c += `// Shadow bounding boxes [sx0, sy0, w, h] per direction and frame in ${shadowSize}x${shadowSize} shadow canvas\n`;
  c += `static const uint8_t g_${cleanName}_shadow_bounds[8][${frameCount}][4] = {\n`;
  for (let d = 0; d < 8; d++) {
    c += `    {\n`;
    for (let f = 0; f < frameCount; f++) {
      const b = shadowBounds[d][f];
      c += `        { ${b[0]}, ${b[1]}, ${b[2]}, ${b[3]} },\n`;
    }
    c += `    },\n`;
  }
  c += `};\n\n`;
  c += `// 4-bit packed shadow coverage masks (${shadowSize}x${shadowSize} / 2 = ${maskBytes} bytes per frame)\n`;
  c += `static const uint8_t g_${cleanName}_shadow_masks[8][${frameCount}][${maskBytes}] __attribute__((aligned(4))) = {\n`;
  for (let d = 0; d < 8; d++) {
    c += `    // Direction ${d} (${DIR_NAMES[d]})\n    {\n`;
    for (let f = 0; f < frameCount; f++) {
      c += `        // Frame ${f}\n        {\n`;
      const mask = masks[d][f];
      for (let i = 0; i < maskBytes; i += 16) {
        c += `            `;
        for (let j = 0; j < 16 && i + j < maskBytes; j++) {
          c += `0x${mask[i + j].toString(16).padStart(2, '0').toUpperCase()}, `;
        }
        c += `\n`;
      }
      c += `        },\n`;
    }
    c += `    },\n`;
  }
  c += `};\n\n`;
  c += `#endif /* ${guard} */\n`;
  return c;
}

// Canvas round trip of a straight-alpha frame (putImageData + toBlob): premultiply then unpremultiply.
function canvasRoundTrip(px) {
  const out = new Uint8Array(px.length);
  for (let i = 0; i < px.length; i += 4) {
    const a = px[i + 3];
    if (a === 0) continue;
    if (a === 255) { out[i] = px[i]; out[i + 1] = px[i + 1]; out[i + 2] = px[i + 2]; out[i + 3] = 255; continue; }
    for (let c = 0; c < 3; c++) {
      const pm = Math.round((px[i + c] * a) / 255);
      out[i + c] = Math.min(255, Math.round((pm * 255) / a));
    }
    out[i + 3] = a;
  }
  return out;
}

function pngOf(frame, size) {
  return encodePng(size, size, canvasRoundTrip(frame.pixels));
}

const README = (name, frameCount, size) => `# ${name}\n\nSpritesheet PNG: ${frameCount} columnas (frames), ${DIR_NAMES.length} filas (direcciones), ${size}x${size}px por celda, RGBA transparente.\n\nIncluye atlas de sombras NDS (768x96 px), mascaras 4-bit, bounds de sombra por direccion, codigo C listo para Nintendo DS (nds_shadow_anchor.h), GIF por direccion, collage GIF, PNG por frame y settings.json. Orden: ${DIR_NAMES.join(', ')}.\n`;

// Writes the package directly into outDir (no zip). `pkg` carries everything computed by the exporter.
function writePackage(outDir, pkg) {
  const write = (rel, data) => {
    const p = path.join(outDir, rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, data);
  };
  const { frames, frameCount, size, results, collageBuf, renderedDirs, shadow, cHeaderText, settings } = pkg;
  const subset = renderedDirs;
  fs.mkdirSync(outDir, { recursive: true });
  if (!subset) {
    write('spritesheet.png', pkg.sheetBuf || encodePng(frameCount * size, 8 * size, atlasPixels(frames, size, frameCount)));
  }
  if (collageBuf) write('collage.gif', collageBuf);
  if (!subset && shadow) {
    write('shadow.png', pkg.shadowBuf || encodePng(shadow.atlasW, shadow.atlasH, shadow.atlas));
    const S = shadow.shadowSize;
    for (let d = 0; d < 8; d++) {
      const cell = new Uint8Array(S * S * 4);
      for (let y = 0; y < S; y++) {
        const src = ((d * S + y) * shadow.atlasW) * 4;
        cell.set(shadow.atlas.subarray(src, src + S * 4), y * S * 4);
      }
      write(`shadows/${d}_${DIR_NAMES[d]}.png`, encodePng(S, S, cell));
    }
  }
  if (!subset) write('nds_shadow_anchor.h', cHeaderText);
  for (const r of results) write(`dirs/${r.index}_${r.name}.gif`, r.buf);
  const dirOrder = subset || Array.from({ length: 8 }, (_, d) => d);
  for (let index = 0; index < frames.length; index++) {
    const d = dirOrder[Math.floor(index / frameCount)];
    const f = index % frameCount;
    write(`frames/${d}_${DIR_NAMES[d]}/${f}.png`, pkg.frameBufs ? pkg.frameBufs[index] : pngOf(frames[index], size));
  }
  write('settings.json', JSON.stringify(settings, null, 2));
  write('README.md', README(settings.name, frameCount, size));
}

// spritesheet pixels: 8 rows (directions) x frameCount columns, straight alpha.
function atlasPixels(frames, size, frameCount) {
  const W = frameCount * size, H = 8 * size;
  const out = new Uint8Array(W * H * 4);
  for (let index = 0; index < frames.length; index++) {
    const fr = frames[index];
    const ox = (index % frameCount) * size, oy = Math.floor(index / frameCount) * size;
    for (let y = 0; y < size; y++) {
      const dst = ((oy + y) * W + ox) * 4;
      out.set(fr.pixels.subarray(y * size * 4, (y + 1) * size * 4), dst);
    }
  }
  return out;
}

module.exports = {
  DIR_NAMES, DIR0_YAW, DIR_STEP, AZIMUTH,
  frameCamera, toPixel, anchorData, findMuzzle, muzzleCaptureOf, shadowFrameCore, assembleShadows, cHeader,
  writePackage, canvasRoundTrip, viewBasis, atlasPixels,
};
