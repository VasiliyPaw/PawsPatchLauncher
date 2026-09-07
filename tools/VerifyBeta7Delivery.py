"""Anonymous readback of advertised feeds/releases, verified using the configured public key."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request
from datetime import datetime, timezone

repo = Path(__file__).resolve().parents[1]
stage = repo / "release_workspace_beta7_v2/publication"
out = stage / "online-readback"
out.mkdir(exist_ok=True)
dotnet = Path(r"C:\Users\Paw\Documents\Codex\Kohan-Reborn\.tools\dotnet\dotnet.exe")
publisher = repo / "tools/PawsPatchPublisher/bin/Release/net8.0-windows/PawsPatchPublisher.dll"
public = repo / ".local/signing/pawpatch-signing-public.pem"

def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "PawsPatchDeliveryAudit/0.5.7", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()

def verify_envelope(path):
    result = subprocess.run([str(dotnet), str(publisher), "verify", str(path), str(public)],
                            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    print((result.stdout + result.stderr).decode("utf-8", errors="replace"), end="")
    result.check_returncode()
    return json.loads(base64.b64decode(json.loads(path.read_bytes())["payload"]))

results = []
for name in ("stable", "beta"):
    path = out / (name + ".json")
    path.write_bytes(fetch("https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/main/feed/" + name + ".json"))
    feed = verify_envelope(path)
    expected = verify_envelope(stage / (name + ".signed.json"))
    assert feed == expected, "Canonical feed has not reached expected version: " + name
    assert feed["launcher"]["version"] == "0.5.7" and len(feed["patchGuide"]["entries"]) == 16
    if name == "beta":
        assert feed["colorDesyncContinue"]
        assert next(p for p in feed["packages"] if p["id"] == "player-colors")["version"] == "0.1.0-beta.7"
        assert next(p for p in feed["packages"] if p["id"] == "common-ui")["version"] == "1.3.72-ui.2-beta.7"
    else:
        previous = verify_envelope(stage / "previous-stable.signed.json")
        assert feed["game"] == previous["game"] and feed["packages"] == previous["packages"]
    results.append({"channel": name, "launcher": feed["launcher"]["version"], "guideEntries": len(feed["patchGuide"]["entries"]),
                    "signed": True, "canonicalMatchesPrepared": True})
history = out / "previous-beta.json"
history.write_bytes(fetch("https://raw.githubusercontent.com/VasiliyPaw/PawsPatchLauncher/main/feed/history/beta-before-beta7.json"))
assert verify_envelope(history) == verify_envelope(repo / "feed/history/beta-before-beta7.json")
api = "https://api.github.com/repos/VasiliyPaw/PawsPatchLauncher/releases/"
for tag, files in (
    ("v0.5.7", list((stage / "assets").iterdir())),
    ("beta.7", list((repo / "release_workspace_beta7_v2/packages").iterdir()))
):
    release = json.loads(fetch(api + "tags/" + tag))
    assert not release["draft"] and release["prerelease"] == (tag == "beta.7")
    for path in files:
        item = next(a for a in release["assets"] if a["name"] == path.name)
        assert item["size"] == path.stat().st_size and item["digest"] == "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        if path.suffix == ".exe":
            data = fetch(item["browser_download_url"])
            assert len(data) == item["size"] and hashlib.sha256(data).hexdigest() == item["digest"].split(":")[1]
            print("DOWNLOADED LAUNCHER HASH PASS")
    print("RELEASE ASSETS PASS", tag)
latest = json.loads(fetch(api + "latest"))
assert latest["tag_name"] == "v0.5.7", "Latest launcher changed unexpectedly"
(out / "results.json").write_text(json.dumps({"verifiedUtc": datetime.now(timezone.utc).isoformat(),
    "feeds": results, "releaseHistoryVerified": True, "latest": latest["tag_name"],
    "releasePackagesUnchanged": True}, indent=2) + "\n")
print("ONLINE DELIVERY PASS: signed canonical feeds, 16-entry guides, latest launcher, all new asset metadata, launcher download and unchanged Release game packages")
