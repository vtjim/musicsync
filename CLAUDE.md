# musicsync

## Archive storage: Synology NAS

Local disk fills up fast with 24-bit taper FLACs, so completed shows get
their masters moved off the Mac once imported and verified in Music:

- Share: `musicarchive` on the Synology DiskStation at `192.168.67.121`,
  mounted at `/Volumes/musicarchive` (mount survives most reboots; if it's
  missing, reconnect via Finder ⌘K → `smb://192.168.67.121` and enter the
  saved keychain credentials — don't script the mount with a password
  inline).
- Archived masters live under `/Volumes/musicarchive/taper-masters/<show>/`.
- **Discipline: copy, verify, then delete.** `rsync -a` the FLACs over,
  then verify every file's size (and spot-check MD5 on a sample) against
  the source before removing the local copy. This exists because a batch
  of Lara Cwass Band tracks was nearly lost once — see the "NEVER delete"
  gotcha further down. Never delete local FLACs based on the rsync exit
  code alone.
- The converted `.m4a` files are **not** archived anywhere separately —
  Apple Music already keeps its own permanent copy in its Media folder on
  import (see "Only FLAC masters live here now" below), so the local
  `.m4a` next to the FLAC is disposable once Music has it.

This folder holds live-show FLAC recordings (mostly Vermont Tapers Collective /
archive.org taper releases) on their way into Apple Music as ALAC. Each show
gets its own subfolder here, named after its source identifier with dots
replaced by underscores, e.g. `lcwass2026-06-05_VERMONT_TAPERS_COLLECTIVE`.

## End-to-end pipeline

1. **Get the source.** Either:
   - A zip lands in `~/Downloads` (check it's done downloading — stable file
     size across a couple seconds, no `.crdownload` sibling), or
   - Jim pastes an archive.org `/details/<identifier>` URL directly. In that
     case, skip the zip step entirely and pull files straight from the item
     (see "Working from an archive.org URL" below).

2. **Extract** into `~/dev/musicsync/<identifier-with-underscores>/`.

3. **Convert + import**: `~/Downloads/flac-pipeline.sh <that-folder>` —
   batch FLAC→ALAC via XLD, then imports each `.m4a` into Apple Music.
   Resumable (skips any `.flac` whose `.m4a` already exists). See the
   script's own header comments for the XLD hang-after-write quirk it
   works around.

4. **Fix tags from the real setlist** (the embedded FLAC tags from tapers
   are usually just "Track 2", "Track 3", etc. — not the actual song
   titles). Get the true track titles from the item's text description,
   not the per-file `title` field. See "Track titles live in the
   description" below.

5. **Delete the processed zip** from `~/Downloads` once conversion +
   import + tagging succeed. Don't delete a zip whose tracks you haven't
   verified are actually in the library — check by exact track-title
   lookup in Music (fast) rather than a full-library scan (slow, see
   gotcha below).

6. **Manual step Jim still has to do himself**: Music → File → Library →
   Update Cloud Library, to push into iCloud Music Library. Terminal has
   no accessibility permission to drive Music's menu bar
   (`osascript ... System Events` fails with `-1719`), so don't try to
   automate this — just remind him.

## Working from an archive.org URL directly

Given just a `/details/<identifier>` page, everything needed is available
without a browser or a zip:

- **Metadata (ground truth):** `curl -s "https://archive.org/metadata/<identifier>"`
  returns raw JSON — title, creator, date, venue, per-file sizes, and a
  `description` field. **Trust this over `WebFetch` on the same URL** —
  WebFetch summarizes through a small model and can invent plausible-looking
  but wrong details (it once reported a totally different file size for an
  item than what was actually on disk). The raw JSON's per-file `size` in
  bytes is a good sanity check against files you already have — if they
  match exactly, it's the same recording.
- **Track titles live in the description, not the per-file tags.** The
  JSON's `files[].title` field is frequently a generic placeholder
  ("Track 2", "Track 3", ...) even when `metadata.description` has the
  real numbered setlist as HTML (`<div>01. Introduction</div>...`). Parse
  the real titles out of `description`.
