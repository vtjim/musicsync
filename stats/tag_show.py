#!/usr/bin/env python3
"""Tag one imported show in Music by matching source .m4a durations to Music tracks (resolve-once, edit-by-ID).

Usage: tag_show.py <show_folder> <spec.json>
spec.json: {"artist":..., "album":..., "year":2026, "titles":["Intro", ...]}  (titles[i] = track i+1)
Matching is by duration (unique per track even when titles collide); aborts on any ambiguity.
"""
import json, subprocess, sys, os, glob, time
folder, spec_path = sys.argv[1], sys.argv[2]
spec = json.load(open(spec_path))
here = os.path.dirname(os.path.abspath(__file__))
recent = json.loads(subprocess.check_output(["osascript", "-l", "JavaScript", os.path.join(here, "resolve_ids.js"), "3"]))
files = sorted(glob.glob(os.path.join(folder, "*.m4a")))
assert len(files) == len(spec["titles"]), f"{len(files)} m4a vs {len(spec['titles'])} titles"
used = set(); plan = []
for i, f in enumerate(files):
    d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]))
    cands = [r for r in recent if abs(r["dur"] - d) < 0.6 and r["pid"] not in used]
    if len(cands) > 1:  # break duration ties with the title Music imported from the file's own tag
        t = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags=title", "-of", "csv=p=0", f],
                           capture_output=True, text=True).stdout.strip()
        cands = [c for c in cands if c["name"].strip() == t.strip()] or cands
    if len(cands) != 1:
        sys.exit(f"AMBIGUOUS/NO MATCH track {i+1} ({os.path.basename(f)}, {d:.1f}s): {len(cands)} candidates {[c['name'] for c in cands]}")
    used.add(cands[0]["pid"]); plan.append((i + 1, cands[0]["pid"], spec["titles"][i]))
print(f"matched {len(plan)} tracks; tagging...")
fails = 0
for n, pid, title in plan:
    r = subprocess.run([os.path.join(here, "tag_track.sh"), pid, title, spec["artist"], spec["album"], str(n), str(spec["year"])])
    fails += r.returncode != 0
print("done, failures:", fails)
sys.exit(1 if fails else 0)
