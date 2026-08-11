#!/usr/bin/env python3
"""Regenerate sitemap.xml from the HTML actually present in the repo.

Run after adding, renaming, or removing any page:

    python3 tools/build-sitemap.py

Pages are discovered, not listed by hand, so a new blog post cannot be
forgotten. Anything carrying <meta name="robots" content="noindex"> is skipped
automatically, which is why 404.html, thanks.html and blog/_template.html stay
out without needing to be special-cased.
"""

import re
import sys
from pathlib import Path

SITE = "https://www.nestlonger.com"
ROOT = Path(__file__).resolve().parent.parent

# Directories never worth crawling.
SKIP_DIRS = {".git", "assets", "tools", "worker", "node_modules", ".github"}

# changefreq / priority by path. First match wins; the rest fall through
# to the default.
RULES = [
    (r"^index\.html$",        "weekly",  "1.0", "/"),
    (r"^(grab-bars|adus)\.html$", "weekly",  "0.9", None),
    (r"^get-matched\.html$",  "monthly", "0.8", None),
    (r"^blog/index\.html$",   "weekly",  "0.7", "/blog/"),
    (r"^blog/.+\.html$",      "monthly", "0.7", None),
    (r"^partners\.html$",     "monthly", "0.7", None),
    (r"^partner-apply\.html$", "monthly", "0.6", None),
    (r"^about\.html$",        "monthly", "0.6", None),
    (r"^privacy\.html$",      "yearly",  "0.3", None),
]
DEFAULT = ("monthly", "0.5")

NOINDEX = re.compile(
    r'<meta[^>]+name=["\']robots["\'][^>]*content=["\'][^"\']*noindex', re.I
)


def discover():
    pages = []
    for path in sorted(ROOT.rglob("*.html")):
        rel = path.relative_to(ROOT)
        if set(rel.parts) & SKIP_DIRS:
            continue
        if NOINDEX.search(path.read_text(encoding="utf-8", errors="ignore")):
            print(f"  skip (noindex): {rel}")
            continue
        pages.append(rel.as_posix())
    return pages


def entry(rel):
    for pattern, freq, prio, override in RULES:
        if re.match(pattern, rel):
            return (override or f"/{rel}"), freq, prio
    return f"/{rel}", *DEFAULT


def main():
    pages = discover()
    if not pages:
        sys.exit("No indexable pages found — refusing to write an empty sitemap.")

    entries = sorted(
        (entry(p) for p in pages),
        key=lambda e: (-float(e[2]), e[0]),
    )

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, freq, prio in entries:
        lines += [
            "  <url>",
            f"    <loc>{SITE}{loc}</loc>",
            f"    <changefreq>{freq}</changefreq>",
            f"    <priority>{prio}</priority>",
            "  </url>",
        ]
    lines += ["</urlset>", ""]

    out = ROOT / "sitemap.xml"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  wrote {out.relative_to(ROOT)} with {len(entries)} URLs:")
    for loc, _, prio in entries:
        print(f"    {prio}  {loc}")


if __name__ == "__main__":
    main()
