#!/usr/bin/env python3
"""Render blog posts from markdown source into static HTML.

    python3 tools/build-blog.py

One post is one file: blog/_posts/<slug>.md, YAML front matter plus a markdown
body. This script renders each to blog/<slug>.html from tools/blog-post.tmpl.html,
regenerates the post list and Blog JSON-LD on blog/index.html between HTML-comment
markers, and rewrites the blog section of llms.txt between its markers. Everything
outside the markers is left untouched.

The publishing agent commits blog/_posts/<slug>.md and nothing else; CI runs this
script (then build-sitemap.py and fingerprint-css.py) and commits the rendered
result back. See README, "Adding a blog post", for the field reference.

Dependencies: the standard library plus the `markdown` package (pip install
markdown). No YAML library — the front matter is a small, fixed schema parsed here.

Editorial guidance carried from the old template, enforced by the content owner and
the publishing agent, not by this script: every statistic gets an inline, named,
linkable source — the template's "(Source name)" pattern is guidance, not a rule —
and every post links to at least one vertical page so crawl equity reaches it. This
script warns on a body sentence that pairs a digit with no link, but it cannot judge
a claim; that is a human's job.

Safe to re-run: identical inputs produce byte-identical outputs.
"""

import datetime as _dt
import html
import json
import re
import sys
from pathlib import Path

import markdown as _markdown

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "blog" / "_posts"
TEMPLATE = ROOT / "tools" / "blog-post.tmpl.html"
INDEX = ROOT / "blog" / "index.html"
LLMS = ROOT / "llms.txt"

SITE = "https://www.nestlonger.com"
ORG = f"{SITE}/#organization"
WEBSITE = f"{SITE}/#website"
DEFAULT_OG_IMAGE = f"{SITE}/assets/images/grab-bars.webp"

# The content owner edits this list. An unknown category fails the build rather
# than inventing a section.
CATEGORIES = ["Grab bars", "ADUs", "Paying for it", "Planning ahead"]

