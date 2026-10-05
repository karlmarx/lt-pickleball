# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "segno>=1.6",
#     "playwright>=1.48",
# ]
# ///
"""Build the static site for balls.93.fyi.

Generates the inline SVG ball diagrams (Fibonacci sphere hole layouts), the
print-only QR code, the favicon, and optionally the 1200x630 Open Graph image.
The page template lives in ``src/index.html``; output goes to ``public/``.

Usage:
    uv run scripts/build.py          # HTML + favicon
    uv run scripts/build.py --og     # also render public/og.png
    uv run scripts/build.py --pdf    # also render the printable handout PDF
"""

from __future__ import annotations

import argparse
import io
import math
import os
from dataclasses import dataclass
from pathlib import Path

import segno

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
PUBLIC = ROOT / "public"
SITE_URL = "https://balls.93.fyi"
PDF_NAME = "LT-Pro-48-handout.pdf"

GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))

# Holes whose surface normal faces the viewer less than this are dropped. Holes
# right on the silhouette would draw as slivers and clutter the outline.
MIN_FACING = 0.12


@dataclass(frozen=True)
class Hole:
    """One hole projected onto the 2D drawing.

    Attributes:
        x: Projected x position, unit sphere coordinates (right is positive).
        y: Projected y position, unit sphere coordinates (up is positive).
        depth: How directly the hole faces the viewer, from 0 (edge) to 1.
    """

    x: float
    y: float
    depth: float


def fibonacci_sphere(n: int) -> list[tuple[float, float, float]]:
    """Spread ``n`` points evenly over a unit sphere.

    Args:
        n: Number of points.

    Returns:
        A list of ``(x, y, z)`` unit vectors.
    """
    points = []
    for i in range(n):
        y = 1.0 - 2.0 * (i + 0.5) / n
        r = math.sqrt(max(0.0, 1.0 - y * y))
        theta = GOLDEN_ANGLE * i
        points.append((math.cos(theta) * r, y, math.sin(theta) * r))
    return points


def rotate(
    p: tuple[float, float, float], ax: float, ay: float
) -> tuple[float, float, float]:
    """Rotate a point about the x axis, then the y axis.

    Args:
        p: The point to rotate.
        ax: Rotation about x, in radians.
        ay: Rotation about y, in radians.

    Returns:
        The rotated point.
    """
    x, y, z = p
    y, z = y * math.cos(ax) - z * math.sin(ax), y * math.sin(ax) + z * math.cos(ax)
    x, z = x * math.cos(ay) + z * math.sin(ay), -x * math.sin(ay) + z * math.cos(ay)
    return x, y, z


def visible_holes(n: int, ax: float = 0.35, ay: float = 0.25) -> list[Hole]:
    """Return the front facing holes of an ``n`` hole ball.

    Args:
        n: Total number of holes on the ball.
        ax: Tilt about the x axis, so the poles are not dead center.
        ay: Turn about the y axis.

    Returns:
        Holes facing the viewer, sorted back to front for painting.
    """
    holes = []
    for p in fibonacci_sphere(n):
        x, y, z = rotate(p, ax, ay)
        if z > MIN_FACING:
            holes.append(Hole(x=x, y=y, depth=z))
    return sorted(holes, key=lambda h: h.depth)


def fmt(v: float) -> str:
    """Format a number compactly for SVG attributes.

    Args:
        v: The value.

    Returns:
        The value rounded to one decimal, without a trailing ``.0``.
    """
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def ellipse(cx: float, cy: float, rx: float, ry: float, angle: float, cls: str) -> str:
    """Build one rotated SVG ellipse.

    Args:
        cx: Center x.
        cy: Center y.
        rx: Radius along the rotated x axis.
        ry: Radius along the rotated y axis.
        angle: Rotation in degrees.
        cls: CSS class.

    Returns:
        The SVG element as a string.
    """
    return (
        f'<ellipse class="{cls}" cx="{fmt(cx)}" cy="{fmt(cy)}" rx="{fmt(rx)}" '
        f'ry="{fmt(ry)}" transform="rotate({fmt(angle)} {fmt(cx)} {fmt(cy)})"/>'
    )


def ball_svg(kind: str, n: int, hole_r: float, title: str) -> tuple[str, int]:
    """Draw one ball as an inline SVG.

    Each hole is foreshortened into an ellipse: its width along the radial
    direction shrinks with depth, as a circle on a sphere would.

    Args:
        kind: ``"lt"`` (chamfered holes) or ``"fr"`` (plain drilled holes).
        n: Total holes on the ball.
        hole_r: Hole radius in drawing units (ball radius is 90).
        title: Accessible title for the drawing.

    Returns:
        The SVG markup and the number of holes drawn.
    """
    c, radius = 100.0, 90.0
    holes = visible_holes(n)
    parts = [
        f'<svg class="ball ball-{kind}" viewBox="0 0 200 200" role="img" '
        f'aria-labelledby="t-{kind}"><title id="t-{kind}">{title}</title>',
        f'<defs><radialGradient id="g-{kind}" cx=".36" cy=".3" r=".78">'
        f'<stop offset="0" class="s0"/><stop offset=".55" class="s1"/>'
        f'<stop offset="1" class="s2"/></radialGradient></defs>',
        f'<circle class="shell" cx="100" cy="100" r="{fmt(radius)}" '
        f'fill="url(#g-{kind})"/>',
    ]
    for h in holes:
        cx, cy = c + radius * h.x, c - radius * h.y
        angle = math.degrees(math.atan2(-h.y, h.x))
        # A hole at the very center has no radial direction; any angle works.
        rx, ry = hole_r * h.depth, hole_r
        if kind == "lt":
            parts.append(ellipse(cx, cy, rx * 1.55, ry * 1.55, angle, "bevel"))
        parts.append(ellipse(cx, cy, rx, ry, angle, "hole"))
    parts.append(
        f'<circle class="rim" cx="100" cy="100" r="{fmt(radius)}" fill="none"/>'
    )
    # Ring the most front facing hole; it is shown when the zoom view is open.
    front = holes[-1]
    parts.append(
        f'<circle class="focus-ring" cx="{fmt(c + radius * front.x)}" '
        f'cy="{fmt(c - radius * front.y)}" r="{fmt(hole_r * 2.3)}"/>'
    )
    parts.append("</svg>")
    return "".join(parts), len(holes)


