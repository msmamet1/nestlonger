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

**Ten standalone HTML pages, no templating.** Six content pages (`index`, `grab-bars`, `adus`, `partners`, `about`, `privacy`), three form pages (`get-matched`, `partner-apply`, `thanks`), and `404.html`. Every page carries its own full copy of the nav, footer, and GA4 snippet. Changing any shared block means editing all of them.

**The shared blocks are not byte-identical**, so blind find-and-replace across pages will corrupt them. Per-page variations to preserve:

- nav CTA target and label (`Get matched` → `get-matched.html?src=<page>`, except partners → `Apply to join` → `partner-apply.html`); form pages have no nav CTA at all
- `class="is-active"` on the nav link matching the current page
- `404.html` uses root-absolute paths (`/adus.html`, `/assets/styles.css`); all other pages use relative paths (`adus.html`)

**Lead capture** is three native HTML forms posting directly to a form endpoint — no third-party script, no JS needed to submit. `get-matched.html` (families), `partner-apply.html` (contractors), and an inline newsletter form on the homepage. All CTAs are `<a class="nl-btn">` links, not buttons.

The per-vertical routing that Tally's `data-source` used to provide now rides on `?src=` in the CTA href; four lines of inline script on `get-matched.html` copy it into a hidden `source` field, falling back to `site` without JS. Sources in use: `homepage`, `grab-bars`, `adus`, `about`, `privacy`, `404`, plus fixed `partner-application` and `newsletter`.

⚠️ **The forms post to the placeholder `FORMSPREE_FORM_ID` and are not live until it is replaced.** See README "Lead capture → Setup". Spam protection is a `_gotcha` honeypot only — deliberately no CAPTCHA, since that would reintroduce a third-party script.

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

**GitHub Pages serves every file in this repository**, with no way to make one private. Internal working documents therefore do not belong here — the brand guide and the Google Search Console disavow list were moved out to `pga/clients/nestlonger` for exactly this reason. Anything added here should be assumed public.

The disavow list is maintained in the PGA repo. The rule that matters when editing it: **disavow uploads replace the live list rather than merging into it**, so that file is the cumulative source of truth — merge new Ahrefs exports into it and re-upload the whole thing, never upload a raw export. As of 2026-08-11 the live list is 422 domains / 0 URLs.
