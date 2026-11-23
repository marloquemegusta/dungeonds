"""Compresor LZ77 en el formato de la BIOS de la DS (tipo 0x10, 'LZ77 WRAM').

Lo descomprime en el cartucho/RAM la funcion de libnds `decompress(src, dst, LZ77)` (BIOS 0x11). Sirve para cualquier
bloque binario que se quiera guardar comprimido (hoy: pixeles de los fotogramas del Campanero en
tools/generate_campanero_bin.py; pensado tambien para los bins de nitrofiles/chars/ de enemigos pesados).

Formato: byte 0x10, tamano descomprimido en 3 bytes little endian, y bloques de 1 byte de banderas (bit 7 primero;
1 = referencia) seguidos de 8 elementos: literal (1 byte) o referencia de 2 bytes ((longitud-3) << 4 | (desp-1) >> 8, (desp-1) & 255),
longitud 3..18, desplazamiento 1..4096. El resultado se rellena con ceros hasta multiplo de 4.
"""


def compress(data: bytes) -> bytes:
    n = len(data)
    assert n < (1 << 24)
    out = bytearray([0x10, n & 255, (n >> 8) & 255, (n >> 16) & 255])
    chains = {}                      # clave de 3 bytes -> posiciones (las mas recientes al final)
    pos = 0
    flags_at, nflags, items = None, 0, 0

    def add_item(is_ref, payload):
        nonlocal flags_at, nflags, items
        if nflags == 0:
            flags_at = len(out)
            out.append(0)
        if is_ref:
            out[flags_at] |= 0x80 >> nflags
        out.extend(payload)
        nflags = (nflags + 1) & 7

    def insert(p):
        if p + 3 <= n:
            chains.setdefault(data[p:p + 3], []).append(p)

    while pos < n:
        best_len, best_disp = 0, 0
        if pos + 3 <= n:
            cand = chains.get(data[pos:pos + 3], ())
            tried = 0
            for q in reversed(cand):
                disp = pos - q
                if disp > 4096:
                    break
                tried += 1
                if tried > 64:
                    break
                ln = 3
                lim = min(18, n - pos)
                while ln < lim and data[q + ln] == data[pos + ln]:
                    ln += 1
                if ln > best_len:
                    best_len, best_disp = ln, disp
                    if ln == lim:
                        break
        if best_len >= 3:
            v = best_disp - 1
            add_item(True, bytes([((best_len - 3) << 4) | (v >> 8), v & 255]))
            for k in range(best_len):
                insert(pos + k)
            pos += best_len
        else:
            add_item(False, bytes([data[pos]]))
            insert(pos)
            pos += 1
    while len(out) & 3:
        out.append(0)
    return bytes(out)


def decompress(blob: bytes) -> bytes:
    """Descompresor de referencia (para el test de host del compresor)."""
    assert blob[0] == 0x10
    size = blob[1] | (blob[2] << 8) | (blob[3] << 16)
    out = bytearray()
    i = 4
    while len(out) < size:
        flags = blob[i]
        i += 1
        for b in range(8):
            if len(out) >= size:
                break
            if flags & (0x80 >> b):
                ln = (blob[i] >> 4) + 3
                disp = (((blob[i] & 15) << 8) | blob[i + 1]) + 1
                i += 2
                for _ in range(ln):
                    out.append(out[-disp])
            else:
                out.append(blob[i])
                i += 1
    return bytes(out)
