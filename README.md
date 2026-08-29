# NestLonger — public marketing site

Static HTML site for **www.nestlonger.com**. Hosted on GitHub Pages, served from the repository root. No build step.

## Structure

```
/                      ← GitHub Pages serves from here
├── index.html         ← Homepage
├── grab-bars.html
├── adus.html
├── partners.html
├── about.html
├── privacy.html
├── get-matched.html   ← family lead form
├── partner-apply.html ← contractor application form
├── thanks.html        ← post-submit confirmation (noindex)
├── 404.html
├── sitemap.xml
├── robots.txt
├── CNAME              ← www.nestlonger.com
├── .nojekyll          ← disables Jekyll processing
├── llms.txt           ← AEO site summary and page index
└── assets/
    ├── styles.css     ← single consolidated stylesheet
    ├── favicon.png
    ├── wordmark.svg   ← used in grab-bars.html JSON-LD logo field
    ├── wordmark-light.svg
    └── images/        ← page imagery (WebP)
```

Pages serves every file in the repository, and there is no way to make one private.
Internal working documents — the brand guide, the Search Console disavow list — live
in `pga/ventures/nestlonger`, not here. Keep it that way.

## Deployment

`git push` to `main`. GitHub Pages handles the rest. There is no build, no bundler, no npm.

## Lead capture

Three native HTML forms, each posting directly to a form endpoint. **No third-party
script and no JavaScript is required to submit** — the browser handles validation and
the POST. There is no backend to run.

| Form | Page | Reached from |
|---|---|---|
| Family lead | `get-matched.html` | every "Get matched" CTA |
| Partner application | `partner-apply.html` | both CTAs on `partners.html` |
| Newsletter | inline on `index.html` | homepage email block |

CTAs are plain `<a>` links styled with `.nl-btn`, not buttons. The entry point rides
along as `?src=<source>` and a four-line inline script on `get-matched.html` copies it
into a hidden `source` field, preserving the per-vertical routing the old Tally
`data-source` attribute provided. With JavaScript disabled the field falls back to
`site` and the form still submits.

Spam is handled by a `website` honeypot field, hidden via `.nl-hp`, plus per-IP rate
limiting in the Worker. No CAPTCHA — Turnstile would reintroduce the third-party script
this setup exists to remove.

### The backend

There is no form vendor. Submissions post **same-origin** to a Cloudflare Worker on this
site's own domain, which writes to a D1 database owned by the account.

```
Browser ──POST /api/lead──▶ Worker "nestlonger-forms"
                              ├─▶ honeypot + validation + rate limit
                              ├─▶ INSERT into D1 "nestlonger-leads"
                              ├─▶ Slack webhook (if SLACK_WEBHOOK_URL is set)
                              └─▶ 303 ──▶ /thanks.html
```

| Endpoint | Table | Form |
|---|---|---|
| `/api/lead` | `leads` | `get-matched.html` |
| `/api/partner` | `partners` | `partner-apply.html` |
| `/api/subscribe` | `subscribers` | homepage newsletter |

This works because the zone is proxied through Cloudflare, so the Worker intercepts
`/api/*` before the request reaches GitHub Pages. Everything else still comes from Pages.

Source lives in [`worker/`](worker/) — `index.js` and `schema.sql`. It holds no secrets
(`SLACK_WEBHOOK_URL` and `IP_SALT` are Worker secrets), so its being publicly served is
harmless. Redeploy after editing:

```bash
npx wrangler deploy worker/index.js --name nestlonger-forms
```

Read the leads (CSV-friendly):

```bash
npx wrangler d1 execute nestlonger-leads --remote \
  --command "SELECT * FROM leads ORDER BY created_at DESC" --json
```

**On the data:** these tables hold a ZIP plus free-text notes about an elderly person's
home. Treat them as sensitive. The submitter's IP is stored only as a salted hash, never
raw.

## Adding a blog post

A post is **one markdown file**: `blog/_posts/<slug>.md`, YAML front matter plus a
markdown body. You commit that file and nothing else. On push to `main`, CI runs
`tools/build-blog.py`, which renders `blog/<slug>.html` from
`tools/blog-post.tmpl.html`, rewrites the post list and Blog JSON-LD on
`blog/index.html`, and updates the blog section of `llms.txt`; then the sitemap and
CSS fingerprint scripts run, and the bot commits the result back. Nothing about the
HTML, the index, the sitemap, or `llms.txt` is touched by hand.

