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
├── 404.html
├── sitemap.xml
├── robots.txt
├── CNAME              ← www.nestlonger.com
├── .nojekyll          ← disables Jekyll processing
├── assets/
│   ├── styles.css     ← single consolidated stylesheet
│   ├── favicon.png
│   ├── wordmark.svg   ← used in grab-bars.html JSON-LD logo field
│   ├── wordmark-light.svg
│   └── images/        ← page imagery (WebP)
└── internal/          ← not part of the site; robots-disallowed
    ├── brand-guide.md
    ├── brand-guide.html
    └── disavow.txt    ← Google Search Console upload artifact
```

Pages serves every file in the repository, so `internal/` is reachable by URL even
though it is excluded from search results. Do not put anything genuinely private there.

## Deployment

`git push` to `main`. GitHub Pages handles the rest. There is no build, no bundler, no npm.

## Lead capture

All CTAs trigger a single Tally popup. Each CTA passes a `source` hidden field so leads can be routed by vertical (`grab-bars`, `adus`, `partners`, `homepage`, `about`, `newsletter`, `404`).

The live Tally form ID is `7R49EL`, hardcoded into the inline script on every page.
To swap forms, find-and-replace that ID across all `*.html` files; the replacement
form must include a hidden field named `source`.

## Analytics

Google Analytics 4 (`G-D2CB1LRG5P`) is wired into every page including 404.

## Working on the site

Edit the HTML directly. Page sections are duplicated across files (no templating); update each page when changing nav, footer, or shared blocks.

CSS lives in a single `assets/styles.css` — design tokens, kit components, and page-specific extensions are all in one file, organized by section comment.
