#!/usr/bin/env python3
"""MDE-60 — rekonesans struktury loader.swf bez Javy (pure-Python parser tagów SWF).

Rozpakowuje CWS (zlib) i chodzi po tagach AVM1/AS2. Cel: wyciągnąć dokładną mapę
symboli bibliotecznych (ExportAssets: charId <-> nazwa) potrzebnych do modu HUD
„My Team" — ikony banera (UI_Banner*Icon), okna-wzorce (UI_Party / UI_Friends),
oraz policzyć nośniki kodu AS2 (DoAction / DoInitAction / DefineSprite).

Użycie:
    python swf_recon.py [ścieżka/do/loader.swf]   # domyślnie ../resources/app/retroclient/loader.swf
    python swf_recon.py --grep Banner             # filtruj nazwy symboli
"""
import os, sys, zlib, struct

TAG_NAMES = {
    0: "End", 1: "ShowFrame", 6: "DefineBits", 9: "SetBackgroundColor",
    12: "DoAction", 20: "DefineBitsLossless", 21: "DefineBitsJPEG2",
    22: "DefineShape2", 26: "PlaceObject2", 32: "DefineShape3",
    34: "DefineButton2", 36: "DefineBitsLossless2", 37: "DefineEditText",
    39: "DefineSprite", 43: "FrameLabel", 46: "DefineMorphShape",
    48: "DefineFont2", 56: "ExportAssets", 59: "DoInitAction",
    76: "SymbolClass", 82: "DoABC", 88: "DefineFontName",
}

def read_uncompressed(path):
    d = open(path, "rb").read()
    sig = d[:3]
    if sig == b"CWS":
        body = zlib.decompress(d[8:])
    elif sig == b"FWS":
        body = d[8:]
    else:
        raise SystemExit(f"Nieznana sygnatura SWF: {sig!r}")
    return d[3], body  # (wersja Flash, ciało: RECT + framerate + framecount + tagi)

def skip_rect(body):
    nbits = body[0] >> 3
    total_bits = 5 + nbits * 4
    return (total_bits + 7) // 8  # bajty zajęte przez RECT

def iter_tags(body):
    off = skip_rect(body) + 4  # RECT + frameRate(2) + frameCount(2)
    end = len(body)
    while off < end:
        code_len = struct.unpack_from("<H", body, off)[0]
        off += 2
        code = code_len >> 6
        length = code_len & 0x3F
        if length == 0x3F:
            length = struct.unpack_from("<I", body, off)[0]
            off += 4
        payload = body[off:off + length]
        yield code, payload
        off += length
        if code == 0:  # End
            break

def parse_export_assets(payload):
    count = struct.unpack_from("<H", payload, 0)[0]
    off = 2
    out = []
    for _ in range(count):
        tag_id = struct.unpack_from("<H", payload, off)[0]
        off += 2
        s = off
        while payload[off] != 0:
            off += 1
        name = payload[s:off].decode("latin1")
        off += 1
        out.append((tag_id, name))
    return out

class Bits:
    """Czytnik bitowy MSB-first (do MATRIX / CXFORM w PlaceObject2)."""
    def __init__(self, data, off):
        self.data = data
        self.byte = off
        self.bit = 0

    def align(self):
        if self.bit:
            self.bit = 0
            self.byte += 1

    def ub(self, n):
        v = 0
        for _ in range(n):
            v = (v << 1) | ((self.data[self.byte] >> (7 - self.bit)) & 1)
            self.bit += 1
            if self.bit == 8:
                self.bit = 0
                self.byte += 1
        return v

    def sb(self, n):
        v = self.ub(n)
        if n and (v >> (n - 1)):
            v -= (1 << n)
        return v

def skip_matrix(bits):
    if bits.ub(1):  # HasScale
        nb = bits.ub(5)
        bits.ub(nb); bits.ub(nb)
    if bits.ub(1):  # HasRotate
        nb = bits.ub(5)
        bits.ub(nb); bits.ub(nb)
    nb = bits.ub(5)  # NTranslateBits
    bits.sb(nb); bits.sb(nb)
    bits.align()

def skip_cxform(bits):
    has_add = bits.ub(1)
    has_mult = bits.ub(1)
    nb = bits.ub(4)
    if has_mult:
        for _ in range(4): bits.sb(nb)
    if has_add:
        for _ in range(4): bits.sb(nb)
    bits.align()

