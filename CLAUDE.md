# musicsync

## Archive storage: Synology NAS

Local disk fills up fast with 24-bit taper FLACs, so completed shows get
their masters moved off the Mac once imported and verified in Music:

- Share: `musicarchive` on the Synology DiskStation at `<NAS_IP>`,
  mounted at `/Volumes/musicarchive` (mount survives most reboots; if it's
  missing, reconnect via Finder ⌘K → `smb://<NAS_IP>` and enter the
  saved keychain credentials — don't script the mount with a password
  inline).
- Archived masters live under `/Volumes/musicarchive/taper-masters/<show>/`.
- **`taper-masters/` is tiny — under 15GB — relative to the share's 3.9TB
  capacity.** As of 2026-09-09 the whole `musicarchive` share was 96% full
  (176GB free) but that has nothing to do with this project; whatever's
  filling it up is other content on the share. Don't assume this project
  is the cause if the NAS looks full — check the actual `taper-masters`
  size (Finder → get info, or sum file sizes via Finder AppleScript — see
  next gotcha) before proposing to move anything off the NAS.
- **Shell tools (`ls`, `du`, `cp`, `rsync`) cannot read `/Volumes/musicarchive`
  at all — fails with "Operation not permitted", even with Terminal's Full
  Disk Access toggled on in System Settings.** This is the same class of
  restriction already documented below for `~/Music`. Finder (via
  AppleScript) *can* see and copy from the share fine — use
  `tell application "Finder" to duplicate folder X of disk "musicarchive" to folder Y`
  to pull files to a normal local path shell tools can then read. Folder-level
  `size`/`physical size` often returns `missing value` over the network even
  with retries; sum `size of every item of folder X` instead (works, since
  each file's size is a synchronous property). Large-show duplicates
  (>1-2GB) can hit `AppleEvent timed out (-1712)` on the default Finder
  timeout — wrap the call in `with timeout of 1800 seconds ... end timeout`
  and verify the file count after, since the copy sometimes actually
  finishes despite the timeout error being thrown.
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

3. **Convert + import**: `~/.claude/skills/music-icloud-sync/flac-pipeline.sh <that-folder>` —
   batch FLAC→ALAC via XLD, then imports each `.m4a` into Apple Music.
   Resumable (skips any `.flac` whose `.m4a` already exists). See the
   script's own header comments for the XLD hang-after-write quirk it
   works around. (This script moved here from `~/Downloads/` at some
   point — if `~/Downloads/flac-pipeline.sh` is missing, check this path
   before assuming the pipeline is gone.)
   - **On a fresh XLD install/reinstall, this will silently produce `.aiff`
     files instead of `.m4a`, and every track will report FAILED** (the
     script polls for a `.m4a` output file that never appears). Root cause:
     XLD's `-f alac` CLI flag doesn't select a format on its own — it needs
     a matching output-format *preference* already configured. A fresh
     install has only AIFF configured (`defaults read jp.tmkk.XLD
     OutputFormatName` reads `AIFF`). Fix: open XLD's GUI once, go to
     Preferences → Output Format tab, choose **Apple Lossless**, then quit
     XLD (`osascript -e 'tell application "XLD" to quit'`) to flush the
     preference to disk — it stays in memory until the app quits. After
     that, `OutputFormatName` reads `Apple Lossless` and `-f alac` on the
     command line converts correctly. Also: a freshly-downloaded XLD.app is
     Gatekeeper-quarantined (`spctl -a -vv /Applications/XLD.app` → `rejected`);
     double-clicking it once and clicking through the Gatekeeper prompt is
     enough to let subsequent CLI invocations run (no need to clear the
     quarantine xattr).
   - **The import step needs Terminal to have Automation permission for
     Music specifically** (System Settings → Privacy & Security →
     Automation → Terminal → Music), separate from the Music/System Events
     grants already covered elsewhere in this file. Without it every
     `osascript ... tell application "Music" to add f` times out after
     120s with `-1712`, and 16 tracks × 120s adds up fast — check
     `sqlite3 ~/Library/Application\ Support/com.apple.TCC/TCC.db "SELECT
     client,indirect_object_identifier,auth_value FROM access WHERE
     service='kTCCServiceAppleEvents'"` for a `com.apple.Music|0` (denied)
     row before waiting out a full timeout run.

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

**The "Setlist Ledger" is also mirrored as its own public GitHub Pages
site** — a second, separate public repo (`vtjim/setlist-ledger`, not this
one), matching the pattern of Jim's other public single-page sites
(`recipes`, `songbook`, `road-trip-shuffle`): plain `index.html` at repo
root, GitHub Pages serving from `main`/`/`.

- Artifact (same content, update via `Artifact` redeploy):
  **https://claude.ai/code/artifact/d03ea4cb-2313-40b5-9b99-367dd25f6b69**
- Public site: **https://vtjim.github.io/setlist-ledger/** — after
  redeploying the artifact, copy the same source into that repo's
  `index.html` (it needs the full `<!doctype html><html><head>...`
  wrapper the artifact's own render skips) and `git push`.

Show data lives as a JS array (`SHOWS`) near the bottom of the file in
both places — keep them in sync. Format: `{c: collection name, a: artist,
d: YYYY-MM-DD, v: venue (blank if redundant with the collection name),
t: track count, id: archive.org identifier (blank string if none
confirmed)}`.

## Backups

**As of 2026-09-17, the `musicsync` GitHub repo
(`https://github.com/vtjim/musicsync`) is PUBLIC** — Jim's own call,
after a scrub pass. Personal values (the NAS's local IP, and the email
addresses used by the library-update-email skill) are placeholders in
the tracked files (`<NAS_IP>`, `<JIM_EMAIL>`, `<MELISSA_EMAIL>`,
`<ALAN_EMAIL>`) resolved from `.claude/local-values.md`, which is
gitignored and must never be committed. **Before adding any new secret,
email address, IP, or other personal detail to a tracked file, add it to
`local-values.md` as a placeholder instead** — this repo is public now,
so anything committed here is world-readable. Commit and push
periodically, especially after a big batch of changes.

A full working clone of both this repo and `setlist-ledger` (with
`origin` pointed at GitHub, not a local path) lives on the "TAPEBACKUP"
USB drive under `git-backups/` as a portable, turnkey copy — `git pull`
there after pushing here to keep it current. `local-values.md` isn't
tracked by git so it doesn't come along automatically on a pull; copy it
over by hand if it changes.

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
| ~~`jrad2026-08-22_jazzbuph`~~ | Joe Russo's Almost Dead, Dillon Amphitheatre CO, 2026-08-22 — complete, **no local folder** (FLAC deleted 2026-09-14 after verifying in Music + USB master, same as the Dead of Summer batch below) | 19 |
| ~~`moe2026-09-05_Adirondack_Fest`~~ | moe., Adirondack Independence Music Festival 2026-09-05 (2 sets, AUD, taped by Ted Gakidis) — **no local folder**, FLAC deleted 2026-09-14 | 16 |
| ~~`ptf2026-09-06_Adirondack_Fest`~~ | Pink Talking Fish, same festival, 2026-09-06 (AUD, same taper) — **no local folder** | 11 |
| ~~`hilltop2026-09-06_Adirondack_Fest`~~ | Hilltop, same festival, 2026-09-06 (SBD, taped by Kyle Holbrook) — **no local folder** | 8 |
| ~~`lcwass2026-09-04_VERMONT_TAPERS_COLLECTIVE`~~ | Lara Cwass Band, live at Zenbarn, Waterbury VT, 2026-09-04 (AUD, VTC — no embedded tags, setlist tagged by hand from the item description) — **no local folder** | 12 |

**Dead of Summer Music Festival, Manchester VT, 2026-07-09 to 07-12** (16 shows,
226 tracks, imported 2026-09-13/14) — these have **no local folder**. FLACs
were downloaded, converted, imported into Apple Music, added to the
`usb-prep-output` CarPlay master, verified in both places, then the local
FLAC was deleted to save disk space (per Jim's call — see the USB/CarPlay
master section below for the full discipline). Re-download from archive.org
if a local ALAC/FLAC copy is ever needed again.

| Artist | Date | Tracks | Source | Notes |
|---|---|---|---|---|
| Steely Dead | 07-09 | 17 | `sd2026-07-09` | no embedded tags — retagged from setlist |
| Creamery Station | 07-10 | 10 | `CS2026-07-10` | no embedded tags, no setlist found — generic "Track N" titles |
| Dead Man's Waltz | 07-10 | 10 | `DMW2026-07-10` | no embedded tags — retagged from setlist |
| God Street Wine | 07-10 | 17 | `gsw2026-07-10.sbd` | tags embedded correctly |
| Splintered Sunlight | 07-10 | 16 | `ssun2026-07-10.sbd` | no embedded tags — retagged from setlist |
| Brown Eyed Women | 07-11 | 13 | `bew2026-07-11.sbd` | tags embedded correctly |
| Deadgrass | 07-11 | 11 | `deadgrass2026-07-11.sbd` | tags embedded correctly |
| Giant Panda Guerilla Dub Squad | 07-11 | 10 | `gpgds2026-07-11` | no embedded tags, no setlist found — generic "Track N" titles |
| Jatoba | 07-11 | 13 | `jatoba2026-07-11` | no embedded tags — retagged from setlist |
| Jerry's Middle Finger | 07-11 | 14 | `jmf2026-07-11.sbd` | tags embedded correctly |
| Pink Talking Fish | 07-11 | 21 | `ptf2026-07-11.sbd` | tags embedded correctly — distinct from the Sept 6 ADK Fest set |
| Terrafunk | 07-11 | 17 | `terrafunk2026-07-11` | no embedded tags, no setlist found — generic "Track N" titles (Meters tribute set) |
| Leftover Salmon | 07-12 | 20 | `los2026-07-12.sbd` | tags embedded correctly |
| Maestro Soup | 07-12 | 5 | `MS2026-07-12.Matrix...` | tags embedded correctly |
| Mystic Dead | 07-12 | 13 | `MD2026-07-12.sbd` | tags embedded correctly |
| Daniel Donato's Cosmic Country | 08-15 (Jay Peak, VT — separate show, not part of DoS) | 19 | `danieldonato2026-08-15.MVBAKGHD` | titles embedded in filenames, carried through cleanly |

Note: `dd2026-08-29_VERMONT_TAPERS_COLLECTIVE` above is Dobbs' Dead, not part
of Dead of Summer — a same-named-initials coincidence caught during this
same session's audit.

**Snugfest, Ripton VT** (3 shows, 34 tracks, imported 2026-09-14) — also
**no local folder**, same discipline. The 2026 edition hasn't been posted
to archive.org yet as of this writing; a recurring watch is checking
hourly (see "Watching for new uploads"). These are the 2024/2025 editions,
pulled in ahead of the 2026 one at Jim's request.

| Artist | Date | Tracks | Source | Notes |
|---|---|---|---|---|
| LaMP | 2025-09-28 | 13 | `lamp25-09-28.mtx.hsm.flac24` | tags embedded correctly |
| Vorcza | 2025-09-28 | 10 | `vorcza2025-09-28.mtx.hsm.flac24` | tags embedded correctly |
| LaMP | 2024-09-29 | 11 | `LaMP2024-09-29.AKG414XLIICoffey` | no embedded tags, setlist template left blank by taper — generic "Track N" titles |

**One-off shows pulled from pasted archive.org links, 2026-09-14** — also
no local folder, same discipline as above.

| Artist | Date/Venue | Tracks | Source | Notes |
|---|---|---|---|---|
| Soule Monde | Lost Nation Brewery, Morrisville VT — 2026-05-23 | 17 | `soulemonde2026-05-23.matrix` | no embedded tags — setlist tagged by hand from item description |
| Scott Metzger | Concert for Star Route Farm, Bearsville Theater, Woodstock NY — 2025-11-20 | 15 | `wolf2025-11-20.mg20` | no embedded tags. A Cline/Medeski/Metzger/Martin improv set — filenames used a "cmmm" prefix, the actual identifier/creator is "Scott Metzger" |
| ESP (opener) + Soule Monde | The Prindle Baldwin Barn, Hinesburg VT — 2023-05-28 | 1 + 11 | `soulemonde2023-05-28.Vermont_Tapers_Collective_FLAC` | no embedded tags, no titled setlist — track 1 is the opening act ESP (per item description "ESP opened, they are the first track"), tracks 2–12 are Soule Monde. Jim specifically asked to find any Soule Monde show in Hinesburg VT; a second taper's version of this same show exists (`soulemonde2023-05-28.antaya`, 14 tracks) and was not pulled. |
| Sans Souci: Tribute to JGB | Camp Birch Hill Rec Hall, New Durham NH — 2026-08-28 | 21 | `sanssouci2026-08-28.m260.tf-11.sbd.flac` | tags embedded correctly (SBD, taped by Ted Gakidis — same taper as several ADK Fest shows above) |
| Todd Snider | The Orange Peel, Asheville NC — 2025-08-06 | 24 | `ToddSnider2025-08-06.m21.flac24` | tags embedded correctly (taped by Gordon Wilson, Microtech Gefell M21). Only Todd Snider live recording posted in the last 2 years — his artist name already had 411 other (studio) tracks in Music from Jim's existing collection, so verify this show by album, not artist, when counting: `album is "2025-08-06 - The Orange Peel - Asheville, NC"` |

**Jeezum Crow Music Festival — Stateside Amphitheater, Jay Peak, Jay VT**
(13 shows, 195 tracks, imported 2026-09-15) — also no local folder, same
discipline as above. Jim asked for the 2023, 2024, and 2025 editions
specifically (2026's has also since been posted but wasn't pulled — ask
before adding it). Where archive.org had multiple tapes of the same set,
the more complete/consistent one was used — see notes per show.

| Artist | Date | Tracks | Source | Notes |
|---|---|---|---|---|
| Leftover Salmon | 2023-07-07 | 21 | `los2023-07-07` | no embedded artist tag (album/title were present) — 6 of 21 tracks had no posted title either, tagged generic "Track N" |
| Sam Grisman Project | 2023-07-07 | 9 | `SGP2023-07-07` | no embedded artist tag, all real titles present |
| Neighbor | 2023-07-08 | 10 | `nbr3pm2023-07-08.tcca.flac16` | no embedded tags at all, titles taken from filenames. Used this identifier over the plain `nbr3pm2023-07-08` (a different, shorter 6-track tape of the same show) |
| Pigeons Playing Ping Pong | 2024-07-19 | 13 | `pppp2024-07-19.MVBAKGHD` | no embedded tags, titles from filenames |
| The Mallett Brothers Band | 2024-07-19 | 9 | `TMBB2024-07-19.MVBAKGHD` | no embedded tags; taper's own setlist marks several songs unidentified ("Track 2/3/4/5/7") — kept as-is, not guessed |
| Del McCoury Band | 2024-07-20 | 24 | `del2024-07-20.MVBAKGHD` | no embedded tags. Used the MVBAKGHD taper's version (same taper as the rest of this day) over a separate 42-track `delmccouryband24-07-20.mc930.hsm.flac24` tape of the same show |
| Charlie Parr | 2024-07-20 | 21 | `cp2024-07-20.MVBAKGHD` | no embedded tags, no posted setlist ("Set list unknown") — all generic "Track N" |
| Eggy | 2024-07-20 | 11 | `eggy2024-07-20.MVBAKGHD` | no embedded tags, titles from filenames — distinct from Eggy's other 2024/2026 sets elsewhere in this catalog |
| Infamous Stringdusters | 2024-07-20 | 12 | `isd2024-07-20.MVBAKGHD` | no embedded tags, titles from filenames |
| Zach Nugent | 2025-07-11 | 13 | `ZachNugent2025-07-11` | already present in Apple Music from an earlier, untracked import (found mid-batch, exact track titles/tags already correct) — only the USB/CarPlay master was backfilled for this one, no FLAC→ALAC→Music step was repeated |
| LaMP | 2025-07-12 | 10 | `LaMP2025-07-12.MVBAKGHD` | no embedded tags (only technical Sound Forge metadata), titles from filenames |
| Dark Star Orchestra | 2025-07-12 | 24 | `dso2025-07-12.MVBAKGHD` | no embedded tags, titles from filenames. Filenames say "07-11" but the item's own date field and description say 2025-07-12 — went with the item's stated date |
| Charlie Parr | 2025-07-12 | 18 | `cp2025-07-12` | no embedded artist tag (album/title were present) — 2 of 18 tracks had no posted title, tagged generic "Track N" |

**John Craigie** (2026-09-15) — no local folder for any of these, same
discipline as above. Jim asked to pull his last 2 years of shows (there's
no VT/Higher Ground or Stowe recording of him on archive.org at all,
despite Jim having seen him there — checked all 34 of his etree items,
none are from Vermont).

| Artist | Date/Venue | Tracks | Source | Notes |
|---|---|---|---|---|
| John Craigie and The Coffis Brothers | Ogden Music Festival — 2025-05-31 | 12 | `jcraigie2025-05-31` | tags embedded correctly |
| John Craigie | Zonnehuis, Amsterdam NL — 2025-01-30 | 21 | `jcraigie2025-01-30.DPA4061.24bit` | tags embedded correctly (24-bit) |
| John Craigie | DelFest — 2024-05-24 | 17 | `jcraigie2024-05-24` | no embedded titles, titles carried through from filenames. Hit mid-import: a `while IFS= read -r fname; do ... done < filelist.txt` loop had the backgrounded XLD process stealing bytes from the loop's own stdin, silently dropping every other filename (tracks 02/04/06/08/10/12/14/16 never downloaded on the first pass) — a new gotcha, not seen before this session. **Fix: never feed a `while read` loop from `< file` when the loop body launches any subprocess** — either read into an array first (`mapfile -t files < filelist.txt` in bash; zsh lacks `mapfile`) and use `for f in "${files[@]}"`, or keep the `while read` but source it from a non-stdin fd (`done 3< filelist.txt` paired with `read ... <&3`) so no child process can compete with the loop for file descriptor 0. The same bug recurred converting this show's Amsterdam sibling to MP3 (see next row) until switched to the fd-3 form. |
| John Craigie | Paradiso, Amsterdam NL — 2024-01-10 | 25 | `jcraigie2024-01-10` | tags embedded correctly, including a real `ALBUM` tag — **but that ALBUM tag was `Live in Amsterdam`, identical to the 2025-01-30 Zonnehuis show above**, even though they're different dates/venues/years. `fix_tags_and_organize.py` groups strictly by ALBUM tag, so it silently merged both shows into one USB-master folder and overlapping `NN - Title.mp3` filenames overwrote each other (46 tracks expected, 37 survived — 9 lost). Fixed on the USB side by deleting the merged folder and rebuilding both shows into distinctly-named folders. **But the identical `Live in Amsterdam` ALBUM tag was never fixed in Apple Music itself** — both shows sat merged into one indistinguishable 46/47-track "album" there (Jim couldn't find/tell apart 2 of his 4 John Craigie albums as a result) until caught and fixed on 2026-09-16, splitting by each track's embedded `year` field (2024 vs 2025) into `Live at Paradiso, Amsterdam NL - 2024-01-10` (25 tracks) and `Live at Zonnehuis, Amsterdam NL - 2025-01-30` (21 tracks) — the year-based split doesn't land on exactly 24/22 as originally documented, one track's embedded year is probably off by a show, not worth chasing further. **General gotcha: don't assume ALBUM tag uniqueness across different shows by the same artist, in Apple Music OR the USB master** — a collision silently merges both in the Music app too, not just the USB organizer script. Check for an existing same-named album/folder before importing a new show, especially for artists who tour the same city/venue-type repeatedly. |

### Resuming a long-running pipeline

If a show is mid-pipeline (some `.m4a` converted, none/some imported),
`~/.claude/skills/music-icloud-sync/flac-pipeline.sh <folder>` is safely
resumable — it skips any `.flac` whose `.m4a` already exists. Before
running it, confirm XLD is installed, Gatekeeper-approved, and its Output
Format preference is set to Apple Lossless, and that Terminal has
Automation permission for Music — see the gotchas under "End-to-end
pipeline" step 3 above. (Dillon Amphitheatre, `jrad2026-08-22_jazzbuph`,
went through exactly this path on 2026-09-13/14 — XLD had gone missing
from `/Applications` at some point, all three of those had to be freshly
set up, and may need re-checking again if this machine's XLD install
changes.)

