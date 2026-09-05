"""Publish immutable launcher assets, using the configured Git credential helper."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import urllib.error
import urllib.parse
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("version")
parser.add_argument("commit")
parser.add_argument("notes")
parser.add_argument("assets", nargs="+")
args = parser.parse_args()
repo = "VasiliyPaw/PawsPatchLauncher"
tag = "v" + args.version
credential = subprocess.run(
    ["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
    text=True, capture_output=True, check=True,
)
fields = dict(line.split("=", 1) for line in credential.stdout.splitlines() if "=" in line)
token = fields.get("password")
if not token:
    raise RuntimeError("No configured GitHub credential")

def request(url, method="GET", data=None, content_type="application/json"):
    headers = {"Authorization": "Bearer " + token, "User-Agent": "PawsPatchPublisher",
               "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
               "Content-Type": content_type}
    if isinstance(data, dict):
        data = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)

api = f"https://api.github.com/repos/{repo}"
try:
    release = request(api + "/releases/tags/" + urllib.parse.quote(tag))
except urllib.error.HTTPError as error:
    if error.code != 404:
        raise
    # A previous interrupted invocation can have left an unpublished draft.
    release = next((r for r in request(api + "/releases?per_page=100") if r["tag_name"] == tag), None)
    if release is None:
        release = request(api + "/releases", "POST", {
            "tag_name": tag, "target_commitish": args.commit,
            "name": "Paw's Patch Launcher " + tag,
            "body": pathlib.Path(args.notes).read_text(encoding="utf-8"),
            "draft": True, "prerelease": False,
        })
if release["target_commitish"] != args.commit:
    raise RuntimeError("Existing release targets a different source revision")
existing = {asset["name"]: asset for asset in release["assets"]}
for path in map(pathlib.Path, args.assets):
    data = path.read_bytes()
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    asset = existing.get(path.name)
    if asset:
        if asset.get("digest") != digest or asset["size"] != len(data):
            raise RuntimeError("Refusing to replace an existing immutable asset: " + path.name)
    else:
        url = release["upload_url"].split("{", 1)[0] + "?name=" + urllib.parse.quote(path.name)
        asset = request(url, "POST", data, "application/octet-stream")
        if asset["size"] != len(data) or asset.get("digest") != digest:
            raise RuntimeError("Uploaded asset digest mismatch")
    print("ASSET VERIFIED", path.name, len(data), digest, flush=True)
if release["draft"]:
    release = request(api + "/releases/" + str(release["id"]), "PATCH", {"draft": False})
print("PUBLISHED", release["html_url"], flush=True)
