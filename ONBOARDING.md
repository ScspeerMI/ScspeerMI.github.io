# Build yourself a self-updating personal website

An afternoon's work. At the end you have a public page at your own address,
listing everything you've published, that refreshes itself every morning
without you touching it. No hosting bill, no website builder, no subscription.

A working example: **https://scspeermi.github.io/** — built in one sitting
from five sources, and the source code is in the repository you're reading.

You do not need to know how to code. You need to know where your work is
published, and to be able to paste what you're told to paste.

---

## What you need first (about twenty minutes)

**A GitHub account.** Free. Sign up at github.com and pick a username you're
happy to have in a URL, because it becomes part of your web address.

**Claude Code**, which you're presumably already in.

**Then ask Claude to do the setup for you.** Paste this:

> Run `gh auth login`: GitHub.com, HTTPS, login with a web browser. Tell me the
> code and wait for me to confirm. Then run `gh auth refresh -h github.com -s
> workflow`. Then set my git name and email globally. Finish with
> `gh auth status` and confirm my username.

It'll hand you a short code to enter in your browser. The `workflow` scope
matters — it's what later lets the site update itself.

If Python isn't installed, Claude will tell you; on Windows
`winget install Python.Python.3.12` sorts it.

---

## Step 1: work out where your writing actually lives

**This is the step that decides whether the whole thing is easy or hard, and
it's the one people skip.**

Some publishers hand their content to anyone who asks. Others make it
effectively unreachable. The difference has nothing to do with how important
the outlet is, and you cannot guess it — it has to be checked.

Make a list of every outlet you publish in, plus any podcast you appear on.
Then hand it over:

> Here are the outlets I publish in: [list]. And podcasts I appear on: [list].
> For each one, check whether my work is reachable programmatically — a
> WordPress REST API, an RSS feed, an author feed, a Substack archive. Tell me
> which are complete archives, which give only recent items, and which are
> closed. Don't guess; check.

Expect a mixed answer. In the example above: two outlets gave complete
archives going back years, one gave only recent pieces, one gave nothing at
all, and one podcast feed turned out to hold 951 episodes that a search index
had reported as 34.

**Whatever is closed, you supply by hand, once.** Copy the titles, dates, and
links from your own author page into a list. Twenty minutes of dull work that
never needs repeating, because new pieces arrive through the feeds.

---

## Step 2: build it

> Build me a personal website like the one in
> https://github.com/ScspeerMI/ScspeerMI.github.io — a fetch script that
> collects my published work from the sources we just checked, and a build
> script that renders it into one self-contained HTML page. Same structure:
> a masthead, my recurring work as roles with counts, a few selected pieces,
> and a searchable archive below.

Then look at what comes back and say what's wrong with it. That's the actual
work, and it's the part only you can do. Real examples from building the page
above:

- The recurring-work cards were five podcasts and one writing credit, which
  made a writer look like a broadcaster. Consolidating them into three
  categories by outlet fixed it — and incidentally fixed a bug.
- One outlet prefixes headlines with the author's name. Sensible on their
  masthead; on your own site every line says your name back at you.
- Two pieces appeared under two different headlines. Which one goes on your
  site is an editorial call, not a technical one.

None of that is findable by the person building it. Look at the page and say
what looks wrong.

---

## Step 3: put it online

> Put this in a GitHub repository named <myusername>.github.io, public, and
> enable GitHub Pages serving from /docs.

Public is required for free Pages. Nothing in the project is sensitive — it's
a list of things you've already published.

Your site is then at `https://<myusername>.github.io/`. Two things reliably
go wrong here, and Claude knows about both: GitHub may serve your README
instead of your page, and it runs a processor over the files that can mangle
hand-built HTML. Both are one-line fixes.

---

## Step 4: make it update itself

> Add a GitHub Actions workflow that runs the fetch and build scripts each
> morning and commits anything that changed.

That's the `workflow` scope from the setup earning its place. From then on you
publish a piece on Tuesday and it appears on your site on Wednesday.

---

## Step 5: your own domain (optional)

> Is seanspeer.com available? Check the registry directly, not a reseller.

Register it yourself — about $20 a year from any registrar. Then:

> I've bought <domain>. Add the CNAME file, give me the DNS records to paste at
> my registrar, and turn on Enforce HTTPS.

The free address keeps working regardless. A custom domain is about how it
looks on a bio line, not whether the site functions.

---

## Four things worth knowing before you start

**Check the feed, not the search index.** An outlet's own feed is usually
complete; a search index over it usually isn't. One search returned 34
podcast episodes where the feed held 951. If a number looks low, it is.

**A 403 is often your own fault.** One publisher rejected every request until
the browser identification was set properly, then handed over its entire
archive. It looked exactly like a permanent block. If something appears
closed, it's worth a second look before you conclude it's impossible.

**Never let a heading depend on pattern-matching a title.** The example site
detected a weekly column by looking for its name in headlines. The publisher
quietly stopped including it, and the page then claimed the column had ended
while it was still running weekly. Group by where something was published,
which doesn't change.

**Pick sources that want to be read.** If you find yourself fighting a
platform that's actively refusing you, that's a signal to find another route,
not to push harder. The example project spent an hour trying to get video off
one platform before discovering the same video, at better quality, in a
podcast feed that was designed to be downloaded.

---

## Honestly, how long?

Under two hours if your outlets cooperate. The example above took longer, but
most of that was spent on a dead end that this guide now tells you to avoid.

The code is not the hard part, and it isn't the part you do. The hard part is
knowing which of your outlets can be read, and looking at the result with an
editor's eye.