def parse_place_object2(payload):
    """Zwróć (depth, charId|None, name|None) z tagu PlaceObject2."""
    flags = payload[0]
    off = 1
    depth = struct.unpack_from("<H", payload, off)[0]; off += 2
    char_id = None
    if flags & 0x02:  # HasCharacter
        char_id = struct.unpack_from("<H", payload, off)[0]; off += 2
    if flags & 0x04:  # HasMatrix
        b = Bits(payload, off); skip_matrix(b); off = b.byte
    if flags & 0x08:  # HasColorTransform
        b = Bits(payload, off); skip_cxform(b); off = b.byte
    if flags & 0x10:  # HasRatio
        off += 2
    name = None
    if flags & 0x20:  # HasName
        s = off
        while payload[off] != 0: off += 1
        name = payload[s:off].decode("latin1")
    return depth, char_id, name

def find_sprite_payload(body, target_id):
    for code, payload in iter_tags(body):
        if code == 39:  # DefineSprite
            sid = struct.unpack_from("<H", payload, 0)[0]
            if sid == target_id:
                return payload
    return None

def iter_sprite_tags(sprite_payload):
    # DefineSprite payload: SpriteID(2) + FrameCount(2) + tagi kontrolne
    off = 4
    end = len(sprite_payload)
    while off < end:
        code_len = struct.unpack_from("<H", sprite_payload, off)[0]; off += 2
        code = code_len >> 6
        length = code_len & 0x3F
        if length == 0x3F:
            length = struct.unpack_from("<I", sprite_payload, off)[0]; off += 4
        yield code, sprite_payload[off:off + length]
        off += length
        if code == 0:
            break

def dump_sprite(body, exports, target):
    id_to_name = {cid: n for cid, n in exports}
    name_to_id = {n: cid for cid, n in exports}
    target_id = int(target) if target.isdigit() else name_to_id.get(target)
    if target_id is None:
        print(f"Nie znaleziono symbolu {target!r}"); return
    payload = find_sprite_payload(body, target_id)
    if payload is None:
        print(f"Brak DefineSprite #{target_id}"); return
    print(f"# Sprite {id_to_name.get(target_id, '?')} (#{target_id}) — placed instances")
    for code, p in iter_sprite_tags(payload):
        if code in (26, 70):  # PlaceObject2 / PlaceObject3 (uproszczone dla 26)
            try:
                depth, cid, name = parse_place_object2(p if code == 26 else p[2:])
            except Exception as e:
                print(f"  [parse err @depth?] {e}"); continue
            sym = id_to_name.get(cid, "-") if cid is not None else "-"
            print(f"  depth {depth:<4} char #{str(cid):<6} {sym:<28} instance={name}")

def main():
    argv = sys.argv[1:]
    grep = None
    sprite = None
    if "--grep" in argv:
        i = argv.index("--grep")
        grep = argv[i + 1].lower()
        del argv[i:i + 2]  # usuń flagę i jej wartość, by nie trafiła jako ścieżka
    if "--sprite" in argv:
        i = argv.index("--sprite")
        sprite = argv[i + 1]
        del argv[i:i + 2]
    args = [a for a in argv if not a.startswith("--")]
    here = os.path.dirname(os.path.abspath(__file__))
    default = os.path.join(here, "..", "resources", "app", "retroclient", "loader.swf")
    path = args[0] if args else default

    ver, body = read_uncompressed(path)
    counts = {}
    exports = []
    for code, payload in iter_tags(body):
        counts[code] = counts.get(code, 0) + 1
        if code == 56:  # ExportAssets
            exports.extend(parse_export_assets(payload))

    if sprite is not None:
        dump_sprite(body, exports, sprite)
        return

    print(f"# {os.path.relpath(path)} — Flash v{ver} (AVM1/AS2), body {len(body)} B")
    print("\n## Rozkład tagów")
    for code in sorted(counts, key=lambda c: -counts[c]):
        print(f"  {counts[code]:6d}  {code:3d}  {TAG_NAMES.get(code, '?')}")

    print(f"\n## ExportAssets — {len(exports)} nazwanych symboli")
    names = exports if grep is None else [e for e in exports if grep in e[1].lower()]
    if grep:
        print(f"(filtr: {grep!r} → {len(names)} trafień)")
    for tag_id, name in sorted(names, key=lambda e: e[1]):
        print(f"  #{tag_id:<6d} {name}")

if __name__ == "__main__":
    main()
