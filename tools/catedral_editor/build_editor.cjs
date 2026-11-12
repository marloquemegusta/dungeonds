const fs = require('fs');
const path = require('path');

// Directorios base
const repoRoot = path.resolve(__dirname, '../..');
const propsDir = path.join(repoRoot, 'assets/environment/cathedral/props/render');
const floorPath = path.join(repoRoot, 'assets/environment/cathedral/floor/rombos_tripo/floor_512x256.png');
const wallPath = path.join(repoRoot, 'assets/environment/cathedral/muros/muro_izq_128.png');
const lapidasDir = path.join(repoRoot, 'assets/environment/cathedral/lapidas');
const lapidasMetaPath = path.join(lapidasDir, 'lapidas_meta.json');
const godraysDir = path.join(repoRoot, 'assets/sprites/godrays');
const templatePath = path.join(__dirname, 'editor_template.html');
const outputPath = path.join(__dirname, 'editor.html');

function fileToBase64Png(filePath) {
  if (!fs.existsSync(filePath)) return null;
  const buffer = fs.readFileSync(filePath);
  return `data:image/png;base64,${buffer.toString('base64')}`;
}

// Categorías conocidas y nombres amigables
const friendlyNames = {
  columna_entera: 'Columna entera (40×120)',
  columna: 'Columna rota (40×56)',
  banco_entero: 'Banco entero (64×32)',
  banco_roto: 'Banco roto (72×40)',
  banco_volcado: 'Banco volcado (72×32)',
  santo: 'Estatua Santo (32×72)',
  relicario: 'Relicario (32×40)',
  sacos: 'Sacos (64×40)',
  vela: 'Vela (32×24)',
  marine: 'Marine (16×31 px)',
  haz_vidriera: 'Haz vidriera (256×128)',
  haz_roseton: 'Haz rosetón (256×128)'
};

function getCategory(pieceName) {
  if (pieceName === 'marine') return 'especial';
  if (pieceName === 'columna' || pieceName === 'columna_entera') return 'columnas';
  if (pieceName.startsWith('banco')) return 'bancos';
  if (pieceName === 'santo' || pieceName === 'relicario' || pieceName === 'sacos' || pieceName === 'vela') return 'atrezo';
  if (pieceName === 'haz_vidriera' || pieceName === 'haz_roseton') return 'luz';
  if (pieceName.startsWith('via_') || pieceName.startsWith('lapida')) return 'lapidas';
  return 'otros';
}

console.log('Compilando editor de planta de la catedral...');

// 1. Cargar textura de suelo
if (!fs.existsSync(floorPath)) {
  console.error('Error: no se encontró la textura de suelo en:', floorPath);
  process.exit(1);
}
const floorBase64 = fileToBase64Png(floorPath);
console.log('Textura de suelo cargada (512×256 px).');

// 2. Cargar textura de muro (muro_izq_128.png)
if (!fs.existsSync(wallPath)) {
  console.error('Error: no se encontró la textura de muro en:', wallPath);
  process.exit(1);
}
const wallBase64 = fileToBase64Png(wallPath);
console.log('Textura de muro cargada (48×128 px).');

// 3. Procesar piezas generales (excluyendo lápidas viejas)
const props = {};
const entries = fs.readdirSync(propsDir, { withFileTypes: true });

