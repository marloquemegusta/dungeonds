/**
 * FBX Binary Splicer & Serializer (v7400)
 * Allows parsing, AST manipulation, node injection (weapons & baked animations),
 * and binary serialization to standard Kaydara FBX Binary format.
 *
 * Compatible with Node.js (CommonJS) and browser environments.
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.FBXBinarySplicer = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const textEncoder = new TextEncoder();
  const textDecoder = new TextDecoder();

  // Standard 27-byte FBX Binary header for v7400
  // "Kaydara FBX Binary  \0\x1a\0" (23 bytes) + uint32 7400 (0x1CE8, 4 bytes)
  const FBX_HEADER_27 = new Uint8Array([
    0x4B, 0x61, 0x79, 0x64, 0x61, 0x72, 0x61, 0x20, // "Kaydara "
    0x46, 0x42, 0x58, 0x20, 0x42, 0x69, 0x6E, 0x61, // "FBX Bina"
    0x72, 0x79, 0x20, 0x20, 0x00, 0x1A, 0x00,       // "ry  \0\x1a\0"
    0xE8, 0x1C, 0x00, 0x00                         // 7400 LE
  ]);

  // Standard 160-byte FBX footer
  const FBX_FOOTER_160 = new Uint8Array(160);
  FBX_FOOTER_160.set([
    0xfa, 0xbc, 0xab, 0x09, 0xd0, 0xc2, 0x6a, 0x64,
    0xb4, 0x73, 0xfc, 0x84, 0x1a, 0x8d, 0x2d, 0x7a
  ], 0);
  // Version at offset 20: 7400
  FBX_FOOTER_160[20] = 0xE8;
  FBX_FOOTER_160[21] = 0x1C;
  FBX_FOOTER_160[22] = 0x00;
  FBX_FOOTER_160[23] = 0x00;
  // Standard FBX footer key at offset 144
  FBX_FOOTER_160.set([
    0xf8, 0x5a, 0x8c, 0x6a, 0xde, 0xf5, 0xd9, 0x7e,
    0xec, 0xe9, 0x0c, 0xe3, 0x75, 0x8f, 0x29, 0x0b
  ], 144);

  // Set of FBX container node names that must write a 13-byte null sentinel
  const CONTAINER_NODES = new Set([
    'Objects', 'Connections', 'Definitions', 'Takes', 'GlobalSettings',
    'Documents', 'References', 'FBXHeaderExtension', 'Model', 'Geometry',
    'Material', 'Texture', 'Video', 'Deformer', 'Pose', 'AnimationStack',
    'AnimationLayer', 'AnimationCurveNode', 'AnimationCurve', 'Properties70',
    'LayerElementNormal', 'LayerElementUV', 'LayerElementMaterial',
    'LayerElementColor', 'Layer'
  ]);

  // KTime conversion constant (46,186,158,000 ticks per second)
  const KTIME_PER_SECOND = 46186158000n;

  // ---------------------------------------------------------------------------
  // Property Creation Helpers
  // ---------------------------------------------------------------------------

  function createPropC(val) {
    const raw = new Uint8Array([val ? 1 : 0]);
    return { type: 'C', value: Boolean(val), rawBytes: raw };
  }

  function createPropY(val) {
    const raw = new Uint8Array(2);
    new DataView(raw.buffer).setInt16(0, Number(val), true);
    return { type: 'Y', value: Number(val), rawBytes: raw };
  }

  function createPropI(val) {
    const raw = new Uint8Array(4);
    new DataView(raw.buffer).setInt32(0, Number(val), true);
    return { type: 'I', value: Number(val), rawBytes: raw };
  }

  function createPropF(val) {
    const raw = new Uint8Array(4);
    new DataView(raw.buffer).setFloat32(0, Number(val), true);
    return { type: 'F', value: Number(val), rawBytes: raw };
  }

  function createPropD(val) {
    const raw = new Uint8Array(8);
    new DataView(raw.buffer).setFloat64(0, Number(val), true);
    return { type: 'D', value: Number(val), rawBytes: raw };
  }

  function createPropL(val) {
    const raw = new Uint8Array(8);
    const bi = BigInt(val);
    new DataView(raw.buffer).setBigInt64(0, bi, true);
    return { type: 'L', value: bi, rawBytes: raw };
  }

  function createPropS(str) {
    const strBytes = textEncoder.encode(String(str));
    const raw = new Uint8Array(4 + strBytes.length);
    new DataView(raw.buffer).setUint32(0, strBytes.length, true);
    raw.set(strBytes, 4);
    return { type: 'S', value: String(str), rawBytes: raw };
  }

  function createPropR(data) {
    const bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
    const raw = new Uint8Array(4 + bytes.length);
    new DataView(raw.buffer).setUint32(0, bytes.length, true);
    raw.set(bytes, 4);
    return { type: 'R', value: bytes, rawBytes: raw };
  }

  function createPropArrayI(arr) {
    const intArr = arr instanceof Int32Array ? arr : new Int32Array(arr);
    const byteLen = intArr.byteLength;
    const raw = new Uint8Array(12 + byteLen);
    const dv = new DataView(raw.buffer);
    dv.setUint32(0, intArr.length, true); // arrayLength
    dv.setUint32(4, 0, true);              // encoding = 0 (uncompressed)
    dv.setUint32(8, byteLen, true);        // compressedLength
    raw.set(new Uint8Array(intArr.buffer, intArr.byteOffset, byteLen), 12);
    return { type: 'i', value: intArr, rawBytes: raw };
  }

  function createPropArrayF(arr) {
    const fArr = arr instanceof Float32Array ? arr : new Float32Array(arr);
    const byteLen = fArr.byteLength;
    const raw = new Uint8Array(12 + byteLen);
    const dv = new DataView(raw.buffer);
    dv.setUint32(0, fArr.length, true);
    dv.setUint32(4, 0, true);
    dv.setUint32(8, byteLen, true);
    raw.set(new Uint8Array(fArr.buffer, fArr.byteOffset, byteLen), 12);
    return { type: 'f', value: fArr, rawBytes: raw };
  }

  function createPropArrayD(arr) {
    const dArr = arr instanceof Float64Array ? arr : new Float64Array(arr);
    const byteLen = dArr.byteLength;
    const raw = new Uint8Array(12 + byteLen);
    const dv = new DataView(raw.buffer);
    dv.setUint32(0, dArr.length, true);
    dv.setUint32(4, 0, true);
    dv.setUint32(8, byteLen, true);
    raw.set(new Uint8Array(dArr.buffer, dArr.byteOffset, byteLen), 12);
    return { type: 'd', value: dArr, rawBytes: raw };
  }

  function createPropArrayL(arr) {
    const lArr = arr instanceof BigInt64Array ? arr : new BigInt64Array(arr.map(x => BigInt(x)));
    const byteLen = lArr.byteLength;
    const raw = new Uint8Array(12 + byteLen);
    const dv = new DataView(raw.buffer);
    dv.setUint32(0, lArr.length, true);
    dv.setUint32(4, 0, true);
    dv.setUint32(8, byteLen, true);
    raw.set(new Uint8Array(lArr.buffer, lArr.byteOffset, byteLen), 12);
    return { type: 'l', value: lArr, rawBytes: raw };
  }

  function createPropArrayB(arr) {
    const bArr = arr instanceof Uint8Array ? arr : new Uint8Array(arr.map(x => x ? 1 : 0));
    const byteLen = bArr.length;
    const raw = new Uint8Array(12 + byteLen);
    const dv = new DataView(raw.buffer);
    dv.setUint32(0, bArr.length, true);
    dv.setUint32(4, 0, true);
    dv.setUint32(8, byteLen, true);
    raw.set(bArr, 12);
    return { type: 'b', value: bArr, rawBytes: raw };
  }

  function createNode(name, props = [], children = []) {
    return { name, props, children };
  }

  // Ensure any property that was created manually has a valid rawBytes payload
  function ensurePropRawBytes(prop) {
    if (prop.rawBytes && prop.rawBytes.length >= 0) return prop;
    const type = prop.type;
    const val = prop.value;
    switch (type) {
      case 'C': return createPropC(val);
      case 'Y': return createPropY(val);
      case 'I': return createPropI(val);
      case 'F': return createPropF(val);
      case 'D': return createPropD(val);
      case 'L': return createPropL(val);
      case 'S': return createPropS(val);
      case 'R': return createPropR(val);
      case 'i': return createPropArrayI(val);
      case 'f': return createPropArrayF(val);
      case 'd': return createPropArrayD(val);
      case 'l': return createPropArrayL(val);
      case 'b': case 'c': return createPropArrayB(val);
      default:
        throw new Error('Unsupported property type: ' + type);
    }
  }

  // Format FBX attribute name string:
  // Converts "AnimCurveNode::T" -> "T\x00\x01AnimCurveNode"
  // Converts "Model::RightHand" -> "RightHand\x00\x01Model"
  function formatBinaryAttrName(attrName, defaultType) {
    if (!attrName) return '';
    if (attrName.includes('\x00\x01')) return attrName;
    const parts = attrName.split('::');
    if (parts.length > 1) {
      const prefix = parts[0];
      const name = parts.slice(1).join('::');
      return name + '\x00\x01' + prefix;
    }
    if (defaultType) {
      return attrName + '\x00\x01' + defaultType;
    }
    return attrName;
  }

  // ---------------------------------------------------------------------------
  // 1. parseFBXBinary(arrayBuffer)
  // ---------------------------------------------------------------------------

  function parseFBXBinary(arrayBuffer) {
    let buffer = arrayBuffer;
    let byteOffset = 0;
    let byteLength = arrayBuffer.byteLength;

    if (arrayBuffer.buffer instanceof ArrayBuffer) {
      buffer = arrayBuffer.buffer;
      byteOffset = arrayBuffer.byteOffset || 0;
      byteLength = arrayBuffer.byteLength;
    }

    if (byteLength < 27) {
      throw new Error('FBX binary buffer too short (<27 bytes).');
    }

    const dv = new DataView(buffer, byteOffset, byteLength);

    // Verify header "Kaydara FBX Binary  \0\x1a\0"
    const headerPrefix = textDecoder.decode(new Uint8Array(buffer, byteOffset, 20));
    if (headerPrefix !== 'Kaydara FBX Binary  ') {
      throw new Error('Invalid FBX Binary magic header.');
    }
    if (dv.getUint8(20) !== 0x00 || dv.getUint8(21) !== 0x1A || dv.getUint8(22) !== 0x00) {
      throw new Error('Invalid FBX Binary signature bytes.');
    }

    const version = dv.getUint32(23, true);
    const is64 = version >= 7500;

    let offset = 27;

    function parseNode() {
      const endOffset = is64
        ? Number(dv.getBigUint64(offset, true))
        : dv.getUint32(offset, true);
      const numProps = is64
        ? Number(dv.getBigUint64(offset + 8, true))
        : dv.getUint32(offset + 4, true);
      const propListLen = is64
        ? Number(dv.getBigUint64(offset + 16, true))
        : dv.getUint32(offset + 8, true);
      const headerBase = is64 ? 25 : 13;
      const nameLen = dv.getUint8(offset + (is64 ? 24 : 12));

      // Null sentinel check
      if (endOffset === 0 && numProps === 0 && propListLen === 0 && nameLen === 0) {
        offset += headerBase;
        return null;
      }

      const name = textDecoder.decode(new Uint8Array(buffer, byteOffset + offset + headerBase, nameLen));
      offset += headerBase + nameLen;

      const props = [];
      for (let i = 0; i < numProps; i++) {
        const type = String.fromCharCode(dv.getUint8(offset++));
        let payloadLen = 0;
        let value = null;

        switch (type) {
          case 'C':
            value = Boolean(dv.getUint8(offset));
            payloadLen = 1;
            break;
          case 'Y':
            value = dv.getInt16(offset, true);
            payloadLen = 2;
            break;
          case 'I':
            value = dv.getInt32(offset, true);
            payloadLen = 4;
            break;
          case 'F':
            value = dv.getFloat32(offset, true);
            payloadLen = 4;
            break;
          case 'D':
            value = dv.getFloat64(offset, true);
            payloadLen = 8;
            break;
          case 'L':
            value = dv.getBigInt64(offset, true);
            payloadLen = 8;
            break;
          case 'S': {
            const len = dv.getUint32(offset, true);
            value = textDecoder.decode(new Uint8Array(buffer, byteOffset + offset + 4, len));
            payloadLen = 4 + len;
            break;
          }
          case 'R': {
            const len = dv.getUint32(offset, true);
            value = new Uint8Array(buffer, byteOffset + offset + 4, len);
            payloadLen = 4 + len;
            break;
          }
          case 'b': case 'c': case 'i': case 'f': case 'd': case 'l': {
            const compLen = dv.getUint32(offset + 8, true);
            payloadLen = 12 + compLen;
            break;
          }
          default:
            throw new Error('Unknown FBX property type: ' + type);
        }

        const rawBytes = new Uint8Array(buffer, byteOffset + offset, payloadLen);
        offset += payloadLen;
        props.push({ type, rawBytes, value });
      }

      const children = [];
      while (offset < endOffset) {
        const child = parseNode();
        if (child === null) break;
        children.push(child);
      }

      return { name, props, children };
    }

    const rootNodes = [];
    while (offset < byteLength - 160) {
      const node = parseNode();
      if (node === null) break;
      rootNodes.push(node);
    }

    // Build Model and Bone indices
    const modelsById = new Map();
    const bonesByName = new Map();

    const objectsNode = rootNodes.find(n => n.name === 'Objects');
    if (objectsNode && objectsNode.children) {
      for (const modelNode of objectsNode.children) {
        if (modelNode.name !== 'Model') continue;
        const id = modelNode.props[0] ? BigInt(modelNode.props[0].value) : 0n;
        const rawName = modelNode.props[1] ? String(modelNode.props[1].value) : '';
        const type = modelNode.props[2] ? String(modelNode.props[2].value) : '';
        const cleanName = rawName.split('\x00\x01')[0].replace(/^Model::/, '');

        let preRotation = [0, 0, 0];
        let postRotation = [0, 0, 0];
        let rotationOrder = 0;
        let lclTranslation = [0, 0, 0];
        let lclRotation = [0, 0, 0];
        let lclScaling = [1, 1, 1];

        const p70 = modelNode.children.find(c => c.name === 'Properties70');
        if (p70 && p70.children) {
          for (const p of p70.children) {
            if (p.name !== 'P' || p.props.length < 5) continue;
            const propName = String(p.props[0].value);
            if (propName === 'PreRotation' && p.props.length >= 7) {
              preRotation = [Number(p.props[4].value), Number(p.props[5].value), Number(p.props[6].value)];
            } else if (propName === 'PostRotation' && p.props.length >= 7) {
              postRotation = [Number(p.props[4].value), Number(p.props[5].value), Number(p.props[6].value)];
            } else if (propName === 'RotationOrder') {
              rotationOrder = Number(p.props[4].value);
            } else if (propName === 'Lcl Translation' && p.props.length >= 7) {
              lclTranslation = [Number(p.props[4].value), Number(p.props[5].value), Number(p.props[6].value)];
            } else if (propName === 'Lcl Rotation' && p.props.length >= 7) {
              lclRotation = [Number(p.props[4].value), Number(p.props[5].value), Number(p.props[6].value)];
            } else if (propName === 'Lcl Scaling' && p.props.length >= 7) {
              lclScaling = [Number(p.props[4].value), Number(p.props[5].value), Number(p.props[6].value)];
            }
          }
        }

        const modelInfo = {
          id,
          name: cleanName,
          cleanName,
          rawName,
          type,
          parentId: null,
          childrenIds: [],
          preRotation,
          postRotation,
          rotationOrder,
          lclTranslation,
          lclRotation,
          lclScaling,
          node: modelNode
        };

        modelsById.set(id.toString(), modelInfo);
        modelsById.set(id, modelInfo);

        bonesByName.set(cleanName, modelInfo);
        bonesByName.set(rawName, modelInfo);
      }
    }

    // Resolve parent-child relationships from Connections
    const connectionsNode = rootNodes.find(n => n.name === 'Connections');
    if (connectionsNode && connectionsNode.children) {
      for (const c of connectionsNode.children) {
        if (c.name !== 'C' || c.props.length < 3) continue;
        if (c.props[0].value !== 'OO') continue;
        const childId = BigInt(c.props[1].value);
        const parentId = BigInt(c.props[2].value);

        const childModel = modelsById.get(childId.toString());
        if (childModel) {
          childModel.parentId = parentId;
          const parentModel = modelsById.get(parentId.toString());
          if (parentModel) {
            parentModel.childrenIds.push(childId);
          }
        }
      }
    }

    return {
      version,
      nodes: rootNodes,
      modelsById,
      bonesByName
    };
  }

  // ---------------------------------------------------------------------------
  // 2. writeFBXBinary7400(astNodes)
  // ---------------------------------------------------------------------------

  function computeNodeLayout(node) {
    const nameBytes = textEncoder.encode(node.name || '');

    // Ensure all properties have rawBytes
    let propertyListLen = 0;
    const props = (node.props || []).map(p => {
      const fixed = ensurePropRawBytes(p);
      propertyListLen += 1 + fixed.rawBytes.length;
      return fixed;
    });

    const isContainer = (node.children && node.children.length > 0) || CONTAINER_NODES.has(node.name);
    let childrenSize = 0;
    const childLayouts = [];

    if (isContainer) {
      if (node.children) {
        for (const child of node.children) {
          const cl = computeNodeLayout(child);
          childLayouts.push(cl);
          childrenSize += cl.totalSize;
        }
      }
      childrenSize += 13; // 13-byte null sentinel for children block
    }

    const headerSize = 13 + nameBytes.length;
    const totalSize = headerSize + propertyListLen + childrenSize;

    return {
      node,
      nameBytes,
      props,
      propertyListLen,
      isContainer,
      childLayouts,
      totalSize
    };
  }

  function writeFBXBinary7400(astInput) {
    const rootNodes = Array.isArray(astInput) ? astInput : (astInput && astInput.nodes ? astInput.nodes : []);

    const rootLayouts = rootNodes.map(computeNodeLayout);
    let rootsTotalSize = 0;
    for (const rl of rootLayouts) {
      rootsTotalSize += rl.totalSize;
    }

    const totalFileSize = 27 + rootsTotalSize + 13 + 160;
    const outputBuffer = new ArrayBuffer(totalFileSize);
    const uint8View = new Uint8Array(outputBuffer);
    const dv = new DataView(outputBuffer);

    // 1. Write Header (27 bytes)
    uint8View.set(FBX_HEADER_27, 0);

    // 2. Recursive Node Writer
    function writeNode(layout, startOffset) {
      const endOffset = startOffset + layout.totalSize;
      dv.setUint32(startOffset, endOffset, true);
      dv.setUint32(startOffset + 4, layout.props.length, true);
      dv.setUint32(startOffset + 8, layout.propertyListLen, true);
      dv.setUint8(startOffset + 12, layout.nameBytes.length);
      uint8View.set(layout.nameBytes, startOffset + 13);

      let curOffset = startOffset + 13 + layout.nameBytes.length;

      // Write properties
      for (const p of layout.props) {
        uint8View[curOffset++] = p.type.charCodeAt(0);
        uint8View.set(p.rawBytes, curOffset);
        curOffset += p.rawBytes.length;
      }

      // Write children
      if (layout.isContainer) {
        for (const cl of layout.childLayouts) {
          writeNode(cl, curOffset);
          curOffset += cl.totalSize;
        }
        // Write 13-byte null sentinel (already 0 in allocated buffer)
        curOffset += 13;
      }
    }

    // 3. Write Root Nodes
    let curOffset = 27;
    for (const rl of rootLayouts) {
      writeNode(rl, curOffset);
      curOffset += rl.totalSize;
    }

    // 4. Write Root 13-byte Null Sentinel
    curOffset += 13;

    // 5. Write Standard 160-byte Footer
    uint8View.set(FBX_FOOTER_160, curOffset);
    curOffset += 160;

    if (curOffset !== totalFileSize) {
      throw new Error(`Serialization size mismatch: expected ${totalFileSize}, wrote ${curOffset}`);
    }

    return outputBuffer;
  }

  // ---------------------------------------------------------------------------
  // 3. spliceAndExportFBX(charFbxBuffer, options)
  // ---------------------------------------------------------------------------

  function spliceAndExportFBX(charFbxBuffer, options = {}) {
    const ast = parseFBXBinary(charFbxBuffer);
    const rootNodes = ast.nodes;

    const objectsNode = rootNodes.find(n => n.name === 'Objects');
    const connectionsNode = rootNodes.find(n => n.name === 'Connections');
    const definitionsNode = rootNodes.find(n => n.name === 'Definitions');
    const takesNode = rootNodes.find(n => n.name === 'Takes');

    if (!objectsNode || !connectionsNode) {
      throw new Error('FBX missing Objects or Connections root nodes.');
    }

    // 1. Remove old animation nodes from Objects
    const animNodeTypes = new Set(['AnimationStack', 'AnimationLayer', 'AnimationCurveNode', 'AnimationCurve']);
    const removedAnimIds = new Set();

    objectsNode.children = objectsNode.children.filter(child => {
      if (animNodeTypes.has(child.name)) {
        if (child.props && child.props[0] && child.props[0].value != null) {
          removedAnimIds.add(child.props[0].value.toString());
        }
        return false;
      }
      return true;
    });

    // Clean old animation connections
    connectionsNode.children = connectionsNode.children.filter(c => {
      if (c.name !== 'C' || c.props.length < 3) return true;
      const childId = c.props[1].value != null ? c.props[1].value.toString() : '';
      const parentId = c.props[2].value != null ? c.props[2].value.toString() : '';
      return !removedAnimIds.has(childId) && !removedAnimIds.has(parentId);
    });

    // Clean Takes
    if (takesNode && takesNode.children) {
      takesNode.children = takesNode.children.filter(c => c.name !== 'Take');
      const curTake = takesNode.children.find(c => c.name === 'Current');
      const firstClipName = options.clips && options.clips.length > 0 ? options.clips[0].name : '';
      if (curTake) {
        curTake.props = [createPropS(firstClipName)];
      } else {
        takesNode.children.push(createNode('Current', [createPropS(firstClipName)]));
      }
    }

    // ID Allocator: find max existing ID across Objects and Connections
    let maxId = 1000000000n;
    for (const obj of objectsNode.children) {
      if (obj.props && obj.props[0] && (obj.props[0].type === 'L' || obj.props[0].type === 'I')) {
        const id = BigInt(obj.props[0].value);
        if (id > maxId) maxId = id;
      }
    }
    for (const c of connectionsNode.children) {
      if (c.props) {
        for (let i = 1; i <= 2; i++) {
          if (c.props[i] && (c.props[i].type === 'L' || c.props[i].type === 'I')) {
            const id = BigInt(c.props[i].value);
            if (id > maxId) maxId = id;
          }
        }
      }
    }
    function allocId() {
      maxId = maxId + 1n;
      return maxId;
    }

    // 2. Inject Weapon (if requested)
    if (options.weapon && options.parentBoneId != null) {
      const w = options.weapon;
      let parentBoneId = options.parentBoneId;

      // If parentBoneId is a bone name string, resolve to ID
      if (typeof parentBoneId === 'string' && ast.bonesByName.has(parentBoneId)) {
        parentBoneId = ast.bonesByName.get(parentBoneId).id;
      } else {
        parentBoneId = BigInt(parentBoneId);
      }

      const geoId = allocId();
      const weaponModelId = allocId();
      const materialId = allocId();
      const videoId = w.pngBytes ? allocId() : null;
      const textureId = w.pngBytes ? allocId() : null;

      // Prepare vertices
      const posArr = w.positions instanceof Float64Array
        ? w.positions
        : new Float64Array(w.positions || []);

      // Prepare indices & PolygonVertexIndex
      let indices = w.indices;
      if (!indices || indices.length === 0) {
        const count = Math.floor(posArr.length / 3);
        indices = new Int32Array(count);
        for (let i = 0; i < count; i++) indices[i] = i;
      } else if (!(indices instanceof Int32Array)) {
        indices = new Int32Array(indices);
      }

      const polyVertexIndex = new Int32Array(indices.length);
      for (let i = 0; i < indices.length; i += 3) {
        polyVertexIndex[i] = indices[i];
        polyVertexIndex[i + 1] = indices[i + 1];
        polyVertexIndex[i + 2] = ~indices[i + 2]; // bitwise NOT for triangle end
      }

      // Prepare normals (ByPolygonVertex)
      const polyVertexCount = indices.length;
      let normalsByPoly;
      if (w.normals && w.normals.length === polyVertexCount * 3) {
        normalsByPoly = w.normals instanceof Float64Array ? w.normals : new Float64Array(w.normals);
      } else if (w.normals && w.normals.length === posArr.length) {
        normalsByPoly = new Float64Array(polyVertexCount * 3);
        for (let i = 0; i < polyVertexCount; i++) {
          const vi = indices[i];
          normalsByPoly[i * 3] = w.normals[vi * 3];
          normalsByPoly[i * 3 + 1] = w.normals[vi * 3 + 1];
          normalsByPoly[i * 3 + 2] = w.normals[vi * 3 + 2];
        }
      } else {
        normalsByPoly = new Float64Array(polyVertexCount * 3);
        // Default normal pointing up [0, 1, 0]
        for (let i = 0; i < polyVertexCount; i++) {
          normalsByPoly[i * 3 + 1] = 1.0;
        }
      }

      // Prepare UVs (if available)
      let uvsByPoly = null;
      if (w.uvs && w.uvs.length > 0) {
        if (w.uvs.length === polyVertexCount * 2) {
          uvsByPoly = w.uvs instanceof Float64Array ? w.uvs : new Float64Array(w.uvs);
        } else if (w.uvs.length === Math.floor(posArr.length / 3) * 2) {
          uvsByPoly = new Float64Array(polyVertexCount * 2);
          for (let i = 0; i < polyVertexCount; i++) {
            const vi = indices[i];
            uvsByPoly[i * 2] = w.uvs[vi * 2];
            uvsByPoly[i * 2 + 1] = w.uvs[vi * 2 + 1];
          }
        }
      }

      // Create Geometry Node
      const geoChildren = [
        createNode('Vertices', [createPropArrayD(posArr)]),
        createNode('PolygonVertexIndex', [createPropArrayI(polyVertexIndex)]),
        createNode('LayerElementNormal', [createPropI(0)], [
          createNode('Version', [createPropI(101)]),
          createNode('Name', [createPropS('')]),
          createNode('MappingInformationType', [createPropS('ByPolygonVertex')]),
          createNode('ReferenceInformationType', [createPropS('Direct')]),
          createNode('Normals', [createPropArrayD(normalsByPoly)])
        ])
      ];

      if (uvsByPoly) {
        geoChildren.push(
          createNode('LayerElementUV', [createPropI(0)], [
            createNode('Version', [createPropI(101)]),
            createNode('Name', [createPropS('UVMap')]),
            createNode('MappingInformationType', [createPropS('ByPolygonVertex')]),
            createNode('ReferenceInformationType', [createPropS('Direct')]),
            createNode('UV', [createPropArrayD(uvsByPoly)])
          ])
        );
      }

      geoChildren.push(
        createNode('LayerElementMaterial', [createPropI(0)], [
          createNode('Version', [createPropI(101)]),
          createNode('Name', [createPropS('')]),
          createNode('MappingInformationType', [createPropS('AllSame')]),
          createNode('ReferenceInformationType', [createPropS('IndexToDirect')]),
          createNode('Materials', [createPropArrayI(new Int32Array([0]))])
        ]),
        createNode('Layer', [createPropI(0)], [
          createNode('Version', [createPropI(100)]),
          createNode('LayerElement', [], [
            createNode('Type', [createPropS('LayerElementNormal')]),
            createNode('TypedIndex', [createPropI(0)])
          ]),
          ...(uvsByPoly ? [
            createNode('LayerElement', [], [
              createNode('Type', [createPropS('LayerElementUV')]),
              createNode('TypedIndex', [createPropI(0)])
            ])
          ] : []),
          createNode('LayerElement', [], [
            createNode('Type', [createPropS('LayerElementMaterial')]),
            createNode('TypedIndex', [createPropI(0)])
          ])
        ])
      );

      const geoNode = createNode('Geometry', [
        createPropL(geoId),
        createPropS(formatBinaryAttrName('Geometry::WeaponGeo', 'Geometry')),
        createPropS('Mesh')
      ], geoChildren);
      objectsNode.children.push(geoNode);

      // Create Model Node for Weapon
      const weaponModelNode = createNode('Model', [
        createPropL(weaponModelId),
        createPropS(formatBinaryAttrName('Model::' + (w.name || 'Weapon'), 'Model')),
        createPropS('Mesh')
      ], [
        createNode('Version', [createPropI(232)]),
        createNode('Properties70', [], [
          createNode('P', [createPropS('Lcl Translation'), createPropS('Lcl Translation'), createPropS(''), createPropS('A'), createPropD(0), createPropD(0), createPropD(0)]),
          createNode('P', [createPropS('Lcl Rotation'), createPropS('Lcl Rotation'), createPropS(''), createPropS('A'), createPropD(0), createPropD(0), createPropD(0)]),
          createNode('P', [createPropS('Lcl Scaling'), createPropS('Lcl Scaling'), createPropS(''), createPropS('A'), createPropD(1), createPropD(1), createPropD(1)])
        ]),
        createNode('Shading', [createPropC(true)]),
        createNode('Culling', [createPropS('CullingOff')])
      ]);
      objectsNode.children.push(weaponModelNode);

      // Create Material Node
      const col = w.color || [0.8, 0.8, 0.8];
      const matNode = createNode('Material', [
        createPropL(materialId),
        createPropS(formatBinaryAttrName('Material::WeaponMat', 'Material')),
        createPropS('')
      ], [
        createNode('Version', [createPropI(102)]),
        createNode('ShadingModel', [createPropS('phong')]),
        createNode('MultiLayer', [createPropI(0)]),
        createNode('Properties70', [], [
          createNode('P', [createPropS('DiffuseColor'), createPropS('ColorRGB'), createPropS('Color'), createPropS(''), createPropD(col[0]), createPropD(col[1]), createPropD(col[2])]),
          createNode('P', [createPropS('Diffuse'), createPropS('Number'), createPropS(''), createPropS('A'), createPropD(1.0)])
        ])
      ]);
      objectsNode.children.push(matNode);

      // Create Video and Texture if pngBytes provided
      if (w.pngBytes) {
        const videoNode = createNode('Video', [
          createPropL(videoId),
          createPropS(formatBinaryAttrName('Video::WeaponTex', 'Video')),
          createPropS('Clip')
        ], [
          createNode('Type', [createPropS('Clip')]),
          createNode('FileName', [createPropS('weapon.png')]),
          createNode('RelativeFilename', [createPropS('weapon.png')]),
          createNode('Content', [createPropR(w.pngBytes)])
        ]);
        objectsNode.children.push(videoNode);

        const texNode = createNode('Texture', [
          createPropL(textureId),
          createPropS(formatBinaryAttrName('Texture::WeaponTex', 'Texture')),
          createPropS('')
        ], [
          createNode('Type', [createPropS('TextureVideoClip')]),
          createNode('Version', [createPropI(202)]),
          createNode('TextureName', [createPropS('Texture::WeaponTex')]),
          createNode('FileName', [createPropS('weapon.png')]),
          createNode('RelativeFilename', [createPropS('weapon.png')]),
          createNode('ModelUVTranslation', [createPropD(0), createPropD(0)]),
          createNode('ModelUVScaling', [createPropD(1), createPropD(1)]),
          createNode('Texture_Alpha_Source', [createPropS('None')])
        ]);
        objectsNode.children.push(texNode);

        connectionsNode.children.push(
          createNode('C', [createPropS('OO'), createPropL(videoId), createPropL(textureId)]),
          createNode('C', [createPropS('OP'), createPropL(textureId), createPropL(materialId), createPropS('DiffuseColor')])
        );
      }

      // Connect Weapon Mesh, Material and Parent Bone
      connectionsNode.children.push(
        createNode('C', [createPropS('OO'), createPropL(geoId), createPropL(weaponModelId)]),
        createNode('C', [createPropS('OO'), createPropL(materialId), createPropL(weaponModelId)]),
        createNode('C', [createPropS('OO'), createPropL(weaponModelId), createPropL(parentBoneId)])
      );
    }

    // 3. Inject Baked Animation Clips
    if (options.clips && options.clips.length > 0) {
      for (const clip of options.clips) {
        const stackId = allocId();
        const layerId = allocId();
        const durationSec = typeof clip.duration === 'number' ? clip.duration : 1.0;
        const stopKTime = BigInt(Math.round(durationSec * Number(KTIME_PER_SECOND)));

        // Create AnimationStack
        const stackNode = createNode('AnimationStack', [
          createPropL(stackId),
          createPropS(formatBinaryAttrName('AnimStack::' + clip.name, 'AnimStack')),
          createPropS('')
        ], [
          createNode('Properties70', [], [
            createNode('P', [createPropS('LocalStart'), createPropS('KTime'), createPropS('Time'), createPropS(''), createPropL(0n)]),
            createNode('P', [createPropS('LocalStop'), createPropS('KTime'), createPropS('Time'), createPropS(''), createPropL(stopKTime)]),
            createNode('P', [createPropS('ReferenceStart'), createPropS('KTime'), createPropS('Time'), createPropS(''), createPropL(0n)]),
            createNode('P', [createPropS('ReferenceStop'), createPropS('KTime'), createPropS('Time'), createPropS(''), createPropL(stopKTime)])
          ])
        ]);
        objectsNode.children.push(stackNode);

        // Create AnimationLayer
        const layerNode = createNode('AnimationLayer', [
          createPropL(layerId),
          createPropS(formatBinaryAttrName('AnimLayer::BaseLayer', 'AnimLayer')),
          createPropS('')
        ]);
        objectsNode.children.push(layerNode);

        // Connect Layer to Stack
        connectionsNode.children.push(
          createNode('C', [createPropS('OO'), createPropL(layerId), createPropL(stackId)])
        );

        // Calculate KTimes for keyframes
        const times = clip.times || [0];
        const kTimes = new BigInt64Array(times.length);
        for (let t = 0; t < times.length; t++) {
          kTimes[t] = BigInt(Math.round(times[t] * Number(KTIME_PER_SECOND)));
        }

        // Process tracks
        if (clip.tracks && clip.tracks.length > 0) {
          for (const track of clip.tracks) {
            let trackModelId = track.modelId;
            if (typeof trackModelId === 'string' && ast.bonesByName.has(trackModelId)) {
              trackModelId = ast.bonesByName.get(trackModelId).id;
            } else {
              trackModelId = BigInt(trackModelId);
            }

            // Translation track (T)
            if (track.T && track.T.length > 0) {
              const curveNodeTId = allocId();
              const curveXId = allocId();
              const curveYId = allocId();
              const curveZId = allocId();

              const curveNodeT = createNode('AnimationCurveNode', [
                createPropL(curveNodeTId),
                createPropS(formatBinaryAttrName('AnimCurveNode::T', 'AnimCurveNode')),
                createPropS('')
              ], [
                createNode('Properties70', [], [
                  createNode('P', [createPropS('d|X'), createPropS('Number'), createPropS(''), createPropS('A'), createPropD(0)]),
                  createNode('P', [createPropS('d|Y'), createPropS('Number'), createPropS(''), createPropS('A'), createPropD(0)]),
                  createNode('P', [createPropS('d|Z'), createPropS('Number'), createPropS(''), createPropS('A'), createPropD(0)])
                ])
              ]);
              objectsNode.children.push(curveNodeT);

              connectionsNode.children.push(
                createNode('C', [createPropS('OO'), createPropL(curveNodeTId), createPropL(layerId)]),
                createNode('C', [createPropS('OP'), createPropL(curveNodeTId), createPropL(trackModelId), createPropS('Lcl Translation')])
              );

              const xVals = new Float32Array(track.T.length);
              const yVals = new Float32Array(track.T.length);
              const zVals = new Float32Array(track.T.length);
              for (let k = 0; k < track.T.length; k++) {
                xVals[k] = track.T[k][0];
                yVals[k] = track.T[k][1];
                zVals[k] = track.T[k][2];
              }

              const curveX = createNode('AnimationCurve', [createPropL(curveXId), createPropS(formatBinaryAttrName('AnimCurve::', 'AnimCurve')), createPropS('')], [
                createNode('KeyTime', [createPropArrayL(kTimes)]),
                createNode('KeyValueFloat', [createPropArrayF(xVals)])
              ]);
              const curveY = createNode('AnimationCurve', [createPropL(curveYId), createPropS(formatBinaryAttrName('AnimCurve::', 'AnimCurve')), createPropS('')], [
                createNode('KeyTime', [createPropArrayL(kTimes)]),
                createNode('KeyValueFloat', [createPropArrayF(yVals)])
              ]);
              const curveZ = createNode('AnimationCurve', [createPropL(curveZId), createPropS(formatBinaryAttrName('AnimCurve::', 'AnimCurve')), createPropS('')], [
                createNode('KeyTime', [createPropArrayL(kTimes)]),
                createNode('KeyValueFloat', [createPropArrayF(zVals)])
              ]);
              objectsNode.children.push(curveX, curveY, curveZ);

              connectionsNode.children.push(
                createNode('C', [createPropS('OP'), createPropL(curveXId), createPropL(curveNodeTId), createPropS('d|X')]),
                createNode('C', [createPropS('OP'), createPropL(curveYId), createPropL(curveNodeTId), createPropS('d|Y')]),
                createNode('C', [createPropS('OP'), createPropL(curveZId), createPropL(curveNodeTId), createPropS('d|Z')])
              );
            }

            // Rotation track (R)
            if (track.R && track.R.length > 0) {
              const curveNodeRId = allocId();
              const curveRXId = allocId();
              const curveRYId = allocId();
              const curveRZId = allocId();

              const curveNodeR = createNode('AnimationCurveNode', [
                createPropL(curveNodeRId),
                createPropS(formatBinaryAttrName('AnimCurveNode::R', 'AnimCurveNode')),
                createPropS('')
              ], [
                createNode('Properties70', [], [
                  createNode('P', [createPropS('d|X'), createPropS('Number'), createPropS(''), createPropS('A'), createPropD(0)]),
                  createNode('P', [createPropS('d|Y'), createPropS('Number'), createPropS(''), createPropS('A'), createPropD(0)]),
                  createNode('P', [createPropS('d|Z'), createPropS('Number'), createPropS(''), createPropS('A'), createPropD(0)])
                ])
              ]);
              objectsNode.children.push(curveNodeR);

              connectionsNode.children.push(
                createNode('C', [createPropS('OO'), createPropL(curveNodeRId), createPropL(layerId)]),
                createNode('C', [createPropS('OP'), createPropL(curveNodeRId), createPropL(trackModelId), createPropS('Lcl Rotation')])
              );

              const rxVals = new Float32Array(track.R.length);
              const ryVals = new Float32Array(track.R.length);
              const rzVals = new Float32Array(track.R.length);
              for (let k = 0; k < track.R.length; k++) {
                rxVals[k] = track.R[k][0];
                ryVals[k] = track.R[k][1];
                rzVals[k] = track.R[k][2];
              }

              const curveRX = createNode('AnimationCurve', [createPropL(curveRXId), createPropS(formatBinaryAttrName('AnimCurve::', 'AnimCurve')), createPropS('')], [
                createNode('KeyTime', [createPropArrayL(kTimes)]),
                createNode('KeyValueFloat', [createPropArrayF(rxVals)])
              ]);
              const curveRY = createNode('AnimationCurve', [createPropL(curveRYId), createPropS(formatBinaryAttrName('AnimCurve::', 'AnimCurve')), createPropS('')], [
                createNode('KeyTime', [createPropArrayL(kTimes)]),
                createNode('KeyValueFloat', [createPropArrayF(ryVals)])
              ]);
              const curveRZ = createNode('AnimationCurve', [createPropL(curveRZId), createPropS(formatBinaryAttrName('AnimCurve::', 'AnimCurve')), createPropS('')], [
                createNode('KeyTime', [createPropArrayL(kTimes)]),
                createNode('KeyValueFloat', [createPropArrayF(rzVals)])
              ]);
              objectsNode.children.push(curveRX, curveRY, curveRZ);

              connectionsNode.children.push(
                createNode('C', [createPropS('OP'), createPropL(curveRXId), createPropL(curveNodeRId), createPropS('d|X')]),
                createNode('C', [createPropS('OP'), createPropL(curveRYId), createPropL(curveNodeRId), createPropS('d|Y')]),
                createNode('C', [createPropS('OP'), createPropL(curveRZId), createPropL(curveNodeRId), createPropS('d|Z')])
              );
            }
          }
        }
      }
    }

    // 4. Update Definitions
    if (definitionsNode && definitionsNode.children) {
      const typeCounts = new Map();
      for (const obj of objectsNode.children) {
        const type = obj.name;
        typeCounts.set(type, (typeCounts.get(type) || 0) + 1);
      }

      // Ensure key required object types exist in Definitions
      const requiredTypes = [
        'AnimationStack', 'AnimationLayer', 'AnimationCurveNode', 'AnimationCurve',
        'Geometry', 'Model', 'Material', 'Texture', 'Video'
      ];
      for (const rt of requiredTypes) {
        if (!typeCounts.has(rt)) {
          typeCounts.set(rt, 0);
        }
      }

      for (const [type, count] of typeCounts.entries()) {
        if (count === 0 && !requiredTypes.includes(type)) continue;
        let defObjType = definitionsNode.children.find(c =>
          c.name === 'ObjectType' && c.props && c.props[0] && String(c.props[0].value) === type
        );
        if (!defObjType) {
          defObjType = createNode('ObjectType', [createPropS(type)], [
            createNode('Count', [createPropI(count)])
          ]);
          definitionsNode.children.push(defObjType);
        } else {
          let countChild = defObjType.children.find(c => c.name === 'Count');
          if (!countChild) {
            countChild = createNode('Count', [createPropI(count)]);
            defObjType.children.unshift(countChild);
          } else {
            countChild.props = [createPropI(count)];
          }
        }
      }

      // Update total Count child of Definitions
      let totalCountNode = definitionsNode.children.find(c => c.name === 'Count');
      if (!totalCountNode) {
        totalCountNode = createNode('Count', [createPropI(objectsNode.children.length)]);
        definitionsNode.children.unshift(totalCountNode);
      } else {
        totalCountNode.props = [createPropI(objectsNode.children.length)];
      }
    }

    // 5. Serialize to FBX Binary 7400
    return writeFBXBinary7400(rootNodes);
  }

  // ---------------------------------------------------------------------------
  // Module Exports
  // ---------------------------------------------------------------------------

  return {
    parseFBXBinary,
    writeFBXBinary7400,
    spliceAndExportFBX,
    createPropC,
    createPropY,
    createPropI,
    createPropF,
    createPropD,
    createPropL,
    createPropS,
    createPropR,
    createPropArrayI,
    createPropArrayF,
    createPropArrayD,
    createPropArrayL,
    createPropArrayB,
    createNode
  };
}));
