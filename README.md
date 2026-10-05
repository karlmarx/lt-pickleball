# lt-pickleball

Source for **https://balls.93.fyi**: the case for switching our open-play courts from the Franklin X-40 to the Life Time LT Pro 48.

It replaces the laminated two-page handout in `source/`. The site is the source of truth now: print the page (letter paper) to get the handout back.

## Layout

- `src/index.html` page template (all CSS and JS inline, no framework, no external fonts)
- `src/og.html` template for the 1200x630 share image
- `scripts/build.py` fills the template: Fibonacci-sphere ball SVGs, print QR code, favicon, og image
- `public/` built output, served as-is by a Cloudflare Worker with static assets (no build step)
- `public/_headers` security + cache headers; `wrangler.jsonc` Worker config (custom domain balls.93.fyi)

## Build

```sh
uv run scripts/build.py        # public/index.html + favicon
uv run scripts/build.py --og   # also og.png and apple-touch-icon.png (needs Chromium)
uv run scripts/build.py --pdf  # also public/LT-Pro-48-handout.pdf, the print layout as a PDF (needs Chromium)
ruff format scripts && ruff check scripts
```

Set `CHROMIUM_PATH` if Chromium is not at `/opt/pw-browsers/chromium`.

## Deploy

```sh
npx wrangler deploy   # needs CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID
```

Pushes to `main` deploy automatically via `.github/workflows/deploy.yml` (repo secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`). The workflow does not build: run the build above and commit `public/` before merging.

balls.93.fyi has its own Cloudflare Access app with a public bypass policy, so the `*.93.fyi` login wall does not apply.

## Rules for copy

- The brand is **Life Time**, the ball is the **LT Pro 48**. Never "Lifetime".
- No em dashes. The build fails if one sneaks into the page.
- No invented stats. Every claim traces to the original handout or a source listed on the page.