def qr_svg(url: str) -> str:
    """Render a QR code for ``url`` as a compact inline SVG.

    Args:
        url: The URL to encode.

    Returns:
        SVG markup with no XML declaration.
    """
    buf = io.BytesIO()
    segno.make(url, error="m").save(
        buf,
        kind="svg",
        xmldecl=False,
        svgns=True,
        scale=4,
        border=2,
        dark="#000",
        light="#fff",
        svgclass="qr",
        lineclass=None,
        omitsize=False,
        title="QR code for balls.93.fyi",
    )
    return buf.getvalue().decode()


FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<defs><radialGradient id="g" cx=".35" cy=".3" r=".75">
<stop offset="0" stop-color="#9be36b"/><stop offset=".6" stop-color="#4cae2c"/>
<stop offset="1" stop-color="#2f7a1d"/></radialGradient></defs>
<circle cx="32" cy="32" r="30" fill="url(#g)"/>
<g fill="#16380f"><circle cx="32" cy="14" r="4"/><circle cx="16" cy="26" r="4"/>
<circle cx="48" cy="26" r="4"/><circle cx="32" cy="32" r="4.5"/>
<circle cx="20" cy="44" r="4"/><circle cx="44" cy="44" r="4"/>
<circle cx="32" cy="52" r="3.5"/></g></svg>
"""


def build_html() -> dict[str, int]:
    """Fill the page template and write ``public/index.html``.

    Returns:
        Visible hole counts per ball, for the caption sanity check.
    """
    lt, lt_count = ball_svg(
        "lt", 48, 7.0, "Life Time LT Pro 48: bright green, 48 holes with beveled edges"
    )
    fr, fr_count = ball_svg(
        "fr", 40, 8.0, "Franklin X-40: optic yellow, 40 plain drilled holes"
    )
    html = (SRC / "index.html").read_text()
    replacements = {
        "{{BALL_LT}}": lt,
        "{{BALL_FR}}": fr,
        "{{LT_VISIBLE}}": str(lt_count),
        "{{FR_VISIBLE}}": str(fr_count),
        "{{QR}}": qr_svg(SITE_URL),
    }
    for key, value in replacements.items():
        html = html.replace(key, value)
    if "{{" in html:
        raise ValueError("Unfilled placeholder left in template")
    if chr(0x2014) in html:
        raise ValueError("Em dash found in output; the style guide bans them")
    PUBLIC.mkdir(exist_ok=True)
    (PUBLIC / "index.html").write_text(html)
    (PUBLIC / "favicon.svg").write_text(FAVICON)
    return {"lt": lt_count, "fr": fr_count}


def chromium_path() -> str:
    """Return the Chromium executable, honoring ``CHROMIUM_PATH``."""
    exe = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium")
    if Path(exe).is_dir():
        exe = str(next(Path(exe).glob("chrome-linux/chrome")))
    return exe


def build_pdf() -> None:
    """Print ``public/index.html`` with its print stylesheet to a letter PDF."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chromium_path())
        page = browser.new_page()
        page.goto((PUBLIC / "index.html").as_uri())
        page.pdf(
            path=str(PUBLIC / PDF_NAME),
            prefer_css_page_size=True,
            print_background=True,
        )
        browser.close()


def build_og() -> None:
    """Render the 1200x630 share image from ``src/og.html`` with Chromium."""
    from playwright.sync_api import sync_playwright

    lt, _ = ball_svg("lt", 48, 7.0, "LT Pro 48")
    fr, _ = ball_svg("fr", 40, 8.0, "Franklin X-40")
    styles = (SRC / "index.html").read_text().split("/*BALL-STYLE*/")[1]
    html = (
        (SRC / "og.html")
        .read_text()
        .replace("{{BALL_LT}}", lt)
        .replace("{{BALL_FR}}", fr)
        .replace("{{BALL_STYLE}}", styles)
    )
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chromium_path())
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        page.set_content(html)
        page.screenshot(path=str(PUBLIC / "og.png"))
        icon = browser.new_page(viewport={"width": 180, "height": 180})
        icon.set_content(
            '<body style="margin:0;background:#fff">'
            f'<div style="padding:10px">{FAVICON}</div></body>'
        )
        icon.screenshot(path=str(PUBLIC / "apple-touch-icon.png"))
        browser.close()


def main() -> None:
    """Parse arguments and run the build."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--og", action="store_true", help="render og.png too")
    parser.add_argument("--pdf", action="store_true", help="render the handout PDF")
    args = parser.parse_args()
    counts = build_html()
    print(f"visible holes: LT {counts['lt']}, Franklin {counts['fr']}")
    if args.og:
        build_og()
        print("wrote public/og.png")
    if args.pdf:
        build_pdf()
        print(f"wrote public/{PDF_NAME}")


if __name__ == "__main__":
    main()
