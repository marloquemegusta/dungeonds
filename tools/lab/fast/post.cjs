// Post-processing of rendered frames (ported from the offline lab bundle and parity.js):
// Blackman-Harris downsample, contrast/saturation (zf), outline (Rf), brightness, C2 legibility,
// composite over the background (Bf), gifenc GIF writer (the bundle's own gifenc module), collage.
// All rounding goes through Uint8ClampedArray assignments, like the browser code does.
'use strict';
const { loadBundle, bundleU8 } = require('./pose.cjs');

const BG = [16, 14, 20];          // Vf (composite background)
const OUTLINE = [16, 16, 24];     // Pf (outline colour)
const LEG_CURVE_GAIN = 1.45, LEG_SHARPEN_AMOUNT = 0.5, LEG_EDGE_ALPHA = 77;

function blackmanHarris(distance, width) {
  const t = distance / width + 0.5;
  if (t < 0 || t > 1) return 0;
  const phase = 2 * Math.PI * t;
  return 0.35875 - 0.48829 * Math.cos(phase) + 0.14128 * Math.cos(2 * phase) - 0.01168 * Math.cos(3 * phase);
}

// Alpha-weighted supersample -> size x size (parity.js downsample). Returns Uint8ClampedArray.
function downsample(source, size, ss, filterWidth) {
  if (ss === 1) return Uint8ClampedArray.from(source);
  const wide = size * ss;
  const out = new Uint8ClampedArray(size * size * 4);
  const radius = filterWidth / 2;
  // Precompute the 1D weights per output pixel and sub-sample row/col (the kernel is separable).
  for (let oy = 0; oy < size; oy++) {
    const cy = (oy + 0.5) * ss;
    const sy0 = Math.max(0, Math.floor(cy - radius * ss)), sy1 = Math.min(wide - 1, Math.ceil(cy + radius * ss));
    for (let ox = 0; ox < size; ox++) {
      const cx = (ox + 0.5) * ss;
      const sx0 = Math.max(0, Math.floor(cx - radius * ss)), sx1 = Math.min(wide - 1, Math.ceil(cx + radius * ss));
      let r = 0, g = 0, b = 0, a = 0, weight = 0;
      for (let sy = sy0; sy <= sy1; sy++) {
        const wy = blackmanHarris((sy + 0.5 - cy) / ss, filterWidth);
        if (!wy) continue;
        for (let sx = sx0; sx <= sx1; sx++) {
          const w = wy * blackmanHarris((sx + 0.5 - cx) / ss, filterWidth);
          if (!w) continue;
          const i = (sy * wide + sx) * 4;
          const alpha = source[i + 3] / 255;
          r += source[i] * alpha * w; g += source[i + 1] * alpha * w; b += source[i + 2] * alpha * w;
          a += alpha * w; weight += w;
        }
      }
      const o = (oy * size + ox) * 4;
      if (a > 1e-6) { out[o] = r / a; out[o + 1] = g / a; out[o + 2] = b / a; }
      out[o + 3] = weight ? Math.round((255 * a) / weight) : 0;
    }
  }
  return out;
}

// zf: contrast around 128, then saturation about Rec.709 luma (alpha untouched).
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

// Rf: outline of 1 px in OUTLINE colour around opaque (alpha > 40) pixels, 4-neighbourhood.
function outline(e, w, h, mode) {
  if (mode === 'none' || mode === undefined) return e;
  const i = new Uint8ClampedArray(e);
  const a = new Uint8Array(w * h);
  for (let k = 0; k < w * h; k++) a[k] = +(e[k * 4 + 3] > 40);
  const nb = [[-1, 0], [1, 0], [0, -1], [0, 1]];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const s = y * w + x;
    if (a[s]) continue;
    let touch = false;
    for (const [dx, dy] of nb) {
      const xx = x + dx, yy = y + dy;
      if (!(xx < 0 || yy < 0 || xx >= w || yy >= h) && a[yy * w + xx]) { touch = true; break; }
    }
    if (touch) {
      const o = s * 4;
      i[o] = OUTLINE[0]; i[o + 1] = OUTLINE[1]; i[o + 2] = OUTLINE[2]; i[o + 3] = 255;
    }
  }
  return i;
}

