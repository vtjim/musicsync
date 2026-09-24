#!/usr/bin/env python3
"""Mirror one tagged show to the USB master: FLAC -> tagged 320k MP3 -> fix_tags_and_organize.py.

Usage: usb_add.py <show_folder> <spec.json>   (same spec.json as tag_show.py)
"""
import glob, json, os, shutil, subprocess, sys, tempfile
folder, spec = sys.argv[1], json.load(open(sys.argv[2]))
flacs = sorted(glob.glob(os.path.join(folder, "*.flac")))
assert len(flacs) == len(spec["titles"]), f"{len(flacs)} flac vs {len(spec['titles'])} titles"
scratch = tempfile.mkdtemp(prefix="usbadd_")
n = len(flacs)
for i, f in enumerate(flacs, 1):
    out = os.path.join(scratch, f"{i:02d}.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f, "-vn", "-ab", "320k", "-map_metadata", "-1",
        "-metadata", f"title={spec['titles'][i-1]}", "-metadata", f"artist={spec['artist']}",
        "-metadata", f"album_artist={spec['artist']}", "-metadata", f"album={spec['album']}",
        "-metadata", f"track={i}/{n}", "-metadata", f"date={spec['year']}",
        "-id3v2_version", "3", "-write_id3v1", "1", out], check=True)
    print(f"  mp3 {i}/{n}", flush=True)
subprocess.run(["python3", os.path.expanduser("~/.claude/skills/usb-music-prep/scripts/fix_tags_and_organize.py"),
    scratch, os.path.expanduser("~/Music/usb-prep-output")], check=True)
shutil.rmtree(scratch)