If a long run is about to start, restart the awake-hold if it's not
already running: `pgrep -fl caffeinate` to check, otherwise
`nohup caffeinate -dims > /dev/null 2>&1 &`.

**Downloading further shows:** use `getshow.py`, not a bash script with
`read` — see the taper-import skill for why (space-containing filenames
get corrupted by shell word-splitting). It lives at
`.claude/skills/taper-import/getshow.py`.

**Disk-cleanup candidates from an earlier full-Mac survey — mostly stale,
checked 2026-09-15:** the "SnagIt app support (~4.4 GB)" and
`Projects/escalator` (~4.6 GB) entries that used to be here were wrong —
neither is reachable by shell, Spotlight, or `/Applications` (SnagIt
isn't even installed anymore), so there's nothing there to reclaim.
Claude's own `vm_bundles` cache was real (found at ~8.7 GB, not the ~13 GB
originally estimated) and was deleted with Jim's approval on 2026-09-15 to
unblock the John Craigie batch — it regenerates automatically if Claude
needs it again, so it's fine to delete again in future if it's grown back
and space is needed. No other cleanup candidates are known right now; if
disk gets tight again, ask Jim rather than assuming these old ones still
apply.

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

## USB/CarPlay master (separate from Apple Music)

`~/Music/usb-prep-output/` (see the `usb-music-prep` skill) is a *separate*
320kbps-MP3, `Artist/Album/` library independent of this project's FLAC/
ALAC pipeline into Apple Music — built for a car's USB stick, not iCloud.
On 2026-09-09 the full musicsync catalog (everything with local FLACs at
the time, pulled from the NAS where needed) was backfilled into it in one
pass: 15 shows, 194 tracks converted via `ffmpeg -ab 320k -map_metadata 0`
then organized with `usb-music-prep/scripts/fix_tags_and_organize.py`.

