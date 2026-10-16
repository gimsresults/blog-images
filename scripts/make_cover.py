"""Build GIMS Results blog covers from the template by swapping the headline.

For every covers/<slug>.json without a matching images/<slug>.jpg, render the
cover. JSON format: {"lines": ["LINE ONE", "*RED LINE*", "LINE THREE"]}
Wrap a line in *...* to colour it red. 2-4 short lines.

Usage: python3 scripts/make_cover.py template.png font.woff
"""
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

TPL, FONT = sys.argv[1:3]
BOX_X, BOX_TOP, BOX_BOTTOM, BOX_W = 707, 362, 672, 820
BLACK, RED, CARD = (12, 12, 12), (236, 18, 18), (253, 253, 253)
GAP = 0.22


def render(lines, out):
    im = Image.open(TPL).convert("RGB")
    d = ImageDraw.Draw(im)
    # Clear the old headline; keep the logo row above and red underline below.
    d.rectangle((703, 345, 1545, 683), fill=CARD)
    n = len(lines)
    size = 140
    while size > 30:
        f = ImageFont.truetype(FONT, size)
        hb = f.getbbox("H")
        cap = hb[3] - hb[1]
        widest = max(f.getbbox(l.strip("*").upper())[2] - f.getbbox(l.strip("*").upper())[0] for l in lines)
        total = cap * n + int(cap * GAP * (n - 1))
        if widest <= BOX_W and total <= BOX_BOTTOM - BOX_TOP and cap <= 92:
            break
        size -= 2
    y = BOX_TOP + (BOX_BOTTOM - BOX_TOP - total) // 2
    for l in lines:
        red = l.startswith("*") and l.endswith("*")
        t = l.strip("*").upper()
        colour = RED if red else BLACK
        d.text((BOX_X - f.getbbox(t)[0], y - hb[1]), t, font=f, fill=colour,
               stroke_width=1, stroke_fill=colour)
        y += cap + int(cap * GAP)
    im.save(out, "JPEG", quality=88, optimize=True, progressive=True)
    print(f"rendered {out} at font size {size}")


root = pathlib.Path(__file__).resolve().parent.parent
(root / "images").mkdir(exist_ok=True)
for spec in sorted((root / "covers").glob("*.json")):
    out = root / "images" / f"{spec.stem}.jpg"
    if out.exists():
        continue
    lines = [l.strip() for l in json.loads(spec.read_text())["lines"] if l.strip()]
    if not 1 <= len(lines) <= 4:
        sys.exit(f"{spec.name}: needs 1-4 lines")
    render(lines, out)
