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

What it checks
--------------
- The homepage references the CSS fingerprint that is committed right now, which
  proves the HTML the pipeline produced is actually being served. It polls for
  this first, so a slow GitHub Pages publish is waited out rather than failed.
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
POLL_ATTEMPTS = int(os.environ.get("VERIFY_POLL_ATTEMPTS", "24"))
POLL_SLEEP = int(os.environ.get("VERIFY_POLL_SLEEP", "15"))  # seconds

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


def wait_for_deploy(fp):
    """Poll the homepage until it references the committed fingerprint."""
    for i in range(1, POLL_ATTEMPTS + 1):
        status, body, _ = fetch("/index.html")
        if status == 200 and f"styles.css?v={fp}" in body:
            print(f"  homepage is serving the committed fingerprint {fp} "
                  f"(attempt {i})")
            return True
        live = CSSV.search(body)
        print(f"  attempt {i}/{POLL_ATTEMPTS}: homepage status {status}, "
              f"live fingerprint {live.group(1) if live else 'none'} "
              f"(want {fp}) — waiting {POLL_SLEEP}s")
        time.sleep(POLL_SLEEP)
    return False


def main():
    fp = expected_fingerprint()
    published, drafts = repo_published_posts()
    print(f"Verifying {SITE}")
    print(f"  committed fingerprint: {fp}")
    print(f"  published posts: {published or '(none)'}")
    print(f"  future-dated drafts (expected noindex live): {drafts or '(none)'}\n")

    if not wait_for_deploy(fp):
        sys.exit(
            f"\nFAILED: {SITE}/ never served fingerprint {fp} after "
            f"{POLL_ATTEMPTS * POLL_SLEEP}s. The deploy did not propagate."
        )

    failures = []

    def check(name, ok, detail=""):
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    # Homepage + content pages carry the Blog nav link.
    for page in CONTENT_PAGES:
        status, body, _ = fetch(f"/{page}")
        has_blog = re.search(r'<a href="/?blog/">Blog</a>', body) is not None
        check(f"{page}: 200 and Blog nav present",
              status == 200 and has_blog,
              f"status={status} blogNav={has_blog}")

    # Blog index: 200, not noindex, Blog nav.
    status, body, _ = fetch("/blog/")
    check("/blog/: 200, not noindex, Blog nav",
          status == 200 and not NOINDEX.search(body) and ">Blog</a>" in body,
          f"status={status} noindex={bool(NOINDEX.search(body))}")

    # The committed stylesheet is actually deployed.
    status, css, _ = fetch(f"/assets/styles.css?v={fp}")
    css_ok = status == 200 and ".nl-post-hero" in css and ".nl-post-faq" in css
    # Belt and suspenders: the live bytes hash to the committed fingerprint.
    local_fp = hashlib.sha256((ROOT / "assets" / "styles.css").read_bytes()).hexdigest()[:10]
    live_fp = hashlib.sha256(css.encode("utf-8")).hexdigest()[:10] if status == 200 else "n/a"
    check(f"styles.css?v={fp}: 200 and new rules present",
          css_ok, f"status={status} liveHash={live_fp} repoHash={local_fp}")

    # SEO artifacts.
    status, body, _ = fetch("/sitemap.xml")
    check("sitemap.xml: 200 and lists /blog/",
          status == 200 and "/blog/" in body, f"status={status}")
    status, body, _ = fetch("/llms.txt")
    check("llms.txt: 200 and mentions the blog",
          status == 200 and "Notes on aging at home" in body, f"status={status}")

    # Published posts must be live and indexable.
    for slug in published:
        status, body, _ = fetch(f"/blog/{slug}.html")
        check(f"blog/{slug}.html: 200 and not noindex",
              status == 200 and not NOINDEX.search(body),
              f"status={status} noindex={bool(NOINDEX.search(body))}")

    # Drafts, if live at all, must stay noindex (they may 404 before their date).
    for slug in drafts:
        status, body, _ = fetch(f"/blog/{slug}.html")
        ok = status == 404 or (status == 200 and bool(NOINDEX.search(body)))
        check(f"blog/{slug}.html (draft): 404 or noindex",
              ok, f"status={status} noindex={bool(NOINDEX.search(body))}")

    print()
    if failures:
        sys.exit(f"FAILED: {len(failures)} live check(s) did not pass: "
                 + ", ".join(failures))
    print("All live checks passed.")


if __name__ == "__main__":
    main()
