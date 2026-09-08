"""Read release/CI state using the repository's configured Git credential helper.

Print only release metadata and workflow status, never credentials or raw logs.
"""
import argparse
import json
import subprocess
import urllib.error
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("commit")
parser.add_argument("--tag", default="v0.6.0")
args = parser.parse_args()
repo = "VasiliyPaw/PawsPatchLauncher"
credential = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                            text=True, capture_output=True, check=True)
fields = dict(line.split("=", 1) for line in credential.stdout.splitlines() if "=" in line)
token = fields.get("password")
if not token:
    raise RuntimeError("No configured GitHub credential")

def get(path):
    request = urllib.request.Request("https://api.github.com/repos/" + repo + path,
        headers={"Authorization": "Bearer " + token, "User-Agent": "PawsPatchReleaseStatus",
                 "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)

runs = get("/actions/runs?head_sha=" + args.commit + "&per_page=20")["workflow_runs"]
print(json.dumps({"workflows": [{key: run.get(key) for key in
    ("id", "name", "event", "status", "conclusion", "head_sha", "html_url")} for run in runs]}, ensure_ascii=False), flush=True)
try:
    release = get("/releases/tags/" + args.tag)
except urllib.error.HTTPError as error:
    if error.code != 404:
        raise
    print(json.dumps({"release": None}), flush=True)
else:
    print(json.dumps({"release": {key: release.get(key) for key in
        ("id", "tag_name", "target_commitish", "draft", "prerelease", "html_url")},
        "assets": [{key: asset.get(key) for key in ("name", "size", "digest", "browser_download_url")}
                   for asset in release["assets"]]}, ensure_ascii=False), flush=True)
