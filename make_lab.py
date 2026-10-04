import os
import base64

with open(r"C:\codexlocal\dungeonds\raw_sheet_b64.txt", "r") as f:
    b64_data = f.read().strip()

html_template = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>DS Sprite Lab - DungeonDS Preview & Tuning</title>
<style>
  :root {
    --bg: #12141a;
    --panel: #1a1e27;
    --border: #2e3548;
    --accent: #ff4757;
    --text: #e1e4ea;
    --muted: #8b92a5;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace;
    display: flex;
    height: 100vh;
    overflow: hidden;
  }
  #sidebar {
    width: 360px;
    background: var(--panel);
    border-right: 1px solid var(--border);
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    overflow-y: auto;
  }
  h1 { font-size: 1.1rem; color: #fff; display: flex; align-items: center; gap: 8px; }
  .badge { background: #2f3542; color: #70a1ff; font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; }
  .group {
    background: #151821;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .group-title {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
    font-weight: 700;
  }
  .row { display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; }
  label { font-size: 0.8rem; color: #ced6e0; }
  input[type="range"] {
    width: 100%;
    margin-top: 4px;
    accent-color: #3742fa;
  }
  select, input[type="file"], button {
    background: #222736;
    border: 1px solid var(--border);
    color: #fff;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 0.8rem;
    width: 100%;
    cursor: pointer;
  }
  button:hover { background: #2f3542; }
  .btn-accent {
    background: #3742fa;
    border-color: #5352ed;
    font-weight: 600;
  }
  .btn-accent:hover { background: #5352ed; }
  
  #main {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 24px;
    gap: 20px;
    position: relative;
  }
  .viewport-card {
    background: #171b24;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  }
  .canvas-wrapper {
    position: relative;
    border: 2px dashed #303952;
    border-radius: 8px;
    overflow: hidden;
  }
  .bg-checker {
    background-color: #202430;
    background-image: 
      linear-gradient(45deg, #282d3c 25%, transparent 25%), 
      linear-gradient(-45deg, #282d3c 25%, transparent 25%), 
      linear-gradient(45deg, transparent 75%, #282d3c 75%), 
      linear-gradient(-45deg, transparent 75%, #282d3c 75%);
    background-size: 16px 16px;
    background-position: 0 0, 8px 8px;
  }
  .bg-dungeon {
    background: #191414;
    background-image: radial-gradient(#3a2720 15%, transparent 16%), radial-gradient(#251815 15%, transparent 16%);
    background-size: 32px 32px;
    background-position: 0 0, 16px 16px;
  }
  .bg-black { background: #000; }
  
  canvas {
    display: block;
    image-rendering: -moz-crisp-edges;
    image-rendering: -webkit-crisp-edges;
    image-rendering: pixelated;
    image-rendering: crisp-edges;
  }
  .dir-selector {
    display: grid;
    grid-template-columns: repeat(3, 40px);
    grid-template-rows: repeat(3, 40px);
    gap: 6px;
    justify-content: center;
  }
  .dir-btn {
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
    height: 40px;
    border-radius: 6px;
  }
  .dir-btn.active {
    background: #ff4757;
    border-color: #ff6b81;
    font-weight: bold;
  }
  .hud {
    font-size: 0.8rem;
    color: var(--muted);
    display: flex;
    gap: 16px;
  }
</style>
<script src="https://cdn.jsdelivr.net/npm/gifshot@0.3.2/build/gifshot.min.js"></script>
</head>
<body>

<div id="sidebar">
  <div>
    <h1>DS Sprite Lab <span class="badge">64x64 NN</span></h1>
    <p style="font-size:0.75rem; color: var(--muted); margin-top:4px;">Tuning en vivo para sprites pre-renderizados NDS</p>
  </div>

  <div class="group">
    <div class="group-title">Visualización y Zoom NN</div>
    <div class="row">
      <label>Escala Nearest-Neighbor:</label>
      <select id="scaleSelect" style="width:100px;">
        <option value="1">1x (64px)</option>
        <option value="2">2x (128px)</option>
        <option value="4" selected>4x (256px)</option>
        <option value="8">8x (512px)</option>
      </select>
    </div>
    <div class="row">
      <label>Fondo:</label>
      <select id="bgSelect" style="width:130px;">
        <option value="bg-dungeon" selected>Dungeon Floor</option>
        <option value="bg-checker">Ajedrez Transp.</option>
        <option value="bg-black">Negro Puro</option>
      </select>
    </div>
    <div class="row">
      <label>FPS Animación: <span id="fpsVal">8</span></label>
      <input type="range" id="fpsSlider" min="2" max="24" value="8">
    </div>
  </div>

  <div class="group">
    <div class="group-title">Legibilidad & Pixel Art Filters</div>
    <div>
      <div class="row">
        <label>Contorno 1px (Outline):</label>
        <input type="checkbox" id="outlineCheck" checked>
      </div>
      <div class="row" style="margin-top:6px;">
        <label>Color Contorno:</label>
        <input type="color" id="outlineColor" value="#101018" style="width:60px; height:24px; padding:0; border:none;">
      </div>
    </div>
    <div>
      <div class="row"><label>Contraste: <span id="contrastVal">1.4</span></label></div>
      <input type="range" id="contrastSlider" min="0.8" max="2.5" step="0.05" value="1.4">
    </div>
    <div>
      <div class="row"><label>Brillo: <span id="brightVal">1.15</span></label></div>
      <input type="range" id="brightSlider" min="0.5" max="1.8" step="0.05" value="1.15">
    </div>
    <div>
      <div class="row"><label>Saturación: <span id="satVal">1.3</span></label></div>
      <input type="range" id="satSlider" min="0.0" max="2.5" step="0.05" value="1.3">
    </div>
    <div class="row">
      <label>Sombra bajo pies (DS Ground):</label>
      <input type="checkbox" id="shadowCheck" checked>
    </div>
    <div class="row">
      <label>Póster/Indexación (Colores NDS):</label>
      <select id="posterSelect" style="width:110px;">
        <option value="0" selected>RGB Completo</option>
        <option value="32">32 Colores</option>
        <option value="16">16 Colores</option>
      </select>
    </div>
  </div>

  <div class="group">
    <div class="group-title">Dirección (8 Ángulos)</div>
    <div class="dir-selector">
      <button class="dir-btn" data-dir="3">&#8598;</button>
      <button class="dir-btn" data-dir="4">&#8593;</button>
      <button class="dir-btn" data-dir="5">&#8599;</button>
      <button class="dir-btn" data-dir="2">&#8592;</button>
      <div style="display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:0.7rem;">&#9678;</div>
      <button class="dir-btn" data-dir="6">&#8594;</button>
      <button class="dir-btn" data-dir="1">&#8601;</button>
      <button class="dir-btn active" data-dir="0">&#8595;</button>
      <button class="dir-btn" data-dir="7">&#8600;</button>
    </div>
  </div>

  <div class="group">
    <div class="group-title">Cargar otro Spritesheet</div>
    <input type="file" id="fileInput" accept="image/png, image/jpeg">
    <button class="btn-accent" id="exportGifBtn">Descargar GIF Escalado (NN)</button>
  </div>
</div>

<div id="main">
  <div class="viewport-card">
    <div class="canvas-wrapper bg-dungeon" id="canvasWrap">
      <canvas id="viewCanvas" width="256" height="256"></canvas>
    </div>
    <div class="hud">
      <span>Frame nativo: 64&times;64</span>
      <span>|</span>
      <span id="scaleLabel">Visual: 256&times;256 (4x NN)</span>
      <span>|</span>
      <span id="dirLabel">Dir: 0 (Sur / Frontal)</span>
    </div>
  </div>
</div>

<script>
const base64Data = "data:image/png;base64,__B64_DATA__";

const rawImg = new Image();
rawImg.src = base64Data;

const viewCanvas = document.getElementById('viewCanvas');
const ctx = viewCanvas.getContext('2d', { willReadFrequently: true });
ctx.imageSmoothingEnabled = false;

const frameW = 64;
const frameH = 64;
const numFrames = 8;
const numDirs = 8;

const nativeCanvas = document.createElement('canvas');
nativeCanvas.width = frameW;
nativeCanvas.height = frameH;
const nativeCtx = nativeCanvas.getContext('2d', { willReadFrequently: true });

let currentDir = 0;
let currentFrame = 0;
let currentScale = 4;
let fps = 8;
let lastTick = performance.now();

const dirBtns = document.querySelectorAll('.dir-btn');
const dirNames = [
  '0 (Sur / Frontal)',
  '1 (Sudoeste)',
  '2 (Oeste / Lateral)',
  '3 (Noroeste)',
  '4 (Norte / Espalda)',
  '5 (Noreste)',
  '6 (Este / Lateral)',
  '7 (Sudeste)'
];

dirBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    dirBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentDir = parseInt(btn.dataset.dir);
    document.getElementById('dirLabel').textContent = 'Dir: ' + dirNames[currentDir];
  });
});

const scaleSelect = document.getElementById('scaleSelect');
const bgSelect = document.getElementById('bgSelect');
const canvasWrap = document.getElementById('canvasWrap');
const fpsSlider = document.getElementById('fpsSlider');
const fpsVal = document.getElementById('fpsVal');

const outlineCheck = document.getElementById('outlineCheck');
const outlineColor = document.getElementById('outlineColor');
const contrastSlider = document.getElementById('contrastSlider');
const contrastVal = document.getElementById('contrastVal');
const brightSlider = document.getElementById('brightSlider');
const brightVal = document.getElementById('brightVal');
const satSlider = document.getElementById('satSlider');
const satVal = document.getElementById('satVal');
const shadowCheck = document.getElementById('shadowCheck');
const posterSelect = document.getElementById('posterSelect');

scaleSelect.addEventListener('change', () => {
  currentScale = parseInt(scaleSelect.value);
  viewCanvas.width = frameW * currentScale;
  viewCanvas.height = frameH * currentScale;
  document.getElementById('scaleLabel').textContent = `Visual: ${viewCanvas.width}x${viewCanvas.height} (${currentScale}x NN)`;
});

bgSelect.addEventListener('change', () => {
  canvasWrap.className = 'canvas-wrapper ' + bgSelect.value;
});

fpsSlider.addEventListener('input', () => {
  fps = parseInt(fpsSlider.value);
  fpsVal.textContent = fps;
});

contrastSlider.addEventListener('input', () => contrastVal.textContent = contrastSlider.value);
brightSlider.addEventListener('input', () => brightVal.textContent = brightSlider.value);
satSlider.addEventListener('input', () => satVal.textContent = satSlider.value);

document.getElementById('fileInput').addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (evt) => {
    rawImg.src = evt.target.result;
  };
  reader.readAsDataURL(file);
});

function renderProcessedFrame(dir, fIdx) {
  nativeCtx.clearRect(0, 0, frameW, frameH);

  if (shadowCheck.checked) {
    nativeCtx.save();
    nativeCtx.beginPath();
    nativeCtx.ellipse(frameW / 2, frameH - 9, 14, 5, 0, 0, Math.PI * 2);
    nativeCtx.fillStyle = 'rgba(10, 8, 12, 0.45)';
    nativeCtx.fill();
    nativeCtx.restore();
  }

  const sx = fIdx * frameW;
  const sy = dir * frameH;
  nativeCtx.drawImage(rawImg, sx, sy, frameW, frameH, 0, 0, frameW, frameH);

  const imgData = nativeCtx.getImageData(0, 0, frameW, frameH);
  const data = imgData.data;

  const contrast = parseFloat(contrastSlider.value);
  const brightness = parseFloat(brightSlider.value);
  const saturation = parseFloat(satSlider.value);
  const posterStep = parseInt(posterSelect.value);

  const cf = (259 * (contrast * 255 + 255)) / (255 * (259 - contrast * 255));

  for (let i = 0; i < data.length; i += 4) {
    if (data[i + 3] === 0) continue;

    let r = data[i];
    let g = data[i + 1];
    let b = data[i + 2];

    r *= brightness;
    g *= brightness;
    b *= brightness;

    r = cf * (r - 128) + 128;
    g = cf * (g - 128) + 128;
    b = cf * (b - 128) + 128;

    const gray = 0.2989 * r + 0.5870 * g + 0.1140 * b;
    r = gray + saturation * (r - gray);
    g = gray + saturation * (g - gray);
    b = gray + saturation * (b - gray);

    if (posterStep > 0) {
      const step = 256 / posterStep;
      r = Math.floor(r / step) * step;
      g = Math.floor(g / step) * step;
      b = Math.floor(b / step) * step;
    }

    data[i] = Math.max(0, Math.min(255, r));
    data[i + 1] = Math.max(0, Math.min(255, g));
    data[i + 2] = Math.max(0, Math.min(255, b));
  }

  nativeCtx.putImageData(imgData, 0, 0);

  if (outlineCheck.checked) {
    const hex = outlineColor.value;
    const ocR = parseInt(hex.slice(1, 3), 16);
    const ocG = parseInt(hex.slice(3, 5), 16);
    const ocB = parseInt(hex.slice(5, 7), 16);

    const outData = nativeCtx.createImageData(frameW, frameH);
    const dOut = outData.data;
    const src = imgData.data;

    for (let y = 0; y < frameH; y++) {
      for (let x = 0; x < frameW; x++) {
        const idx = (y * frameW + x) * 4;
        if (src[idx + 3] > 30) {
          dOut[idx] = src[idx];
          dOut[idx + 1] = src[idx + 1];
          dOut[idx + 2] = src[idx + 2];
          dOut[idx + 3] = src[idx + 3];
          continue;
        }

        let hasNeighbor = false;
        const neighbors = [[x - 1, y], [x + 1, y], [x, y - 1], [x, y + 1]];
        for (let n = 0; n < neighbors.length; n++) {
          const nx = neighbors[n][0];
          const ny = neighbors[n][1];
          if (nx >= 0 && nx < frameW && ny >= 0 && ny < frameH) {
            const nIdx = (ny * frameW + nx) * 4;
            if (src[nIdx + 3] > 60) {
              hasNeighbor = true;
              break;
            }
          }
        }

        if (hasNeighbor) {
          dOut[idx] = ocR;
          dOut[idx + 1] = ocG;
          dOut[idx + 2] = ocB;
          dOut[idx + 3] = 255;
        }
      }
    }
    nativeCtx.putImageData(outData, 0, 0);
  }
}

function loop(now) {
  requestAnimationFrame(loop);

  if (now - lastTick >= (1000 / fps)) {
    lastTick = now;
    currentFrame = (currentFrame + 1) % numFrames;
  }

  renderProcessedFrame(currentDir, currentFrame);

  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, viewCanvas.width, viewCanvas.height);
  ctx.drawImage(nativeCanvas, 0, 0, frameW, frameH, 0, 0, viewCanvas.width, viewCanvas.height);
}

rawImg.onload = () => {
  requestAnimationFrame(loop);
};

document.getElementById('exportGifBtn').addEventListener('click', () => {
  const exportBtn = document.getElementById('exportGifBtn');
  exportBtn.textContent = 'Generando GIF NN...';
  exportBtn.disabled = true;

  const tempCanv = document.createElement('canvas');
  tempCanv.width = frameW * currentScale;
  tempCanv.height = frameH * currentScale;
  const tCtx = tempCanv.getContext('2d');
  tCtx.imageSmoothingEnabled = false;

  const gifFrames = [];
  for (let f = 0; f < numFrames; f++) {
    renderProcessedFrame(currentDir, f);
    tCtx.clearRect(0, 0, tempCanv.width, tempCanv.height);
    tCtx.drawImage(nativeCanvas, 0, 0, frameW, frameH, 0, 0, tempCanv.width, tempCanv.height);
    gifFrames.push(tempCanv.toDataURL('image/png'));
  }

  gifshot.createGIF({
    images: gifFrames,
    gifWidth: tempCanv.width,
    gifHeight: tempCanv.height,
    interval: 1 / fps,
    numFrames: numFrames
  }, (obj) => {
    exportBtn.textContent = 'Descargar GIF Escalado (NN)';
    exportBtn.disabled = false;
    if (!obj.error) {
      const a = document.createElement('a');
      a.href = obj.image;
      a.download = `sprite_dir_${currentDir}_${currentScale}x_nn.gif`;
      a.click();
    } else {
      alert('Error generando GIF: ' + obj.error);
    }
  });
});
</script>
</body>
</html>
"""

final_html = html_template.replace("__B64_DATA__", b64_data)

with open(r"C:\codexlocal\dungeonds\sprite_lab.html", "w", encoding="utf-8") as f:
    f.write(final_html)

print("sprite_lab.html written successfully!")