REQUIRED = ["title", "description", "date", "category"]
SLUG_RE = re.compile(r"^[a-z0-9-]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

MARKERS = {
    "list": ("<!-- BLOG-LIST:START -->", "<!-- BLOG-LIST:END -->"),
    "jsonld": ("<!-- BLOG-JSONLD:START -->", "<!-- BLOG-JSONLD:END -->"),
    "llms": ("<!-- BLOG-POSTS:START -->", "<!-- BLOG-POSTS:END -->"),
}

TODAY = _dt.date.today()


class PostError(Exception):
    """A validation failure that must fail the build with a named field."""


# --------------------------------------------------------------------------- #
# Minimal front-matter parser (no YAML dependency).                            #
# --------------------------------------------------------------------------- #

def _unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_front_matter(text, slug):
    """Split leading `---` front matter from the markdown body.

    Returns (meta_dict, body_str). Scalars become strings; `sources` and `faq`
    become lists of dicts. Unknown shapes fail rather than guess.
    """
    if not text.startswith("---"):
        raise PostError(f"{slug}: missing front matter (file must start with '---')")
    parts = re.split(r"^---[ \t]*$", text, maxsplit=2, flags=re.M)
    # parts[0] is empty (before first ---), parts[1] is front matter, parts[2] body.
    if len(parts) < 3:
        raise PostError(f"{slug}: front matter is not closed with a second '---'")
    fm_lines = parts[1].splitlines()
    body = parts[2].lstrip("\n")

    meta = {}
    i = 0
    n = len(fm_lines)
    while i < n:
        line = fm_lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line[:1] in " \t":
            raise PostError(f"{slug}: unexpected indentation in front matter: {line!r}")
        m = re.match(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$", line)
        if not m:
            raise PostError(f"{slug}: cannot parse front-matter line: {line!r}")
        key, rest = m.group(1), m.group(2).strip()
        if rest == "":
            items, i = _collect_dict_list(fm_lines, i + 1, slug, key)
            meta[key] = items
        else:
            meta[key] = _unquote(rest)
            i += 1
    return meta, body


def _collect_dict_list(lines, i, slug, key):
    """Collect an indented block of `- ` dict items into a list of dicts."""
    items = []
    current = None
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            break  # back to a top-level key
        stripped = line.strip()
        dash = re.match(r"^-[ \t]+(.*)$", stripped)
        if dash:
            current = {}
            items.append(current)
            first = dash.group(1).strip()
            if first:
                kv = re.match(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$", first)
                if not kv:
                    raise PostError(f"{slug}: cannot parse '{key}' item: {stripped!r}")
                current[kv.group(1)] = _unquote(kv.group(2))
        else:
            if current is None:
                raise PostError(f"{slug}: '{key}' block must begin with '- '")
            kv = re.match(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$", stripped)
            if not kv:
                raise PostError(f"{slug}: cannot parse '{key}' field: {stripped!r}")
            current[kv.group(1)] = _unquote(kv.group(2))
        i += 1
    return items, i


# --------------------------------------------------------------------------- #
# Validation.                                                                  #
# --------------------------------------------------------------------------- #

def _valid_date(value, slug, field):
    if not isinstance(value, str) or not DATE_RE.match(value):
        raise PostError(f"{slug}: '{field}' must be YYYY-MM-DD, got {value!r}")
    try:
        return _dt.date.fromisoformat(value)
    except ValueError:
        raise PostError(f"{slug}: '{field}' is not a real date: {value!r}")


def validate(meta, body, slug):
    if not SLUG_RE.match(slug):
        raise PostError(f"{slug}: slug must match [a-z0-9-]+")

    for field in REQUIRED:
        if not meta.get(field):
            raise PostError(f"{slug}: missing required field '{field}'")

    title = meta["title"]
    if len(title) > 110:
        raise PostError(f"{slug}: 'title' is {len(title)} chars, over the 110 limit")

    desc = meta["description"]
    if not (140 <= len(desc) <= 158):
        raise PostError(
            f"{slug}: 'description' is {len(desc)} chars, outside the required 140-158"
        )

    if meta["category"] not in CATEGORIES:
        raise PostError(
            f"{slug}: 'category' {meta['category']!r} is not one of {CATEGORIES}"
        )

    date = _valid_date(meta["date"], slug, "date")
    updated_raw = meta.get("updated") or meta["date"]
    updated = _valid_date(updated_raw, slug, "updated")

    if meta.get("image") and not meta.get("image_alt"):
        raise PostError(f"{slug}: 'image' is set but 'image_alt' is missing")

    faq = meta.get("faq") or []
    if faq and not isinstance(faq, list):
        raise PostError(f"{slug}: 'faq' must be a list of q/a items")
    for entry in faq:
        if not entry.get("q") or not entry.get("a"):
            raise PostError(f"{slug}: every 'faq' item needs a non-empty 'q' and 'a'")

    sources = meta.get("sources") or []
    for entry in sources:
        if not entry.get("name") or not entry.get("url"):
            raise PostError(f"{slug}: every 'sources' item needs 'name' and 'url'")

    meta["_date"] = date
    meta["_updated"] = updated
    return meta


def warn_unsourced(body, slug):
    """Nudge, not a gate: a sentence with a digit and no link. Printed, not fatal."""
    # Strip fenced code so code samples do not trip the check.
    stripped = re.sub(r"```.*?```", "", body, flags=re.S)
    for para in re.split(r"\n\s*\n", stripped):
        for sentence in re.split(r"(?<=[.!?])\s+", para):
            if re.search(r"\d", sentence) and "](" not in sentence and "<a " not in sentence:
                text = " ".join(sentence.split())
                print(f"  warning: {slug}: number without an inline link: {text[:90]}")


# --------------------------------------------------------------------------- #
# Rendering.                                                                   #
# --------------------------------------------------------------------------- #

def human_date(date):
    return f"{date.strftime('%B')} {date.day}, {date.year}"


def og_image(meta):
    img = meta.get("image")
    return f"{SITE}/assets/images/{img}" if img else DEFAULT_OG_IMAGE


def render_body(body):
    md = _markdown.Markdown(extensions=["extra", "sane_lists"], output_format="html5")
    return md.convert(body)


def image_block(meta):
    if not meta.get("image"):
        return ""
    alt = html.escape(meta["image_alt"], quote=True)
    return (
        f'      <img class="nl-post-hero" src="../assets/images/{meta["image"]}" '
        f'width="1200" height="630" alt="{alt}" loading="eager" decoding="async" />\n'
    )


def sources_block(meta):
    sources = meta.get("sources") or []
    if not sources:
        return ""
    lines = ['      <div class="nl-post-sources">', "        <h2>Sources</h2>", "        <ol>"]
    for s in sources:
        name = html.escape(s["name"])
        url = html.escape(s["url"], quote=True)
        retrieved = s.get("retrieved")
        tail = f" Retrieved {html.escape(retrieved)}." if retrieved else ""
        # The source name is the anchor text, not the raw URL: a long unbroken URL
        # overflows the measure on a narrow screen.
        lines.append(f'          <li><a href="{url}">{name}</a>.{tail}</li>')
    lines += ["        </ol>", "      </div>"]
    return "\n".join(lines) + "\n"


def faq_block(meta):
    """Visible nl-faq block. Text is emitted here and into JSON-LD from the same
    source strings, so visible and markup text are identical by construction."""
    faq = meta.get("faq") or []
    if not faq:
        return ""
    lines = [
        '      <section class="nl-post-faq">',
        '        <h2>Common questions</h2>',
        '        <div class="nl-faq-list">',
    ]
    for entry in faq:
        q = html.escape(entry["q"])
        a = html.escape(entry["a"])
        lines += [
            '          <div class="nl-faq-item">',
            f'            <h3 class="nl-faq-q">{q}</h3>',
            f'            <p class="nl-faq-a">{a}</p>',
            "          </div>",
        ]
    lines += ["        </div>", "      </section>"]
    return "\n".join(lines) + "\n"


def related_block(post, published):
    """Up to three other published posts in the same category, newest first."""
    peers = [
        p for p in published
        if p["category"] == post["category"] and p["slug"] != post["slug"]
    ][:3]
    if not peers:
        return ""
    cat = html.escape(post["category"])
    lines = [
        '      <div class="nl-post-related">',
        f"        <h2>More on {cat}</h2>",
        '        <div class="nl-blog-list">',
    ]
    for p in peers:
        lines.append(_blog_item(p, href=f'{p["slug"]}.html'))
    lines += ["        </div>", "      </div>"]
    return "\n".join(lines) + "\n"


def _blog_item(post, href):
    return (
        f'          <a class="nl-blog-item" href="{href}">\n'
        f'            <div class="nl-blog-item-meta"><time datetime="{post["date"]}">'
        f'{post["date_human"]}</time> · {html.escape(post["category"])}</div>\n'
        f'            <h2 class="nl-blog-item-h">{html.escape(post["title"])}</h2>\n'
        f'            <p class="nl-blog-item-body">{html.escape(post["description"])}</p>\n'
        f"          </a>"
    )


def build_jsonld(post):
    article = {
        "@type": "BlogPosting",
        "@id": f"{SITE}/blog/{post['slug']}.html#article",
        "headline": post["title"],
        "description": post["description"],
        "datePublished": post["date"],
        "dateModified": post["updated"],
        "articleSection": post["category"],
        "image": post["og_image"],
        "author": {"@id": ORG},
        "publisher": {"@id": ORG},
        "isPartOf": {"@id": WEBSITE},
        "mainEntityOfPage": f"{SITE}/blog/{post['slug']}.html",
        "inLanguage": "en-US",
    }
    sources = post["meta"].get("sources") or []
    if sources:
        article["citation"] = [s["url"] for s in sources]

    graph = [article]

    faq = post["meta"].get("faq") or []
    if faq:
        graph.append({
            "@type": "FAQPage",
            "@id": f"{SITE}/blog/{post['slug']}.html#faq",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": e["q"],
                    "acceptedAnswer": {"@type": "Answer", "text": e["a"]},
                }
                for e in faq
            ],
        })

    graph.append({
        "@type": "BreadcrumbList",
        "@id": f"{SITE}/blog/{post['slug']}.html#breadcrumb",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": f"{SITE}/blog/"},
            {"@type": "ListItem", "position": 3, "name": post["title"]},
        ],
    })

    doc = {"@context": "https://schema.org", "@graph": graph}
    return json.dumps(doc, indent=2, ensure_ascii=False)


def render_post(post, template, published):
    meta = post["meta"]
    robots = ""
    if post["future"]:
        robots = '  <meta name="robots" content="noindex, nofollow" />\n'
    tokens = {
        "@@ROBOTS@@": robots.rstrip("\n"),
        "@@TITLE@@": html.escape(post["title"], quote=True),
        "@@DESCRIPTION@@": html.escape(post["description"], quote=True),
        "@@SLUG@@": post["slug"],
        "@@OG_IMAGE@@": html.escape(post["og_image"], quote=True),
        "@@DATE@@": post["date"],
        "@@UPDATED@@": post["updated"],
        "@@CATEGORY@@": html.escape(post["category"]),
        "@@DATE_HUMAN@@": post["date_human"],
        "@@JSONLD@@": build_jsonld(post),
        "@@IMAGE_BLOCK@@": image_block(meta).rstrip("\n"),
        "@@BODY@@": post["body_html"],
        "@@SOURCES_BLOCK@@": sources_block(meta).rstrip("\n"),
        "@@FAQ_BLOCK@@": faq_block(meta).rstrip("\n"),
        "@@RELATED_BLOCK@@": related_block(post, published).rstrip("\n"),
    }
    out = template
    for token, value in tokens.items():
        out = out.replace(token, value)
    # Collapse any blank lines left where an optional block was empty.
    out = re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", out)
    return out


# --------------------------------------------------------------------------- #
# Marker rewrites on shared files.                                             #
# --------------------------------------------------------------------------- #

def replace_between(text, start, end, new_inner, path):
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end), re.S
    )
    if not pattern.search(text):
        sys.exit(f"markers {start} ... {end} not found in {path}")
    return pattern.sub(lambda _: f"{start}{new_inner}{end}", text, count=1)


