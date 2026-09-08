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
parser.add_argument("--tag", help="Explicit tag for a separately versioned package release")
parser.add_argument("--name", help="Release display name")
parser.add_argument("--prerelease", action="store_true")
parser.add_argument("--attach-only", action="store_true", help="Only add immutable assets to an already published, commit-verified release")
args = parser.parse_args()
repo = "VasiliyPaw/PawsPatchLauncher"
tag = args.tag or "v" + args.version
if args.tag and (tag.startswith("v") or not args.prerelease and tag != "patch-" + args.version):
    raise RuntimeError("Package releases require patch-<version>, or a prerelease tag outside the launcher v* workflow")
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
    if args.attach_only:
        raise RuntimeError("Attach-only mode requires an existing public release") from None
    # A previous interrupted invocation can have left an unpublished draft.
    release = next((r for r in request(api + "/releases?per_page=100") if r["tag_name"] == tag), None)
    if release is None:
        release = request(api + "/releases", "POST", {
            "tag_name": tag, "target_commitish": args.commit,
            "name": args.name or "Paw's Patch Launcher " + tag,
            "body": pathlib.Path(args.notes).read_text(encoding="utf-8"),
            "draft": True, "prerelease": args.prerelease,
            **({"make_latest": "false"} if args.prerelease or args.tag else {}),
        })
if args.attach_only or release["target_commitish"] != args.commit:
    # CI-created releases can store the branch name as target_commitish. Verify
    # the immutable tag's actual commit instead of trusting a moving branch.
    tagged = request(api + "/git/ref/tags/" + urllib.parse.quote(tag))["object"]
    for _ in range(4):
        if tagged["type"] != "tag":
            break
        tagged = request(api + "/git/tags/" + tagged["sha"])["object"]
    if tagged["type"] != "commit" or tagged["sha"] != args.commit:
        raise RuntimeError("Existing release tag targets a different source revision")
if args.attach_only and release["draft"]:
    raise RuntimeError("Attach-only mode refuses unpublished drafts")
if release["prerelease"] != args.prerelease:
    raise RuntimeError("Existing release has a different prerelease status")
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
    release = request(api + "/releases/" + str(release["id"]), "PATCH", {
        "draft": False, "make_latest": "false" if args.prerelease or args.tag else "true"})
print("PUBLISHED", release["html_url"], flush=True)
