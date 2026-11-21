// PNG decoder/encoder for the fast character exporter (Node only: zlib + Buffer).
// decodePng(buf) -> { width, height, data: Uint8Array RGBA8 (straight alpha) }
// encodePng(width, height, rgba) -> Buffer (8-bit RGBA, filter None per row)
'use strict';
const zlib = require('node:zlib');

const SIG = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

function readChunks(buf) {
  if (!buf.subarray(0, 8).equals(SIG)) throw new Error('png: bad signature');
  const chunks = [];
  let p = 8;
  while (p + 8 <= buf.length) {
    const len = buf.readUInt32BE(p);
    const type = buf.toString('latin1', p + 4, p + 8);
    chunks.push({ type, data: buf.subarray(p + 8, p + 8 + len) });
    p += 12 + len;
    if (type === 'IEND') break;
  }
  return chunks;
}

const CHANNELS = { 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 };

// Paeth predictor and the five PNG filters, applied in place to one scanline.
function unfilterRow(type, row, prev, bpp, out) {
  const n = row.length;
  switch (type) {
    case 0: for (let i = 0; i < n; i++) out[i] = row[i]; break;
    case 1: for (let i = 0; i < n; i++) out[i] = (row[i] + (i >= bpp ? out[i - bpp] : 0)) & 255; break;
    case 2: for (let i = 0; i < n; i++) out[i] = (row[i] + prev[i]) & 255; break;
    case 3:
      for (let i = 0; i < n; i++) {
        const left = i >= bpp ? out[i - bpp] : 0;
        out[i] = (row[i] + ((left + prev[i]) >> 1)) & 255;
      }
      break;
    case 4:
      for (let i = 0; i < n; i++) {
        const a = i >= bpp ? out[i - bpp] : 0, b = prev[i], c = i >= bpp ? prev[i - bpp] : 0;
        const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
        const pr = (pa <= pb && pa <= pc) ? a : (pb <= pc ? b : c);
        out[i] = (row[i] + pr) & 255;
      }
      break;
    default: throw new Error('png: bad filter ' + type);
  }
}

// Decodes one (sub)image of `w` x `h` pixels from a raw inflated stream starting at `off`.
// Returns { next: offset after the consumed data, pixels: Uint8Array of w*h*CH samples (unpacked to 8 bit) }.
function decodePass(raw, off, w, h, colorType, bitDepth, palette, trns) {
  const ch = CHANNELS[colorType];
  const bitsPerPixel = ch * bitDepth;
  const bpp = Math.max(1, bitsPerPixel >> 3);
  const stride = Math.ceil((w * bitsPerPixel) / 8);
  const outSamples = new Uint8Array(w * h * ch);
  if (w === 0 || h === 0) return { next: off, pixels: outSamples };
  let prev = new Uint8Array(stride);
  let cur = new Uint8Array(stride);
  let p = off;
  const maxVal = (1 << bitDepth) - 1;
  for (let y = 0; y < h; y++) {
    const filter = raw[p];
    const row = raw.subarray(p + 1, p + 1 + stride);
    unfilterRow(filter, row, prev, bpp, cur);
    p += 1 + stride;
    for (let x = 0; x < w; x++) {
      for (let c = 0; c < ch; c++) {
        const idx = x * ch + c;
        let v;
        if (bitDepth === 8) v = cur[idx];
        else if (bitDepth === 16) v = cur[idx * 2]; // high byte
        else {
          const bit = idx * bitDepth;
          v = (cur[bit >> 3] >> (8 - bitDepth - (bit & 7))) & maxVal;
          if (colorType !== 3) v = Math.round((v * 255) / maxVal);
        }
        outSamples[(y * w + x) * ch + c] = v;
      }
    }
    const t = prev; prev = cur; cur = t;
  }
  return { next: p, pixels: outSamples };
}

