const fs = require('node:fs'); const path = require('node:path');
const { decodePng, encodePng } = require('../png.cjs');
const dir = process.argv[2];
const expect = require('node:child_process');
// round trip
const w = 37, h = 23; const data = new Uint8Array(w * h * 4);
let s = 7; for (let i = 0; i < data.length; i++) { s = (s * 1103515245 + 12345) & 0x7fffffff; data[i] = s >> 16 & 255; }
const enc = encodePng(w, h, data); const dec = decodePng(enc);
console.log('roundtrip', dec.width === w && dec.height === h && Buffer.from(dec.data).equals(Buffer.from(data)) ? 'OK' : 'FAIL');
fs.writeFileSync(path.join(dir, 'rt.png'), enc);
for (const f of ['rgba.png', 'rgb.png', 'gray.png', 'pal.png', 'rgba_adam.png']) {
  const p = decodePng(fs.readFileSync(path.join(dir, f)));
  console.log(f, p.width, p.height, p.data.length, p.data.slice(0, 8).join(','));
}
