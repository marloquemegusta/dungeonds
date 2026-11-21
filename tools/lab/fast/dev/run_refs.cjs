// Dev runner: exports the four reference characters with the arguments rebuild_all.py would pass
// (characters.json entries; cireneo_charge takes fitExtent/normScale from cireneo as scaleRef does).
// usage: node dev/run_refs.cjs <outRoot> [--only name] [--fast-only]
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const MAIN = 'C:/codexlocal/dungeonds';
const CLI = path.join(__dirname, '..', 'export_character_fast.cjs');
const outRoot = process.argv[2];
const only = process.argv.includes('--only') ? process.argv[process.argv.indexOf('--only') + 1] : null;
const cases = {
  corazon: ['assets/models/characters/corazon/corazon_walk.fbx', 'corazon_walk (1.07s)', 40, ['--fitZoom', '0.86', '--muzzleBone', 'mixamorig:Spine2', '--muzzleForward', '0.05'], 'assets/sprites/characters/corazon/settings.json'],
  exvoto: ['assets/models/characters/exvoto/exvoto_walk.fbx', 'exvoto_walk (1.47s)', 40, ['--fitZoom', '0.86'], 'assets/sprites/characters/skeleton/settings.json'],
  cireneo: ['assets/models/characters/cireneo/cireneo_walk.fbx', 'cireneo_walk (1.63s)', 60, ['--fitZoom', '0.88'], 'assets/sprites/characters/cireneo/settings.json'],
  cireneo_charge: ['assets/models/characters/cireneo/cireneo_charge.fbx', 'cireneo_charge (0.96s)', 60,
    ['--fitZoom', '0.88', '--fitExtent', '1.872183561426501', '--normScale', '0.018199056080475513'], 'assets/sprites/characters/cireneo_charge/settings.json'],
};
for (const [name, [model, anim, res, extra, tpl]] of Object.entries(cases)) {
  if (only && only !== name) continue;
  const args = [CLI, path.join(MAIN, model), path.join(outRoot, name), '--template', path.join(MAIN, tpl), '--anim', anim,
    '--resolution', String(res), ...extra, '--light', 'neutral', '--outline', 'none', '--saturation', '1.0', '--legibility', 'c2', '--timing'];
  const t0 = Date.now();
  const r = spawnSync(process.execPath, args, { encoding: 'utf8' });
  const lines = (r.stdout || '').split('\n').filter(l => /^(FIT|TIMING|WARNING|LOG|package)/.test(l) || l.trim());
  console.log(`== ${name} exit ${r.status} in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  for (const l of lines.slice(-6)) console.log('   ' + l.slice(0, 260));
  if (r.stderr && r.stderr.trim()) console.log('   stderr: ' + r.stderr.trim().slice(0, 600));
}
