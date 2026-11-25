import hashlib
import io
import json
import pathlib
import re
import urllib.request
import zipfile

ARCHIVES = "https://github.com/penny323mo/valley-crown/releases/download/"
REQUIRED_WEB_FILES = {"index.html", "index.js", "index.pck", "index.wasm"}
BUILD_ID = re.compile(r"vc-[0-9a-f]{12}")
HASH = re.compile(r"[0-9a-f]{64}")


def validate(config):
    build = config["build"]
    if not BUILD_ID.fullmatch(build):
        raise ValueError(f"Invalid build ID: {build}")
    url = config["artifact_url"]
    if not url.startswith(ARCHIVES) or not HASH.fullmatch(config["zip_sha256"]):
        raise ValueError(f"Invalid archive pin for {build}")
    files = config["files_sha256"]
    if not REQUIRED_WEB_FILES <= files.keys():
        raise ValueError(f"Missing Web entry file for {build}")
    for name, digest in files.items():
        path = pathlib.PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or str(path) != name or name in {
            ".", "WEB_EXPORT_MANIFEST.json"
        } or "\\" in name or not HASH.fullmatch(digest):
            raise ValueError(f"Invalid file pin for {build}: {name}")


def manifest(config):
    return json.dumps(config, indent=2) + "\n"


def stage(config, builds, fetch):
    data = fetch(config["artifact_url"])
    if hashlib.sha256(data).hexdigest() != config["zip_sha256"]:
        raise ValueError(f"ZIP hash mismatch: {config['build']}")
    dest = builds / config["build"]
    dest.mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        for name, digest in config["files_sha256"].items():
            candidates = ["artifacts/clean-a/" + name, "notices/" + name]
            matches = [n for n in names if n in candidates]
            if len(matches) != 1:
                raise ValueError(f"Missing or duplicate archive member: {name}")
            contents = archive.read(matches[0])
            if hashlib.sha256(contents).hexdigest() != digest:
                raise ValueError(f"File hash mismatch: {config['build']}/{name}")
            path = dest / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents)
    (dest / "WEB_EXPORT_MANIFEST.json").write_text(manifest(config))


def download(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def publish(current, previous, root, fetch=download):
    for config in (current, previous):
        validate(config)
    if current["build"] == previous["build"]:
        raise ValueError("Current and previous build must differ")
    root.mkdir()
    for config in (current, previous):
        stage(config, root / "builds", fetch)
    (root / ".nojekyll").touch()
    (root / "release.json").write_text(manifest(current))
    build = current["build"]
    for sub, target in [("", f"builds/{build}/"), ("play", f"../builds/{build}/")]:
        path = root / sub
        path.mkdir(exist_ok=True)
        (path / "index.html").write_text(
            '<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url='
            + target + '"><title>Valley Crown</title><a href="' + target
            + '">Play Valley Crown ' + build + '</a>'
        )
    size = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
    if size >= 900_000_000:
        raise ValueError("Pages payload exceeds the size limit")
    print(f"Verified published build {build}, retained {previous['build']}; bytes {size}")


if __name__ == "__main__":
    # For each new release, atomically move the old release.json to
    # previous-release.json before replacing release.json. Keep both pins exact.
    publish(
        json.loads(pathlib.Path("release.json").read_text()),
        json.loads(pathlib.Path("previous-release.json").read_text()),
        pathlib.Path("_site"),
    )