- `dd2026-08-29_VERMONT_TAPERS_COLLECTIVE` was skipped — it's Dobbs' Dead's
  2026-08-29 "Jam in The Parks" show, already present in `usb-prep-output`
  from an earlier, separate pipeline (same 7 tracks, same titles, confirmed
  byte-for-byte-equivalent setlist before skipping).
- Several JRAD FLACs (`jrad-eugene2026-08-14`, `jrad2023-08-13_VERMONT_TAPERS_COLLECTIVE`,
  `jrad2026-06-20_mbhoka200` — 41 tracks total) carry **no embedded tags at
  all** (same gotcha as the VTC-FLAC note below), so the auto-organizer
  filed them under "Unknown Artist". They were manually fixed by pulling
  the correct artist/album/titles from these same shows' already-correct
  entries in the Apple Music library (these three were imported properly
  there already) rather than re-deriving from archive.org.
  `moe2026-09-05_Adirondack_Fest`'s FLACs are also missing an `ALBUM` tag
  (like their `.m4a` copies — see the tagging section above); it was
  manually merged into the existing `moe./ADK Fest 2026` folder rather
  than left under an ugly folder-name fallback.
- `jrad2026-08-22_jazzbuph` (Dillon) **was** included in this backfill even
  though its Apple Music import is still incomplete — the USB conversion
  works straight from the FLACs and doesn't depend on the Music import.
