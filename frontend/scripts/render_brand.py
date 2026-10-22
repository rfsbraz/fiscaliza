"""Render the brand images in public/ from the SVG sources in brand/.

    pip install resvg-py==0.5.0 pillow
    python frontend/scripts/render_brand.py

og-image.png is the 1200x630 social card; favicon.ico holds 16, 32 and 48 px. The PNG is saved
with a small palette to keep it light. Run it again after changing a file in brand/.
"""

import io
from pathlib import Path

import resvg_py
from PIL import Image

FRONTEND = Path(__file__).resolve().parent.parent
BRAND = FRONTEND / "brand"
PUBLIC = FRONTEND / "public"


def render(svg, width, height):
    png = resvg_py.svg_to_bytes(svg_path=str(svg), width=width, height=height, skip_system_fonts=True)
    return Image.open(io.BytesIO(bytes(png))).convert("RGBA")


def main():
    card = render(BRAND / "og-image.svg", 1200, 630).convert("RGB")
    card = card.quantize(colors=48, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    card.save(PUBLIC / "og-image.png", optimize=True)

    sizes = [16, 32, 48]
    icons = [render(BRAND / "favicon.svg", s, s) for s in sizes]
    icons[-1].save(PUBLIC / "favicon.ico", sizes=[(s, s) for s in sizes], append_images=icons[:-1])
    (PUBLIC / "favicon.svg").write_bytes((BRAND / "favicon.svg").read_bytes())


if __name__ == "__main__":
    main()