for (const entry of entries) {
  if (!entry.isDirectory()) continue;
  const pieceName = entry.name;

  // Quitar de la paleta las 36 lápidas viejas
  if (pieceName.startsWith('lapida')) {
    continue;
  }

  const dir = path.join(propsDir, pieceName);
  const metaPath = path.join(dir, 'meta.json');
  const colorPath = path.join(dir, 'color.png');
  const shadowPath = path.join(dir, 'shadow.png');

  if (!fs.existsSync(metaPath) || !fs.existsSync(colorPath)) {
    continue;
  }

  const meta = JSON.parse(fs.readFileSync(metaPath, 'utf8'));
  const colorBase64 = fileToBase64Png(colorPath);
  const shadowBase64 = fs.existsSync(shadowPath) ? fileToBase64Png(shadowPath) : null;

  const category = getCategory(pieceName);
  const name = friendlyNames[pieceName] || `${pieceName} (${meta.size_px[0]}×${meta.size_px[1]})`;

  const propData = {
    piece: pieceName,
    name: name,
    category: category,
    w: meta.size_px[0],
    h: meta.size_px[1],
    color: colorBase64,
    shadow: null
  };

  if (shadowBase64 && meta.shadow_canvas_px && meta.shadow_offset_px) {
    propData.shadow = {
      w: meta.shadow_canvas_px[0],
      h: meta.shadow_canvas_px[1],
      dx: meta.shadow_offset_px[0],
      dy: meta.shadow_offset_px[1],
      data: shadowBase64
    };
  }

  props[pieceName] = propData;
}

// 4. Cargar las 4 lápidas definitivas
if (!fs.existsSync(lapidasMetaPath)) {
  console.error('Error: no se encontró lapidas_meta.json en:', lapidasMetaPath);
  process.exit(1);
}
const lapidasMeta = JSON.parse(fs.readFileSync(lapidasMetaPath, 'utf8'));
for (const [key, meta] of Object.entries(lapidasMeta)) {
  const lapidaPngPath = path.join(lapidasDir, `${key}.png`);
  if (!fs.existsSync(lapidaPngPath)) {
    console.error(`Error: falta imagen de lápida en ${lapidaPngPath}`);
    continue;
  }
  props[key] = {
    piece: key,
    name: `Lápida: ${meta.label} (${meta.size_px[0]}×${meta.size_px[1]})`,
    category: 'lapidas',
    w: meta.size_px[0],
    h: meta.size_px[1],
    floor_origin_px: meta.floor_origin_px || [0, 62],
    color: fileToBase64Png(lapidaPngPath),
    shadow: null
  };
}
console.log(`Cargadas 4 lápidas definitivas.`);

// 5. Cargar las 2 luces (godrays)
const lightDefs = [
  { key: 'haz_vidriera', label: 'Haz vidriera (256×128)', file: 'ray_lancet_vitral.png' },
  { key: 'haz_roseton', label: 'Haz rosetón (256×128)', file: 'ray_rose_vitral.png' }
];

for (const light of lightDefs) {
  const lightPath = path.join(godraysDir, light.file);
  if (!fs.existsSync(lightPath)) {
    console.error(`Error: no se encontró godray en ${lightPath}`);
    process.exit(1);
  }
  props[light.key] = {
    piece: light.key,
    name: light.label,
    category: 'luz',
    w: 256,
    h: 128,
    color: fileToBase64Png(lightPath),
    shadow: null
  };
}
console.log('Cargados 2 haces de luz.');

// 6. Añadir pieza especial marine
props['marine'] = {
  piece: 'marine',
  name: friendlyNames['marine'],
  category: 'especial',
  w: 16,
  h: 31,
  color: null,
  shadow: null
};

const totalProps = Object.keys(props).length;
console.log(`Cargadas ${totalProps} piezas en total.`);

const assetsData = {
  floor: floorBase64,
  wall: wallBase64,
  props: props,
  lapidasMeta: lapidasMeta
};

// 7. Inyectar en editor_template.html
if (!fs.existsSync(templatePath)) {
  console.error('Error: no se encontró editor_template.html');
  process.exit(1);
}

const template = fs.readFileSync(templatePath, 'utf8');
const replacement = `const ASSETS = ${JSON.stringify(assetsData)};`;
const outputHtml = template.replace('/*__ASSETS_DATA__*/', replacement);

fs.writeFileSync(outputPath, outputHtml, 'utf8');
const stats = fs.statSync(outputPath);
const kb = Math.round(stats.size / 1024);
console.log(`Generado con éxito: ${outputPath} (${kb} KB, ${stats.size} bytes).`);