- Going forward, add each new show to this master as part of step 6
  (cleanup/report) of the taper-import pipeline, not just the Apple Music
  side — `ffmpeg -i in.flac -ab 320k -map_metadata 0 -id3v2_version 3
  -write_id3v1 1 out.mp3` per track, then
  `fix_tags_and_organize.py <scratch_dir_with_mp3s> ~/Music/usb-prep-output`.

### Local disk space: delete the FLAC once it's safely in both places

As of 2026-09-13, once a show is **verified in Apple Music AND its MP3 has
landed in `usb-prep-output`**, the local FLAC gets deleted rather than kept
or sent to the NAS — Jim's call, to keep this Mac's disk from filling up.
This replaces the earlier "always archive to NAS" assumption for new
imports; the NAS is still where the pre-existing catalog's masters live,
this is just a lighter-weight option for anything freshly imported when the
NAS isn't worth the trip. **Verify both destinations before deleting** —
same discipline as the NAS copy-verify-delete rule, for the same reason
(Music has lost tracks silently before). When importing a batch where
several FLACs will roughly double in size as ALAC `.m4a` siblings before
Music copies them into its own library, budget for that temporary spike —
converting the FLAC→ALAC and Apple-Music-importing a whole batch before
deleting anything risks running out of disk space mid-batch; delete each
show's FLAC right after *that show* verifies, not after the whole batch.

