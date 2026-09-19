#!/usr/bin/env python3
"""
getshow.py <identifier> <destdir>

Downloads every .flac plus the best cover image for an archive.org item,
verifying each file's size against the manifest and retrying on mismatch.
Does everything in Python so filenames with spaces, ">", ":", parentheses,
apostrophes etc. are never passed through a shell word-splitting step.

Supersedes an earlier bash version (getshow.sh) that piped "name size"
pairs through `read -r name size` — any filename containing a space
(common on well-tagged taper releases, e.g. "2-03 Wharf Rat ->.flac")
got split across the two variables and silently corrupted every
download. Always use this version.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

def fetch_json(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())

def download(url, dest, expected_size, tries=4, timeout=900):
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "musicsync/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as f:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            got = os.path.getsize(dest)
            if got == expected_size:
                return True, got
            print(f"  retry {attempt}: size mismatch got={got} want={expected_size}")
        except Exception as e:
            print(f"  retry {attempt}: error {e}")
        time.sleep(4)
    return False, os.path.getsize(dest) if os.path.exists(dest) else 0

def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    identifier, destdir = sys.argv[1], sys.argv[2]
    os.makedirs(destdir, exist_ok=True)

    meta = fetch_json(f"https://archive.org/metadata/{identifier}")
    files = meta.get("files", [])

    flacs = [f for f in files if f.get("name", "").lower().endswith(".flac")]
    imgs = [f for f in files if f.get("format") == "JPEG"]

    if imgs:
        cover = max(imgs, key=lambda f: int(f.get("size") or 0))
        url = f"https://archive.org/download/{identifier}/" + urllib.parse.quote(cover["name"])
        ok, got = download(url, os.path.join(destdir, "cover.jpg"), int(cover["size"]))
        print(f"cover: {'ok' if ok else 'FAILED'} ({got} bytes)")

    bad = []
    for f in sorted(flacs, key=lambda x: x["name"]):
        name = f["name"]
        size = int(f["size"])
        dest = os.path.join(destdir, os.path.basename(name))  # items may keep files in a subfolder; flatten locally
        url = f"https://archive.org/download/{identifier}/" + urllib.parse.quote(name)
        print(f"downloading: {name}")
        ok, got = download(url, dest, size)
        if ok:
            print(f"  ok: {name} ({got} bytes)")
        else:
            print(f"  FAILED: {name} (got {got}, want {size})")
            bad.append(name)

    n_ok = len(flacs) - len(bad)
    print(f"DOWNLOAD_COMPLETE {n_ok} flacs" + (f" ({len(bad)} FAILED)" if bad else ""))

if __name__ == "__main__":
    main()