def update_index(published):
    text = INDEX.read_text(encoding="utf-8")

    if published:
        items = "\n".join(_blog_item(p, href=f'{p["slug"]}.html') for p in published)
        list_inner = "\n" + items + "\n        "
    else:
        list_inner = (
            "\n"
            '        <div class="nl-blog-item">\n'
            '          <p class="nl-blog-item-body">\n'
            "            First posts are on the way. In the meantime, the\n"
            '            <a href="../grab-bars.html">grab bars</a> and '
            '<a href="../adus.html">ADU</a>\n'
            "            pages cover the questions we get asked most.\n"
            "          </p>\n"
            "        </div>\n"
            "        "
        )
    text = replace_between(text, *MARKERS["list"], list_inner, INDEX)

    blog_node = {
        "@type": "Blog",
        "@id": f"{SITE}/blog/#blog",
        "name": "Notes on aging at home",
        "description": "Practical writing for adult children arranging home modifications for an aging parent.",
        "url": f"{SITE}/blog/",
        "publisher": {"@id": ORG},
        "isPartOf": {"@id": WEBSITE},
        "inLanguage": "en-US",
    }
    if published:
        blog_node["blogPost"] = [
            {"@id": f"{SITE}/blog/{p['slug']}.html#article"} for p in published
        ]
    doc = {
        "@context": "https://schema.org",
        "@graph": [
            blog_node,
            {
                "@type": "BreadcrumbList",
                "@id": f"{SITE}/blog/#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE}/"},
                    {"@type": "ListItem", "position": 2, "name": "Blog"},
                ],
            },
        ],
    }
    jsonld = json.dumps(doc, indent=2, ensure_ascii=False)
    inner = (
        "\n"
        '  <script type="application/ld+json">\n'
        + jsonld
        + "\n  </script>\n  "
    )
    text = replace_between(text, *MARKERS["jsonld"], inner, INDEX)
    INDEX.write_text(text, encoding="utf-8")