To preview locally before pushing: `pip install markdown` once, then
`python3 tools/build-blog.py` and open the generated `blog/<slug>.html`.

### Front matter

The slug is the filename. Fields are required unless marked optional.

| Field | Rule |
| --- | --- |
| `title` | Under 110 characters. Becomes `<title>`, `og:title`, the `headline`, and the breadcrumb name. |
| `description` | 140–158 characters. Becomes the meta description, `og:description`, `twitter:description`, and the BlogPosting `description`. |
| `date` | `YYYY-MM-DD`. The published date, visible and in the schema. |
| `updated` | `YYYY-MM-DD`, optional; defaults to `date`. Drives `dateModified` and the sitemap `<lastmod>`. |
| `category` | Must be one of the `CATEGORIES` at the top of `tools/build-blog.py` (`Grab bars`, `ADUs`, `Paying for it`, `Planning ahead`). An unknown value fails the build. |
| `image` | Optional. A filename under `assets/images/`, 1200×630 webp. Defaults to the site-wide OG image when absent. |
| `image_alt` | Required **only** when `image` is set. The image's alt text. |
| `sources` | Optional list of `{name, url, retrieved}`. Rendered as the Sources block and carried into the BlogPosting `citation`. |
| `faq` | Optional list of `{q, a}`. Rendered as a visible FAQ block and as `FAQPage` JSON-LD with identical text. Omit the key and neither appears. |

Example:

```markdown
---
title: What grab bar installation actually costs
description: A plain-language walkthrough of what a bathroom grab bar job runs, what drives the price, and how to arrange it without guesswork or a sales pitch.
date: 2026-09-15
category: Grab bars
sources:
  - name: Cochrane systematic review, 2023
    url: https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.CD013258.pub2/full
    retrieved: 2026-09-15
faq:
  - q: How long does a typical installation take?
    a: About two hours per bathroom for a standard job.
---

Lead with the outcome for the adult child doing the arranging.

## A section heading

Body copy, with a [link to a vertical page](../grab-bars.html) so crawl equity
reaches it.
```

The build **fails** (committing nothing) on a missing required field, a description
out of range, a title over 110 characters, an unknown category, a malformed date, a
slug that is not `[a-z0-9-]+`, an `image` without `image_alt`, or an empty `faq`
question or answer. It **warns** (but does not block) on a body sentence that pairs a
number with no link, as a nudge toward the rule below.

A post whose `date` is in the future is rendered with `noindex` and left out of the
index list, `llms.txt`, and the sitemap, so a draft can be committed ahead of its
date and goes live on the first CI run after it.

Two editorial rules, enforced by the author, not the script — `llms.txt` tells AI
crawlers this site attributes its claims:

- **Every statistic gets an inline, named, linkable source.** No unsourced numbers.
- **Link to at least one vertical page** (`grab-bars.html`, `adus.html`) from each
  post. That is how crawl equity reaches the pages that convert.

Voice, palette, and the "Never Say" list live in the brand guide in
`pga/ventures/nestlonger`, not this repo.

## Verifying a deploy

A deploy is only done when it is true against the live site, not the repo. That
check is automated: **`.github/workflows/verify-live.yml`** runs
`tools/verify-live.py` on a GitHub runner after every push to `main` (chained off
the "Generated files" workflow, so it sees the bot's regenerated commit too). It
polls the live homepage until it serves the CSS fingerprint that was just
committed — waiting out the GitHub Pages publish — then asserts the blog index,
the "Blog" nav link, the stylesheet, `sitemap.xml`, `llms.txt`, and every
published post are live and correctly (non-)indexed. A bad or non-propagated
deploy turns the check red.

Runners have full internet egress, so this works even when the change was shipped
from an environment with no outbound web access (the Claude Code cloud sandbox's
"trusted network access" policy blocks arbitrary sites). To run the same checks
by hand from any machine with web access:

```bash
python3 tools/verify-live.py                    # checks https://www.nestlonger.com
SITE=https://www.nestlonger.com python3 tools/verify-live.py
```

## Analytics

Google Analytics 4 (`G-D2CB1LRG5P`) is wired into every page including 404.

## Working on the site

Edit the HTML directly. Page sections are duplicated across files (no templating); update each page when changing nav, footer, or shared blocks.

CSS lives in a single `assets/styles.css` — design tokens, kit components, and page-specific extensions are all in one file, organized by section comment.
