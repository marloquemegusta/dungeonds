"""Recorta la cola quieta del remate de la Super Monja (smonja_d*.bin) a N fotogramas + restos.

Los renders del lab ya no estan en el repo, asi que se trabaja sobre los bins: el movimiento real acaba hacia el
fotograma 15 (diferencias de cientos de pixeles) y los fotogramas 16..35 solo reasientan unos pocos pixeles.
Se conservan los N primeros fotogramas y el de restos; cambia `frames` de smonja en source/remate_sprites.c.

Uso: python tools/trim_remate_smonja.py [N] (por defecto 18; el bin de partida debe tener FROM=36 fotogramas).
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_remate_sprites as G

WT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FROM = 36
N = int(sys.argv[1]) if len(sys.argv) > 1 else 18
MAGIC = G.MAGIC   # 'RMT1': mascaras 1 bpp; el empaquetado y la migracion viven en generate_remate_sprites.py


def trim(path, F, n):
    G.migrate_bin_masks(path, F)   # un bin 'RMAT' antiguo (4 bpp) pasa a 'RMT1' antes de recortarlo; si ya lo es, no hace nada
    b = open(path, 'rb').read()
    magic, pb, rb, mb = struct.unpack_from('<4I', b, 0)
    assert magic == MAGIC
    off = 16

    def take(fmt, cnt):
        nonlocal off
        v = struct.unpack_from('<%d%s' % (cnt, fmt), b, off)
        off += cnt * struct.calcsize(fmt)
        return list(v)

    fb = [tuple(take('B', 4)) for _ in range(F + 1)]
    fp = take('I', F + 1); fr = take('I', F + 1)
    sb = [tuple(take('B', 4)) for _ in range(F)]
    so = take('I', F)
    db = [tuple(take('B', 4)) for _ in range(F + 1)]
    dp = take('I', F + 1); dr = take('I', F + 1)
    pix = struct.unpack_from('<%dH' % (pb // 2), b, off); off += pb
    runs = struct.unpack_from('<%dH' % (rb // 2), b, off); off += rb
    masks = b[off:off + mb]
    assert all(x[2] == 0 for x in db), 'solo capa unica'
    pend, rend = pb // 2, rb // 2
    seg = lambda arr, i, end: arr[i] if i < F else end
    npix, nruns, nfp, nfr = [], [], [], []
    for i in list(range(n)) + [F]:
        s = fp[i]; e = fp[i + 1] if i < F else pend
        nfp.append(len(npix)); npix.extend(pix[s:e])
        s = fr[i]; e = fr[i + 1] if i < F else rend
        nfr.append(len(nruns)); nruns.extend(runs[s:e])
    ndp = [nfp[i + 1] for i in range(n)] + [len(npix)]
    ndr = [nfr[i + 1] for i in range(n)] + [len(nruns)]
    # mascaras de sombra: las de los n primeros fotogramas son un prefijo (offsets crecientes)
    mx = max(so[:n])
    nxt = [o for o in so if o > mx]
    mend = min(nxt) if nxt else mb
    nmasks = bytearray(masks[:mend])
    while len(nmasks) & 3:
        nmasks.append(0)
    if len(npix) & 1: npix.append(0)
    if len(nruns) & 1: nruns.append(0)
    fbn = fb[:n] + [fb[F]]
    out = bytearray(struct.pack('<4I', MAGIC, len(npix) * 2, len(nruns) * 2, len(nmasks)))
    for x in fbn: out += struct.pack('<4B', *x)
    out += struct.pack('<%dI' % (n + 1), *nfp)
    out += struct.pack('<%dI' % (n + 1), *nfr)
    for x in sb[:n]: out += struct.pack('<4B', *x)
    out += struct.pack('<%dI' % n, *so[:n])
    for _ in range(n + 1): out += struct.pack('<4B', 0, 0, 0, 0)
    out += struct.pack('<%dI' % (n + 1), *ndp)   # dp/dr: capa B vacia (misma convencion que el generador)
    out += struct.pack('<%dI' % (n + 1), *ndr)
    out += struct.pack('<%dH' % len(npix), *npix)
    out += struct.pack('<%dH' % len(nruns), *nruns)
    out += bytes(nmasks)
    return bytes(out), len(b)


for d in range(8):
    p = os.path.join(WT, 'nitrofiles', 'remate', 'smonja_d%d.bin' % d)
    data, old = trim(p, FROM, N)
    open(p, 'wb').write(data)
    print('smonja_d%d.bin %d -> %d bytes' % (d, old, len(data)))

cp = os.path.join(WT, 'source', 'remate_sprites.c')
t = open(cp, encoding='utf-8', newline='').read()
t2 = t.replace('{ 160, 160, 1, %d, %d, 4 }, /* smonja */' % (FROM, FROM), '{ 160, 160, 1, %d, %d, 4 }, /* smonja */' % (N, N))
assert t2 != t
open(cp, 'w', encoding='utf-8', newline='').write(t2)