def update_llms(published):
    text = LLMS.read_text(encoding="utf-8")
    if published:
        lines = "\n".join(
            f'- [{p["title"]}]({SITE}/blog/{p["slug"]}.html): {p["description"]}'
            for p in published
        )
        inner = "\n" + lines + "\n"
    else:
        inner = "\n"
    text = replace_between(text, *MARKERS["llms"], inner, LLMS)
    LLMS.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Stale-output cleanup.                                                        #
# --------------------------------------------------------------------------- #

GENERATED_MARK = "GENERATED FILE — do not edit by hand"


def clean_stale(current_slugs):
    for path in sorted((ROOT / "blog").glob("*.html")):
        if path.name == "index.html":
            continue
        slug = path.stem
        text = path.read_text(encoding="utf-8", errors="ignore")
        if GENERATED_MARK in text and slug not in current_slugs:
            path.unlink()
            print(f"  removed stale post: blog/{path.name}")


# --------------------------------------------------------------------------- #
# Main.                                                                        #
# --------------------------------------------------------------------------- #

def main():
    if not TEMPLATE.exists():
        sys.exit(f"missing template: {TEMPLATE.relative_to(ROOT)}")
    template = TEMPLATE.read_text(encoding="utf-8")

    posts = []
    if POSTS_DIR.exists():
        for path in sorted(POSTS_DIR.glob("*.md")):
            slug = path.stem
            try:
                meta, body = parse_front_matter(path.read_text(encoding="utf-8"), slug)
                validate(meta, body, slug)
            except PostError as exc:
                sys.exit(f"  BUILD FAILED: {exc}")
            warn_unsourced(body, slug)
            date = meta["_date"]
            posts.append({
                "slug": slug,
                "meta": meta,
                "title": meta["title"],
                "description": meta["description"],
                "category": meta["category"],
                "date": meta["date"],
                "updated": meta["_updated"].isoformat(),
                "date_human": human_date(date),
                "og_image": og_image(meta),
                "body_html": render_body(body),
                "future": date > TODAY,
            })

    current_slugs = {p["slug"] for p in posts}
    clean_stale(current_slugs)

    # Published = not future-dated. Newest first, slug as a stable tie-break.
    published = sorted(
        (p for p in posts if not p["future"]),
        key=lambda p: (p["date"], p["slug"]),
        reverse=True,
    )

    for post in posts:
        html_out = render_post(post, template, published)
        out_path = ROOT / "blog" / f"{post['slug']}.html"
        out_path.write_text(html_out, encoding="utf-8")
        state = "draft (noindex, future date)" if post["future"] else "published"
        print(f"  wrote blog/{post['slug']}.html ({state})")

    update_index(published)
    update_llms(published)

    print(
        f"\n  {len(posts)} post(s): {len(published)} published, "
        f"{len(posts) - len(published)} future-dated draft(s)."
    )


if __name__ == "__main__":
    main()
