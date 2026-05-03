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
└── assets/
    ├── styles.css     ← single consolidated stylesheet
    ├── favicon.png
    ├── wordmark.svg
    ├── wordmark-light.svg
    └── images/        ← page imagery (WebP)
```

## Deployment

`git push` to `main`. GitHub Pages handles the rest. There is no build, no bundler, no npm.

## Lead capture

All CTAs trigger a single Tally popup. Each CTA passes a `source` hidden field so leads can be routed by vertical (`grab-bars`, `adus`, `partners`, `homepage`, `about`, `newsletter`, `404`).

The Tally form ID is currently a placeholder. To activate:

1. Create the Tally form (must include a hidden field named `source`).
2. Find-and-replace `TALLY_FORM_ID` across all `*.html` files with the real form ID.

## Analytics

Google Analytics 4 (`G-D2CB1LRG5P`) is wired into every page including 404.

## Working on the site

Edit the HTML directly. Page sections are duplicated across files (no templating); update each page when changing nav, footer, or shared blocks.

CSS lives in a single `assets/styles.css` — design tokens, kit components, and page-specific extensions are all in one file, organized by section comment.