### A "gap" in Apple Music can be a false positive — verify by count, not existence

While auditing Apple Music for live shows that had been imported (some other
way) without a matching local FLAC master, a bulk scan of `artist ||| album`
pairs among tracks added in 2026 turned up entries that *looked* like full
show imports but several turned out to be a single stray track sharing that
artist/album combo — not a real recording. (Concretely: `LOS ||| 2026-07-12`
looked like a full Leftover Salmon set, but querying `artist is "LOS"`
found exactly one track named "Track 09".) Always confirm with an actual
track **count** for that specific artist/album before treating something as
"already imported and just needs its master backfilled" — a same-artist
query that returns far fewer tracks than the source recording has means
it's not actually there, and the show needs the full FLAC→ALAC→import
pipeline, not just an archive backfill.

### The "N tracks in Music" figure is arithmetic, not a verified count

Every status update in this project that quotes a track total "in Apple
Music" is really a running sum of each show's logged count in this file —
never an independent, live count of the library. That's because Music's
`Library` playlist mixes in Jim's entire personal collection (thousands of
unrelated tracks — one single artist, Todd Snider, has 411 personal tracks
under his own name), so there's no clean filter that isolates "just the
taper-import tracks." Trust the per-show counts (verified individually by
artist+album at import time) over any aggregate total, and treat a full
reconciliation audit (see below) as worth repeating periodically rather
than a one-time fix.

### USB/Music reconciliation, 2026-09-16 — a real ~220-track gap had opened up

A routine "why don't these two totals match" question turned up two
distinct problems, both now fixed:

**1. A silent artist-name bug.** Pink Talking Fish's Dead of Summer
7/11/26 show (21 tracks, already logged correctly in this file) had
actually been tagged "Pink Talking Phish" (extra silent "h") in both
Apple Music and the USB master at some point during manual retagging —
the typo just never got caught because CLAUDE.md's own notes said "Pink
Talking Fish" and nobody cross-checked the real tag. Investigating it
surfaced a second, previously undocumented Pink Talking Fish/Phish show
too (Stateside Amphitheater, Jay Peak — 8/23/25). Of the 50 tracks sitting
under the misspelled "Pink Talking Phish" in Music, only 32 turned out to
be real Pink Talking Fish content (the 21-track Dead of Summer show +
10 usable tracks from the Jay Peak show); the other ~19 are lossy,
cloud-evicted tracks of unknown origin that got reverted back to "Pink
Talking Phish" rather than force-relabeled, since guessing their real
source risked making the data worse, not better. **If Jim ever wants to
sort out that remaining 19-track "Pink Talking Phish" pile, they need
identifying by ear.** Song titles suggest it's not Pink Talking Fish at
all — filenames are prefixed "SF2025-08-22" (two sets, 18 real-looking
titles: Tuning Intro, Two Boys, Stout Hearted, Like You Anyway, Paperback
Book, Shift My Step, Sometimes, As, Lines and Circles, Whatever, Utterly
Addled-What Say You, Chasing Away, Westerly, Blue and Grey, Cabin John,
Far From Yourself, So Well) plus one lone raw-filename track
("VM162228") that's probably not music at all. Ask Jim what "SF" is
before spending any more time on this — it's very likely an entirely
different band that got mixed into the wrong artist bucket at some point. The USB master's "Pink Talking Phish" folder also had an
18-track partial duplicate of the Dead of Summer show sitting alongside
the correct 21-track copy (lost to a filename collision, some other run) —
deleted; USB "Pink Talking Fish" now correctly totals 32 tracks (11 ADK
Fest + 21 Dead of Summer), matching Music's non-lossy portion exactly. The
10 usable Jay Peak tracks are lossy/cloud-only and can't be mirrored to
the USB master — that's a real, permanent gap between the two totals, not
a bug.

**2. Nine real shows existed on the USB master but had never been
imported into Apple Music at all** (~181 tracks, predating careful
per-show tracking). All nine are now imported, verified, and tagged —
see the table below. **Not every show master originates from
archive.org** — one of these nine (LDB, below) turned out to be a zip
Jim had downloaded directly, sitting forgotten in `~/Downloads` with no
archive.org identifier at all. A future "I searched archive.org and can't
find this show" dead end should prompt a check of `~/Downloads` for an
already-present zip before concluding a show is unrecoverable — that's
exactly what happened here, and archive.org search alone would never
have found it.

| Artist | Date/Venue | Tracks | Source | Notes |
|---|---|---|---|---|
| New Mastersounds | Brooklyn Bowl, Brooklyn NY — 2025-11-22 | 29 | `nms2025-11-22.cmc622.sbd.matrix.flac24` | tags embedded correctly |
| New Mastersounds | Jam Cruise 22 Pool Deck — 2026-02-10 | 19 | `nms2026-02-10` | embedded artist tag said "The New Mastersounds" — renamed to "New Mastersounds" for consistency with the Brooklyn Bowl show and the USB folder ("NMS") |
| Nico Suave | Mothership (Led Zeppelin tribute set), Nectar's — 2022-05-07 | 25 | `NicoSuaveMothership2022-05-07` | no embedded tags — tagged "Nico Suave" (not the full "Nico Suave & The Mothership") to match the USB master's existing convention |
| Lyle Brewer (opener) + Ryan Montbleau | Higher Ground, South Burlington VT — 2025-03-29 | 8 + 21 | `montbleau2025-03-29` | single archive.org item, split by filename prefix same as the ESP+Soule Monde Hinesburg precedent above. Montbleau's set titles came from the item's own setlist description (3 songs left as "Track N" where the taper marked them unknown); Lyle Brewer's 8-track opener had no posted setlist, generic "Track N". Ryan Montbleau already had 24 unrelated personal/studio tracks in Music under his name — don't confuse those with this live show |
| Organ Fairchild | Dead of Summer Music Festival — 2024-07-13 | 9 | `of2024-07-13` | no embedded tags, no setlist — generic "Track N". **This is the 2024 edition of Dead of Summer, a different year from the 16-show 2026 batch documented above** — don't merge them |
| Soule Monde | Town Hall Theater, Middlebury VT (NYE) — 2025-12-31 | 19 | `soulemonde2025-12-31.akg414.m950` | no embedded tags — tagged by set/track number ("Set 1 Track 01" etc.) to match the USB master's existing convention; USB folder renamed from inconsistent "Soulemonde" to "Soule Monde" to match the other two Soule Monde shows |
| Hug Your Farmer | 2025-11-21 | 24 | `hyf20251121t23` | no embedded tags — generic "Track N". One track failed XLD conversion on the first pass, succeeded on a resumed retry — no data lost |
| LDB | "Les Brers In A Minor Jam" (Allman Brothers/Dead tribute set), Nectar's — 2025-04-01 | 18 | **not on archive.org** — direct zip download, see note above | no embedded tags, but real song titles were in the filenames (a Dead/Allmans setlist) — tagged from those |
| All Night Boogie Band | "Jam in the Parks" — 2026-08-29 | 9 | `anbb2026-08-29` (archive.org identifier reads "2029" due to an uploader typo — the content is the real 2026-08-29 show) | no embedded tags — generic "Track N". Same event Dobbs' Dead played that day, already documented above |

Two zips for undocumented Zach Nugent shows (`2024-04-05`, `2024-04-08` —
plus a duplicate download of the 04-08 one) were found sitting in
`~/Downloads` during this cleanup and are **not yet processed** — ask Jim
before pulling those in, they were out of scope for this reconciliation.

Even after fixing both problems above, the Music/USB totals don't land
on an exact match — expect roughly a 70-90 track gap (Music higher),
accounted for by the ~19 unresolved "Pink Talking Phish" tracks and the
10 lossy Jay Peak tracks that can't be mirrored to USB, plus some smaller
drift this pass didn't fully chase down. Worth another audit pass
eventually rather than assuming the two numbers should ever match exactly.