// Kf without the capture: grade -> brightness -> outline. Returns the processed (straight alpha) frame.
function processFrame(ssPixels, size, ss, params) {
  const down = downsample(ssPixels, size, ss, params.filterWidth ?? 1.5);
  let graded = gradeContrastSaturation(down, params.contrast, params.saturation);
  const brightness = params.brightness ?? 1;
  if (brightness !== 1) {
    for (let k = 0; k < graded.length; k += 4) {
      graded[k] = graded[k] * brightness;
      graded[k + 1] = graded[k + 1] * brightness;
      graded[k + 2] = graded[k + 2] * brightness;
    }
  }
  let processed = outline(graded, size, size, params.outlineMode);
  if (!(processed instanceof Uint8ClampedArray)) processed = new Uint8ClampedArray(processed);
  return { pixels: new Uint8ClampedArray(processed), width: size, height: size };
}

// Bf: composite a straight-alpha frame over BG, alpha forced to 255 (GIF/collage input).
function composite(pixels, w, h, bg = BG) {
  const i = new Uint8ClampedArray(w * h * 4);
  for (let a = 0; a < w * h; a++) {
    const t = pixels[a * 4 + 3] / 255, n = a * 4;
    i[n] = pixels[n] * t + bg[0] * (1 - t);
    i[n + 1] = pixels[n + 1] * t + bg[1] * (1 - t);
    i[n + 2] = pixels[n + 2] * t + bg[2] * (1 - t);
    i[n + 3] = 255;
  }
  return i;
}

// C2 legibility (parity.js applyLegibilityC2): one luminance pivot over all frames, S-curve, alpha-aware sharpen.
function legibilityPivot(frames) {
  const lum = [];
  for (const f of frames) {
    const px = f.pixels;
    for (let i = 0; i < px.length; i += 4) {
      if (px[i + 3] > 0) lum.push(0.2126 * (px[i] / 255) + 0.7152 * (px[i + 1] / 255) + 0.0722 * (px[i + 2] / 255));
    }
  }
  if (!lum.length) return 0.5;
  const sorted = Float64Array.from(lum).sort();
  const n = sorted.length;
  return n % 2 ? sorted[(n - 1) / 2] : (sorted[n / 2 - 1] + sorted[n / 2]) / 2;
}

function blur3(src, w, h, channels) {
  const k0 = 0.25, k1 = 0.5, k2 = 0.25;
  const tmp = new Float64Array(src.length), out = new Float64Array(src.length);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const xl = Math.max(0, x - 1), xr = Math.min(w - 1, x + 1);
    for (let c = 0; c < channels; c++) {
      tmp[(y * w + x) * channels + c] = k0 * src[(y * w + xl) * channels + c] + k1 * src[(y * w + x) * channels + c] + k2 * src[(y * w + xr) * channels + c];
    }
  }
  for (let y = 0; y < h; y++) {
    const yu = Math.max(0, y - 1), yd = Math.min(h - 1, y + 1);
    for (let x = 0; x < w; x++) for (let c = 0; c < channels; c++) {
      out[(y * w + x) * channels + c] = k0 * tmp[(yu * w + x) * channels + c] + k1 * tmp[(y * w + x) * channels + c] + k2 * tmp[(yd * w + x) * channels + c];
    }
  }
  return out;
}

