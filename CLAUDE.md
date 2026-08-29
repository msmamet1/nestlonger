# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

The public marketing site for **www.nestlonger.com** — a matchmaking service connecting families with certified professionals for aging-in-place home modifications (grab bars, ADUs). Hand-written static HTML served by GitHub Pages from the repository root.

## Commands

There is no build, bundler, package manager, test suite, or linter. `.nojekyll` disables Jekyll processing, so files are served exactly as committed.

```bash
python3 -m http.server 8000        # local preview at http://localhost:8000
python3 tools/fingerprint-css.py   # REQUIRED after any edit to assets/styles.css
python3 tools/build-sitemap.py     # regenerate sitemap.xml after adding/removing a page
git push origin main               # deploy — GitHub Pages publishes from main at repo root
```

### ⚠️ Run `fingerprint-css.py` after every stylesheet edit

Pages link `assets/styles.css?v=<sha256[:10]>`. The hash is derived from the file's
own bytes, so it cannot be forgotten the way a hand-incremented `?v=2` can — but the
script has to be run, and it must run **after** the CSS edit, not before.

Without it, a returning visitor arriving within the 4-hour cache window gets the new
HTML and the old CSS. On `get-matched.html` that used to render as unstyled
browser-default fields with the spam honeypot showing as a visible "Company website"
input on a real form. The honeypot is now hidden by an **inline** style as well as by
`.nl-hp`, specifically so a missing stylesheet cannot expose it — do not remove that
inline style.

`.github/workflows/generated-files.yml` runs both this script and `build-sitemap.py`
on every push to `main` and commits the result back if either changed a file, so a
forgotten run repairs itself. That is a backstop, not a substitute: the site is live
with the stale artifact for the one to two minutes the workflow takes. Run the script
yourself and push one correct commit.

