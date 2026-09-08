---
name: taper-import
description: Import a live taper recording into Apple Music - download FLACs from an archive.org URL/identifier (or extract a zip from ~/Downloads), convert to ALAC via XLD, tag from the real setlist, embed artwork, import, and clean up. Use when Jim pastes an archive.org link, names a show or festival to grab, or drops a taper zip in Downloads.
---

# Importing a taper show

Turns a live recording into correctly-tagged ALAC in Apple Music. Read
`CLAUDE.md` in this folder too — it carries the library inventory and the
hard-won gotchas this skill assumes.

## 1. Work out what you were given

- **An archive.org URL or identifier** → go to step 2.
- **A festival, band, or date** ("grab the whole Adirondack fest") →
  find the identifiers first:
  ```
  curl -s "https://archive.org/advancedsearch.php?q=collection%3Aetree+AND+\
  title%3A%28<TERM>%29&fl%5B%5D=identifier&fl%5B%5D=title&fl%5B%5D=date\
  &fl%5B%5D=addeddate&sort%5B%5D=addeddate+desc&rows=25&output=json"
  ```
  Sort by `addeddate desc` so newly-posted sets surface even when their
  performance date is one you already have. Show Jim the list and
  confirm scope before pulling several gigabytes.
- **A zip in `~/Downloads`** → confirm it finished (size stable across a
  couple of seconds, no `.crdownload` sibling), extract into
  `~/dev/musicsync/<name-with-dots-as-underscores>/`, then skip to step 4.

## 2. Read the real metadata

```
curl -s "https://archive.org/metadata/<identifier>" -o /tmp/<id>_meta.json
```

Use this raw JSON as the source of truth. **Don't** rely on `WebFetch` of
the details page — it summarizes through a small model and has reported a
flatly wrong item size before.

Pull from it:
- `metadata.title`, `creator`, `date`, `venue`, `coverage`, `lineage`, `taper`
- every file where the name ends `.flac` and `source == "original"` —
  take the **exact `name`**, since the identifier prefix often differs
  from the filenames (`hsss2026-09-04` holds `hssb2026-09-04*` files)
- the per-file `title` and `track` fields
- a photo for artwork (a real `*.jpg` from the item beats `__ia_thumb.jpg`)

**Where the true song titles live:** matrix/soundboard releases usually
carry correct per-file `title` tags that XLD passes straight through, so
no retagging is needed. Taper AUD releases are inconsistent — often only
track 1 has a real title and the rest are `Track 2`, `Track 3`… In that
case parse the numbered setlist out of `metadata.description` (it's HTML,
like `<div>01. Introduction</div>`). Check with
`ffprobe -show_entries format_tags` before assuming a full retag is needed.

Watch for mojibake in titles (`â€™` where a curly apostrophe belongs) and
fix it when you tag.

## 3. Download

Into `~/dev/musicsync/<identifier-with-dots-as-underscores>/`, from
`https://archive.org/download/<identifier>/<filename>`. Print a line per
file as it lands — Jim wants to watch it happen, not just get a summary.

Use `getshow.py` in this skill folder rather than writing a fresh
downloader each time:

```
python3 .claude/skills/taper-import/getshow.py <identifier> <destdir>
```

It fetches the real metadata JSON, downloads every `.flac` plus the
largest cover image, verifies each file's size against the manifest, and
retries mismatches. It replaced an earlier bash version that piped
`"name size"` through `read -r name size` — any filename containing a
space (common on well-titled taper releases, e.g.
`2-03 Wharf Rat ->.flac`) split across the two variables and silently
corrupted the whole batch. Do the download in Python, never in bash with
`read`, whenever filenames might contain spaces.

For anything multi-gigabyte, hold the Mac awake first:
`nohup caffeinate -dims > /dev/null 2>&1 &`

## 4. Convert and import

```
/Users/jim/Downloads/flac-pipeline.sh <that-folder>
```

XLD FLAC→ALAC, then imports each `.m4a` into Apple Music. It's resumable
(skips any `.flac` whose `.m4a` already exists) and prints per-track
progress. Large 24/96 sets take a few minutes per track — run it in the
background and report progress rather than blocking silently.

## 5. Tag

If the embedded tags already came through correctly, just spot-check and
move on. Otherwise fix **both** the file on disk and Music's own copy —
Music copies media into its managed folder on import, so editing the
source afterwards does not update the library.

On disk, via ffmpeg (re-mux, no re-encode), **one file at a time with an
explicit index** — an array loop silently shifted every title by one the
first time this was tried:

```
ffmpeg -i in.m4a -i cover.jpg -map 0:a -map 1:v -c copy \
  -disposition:v:0 attached_pic \
  -metadata title="..." -metadata artist="..." -metadata album="..." \
  -metadata track="N/total" -metadata date="YYYY-MM-DD" \
  -metadata comment="<lineage / taper / venue>" out.m4a
```

Verify each with `ffprobe` right after writing it.

In Music: resolve `location contains <filename>` to a `persistent ID`
**once**, then make every edit addressed by that ID. Never batch-loop
location-based edits — "Keep Music Media folder organized" renames files
the instant tags change, and a loop that re-derives `location` races its
own side effects. That corrupted a 5-track batch once: three tracks lost
their album and landed in "Unknown Album", one lost its artist entirely.

Two more traps: don't name a flag variable `matched` (collides with an
AppleScript term, throws `Can't set «constant eClSkMat»`), and use
`whose name contains` rather than `whose name is` for titles holding `>`
— exact match fails on them even when the stored tag is correct.

## 6. Clean up and report

- Delete the source zip from `~/Downloads` once import and tagging
  succeed. Direct archive.org pulls have no zip — nothing to delete.
- Keep the FLACs and `.m4a` in the show folder; that's the local archive.
- Republish the Tape Desk artifact (same URL, read it back first, keep
  the design): https://claude.ai/code/artifact/d515b1da-20e9-424d-8f4f-0cbb74a6c498
- Add the show to the inventory table in `CLAUDE.md`.
- Remind Jim about Music → File → Library → Update Cloud Library — the
  upload is a manual at-the-Mac step and cannot be triggered remotely.
  See CLAUDE.md for why, so it isn't re-investigated each time.
