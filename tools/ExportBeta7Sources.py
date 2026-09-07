"""Copy the generated, compiled patch sources/resources only; never game EXE or user logs."""
import json
import hashlib
import shutil
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
source = repo.parent / "beta_game_1372/release-beta7"
build = json.loads((source / "build.json").read_bytes())
destination = repo / "game/beta7"
destination.mkdir(parents=True, exist_ok=True)
for name in build["variants"]:
    assert hashlib.sha256((source / name["name"]).read_bytes()).hexdigest().upper() == name["sha256"]
for file in (source / "source").iterdir():
    if file.suffix not in (".cs", ".bin"):
        raise ValueError("Unexpected generated source: " + file.name)
    shutil.copyfile(file, destination / file.name)
shutil.copyfile(source / "paws_player_colors.ini", destination / "paws_player_colors.ini")
shutil.copyfile(repo.parent / "beta_game_1372/paws_patch_versions.ini", destination / "paws_patch_versions.ini")
(destination / "variants.json").write_text(json.dumps({v["name"]: v["defines"] for v in build["variants"]}, indent=2) + "\n")
print("EXPORTED patch-owned sources, resources and version metadata; no game EXE or diagnostics.")
