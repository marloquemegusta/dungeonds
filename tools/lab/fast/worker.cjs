// Worker thread entry: runs one task per message and answers with the same id.
'use strict';
const { parentPort } = require('node:worker_threads');
const { TASKS } = require('./tasks.cjs');

parentPort.on('message', (msg) => {
  try {
    const value = TASKS[msg.type](msg.payload);
    parentPort.postMessage({ id: msg.id, ok: true, value });
  } catch (e) {
    parentPort.postMessage({ id: msg.id, ok: false, error: String((e && e.stack) || e) });
  }
});