The fingerprint is a query string, not a hashed filename, so `worker/index.js` can keep
referencing `/assets/styles.css` on its error page. The zone's cache level is
`aggressive` (Cloudflare's "Standard"), which includes the query string in the cache
key, so this busts edge and browser caches together.

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

## Definition of done

A task is done when every acceptance criterion is verifiably true against the live site at `https://www.nestlonger.com`, not against the repo. Pages deploy in roughly 30 to 60 seconds; assets need a cache purge first, per the warning above. Report the actual HTTP status or rendered output observed.

Matthew works in a local checkout that has diverged from `origin/main` before. Pull and rebase before starting, and say so when you finish.

Specs live in `msmamet1/pga` at `ventures/nestlonger/specs/`, written by the engagement manager and executed here. Open both repos in one VS Code workspace rather than copying specs into this one, since everything tracked here is served publicly. Completion notes, research inputs, and measurement baselines are written back to pga.

## Architecture

**Ten standalone HTML pages, no templating.** Six content pages (`index`, `grab-bars`, `adus`, `partners`, `about`, `privacy`), three form pages (`get-matched`, `partner-apply`, `thanks`), and `404.html`. Every page carries its own full copy of the nav, footer, and GA4 snippet. Changing any shared block means editing all of them.

**The shared blocks are not byte-identical**, so blind find-and-replace across pages will corrupt them. Per-page variations to preserve:

- nav CTA target and label (`Get matched` → `get-matched.html?src=<page>`, except partners → `Apply to join` → `partner-apply.html`); form pages have no nav CTA at all
- `class="is-active"` on the nav link matching the current page — **in two places**, the inline bar link and the mobile disclosure panel link
- `404.html` uses root-absolute paths (`/adus.html`, `/assets/styles.css`); all other pages use relative paths (`adus.html`); `blog/` uses `../`

**Mobile nav** is a native `<details class="nl-nav-mobile">` disclosure inside `.nl-nav-links`, shown only below 880px. No JavaScript. Because the panel's links are nested inside `.nl-nav-links`, every rule targeting the inline bar links is scoped with `>` (`.nl-nav-links > a:not(.nl-btn)`). Dropping that combinator makes the mobile rule `display: none` hide the panel's own links, and the menu opens as an empty box.

**Lead capture uses no third-party form service.** Three native HTML forms post same-origin to `/api/*`, handled by a Cloudflare Worker (`nestlonger-forms`) that writes to a D1 database (`nestlonger-leads`) and answers with a 303 to `thanks.html`. No JS is needed to submit. Worker source is in `worker/`; see README "Lead capture → The backend" for the deploy and query commands.

This only works because **the zone is proxied through Cloudflare** — the Worker intercepts `/api/*` before the request reaches GitHub Pages. If the proxy is ever switched to DNS-only, every form silently breaks.

The per-vertical routing that Tally's `data-source` used to provide now rides on `?src=` in the CTA href; four lines of inline script on `get-matched.html` copy it into a hidden `source` field, falling back to `site` without JS. Sources in use: `homepage`, `grab-bars`, `adus`, `about`, `privacy`, `404`, plus `newsletter`.

Spam protection is a `website` honeypot plus per-IP rate limiting in the Worker — deliberately no CAPTCHA, since Turnstile would reintroduce a third-party script.

⚠️ **Cloudflare Bot Fight Mode must stay off.** It was enabled until 2026-08-11. Free-plan Bot Fight Mode has no verified-crawler exemption, and it would block form POSTs to the Worker, so it stays off. It was previously blamed for the site's near-zero search traffic. That is false. Search Console shows Googlebot smartphone fetched `grab-bars.html` successfully on 8 August 2026 and indexed it, with crawl allowed and indexing allowed, three days before the mode was disabled. The 0 organic keywords and 3 impressions over 3.5 months is a ranking problem, not an access problem, which is an ordinary result for a three-month-old domain with thin content and a spam-only link profile. Full write-up in `pga/ventures/nestlonger/2026-08-11-crawlability-root-cause.md`.

Two further Cloudflare settings were corrected on 2026-08-11 and must not regress.

**AI Scrapers and Crawlers (`ai_bots_protection`) must stay `disabled`.** When set to `block` it disallowed ClaudeBot, GPTBot, Google-Extended, CCBot, meta-externalagent, Amazonbot, Applebot-Extended, and Bytespider. Answer-engine citation is the primary traffic strategy for this site, so blocking those agents defeats the plan.

**Managed robots.txt (`is_robots_txt_managed`) must stay `false`.** When true, Cloudflare injected its own robots.txt over the one in this repo, so editing `robots.txt` here had no effect on what was served. If a robots.txt change appears not to deploy, check this setting before debugging anything else.

Disabling the AI crawler block also removed Cloudflare's `Content-Signal` directives, including `ai-train=no`, which was a rights reservation under Article 4 of the EU copyright directive. That removal was intentional.

**Analytics**: GA4 `G-D2CB1LRG5P`, inline on every page including 404.

**Styling** is one consolidated `assets/styles.css` (~900 lines), organized by `/* ===== SECTION ===== */` comments — design tokens first, then the shared UI kit (nav, buttons, sections, stats, steps, footer), then page-specific blocks (`HOMEPAGE`, `PARTNER PAGE`, `ABOUT PAGE`, `PRIVACY PAGE`, `404`), with `RESPONSIVE` last. Everything is driven by `--nl-*` custom properties in `:root` (colors, semantic aliases, type, spacing, radius, borders, shadows) — use the existing tokens rather than introducing raw hex values or new one-off variables. Google Fonts arrive via `@import` at the top of the stylesheet, not via `<link>` tags in the HTML.

Class names are all `nl-` prefixed and semantic (`nl-vert-card`, `nl-prob-cell`, `nl-trustsig-grid`). There is no utility-class system.

## Brand and copy

The brand guide lives **outside this repo**, in `pga/ventures/nestlonger` — it is the source of truth for voice, palette, type, and UI patterns, and it is prescriptive, including a **Never Say** list (notably: "loved one", "senior/elderly", "journey", "seamless/robust/holistic", "empowering families to"). Read it before writing any user-facing copy or adding visual components; ask for it if the PGA repo is not attached to the session.

Write for the adult child, not the aging parent. Clear, warm, practical.

## No unsourced statistics

Every numeric claim on a public page carries an inline attribution to a named, linkable source, or it does not ship. This applies to body copy, headings, the `description` / `og:description` / `twitter:description` trio, image alt text, and JSON-LD.

The category is health-adjacent, where an inaccurate efficacy or coverage claim is a trust and compliance liability rather than just a missed ranking. Answer engines also preferentially cite pages that attribute their claims, which makes this the cheapest AEO improvement available.

If a task hands you a claim without a citation, stop and flag it. Do not source it yourself, do not infer a source, do not substitute a similar figure from a different study. The "reduces falls by up to 80%" claim is what happens without this rule. It is attributed across the web to a CDC study that does not exist, and it originates as a misread of a statistic about where falls occur rather than what prevents them. It was removed from `grab-bars.html`, then found again eight days later on `about.html`, which is why the sweeps below are scoped by claim rather than by page.

Insurance and public-program coverage claims carry a further rule. State the plan year, and never assert that a specific plan covers a specific modification. CMS narrowed Special Supplemental Benefits for the Chronically Ill for 2026, and coverage now depends on plan, county, plan year, and documented condition.

### Bare scope quantifiers

A bare scope quantifier is a statistic. "Most", "many", "a lot of", "usually", "often" and "commonly" all assert a proportion without stating one, and they are subject to the no-unsourced-statistics rule exactly as a percentage is. Do not soften an unsourceable "most" to "many"; that is the same claim with a smaller number. Either state the real figure with a source, or make the sentence about something you can support. The site has produced eight of these; assume there is a ninth.

Two things are not in this class and are always fine. Statements about NestLonger's own service ("usually within one business day", "we typically respond within two business days") are first-party operational commitments, not claims about the world. Quantifiers that weaken a claim rather than carry it ("estimates vary widely", "nearly all of that research comes from California") are hedges, and removing them would make the sentence less accurate, not more.

### Coverage claims

A coverage claim is any statement that an insurer, plan, or benefit program covers, reimburses, is likely to cover, or commonly covers anything. This includes prevalence claims ("most families", "a lot of plans"), likelihood badges ("often covered"), and adjectives that imply coverage ("insurance-friendly"). Do not publish one. Statements about what NestLonger does, such as checking a plan or helping submit, are not coverage claims and are always fine.

Coverage claims hide in eight places, and a fix that touches only one of them is not a fix: headings, hero stat labels, trust bars, badges and tags, card body copy, FAQ answers, JSON-LD of every type, and meta descriptions. Sweep all eight.

This rule exists because three consecutive specs each removed the same class of claim from one artifact and left it standing on another — the JSON-LD, then the card copy, then the heading, stat label, and trust bar above them. Scope by claim, not by component.

## When adding or renaming a page

1. Run `python3 tools/build-sitemap.py` — **never hand-edit `sitemap.xml`**. It discovers pages from the filesystem and skips anything with a `noindex` meta tag.
2. Add the nav/footer link to every other page (they are independent copies)
3. Pick a `?src=` value for its CTAs
4. Set canonical, OG, and Twitter meta to the `https://www.nestlonger.com/…` absolute URL
5. Reference the shared schema `@id`s rather than redeclaring the Organization

Blog posts are generated from markdown, not hand-authored HTML. Commit one file, `blog/_posts/<slug>.md` (YAML front matter plus a markdown body), and nothing else; on push, CI runs `tools/build-blog.py` to render `blog/<slug>.html` from `tools/blog-post.tmpl.html`, rewrite the post list and Blog JSON-LD on `blog/index.html`, and update the blog section of `llms.txt`, then the sitemap and fingerprint scripts run and the bot commits the result. The full field table and the validation rules are in README, "Adding a blog post". A future-dated post renders with `noindex` and stays out of the index, `llms.txt`, and the sitemap until its date passes, so drafts can be committed ahead of time. Preview locally with `pip install markdown` then `python3 tools/build-blog.py`.

## SEO artifacts

`robots.txt` points at the sitemap; `CNAME` pins the custom domain, do not remove it. `llms.txt` is the AEO site summary and page index — update it when pages are added or their purpose changes.

**GitHub Pages serves every file in this repository**, with no way to make one private. Internal working documents therefore do not belong here — the brand guide and the Google Search Console disavow list were moved out to `pga/ventures/nestlonger` for exactly this reason. Anything added here should be assumed public.

The disavow list is maintained in the PGA repo. The rule that matters when editing it: **disavow uploads replace the live list rather than merging into it**, so that file is the cumulative source of truth — merge new Ahrefs exports into it and re-upload the whole thing, never upload a raw export. As of 2026-08-11 the live list is 422 domains / 0 URLs.
