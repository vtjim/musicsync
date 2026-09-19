// Dump per-track facts from Music.app as JSON (JXA). Bulk property reads, fast even for large libraries.
// Run: osascript -l JavaScript music_dump.js > music_dump.json
// Row: [dateAdded, seconds, bytes, artist, album, kind, isLocal(1/0), cloudStatus]
const M = Application("Music");
const tr = M.playlists.byName("Library").tracks;
const since = new Date(2026, 7, 25); // taper project start: Aug 25 2026 (month is 0-based)
const added = tr.dateAdded();
const idx = [];
for (let i = 0; i < added.length; i++) if (added[i] >= since) idx.push(i);
const dur = tr.duration(), size = tr.size(), alb = tr.album(), art = tr.artist(),
      kind = tr.kind(), cs = tr.cloudStatus();
// Bulk location() throws when any track is cloud-only, so read it per matching track.
const isLocal = i => { try { return tr[i].location() ? 1 : 0; } catch (e) { return 0; } };
const ymd = d => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
JSON.stringify({
  total_library_tracks: added.length,
  rows: idx.map(i => [ymd(added[i]), Math.round(dur[i]), size[i], art[i], alb[i], kind[i], isLocal(i), String(cs[i])])
});
