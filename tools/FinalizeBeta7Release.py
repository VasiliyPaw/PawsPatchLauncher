"""Prepare final signed launcher/game feeds and portable assets; never uploads or advertises."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parents[1]
STAGE = REPO / "release_workspace_beta7_v2"
OUT = STAGE / "publication"
DOTNET = Path(r"C:\Users\Paw\Documents\Codex\Kohan-Reborn\.tools\dotnet\dotnet.exe")
PUBLISHER = REPO / "tools/PawsPatchPublisher/bin/Release/net8.0-windows/PawsPatchPublisher.dll"
KEYS = REPO / ".local/signing"
ENTRY = {
    "category": "launcher", "version": "0.5.7", "publishedAt": "2026-09-07",
    "title": {"ru": "Автообновляемая справка и цвета с пропуском рассинхрона",
              "en": "Automatic guide updates and colors with desync bypass"},
    "body": {
        "ru": "«О патче» загружается из подписанных данных выбранного выпуска, обновляется без нового EXE и сохраняется для работы без интернета. Справка дополнена случайной картой, временем суток и новыми правилами сетевых цветов. В бете 7 расширенные цвета можно сочетать с пропуском рассинхрона; настройка сохраняется и передаётся кодом друга. У старых бет без соответствующего файла запуска это сочетание недоступно.",
        "en": "About the patch comes from the selected release's signed feed, updates without a new EXE and remains available offline. The guide now covers random map type, time of day and multiplayer color behavior. Beta 7 allows extended colors with desync bypass, including saved settings and friend codes. Older Betas without the combined helper retain their compatibility restriction."
    }
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def run(*args):
    result = subprocess.run(list(map(str, args)), cwd=REPO, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    print((result.stdout + result.stderr).decode("utf-8", errors="replace"), end="")
    result.check_returncode()

def read_feed(path):
    run(DOTNET, PUBLISHER, "verify", path, KEYS / "pawpatch-signing-public.pem")
    return json.loads(base64.b64decode(json.loads(path.read_bytes())["payload"]))

def main():
    assert not OUT.exists(), "Preserve previous prepared publication."
    OUT.mkdir(parents=True)
    assets = OUT / "assets"; assets.mkdir()
    launcher = STAGE / "launcher/win-x64/PawsPatchLauncher.exe"
    shutil.copyfile(launcher, assets / launcher.name)
    with zipfile.ZipFile(assets / "PawsPatchLauncher-v0.5.7-win-x64.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.write(launcher, launcher.name)
        z.write(launcher.parent / "launcher.config.json", "launcher.config.json")
    preparation = json.loads((STAGE / "preparation.json").read_bytes())
    assert sha(REPO / "feed/stable.json") == preparation["stable_sha256"]
    assert sha(REPO / "feed/beta.json") == preparation["old_beta_sha256"]
    stable = read_feed(REPO / "feed/stable.json")
    beta = read_feed(STAGE / "feed/beta.production.signed.json")
    guide = json.loads((REPO / "feed/patch-guide.json").read_bytes())
    history = json.loads((STAGE / "changelog.history.json").read_bytes())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for name, feed in (("stable", stable), ("beta", beta)):
        original_packages = copy.deepcopy(feed["packages"])
        feed["launcher"] = {"version": "0.5.7", "size": launcher.stat().st_size, "sha256": sha(launcher),
            "urls": ["https://github.com/VasiliyPaw/PawsPatchLauncher/releases/download/v0.5.7/PawsPatchLauncher.exe"]}
        feed["patchGuide"] = copy.deepcopy(guide)
        if name == "stable":
            feed["patchGuide"]["version"] = "1.3.72-data.8-r2 / 2026-09-07"
        feed["publishedAt"] = now
        assert not any(e["category"] == "launcher" and e["version"] == "0.5.7" for e in history[name])
        history[name] = [ENTRY] + history[name]
        feed["changelog"] = history[name]
        feed["newsTitle"], feed["newsBody"] = history[name][0]["title"], history[name][0]["body"]
        assert feed["packages"] == original_packages
        payload = OUT / (name + ".payload.json")
        signed = OUT / (name + ".signed.json")
        payload.write_text(json.dumps(feed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run(DOTNET, PUBLISHER, "sign", payload, KEYS / "pawpatch-signing-private.pem", "pawpatch-prod-2026", signed)
        assert read_feed(signed) == feed
    (OUT / "changelog.history.json").write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert json.loads((OUT / "stable.payload.json").read_bytes())["packages"] == stable["packages"]
    (OUT / "assets.json").write_text(json.dumps({p.name: {"size": p.stat().st_size, "sha256": sha(p)}
        for p in assets.iterdir()}, indent=2) + "\n")
    print("FINAL FEEDS PREPARED: launcher 0.5.7, Beta 7, signed auto-guide; unchanged Release game packages; nothing uploaded.")

if __name__ == "__main__":
    main()
