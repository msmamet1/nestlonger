#!/usr/bin/env python3
"""Verify the LIVE site matches what is committed, after a deploy.

    python3 tools/verify-live.py            # verify https://www.nestlonger.com
    SITE=https://staging.example python3 tools/verify-live.py

Why this exists
---------------
A deploy is only done when the acceptance criteria are true against the live
site, not the repo (see CLAUDE.md, "Definition of done"). That check used to be
manual, and some environments — including the Claude Code cloud sandbox this
repo is often edited from — have no outbound web access, so the agent that
shipped the change literally cannot open the page it shipped.

GitHub Actions runners DO have full internet egress. So this script runs in CI
(.github/workflows/verify-live.yml) on every deploy and fails the workflow,
visibly, if the live site does not reflect the committed HEAD. It is also
runnable by hand from any machine with web access.

Waiting out the publish
-----------------------
A GitHub Pages publish that has not finished yet looks exactly like a broken one
on the first request: the page 404s, or serves its previous bytes. So every
expect-200 check is retried until it passes or a single shared propagation
budget runs out, rather than being failed on first look.

The budget is shared across the whole run, not per check, so a genuinely broken
deploy still fails in about one budget rather than one budget per failing check.
The trade is deliberate: a real failure is reported up to VERIFY_POLL_ATTEMPTS *
VERIFY_POLL_SLEEP later than it could be, because on a deploy verifier a false
failure costs more than a slow true one.

This used to gate on one thing only — the homepage serving the committed CSS
fingerprint — and then assert everything else immediately. That is a sound proxy
when a change touches the stylesheet and no proxy at all when it does not. Five
consecutive blog posts each failed this workflow that way on 2026-08-29: the
fingerprint was byte-identical across all of them because none touched
assets/styles.css, so the gate was satisfied on attempt 1 by the PREVIOUS
deploy, waited zero seconds, and checked a post GitHub Pages had not published
yet. Gate on what actually changed, or on everything; not on a stand-in.

What it checks
--------------
- The homepage references the CSS fingerprint that is committed right now, which
  proves the HTML the pipeline produced is actually being served.
- The homepage and every content page carry the "Blog" nav link.
- /blog/ returns 200, is not noindexed, and shows the Blog nav.
- The live stylesheet at the committed ?v= hash returns 200 and contains the
  markers this version added, proving the new CSS deployed.
- sitemap.xml and llms.txt return 200 and mention the blog.
- Every PUBLISHED post (a blog/<slug>.html the repo does not mark noindex)
  returns 200 and is not noindexed. Future-dated drafts, which the repo marks
  noindex on purpose, are expected to be noindexed live and are checked for
  exactly that.

Standard library only; no dependency to install on the runner.
"""

import hashlib
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = os.environ.get("SITE", "https://www.nestlonger.com").rstrip("/")

# How long to wait for a GitHub Pages publish to propagate before giving up.
# Shared across every check in the run, not spent per check.
POLL_ATTEMPTS = int(os.environ.get("VERIFY_POLL_ATTEMPTS", "24"))
POLL_SLEEP = int(os.environ.get("VERIFY_POLL_SLEEP", "15"))  # seconds
POLL_BUDGET = POLL_ATTEMPTS * POLL_SLEEP

NOINDEX = re.compile(
    r'<meta[^>]+name=["\']robots["\'][^>]*content=["\'][^"\']*noindex', re.I
)
CSSV = re.compile(r"styles\.css\?v=([0-9a-f]+)")

# Top-level served pages that must carry the Blog nav link.
CONTENT_PAGES = [
    "index.html", "grab-bars.html", "adus.html", "partners.html",
    "about.html", "privacy.html", "get-matched.html", "partner-apply.html",
    "thanks.html",
]

UA = {"User-Agent": "nestlonger-verify-live/1.0 (+CI)"}


def fetch(path, tries=3):
    """GET SITE+path. Returns (status, body_text, body_bytes). Retries transient
    network errors a few times; an HTTP status (even 404) is returned, not raised."""
    url = path if path.startswith("http") else f"{SITE}{path}"
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                return r.status, raw.decode("utf-8", "replace"), raw
        except urllib.error.HTTPError as e:
            raw = e.read()
            return e.code, raw.decode("utf-8", "replace"), raw
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise SystemExit(f"  network error fetching {url}: {last}")


def expected_fingerprint():
    m = CSSV.search((ROOT / "index.html").read_text(encoding="utf-8"))
    if not m:
        sys.exit("could not read the committed CSS fingerprint from index.html")
    return m.group(1)


def repo_published_posts():
    """Slugs of posts the repo intends to be indexed, and those it marks noindex."""
    published, drafts = [], []
    blog = ROOT / "blog"
    for p in sorted(blog.glob("*.html")):
        if p.name == "index.html":
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        (drafts if NOINDEX.search(text) else published).append(p.stem)
    return published, drafts


