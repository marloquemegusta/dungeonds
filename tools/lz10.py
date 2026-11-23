"""LZ10 (el formato de swiDecompressLZSSWram de la BIOS), compartido por los generadores."""
import struct


def lz10_compress(data: bytes) -> bytes:
    n = len(data)
    out = bytearray(struct.pack("<I", 0x10 | (n << 8)))
    heads = {}
    pos = 0
    flags_pos = None
    bit = 0
    while pos < n:
        if bit == 0:
            flags_pos = len(out)
            out.append(0)
        best_len, best_disp = 0, 0
        if pos + 3 <= n:
            key = data[pos:pos + 3]
            chain = heads.get(key, ())
            for cand in reversed(chain[-48:]):
                disp = pos - cand
                if disp > 4096:
                    break
                ln = 3
                while ln < 18 and pos + ln < n and data[cand + ln] == data[pos + ln]:
                    ln += 1
                if ln > best_len:
                    best_len, best_disp = ln, disp
                    if ln == 18:
                        break
        step = best_len if best_len >= 3 else 1
        if best_len >= 3:
            out[flags_pos] |= 0x80 >> bit
            d = best_disp - 1
            out += bytes(((best_len - 3) << 4 | (d >> 8), d & 0xff))
        else:
            out.append(data[pos])
        for k in range(pos, min(pos + step, n - 2)):
            heads.setdefault(data[k:k + 3], []).append(k)
        pos += step
        bit = (bit + 1) & 7
    while len(out) & 3:
        out.append(0)
    return bytes(out)


def lz10_decompress(blob: bytes) -> bytes:
    assert blob[0] == 0x10
    size = struct.unpack_from("<I", blob, 0)[0] >> 8
    out = bytearray()
    i = 4
    while len(out) < size:
        flags = blob[i]; i += 1
        for b in range(8):
            if len(out) >= size:
                break
            if flags & (0x80 >> b):
                x, y = blob[i], blob[i + 1]; i += 2
                ln, disp = (x >> 4) + 3, (((x & 15) << 8) | y) + 1
                for _ in range(ln):
                    out.append(out[-disp])
            else:
                out.append(blob[i]); i += 1
    return bytes(out)
