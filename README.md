# Sean Speer — personal site

A self-updating index of published writing, podcast appearances, and talks.
Two small Python scripts collect the work and render a single HTML page.
GitHub Actions runs them every morning; GitHub Pages serves the result.

There is no server, no database, and no build toolchain. The published page
carries its own data inline, so it works opened straight from disk.

## How it works

```
sources ──▶ fetch.py ──▶ data/items.json ──▶ build.py ──▶ docs/index.html
```

`fetch.py` reads every source and writes one flat list of items.
`build.py` turns that list into the page. Run them in that order.

```bash
python fetch.py
python build.py
```

## Where the work comes from

| Source | Method | Coverage |
| --- | --- | --- |
| The Hub | WordPress REST API | Complete archive, every co-author byline |
| The Hub podcasts | Acast RSS feed | Complete; recurring series shown as roles |
| National Post | WordPress REST API | Complete archive |
| New York Post | Author RSS feed | Recent window |
| City Journal | Substack archive API, plus `data/manual.json` | April 2026 onward automatically |
| Other podcasts | Apple's public podcast index | Best effort |
| Talks, one-offs | `data/manual.json` | By hand |

### Things worth knowing

**The Hub gives every co-authorship its own author record.** Querying a single
author id would miss most of the work, so `fetch_hub` collects every byline
containing the name and pulls posts for each. There are sixteen.

**Cloudflare rejects stub user agents.** Requests to The Hub with a short
`User-Agent` come back 403, which looks exactly like a block. A real browser
string gets through. The same request succeeds or fails purely on that header.

**City Journal uses editorial slugs, not title slugs.** "Bill Clinton Was Right
About Welfare" lives at `/article/welfare-work-manhattan-institute-poll-bill-clinton`.
Those cannot be derived from a title, which is why some City Journal pieces are
listed by hand in `data/manual.json`.

**Apple's podcast search is not a substitute for a feed.** Searching a name
capped out at 34 Hub episodes; reading the feed found 951. Where a show has a
feed, read the feed.

**Recurring work is a role, not rows.** Nearly a thousand Hub episodes would
bury 451 pieces of writing, so anything tagged with a `series` is summarised as
a count and a date range, and its episodes are left out of the archive list.

## Adding something by hand

`data/manual.json` is a list of entries. A URL is preferred but optional; an
item without one is shown as plain text rather than a link.

```json
{
  "type": "article",
  "outlet": "City Journal",
  "title": "A piece the scrapers cannot reach",
  "date": "2026-02-14",
  "url": "https://www.city-journal.org/article/...",
  "byline": "Sean Speer",
  "coauthored": false
}
```

`type` is `article`, `podcast`, or `video`. Manual entries take precedence over
anything a feed returns for the same piece, so they are also the way to correct
a wrong title or outlet.

## Changing the page

Everything editable by hand lives in the `PROFILE` block at the top of
`build.py`: the name, tagline, bio, portrait, contact address, social links, and
which pieces appear under Selected work. Leave a field empty and the page omits
that section rather than showing a gap.

## Automation

`.github/workflows/update.yml` runs both scripts each morning and commits any
change. It can also be triggered by hand from the repository's Actions tab.
If a source breaks, that source reports the failure and the others still run.
