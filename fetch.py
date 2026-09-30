#!/usr/bin/env python3
"""
fetch.py - collect Sean Speer's published writing and podcast appearances.

Each source is a separate function so one breaking does not take the rest down.
Everything lands in data/items.json as a single flat list, which build.py turns
into the site. Re-running is safe: it overwrites cleanly and nothing is lost,
because the sources are the source of truth, not this file.

Sources that work today:
  - The Hub          WordPress REST API, full archive, every co-author byline
  - Podcasts         Apple's public podcast index, searched by name
  - City Journal     the Substack archive API (Substack began April 2026)

Sources needing a hand:
  - City Journal proper, National Post, Globe and Mail all render their author
    pages with JavaScript and expose no archive API. Add those by hand in
    data/manual.json - see that file for the shape.
"""

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

# A real browser string. Cloudflare in front of The Hub rejects stub agents,
# which is what made this look blocked the first time round.
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}

YEARS = 7
CUTOFF = datetime.now(timezone.utc).year - YEARS


def get(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers


def get_json(url, timeout=40):
    body, headers = get(url, timeout)
    return json.loads(body), headers


def clean(text):
    """WordPress returns titles with HTML entities and stray tags."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    for a, b in [("&#8217;", "’"), ("&#8216;", "‘"), ("&#8220;", "“"),
                 ("&#8221;", "”"), ("&#8211;", "–"), ("&#8212;", "—"),
                 ("&amp;", "&"), ("&nbsp;", " "), ("&quot;", '"'), ("&#039;", "'")]:
        text = text.replace(a, b)
    return text.strip()


# ---------------------------------------------------------------- The Hub

def fetch_hub(name="speer"):
    """The Hub gives every co-authorship its own author record, so a single
    author id misses most of the work. Collect every byline containing the
    name, then pull posts for each."""
    base = "https://thehub.ca/wp-json/wp/v2/"
    authors, page = [], 1
    while True:
        d, _ = get_json(base + "users?" + urllib.parse.urlencode(
            {"search": name, "per_page": 100, "page": page}))
        if not d:
            break
        authors += [u for u in d if name in (u.get("name") or "").lower()]
        if len(d) < 100:
            break
        page += 1

    items = []
    for u in authors:
        page = 1
        while True:
            try:
                posts, _ = get_json(base + "posts?" + urllib.parse.urlencode(
                    {"author": u["id"], "per_page": 100, "page": page,
                     "orderby": "date", "order": "desc"}))
            except urllib.error.HTTPError as e:
                if e.code == 400:      # past the last page
                    break
                raise
            if not posts:
                break
            for p in posts:
                d_ = (p.get("date") or "")[:10]
                if d_ and int(d_[:4]) < CUTOFF:
                    continue
                items.append({
                    "type": "article",
                    "outlet": "The Hub",
                    "title": clean((p.get("title") or {}).get("rendered")),
                    "date": d_,
                    "url": p.get("link"),
                    "byline": clean(u.get("name")),
                    "coauthored": " and " in (u.get("name") or "") or "," in (u.get("name") or ""),
                })
            if len(posts) < 100:
                break
            page += 1
            time.sleep(0.15)
    return items


# --------------------------------------------------- City Journal Substack

def fetch_substack(host="cityjournal.substack.com", name="speer", outlet="City Journal"):
    items, offset = [], 0
    while offset < 2000:
        try:
            d, _ = get_json("https://{}/api/v1/archive?sort=new&limit=50&offset={}".format(host, offset))
        except Exception:
            break
        if not d:
            break
        for p in d:
            bylines = [a.get("name", "") for a in (p.get("publishedBylines") or [])]
            if not any(name in b.lower() for b in bylines):
                continue
            d_ = (p.get("post_date") or "")[:10]
            if d_ and int(d_[:4]) < CUTOFF:
                continue
            items.append({
                "type": "article",
                "outlet": outlet,
                "series": outlet + " Substack",
                "role": "Columnist",
                "title": clean(p.get("title")),
                "date": d_,
                "url": p.get("canonical_url"),
                "byline": ", ".join(bylines),
                "coauthored": len(bylines) > 1,
            })
        offset += 50
        time.sleep(0.2)
    return items


# --------------------------------------------- generic WordPress author feed

def fetch_wp_author(site, slug, outlet):
    """Postmedia and NY Post both run WordPress with author archives.

    Prefer the REST API, which returns the complete archive. Fall back to the
    author's RSS feed, which most WordPress sites expose at
    /author/<slug>/feed/ even when the API is locked down - that returns only
    the recent window, but for an outlet with a handful of pieces it is often
    the whole set anyway.
    """
    items = []
    # 1. REST API, if it will talk to us
    try:
        users, _ = get_json("{}/wp-json/wp/v2/users?{}".format(
            site, urllib.parse.urlencode({"search": "speer", "per_page": 20})))
        uid = next((u["id"] for u in users
                    if "speer" in (u.get("name") or "").lower()
                    or u.get("slug") == slug), None)
        if uid:
            page = 1
            while True:
                posts, _ = get_json("{}/wp-json/wp/v2/posts?{}".format(site, urllib.parse.urlencode(
                    {"author": uid, "per_page": 100, "page": page, "orderby": "date"})))
                if not posts:
                    break
                for p in posts:
                    d_ = (p.get("date") or "")[:10]
                    if d_ and int(d_[:4]) < CUTOFF:
                        continue
                    items.append({
                        "type": "article", "outlet": outlet,
                        "title": clean((p.get("title") or {}).get("rendered")),
                        "date": d_, "url": p.get("link"), "byline": "", "coauthored": False,
                    })
                if len(posts) < 100:
                    break
                page += 1
                time.sleep(0.2)
            if items:
                return items
    except Exception:
        pass

    # 2. Author RSS feed
    try:
        import xml.etree.ElementTree as ET
        body, _ = get("{}/author/{}/feed/".format(site, slug))
        ch = ET.fromstring(body).find("channel")
        for it in ch.findall("item"):
            d_ = parse_rss_date(it.findtext("pubDate"))
            if d_ and int(d_[:4]) < CUTOFF:
                continue
            items.append({
                "type": "article", "outlet": outlet,
                "title": clean(it.findtext("title")), "date": d_,
                "url": it.findtext("link"), "byline": "", "coauthored": False,
            })
    except Exception as e:
        print("  {} feed failed: {}".format(outlet, type(e).__name__), file=sys.stderr)
    return items


def parse_rss_date(s):
    """RFC-822 pubDate -> YYYY-MM-DD."""
    if not s:
        return ""
    months = {m: i for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", s)
    if not m:
        return ""
    return "{}-{:02d}-{:02d}".format(m.group(3), months.get(m.group(2), 1), int(m.group(1)))


# ---------------------------------------------------------------- Podcasts

HUB_FEED = "https://feeds.acast.com/public/shows/69cc1a3992d007a7658eee4e"

# Recurring work is reported as a role with a count, not as hundreds of rows.
# Which series an episode belongs to is decided by its title prefix where it has
# one, and otherwise by the series boilerplate Acast appends to the description.
HUB_SERIES = [
    ("Hub Dialogues", "Host", ["hub dialogues"], ["dialogues"]),
    ("Hub Roundtable", "Co-host", ["hub roundtable"], ["roundtable"]),
    ("Hub Hits", "Contributor", ["hub hits"], ["hub hits"]),
]


def fetch_hub_podcasts():
    """Read The Hub's own feed and pick out the episodes he is on.

    Apple's episode search caps its results and matches loosely; it found 34 of
    these. The feed carries all 2,000-odd episodes and says who is on each.
    """
    import xml.etree.ElementTree as ET

    body, _ = get(HUB_FEED, timeout=120)
    items = ET.fromstring(body).find("channel").findall("item")

    def blob(it):
        d = (it.findtext("description") or "") + " " + (it.findtext(
            "{http://www.itunes.com/dtds/podcast-1.0.dtd}summary") or "")
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", d))

    out = []
    for it in items:
        title = clean(it.findtext("title"))
        text = blob(it)
        if "speer" not in (title + " " + text).lower():
            continue
        low = title.lower()
        series, role = "Hub Podcasts", "Contributor"
        for name, r, prefixes, markers in HUB_SERIES:
            if any(low.startswith(p) for p in prefixes) or \
               any(m in text.lower() for m in markers):
                series, role = name, r
                break
        else:
            # Hub Headlines is an audio reading of a published article, so it is
            # the writing appearing again rather than a separate appearance.
            if low.startswith("hub headlines") or "hub headlines features audio versions" in text.lower():
                continue
        out.append({
            "type": "podcast", "outlet": "The Hub", "series": series, "role": role,
            "title": title, "date": parse_rss_date(it.findtext("pubDate")),
            "url": it.findtext("link") or "", "byline": "", "coauthored": False,
            "recurring": True,
        })
    return out


def fetch_podcasts(term="sean speer"):
    """Apple's public index. It over-returns - a search for a name pulls in
    whole shows the person is associated with - so keep only episodes whose
    title or description actually names them."""
    q = urllib.parse.urlencode({"term": term, "entity": "podcastEpisode",
                                "limit": 200, "country": "CA"})
    try:
        d, _ = get_json("https://itunes.apple.com/search?" + q)
    except Exception as e:
        print("  podcast search failed:", type(e).__name__, file=sys.stderr)
        return []

    last = term.split()[-1].lower()
    items = []
    for r in d.get("results", []):
        hay = ((r.get("trackName") or "") + " " + (r.get("description") or "")).lower()
        if last not in hay:
            continue
        # The Hub's own shows come from the feed instead, which is complete.
        if "hub podcast" in (r.get("collectionName") or "").lower():
            continue
        d_ = (r.get("releaseDate") or "")[:10]
        if d_ and int(d_[:4]) < CUTOFF:
            continue
        items.append({
            "type": "podcast",
            "outlet": r.get("collectionName") or "",
            "title": clean(r.get("trackName")),
            "date": d_,
            "url": r.get("trackViewUrl") or r.get("episodeUrl"),
            "byline": "",
            "coauthored": False,
        })
    return items


# ------------------------------------------------------------ manual entries

def fetch_manual():
    """Outlets with no machine-readable archive go here by hand."""
    p = DATA / "manual.json"
    if not p.exists():
        return []
    try:
        entries = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print("  manual.json is not valid JSON:", e, file=sys.stderr)
        return []
    out = []
    for e in entries:
        e.setdefault("type", "article")
        e.setdefault("byline", "")
        e.setdefault("coauthored", False)
        # A URL is preferred but not required: a piece with no resolvable link
        # still belongs in the record, and build.py renders it unlinked.
        e.setdefault("url", "")
        if e.get("title"):
            out.append(e)
    return out


# ---------------------------------------------------------------------------

def main():
    DATA.mkdir(parents=True, exist_ok=True)
    # Manual entries go first: when the same piece also arrives from a feed,
    # the hand-written record wins, because it carries the real co-author
    # bylines and the outlet's own name for the piece.
    sources = [
        ("Manual entries", fetch_manual),
        ("The Hub", fetch_hub),
        ("National Post", lambda: fetch_wp_author("https://nationalpost.com", "sspeer", "National Post")),
        ("New York Post", lambda: fetch_wp_author("https://nypost.com", "sean-speer", "New York Post")),
        ("City Journal (Substack)", fetch_substack),
        ("Hub podcasts", fetch_hub_podcasts),
        ("Other podcasts", fetch_podcasts),
    ]

    all_items = []
    for label, fn in sources:
        print("Fetching {} ...".format(label))
        try:
            got = fn()
            print("  {} items".format(len(got)))
            all_items += got
        except Exception as e:
            print("  FAILED: {}: {}".format(type(e).__name__, e), file=sys.stderr)

    # De-duplicate, keeping the first seen. Match on URL and, separately, on a
    # normalised title: the same piece often appears under two addresses (a
    # Substack copy and the outlet's own), and those are one item, not two.
    def norm(t):
        t = (t or "").lower()
        t = t.replace("’", "'").replace("‘", "'")
        t = t.replace("—", " ").replace("–", " ")
        return re.sub(r"[^a-z0-9]+", " ", t).strip()

    seen_urls, seen_titles, deduped = set(), set(), []
    for it in all_items:
        url_key = (it.get("url") or "").split("?")[0].rstrip("/")
        # Scope the title match to the type: an episode and an article can
        # legitimately share a title and are still two different things.
        title_key = it.get("type", "") + "|" + norm(it.get("title"))
        if not norm(it.get("title")):
            title_key = ""
        if url_key and url_key in seen_urls:
            continue
        if title_key and title_key in seen_titles:
            continue
        if url_key:
            seen_urls.add(url_key)
        if title_key:
            seen_titles.add(title_key)
        deduped.append(it)

    # The Weekly Wrap is a named column, not a one-off, so tag it as a series
    # while leaving each instalment in the archive - it is writing, after all.
    for it in deduped:
        if re.search(r"the weekly wrap", it.get("title") or "", re.I):
            it["series"] = "The Weekly Wrap"
            it["role"] = "Author"

    # Everything else written for The Hub is a body of work in its own right.
    # Without this the written output shows up as the Weekly Wrap alone, which
    # reads as a few dozen pieces beside several hundred podcast episodes.
    for it in deduped:
        if (it.get("type") == "article" and it.get("outlet") == "The Hub"
                and not it.get("series")):
            it["series"] = "Hub commentary"
            it["role"] = "Columnist"

    # Summarise anything recurring: a role and a count read better than
    # hundreds of near-identical rows.
    # The uncategorised Hub episodes are Dialogues in all but the boilerplate,
    # so they are counted there rather than as a vague second podcast card.
    MERGE_INTO = {"Hub Podcasts": "Hub Dialogues"}

    groups = {}
    for it in deduped:
        s = MERGE_INTO.get(it.get("series"), it.get("series"))
        if not s:
            continue
        g = groups.setdefault(s, {"name": s, "role": it.get("role", ""),
                                  "outlet": it.get("outlet", ""), "count": 0,
                                  "first": "9999", "last": "0000",
                                  "type": it.get("type", "")})
        g["count"] += 1
        # When a group absorbs another, keep the role of the named series
        # rather than whichever item happened to be seen first.
        if it.get("series") == s and it.get("role"):
            g["role"] = it["role"]
        d_ = it.get("date") or ""
        if d_:
            g["first"] = min(g["first"], d_)
            g["last"] = max(g["last"], d_)
    series = sorted(groups.values(), key=lambda g: -g["count"])

    deduped.sort(key=lambda x: x.get("date") or "", reverse=True)
    out = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "cutoff_year": CUTOFF,
        "series": series,
        "items": deduped,
    }
    (DATA / "items.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    dropped = len(all_items) - len(deduped)
    print("\n{} items ({} duplicates removed) -> {}".format(
        len(deduped), dropped, DATA / "items.json"))
    if deduped:
        print("date range: {} -> {}".format(deduped[-1].get("date"), deduped[0].get("date")))
        by_outlet = {}
        for it in deduped:
            by_outlet[it["outlet"]] = by_outlet.get(it["outlet"], 0) + 1
        print("\ntop outlets:")
        for o, n in sorted(by_outlet.items(), key=lambda x: -x[1])[:8]:
            print("  {:>4}  {}".format(n, o[:48]))


if __name__ == "__main__":
    main()
