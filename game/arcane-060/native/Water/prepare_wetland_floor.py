"""Build only the missing 256px wetland bottom mixtures from original inputs.

Existing frozen/mist-swamp aliases reuse byte-identical floor asset families.
Reads archives by entry rather than unpacking a game. Never edits the inputs.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import struct

import numpy as np
from PIL import Image


def text(raw):
    return raw.decode("utf-16") if raw.startswith(b"\xff\xfe") else raw.decode("cp1252")


class Inputs:
    def __init__(self, archive, data):
        self.archive, self.data = archive, data
        self.f = archive.open("rb")
        self.f.seek(-288, 2)
        sections = {}
        for _ in range(3):
            b = self.f.read(96)
            sections[b[:64].decode("utf-16le").split("\0")[0]] = struct.unpack_from("<QQIIQ", b, 64)[:2]
        self.base = sections["Files"][0]
        self.f.seek(sections["Footer"][0])
        self.rows = {}
        for _ in range(struct.unpack("<I", self.f.read(4))[0]):
            n = struct.unpack("<H", self.f.read(2))[0]
            name = self.f.read(n * 2).decode("utf-16le")
            off, size, _, _ = struct.unpack("<QQII", self.f.read(24))
            self.rows[name.lower()] = (name, off, size)
        self.used = {}

    def read(self, name):
        loose = self.data / name
        if loose.is_file():
            raw, origin = loose.read_bytes(), str(loose)
        else:
            original, off, size = self.rows[name.lower()]
            self.f.seek(self.base + off)
            raw, origin = self.f.read(size), str(self.archive) + "::" + original
        self.used[origin] = hashlib.sha256(raw).hexdigest()
        return raw


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-archive", type=Path, required=True)
    p.add_argument("--game-data", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve()
    assert out.drive.upper() == "G:", "New outputs must be physically on G:"
    out.mkdir(parents=True, exist_ok=True)
    target = out / "assets/Textures/PawsWaterFloor"
    target.mkdir(parents=True, exist_ok=True)
    inp = Inputs(a.base_archive, a.game_data)
    try:
        definitions = {n: inp.read(n) for n in inp.rows if n.startswith("terrain/") and n.endswith(".tgi")}
        for f in (a.game_data / "Terrain").rglob("*.tgi"):
            definitions[f.relative_to(a.game_data).as_posix().lower()] = inp.read(f.relative_to(a.game_data).as_posix())
        variations = {}
        for name, raw in definitions.items():
            t = text(raw)
            if not re.search(r"\btemplate\s*=\s*WaterTerrain\b", t):
                continue
            for block in re.split(r"\[Variation\]", t)[1:]:
                id_match = re.search(r"\bIDS\s*=\s*(\w+)", block)
                tex_match = re.search(r"\btexture\s*=\s*([^\r\n]+)", block)
                if id_match and tex_match:
                    texture = tex_match[1].strip().strip('"').replace("\\", "/")
                    variations[id_match[1]] = (Path(name).parent / texture).as_posix()
        slots = ("temperate", "arctic", "desert", "cursed")
        refs = [Image.open(io.BytesIO(inp.read(variations[s + "_lake01"]))).convert("RGB") for s in slots]
        header = Path(__file__).with_name("water_floor_sources.h").read_text()
        sources = re.findall(r'\{L"([^"]+)",(\d),L"([^"]+)"\}', header)
        new_ids = {"temperate_marsh01", "temperate_marsh02", "cursed_marsh01", "cursed_marsh02",
                   "desert_quicksand01", "arctic_watershadow01", "desert_watershadow01", "desert_waterblood01"}
        palette = [(i, j, k, 8 - i - j - k) for i in range(9) for j in range(9 - i) for k in range(9 - i - j)]
        result, count, size = [], 0, 0
        for id, slot, asset in sources:
            if id != asset or id not in new_ids:
                continue
            own = int(slot)
            original = Image.open(io.BytesIO(inp.read(variations[id]))).convert("RGB")
            original.thumbnail((256, 256))
            layers = [np.asarray(im.resize(original.size, Image.Resampling.BILINEAR)).astype(np.float32) for im in refs]
            layers[own] = np.asarray(original).astype(np.float32)
            for code, weights in enumerate(palette, 1):
                if weights[own] in (0, 8):
                    continue
                rgb = np.rint(sum(im * (w / 8) for im, w in zip(layers, weights))).clip(0, 255).astype(np.uint8)
                dest = target / f"{id}_{code}.png"
                Image.fromarray(rgb).convert("RGBA").save(dest, compress_level=9)
                # Verify every emitted asset and exact pixel values after encoding.
                actual = Image.open(dest)
                assert actual.size == original.size and actual.mode == "RGBA"
                assert np.array_equal(np.asarray(actual)[:, :, :3], rgb)
                count += 1
                size += dest.stat().st_size
            result.append({"id": id, "source": variations[id], "dimensions": original.size})
        assert len(result) == len(new_ids)
        report = {"sources": result, "files": count, "bytes": size,
                  "aliases": [{"id": id, "asset": asset} for id, _, asset in sources if id != asset],
                  "inputSha256": inp.used, "verification": "Every PNG reopened; exact decoded RGB equality"}
        (out / "wetland-floor-assets.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("WETLAND_FLOOR_ASSETS_PASS", count, "files", size, "bytes")
    finally:
        inp.f.close()


if __name__ == "__main__":
    main()