- **Files to fetch:** original `.flac` files (`files[].format == "Flac"`,
  `source == "original"`) and one image for artwork — the item's own
  photo credit file if present (e.g. a `facebook_*.jpg`) reads better
  than the generic `__ia_thumb.jpg`. Download via
  `https://archive.org/download/<identifier>/<filename>`.
- **Same show, multiple tapes:** a Vermont Tapers Collective AUD recording
  and a separate MTX/matrix release can both exist for the same date/venue
  as different archive.org identifiers with different, higher track counts
  or a 24-bit/96kHz source. Don't assume a new identifier for a familiar
  date is a duplicate — check the description (recording lineage, taper
  credit) and confirm with Jim before pulling in a second version of a
  show he already has.

## Fixing tags after the fact

If tags were already imported wrong (or generic), fix both the source file
and Music's own copy — editing the file on disk alone does **not** update
what's already in the library, since Music copies media into its own
managed folder on import.

- **Source `.m4a` file**, via ffmpeg (re-muxes, no re-encode):
  ```
  ffmpeg -i in.m4a -i cover.jpg -map 0:a -map 1:v -c copy \
    -disposition:v:0 attached_pic \
    -metadata title="..." -metadata artist="Lara Cwass Band" \
    -metadata album="..." -metadata track="N/total" \
    out.m4a
  ```
  Do this **one file at a time with an explicit index**, not a bash array
  looped by position — an off-by-one in the array/loop silently shifted
  every title down by one track and left track 1 blank the first time
  this was tried. Verify each file's tag with `ffprobe` right after
  writing it, before moving to the next.

- **Already-imported Music track: match by `location contains <filename>`
  exactly ONCE to capture `persistent ID`, then do every subsequent edit
  by that ID — never re-match by location inside a loop that also sets
  `album`/`name`.** Music's "Keep Music Media folder organized" moves and
  renames the underlying file live, the instant a track's name/album/artist
  changes. A loop that both edits several tracks AND re-derives `location`
  for the next one races its own side effects: one run of this actually
  corrupted a 5-track batch — one track landed correctly, three others got
  their `album`/`track number` silently dropped and were shoved into an
  "Unknown Album" folder, and one track's `artist` was wiped entirely
  (invisible to `whose artist is "..."` afterwards — it takes an
  unfiltered scan by `location contains "<folder>"` to even find it again).
  The fix pattern:
  ```applescript
  -- Pass 1: resolve name/location -> persistent ID once, before any edits.
  tell application "Music"
    repeat with t in (every track of playlist "Library")
      if (location of t as string) contains "laracwassband20260605t01.m4a" then
        log (persistent ID of t) -- capture this
      end if
    end repeat
  end tell
  ```
  ```applescript
  -- Pass 2: all edits addressed by persistent ID (fast — "whose" is
  -- native-indexed, unlike a manual repeat+compare).
  tell application "Music"
    set matches to (every track of playlist "Library" whose persistent ID is "01F387096BB576E1")
    repeat with t in matches
      set name of t to "Introduction"
      set track number of t to 1
      -- etc: artist, album, album artist, year, comment
    end repeat
  end tell
  ```
  Don't name a found-flag variable `matched` — it collides with an
  AppleScript reserved term and throws a cryptic
  `Can't set «constant eClSkMat» to false` error. Call it `foundIt` or
  similar instead.

