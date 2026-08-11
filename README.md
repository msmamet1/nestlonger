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
in `pga/clients/nestlonger`, not here. Keep it that way.

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

Posts are hand-authored HTML in `blog/`. There is no build step and no CMS.

1. `cp blog/_template.html blog/<your-slug>.html`
2. Replace every `{{ ... }}` placeholder, and **delete the `noindex` meta tag** —
   it exists to keep the template itself out of search results.
3. Add a listing entry at the top of the list in `blog/index.html` (a commented-out
   example block is there to copy).
4. Regenerate the sitemap: `python3 tools/build-sitemap.py`
5. Commit and push.

The generator discovers pages from the filesystem rather than a hand-maintained
list, and skips anything carrying a `noindex` meta tag — so a post cannot be left
out of the sitemap by forgetting to add it, and drafts stay out by keeping the tag.

Two editorial rules carried over from `llms.txt`, which tells AI crawlers this site
attributes its claims:

- **Every statistic gets an inline, named, linkable source.** No unsourced numbers.
- **Link to at least one vertical page** (`grab-bars.html`, `adus.html`) from each
  post. That is how crawl equity reaches the pages that convert.

Voice, palette, and the "Never Say" list live in the brand guide in
`pga/clients/nestlonger`, not this repo.

## Analytics

Google Analytics 4 (`G-D2CB1LRG5P`) is wired into every page including 404.

## Working on the site

Edit the HTML directly. Page sections are duplicated across files (no templating); update each page when changing nav, footer, or shared blocks.

CSS lives in a single `assets/styles.css` — design tokens, kit components, and page-specific extensions are all in one file, organized by section comment.
