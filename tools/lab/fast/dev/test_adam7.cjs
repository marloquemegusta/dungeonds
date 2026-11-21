const zlib = require('node:zlib');
const { decodePng } = require('../png.cjs');
const W = 13, H = 11, ch = 4;
const src = new Uint8Array(W * H * ch);
let s = 3;
for (let i = 0; i < src.length; i++) { s = (s * 1103515245 + 12345) & 0x7fffffff; src[i] = (s >> 16) & 255; }
const passes = [[0, 0, 8, 8], [4, 0, 8, 8], [0, 4, 4, 8], [2, 0, 4, 4], [0, 2, 2, 4], [1, 0, 2, 2], [0, 1, 1, 2]];
const parts = [];
for (const [x0, y0, dx, dy] of passes) {
  const pw = Math.ceil((W - x0) / dx), ph = Math.ceil((H - y0) / dy);
  if (pw <= 0 || ph <= 0) continue;
  const rowLen = pw * ch + 1;
  const raw = Buffer.alloc(rowLen * ph);
  for (let y = 0; y < ph; y++) {
    raw[y * rowLen] = 0; // filter None
    for (let x = 0; x < pw; x++) for (let c = 0; c < ch; c++) {
      raw[y * rowLen + 1 + x * ch + c] = src[((y0 + y * dy) * W + (x0 + x * dx)) * ch + c];
    }
  }
  parts.push(raw);
}
const idat = zlib.deflateSync(Buffer.concat(parts));
function chunk(t, d) {
  const l = Buffer.alloc(4); l.writeUInt32BE(d.length, 0);
  const td = Buffer.concat([Buffer.from(t, 'latin1'), d]);
  const c = Buffer.alloc(4); c.writeUInt32BE(zlib.crc32(td) >>> 0, 0);
  return Buffer.concat([l, td, c]);
}
const ih = Buffer.alloc(13);
ih.writeUInt32BE(W, 0); ih.writeUInt32BE(H, 4); ih[8] = 8; ih[9] = 6; ih[12] = 1;
const png = Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ih), chunk('IDAT', idat), chunk('IEND', Buffer.alloc(0))]);
const dec = decodePng(png);
console.log('adam7 equal', Buffer.from(dec.data).equals(Buffer.from(src)));