- **Pace AppleScript tag writes — Music rejects rapid successive edits.**
  While Music is relocating a file it just re-tagged ("Keep Music Media
  folder organized"), further property writes fail with
  `Parameter error (-50)` or `File permission error (-54)`. These look
  like bad values or permissions problems and are neither: the exact same
  assignments succeed moments later. On the JRAD import a batch aborted
  after 2 of 14 tracks this way, and individual retries then reported
  spurious permission errors on tracks that were mid-move. Do one track
  per `osascript` call, retry up to 3-4 times with a ~5s sleep, and pause
  ~2-3s between tracks. Always re-query the album afterwards to confirm
  the real count rather than trusting the per-call return values.

- **NEVER delete a show's local files without first confirming its tracks
  are actually still in Music.** On 2026-09-07 all six Lara Cwass matrix
  tracks had vanished from the library between one day's verification and
  the next — every persistent ID resolving to nothing, no error, no trace.
  They were only recovered because the local files still existed and a
  pre-deletion check caught it. Music has now lost or scrambled tracks
  three separate ways (a batch scrambled mid-tagging, one track shedding
  artist/album after verifying clean, and six disappearing outright), so
  treat its library as unreliable storage. Count the show's tracks in
  Music immediately before any `rm`, and re-import from the local copy if
  they're missing. Possibly related: those six were the tracks flagged as
  over iCloud's ~200 MB per-track ceiling (209–226 MB) — unproven, but
  suspicious.

- **Verify twice, with a delay — tags can silently drift after they read
  as correct.** On the JRAD import the album verified at a clean 14/14,
  and minutes later read 13: track 14 had kept its title but silently lost
  its `artist` and `album`, landing back in "Unknown Artist / Unknown
  Album". Nothing errored. Music's background reorganize appears able to
  drop properties written moments earlier. So after tagging a show, count
  the album, wait ~20-45s, and count again before declaring it done or
  telling Jim it's ready. Re-apply anything that fell out, one property
  per call with pauses.

- **Vermont Tapers Collective FLACs often carry NO embedded tags at all.**
  Not placeholders — genuinely empty (`ffprobe -show_entries format_tags`
  returns nothing). Archive.org shows per-file `title`/`track` values in
  its item metadata, but those live only in the item record, not in the
  files, so XLD passes nothing through and every track imports named by
  filename (`jrad20230813t01`). When that happens the tracks land under
  "Unknown Artist / Unknown Album" and an artist-name search will not
  find them — look them up by `whose name contains "<filename stem>"`.
  Take the setlist from `metadata.description` and tag from scratch.

- **Check what's already embedded before re-tagging at all.** Some
  archive.org FLACs (matrix/soundboard releases especially) already carry
  real per-track titles and album in their embedded tags — XLD carries
  those straight through the ALAC conversion, and Music picks them up on
  import with no extra work. Taper AUD releases are inconsistent: often
  only track 1 has a real embedded title and the rest are generic
  placeholders ("Track 2", "Track 3", ...). Check a track's tags with
  `ffprobe -show_entries format_tags` before assuming a full re-tag pass
  is needed.

- **When cleaning up a corrupted batch is easier than repairing it** (e.g.
  the tracks being fixed are also being replaced by a better source, per
  "Same show, multiple tapes" above), just delete the broken track objects
  by persistent ID and re-import clean, rather than trying to repair
  fields in place:
  ```applescript
  tell application "Music"
    set matches to (every track of playlist "Library" whose persistent ID is "755EFF5710DD4987")
    repeat with t in matches
      delete t
    end repeat
  end tell
  ```

- **Avoid full-library scans.** Looping over *every* track in the Library
  playlist to search by name/location is slow (multi-minute) once the
  library is large. Prefer an exact/existential check —
  `exists (some track of playlist "Library" whose name is "...")` —
  which short-circuits, over `repeat` + manual `count`/compare.

## Progress page

A "Tape Desk" artifact tracks intake as a running summary (shows in
library, tracks converted, a session log, and a flagged card for
anything needing a manual check):

**https://claude.ai/code/artifact/d515b1da-20e9-424d-8f4f-0cbb74a6c498**

Redeploy that same URL after each new show is processed rather than
creating a new one (`Artifact` with `url:` set, after reading it back).
If the URL ever goes missing, find it with `Artifact` → `list`.

## What's in the library

Each show lives in its own folder here, with the original FLACs and the
converted `.m4a` kept side by side. Current contents:

| Folder | Show | Tracks |
|---|---|---|
| `dd2026-08-29_VERMONT_TAPERS_COLLECTIVE` | 2026-08-29, VTC tape | 7 |
| `laracwassband26-06-05_MTX_HSM_FLAC24` | Lara Cwass Band, Burlington Discover Jazz Festival 2026-06-05, MTX 24/96 | 6 |
| `moe2026-09-04_Adirondack_Fest` | moe., Adirondack Independence Music Festival 2026-09-04 (2 sets) | 16 |
| `danieldonato2026-09-04_Adirondack_Fest` | Daniel Donato's Cosmic Country, same festival | 11 |
| `aod2026-09-04_Adirondack_Fest` | Assembly of Dust, same festival | 8 |
| `eggy2026-09-04_Adirondack_Fest` | Eggy, same festival | 9 |
| `hsss2026-09-04_Adirondack_Fest` | The Hogslop String Band, same festival | 11 |
| `fdbb2026-09-04_Adirondack_Fest` | Funky Dawgz Brass Band, same festival — songs unidentified by the taper, tagged "Track 1"–"Track 8" | 8 |
| `jrad2023-08-13_VERMONT_TAPERS_COLLECTIVE` | Joe Russo's Almost Dead, Jay's Peak Amphitheater VT, 2023-08-13 (taped by Dave Kemp) | 14 |
| `jrad-eugene2026-08-14` | Joe Russo's Almost Dead, The Cuthbert Amphitheater, Eugene OR, 2026-08-14 (taped by Matt Nida) | 15 |
| `DogsinaPile2026-09-06_Adirondack_Fest` | Dogs In A Pile, Adirondack Independence Music Festival, 2026-09-06 — the first **Sept 6** set from that festival (taped by Al W.) | 17 |
| `jrad2026-08-01_MK4_2496` | Joe Russo's Almost Dead, Quarry Amphitheater, 2026-08-01, MK4 24/96 | 13 |
| `jrad2026-06-20_mbhoka200` | Joe Russo's Almost Dead, Northlands Arts & Music Fest, 2026-06-20 | 12 |
| `jrad2026-08-22_jazzbuph` | Joe Russo's Almost Dead, Dillon Amphitheatre CO, 2026-08-22 — **IN PROGRESS, see "Current state" below** | 19 |

### Current state / resume here

`jrad2026-08-22_jazzbuph` (Dillon) is mid-pipeline: all 19 FLACs are
downloaded and size-verified, but conversion/import is incomplete. Check
actual progress before assuming any specific track count — it's been
worked on across more than one session tick:

```
ls jrad2026-08-22_jazzbuph/*.m4a | wc -l   # how many converted so far
osascript -e 'tell application "Music" to count (every track of playlist "Library" whose album is "Dillon")'
```

To resume conversion + import (skips whatever `.m4a` already exist):

```
/Users/jim/Downloads/flac-pipeline.sh /Users/jim/dev/musicsync/jrad2026-08-22_jazzbuph
```

After it finishes: tag from the setlist if titles didn't carry through
(check with `ffprobe -show_entries format_tags` on a track first — these
files have real per-file titles in the archive.org metadata, so they
likely need no retagging), do the delayed double-verify (count now, again
in 30s), then archive the FLACs to
`/Volumes/musicarchive/taper-masters/jrad2026-08-22_jazzbuph/` per the
copy-verify-delete discipline above, and add its inventory row's track
count once confirmed complete.

If a long run is about to start, restart the awake-hold if it's not
already running: `pgrep -fl caffeinate` to check, otherwise
`nohup caffeinate -dims > /dev/null 2>&1 &`.

**Downloading further shows:** use `getshow.py`, not a bash script with
`read` — see the taper-import skill for why (space-containing filenames
get corrupted by shell word-splitting). It lives at
`.claude/skills/taper-import/getshow.py`.

**Other disk-cleanup candidates surfaced during a full-Mac survey, not
yet acted on:** SnagIt app support (~4.4 GB), a dormant
`Projects/escalator` folder (~4.6 GB), and Claude's own `vm_bundles`
cache (~13 GB) — all candidates for moving to the NAS or deleting, ask
Jim before touching any of them.

**Only FLAC masters live here now.** The converted `.m4a` files were deleted
on 2026-09-07 — Apple Music copies every import into its own Media folder
(`~/Music/Music/Media.localized/Music/...`) and never references this
directory, so keeping them was pure duplication (6.5 GB). Re-convert from
the FLACs if a local ALAC copy is ever needed. Note the shell cannot read
`~/Music` at all (macOS TCC blocks it) — `du`/`ls` there return empty, so
verify Music-side files through AppleScript's `location` property instead.

A 5-track Vermont Tapers Collective **AUD** tape of the 2026-06-05 Lara
Cwass Band show was imported and then deliberately removed from Music,
replaced by the higher-resolution MTX matrix tape of the same show. Don't
re-import the AUD version.

## Watching for new uploads

Tapers post a multi-day festival in pieces over the following days, so
it's worth re-checking an event for a week or so. Two query shapes:

```
# by PERFORMANCE date — finds a specific night
curl -s "https://archive.org/advancedsearch.php?q=collection%3Aetree+AND+\
creator%3A%28moe.%29+AND+date%3A%5B2026-09-05+TO+2026-09-07%5D\
&fl%5B%5D=identifier&fl%5B%5D=title&fl%5B%5D=date&rows=20&output=json"

# by UPLOAD date — finds anything newly posted, newest first
curl -s "https://archive.org/advancedsearch.php?q=collection%3Aetree+AND+\
title%3A%28Adirondack%29&fl%5B%5D=identifier&fl%5B%5D=addeddate\
&sort%5B%5D=addeddate+desc&rows=10&output=json"
```

**Use both.** A watch that filters only on performance date will silently
miss a newly-uploaded set from a night you already have — that exact bug
hid The Hogslop String Band's 2026-09-04 set for a whole night, because
the watch was scoped to Sept 5–7 performance dates while the new upload
carried a Sept 4 date. Sort by `addeddate desc` to catch everything.

Also note the identifier prefix need not match the band or the filenames:
the Hogslop item is `hsss2026-09-04` but its files are `hssb2026-09-04*`.
Always read the real file names out of the metadata JSON rather than
guessing them from the identifier.

## iCloud Music Library: what can and can't be automated

Newly imported tracks show `cloud status` of `unknown` and do **not**
upload on their own — they appear on other devices by name but won't
play. Forcing the upload is a **manual, at-the-Mac step**:
Music → File → Library → Update Cloud Library.

This cannot be triggered remotely, and it's worth not re-litigating:

- Music's AppleScript dictionary exposes `cloud status` as **read-only**
  and has no "update cloud library" command (checked the sdef directly —
  note `sdef` itself needs Xcode, so read
  `/System/Applications/Music.app/Contents/Resources/com.apple.Music.sdef`).
- Driving the menu via System Events fails with `-1719` (osascript has no
  Accessibility permission). Granting Terminal Accessibility permission
  once, in System Settings → Privacy & Security → Accessibility, would
  make this automatable in future — Jim has been told, it's his call.
- Screen Sharing and Remote Login are both off, so there's no remote-GUI
  fallback either.
- Quitting and relaunching Music does **not** kick off the upload
  (tried it; status stayed `unknown` across 20+ checks over 10 hours).

Per-track ceiling is about **200 MB**; four of the Lara Cwass MTX ALAC
tracks are 209–226 MB and may report `ineligible` even after a manual
sync. Everything else in the library is comfortably under.

When Jim needs to listen before an upload completes, the recordings
stream free from their archive.org page — that's the practical answer,
not waiting on iCloud.

## Long runs

For multi-gigabyte downloads or long conversion batches, hold the Mac
awake first:

```
nohup caffeinate -dims > /dev/null 2>&1 &
```

Print a per-track progress line as each file downloads and converts —
Jim likes watching the work happen rather than getting only a final
summary.