**Reconciliation completed 2026-09-16.** All nine shows in the table above
are now confirmed imported into Music (verified with the delayed
double-check — Music's indexing lagged 60-90 seconds behind the actual
import on several of these, reading 0 or a partial count immediately
after import and only settling to the true number after a wait; don't
trust an immediate post-import count on this library, it's large enough
now that indexing visibly lags) and mirrored to the USB master with real
setlist titles where one existed. Final totals: **69 shows, ~1,013 tracks
in Music (arithmetic), 1,090 tracks on the USB master (verified real
count).**

**Two more bugs found and fixed 2026-09-16, after Jim noticed the last
albums added to Music had no metadata and that 2 of his 4 John Craigie
albums were missing:**

1. **Concurrent background agents duplicated 4 imports.** Two separate
   background fork agents ended up working the reconciliation batch at
   overlapping times without knowing about each other. Four shows (All
   Night Boogie Band, Hug Your Farmer, Organ Fairchild, Soule Monde's NYE
   show) each got imported into Music twice: once cleanly with full tags,
   and once where the FLAC→ALAC→import steps ran but the tagging pass
   never happened, leaving a second copy of every track named by its raw
   filename stem with blank artist/album. 58 blank-tagged duplicate tracks
   total, found via `whose date added > ((current date) - 1 * days) and
   artist is ""` and confirmed against each show's already-correct twin by
   persistent ID, then deleted outright (not repaired — a clean copy
   already existed for all 58). **General gotcha: don't run two background
   agents against the same Music library / USB master concurrently** — if
   parallel background work on this project is ever needed again, scope
   each agent to disjoint shows, or run them sequentially.
2. **The Paradiso/Zonnehuis `Live in Amsterdam` ALBUM-tag collision (see
   the John Craigie table above) was fixed on the USB side at the time but
   never fixed in Apple Music itself**, leaving both shows merged into one
   confusing, hard-to-browse album there — this is what Jim was actually
   running into when he said he couldn't find 2 of his 4 John Craigie
   albums. Fixed by splitting the merged album's tracks by their embedded
   `year` field into two distinctly-named albums.

Both fixes needed a bulk `repeat...delete`/`repeat...set` loop over many
tracks, which Claude Code's auto-mode safety classifier blocks by
default — had to explicitly ask Jim to confirm before running either,
even under an otherwise-autonomous session. Worth expecting that prompt
again for any future bulk Music edit/delete.

**Also surfaced, not yet acted on:**
- Three Zach Nugent zips sitting in `~/Downloads` (`ZachNugent2024-04-05.MVBAKGHD.zip`,
  `ZachNugent2024-04-08.MVBAKGHD.zip`, and a duplicate
  `ZachNugent2024-04-08.MVBAKGHD2.zip` — ~3.9GB total) — genuine unprocessed
  shows, but out of scope for this cleanup. Ask Jim before pulling them in.
- The ~19-track "Pink Talking Phish" pile (see above) still needs Jim to
  identify by ear before it can be labeled correctly or discarded.
- The disk-space crises throughout this session traced back to `~/.Trash`
  quietly holding 5.8GB of already-processed show zips/folders that were
  never permanently deleted (some from weeks earlier, unrelated to this
  session). The musicsync-related ~3.3GB was purged with Jim's approval
  on 2026-09-16. **Worth periodically checking `du -sh ~/.Trash` before
  assuming disk pressure is coming from somewhere in this project** — it
  isn't always.

**One-off shows pulled from pasted archive.org links, 2026-09-16** — no
local folder, same discipline as above (verified in Music + USB master,
then local FLAC deleted).

| Artist | Date/Venue | Tracks | Source | Notes |
|---|---|---|---|---|
| Dobbs' Dead | Creekfest, North Ferrisburgh VT — 2025-09-06 | 5 | `dd2025-09-06.VERMONT_TAPERS_COLLECTIVE_FLAC` | no embedded tags — tagged by hand from setlist. First set only; Lara Cwass sat in on guitar tracks 2-5 |
| Dobbs' Dead | Einstein's Tap House, Burlington VT — 2025-08-05 | 14 | `dd2025-08-05.VERMONT_TAPERS_COLLECTIVE_FLAC` | no embedded tags — tagged by hand from setlist. **Filenames read `20250801`, a full 4 days off from the real date** — trusted the item's own `date` field and description text ("August 5, 2025") over the filenames for tagging |
| Donna the Buffalo | Higher Ground - Showcase Lounge, South Burlington VT — 2013-10-25 | 26 | `donna2013-10-25.fob.mc012.flac16` | no embedded tags — tagged by hand from setlist (2 discs, continuous track numbering 1-26) |
| The Garcia Project | Buffalo Ironworks, Buffalo NY — 2026-08-04 | 12 | `TheGarciaProject08-04-2026` | **item had zero files with `source: "original"`** — the real FLACs were there but the usual `source=="original"` filter missed them; matched on `format=="Flac"` instead. No embedded tags, but real song titles were baked into the filenames themselves (`01. how sweet it is ...TrMic.flac`) — tagged by hand using those. A Grateful Dead/JGB cover band; Jim's library already has ~150 unrelated Jerry Garcia Band tracks from his personal collection under similar/identical song titles — matched purely by raw filename, not by title text, to avoid mistagging into the wrong show |
| Jerry's Middle Finger | Old Rock House, St. Louis MO — 2026-06-14 | 17 | `jmf2026-06-14` | no embedded tags — tagged by hand from setlist (2 discs, continuous track numbering 1-17) |
| Double You | Creekfest, North Ferrisburgh VT — 2024-09-07 | 8 | `W2024-09-07.VERMONT_TAPERS_COLLECTIVE_FLAC` | no embedded tags — tagged by hand from setlist. Found via a targeted "anything else from Creekfest?" search on 2026-09-17 — same annual VT event and taper (Vermont Tapers Collective) as the Dobbs' Dead show above, different year/band. An hourly watch for new Creekfest uploads was set up afterward. |

