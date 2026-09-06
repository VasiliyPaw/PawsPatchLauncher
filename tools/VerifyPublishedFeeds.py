"""Validate every published asset before advertising a release. Uses anonymous HTTPS."""
import argparse
import base64
import concurrent.futures
import hashlib
import json
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("feeds", nargs="+")
parser.add_argument("--skip-launcher", action="store_true")
parser.add_argument("--workers", type=int, choices=range(1, 5), default=4, help="Use 1 to keep publication checks sequential")
args = parser.parse_args()
assets = {}
for path in args.feeds:
    if path.startswith("https://"):
        data = urllib.request.urlopen(path, timeout=30).read()
    else:
        with open(path, "rb") as stream:
            data = stream.read()
    envelope = json.loads(data)
    manifest = json.loads(base64.b64decode(envelope["payload"]))
    releases = list(manifest["packages"])
    if not args.skip_launcher:
        releases.append(dict(manifest["launcher"], id="launcher"))
    for package in releases:
        for url in package["urls"]:
            assets[url] = package

def verify(item):
    url, package = item
    digest = hashlib.sha256()
    size = 0
    request = urllib.request.Request(url, headers={"User-Agent": "PawsPatchReleaseAudit/0.5", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(request, timeout=60) as response:
        while block := response.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    if size != package["size"] or digest.hexdigest().upper() != package["sha256"].upper():
        raise RuntimeError("Published bytes do not match signed metadata: " + url)
    return f"PASS {package['id']} {package['version']} {size} bytes"

with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
    for result in pool.map(verify, assets.items()):
        print(result, flush=True)
print(f"PUBLICATION PASS {len(assets)} unique assets")
