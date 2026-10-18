/**
 * Minimal standalone GLB (GLTF 2.0 Binary) loader.
 * No external dependencies. Supports browser (window.MinimalGLBLoader) and Node (CommonJS).
 */
(function (global) {
  'use strict';

  // Math helpers for 4x4 matrix and normal transforms
  function mat4Identity() {
    return new Float32Array([
      1, 0, 0, 0,
      0, 1, 0, 0,
      0, 0, 1, 0,
      0, 0, 0, 1
    ]);
  }

  function mat4Multiply(out, a, b) {
    const a00 = a[0], a01 = a[4], a02 = a[8], a03 = a[12];
    const a10 = a[1], a11 = a[5], a12 = a[9], a13 = a[13];
    const a20 = a[2], a21 = a[6], a22 = a[10], a23 = a[14];
    const a30 = a[3], a31 = a[7], a32 = a[11], a33 = a[15];

    for (let i = 0; i < 4; i++) {
      const b0 = b[i * 4 + 0], b1 = b[i * 4 + 1], b2 = b[i * 4 + 2], b3 = b[i * 4 + 3];
      out[i * 4 + 0] = a00 * b0 + a01 * b1 + a02 * b2 + a03 * b3;
      out[i * 4 + 1] = a10 * b0 + a11 * b1 + a12 * b2 + a13 * b3;
      out[i * 4 + 2] = a20 * b0 + a21 * b1 + a22 * b2 + a23 * b3;
      out[i * 4 + 3] = a30 * b0 + a31 * b1 + a32 * b2 + a33 * b3;
    }
    return out;
  }

  function mat4FromTRS(translation, rotation, scale) {
    const out = mat4Identity();
    const t = translation || [0, 0, 0];
    const r = rotation || [0, 0, 0, 1]; // [x, y, z, w]
    const s = scale || [1, 1, 1];

    const x = r[0], y = r[1], z = r[2], w = r[3];
    const x2 = x + x, y2 = y + y, z2 = z + z;
    const xx = x * x2, xy = x * y2, xz = x * z2;
    const yy = y * y2, yz = y * z2, zz = z * z2;
    const wx = w * x2, wy = w * y2, wz = w * z2;

    const sx = s[0], sy = s[1], sz = s[2];

    out[0] = (1 - (yy + zz)) * sx;
    out[1] = (xy + wz) * sx;
    out[2] = (xz - wy) * sx;
    out[3] = 0;

    out[4] = (xy - wz) * sy;
    out[5] = (1 - (xx + zz)) * sy;
    out[6] = (yz + wx) * sy;
    out[7] = 0;

    out[8] = (xz + wy) * sz;
    out[9] = (yz - wx) * sz;
    out[10] = (1 - (xx + yy)) * sz;
    out[11] = 0;

    out[12] = t[0];
    out[13] = t[1];
    out[14] = t[2];
    out[15] = 1;

    return out;
  }

  function mat3NormalFromMat4(m) {
    const a00 = m[0], a01 = m[4], a02 = m[8];
    const a10 = m[1], a11 = m[5], a12 = m[9];
    const a20 = m[2], a21 = m[6], a22 = m[10];

    const b01 = a22 * a11 - a12 * a21;
    const b11 = -a22 * a10 + a12 * a20;
    const b21 = a21 * a10 - a11 * a20;

    let det = a00 * b01 + a01 * b11 + a02 * b21;
    if (Math.abs(det) < 1e-12) {
      return [1, 0, 0, 0, 1, 0, 0, 0, 1];
    }
    const inv = 1.0 / det;

    // Transpose of inverse(A):
    return [
      b01 * inv,
      (a02 * a21 - a22 * a01) * inv,
      (a12 * a01 - a02 * a11) * inv,
      b11 * inv,
      (a22 * a00 - a02 * a20) * inv,
      (-a12 * a00 + a02 * a10) * inv,
      b21 * inv,
      (-a21 * a00 + a01 * a20) * inv,
      (a11 * a00 - a01 * a10) * inv
    ];
  }

  function transformPoint(p, m) {
    const x = p[0], y = p[1], z = p[2];
    const w = m[3] * x + m[7] * y + m[11] * z + m[15];
    const invW = Math.abs(w) > 1e-7 ? 1.0 / w : 1.0;
    return [
      (m[0] * x + m[4] * y + m[8] * z + m[12]) * invW,
      (m[1] * x + m[5] * y + m[9] * z + m[13]) * invW,
      (m[2] * x + m[6] * y + m[10] * z + m[14]) * invW
    ];
  }

  function transformNormal(n, normMat) {
    const nx = n[0], ny = n[1], nz = n[2];
    let tx = normMat[0] * nx + normMat[3] * ny + normMat[6] * nz;
    let ty = normMat[1] * nx + normMat[4] * ny + normMat[7] * nz;
    let tz = normMat[2] * nx + normMat[5] * ny + normMat[8] * nz;
    const len = Math.hypot(tx, ty, tz);
    if (len > 1e-8) {
      tx /= len;
      ty /= len;
      tz /= len;
    }
    return [tx, ty, tz];
  }

  /**
   * Parse binary GLB buffer into JSON structure and BIN chunk.
   */
  function parseGLBContainer(arrayBuffer) {
    const view = new DataView(arrayBuffer);
    const magic = view.getUint32(0, true);
    if (magic !== 0x46546c67) {
      throw new Error(`Invalid GLB magic: 0x${magic.toString(16)} (expected 0x46546c67)`);
    }
    const version = view.getUint32(4, true);
    if (version !== 2) {
      throw new Error(`Unsupported GLB version: ${version} (expected 2)`);
    }
    const totalLength = view.getUint32(8, true);

    let offset = 12;
    let jsonChunk = null;
    let binChunk = null;

    while (offset < totalLength && offset < arrayBuffer.byteLength) {
      const chunkLength = view.getUint32(offset, true);
      const chunkType = view.getUint32(offset + 4, true);
      const chunkDataOffset = offset + 8;

      if (chunkType === 0x4e4f534a) {
        // 'JSON'
        const jsonBytes = new Uint8Array(arrayBuffer, chunkDataOffset, chunkLength);
        const jsonStr = new TextDecoder('utf-8').decode(jsonBytes);
        jsonChunk = JSON.parse(jsonStr);
      } else if (chunkType === 0x004e4942) {
        // 'BIN\0'
        binChunk = new Uint8Array(arrayBuffer, chunkDataOffset, chunkLength);
      }

      // 4-byte alignment
      offset = chunkDataOffset + ((chunkLength + 3) & ~3);
    }

    if (!jsonChunk) {
      throw new Error('GLB missing JSON chunk');
    }

    return { gltf: jsonChunk, bin: binChunk };
  }

  /**
   * Helper to decode an accessor into a typed array.
   */
  function getAccessorData(gltf, bin, accessorIndex) {
    const accessor = gltf.accessors[accessorIndex];
    if (!accessor) return null;

    const bufferView = gltf.bufferViews[accessor.bufferView !== undefined ? accessor.bufferView : 0];
    if (!bufferView) return null;

    const bufferIndex = bufferView.buffer || 0;
    if (bufferIndex !== 0 || !bin) {
      throw new Error('External GLTF buffers not supported in minimal GLB loader');
    }

    const byteOffset = (bufferView.byteOffset || 0) + (accessor.byteOffset || 0);
    const count = accessor.count;

    const numComponentsMap = {
      SCALAR: 1,
      VEC2: 2,
      VEC3: 3,
      VEC4: 4,
      MAT2: 4,
      MAT3: 9,
      MAT4: 16
    };
    const numComponents = numComponentsMap[accessor.type] || 1;
    const totalElements = count * numComponents;

    let componentByteSize = 1;
    let TypedArrayClass = Uint8Array;

    switch (accessor.componentType) {
      case 5120: // BYTE
        TypedArrayClass = Int8Array;
        componentByteSize = 1;
        break;
      case 5121: // UNSIGNED_BYTE
        TypedArrayClass = Uint8Array;
        componentByteSize = 1;
        break;
      case 5122: // SHORT
        TypedArrayClass = Int16Array;
        componentByteSize = 2;
        break;
      case 5123: // UNSIGNED_SHORT
        TypedArrayClass = Uint16Array;
        componentByteSize = 2;
        break;
      case 5125: // UNSIGNED_INT
        TypedArrayClass = Uint32Array;
        componentByteSize = 4;
        break;
      case 5126: // FLOAT
        TypedArrayClass = Float32Array;
        componentByteSize = 4;
        break;
      default:
        throw new Error(`Unsupported componentType: ${accessor.componentType}`);
    }

    const defaultStride = numComponents * componentByteSize;
    const stride = bufferView.byteStride !== undefined && bufferView.byteStride !== 0
      ? bufferView.byteStride
      : defaultStride;

    if (stride === defaultStride) {
      // Direct view if byteOffset is properly aligned, else slice
      const binBuffer = bin.buffer;
      const binOffset = bin.byteOffset + byteOffset;
      if (binOffset % componentByteSize === 0) {
        return new TypedArrayClass(binBuffer, binOffset, totalElements);
      } else {
        const copy = new Uint8Array(binBuffer, binOffset, totalElements * componentByteSize);
        return new TypedArrayClass(copy.buffer, copy.byteOffset, totalElements);
      }
    } else {
      // Strided data
      const result = new TypedArrayClass(totalElements);
      const dataView = new DataView(bin.buffer, bin.byteOffset + byteOffset);
      let outIdx = 0;
      for (let i = 0; i < count; i++) {
        const elemOffset = i * stride;
        for (let c = 0; c < numComponents; c++) {
          const compOffset = elemOffset + c * componentByteSize;
          let val = 0;
          switch (accessor.componentType) {
            case 5120: val = dataView.getInt8(compOffset); break;
            case 5121: val = dataView.getUint8(compOffset); break;
            case 5122: val = dataView.getInt16(compOffset, true); break;
            case 5123: val = dataView.getUint16(compOffset, true); break;
            case 5125: val = dataView.getUint32(compOffset, true); break;
            case 5126: val = dataView.getFloat32(compOffset, true); break;
          }
          result[outIdx++] = val;
        }
      }
      return result;
    }
  }

  /**
   * Traverse the GLTF node tree and compute world matrices for each node.
   */
  function computeNodeWorldMatrices(gltf) {
    const nodes = gltf.nodes || [];
    const worldMatrices = new Array(nodes.length);
    const visited = new Uint8Array(nodes.length);

    // Build parent-child relationships
    const parentMap = new Array(nodes.length).fill(-1);
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      if (node.children) {
        for (let c = 0; c < node.children.length; c++) {
          parentMap[node.children[c]] = i;
        }
      }
    }

    function getNodeLocalMatrix(node) {
      if (node.matrix) {
        return new Float32Array(node.matrix);
      }
      return mat4FromTRS(node.translation, node.rotation, node.scale);
    }

    function evaluateNode(nodeIdx) {
      if (visited[nodeIdx]) return worldMatrices[nodeIdx];
      const node = nodes[nodeIdx];
      const localMat = getNodeLocalMatrix(node);
      const parentIdx = parentMap[nodeIdx];
      if (parentIdx >= 0) {
        const parentWorld = evaluateNode(parentIdx);
        const world = mat4Identity();
        mat4Multiply(world, parentWorld, localMat);
        worldMatrices[nodeIdx] = world;
      } else {
        worldMatrices[nodeIdx] = localMat;
      }
      visited[nodeIdx] = 1;
      return worldMatrices[nodeIdx];
    }

    // Evaluate all root nodes in active scene, or all nodes
    let roots = [];
    if (gltf.scene !== undefined && gltf.scenes && gltf.scenes[gltf.scene]) {
      roots = gltf.scenes[gltf.scene].nodes || [];
    } else {
      for (let i = 0; i < nodes.length; i++) {
        if (parentMap[i] === -1) roots.push(i);
      }
    }

    for (let r = 0; r < roots.length; r++) {
      evaluateNode(roots[r]);
    }

    // Catch any detached nodes
    for (let i = 0; i < nodes.length; i++) {
      if (!visited[i]) evaluateNode(i);
    }

    return worldMatrices;
  }

  /**
   * Parse a GLB ArrayBuffer into raw unified mesh data:
   * positions, normals, uvs, indices, color, imageBytes, mimeType
   */
  function parseGLBToMeshData(arrayBuffer) {
    if (arrayBuffer instanceof Uint8Array) {
      arrayBuffer = arrayBuffer.buffer.slice(
        arrayBuffer.byteOffset,
        arrayBuffer.byteOffset + arrayBuffer.byteLength
      );
    }

    const { gltf, bin } = parseGLBContainer(arrayBuffer);
    const worldMatrices = computeNodeWorldMatrices(gltf);

    const allPositions = [];
    const allNormals = [];
    const allUvs = [];
    const allIndices = [];

    let primaryColor = [0.8, 0.8, 0.8];
    let primaryImageBytes = null;
    let primaryMimeType = null;
    const materialInfoByIndex = new Map();
    const groups = [];

    // Helper to extract material info
    function extractMaterialInfo(matIndex) {
      if (matIndex === undefined || !gltf.materials || !gltf.materials[matIndex]) return null;
      if (materialInfoByIndex.has(matIndex)) return materialInfoByIndex.get(matIndex);
      const mat = gltf.materials[matIndex];
      const pbr = mat.pbrMetallicRoughness;
      let color = [0.8, 0.8, 0.8], imageBytes = null, mimeType = null;
      let emissive = (mat.emissiveFactor && Array.isArray(mat.emissiveFactor)) ? mat.emissiveFactor.slice(0, 3) : null;
      if (pbr) {
        if (pbr.baseColorFactor && Array.isArray(pbr.baseColorFactor)) color = pbr.baseColorFactor.slice(0, 3);
        if (pbr.baseColorTexture && gltf.textures && gltf.images) {
          const tex = gltf.textures[pbr.baseColorTexture.index];
          if (tex && tex.source !== undefined) {
            const img = gltf.images[tex.source];
            if (img && img.bufferView !== undefined && gltf.bufferViews) {
              const bv = gltf.bufferViews[img.bufferView];
              const byteOffset = bv.byteOffset || 0;
              const byteLength = bv.byteLength;
              if (bin && byteOffset + byteLength <= bin.byteLength) {
                imageBytes = new Uint8Array(
                  bin.buffer,
                  bin.byteOffset + byteOffset,
                  byteLength
                );
                mimeType = img.mimeType || 'image/png';
              }
            }
          }
        }
      }
      const info = { name: mat.name || ('Material ' + (matIndex + 1)), color, emissive, imageBytes, mimeType };
      materialInfoByIndex.set(matIndex, info);
      return info;
    }

    let globalVertexCount = 0;

    // Iterate through all nodes with meshes
    const nodes = gltf.nodes || [];
    for (let nodeIdx = 0; nodeIdx < nodes.length; nodeIdx++) {
      const node = nodes[nodeIdx];
      if (node.mesh === undefined || !gltf.meshes || !gltf.meshes[node.mesh]) continue;

      const mesh = gltf.meshes[node.mesh];
      const worldMat = worldMatrices[nodeIdx] || mat4Identity();
      const normMat = mat3NormalFromMat4(worldMat);

      for (let primIdx = 0; primIdx < mesh.primitives.length; primIdx++) {
        const prim = mesh.primitives[primIdx];
        if (prim.attributes.POSITION === undefined) continue;

        const sourceMaterialIndex = prim.material === undefined ? -1 : prim.material;
        if (!materialInfoByIndex.has(sourceMaterialIndex)) {
          const info = sourceMaterialIndex < 0
            ? { name: 'Default', color: [0.8, 0.8, 0.8], imageBytes: null, mimeType: null }
            : extractMaterialInfo(sourceMaterialIndex);
          materialInfoByIndex.set(sourceMaterialIndex, info || { name: 'Material', color: [0.8, 0.8, 0.8], imageBytes: null, mimeType: null });
        }
        const outputMaterialIndex = [...materialInfoByIndex.keys()].indexOf(sourceMaterialIndex);

        const posData = getAccessorData(gltf, bin, prim.attributes.POSITION);
        if (!posData) continue;
        const vertCount = posData.length / 3;

        const normData = prim.attributes.NORMAL !== undefined
          ? getAccessorData(gltf, bin, prim.attributes.NORMAL)
          : null;

        const uvData = prim.attributes.TEXCOORD_0 !== undefined
          ? getAccessorData(gltf, bin, prim.attributes.TEXCOORD_0)
          : null;

        let indexData = null;
        if (prim.indices !== undefined) {
          indexData = getAccessorData(gltf, bin, prim.indices);
        }

        // Indices preparation
        const primIndices = [];
        if (indexData) {
          for (let i = 0; i < indexData.length; i++) {
            primIndices.push(indexData[i] + globalVertexCount);
          }
        } else {
          for (let i = 0; i < vertCount; i++) {
            primIndices.push(i + globalVertexCount);
          }
        }

        // Transform vertices to world space
        const primPositions = new Float32Array(vertCount * 3);
        for (let i = 0; i < vertCount; i++) {
          const rawP = [posData[i * 3 + 0], posData[i * 3 + 1], posData[i * 3 + 2]];
          const tp = transformPoint(rawP, worldMat);
          primPositions[i * 3 + 0] = tp[0];
          primPositions[i * 3 + 1] = tp[1];
          primPositions[i * 3 + 2] = tp[2];
        }

        // Normals preparation: transform existing or compute per-vertex
        const primNormals = new Float32Array(vertCount * 3);
        if (normData) {
          for (let i = 0; i < vertCount; i++) {
            const rawN = [normData[i * 3 + 0], normData[i * 3 + 1], normData[i * 3 + 2]];
            const tn = transformNormal(rawN, normMat);
            primNormals[i * 3 + 0] = tn[0];
            primNormals[i * 3 + 1] = tn[1];
            primNormals[i * 3 + 2] = tn[2];
          }
        } else {
          // Compute vertex normals by accumulating face normals
          const localIndices = indexData || Array.from({ length: vertCount }, (_, i) => i);
          const triCount = Math.floor(localIndices.length / 3);
          for (let t = 0; t < triCount; t++) {
            const i0 = localIndices[t * 3 + 0];
            const i1 = localIndices[t * 3 + 1];
            const i2 = localIndices[t * 3 + 2];

            const p0x = primPositions[i0 * 3 + 0], p0y = primPositions[i0 * 3 + 1], p0z = primPositions[i0 * 3 + 2];
            const p1x = primPositions[i1 * 3 + 0], p1y = primPositions[i1 * 3 + 1], p1z = primPositions[i1 * 3 + 2];
            const p2x = primPositions[i2 * 3 + 0], p2y = primPositions[i2 * 3 + 1], p2z = primPositions[i2 * 3 + 2];

            const e1x = p1x - p0x, e1y = p1y - p0y, e1z = p1z - p0z;
            const e2x = p2x - p0x, e2y = p2y - p0y, e2z = p2z - p0z;

            // Cross product e1 x e2
            const fnx = e1y * e2z - e1z * e2y;
            const fny = e1z * e2x - e1x * e2z;
            const fnz = e1x * e2y - e1y * e2x;

            primNormals[i0 * 3 + 0] += fnx;
            primNormals[i0 * 3 + 1] += fny;
            primNormals[i0 * 3 + 2] += fnz;

            primNormals[i1 * 3 + 0] += fnx;
            primNormals[i1 * 3 + 1] += fny;
            primNormals[i1 * 3 + 2] += fnz;

            primNormals[i2 * 3 + 0] += fnx;
            primNormals[i2 * 3 + 1] += fny;
            primNormals[i2 * 3 + 2] += fnz;
          }

          // Normalize accumulated normals
          for (let i = 0; i < vertCount; i++) {
            let nx = primNormals[i * 3 + 0];
            let ny = primNormals[i * 3 + 1];
            let nz = primNormals[i * 3 + 2];
            const len = Math.hypot(nx, ny, nz);
            if (len > 1e-8) {
              primNormals[i * 3 + 0] = nx / len;
              primNormals[i * 3 + 1] = ny / len;
              primNormals[i * 3 + 2] = nz / len;
            } else {
              primNormals[i * 3 + 0] = 0;
              primNormals[i * 3 + 1] = 1;
              primNormals[i * 3 + 2] = 0;
            }
          }
        }

        // UVs preparation
        const primUvs = new Float32Array(vertCount * 2);
        if (uvData) {
          primUvs.set(uvData.subarray(0, vertCount * 2));
        }

        groups.push({ start: allIndices.length, count: primIndices.length, materialIndex: outputMaterialIndex });
        allPositions.push(primPositions);
        allNormals.push(primNormals);
        allUvs.push(primUvs);
        for (let i = 0; i < primIndices.length; i++) {
          allIndices.push(primIndices[i]);
        }

        globalVertexCount += vertCount;
      }
    }

    // Merge all primitive buffers
    const totalVerts = globalVertexCount;
    const finalPositions = new Float32Array(totalVerts * 3);
    const finalNormals = new Float32Array(totalVerts * 3);
    const finalUvs = new Float32Array(totalVerts * 2);

    let posOffset = 0;
    let uvOffset = 0;
    for (let p = 0; p < allPositions.length; p++) {
      finalPositions.set(allPositions[p], posOffset);
      finalNormals.set(allNormals[p], posOffset);
      posOffset += allPositions[p].length;

      finalUvs.set(allUvs[p], uvOffset);
      uvOffset += allUvs[p].length;
    }

    const finalIndices = new Uint32Array(allIndices);

    const materials = [...materialInfoByIndex.values()];
    if (materials.length) {
      primaryColor = materials[0].color;
      primaryImageBytes = materials[0].imageBytes;
      primaryMimeType = materials[0].mimeType;
    }

    return {
      positions: finalPositions,
      normals: finalNormals,
      uvs: finalUvs,
      indices: finalIndices,
      groups,
      materials,
      color: primaryColor,
      imageBytes: primaryImageBytes,
      mimeType: primaryMimeType
    };
  }

  /**
   * Instantiate a ready THREE.Mesh from a GLB ArrayBuffer.
   */
  function buildThreeMeshFromGLB(THREE, arrayBuffer) {
    if (!THREE) {
      throw new Error('THREE instance must be provided to buildThreeMeshFromGLB');
    }

    const meshData = parseGLBToMeshData(arrayBuffer);
    const geometry = new THREE.BufferGeometry();

    geometry.setAttribute('position', new THREE.BufferAttribute(meshData.positions, 3));
    geometry.setAttribute('normal', new THREE.BufferAttribute(meshData.normals, 3));
    geometry.setAttribute('uv', new THREE.BufferAttribute(meshData.uvs, 2));
    geometry.setIndex(new THREE.BufferAttribute(meshData.indices, 1));

    if (meshData.groups && meshData.groups.length > 0 && meshData.materials && meshData.materials.length > 0) {
      geometry.clearGroups();
      for (let i = 0; i < meshData.groups.length; i++) {
        const g = meshData.groups[i];
        geometry.addGroup(g.start, g.count, g.materialIndex);
      }

      const materialsArray = meshData.materials.map(matInfo => {
        if (matInfo.imageBytes && typeof URL !== 'undefined' && typeof Blob !== 'undefined') {
          try {
            const blob = new Blob([matInfo.imageBytes], { type: matInfo.mimeType || 'image/png' });
            const objectUrl = URL.createObjectURL(blob);
            const texture = new THREE.TextureLoader().load(objectUrl);
            if (THREE.SRGBColorSpace) {
              texture.colorSpace = THREE.SRGBColorSpace;
            } else if (THREE.sRGBEncoding) {
              texture.encoding = THREE.sRGBEncoding;
            }
            const mat = new THREE.MeshStandardMaterial({
              map: texture,
              color: new THREE.Color(1, 1, 1),
              roughness: 0.85,
              metalness: 0.05
            });
            if (matInfo.emissive) {
              mat.emissive = new THREE.Color(matInfo.emissive[0], matInfo.emissive[1], matInfo.emissive[2]);
            }
            return mat;
          } catch (err) {
            // Fallback to color
          }
        }
        const c = matInfo.color || [0.8, 0.8, 0.8];
        const mat = new THREE.MeshStandardMaterial({
          color: new THREE.Color(c[0], c[1], c[2]),
          roughness: 0.85,
          metalness: 0.05
        });
        if (matInfo.emissive) {
          mat.emissive = new THREE.Color(matInfo.emissive[0], matInfo.emissive[1], matInfo.emissive[2]);
        }
        return mat;
      });

      const mesh = new THREE.Mesh(geometry, materialsArray);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      return mesh;
    }

    let material;
    if (meshData.imageBytes && typeof URL !== 'undefined' && typeof Blob !== 'undefined') {
      try {
        const blob = new Blob([meshData.imageBytes], { type: meshData.mimeType || 'image/png' });
        const objectUrl = URL.createObjectURL(blob);
        const texture = new THREE.TextureLoader().load(objectUrl);
        if (THREE.SRGBColorSpace) {
          texture.colorSpace = THREE.SRGBColorSpace;
        } else if (THREE.sRGBEncoding) {
          texture.encoding = THREE.sRGBEncoding;
        }
        material = new THREE.MeshStandardMaterial({
          map: texture,
          roughness: 0.85,
          metalness: 0.05
        });
      } catch (err) {
        // Fallback to color if texture creation fails
        const c = meshData.color || [0.8, 0.8, 0.8];
        material = new THREE.MeshStandardMaterial({
          color: new THREE.Color(c[0], c[1], c[2]),
          roughness: 0.85,
          metalness: 0.05
        });
      }
    } else {
      const c = meshData.color || [0.8, 0.8, 0.8];
      material = new THREE.MeshStandardMaterial({
        color: new THREE.Color(c[0], c[1], c[2]),
        roughness: 0.85,
        metalness: 0.05
      });
    }

    const mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    return mesh;
  }

  const MinimalGLBLoader = {
    parseGLBContainer,
    parseGLBToMeshData,
    buildThreeMeshFromGLB
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = MinimalGLBLoader;
  }
  if (typeof window !== 'undefined') {
    window.MinimalGLBLoader = MinimalGLBLoader;
  }
})(typeof globalThis !== 'undefined' ? globalThis : typeof window !== 'undefined' ? window : this);
