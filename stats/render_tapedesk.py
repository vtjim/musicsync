#!/usr/bin/env python3
"""Render the Tape Desk page: stats dashboard (from data.json) on top of the preserved session log.

Usage: render_tapedesk.py <base_page.html> <out.html> [--sets N] [--vtmusic-tracks N]
base_page.html is the currently published Tape Desk (saved via Artifact read with path=index.html); everything from
its first "section-label" onward is kept as the session log, so history is never retyped.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
base, out = sys.argv[1], sys.argv[2]
args = sys.argv[3:]
sets = int(args[args.index("--sets") + 1]) if "--sets" in args else 0
DATA = json.load(open(os.path.join(HERE, "data.json")))
DATA["sets"] = sets

page = open(base).read()
# strip the platform wrapper: keep from <title> to before </body>
page = page[page.index("<title>"):page.rindex("</body>")]

CSS = open(os.path.join(HERE, "tapedesk.css")).read()
DASH = open(os.path.join(HERE, "tapedesk_dash.html")).read()
JS = open(os.path.join(HERE, "tapedesk.js")).read()
LOG_NEW = open(os.path.join(HERE, "tapedesk_log_new.html")).read()

page = page.replace("</style>", CSS + "\n</style>", 1)

# header refresh stamp
page = re.sub(r'<strong id="refreshed-at">.*?</strong>', '<strong id="refreshed-at"></strong>', page, flags=re.S)

# swap watch bar + stats tiles for the dashboard
a = page.index('<div class="watch-bar">')
b = page.index('<p class="section-label">Today — five more pasted links</p>')
page = page[:a] + DASH + "\n" + LOG_NEW + "\n  " + page[b:]

# relative day names in the preserved log are stale; pin them to real dates
for old, new in [
    ("Today — five more pasted links", "Sep 16 — five more pasted links"),
    ("Today — USB/Music reconciliation", "Sep 16 — USB/Music reconciliation"),
    ("Yesterday — Todd Snider", "Sep 15 — Todd Snider"),
    ("Yesterday — John Craigie (last 2 years)", "Sep 15 — John Craigie (last 2 years)"),
    ("Today — Jeezum Crow Music Festival, Jay Peak VT (2023–2025)", "Sep 15 — Jeezum Crow Music Festival, Jay Peak VT (2023–2025)"),
    ("Yesterday — one more pasted link", "Sep 14 — one more pasted link"),
]:
    page = page.replace(old, new)

# footer: refresh the stale USB-drive sentence
page = re.sub(r"Separately, <code>~/Music/usb-prep-output</code>.*?manual click — Terminal doesn't have permission to drive Music's menus on this machine\.",
              "Separately, <code>~/Music/usb-prep-output</code> holds a 320kbps-MP3 mirror of the catalog for the car's USB stick (\"VTMUSIC\", FAT32) and is copied to the \"TAPEBACKUP\" drive as a safety backup. "
              "The iCloud upload (File → Library → Update Cloud Library) is now triggered automatically after each batch. "
              "Numbers above come from <code>stats/build_stats.py</code>; rerun it and <code>stats/render_tapedesk.py</code> to refresh this page.",
              page, flags=re.S)

page += "\n<script>\nconst DATA = " + json.dumps(DATA) + ";\n" + JS + "\n</script>\n"
open(out, "w").write(page)
print("wrote", out, len(page), "bytes")
