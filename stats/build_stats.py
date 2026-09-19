#!/usr/bin/env python3
"""Collect library/disk stats for the Tape Desk page and render it.

Usage: build_stats.py            # gather, append a snapshot, write data.json + tapedesk.html
Needs: Music.app running (JXA dump), mutagen (pip install mutagen), the usb-prep-output master.

Definitions the page relies on:
  - "In Music" = tracks Music says were added on/after 2026-08-25 (taper project start), from music_dump.js.
    Includes a few non-taper adds; treat as "the taper library" within a small margin.
  - "On disk" = the subset with a local file (location present). The rest is iCloud-only (Optimize Storage).
  - "USB master" = ~/Music/usb-prep-output, the 320 kbps MP3 mirror (real files, real durations).
"""
import collections, datetime, glob, json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.expanduser("~/Music/usb-prep-output")
PROJECT = os.path.expanduser("~/dev/musicsync")
SNAP = os.path.join(HERE, "snapshots.jsonl")
GB = 1e9


def music_rows():
    out = subprocess.check_output(["osascript", "-l", "JavaScript", os.path.join(HERE, "music_dump.js")], text=True)
    d = json.loads(out)
    return d["total_library_tracks"], d["rows"]


def master_stats():
    from mutagen.mp3 import MP3
    n = secs = size = 0
    albums = set()
    for p in glob.glob(MASTER + "/*/*/*.mp3"):
        try:
            secs += MP3(p).info.length
        except Exception:
            pass
        size += os.path.getsize(p)
        n += 1
        albums.add(tuple(p[len(MASTER) + 1:].split("/")[:2]))
    return dict(tracks=n, hours=secs / 3600, gb=size / GB, albums=len(albums))


def du(path):
    try:
        return int(subprocess.check_output(["du", "-sk", path], text=True, stderr=subprocess.DEVNULL).split()[0]) * 1024
    except Exception:
        return 0


def main():
    total_lib, rows = music_rows()
    local = [r for r in rows if r[6]]
    by_day = collections.OrderedDict()
    for r in sorted(rows, key=lambda r: r[0]):
        b = by_day.setdefault(r[0], dict(tracks=0, secs=0, bytes=0))
        b["tracks"] += 1; b["secs"] += r[1]; b["bytes"] += r[2]
    cum = 0; timeline = []
    for day, b in by_day.items():
        cum += b["secs"]
        timeline.append(dict(day=day, tracks=b["tracks"], hours=round(b["secs"] / 3600, 2), cum_hours=round(cum / 3600, 1)))

    du_disk = shutil.disk_usage("/System/Volumes/Data")
    master = master_stats()
    lossless = [r for r in rows if "Lossless" in r[5]]
    cloud = collections.Counter(r[7] for r in rows)

    data = dict(
        generated=datetime.datetime.now().astimezone().isoformat(timespec="minutes"),
        disk=dict(total_gb=du_disk.total / GB, used_gb=du_disk.used / GB, free_gb=du_disk.free / GB),
        music=dict(
            tracks=len(rows), hours=sum(r[1] for r in rows) / 3600,
            total_gb=sum(r[2] for r in rows) / GB,
            local_tracks=len(local), local_gb=sum(r[2] for r in local) / GB,
            cloud_only_tracks=len(rows) - len(local), cloud_only_gb=sum(r[2] for r in rows if not r[6]) / GB,
            lossless_tracks=len(lossless), whole_library_tracks=total_lib,
            cloud_status=dict(cloud),
        ),
        master=master,
        scratch_gb=du(PROJECT) / GB,
        backup=None,
        timeline=timeline,
    )
    for vol, key in (("/Volumes/TAPEBACKUP", "tapebackup"), ("/Volumes/VTMUSIC", "vtmusic")):
        if os.path.isdir(vol):
            u = shutil.disk_usage(vol)
            data.setdefault("drives", {})[key] = dict(total_gb=u.total / GB, used_gb=u.used / GB, free_gb=u.free / GB)

    with open(SNAP, "a") as f:
        f.write(json.dumps(dict(ts=data["generated"], free_gb=round(data["disk"]["free_gb"], 1),
                                used_gb=round(data["disk"]["used_gb"], 1), music_tracks=data["music"]["tracks"],
                                music_local_gb=round(data["music"]["local_gb"], 1), master_tracks=master["tracks"],
                                master_gb=round(master["gb"], 1), hours=round(data["music"]["hours"], 1))) + "\n")
    data["snapshots"] = [json.loads(l) for l in open(SNAP)]
    json.dump(data, open(os.path.join(HERE, "data.json"), "w"), indent=1)
    print(f"music {data['music']['tracks']} trk / {data['music']['hours']:.1f} h; on disk {data['music']['local_gb']:.1f} GB; "
          f"master {master['tracks']} trk; free {data['disk']['free_gb']:.1f} GB")


if __name__ == "__main__":
    main()
