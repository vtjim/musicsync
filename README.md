# musicsync

A personal pipeline for archiving live-taper concert recordings — mostly
Vermont's jam-band scene, plus touring bands whenever a good taper
release turns up on [archive.org](https://archive.org). It pulls FLAC
masters from archive.org, converts them to Apple Lossless (ALAC) for a
local Apple Music library, and mirrors a 320kbps MP3 copy for a CarPlay
USB drive — so the same show is available both as a lossless library
track and as something a car head unit can just read off a stick.

**Browse the catalog:** the running list of everything collected is a
searchable, filterable page — **[vtjim.github.io/setlist-ledger](https://vtjim.github.io/setlist-ledger/)**
— every show links straight back to its archive.org source.

## How it works

1. **Find the source.** A show gets added either by searching
   archive.org for a specific festival/artist/date, or from a
   `/details/<identifier>` link pasted in directly. A handful of
   recurring searches also run on a schedule, watching for new uploads
   from specific tapers or festivals.
2. **Pull the real metadata.** archive.org's own `/metadata/<identifier>`
   JSON is the source of truth for title, date, venue, and track titles
   — not the page itself, which can summarize things inaccurately.
3. **Download the FLACs**, verifying each file's size against the
   archive.org manifest as it comes down.
4. **Convert to ALAC** with [XLD](https://tmkk.undo.jp/xld/index_e.html)
   and import into Apple Music. Many taper releases (especially
   Vermont Tapers Collective recordings) carry no embedded tags at all,
   so titles often get filled in by hand from the item's own setlist
   text.
5. **Mirror to a CarPlay master** — the same show gets converted again,
   this time to 320kbps MP3, tagged, and organized into an
   `Artist/Album/NN - Title.mp3` tree that syncs onto a FAT32 USB drive.
6. **Verify, then clean up.** Once a show is confirmed present in both
   Apple Music and the USB master, the local FLAC master gets deleted —
   it can always be re-pulled from archive.org later if needed.

## What's in this repo

- **`CLAUDE.md`** — the full operational playbook: every gotcha,
  workaround, and convention discovered while building this out (XLD
  quirks, Apple Music's AppleScript automation pitfalls, archive.org
  metadata edge cases, disk-space discipline, and so on). It's written
  for an AI coding agent to pick up and run the pipeline autonomously,
  but it's also just a fairly detailed log of how the whole thing
  actually works.
- **`.claude/skills/`** — reusable task definitions the agent follows
  for specific recurring jobs (importing a show end-to-end, sending a
  library-update email).

## A note on privacy

This repo is public, but the actual library — the audio, the Apple
Music database, the local file paths — lives only on the machine this
runs on. Nothing here is a substitute for the archive.org sources
themselves, which is exactly why every entry in the catalog links back
to one.