def settle(probe, deadline):
    """Call probe() until it reports ok, or the shared deadline passes.

    probe returns (ok, detail). Returns (ok, detail, attempts) from the last
    call, so a check that had to wait says so in its output."""
    attempts = 0
    while True:
        attempts += 1
        ok, detail = probe()
        if ok or time.monotonic() >= deadline:
            return ok, detail, attempts
        time.sleep(POLL_SLEEP)


def main():
    fp = expected_fingerprint()
    published, drafts = repo_published_posts()
    print(f"Verifying {SITE}")
    print(f"  committed fingerprint: {fp}")
    print(f"  published posts: {published or '(none)'}")
    print(f"  future-dated drafts (expected noindex live): {drafts or '(none)'}")
    print(f"  propagation budget: {POLL_BUDGET}s, shared across all checks\n")

    deadline = time.monotonic() + POLL_BUDGET
    failures = []

    def check(name, probe):
        ok, detail, attempts = settle(probe, deadline)
        waited = f" (settled after {attempts} attempts)" if attempts > 1 else ""
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}{waited}"
              + (f" — {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    # The homepage is serving the HTML this pipeline produced. Checked first
    # because it is the cheapest signal that the publish landed at all, but no
    # longer the only thing waited on.
    def probe_home():
        status, body, _ = fetch("/index.html")
        live = CSSV.search(body)
        return (status == 200 and f"styles.css?v={fp}" in body,
                f"status={status} live={live.group(1) if live else 'none'} want={fp}")
    check(f"index.html: serving committed fingerprint {fp}", probe_home)

    # Homepage + content pages carry the Blog nav link.
    def probe_page(page):
        def p():
            status, body, _ = fetch(f"/{page}")
            has_blog = re.search(r'<a href="/?blog/">Blog</a>', body) is not None
            return status == 200 and has_blog, f"status={status} blogNav={has_blog}"
        return p
    for page in CONTENT_PAGES:
        check(f"{page}: 200 and Blog nav present", probe_page(page))

    # Blog index: 200, not noindex, Blog nav.
    def probe_blog_index():
        status, body, _ = fetch("/blog/")
        return (status == 200 and not NOINDEX.search(body) and ">Blog</a>" in body,
                f"status={status} noindex={bool(NOINDEX.search(body))}")
    check("/blog/: 200, not noindex, Blog nav", probe_blog_index)

    # The committed stylesheet is actually deployed.
    local_fp = hashlib.sha256(
        (ROOT / "assets" / "styles.css").read_bytes()).hexdigest()[:10]

    def probe_css():
        status, css, _ = fetch(f"/assets/styles.css?v={fp}")
        live_fp = (hashlib.sha256(css.encode("utf-8")).hexdigest()[:10]
                   if status == 200 else "n/a")
        ok = status == 200 and ".nl-post-hero" in css and ".nl-post-faq" in css
        return ok, f"status={status} liveHash={live_fp} repoHash={local_fp}"
    check(f"styles.css?v={fp}: 200 and new rules present", probe_css)

    # SEO artifacts.
    def probe_sitemap():
        status, body, _ = fetch("/sitemap.xml")
        return status == 200 and "/blog/" in body, f"status={status}"
    check("sitemap.xml: 200 and lists /blog/", probe_sitemap)

    def probe_llms():
        status, body, _ = fetch("/llms.txt")
        return (status == 200 and "Notes on aging at home" in body,
                f"status={status}")
    check("llms.txt: 200 and mentions the blog", probe_llms)

    # Published posts must be live and indexable. This is the check the old
    # single-gate version raced: a post committed seconds ago 404s until Pages
    # publishes it.
    def probe_post(slug):
        def p():
            status, body, _ = fetch(f"/blog/{slug}.html")
            return (status == 200 and not NOINDEX.search(body),
                    f"status={status} noindex={bool(NOINDEX.search(body))}")
        return p
    for slug in published:
        check(f"blog/{slug}.html: 200 and not noindex", probe_post(slug))

    # Drafts, if live at all, must stay noindex (they may 404 before their date).
    def probe_draft(slug):
        def p():
            status, body, _ = fetch(f"/blog/{slug}.html")
            ok = status == 404 or (status == 200 and bool(NOINDEX.search(body)))
            return ok, f"status={status} noindex={bool(NOINDEX.search(body))}"
        return p
    for slug in drafts:
        check(f"blog/{slug}.html (draft): 404 or noindex", probe_draft(slug))

    print()
    if failures:
        sys.exit(f"FAILED: {len(failures)} live check(s) did not pass: "
                 + ", ".join(failures))
    print("All live checks passed.")


if __name__ == "__main__":
    main()
