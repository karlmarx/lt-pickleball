# lt-pickleball

Source for **https://lt.93.fyi**: the case for switching our open-play courts from the Franklin X-40 to the Life Time LT Pro 48.

It replaces the laminated two-page handout in `source/`. The site is the source of truth now: print the page (letter paper) to get the handout back.

## Layout

- `src/index.html` page template (all CSS and JS inline, no framework, no external fonts)
- `src/og.html` template for the 1200x630 share image
- `scripts/build.py` fills the template: Fibonacci-sphere ball SVGs, print QR code, favicon, og image
- `public/` built output, served as-is by Vercel (no build step on Vercel)

## Build

```sh
uv run scripts/build.py        # public/index.html + favicon
uv run scripts/build.py --og   # also og.png and apple-touch-icon.png (needs Chromium)
ruff format scripts && ruff check scripts
```

Set `CHROMIUM_PATH` if Chromium is not at `/opt/pw-browsers/chromium`.

## Rules for copy

- The brand is **Life Time**, the ball is the **LT Pro 48**. Never "Lifetime".
- No em dashes. The build fails if one sneaks into the page.
- No invented stats. Every claim traces to the original handout or a source listed on the page.
