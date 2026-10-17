// Use the exact Three.js/FBXLoader shipped in the offline lab for host tests.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, 'FBX-Web-Renderer-offline.html'), 'utf8');
const script = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));
const boundary = script.indexOf('var tp=8');
if (boundary < 0) throw new Error('Offline Three.js bundle boundary missing');
function imageStub() {
  const handlers = {};
  return { addEventListener(t, fn) { handlers[t] = fn; }, removeEventListener() {},
    set src(value) { if (handlers.load) handlers.load.call(this); }, width: 1, height: 1 };
}
module.exports = vm.runInNewContext(script.slice(0, boundary) + `;({
  Vector2:G, Vector3:K, Vector4:mn, Quaternion:Xt, Euler:On, Matrix3:q, Matrix4:Y,
  Box3:hr, Color:X, Object3D:Gn, Group:Kn, Scene:er, Bone:ji, Skeleton:Fi,
  Mesh:vi, SkinnedMesh:Ai, BufferGeometry:Jr, BufferAttribute:Nr,
  Float32BufferAttribute:Ir, Uint16BufferAttribute:Pr, Uint32BufferAttribute:Fr,
  MeshStandardMaterial:Xa, MeshPhongMaterial:Za, MeshBasicMaterial:oi,
  AnimationMixer:Ts, AnimationClip:wo, VectorKeyframeTrack:Co,
  QuaternionKeyframeTrack:xo, NumberKeyframeTrack:yo, FBXLoader:cf, MathUtils:Yt
})`, { console, URL, Blob, TextDecoder, TextEncoder, Buffer, setTimeout, clearTimeout,
  performance, document: { createElement: () => ({ relList: { supports: () => true } }),
    createElementNS: imageStub }, window: { URL }, self: {}, require });
