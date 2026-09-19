// List tracks added in the last N days (default 2) with the fields needed to match them to source files.
// Music renames files by title on import ("01 track01.m4a"), so match by DURATION, not file name.
// Resolve persistent IDs once, BEFORE any tag edits: Music relocates files the instant tags change (see CLAUDE.md).
// Run: osascript -l JavaScript resolve_ids.js [days]
function run(argv) {
  const days = Number(argv[0] || 2);
  const tr = Application("Music").playlists.byName("Library").tracks;
  const cutoff = new Date(Date.now() - days * 86400000);
  const added = tr.dateAdded(), pid = tr.persistentID(), name = tr.name(), artist = tr.artist(),
        album = tr.album(), dur = tr.duration(), num = tr.trackNumber();
  const out = [];
  for (let i = 0; i < added.length; i++)
    if (added[i] >= cutoff) out.push({ pid: pid[i], name: name[i], artist: artist[i], album: album[i], dur: dur[i], num: num[i] });
  return JSON.stringify(out);
}