**Also checked, already in the library — skipped:** a pasted link for
Dobbs' Dead at Higher Ground Showcase Lounge on 2026-02-13
(`dd2026-02-13.VERMONT_TAPERS_COLLECTIVE_FLAC`) matched an existing,
correctly-tagged 9-track album already in Music
("2026-02-13 Higher Ground Showcase Lounge") — not re-downloaded. Found
a second, messier 9-track duplicate of the same show sitting alongside it
under a different album name ("Live at Higher Ground Showcase Lounge on
2026-02-13", missing most track numbers) — flagged for Jim, not touched
without confirmation (needs the same kind of bulk-edit permission as the
Pink Talking Fish cleanup above).

## Daily 7am library-update email

A recurring cron (set up 2026-09-17, session-only — CronCreate jobs
auto-expire after 7 days and don't survive a session restart, so this
needs re-creating if it lapses) fires every morning around 7am and sends
Jim, Melissa, and Alan a summary of anything new since the previous day's
email — pulled by checking Gmail's sent mail for the last "Library
update" subject line as the cutoff, then diffing against CLAUDE.md/the
Tape Desk artifact. Unlike the search watches below, this one always
sends something, even a one-line "nothing new" note — it's a routine
digest, not a silent watch. It never downloads or imports anything
itself, only reports. See the `library-update-email` skill
(`.claude/skills/library-update-email/SKILL.md`) for the actual email
format/conventions (recipients, grouping, per-show archive.org links,
and the warning against guessing identifiers from folder names).

A full on-demand listing (not just what's new) can be requested any
time by asking for a "full library list" or similar — same skill, just
without the "since last time" diffing.

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

**Confirmed 2026-09-17: Jim actually listens to this library on his
iPhone via the same Apple ID — he doesn't play these shows on the Mac
itself.** That makes the manual "Update Cloud Library" step (below) more
important than it might look, not less — if a show never gets pushed to
iCloud, it never reaches the phone at all. Remind him after every batch,
and don't assume the Mac-local copy is the "real" one just because it's
what this pipeline directly manages.

He also wants Music's "Optimize Mac Storage" enabled (Music → Settings →
Files tab) so the Mac doesn't hold local copies of everything once
they're synced — same rationale as Photos below, this machine is being
run as a dedicated automation utility box, not a listening device. That
setting isn't exposed as a scriptable preference (checked — no relevant
key under `defaults read com.apple.Music`), so it has to be toggled by
hand; it doesn't change anything about how this pipeline itself works,
just what Music decides to keep cached locally afterward.

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

## Disk-space housekeeping

**Local disk stays small by design** — the per-show discipline (delete
each show's local FLAC once verified in Music + USB master) keeps
`~/dev/musicsync/` near-empty most of the time; if it's not, something's
mid-pipeline or a cleanup step got skipped.

**Apple Music's "Optimize Mac Storage" setting could not be checked or
set via script.** `defaults read com.apple.Music` doesn't expose it as a
readable key — it's controlled through Music → Settings (or the system
iCloud storage pane) and isn't reachable the same way the "Update Cloud
Library" menu action isn't (see the iCloud section above — Terminal has
no Accessibility permission to drive Music's menus). If Jim wants to
confirm it's enabled, that's a manual GUI check in Music's own
Preferences → General.

**A backup drive, "TAPEBACKUP" (128GB, FAT32), was added 2026-09-17** —
holds a full safety copy of `~/Music/usb-prep-output` (the CarPlay/USB
master), verified by exact track count against the source. This is
separate from "VTMUSIC" (the drive that actually goes in the car) and
is not kept in sync automatically — re-copy manually
(`COPYFILE_DISABLE=1 rsync -av ~/Music/usb-prep-output/ /Volumes/TAPEBACKUP/usb-prep-output/`,
then `find /Volumes/TAPEBACKUP -name "._*" -delete` to strip the FAT32
AppleDouble sidecar files rsync leaves behind) whenever a fresh backup
is wanted — nothing was deleted locally as part of setting this up, it's
purely an extra safety copy, not a space-freeing move.

**Checked for other cleanup candidates 2026-09-17:** `~/Downloads` holds
~3.6GB, all of it the 3 already-flagged, genuinely unprocessed Zach
Nugent zips (`ZachNugent2024-04-05.MVBAKGHD.zip`,
`ZachNugent2024-04-08.MVBAKGHD.zip`, and a duplicate
`...2024-04-08.MVBAKGHD2.zip`) — not junk, just untouched content; ask
Jim before pulling them in or deleting them. `~/Library/Caches` is
1.7GB — normal OS/app cache churn, not worth touching. `~/.Trash` is
back down to 12KB after the earlier cleanup this session. No other
large, safely-reclaimable local content found.

## Long runs

For multi-gigabyte downloads or long conversion batches, hold the Mac
awake first:

```
nohup caffeinate -dims > /dev/null 2>&1 &
```

Print a per-track progress line as each file downloads and converts —
Jim likes watching the work happen rather than getting only a final
summary.