function decodePng(buf) {
  const chunks = readChunks(buf);
  const ihdr = chunks.find(c => c.type === 'IHDR');
  if (!ihdr) throw new Error('png: no IHDR');
  const width = ihdr.data.readUInt32BE(0), height = ihdr.data.readUInt32BE(4);
  const bitDepth = ihdr.data[8], colorType = ihdr.data[9], interlace = ihdr.data[12];
  if (!(colorType in CHANNELS)) throw new Error('png: bad color type ' + colorType);
  const idat = Buffer.concat(chunks.filter(c => c.type === 'IDAT').map(c => c.data));
  const raw = new Uint8Array(zlib.inflateSync(idat));
  if (bitDepth === 8 && interlace === 0 && (colorType === 6 || colorType === 2)) {
    return { width, height, data: decodeFast8(raw, width, height, colorType) };
  }
  const plte = chunks.find(c => c.type === 'PLTE');
  const palette = plte ? plte.data : null;
  const trnsChunk = chunks.find(c => c.type === 'tRNS');
  const trns = trnsChunk ? trnsChunk.data : null;
  const ch = CHANNELS[colorType];
  const samples = new Uint8Array(width * height * ch);

  // Adam7 passes (interlace 1) or the whole image (interlace 0).
  const passes = interlace === 1
    ? [[0, 0, 8, 8], [4, 0, 8, 8], [0, 4, 4, 8], [2, 0, 4, 4], [0, 2, 2, 4], [1, 0, 2, 2], [0, 1, 1, 2]]
    : [[0, 0, 1, 1]];
  let off = 0;
  for (const [x0, y0, dx, dy] of passes) {
    const pw = Math.ceil((width - x0) / dx), ph = Math.ceil((height - y0) / dy);
    if (pw <= 0 || ph <= 0) continue;
    const r = decodePass(raw, off, pw, ph, colorType, bitDepth, palette, trns);
    off = r.next;
    for (let y = 0; y < ph; y++) for (let x = 0; x < pw; x++) {
      const dst = ((y0 + y * dy) * width + (x0 + x * dx)) * ch;
      const src = (y * pw + x) * ch;
      for (let c = 0; c < ch; c++) samples[dst + c] = r.pixels[src + c];
    }
  }

  // Expand to RGBA8.
  const rgba = new Uint8Array(width * height * 4);
  const n = width * height;
  if (colorType === 6) {
    if (bitDepth === 8) rgba.set(samples.subarray(0, n * 4));
    else for (let i = 0; i < n * 4; i++) rgba[i] = samples[i];
  } else if (colorType === 2) {
    for (let i = 0; i < n; i++) {
      rgba[i * 4] = samples[i * 3]; rgba[i * 4 + 1] = samples[i * 3 + 1]; rgba[i * 4 + 2] = samples[i * 3 + 2]; rgba[i * 4 + 3] = 255;
    }
    if (trns && trns.length >= 6) {
      const tr = trns.readUInt16BE(0), tg = trns.readUInt16BE(2), tb = trns.readUInt16BE(4);
      for (let i = 0; i < n; i++) {
        if (samples[i * 3] === tr && samples[i * 3 + 1] === tg && samples[i * 3 + 2] === tb) rgba[i * 4 + 3] = 0;
      }
    }
  } else if (colorType === 0) {
    for (let i = 0; i < n; i++) {
      const g = samples[i];
      rgba[i * 4] = rgba[i * 4 + 1] = rgba[i * 4 + 2] = g; rgba[i * 4 + 3] = 255;
    }
    if (trns && trns.length >= 2) {
      const tg = trns.readUInt16BE(0);
      for (let i = 0; i < n; i++) if (samples[i] === tg) rgba[i * 4 + 3] = 0;
    }
  } else if (colorType === 4) {
    for (let i = 0; i < n; i++) {
      const g = samples[i * 2];
      rgba[i * 4] = rgba[i * 4 + 1] = rgba[i * 4 + 2] = g; rgba[i * 4 + 3] = samples[i * 2 + 1];
    }
  } else if (colorType === 3) {
    if (!palette) throw new Error('png: indexed image without PLTE');
    for (let i = 0; i < n; i++) {
      const k = samples[i];
      rgba[i * 4] = palette[k * 3]; rgba[i * 4 + 1] = palette[k * 3 + 1]; rgba[i * 4 + 2] = palette[k * 3 + 2];
      rgba[i * 4 + 3] = trns && k < trns.length ? trns[k] : 255;
    }
  }
  return { width, height, data: rgba };
}


