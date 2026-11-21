// Three r186 + FBXLoader sacados del bundle del lab (igual que ../offline_three.cjs), con mas simbolos exportados
// y un Blob/URL propios para recuperar sincronamente los PNG/JPEG embebidos del FBX (sin navegador).
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function createEnv() {
  const html = fs.readFileSync(path.join(__dirname, '..', 'FBX-Web-Renderer-offline.html'), 'utf8');
  const script = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));
  const boundary = script.indexOf('var tp=8');
  if (boundary < 0) throw new Error('Offline Three.js bundle boundary missing');
  const blobs = new Map();
  let nextId = 1;
  class FakeBlob {
    constructor(parts, opts) {
      this.data = Buffer.concat((parts || []).map(p => Buffer.from(p.buffer ? new Uint8Array(p.buffer, p.byteOffset, p.byteLength) : p)));
      this.type = (opts && opts.type) || '';
      this.size = this.data.length;
    }
  }
  const FakeURL = {
    createObjectURL(blob) { const u = 'blob:fast/' + (nextId++); blobs.set(u, blob); return u; },
    revokeObjectURL() {},
  };
  function imageStub() {
    const handlers = {};
    return {
      addEventListener(t, fn) { handlers[t] = fn; }, removeEventListener() {},
      set src(value) { this._src = value; if (handlers.load) handlers.load.call(this); },
      get src() { return this._src; },
      width: 1, height: 1,
    };
  }
  const T = vm.runInNewContext(script.slice(0, boundary) + `;({
    Vector2:G, Vector3:K, Vector4:mn, Quaternion:Xt, Euler:On, Matrix3:q, Matrix4:Y,
    Box3:hr, Color:X, Object3D:Gn, Group:Kn, Scene:er, Bone:ji, Skeleton:Fi,
    Mesh:vi, SkinnedMesh:Ai, BufferGeometry:Jr, BufferAttribute:Nr,
    MeshStandardMaterial:Xa, MeshPhongMaterial:Za, AnimationMixer:Ts, AnimationClip:wo,
    FBXLoader:cf, MathUtils:Yt, PropertyBinding:Ss, OrthographicCamera:ts, Texture:pn, SRGB:ot, ArrayBuffer
  })`, {
    console, URL: FakeURL, Blob: FakeBlob, TextDecoder, TextEncoder, Buffer, setTimeout, clearTimeout, performance,
    document: { createElement: () => ({ relList: { supports: () => true } }), createElementNS: imageStub },
    window: { URL: FakeURL }, self: {}, require,
  });
  T.__blobs = blobs;
  // El FBXLoader comprueba `Content instanceof ArrayBuffer`: el buffer debe ser del ArrayBuffer del contexto vm.
  T.toContextBuffer = (buf) => { const ab = new T.ArrayBuffer(buf.length); new Uint8Array(ab).set(buf); return ab; };
  return T;
}
module.exports = { createEnv };
