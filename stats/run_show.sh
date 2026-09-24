#!/bin/bash
# run_show.sh <identifier> <spec.json> : download -> convert/import -> tag -> verify x2 -> USB master -> delete local.
set -e
cd ~/dev/musicsync
id=$1; spec=$2; d=$(echo "$id" | tr . _)
python3 .claude/skills/taper-import/getshow.py "$id" "$d" | grep -E "COMPLETE|FAIL|mismatch" || true
~/.claude/skills/music-icloud-sync/flac-pipeline.sh "$d" | grep -E "flac found|FAIL|failed"
python3 stats/tag_show.py "$d" "$spec" | tail -2
art=$(python3 -c "import json;print(json.load(open('$spec'))['artist'])"); alb=$(python3 -c "import json;print(json.load(open('$spec'))['album'])"); n=$(python3 -c "import json;print(len(json.load(open('$spec'))['titles']))")
cnt(){ osascript -e "tell application \"Music\" to count (every track of playlist \"Library\" whose album is \"$alb\" and artist is \"$art\")"; }
c1=$(cnt); sleep 45; c2=$(cnt); echo "music count: $c1 then $c2 (expect $n)"
[ "$c1" = "$n" ] && [ "$c2" = "$n" ] || { echo "VERIFY FAILED - keeping local files"; exit 1; }
python3 stats/usb_add.py "$d" "$spec" | tail -1
u=$(find ~/Music/usb-prep-output/"$art"/"$alb" -name '*.mp3' | wc -l | tr -d " "); echo "usb count: $u (expect $n)"
[ "$u" = "$n" ] || { echo "USB VERIFY FAILED - keeping local files"; exit 1; }
rm -rf "$d"; echo "SHOW DONE: $art / $alb"
