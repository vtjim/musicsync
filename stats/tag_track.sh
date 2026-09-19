#!/bin/bash
# Usage: tag_track.sh <persistentID> <name> <artist> <album> <track#> <year>
# One track per call, retried: Music rejects rapid edits while it relocates a re-tagged file
# (-50 / -54 look like bad values but succeed moments later). See CLAUDE.md.
pid="$1"; name="$2"; artist="$3"; album="$4"; num="$5"; year="$6"
for attempt in 1 2 3 4; do
  if osascript -e 'on run argv' \
    -e 'tell application "Music"' \
    -e 'set t to (first track of playlist "Library" whose persistent ID is (item 1 of argv))' \
    -e 'set name of t to (item 2 of argv)' \
    -e 'set artist of t to (item 3 of argv)' \
    -e 'set album artist of t to (item 3 of argv)' \
    -e 'set album of t to (item 4 of argv)' \
    -e 'set track number of t to ((item 5 of argv) as integer)' \
    -e 'set year of t to ((item 6 of argv) as integer)' \
    -e 'end tell' -e 'end run' "$pid" "$name" "$artist" "$album" "$num" "$year" >/dev/null 2>&1; then
    echo "  tagged $num: $name"; sleep 3; exit 0
  fi
  sleep 5
done
echo "  TAG FAILED $num: $name"; exit 1
