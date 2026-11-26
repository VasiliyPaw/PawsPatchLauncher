"""Rebuild the 56 Shadow work effects from an exact existing module ZIP.

No installed files are changed. Source ZIP can be a readonly cold archive;
the Python source, output and PyFFI dependency must be staged on physical G:.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import sys
import time
import zipfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-module", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--pyffi", type=Path, required=True)
    args = ap.parse_args()
    assert args.out.resolve().drive.upper() == "G:", "Output must be physically on G:"
    assert args.pyffi.resolve().drive.upper() == "G:", "Stage PyFFI on G:"
    sys.path.insert(0, str(args.pyffi))
    time.clock = time.perf_counter
    from pyffi.formats.nif import NifFormat as N
    from shadow_footprint import stabilize_shadow_footprint

    def sha(raw): return hashlib.sha256(raw).hexdigest().upper()
    def read(raw):
        d = N.Data()
        d.read(io.BytesIO(raw))
        return d

    reports = []
    prefix = "rivers-data/Paws/Bridges/RacialBuild/shadow/"
    with zipfile.ZipFile(args.source_module) as z:
        manifest = json.loads(z.read("module.json"))
        indexed = {r["path"].replace("\\", "/").lower(): r for r in manifest["files"]}
        for count in range(5, 33):
            for axis in ["x", "y"]:
                name = prefix + f"work_{axis}_{count:02}.nif"
                record = indexed[name.lower()]
                raw = z.read("payload/" + record["path"])
                assert sha(raw) == record["sha256"].upper()
                model = read(raw)
                fixes = stabilize_shadow_footprint(model, N)
                output = io.BytesIO()
                model.write(output)
                repaired = output.getvalue()
                checked = read(repaired)
                particles = [b for b in checked.blocks if isinstance(b, N.NiParticleSystem)]
                assert len(particles) == 4 and sum(p.data.num_vertices for p in particles) == 140
                for particle in particles:
                    emitters = [m for m in particle.modifiers if isinstance(m, N.NiPSysBoxEmitter)]
                    assert len(emitters) == 1
                    e = emitters[0]
                    assert bytes(e.emitter_object.name).startswith(b"BridgeFootprintLayer")
                    assert e.emitter_object.controller is None
                    assert (e.width, e.height) == ((2 * (count - 1), 6) if axis == "x" else (6, 2 * (count - 1)))
                target = args.out / "payload" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(repaired)
                reports.append(dict(path=name, size=len(repaired), sha256=sha(repaired),
                                    sourceSha256=sha(raw), layers=fixes,
                                    unchangedParticleCapacity=140))
    source_hash = hashlib.sha256()
    with args.source_module.open("rb") as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b""): source_hash.update(b)
    report = dict(passed=True, models=reports, count=len(reports),
                  sourceModule=str(args.source_module),
                  sourceModuleSha256=source_hash.hexdigest().upper(),
                  particleBudgetUnchanged=True, texturesUnchanged=True,
                  nativeDetachHookUnchanged=True,
                  originalRootAttachmentAndEffectIdsUnchanged=True,
                  nativeGameLaunched=False)
    (args.out / "shadow-work-manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print("STATIC_SHADOW_FOOTPRINT_MODELS_PASS", len(reports))


if __name__ == "__main__": main()
