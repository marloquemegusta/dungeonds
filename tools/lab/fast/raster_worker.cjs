// Worker del rasterizador (raster.cjs). Mensajes:
//   build  -> construye los niveles de mip de una textura (en SharedArrayBuffer) y los devuelve
//   init   -> crea el nucleo de render con la config ya completa
//   frames -> fija los fotogramas (SharedArrayBuffer, sin respuesta)
//   render -> renderiza los trabajos asignados y devuelve los RGBA (transferidos)
'use strict';
const { parentPort } = require('node:worker_threads');
const { makeCore, buildTexture } = require('./raster.cjs');

let core = null;
parentPort.on('message', (msg) => {
  if (msg.type === 'build') {
    parentPort.postMessage({ id: msg.id, res: buildTexture(msg.tex) });
  } else if (msg.type === 'init') {
    core = makeCore(msg.cfg);
    parentPort.postMessage({ id: msg.id });
  } else if (msg.type === 'frames') {
    core.setFrames(msg.frames);
  } else if (msg.type === 'render') {
    const out = msg.jobs.map(j => core.renderJob(j, msg.cam));
    const bufs = out.map(o => o.buffer);
    parentPort.postMessage({ id: msg.id, idx: msg.idx, out: bufs }, bufs);
  }
});
