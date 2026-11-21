// Small worker_threads pool: run(type, payload) -> Promise. threads = 0 runs the tasks in-process.
'use strict';
const path = require('node:path');
const { Worker } = require('node:worker_threads');
const { TASKS } = require('./tasks.cjs');

class Pool {
  constructor(threads) {
    this.threads = threads;
    this.idle = [];
    this.queue = [];
    this.nextId = 1;
    this.waiting = new Map();
    this.workers = [];
    for (let i = 0; i < threads; i++) {
      const w = new Worker(path.join(__dirname, 'worker.cjs'));
      w.on('message', (msg) => {
        const job = this.waiting.get(msg.id);
        this.waiting.delete(msg.id);
        this.idle.push(w);
        if (msg.ok) job.resolve(msg.value); else job.reject(new Error(msg.error));
        this.pump();
      });
      w.on('error', (e) => { for (const j of this.waiting.values()) j.reject(e); });
      this.workers.push(w);
      this.idle.push(w);
    }
    // warm the bundle in every worker now (runs while the main thread loads the model)
    for (let i = 0; i < threads; i++) this.run('warm', {}).catch(() => {});
  }

  run(type, payload) {
    if (this.threads === 0) {
      return new Promise((resolve, reject) => {
        try { resolve(TASKS[type](payload)); } catch (e) { reject(e); }
      });
    }
    const dbg = process.env.DS_POOL_DEBUG ? (m) => process.stderr.write(`[pool] ${m}
`) : null;
    if (dbg) dbg(`queued ${type}`);
    return new Promise((resolve, reject) => {
      this.queue.push({ type, payload, resolve: (v) => { if (dbg) dbg(`done ${type}`); resolve(v); }, reject: (e) => { if (dbg) dbg(`ERR ${type} ${e.message}`); reject(e); } });
      this.pump();
    });
  }

  pump() {
    if (process.env.DS_POOL_DEBUG) process.stderr.write(`[pool] pump idle=${this.idle.length} queue=${this.queue.length} waiting=${this.waiting.size}
`);
    while (this.idle.length && this.queue.length) {
      const w = this.idle.shift();
      const job = this.queue.shift();
      const id = this.nextId++;
      this.waiting.set(id, job);
      w.postMessage({ id, type: job.type, payload: job.payload });
    }
  }

  async close() {
    await Promise.all(this.workers.map(w => w.terminate()));
  }
}

module.exports = { Pool };
