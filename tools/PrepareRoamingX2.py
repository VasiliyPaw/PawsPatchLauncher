"""Build verified, combined x2 roaming overlays and LOCAL signed candidate feeds.

No game installation, canonical feed changes or publication. Existing 13 packages,
including all seven badge models, retain their exact hashes.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile
import PrepareBeta7Release as base

OUT = base.REPO / "release_workspace_059" / "components-v2"
VERSION = "1.3.72-options.3"
FIELD = lambda name: re.compile(rb"(?m)^(\s*" + name + rb"\s*=\s*)([0-9.]+)([^\r\n]*)(\r?$)")


def payload(package):
    path = Path(package["urls"][0])
    assert path.is_file() and path.stat().st_size == package["size"] and base.sha(path) == package["sha256"].upper()
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read("module.json"))
        assert manifest["id"] == package["id"] and manifest["version"] == package["version"] and not manifest.get("remove")
        names = {n.replace("\\", "/").lower(): n for n in archive.namelist()}
        result = {}
        for file in manifest["files"]:
            name = file["path"].replace("\\", "/")
            data = archive.read(names[("payload/" + name).lower()])
            assert len(data) == file["size"] and hashlib.sha256(data).hexdigest().upper() == file["sha256"].upper()
            result[name] = data
        return result


def transform(data, name):
    times, chances, marauders = [list(FIELD(field).finditer(data)) for field in (b"event_time", b"event_chance", b"marauder_chance")]
    if not times or not chances or not marauders:
        return data, None
    # Reviewed source files have a single explicit LairComponent event, no global replacement.
    assert len(times) == len(chances) == len(marauders) == 1, name
    time, chance, marauder = [float(matches[0][2]) for matches in (times, chances, marauders)]
    if chance == 0 or marauder == 0:
        return data, None
    assert time > 0 and 0 < chance <= 1 and 0 < marauder <= 1
    new_chance = min(chance * 1.5, 1)
    new_time = time * new_chance / chance / 2
    # All current active inputs remain below the chance cap.
    assert new_chance < 1, (name, chance)
    changed = data
    for field, value in ((b"event_time", new_time), (b"event_chance", new_chance)):
        changed = FIELD(field).sub(lambda m: m[1] + format(value, ".8g").encode("ascii") + m[3] + m[4], changed)
    # Prove these two scalar values are the ONLY modifications, including translation bytes.
    scrub = lambda raw: FIELD(b"event_chance").sub(rb"\g<1>#\g<3>\g<4>", FIELD(b"event_time").sub(rb"\g<1>#\g<3>\g<4>", raw))
    assert scrub(changed) == scrub(data)
    assert abs((new_chance / new_time) / (chance / time) - 2) < 1e-8
    return changed, {"path": name, "time": [time, new_time], "chance": [chance, new_chance], "marauder": marauder, "expectedRatio": 2}


def main():
    if len(sys.argv) == 3 and sys.argv[2] == "--refresh-guide":
        guide = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
        guide["version"] = "0.2.1"
        for channel in ("stable", "beta"):
            unsigned = OUT / "feed" / (channel + ".local.payload.json")
            signed = OUT / "feed" / (channel + ".local.signed.json")
            candidate = base.read_feed(signed)
            candidate["patchGuide"] = guide
            unsigned.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            base.run(base.DOTNET, base.PUBLISHER, "sign", unsigned, base.KEYS / "pawpatch-signing-private.pem", "pawpatch-prod-2026", signed)
            base.run(base.DOTNET, base.PUBLISHER, "verify", signed, base.KEYS / "pawpatch-signing-public.pem")
        return
    assert not OUT.exists(), "Use a fresh staging directory; do not overwrite candidates."
    feed = base.read_feed(base.REPO / "release_workspace_020/feed/stable.local.signed.json")
    packages = {p["id"]: p for p in feed["packages"]}
    evidence = []
    additions = []
    for suffix, original in (("with-new", "roaming-profile-standard-with-new"), ("no-new", "roaming-profile-standard-no-new")):
        module = "roaming-profile-x2-" + suffix
        source = OUT / "sources" / module
        active = []
        files = payload(packages[original])
        for name, data in files.items():
            changed, event = transform(data, name)
            target = (source / name).resolve()
            assert target.is_relative_to(source.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(changed)
            if event:
                active.append(event)
        assert active
        archive = OUT / "packages" / (module + "-" + VERSION + ".zip")
        archive.parent.mkdir(parents=True, exist_ok=True)
        base.run(base.DOTNET, base.PUBLISHER, "pack", module, VERSION, source, archive)
        package = copy.deepcopy(packages[original])
        package.update(id=module, version=VERSION, priority=530 if suffix == "with-new" else 540,
                       size=archive.stat().st_size, sha256=base.sha(archive), urls=[str(archive)])
        package["name"] = {"ru": "Частота ×2: " + ("с новыми ротами" if suffix == "with-new" else "без новых рот"), "en": "Frequency ×2: " + suffix}
        package["description"] = {"ru": "Совместный профиль частоты и состава блуждающих рот", "en": "Combined roaming frequency and company profile"}
        additions.append(package)
        evidence.append({"module": module, "files": len(files), "activeSources": active, "sha256": package["sha256"]})
    # Use the authored guide generated by the newly built launcher, not old release prose.
    guide = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    guide["version"] = "0.2.1"
    for channel in ("stable", "beta"):
        candidate = base.read_feed(base.REPO / f"release_workspace_020/feed/{channel}.local.signed.json")
        candidate["packages"].extend(copy.deepcopy(additions))
        candidate["patchGuide"] = guide
        folder = OUT / "feed"
        folder.mkdir(parents=True, exist_ok=True)
        unsigned = folder / (channel + ".local.payload.json")
        unsigned.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        signed = folder / (channel + ".local.signed.json")
        base.run(base.DOTNET, base.PUBLISHER, "sign", unsigned, base.KEYS / "pawpatch-signing-private.pem", "pawpatch-prod-2026", signed)
        base.run(base.DOTNET, base.PUBLISHER, "verify", signed, base.KEYS / "pawpatch-signing-public.pem")
    (OUT / "roaming-x2-audit.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps([{"module": e["module"], "files": e["files"], "activeSources": len(e["activeSources"])} for e in evidence]))


if __name__ == "__main__":
    main()