function applyLegibilityC2(frames, pivotOverride) {
  const gain = LEG_CURVE_GAIN;
  const p = (typeof pivotOverride === 'number' && isFinite(pivotOverride)) ? pivotOverride : legibilityPivot(frames);
  for (const f of frames) {
    const px = f.pixels, w = f.width, h = f.height;
    for (let i = 0; i < px.length; i += 4) {
      if (px[i + 3] === 0) continue;
      const r = px[i] / 255, g = px[i + 1] / 255, b = px[i + 2] / 255;
      const L = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      const d = L - p;
      const m = d < 0 ? p : 1 - p;
      const out = p + d * gain / (1 + (gain - 1) * Math.abs(d) / Math.max(m, 1e-4));
      const scale = L > 1e-4 ? out / Math.max(L, 1e-4) : 1;
      px[i] = Math.floor(Math.min(1, Math.max(0, r * scale)) * 255);
      px[i + 1] = Math.floor(Math.min(1, Math.max(0, g * scale)) * 255);
      px[i + 2] = Math.floor(Math.min(1, Math.max(0, b * scale)) * 255);
    }
    const n = w * h;
    const rgbm = new Float64Array(n * 3), mask = new Float64Array(n);
    for (let j = 0; j < n; j++) {
      const m = px[j * 4 + 3] >= LEG_EDGE_ALPHA ? 1 : 0;
      mask[j] = m;
      rgbm[j * 3] = px[j * 4] * m; rgbm[j * 3 + 1] = px[j * 4 + 1] * m; rgbm[j * 3 + 2] = px[j * 4 + 2] * m;
    }
    const bl = blur3(rgbm, w, h, 3), bm = blur3(mask, w, h, 1);
    for (let j = 0; j < n; j++) {
      if (px[j * 4 + 3] === 0) continue;
      const den = Math.max(bm[j], 1e-3);
      for (let c = 0; c < 3; c++) {
        const v = px[j * 4 + c];
        px[j * 4 + c] = Math.floor(Math.min(255, Math.max(0, v + LEG_SHARPEN_AMOUNT * (v - bl[j * 3 + c] / den))));
      }
    }
  }
  return p;
}

// GIF writer: the bundle's gifenc (quantize 256, applyPalette, dispose 1). Returns a Buffer.
function gif(frames, w, h, delay) {
  const Mf = loadBundle().Mf;
  const enc = Mf.GIFEncoder();
  for (let a = 0; a < frames.length; a++) {
    // gifenc wants a plain Uint8Array view over the same bytes
    const o = bundleU8(new Uint8Array(frames[a].buffer, frames[a].byteOffset, frames[a].byteLength));
    const palette = Mf.quantize(o, 256);
    const index = Mf.applyPalette(o, palette);
    enc.writeFrame(index, w, h, { palette, delay, repeat: 0, dispose: a === 0 ? -1 : 1 });
  }
  enc.finish();
  return Buffer.from(enc.bytes());
}

// $f: 4 columns x 2 rows collage of up to 8 composited first frames, one still GIF with delay 0.
function collage(firstFrames, size) {
  const n = 4 * size, r = 2 * size;
  const i = new Uint8ClampedArray(n * r * 4);
  for (let k = 0; k < n * r; k++) {
    const t = k * 4;
    i[t] = BG[0]; i[t + 1] = BG[1]; i[t + 2] = BG[2]; i[t + 3] = 255;
  }
  for (let k = 0; k < firstFrames.length && k < 8; k++) {
    const a = firstFrames[k];
    const col = k % 4, row = Math.floor(k / 4);
    const c = col * size, l = row * size;
    for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
      const o = (y * size + x) * 4;
      const s = ((l + y) * n + (c + x)) * 4;
      i[s] = a[o]; i[s + 1] = a[o + 1]; i[s + 2] = a[o + 2]; i[s + 3] = 255;
    }
  }
  return gif([i], n, r, 0);
}

module.exports = { canvasRoundTripPx: (px) => require('./package.cjs').canvasRoundTrip(px), downsample, processFrame, composite, applyLegibilityC2, legibilityPivot, gif, collage, BG, blackmanHarris };
