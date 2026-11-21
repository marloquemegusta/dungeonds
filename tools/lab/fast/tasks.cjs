// Work items run either in a worker thread (worker.cjs) or in-process (DS_FAST_THREADS=0).
'use strict';
const pkg = require('./package.cjs');
const post = require('./post.cjs');
const { decodePng, encodePng } = require('./png.cjs');

const TASKS = {
  // loads the bundle (gifenc) in this worker while the main thread loads the model
  warm: () => { require('./pose.cjs').loadBundle(); return true; },
  // frames -> PNG bytes (canvas round trip as in package.cjs pngOf)
  pngFrames: (p) => p.items.map(it => new Uint8Array(encodePng(p.size, p.size, post.canvasRoundTripPx(it.pixels)))),
  // one 8-bit RGBA image -> PNG bytes
  pngImage: (p) => new Uint8Array(encodePng(p.width, p.height, p.pixels)),
  // C2 legibility with a pivot given by the main thread (per direction), then composite + GIF;
  // returns the GIF and the processed frames (the PNG frames need them).
  gifC2: (p) => {
    if (typeof p.pivot === 'number') post.applyLegibilityC2(p.frames, p.pivot);
    const frames = p.frames.map(f => post.composite(f.pixels, p.size, p.size));
    const gif = new Uint8Array(post.gif(frames, p.size, p.size, p.delay));
    // the PNG frames of this direction are encoded here too (same worker, no extra round trip)
    const pngs = p.frames.map(f => new Uint8Array(encodePng(p.size, p.size, post.canvasRoundTripPx(f.pixels))));
    return { gif, frames: p.frames, pngs };
  },
  // embedded PNG texture -> {width, height, data RGBA}
  png: (bytes) => { const d = decodePng(Buffer.from(bytes.buffer, bytes.byteOffset, bytes.byteLength)); return { width: d.width, height: d.height, data: d.data }; },
  // one frame, the 8 directions: [{dir, mask, bounds}]
  shadow: (p) => pkg.shadowFrameCore(p),
  // one direction: downsample + grade + outline per frame (straight alpha, processed)
  proc: (p) => p.bufs.map(b => {
    const f = post.processFrame(b, p.size, p.ss, p.params);
    return { pixels: f.pixels, width: f.width, height: f.height };
  }),
  // one direction: composite over the background and encode the GIF; returns a Uint8Array
  gif: (p) => {
    const frames = p.frames.map(f => post.composite(f.pixels, p.size, p.size));
    return new Uint8Array(post.gif(frames, p.size, p.size, p.delay));
  },
};

module.exports = { TASKS };