// Fast path: 8-bit RGB/RGBA, not interlaced (the common case for embedded textures). Unfilters into one
// buffer with typed loops per filter type and expands RGB to RGBA; RGBA is returned without a copy.
function decodeFast8(raw, width, height, colorType) {
  const ch = colorType === 6 ? 4 : 3;
  const stride = width * ch;
  const out = new Uint8Array(stride * height);
  let p = 0;
  for (let y = 0; y < height; y++) {
    const filter = raw[p++];
    const o = y * stride;
    const pr = o - stride; // previous row offset in out (only valid when y > 0)
    if (filter === 0) {
      out.set(raw.subarray(p, p + stride), o);
    } else if (filter === 1) { // Sub
      for (let i = 0; i < ch && i < stride; i++) out[o + i] = raw[p + i];
      for (let i = ch; i < stride; i++) out[o + i] = (raw[p + i] + out[o + i - ch]) & 255;
    } else if (filter === 2) { // Up
      if (y === 0) out.set(raw.subarray(p, p + stride), o);
      else for (let i = 0; i < stride; i++) out[o + i] = (raw[p + i] + out[pr + i]) & 255;
    } else if (filter === 3) { // Average
      for (let i = 0; i < stride; i++) {
        const left = i >= ch ? out[o + i - ch] : 0;
        const up = y > 0 ? out[pr + i] : 0;
        out[o + i] = (raw[p + i] + ((left + up) >> 1)) & 255;
      }
    } else if (filter === 4) { // Paeth
      for (let i = 0; i < stride; i++) {
        const a = i >= ch ? out[o + i - ch] : 0;
        const b = y > 0 ? out[pr + i] : 0;
        const c = (i >= ch && y > 0) ? out[pr + i - ch] : 0;
        const pp = a + b - c;
        const pa = pp > a ? pp - a : a - pp;
        const pb = pp > b ? pp - b : b - pp;
        const pc = pp > c ? pp - c : c - pp;
        const pred = (pa <= pb && pa <= pc) ? a : (pb <= pc ? b : c);
        out[o + i] = (raw[p + i] + pred) & 255;
      }
    } else {
      throw new Error('png: bad filter ' + filter);
    }
    p += stride;
  }
  if (ch === 4) return out;
  const rgba = new Uint8Array(width * height * 4);
  for (let i = 0, j = 0, n = width * height; i < n; i++, j += 3) {
    const d = i * 4;
    rgba[d] = out[j]; rgba[d + 1] = out[j + 1]; rgba[d + 2] = out[j + 2]; rgba[d + 3] = 255;
  }
  return rgba;
}

// Encodes 8-bit RGBA (straight alpha). `rgba` may be a Uint8Array or Uint8ClampedArray.
function encodePng(width, height, rgba) {
  const stride = width * 4;
  const raw = Buffer.alloc((stride + 1) * height);
  for (let y = 0; y < height; y++) {
    raw[y * (stride + 1)] = 0;
    Buffer.from(rgba.buffer, rgba.byteOffset + y * stride, stride).copy(raw, y * (stride + 1) + 1);
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0); ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; ihdr[9] = 6; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
  const chunk = (type, data) => {
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length, 0);
    const td = Buffer.concat([Buffer.from(type, 'latin1'), data]);
    const crc = Buffer.alloc(4); crc.writeUInt32BE(zlib.crc32 ? zlib.crc32(td) >>> 0 : crc32(td), 0);
    return Buffer.concat([len, td, crc]);
  };
  return Buffer.concat([
    SIG,
    chunk('IHDR', ihdr),
    chunk('IDAT', zlib.deflateSync(raw, { level: 6 })),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

// Fallback CRC32 (only used on Node builds without zlib.crc32).
let CRC_TABLE = null;
function crc32(buf) {
  if (!CRC_TABLE) {
    CRC_TABLE = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      CRC_TABLE[n] = c >>> 0;
    }
  }
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]) & 255] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

module.exports = { decodePng, encodePng };
