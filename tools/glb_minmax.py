"""Lector minimo de GLB (mallas ya horneadas, sin piel): vertices en mundo (glTF, Y arriba)."""
import json
import struct
import numpy as np

_CT = {5126: ('<f4', 4), 5123: ('<u2', 2), 5125: ('<u4', 4)}


def _local(n):
    if 'matrix' in n:
        return np.array(n['matrix'], dtype=np.float64).reshape(4, 4).T
    t = np.array(n.get('translation', [0, 0, 0]), dtype=np.float64)
    q = n.get('rotation', [0, 0, 0, 1])
    s = np.array(n.get('scale', [1, 1, 1]), dtype=np.float64)
    x, y, z, w = q
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m = np.eye(4)
    m[:3, :3] = r * s
    m[:3, 3] = t
    return m


def world_points(path, only=None, by_node=None):
    data = open(path, 'rb').read()
    jl, _ = struct.unpack_from('<II', data, 12)
    js = json.loads(data[20:20 + jl])
    off = 20 + jl
    bl, _ = struct.unpack_from('<II', data, off)
    blob = data[off + 8:off + 8 + bl]
    pts = []

    def walk(ni, parent):
        n = js['nodes'][ni]
        m = parent @ _local(n)
        if 'mesh' in n and (only is None or only in n.get('name', '')):
            for p in js['meshes'][n['mesh']]['primitives']:
                acc = js['accessors'][p['attributes']['POSITION']]
                bv = js['bufferViews'][acc['bufferView']]
                o = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
                stride = bv.get('byteStride', 12)
                raw = np.frombuffer(blob, dtype=np.uint8, count=(acc['count'] - 1) * stride + 12, offset=o)
                v = np.lib.stride_tricks.as_strided(raw, shape=(acc['count'], 12), strides=(stride, 1)).copy().view('<f4').reshape(-1, 3)
                v = np.c_[v.astype(np.float64), np.ones(len(v))] @ m.T
                pts.append(v[:, :3])
                if by_node is not None:
                    by_node.setdefault(n.get('name', ''), []).append(v[:, :3])
        for c in n.get('children', []):
            walk(c, m)

    sc = js['scenes'][js.get('scene', 0)]
    for r in sc['nodes']:
        walk(r, np.eye(4))
    return np.vstack(pts) if pts else np.zeros((0, 3))


def node_translation(path, name):
    """Traslacion (x, y, z) glTF del primer nodo cuyo nombre contiene `name`."""
    data = open(path, 'rb').read()
    jl, _ = struct.unpack_from('<II', data, 12)
    js = json.loads(data[20:20 + jl])
    for n in js['nodes']:
        if name in n.get('name', ''):
            return tuple(n.get('translation', [0, 0, 0]))
    raise KeyError(name)


def min_y(path):
    p = world_points(path)
    return float(p[:, 1].min()) if len(p) else 0.0
