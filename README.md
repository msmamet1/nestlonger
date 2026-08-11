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

Spam is handled by a `_gotcha` honeypot field, hidden via `.nl-hp`. No CAPTCHA, which
would mean reintroducing a third-party script.

### Setup — the forms are not live until you do this

The `action` on all three forms is the placeholder `FORMSPREE_FORM_ID`. To activate:

1. Create a form at [formspree.io](https://formspree.io) (free tier is sufficient).
2. Find-and-replace `FORMSPREE_FORM_ID` across all `*.html` with your form ID.
3. Submit each form once to confirm delivery and that the redirect to `thanks.html` works.

Any endpoint that accepts a plain form POST works — Formspree is just the default.
Swapping providers means changing the `action` URL and, if it uses different names,
the `_next` / `_subject` / `_gotcha` hidden fields.

## Analytics

Google Analytics 4 (`G-D2CB1LRG5P`) is wired into every page including 404.

## Working on the site

Edit the HTML directly. Page sections are duplicated across files (no templating); update each page when changing nav, footer, or shared blocks.

CSS lives in a single `assets/styles.css` — design tokens, kit components, and page-specific extensions are all in one file, organized by section comment.
