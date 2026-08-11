#!/usr/bin/env python3
"""Stamp a content hash onto every reference to assets/styles.css.

    python3 tools/fingerprint-css.py

Why this exists
---------------
Cloudflare serves assets/styles.css with cache-control: max-age=14400. Without a
fingerprint, a returning visitor who arrives within four hours of a stylesheet
change gets the NEW html and the OLD css. On get-matched.html that renders as
unstyled browser-default fields — and the spam honeypot, which is hidden by CSS,
would render as a visible unlabelled "Company website" input on a real form.

The hash is derived from the file's own bytes, so it cannot be forgotten the way
a hand-incremented ?v=2 can. Run this after ANY edit to assets/styles.css, and
before committing.

A query string rather than a hashed filename, deliberately: the file keeps one
name, so worker/index.js can keep referencing /assets/styles.css on its error
page, and there are no orphaned styles.<old-hash>.css files to clean up. The
zone's cache level is "aggressive" (Cloudflare's Standard), which includes the
query string in the cache key, so this busts both edge and browser caches.
"""

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = ROOT / "assets" / "styles.css"

# Matches href="<anything>assets/styles.css<optional ?v=...>"
LINK = re.compile(r'(href=")((?:\.\./|/)?assets/styles\.css)(\?v=[0-9a-f]+)?(")')


def main():
    if not CSS.exists():
        sys.exit(f"missing {CSS}")

    digest = hashlib.sha256(CSS.read_bytes()).hexdigest()[:10]
    print(f"  assets/styles.css  sha256[:10] = {digest}\n")

    changed, checked = [], 0
    for path in sorted(ROOT.rglob("*.html")):
        if any(part in {".git", "node_modules"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        if "assets/styles.css" not in text:
            continue
        checked += 1
        new = LINK.sub(lambda m: f"{m.group(1)}{m.group(2)}?v={digest}{m.group(4)}", text)
        rel = path.relative_to(ROOT).as_posix()
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed.append(rel)
            print(f"    stamped  {rel}")
        else:
            print(f"    current  {rel}")

    print(f"\n  {checked} file(s) reference the stylesheet; {len(changed)} updated.")

    # Fail loudly rather than silently leaving a page on a stale hash.
    missing = []
    for path in sorted(ROOT.rglob("*.html")):
        if any(part in {".git", "node_modules"} for part in path.parts):
            continue
        t = path.read_text(encoding="utf-8")
        if "assets/styles.css" in t and f"styles.css?v={digest}" not in t:
            missing.append(path.relative_to(ROOT).as_posix())
    if missing:
        sys.exit("  NOT STAMPED: " + ", ".join(missing))


if __name__ == "__main__":
    main()
