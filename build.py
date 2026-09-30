#!/usr/bin/env python3
"""
build.py - turn data/items.json into a single self-contained public/index.html.

The page carries its own data, so it works anywhere: opened from disk, served by
GitHub Pages, or published as an artifact. No build step, no server, no deps.

Everything you would want to change by hand is in PROFILE below.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
# GitHub Pages serves from the repository root or from /docs, and /docs keeps
# the source files out of the published site. Hence the name.
PUBLIC = ROOT / "docs"

PROFILE = {
    "name": "Sean Speer",
    "tagline": "The political economy of Canada and the United States.",
    "bio": "Co-founder and editor-at-large at The Hub. Writer at the Manhattan "
           "Institute. Former senior economic adviser to the prime minister.",

    # Leave any of these empty and the page simply omits them.
    "photo": "portrait.jpg",        # sits next to index.html in docs/
    # Addresses are shown as selectable text with a copy button rather than
    # mailto: links, which are unreliable and hand the address to scrapers.
    "emails": [
        {"label": "The Hub", "address": "sean@thehub.ca"},
        {"label": "Manhattan Institute", "address": "sspeer@manhattan.institute"},
    ],
    "email_note": "Editors and speaking enquiries",
    "socials": [{"label": "@sean_speer", "url": "https://x.com/sean_speer"}],

    "links": [
        {"label": "The Hub", "url": "https://thehub.ca/"},
        {"label": "Manhattan Institute", "url": "https://manhattan.institute/person/sean-speer"},
    ],

    # URLs of the pieces to feature, in the order they should appear.
    "featured": [
        "https://www.city-journal.org/article/uaw-union-universities-politics",
        "https://thehub.ca/2025/10/23/in-defence-of-ronald-reagan/",
        "https://www.city-journal.org/article/messy-jobs-work-ai-cannot-reach",
        "https://thehub.ca/2026/06/26/the-politics-of-transgression-versus-the-politics-of-normalcy/",
        "https://thehub.ca/2025/08/09/sean-speer-two-cheers-for-neoliberalism-and-none-for-economic-nationalism/",
    ],
}

# Recurring work is shown as a role, and its individual episodes are kept out of
# the archive list: 950 near-identical rows would bury everything else.
COLLAPSE_SERIES_OF_TYPE = {"podcast"}

TEMPLATE = """<title>__NAME__</title>
<style>
  /* Layout: a masthead and roles above a filterable, year-banded archive */
  :root {
    --paper:#f7f6f4; --card:#ffffff; --ink:#15181c; --ink-soft:#575f68;
    --ink-faint:#8a8f96; --rule:#e0ddd8; --accent:#1c3d5a; --accent-bg:#e7edf3;
    /* one hue per kind of work, so the archive reads at a glance */
    --c-write:#1c3d5a; --c-write-bg:#e7edf3;
    --c-pod:#0c5b52;   --c-pod-bg:#dfeeea;
    --c-talk:#8a5310;  --c-talk-bg:#f6ecd9;
    --font-display:"Newsreader", Georgia, "Times New Roman", serif;
    --font-ui:"IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --paper:#101215; --card:#171a1f; --ink:#e8e9ea; --ink-soft:#9aa0a8;
      --ink-faint:#6e747c; --rule:#262a30; --accent:#8bb6dd; --accent-bg:#18242f;
      --c-write:#8bb6dd; --c-write-bg:#18242f;
      --c-pod:#6ec7b9;   --c-pod-bg:#132724;
      --c-talk:#dca95c;  --c-talk-bg:#2a2317;
      color-scheme: dark;
    }
  }
  :root[data-theme="dark"] {
    --paper:#101215; --card:#171a1f; --ink:#e8e9ea; --ink-soft:#9aa0a8;
    --ink-faint:#6e747c; --rule:#262a30; --accent:#8bb6dd; --accent-bg:#18242f;
    --c-write:#8bb6dd; --c-write-bg:#18242f;
    --c-pod:#6ec7b9;   --c-pod-bg:#132724;
    --c-talk:#dca95c;  --c-talk-bg:#2a2317;
    color-scheme: dark;
  }

  * { box-sizing:border-box; }
  body { margin:0; background:var(--paper); color:var(--ink);
         font-family:var(--font-ui); font-size:16px; line-height:1.55;
         -webkit-font-smoothing:antialiased; }
  .wrap { max-width:880px; margin:0 auto; padding-inline:20px; padding-block:56px 80px; }
  a { color:var(--accent); }

  /* masthead */
  .mast { display:flex; gap:28px; align-items:flex-start; flex-wrap:wrap;
          border-bottom:2px solid var(--ink); padding-bottom:30px; }
  /* a square source image, shown square with softened corners */
  .portrait { width:148px; aspect-ratio:1/1; border-radius:10px; object-fit:cover;
              flex:0 0 auto; background:var(--accent-bg); max-width:100%; }
  .mast-body { flex:1 1 320px; min-width:0; }
  h1 { font-family:var(--font-display); font-weight:600; font-size:clamp(34px,6vw,52px);
       letter-spacing:-0.02em; line-height:1.04; margin:0 0 10px; text-wrap:balance; }
  .tagline { font-family:var(--font-display); font-size:19px; color:var(--ink-soft);
             margin:0 0 14px; text-wrap:balance; }
  .bio { color:var(--ink-soft); max-width:62ch; font-size:15.5px; margin:0 0 16px; }
  .chips { display:flex; flex-wrap:wrap; gap:8px 18px; font-size:14px; align-items:center; }
  .chips a { text-decoration:none; border-bottom:1px solid transparent; }
  .chips a:hover, .chips a:focus-visible { border-bottom-color:var(--accent); }
  .contact { margin-top:16px; }
  .contact .note { font-size:12px; letter-spacing:.07em; text-transform:uppercase;
                   color:var(--ink-faint); margin-bottom:7px; }
  .mailrow { display:flex; align-items:center; gap:8px; flex-wrap:wrap;
             margin-bottom:6px; font-size:14px; color:var(--ink-soft); }
  .mailrow > span:first-child { min-width:132px; }
  .mailrow code { font-family:var(--font-ui); background:var(--accent-bg);
                  color:var(--accent); padding:3px 9px; border-radius:5px; user-select:all; }
  .mailrow button { font:inherit; font-size:12.5px; padding:4px 10px; border-radius:6px;
                    border:1px solid var(--rule); background:var(--card);
                    color:var(--ink-soft); cursor:pointer; }
  .ok { color:#15803d; font-size:12px; }

  h2 { font-family:var(--font-display); font-size:13px; font-weight:600; letter-spacing:.14em;
       text-transform:uppercase; color:var(--ink-faint); margin:42px 0 12px; }

  /* roles */
  .roles { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:1px;
           background:var(--rule); border:1px solid var(--rule); border-radius:10px; overflow:hidden; }
  .role { background:var(--card); padding:15px 17px; }
  .role .n { font-family:var(--font-display); font-size:27px; font-weight:600; line-height:1;
             font-variant-numeric:tabular-nums; color:var(--c-write); }
  .role.t-podcast .n { color:var(--c-pod); }
  .role.t-video .n   { color:var(--c-talk); }
  .role .t { margin-top:5px; font-size:14.5px; font-weight:500; }
  .role .s { margin-top:2px; font-size:12.5px; color:var(--ink-faint);
             font-variant-numeric:tabular-nums; }

  /* featured */
  .feat { display:grid; grid-template-columns:repeat(auto-fit,minmax(255px,1fr)); gap:16px; }
  .fcard { background:var(--card); border:1px solid var(--rule); border-radius:10px;
           padding:16px 17px; display:flex; flex-direction:column; gap:7px; min-width:0; }
  .fcard .o { font-size:11px; letter-spacing:.07em; text-transform:uppercase; color:var(--accent); }
  .fcard a { font-family:var(--font-display); font-size:17.5px; font-weight:500;
             line-height:1.3; color:var(--ink); text-decoration:none; }
  .fcard a:hover, .fcard a:focus-visible { color:var(--accent); }
  .fcard .d { font-size:12.5px; color:var(--ink-faint); font-variant-numeric:tabular-nums;
              margin-top:auto; }

  /* archive */
  .controls { position:sticky; top:env(safe-area-inset-top,0px); z-index:5;
              background:var(--paper); border-bottom:1px solid var(--rule);
              padding-block:14px; display:flex; flex-wrap:wrap; gap:10px; align-items:center; }
  .seg { display:flex; border:1px solid var(--rule); border-radius:7px; overflow:hidden; }
  .seg button { font:inherit; font-size:13.5px; padding:7px 14px; border:0; cursor:pointer;
                background:var(--card); color:var(--ink-soft); border-right:1px solid var(--rule); }
  .seg button:last-child { border-right:0; }
  .seg button[aria-pressed="true"] { background:var(--accent); color:#fff; }
  select, input[type="search"] { font:inherit; font-size:13.5px; padding:7px 10px;
    border-radius:7px; border:1px solid var(--rule); background:var(--card); color:var(--ink); min-width:0; }
  input[type="search"] { flex:1 1 180px; }
  select { max-width:200px; }
  .count { margin-left:auto; font-size:13px; color:var(--ink-faint); font-variant-numeric:tabular-nums; }

  .year { font-family:var(--font-display); font-size:13px; font-weight:600; letter-spacing:.14em;
          text-transform:uppercase; color:var(--ink-faint); padding:28px 0 8px;
          border-bottom:1px solid var(--rule); font-variant-numeric:tabular-nums; }
  ol { list-style:none; margin:0; padding:0; }
  li.item { display:grid; grid-template-columns:78px 1fr; gap:4px 18px; padding:14px 0;
            border-bottom:1px solid var(--rule); align-items:baseline; }
  .date { font-size:12.5px; color:var(--ink-faint); font-variant-numeric:tabular-nums; white-space:nowrap; }
  .body { min-width:0; }
  .title { font-family:var(--font-display); font-size:18px; font-weight:500; line-height:1.32;
           color:var(--ink); text-decoration:none; display:inline-block; border-bottom:1px solid transparent; }
  a.title:hover, a.title:focus-visible { color:var(--accent); border-bottom-color:var(--accent); }
  .title.nolink { color:var(--ink-soft); cursor:default; }
  .meta { margin-top:3px; font-size:13px; color:var(--ink-soft);
          display:flex; flex-wrap:wrap; gap:8px; align-items:center; }
  .tag { font-size:11px; letter-spacing:.06em; text-transform:uppercase; padding:2px 7px;
         border-radius:4px; background:var(--accent-bg); color:var(--accent); white-space:nowrap; }
  .tag.t-article { background:var(--c-write-bg); color:var(--c-write); }
  .tag.t-podcast { background:var(--c-pod-bg);   color:var(--c-pod); }
  .tag.t-video   { background:var(--c-talk-bg);  color:var(--c-talk); }
  .with { color:var(--ink-faint); font-style:italic; }
  .empty { padding:44px 0; text-align:center; color:var(--ink-faint); }
  footer { margin-top:46px; padding-top:18px; border-top:1px solid var(--rule);
           font-size:12.5px; color:var(--ink-faint); display:flex; flex-wrap:wrap; gap:12px; }

  @media (max-width:560px) {
    li.item { grid-template-columns:1fr; gap:3px; }
    .date { order:2; }
    .wrap { padding-block:34px 60px; }
    .count { width:100%; margin-left:0; }
    .portrait { width:104px; }
  }
  @media (prefers-reduced-motion:reduce) { * { transition:none !important; } }
</style>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&family=IBM+Plex+Sans:wght@400;500&display=swap">

<div class="wrap">
  <div class="mast">
    __PORTRAIT__
    <div class="mast-body">
      <h1>__NAME__</h1>
      <p class="tagline">__TAGLINE__</p>
      <p class="bio">__BIO__</p>
      <div class="chips">__LINKS__</div>
      __CONTACT__
    </div>
  </div>

  __ROLES__
  __FEATURED__

  <h2>Archive</h2>
  <div class="controls">
    <div class="seg" role="group" aria-label="Filter by type">
      <button aria-pressed="true"  data-type="">All</button>
      <button aria-pressed="false" data-type="article">Writing</button>
      <button aria-pressed="false" data-type="podcast">Podcasts</button>
      <button aria-pressed="false" data-type="video">Talks</button>
    </div>
    <select id="outlet" aria-label="Filter by outlet"></select>
    <input id="q" type="search" placeholder="Search titles" aria-label="Search titles">
    <span class="count" id="count"></span>
  </div>
  <div id="list"></div>

  <footer>
    <span>__TOTAL__ items, __RANGE__.</span>
    <span>Updated __GENERATED__.</span>
  </footer>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  var items = JSON.parse(document.getElementById('data').textContent);
  var listEl = document.getElementById('list');
  var countEl = document.getElementById('count');
  var qEl = document.getElementById('q');
  var outletEl = document.getElementById('outlet');
  var segBtns = Array.prototype.slice.call(document.querySelectorAll('.seg button'));
  var state = { type: '', outlet: '', q: '' };
  var LABEL = { article: 'Writing', podcast: 'Podcast', video: 'Talk' };

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function fmtDate(d) {
    if (!d) return '';
    var p = d.split('-');
    var M = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return (M[parseInt(p[1], 10) - 1] || '') + ' ' + parseInt(p[2], 10);
  }

  var outlets = {};
  items.forEach(function (it) { outlets[it.outlet] = (outlets[it.outlet] || 0) + 1; });
  outletEl.innerHTML = '<option value="">All outlets</option>' +
    Object.keys(outlets).sort(function (a, b) { return outlets[b] - outlets[a]; })
      .map(function (n) {
        return '<option value="' + esc(n) + '">' + esc(n) + ' (' + outlets[n] + ')</option>';
      }).join('');

  function render() {
    var q = state.q.trim().toLowerCase();
    var shown = items.filter(function (it) {
      if (state.type && it.type !== state.type) return false;
      if (state.outlet && it.outlet !== state.outlet) return false;
      if (q && (it.title || '').toLowerCase().indexOf(q) === -1 &&
               (it.outlet || '').toLowerCase().indexOf(q) === -1) return false;
      return true;
    });
    countEl.textContent = shown.length + (shown.length === 1 ? ' item' : ' items');
    if (!shown.length) { listEl.innerHTML = '<p class="empty">Nothing matches that.</p>'; return; }

    var html = '', year = null;
    shown.forEach(function (it) {
      var y = (it.date || '').slice(0, 4);
      if (y !== year) {
        if (year !== null) html += '</ol>';
        html += '<div class="year">' + esc(y || 'Undated') + '</div><ol>';
        year = y;
      }
      var withWhom = '';
      if (it.coauthored && it.byline) {
        var others = it.byline.split(/,| and /).map(function (s) { return s.trim(); })
                       .filter(function (s) { return s && s.toLowerCase().indexOf('speer') === -1; });
        if (others.length) withWhom = '<span class="with">with ' + esc(others.join(', ')) + '</span>';
      }
      html += '<li class="item"><span class="date">' + esc(fmtDate(it.date)) + '</span>' +
              '<div class="body">' +
                (it.url ? '<a class="title" href="' + esc(it.url) + '" target="_blank" rel="noopener">' +
                            esc(it.title) + '</a>'
                        : '<span class="title nolink">' + esc(it.title) + '</span>') +
                '<div class="meta"><span class="tag t-' + esc(it.type) + '">' +
                    (LABEL[it.type] || 'Item') + '</span>' +
                  '<span>' + esc(it.outlet) + '</span>' + withWhom + '</div>' +
              '</div></li>';
    });
    listEl.innerHTML = html + '</ol>';
  }

  segBtns.forEach(function (b) {
    b.addEventListener('click', function () {
      state.type = b.dataset.type;
      segBtns.forEach(function (o) { o.setAttribute('aria-pressed', String(o === b)); });
      render();
    });
  });
  outletEl.addEventListener('change', function () { state.outlet = outletEl.value; render(); });
  qEl.addEventListener('input', function () { state.q = qEl.value; render(); });
  render();

  Array.prototype.forEach.call(document.querySelectorAll('.copymail'), function (btn) {
    btn.addEventListener('click', function () {
      var note = btn.nextElementSibling;
      var code = btn.previousElementSibling;
      function done() {
        note.textContent = 'copied';
        setTimeout(function () { note.textContent = ''; }, 1800);
      }
      function selectIt() {
        // Some app views refuse clipboard writes; selecting the text lets the
        // reader copy it themselves rather than leaving the button dead.
        var r = document.createRange();
        r.selectNodeContents(code);
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(r);
      }
      try {
        navigator.clipboard.writeText(btn.dataset.addr).then(done, selectIt);
      } catch (e) { selectIt(); }
    });
  });
})();
</script>
"""


def stamp():
    """Today as '29 September 2026'. Built by hand: the no-pad day directive
    differs between platforms (%-d on Unix, %#d on Windows)."""
    now = datetime.now(timezone.utc)
    return "{} {} {}".format(now.day, now.strftime("%B"), now.year)


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def fmt_month(d):
    if not d or len(d) < 7:
        return ""
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return "{} {}".format(names[int(d[5:7]) - 1], d[:4])


def fmt_day(d):
    if not d or len(d) < 10:
        return ""
    return "{} {}".format(int(d[8:10]), fmt_month(d))


def build_roles(series):
    if not series:
        return ""
    cards = []
    for s in series:
        span = fmt_month(s["first"])
        if s["last"][:7] != s["first"][:7]:
            span += " – " + fmt_month(s["last"])
        cards.append(
            '<div class="role t-{}"><div class="n">{}</div>'
            '<div class="t">{}, {}</div><div class="s">{}</div></div>'.format(
                esc(s.get("type", "article")), s["count"],
                esc(s["role"]), esc(s["name"]), esc(span)))
    return '<h2>Recurring work</h2><div class="roles">' + "".join(cards) + "</div>"


def build_featured(items, chosen):
    picks = []
    if chosen:
        by_url = {i.get("url"): i for i in items if i.get("url")}
        picks = [by_url[u] for u in chosen if u in by_url]
    if not picks:
        # Placeholder: the most recent piece from each major outlet.
        seen = set()
        for it in items:
            o = it.get("outlet")
            if it.get("type") != "article" or o in seen:
                continue
            seen.add(o)
            picks.append(it)
            if len(picks) >= 6:
                break
    if not picks:
        return ""
    cards = []
    for p in picks:
        cards.append(
            '<div class="fcard"><span class="o">{}</span>'
            '<a href="{}" target="_blank" rel="noopener">{}</a>'
            '<span class="d">{}</span></div>'.format(
                esc(p.get("outlet")), esc(p.get("url")), esc(p.get("title")),
                esc(fmt_day(p.get("date")))))
    return '<h2>Selected work</h2><div class="feat">' + "".join(cards) + "</div>"


def main():
    payload = json.loads((DATA / "items.json").read_text(encoding="utf-8"))
    all_items = payload["items"]
    series = payload.get("series", [])
    PUBLIC.mkdir(parents=True, exist_ok=True)

    # Recurring episodes are represented by their series card, not as rows.
    archive = [i for i in all_items
               if not (i.get("recurring") and i.get("type") in COLLAPSE_SERIES_OF_TYPE)]

    years = sorted({(i.get("date") or "")[:4] for i in archive if i.get("date")})
    rng = "{}–{}".format(years[0], years[-1]) if years else "no dated items"

    portrait = ('<img class="portrait" src="{}" alt="{}">'.format(
        esc(PROFILE["photo"]), esc(PROFILE["name"])) if PROFILE["photo"] else "")

    chips = " ".join('<a href="{}" target="_blank" rel="noopener">{}</a>'.format(
        esc(l["url"]), esc(l["label"])) for l in PROFILE["links"] + PROFILE["socials"])

    contact = ""
    if PROFILE["emails"]:
        rows = "".join(
            '<div class="mailrow"><span>{}</span><code>{}</code>'
            '<button class="copymail" type="button" data-addr="{}">Copy</button>'
            '<span class="ok"></span></div>'.format(
                esc(e["label"]), esc(e["address"]), esc(e["address"]))
            for e in PROFILE["emails"])
        contact = '<div class="contact"><div class="note">{}</div>{}</div>'.format(
            esc(PROFILE["email_note"]), rows)

    html = (TEMPLATE
            .replace("__NAME__", esc(PROFILE["name"]))
            .replace("__TAGLINE__", esc(PROFILE["tagline"]))
            .replace("__BIO__", esc(PROFILE["bio"]))
            .replace("__PORTRAIT__", portrait)
            .replace("__LINKS__", chips)
            .replace("__CONTACT__", contact)
            .replace("__ROLES__", build_roles(series))
            .replace("__FEATURED__", build_featured(archive, PROFILE["featured"]))
            .replace("__TOTAL__", str(len(archive)))
            .replace("__RANGE__", rng)
            .replace("__GENERATED__", stamp())
            .replace("__DATA__", json.dumps(archive, ensure_ascii=False)))

    out = PUBLIC / "index.html"
    out.write_text(html, encoding="utf-8")
    print("Wrote {}  ({:.0f} KB)".format(out, out.stat().st_size / 1024))
    print("  {} archive rows, {} recurring episodes folded into {} series".format(
        len(archive), len(all_items) - len(archive), len(series)))


if __name__ == "__main__":
    main()
