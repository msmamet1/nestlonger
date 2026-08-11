# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

The public marketing site for **www.nestlonger.com** — a matchmaking service connecting families with certified professionals for aging-in-place home modifications (grab bars, ADUs). Hand-written static HTML served by GitHub Pages from the repository root.

## Commands

There is no build, bundler, package manager, test suite, or linter. `.nojekyll` disables Jekyll processing, so files are served exactly as committed.

```bash
python3 -m http.server 8000    # local preview at http://localhost:8000
git push origin main            # deploy — GitHub Pages publishes from main at repo root
```

Preview must be served over HTTP, not opened via `file://` — `404.html` uses root-absolute paths that only resolve from a server root.

## Architecture

**Seven standalone HTML pages, no templating.** `index.html`, `grab-bars.html`, `adus.html`, `partners.html`, `about.html`, `privacy.html`, `404.html`. Every page carries its own full copy of the nav, footer, GA4 snippet, and Tally script. Changing any shared block means editing all seven files.

**The shared blocks are not byte-identical**, so blind find-and-replace across pages will corrupt them. Per-page variations to preserve:

- nav CTA `data-source` value (one per page) and its label (`Get matched`, except partners → `Apply to join`)
- `class="is-active"` on the nav link matching the current page
- `404.html` uses root-absolute paths (`/adus.html`, `/assets/styles.css`); all other pages use relative paths (`adus.html`)

**Lead capture** is a single Tally popup (form ID `7R49EL`) behind a delegated click handler. Any element with `data-tally-cta` opens it; its `data-source` attribute is passed as a hidden field so leads route by vertical. Current values: `homepage`, `newsletter`, `grab-bars`, `adus`, `partners`, `about`, `privacy`, `404`. If the Tally widget script hasn't loaded, the handler falls back to a full-page redirect to `tally.so/r/7R49EL?source=…`. Note: `README.md` still describes the form ID as an unreplaced `TALLY_FORM_ID` placeholder — that is stale, the real ID is wired into every page.

**Analytics**: GA4 `G-D2CB1LRG5P`, inline on every page including 404.

**Styling** is one consolidated `assets/styles.css` (~900 lines), organized by `/* ===== SECTION ===== */` comments — design tokens first, then the shared UI kit (nav, buttons, sections, stats, steps, footer), then page-specific blocks (`HOMEPAGE`, `PARTNER PAGE`, `ABOUT PAGE`, `PRIVACY PAGE`, `404`), with `RESPONSIVE` last. Everything is driven by `--nl-*` custom properties in `:root` (colors, semantic aliases, type, spacing, radius, borders, shadows) — use the existing tokens rather than introducing raw hex values or new one-off variables. Google Fonts arrive via `@import` at the top of the stylesheet, not via `<link>` tags in the HTML.

Class names are all `nl-` prefixed and semantic (`nl-vert-card`, `nl-prob-cell`, `nl-trustsig-grid`). There is no utility-class system.

## Brand and copy

The brand guide lives **outside this repo**, in `pga/clients/nestlonger` — it is the source of truth for voice, palette, type, and UI patterns, and it is prescriptive, including a **Never Say** list (notably: "loved one", "senior/elderly", "journey", "seamless/robust/holistic", "empowering families to"). Read it before writing any user-facing copy or adding visual components; ask for it if the PGA repo is not attached to the session.

Write for the adult child, not the aging parent. Clear, warm, practical.

## When adding or renaming a page

1. Add a `<loc>` entry to `sitemap.xml` (it lists the six real pages; 404 is correctly excluded)
2. Add the nav/footer link to all seven pages
3. Pick a new `data-source` value for its CTAs
4. Set canonical, OG, and Twitter meta to the `https://www.nestlonger.com/…` absolute URL

## SEO artifacts

`robots.txt` points at the sitemap; `CNAME` pins the custom domain, do not remove it. `llms.txt` is the AEO site summary and page index — update it when pages are added or their purpose changes.

**GitHub Pages serves every file in this repository**, with no way to make one private. Internal working documents therefore do not belong here — the brand guide and the Google Search Console disavow list were moved out to `pga/clients/nestlonger` for exactly this reason. `robots.txt` still carries a `Disallow: /internal/` rule from before that move; it is inert but harmless.

The disavow list is maintained in the PGA repo. The rule that matters when editing it: **disavow uploads replace the live list rather than merging into it**, so that file is the cumulative source of truth — merge new Ahrefs exports into it and re-upload the whole thing, never upload a raw export. As of 2026-08-11 the live list is 422 domains / 0 URLs.
