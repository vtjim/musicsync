(function () {
  const $ = id => document.getElementById(id);
  const n0 = x => Math.round(x).toLocaleString();
  const n1 = x => x.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const NS = "http://www.w3.org/2000/svg";
  const el = (tag, attrs, text) => {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (text != null) e.textContent = text;
    return e;
  };
  const D = DATA, M = D.music, MS = D.master, DK = D.disk;

  // refreshed stamp
  const gen = new Date(D.generated);
  $("refreshed-at").textContent = gen.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) +
    " · " + gen.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });

  // tiles
  const tiles = [
    [D.sets ? n0(D.sets) : "—", "sets in the library, each linked from the public Setlist Ledger"],
    [n0(M.tracks), "tracks in Music since Aug 25 · <b>" + n0(M.lossless_tracks) + "</b> lossless"],
    [n0(M.hours) + "<small> h</small>", "of music · about " + n1(M.hours / 24) + " days nonstop"],
    [n0(MS.tracks), "tracks in the USB master · " + n0(MS.hours) + " h · " + n1(MS.gb) + " GB of MP3"],
    [n1(DK.free_gb) + "<small> GB</small>", "free on the Mac · " + Math.round(DK.used_gb / DK.total_gb * 100) + "% of " + n0(DK.total_gb) + " GB used"],
  ];
  $("tiles").innerHTML = tiles.map(t => '<div class="stat"><span class="n">' + t[0] + '</span><span class="l">' + t[1] + '</span></div>').join("");

  // disk bar
  const lib = M.local_gb, usb = MS.gb, scratch = D.scratch_gb;
  const other = Math.max(0, DK.used_gb - lib - usb - scratch);
  const segs = [
    ["seg-lib", lib, "Taper library in Music, on disk", n0(M.local_tracks) + " tracks kept locally"],
    ["seg-usb", usb, "USB master (MP3)", n0(MS.tracks) + " tracks in ~/Music/usb-prep-output"],
    ["seg-scratch", scratch, "Import scratch", "downloaded FLAC and converted ALAC, cleared after each show verifies"],
    ["seg-other", other, "Everything else", "macOS, apps, and the rest of your own Music library"],
    ["seg-free", DK.free_gb, "Free", n1(DK.free_gb / DK.total_gb * 100) + "% of the disk"],
  ];
  $("disk-title").textContent = n1(DK.free_gb) + " GB free of " + n0(DK.total_gb) + " GB";
  $("disk-note").textContent = "Data volume, measured " + gen.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  $("diskbar").innerHTML = segs.map(s => '<div class="' + s[0] + '" style="width:' + (s[1] / DK.total_gb * 100) + '%" title="' + s[2] + ': ' + n1(s[1]) + ' GB"></div>').join("");
  $("disk-legend").innerHTML = segs.map(s =>
    '<div class="k"><span class="sw ' + s[0] + '"></span><span><span>' + s[2] + '</span><span class="d">' + s[3] + '</span></span><span class="v">' + (s[1] < 0.05 ? "&lt; 0.1" : n1(s[1])) + ' GB</span></div>').join("") +
    '<div class="k"><span class="sw" style="background:transparent;border-style:dashed"></span><span><span>Only in iCloud</span><span class="d">' + n0(M.cloud_only_tracks) + ' tracks that take no disk here (Optimize Storage)</span></span><span class="v">' + n1(M.cloud_only_gb) + ' GB</span></div>';

  // drives
  const dr = D.drives || {};
  const tb = dr.tapebackup, behind = MS.tracks - 1298;
  $("drives").innerHTML =
    '<div class="drive"><b>TAPEBACKUP</b>' + (tb ? '<span class="st on">connected</span>' : '<span class="st off">not connected</span>') +
    '<p>' + (tb ? n1(tb.used_gb) + ' of ' + n0(tb.total_gb) + ' GB used. Full mirror of the USB master, checked track for track (' + n0(MS.tracks) + ' = ' + n0(MS.tracks) + ').' : 'Plug in to refresh the backup.') + '</p></div>' +
    '<div class="drive"><b>VTMUSIC</b>' + (dr.vtmusic ? '<span class="st on">connected</span>' : '<span class="st off">not connected</span>') +
    '<p>' + (dr.vtmusic ? 'Car stick attached.' : 'The car stick. It last synced at 1,298 tracks, so it needs ' + n0(behind) + ' more (Snugfest 2026 and North Mississippi Allstars) the next time it is plugged in.') + '</p></div>';

  // additions timeline
  const tl = D.timeline;
  if (tl.length) {
    const svg = $("tl-chart"), W = 760, H = 250, L = 40, R = 46, T = 16, B = 34;
    const day = s => Date.parse(s + "T12:00:00");
    const t0 = day(tl[0].day), t1 = day(tl[tl.length - 1].day), DAY = 86400000;
    const ndays = Math.round((t1 - t0) / DAY) + 1;
    const maxT = Math.max(...tl.map(d => d.tracks)), yMaxT = Math.ceil(maxT / 100) * 100;
    const maxH = tl[tl.length - 1].cum_hours, yMaxH = Math.ceil(maxH / 50) * 50;
    const pw = W - L - R, ph = H - T - B, bw = Math.max(3, pw / ndays * 0.72);
    const x = i => L + (i + 0.5) * pw / ndays;
    const yT = v => T + ph - v / yMaxT * ph, yH = v => T + ph - v / yMaxH * ph;
    for (let g = 0; g <= 4; g++) {
      const y = T + ph - g / 4 * ph;
      svg.appendChild(el("line", { x1: L, x2: W - R, y1: y, y2: y, class: g ? "grid" : "axis" }));
      svg.appendChild(el("text", { x: L - 6, y: y + 3.5, "text-anchor": "end" }, n0(g / 4 * yMaxT)));
      svg.appendChild(el("text", { x: W - R + 6, y: y + 3.5 }, n0(g / 4 * yMaxH) + " h"));
    }
    const byIdx = {};
    tl.forEach(d => { byIdx[Math.round((day(d.day) - t0) / DAY)] = d; });
    Object.keys(byIdx).forEach(i => {
      const d = byIdx[i], h = d.tracks / yMaxT * ph;
      const r = el("rect", { x: x(+i) - bw / 2, y: T + ph - h, width: bw, height: h, rx: 1.5, class: "bar" });
      r.appendChild(el("title", {}, d.day + ": " + d.tracks + " tracks, " + n1(d.hours) + " h"));
      svg.appendChild(r);
    });
    // cumulative line over every calendar day
    let last = 0, pts = [];
    for (let i = 0; i < ndays; i++) { if (byIdx[i]) last = byIdx[i].cum_hours; pts.push([x(i), yH(last)]); }
    svg.appendChild(el("polyline", { points: pts.map(p => p.join(",")).join(" "), class: "line" }));
    const lp = pts[pts.length - 1];
    svg.appendChild(el("circle", { cx: lp[0], cy: lp[1], r: 4, class: "dotm" }));
    svg.appendChild(el("text", { x: lp[0] - 8, y: lp[1] - 9, "text-anchor": "end", class: "lbl-end" }, n1(maxH) + " h"));
    const step = ndays > 18 ? 3 : ndays > 9 ? 2 : 1;
    for (let i = 0; i < ndays; i += step) {
      const d = new Date(t0 + i * DAY);
      svg.appendChild(el("text", { x: x(i), y: H - 12, "text-anchor": "middle" }, d.toLocaleDateString(undefined, { month: "short", day: "numeric" })));
    }
    $("tl-note").textContent = n0(M.tracks) + " tracks · " + tl[0].day.slice(5) + " to " + tl[tl.length - 1].day.slice(5);
  }

  // free-space history: reported points from earlier sessions + measured snapshots
  const reported = [["2026-09-15T18:00", 1.2], ["2026-09-16T12:00", 10]];
  const pts = reported.map(r => ({ t: Date.parse(r[0]), v: r[1], r: 1 })).concat(
    D.snapshots.map(s => ({ t: Date.parse(s.ts), v: s.free_gb, r: 0 }))).sort((a, b) => a.t - b.t);
  const fs = $("free-chart"), W2 = 760, H2 = 200, L2 = 40, R2 = 30, T2 = 16, B2 = 30;
  const ta = pts[0].t, tb2 = pts[pts.length - 1].t, span = Math.max(tb2 - ta, 1);
  const yMax = Math.ceil(Math.max(...pts.map(p => p.v)) * 1.15 / 20) * 20;
  const fx = t => L2 + (t - ta) / span * (W2 - L2 - R2), fy = v => T2 + (H2 - T2 - B2) * (1 - v / yMax);
  for (let g = 0; g <= 4; g++) {
    const y = T2 + (H2 - T2 - B2) * (1 - g / 4);
    fs.appendChild(el("line", { x1: L2, x2: W2 - R2, y1: y, y2: y, class: g ? "grid" : "axis" }));
    fs.appendChild(el("text", { x: L2 - 6, y: y + 3.5, "text-anchor": "end" }, n0(g / 4 * yMax)));
  }
  fs.appendChild(el("polyline", { points: pts.map(p => fx(p.t) + "," + fy(p.v)).join(" "), class: "line", style: "stroke:var(--wait)" }));
  pts.forEach((p, i) => {
    const c = el("circle", { cx: fx(p.t), cy: fy(p.v), r: 4.5, class: p.r ? "dotr" : "dotm", style: p.r ? "" : "fill:var(--wait)" });
    c.appendChild(el("title", {}, new Date(p.t).toLocaleDateString() + ": " + n1(p.v) + " GB free" + (p.r ? " (reported)" : "")));
    fs.appendChild(c);
    if (i === 0 || i === pts.length - 1)
      fs.appendChild(el("text", { x: fx(p.t) + (i === pts.length - 1 ? -8 : 8), y: fy(p.v) - 9, "text-anchor": i === pts.length - 1 ? "end" : "start", class: "lbl-end" }, n1(p.v) + " GB"));
  });
  [pts[0], pts[pts.length - 1]].forEach((p, i) =>
    fs.appendChild(el("text", { x: fx(p.t), y: H2 - 8, "text-anchor": i ? "end" : "start" },
      new Date(p.t).toLocaleDateString(undefined, { month: "short", day: "numeric" }))));
})();
