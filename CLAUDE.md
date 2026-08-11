# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

The public marketing site for **www.nestlonger.com** — a matchmaking service connecting families with certified professionals for aging-in-place home modifications (grab bars, ADUs). Hand-written static HTML served by GitHub Pages from the repository root.

## Commands

There is no build, bundler, package manager, test suite, or linter. `.nojekyll` disables Jekyll processing, so files are served exactly as committed.

```bash
python3 -m http.server 8000       # local preview at http://localhost:8000
python3 tools/build-sitemap.py    # regenerate sitemap.xml after adding/removing a page
git push origin main              # deploy — GitHub Pages publishes from main at repo root
```

Preview must be served over HTTP, not opened via `file://` — `404.html` uses root-absolute paths that only resolve from a server root.

### ⚠️ Always purge the Cloudflare cache after changing CSS or any asset

The site is proxied through Cloudflare, which caches static assets for **4 hours**
(`cache-control: max-age=14400`). HTML updates appear straight after a Pages deploy;
`assets/styles.css`, images, and other static files **do not**. Pushing is not enough —
without a purge, visitors and you keep getting the old file, and the change looks like
it silently failed to deploy.

This has already bitten once: a stylesheet edit deployed correctly but Cloudflare served
the previous version for the next several hours.

Purge after every change to `assets/**` — via the Cloudflare MCP:

```js
cloudflare.request({
  method: "POST",
  path: "/zones/11efc27bae375de8ba52baee28ff7a13/purge_cache",
  body: { files: ["https://www.nestlonger.com/assets/styles.css"] }   // or { purge_everything: true }
})
```

or Cloudflare dashboard → nestlonger.com → Caching → Configuration → Purge Everything.

Then confirm the new bytes are actually being served, rather than assuming:

```bash
curl -s https://www.nestlonger.com/assets/styles.css | grep "<something you just added>"
```

## Architecture

**Ten standalone HTML pages, no templating.** Six content pages (`index`, `grab-bars`, `adus`, `partners`, `about`, `privacy`), three form pages (`get-matched`, `partner-apply`, `thanks`), and `404.html`. Every page carries its own full copy of the nav, footer, and GA4 snippet. Changing any shared block means editing all of them.

**The shared blocks are not byte-identical**, so blind find-and-replace across pages will corrupt them. Per-page variations to preserve:

- nav CTA target and label (`Get matched` → `get-matched.html?src=<page>`, except partners → `Apply to join` → `partner-apply.html`); form pages have no nav CTA at all
- `class="is-active"` on the nav link matching the current page
- `404.html` uses root-absolute paths (`/adus.html`, `/assets/styles.css`); all other pages use relative paths (`adus.html`)

**Lead capture uses no third-party form service.** Three native HTML forms post same-origin to `/api/*`, handled by a Cloudflare Worker (`nestlonger-forms`) that writes to a D1 database (`nestlonger-leads`) and answers with a 303 to `thanks.html`. No JS is needed to submit. Worker source is in `worker/`; see README "Lead capture → The backend" for the deploy and query commands.

This only works because **the zone is proxied through Cloudflare** — the Worker intercepts `/api/*` before the request reaches GitHub Pages. If the proxy is ever switched to DNS-only, every form silently breaks.

The per-vertical routing that Tally's `data-source` used to provide now rides on `?src=` in the CTA href; four lines of inline script on `get-matched.html` copy it into a hidden `source` field, falling back to `site` without JS. Sources in use: `homepage`, `grab-bars`, `adus`, `about`, `privacy`, `404`, plus `newsletter`.

Spam protection is a `website` honeypot plus per-IP rate limiting in the Worker — deliberately no CAPTCHA, since Turnstile would reintroduce a third-party script.

⚠️ **Cloudflare Bot Fight Mode must stay off.** It was enabled until 2026-08-11 and was serving a 403 managed challenge on every HTML page — Googlebot cannot solve a JS challenge, so the site was uncrawlable (0 organic keywords, 3 impressions in 3.5 months). Free-plan Bot Fight Mode has no verified-crawler exemption. It would also block form POSTs.

**Analytics**: GA4 `G-D2CB1LRG5P`, inline on every page including 404.

**Styling** is one consolidated `assets/styles.css` (~900 lines), organized by `/* ===== SECTION ===== */` comments — design tokens first, then the shared UI kit (nav, buttons, sections, stats, steps, footer), then page-specific blocks (`HOMEPAGE`, `PARTNER PAGE`, `ABOUT PAGE`, `PRIVACY PAGE`, `404`), with `RESPONSIVE` last. Everything is driven by `--nl-*` custom properties in `:root` (colors, semantic aliases, type, spacing, radius, borders, shadows) — use the existing tokens rather than introducing raw hex values or new one-off variables. Google Fonts arrive via `@import` at the top of the stylesheet, not via `<link>` tags in the HTML.

Class names are all `nl-` prefixed and semantic (`nl-vert-card`, `nl-prob-cell`, `nl-trustsig-grid`). There is no utility-class system.

## Brand and copy

The brand guide lives **outside this repo**, in `pga/clients/nestlonger` — it is the source of truth for voice, palette, type, and UI patterns, and it is prescriptive, including a **Never Say** list (notably: "loved one", "senior/elderly", "journey", "seamless/robust/holistic", "empowering families to"). Read it before writing any user-facing copy or adding visual components; ask for it if the PGA repo is not attached to the session.

Write for the adult child, not the aging parent. Clear, warm, practical.

## When adding or renaming a page

1. Run `python3 tools/build-sitemap.py` — **never hand-edit `sitemap.xml`**. It discovers pages from the filesystem and skips anything with a `noindex` meta tag.
2. Add the nav/footer link to every other page (they are independent copies)
3. Pick a `?src=` value for its CTAs
4. Set canonical, OG, and Twitter meta to the `https://www.nestlonger.com/…` absolute URL
5. Reference the shared schema `@id`s rather than redeclaring the Organization

Blog posts start from `blog/_template.html`; the full checklist is in README, "Adding a blog post". The template carries a `noindex` tag that **must be deleted** in a real post — it is what keeps the template itself out of the sitemap and search results.

## SEO artifacts

`robots.txt` points at the sitemap; `CNAME` pins the custom domain, do not remove it. `llms.txt` is the AEO site summary and page index — update it when pages are added or their purpose changes.

**GitHub Pages serves every file in this repository**, with no way to make one private. Internal working documents therefore do not belong here — the brand guide and the Google Search Console disavow list were moved out to `pga/clients/nestlonger` for exactly this reason. Anything added here should be assumed public.

The disavow list is maintained in the PGA repo. The rule that matters when editing it: **disavow uploads replace the live list rather than merging into it**, so that file is the cumulative source of truth — merge new Ahrefs exports into it and re-upload the whole thing, never upload a raw export. As of 2026-08-11 the live list is 422 domains / 0 URLs.
