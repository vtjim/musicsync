# Library update email

Jim asks for this "from time to time" — an organized summary of what's in
the musicsync live-recording library, emailed to him and Melissa.

## Recipients

- `jim.silvia@gmail.com`
- `mjlevy718@gmail.com` (Melissa — confirmed 2026-09-14: she's cc'd on his
  recurring "Reels, Riffs & Ridgelines" digest and appears as "Melissa
  Smith" in his Venmo history. Don't re-ask each time; only re-confirm if
  a send ever bounces or Jim gives a different address.)

## What to include

1. **Totals up top**: shows in the catalog, tracks in Apple Music, tracks
   on the vtMusic/CarPlay USB drive. Pull current numbers from the Tape
   Desk artifact (https://claude.ai/code/artifact/d515b1da-20e9-424d-8f4f-0cbb74a6c498)
   or CLAUDE.md's inventory tables — read one back first rather than
   guessing at stale numbers.
2. **Grouped by festival/collection/series**, not one flat list — Dead of
   Summer, Adirondack Fest, JRAD, Snugfest, Lara Cwass Band, Dobbs' Dead,
   one-off finds, etc., matching the groupings already used in CLAUDE.md's
   "What's in the library" section.
3. **Per-show line**: artist, date/venue, track count.
4. **An archive.org link for every show**, so Melissa (or anyone remote
   from Jim) can stream or download the source recording on their own
   without needing anything from Jim's Mac or Apple Music/iCloud. Link
   format: `https://archive.org/details/<identifier>`.

## Getting the archive.org identifier right

CLAUDE.md's inventory tables record the *local folder name*, and by this
project's own convention (see CLAUDE.md's "Extract" step) dots in the
original archive.org identifier get replaced with underscores when
naming that folder. **The folder name is therefore often NOT the real
identifier** — `moe2026-09-04_Adirondack_Fest` as a folder name does not
mean the identifier is `moe2026-09-04.Adirondack_Fest`; the real one
turned out to be plain `moe2026-09-04`, and a same-day JRAD show's folder
`jrad2026-08-22_jazzbuph` was actually identifier `jrad2026-08-22.-jazzbuph`
(note the extra hyphen — not reconstructable by guessing).

Where CLAUDE.md's own "Source" column already gives a dotted identifier
(most one-off/pasted-link shows do), trust it directly. For anything
where only a folder name is on record, **don't guess-convert underscores
back to dots** — verify first:

```bash
# Quick existence check for a candidate identifier:
curl -s "https://archive.org/metadata/<candidate>" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print('OK' if d.get('metadata') else 'MISSING')"

# If that's MISSING, search by creator + narrow date range instead —
# this is the reliable path, not guessing at punctuation:
curl -s "https://archive.org/advancedsearch.php?q=collection%3Aetree+AND+\
creator%3A%28<Artist+Name>%29+AND+date%3A%5B<start>+TO+<end>%5D\
&fl%5B%5D=identifier&fl%5B%5D=date&fl%5B%5D=title&rows=10&output=json"
```

Match on venue/date text in the returned `title` field to pick the right
one when a search returns several tapes of the same show (matrix vs SBD
vs AUD) — prefer whichever one this project actually imported (check
CLAUDE.md's per-show notes for taper name or recording type to disambiguate).

A wrong or missing link is worse than a short delay to verify — don't
publish a guessed identifier in an email that goes out to someone who
might actually click it.

## Sending

Use the Gmail tools: `create_draft` (to review the HTML) or
`send_message` directly. `mcp__claude_ai_Gmail__search_threads` is
useful up front only if Melissa's address ever needs re-confirming.

Past subject line style: "Live music library — what's in it now (N shows)".
Keep the tone the same as that first email — plain organized HTML, short
intro line, `<h3>` per collection, a bulleted per-show list, totals
called out at the top, and a closing note on any active watches/searches
still running.
