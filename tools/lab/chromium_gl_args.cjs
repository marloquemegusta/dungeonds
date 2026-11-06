// Chromium flags for headless lab renders.
// Default: real GPU through ANGLE/D3D11 (seconds per character instead of minutes).
// LAB_GL=swiftshader forces the software renderer (machines without GPU, or A/B checks).
'use strict';
function labGlArgs() {
  const mode = (process.env.LAB_GL || 'gpu').toLowerCase();
  const common = ['--enable-webgl', '--disable-dev-shm-usage', '--no-sandbox'];
  if (mode === 'swiftshader') {
    return common.concat(['--use-angle=swiftshader', '--enable-unsafe-swiftshader']);
  }
  return common.concat(['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist']);
}
module.exports = { labGlArgs };
