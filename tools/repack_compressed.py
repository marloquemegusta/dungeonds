"""Convierte nitrofiles/levelup/*.bin y nitrofiles/bestiary/*.bin del formato sin comprimir al comprimido (LZ10).
Idempotente: los que ya estan comprimidos se saltan. Uso: python tools/repack_compressed.py [--check]"""
import struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from lz10 import lz10_compress, lz10_decompress

ROOT = Path(__file__).resolve().parent.parent / "nitrofiles"
LVC_RAW, LVC_LZ = 0x4C43, 0x4C44
BST_RAW, BST_LZ = 0x4251, 0x4252
BST_HDR = 584


def lvc_compress(raw):
    """raw: bytes del formato viejo -> formato comprimido (cabecera 516 B + LZ10 de los indices)."""
    head, pix = raw[:516], raw[516:]
    return struct.pack("<H", LVC_LZ) + head[2:] + lz10_compress(pix)


def lvc_decompress(data):
    return struct.pack("<H", LVC_RAW) + data[2:516] + lz10_decompress(data[516:])


def bst_compress(raw):
    hdr = bytearray(raw[:BST_HDR])
    offs = struct.unpack_from("<8I", hdr, 520)
    sizes = struct.unpack_from("<8I", hdr, 552)
    blocks = [lz10_compress(raw[o:o + s]) for o, s in zip(offs, sizes)]
    pos, new_offs = BST_HDR, []
    for b in blocks:
        new_offs.append(pos)
        pos += len(b)
    struct.pack_into("<H", hdr, 0, BST_LZ)
    struct.pack_into("<8I", hdr, 520, *new_offs)
    struct.pack_into("<8I", hdr, 552, *[len(b) for b in blocks])
    return bytes(hdr) + b"".join(blocks)


def bst_decompress(data):
    hdr = bytearray(data[:BST_HDR])
    offs = struct.unpack_from("<8I", hdr, 520)
    sizes = struct.unpack_from("<8I", hdr, 552)
    blocks = [lz10_decompress(data[o:o + s]) for o, s in zip(offs, sizes)]
    pos, new_offs = BST_HDR, []
    for b in blocks:
        new_offs.append(pos)
        pos += len(b)
    struct.pack_into("<H", hdr, 0, BST_RAW)
    struct.pack_into("<8I", hdr, 520, *new_offs)
    struct.pack_into("<8I", hdr, 552, *[len(b) for b in blocks])
    return bytes(hdr) + b"".join(blocks)


def main():
    check = "--check" in sys.argv
    for folder, raw_m, comp, decomp in (("levelup", LVC_RAW, lvc_compress, lvc_decompress),
                                        ("bestiary", BST_RAW, bst_compress, bst_decompress)):
        for p in sorted((ROOT / folder).glob("*.bin")):
            data = p.read_bytes()
            if struct.unpack_from("<H", data)[0] != raw_m:
                print("skip", p.name)
                continue
            new = comp(data)
            ok = decomp(new) == data
            print("%s/%s %d -> %d roundtrip=%s" % (folder, p.name, len(data), len(new), ok))
            assert ok
            if not check:
                p.write_bytes(new)


if __name__ == "__main__":
    main()
