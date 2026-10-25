"""Render GIMS Results Instagram/Facebook carousels (1080x1350) from JSON specs.

For every carousels/<slug>.json without carousels/<slug>/01.jpg, render all
slides to carousels/<slug>/NN.jpg.

Spec:
{
  "slides": [
    {"type": "cover", "title": ["WHO GOOGLE", "*PUTS ON*", "THE MAP"], "sub": "One line of promise."},
    {"type": "text",  "kicker": "1. RELEVANCE", "title": ["DO YOU MATCH", "*THE SEARCH?*"], "body": "Up to ~25 words."},
    {"type": "list",  "title": ["*RECAP*"], "items": ["Point one", "Point two"]},
    {"type": "cta",   "title": ["WANT A", "*FREE AUDIT?*"], "body": "Comment GOOGLE ...", "keyword": "GOOGLE"}
  ]
}
Wrap a title line in *...* to make it red.

Usage: python3 scripts/make_carousel.py template.png headline.woff body.woff body_bold.woff
"""
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

TPL, HEAD, BODY, BODYB = sys.argv[1:5]
W, H = 1080, 1350
BLACK, RED, WHITE, GREY = (12, 12, 12), (236, 18, 18), (253, 253, 253), (90, 90, 90)
HANDLE = "@gimsresults"
ROOT = pathlib.Path(__file__).resolve().parent.parent

tpl = Image.open(TPL).convert("RGB")
# Brand pieces cut from George's blog-cover template
HEADER = tpl.crop((672, 208, 1062, 298))          # logo + "GIMS Results" + tick
UNDERLINE = tpl.crop((700, 684, 1192, 724))        # red hand-drawn underline
PHOTO = tpl.crop((0, 60, 640, 860))                # George on the hex background (4:5)
BG_TEXTURE = tpl.crop((900, 0, 1661, 150))         # dark hex texture strip


def font(path, size):
    return ImageFont.truetype(path, size)


def background():
    """Dark hex texture fading into deep red, like the blog covers."""
    tex = BG_TEXTURE.resize((W, int(W * BG_TEXTURE.height / BG_TEXTURE.width)))
    bg = Image.new("RGB", (W, H))
    for y in range(0, H, tex.height):
        bg.paste(tex, (0, y))
    bg = bg.filter(ImageFilter.GaussianBlur(1))
    red = Image.new("RGB", (W, H), (120, 0, 0))
    mask = Image.linear_gradient("L").resize((W, H))  # black top -> white bottom
    return Image.composite(red, bg, mask.point(lambda v: int(v * 0.75)))


def rounded_card(im, box, radius=46):
    shadow = Image.new("L", im.size, 0)
    ImageDraw.Draw(shadow).rounded_rectangle((box[0] + 8, box[1] + 14, box[2] + 8, box[3] + 14), radius, fill=150)
    im.paste((0, 0, 0), (0, 0), shadow.filter(ImageFilter.GaussianBlur(18)))
    ImageDraw.Draw(im).rounded_rectangle(box, radius, fill=WHITE)


def fit_title(lines, max_w, max_h, start=150, floor=56):
    size = start
    while size > floor:
        f = font(HEAD, size)
        hb = f.getbbox("H")
        cap = hb[3] - hb[1]
        widest = max(f.getbbox(l.strip("*").upper())[2] for l in lines)
        total = cap * len(lines) + int(cap * 0.24) * (len(lines) - 1)
        if widest <= max_w and total <= max_h:
            return f, cap, total
        size -= 2
    f = font(HEAD, floor)
    hb = f.getbbox("H")
    cap = hb[3] - hb[1]
    return f, cap, cap * len(lines) + int(cap * 0.24) * (len(lines) - 1)


def draw_title(d, lines, x, y, f, cap):
    hb = f.getbbox("H")
    for l in lines:
        red = l.startswith("*") and l.endswith("*")
        t = l.strip("*").upper()
        c = RED if red else BLACK
        d.text((x, y - hb[1]), t, font=f, fill=c, stroke_width=1, stroke_fill=c)
        y += cap + int(cap * 0.24)
    return y


def wrap(d, text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textlength(test, font=f) <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_body(d, text, x, y, max_w, size=46, colour=BLACK, bold=False):
    f = font(BODYB if bold else BODY, size)
    for line in wrap(d, text, f, max_w):
        d.text((x, y), line, font=f, fill=colour)
        y += int(size * 1.32)
    return y


def footer(im, d, n, total):
    f = font(BODY, 34)
    d.text((W - 90 - d.textlength(HANDLE, font=f), H - 82), HANDLE, font=f, fill=WHITE)
    tag = f"{n}/{total}"
    d.text((90, H - 82), tag, font=f, fill=WHITE)


def cover(s, n, total):
    im = PHOTO.resize((W, H))
    # darken the bottom so the card sits well
    shade = Image.linear_gradient("L").resize((W, H)).point(lambda v: max(0, v - 90))
    im = Image.composite(Image.new("RGB", (W, H), (20, 0, 0)), im, shade)
    d = ImageDraw.Draw(im)
    box = (60, 640, W - 60, H - 120)
    rounded_card(im, box)
    d = ImageDraw.Draw(im)
    hdr = HEADER.resize((int(HEADER.width * 0.9), int(HEADER.height * 0.9)))
    im.paste(hdr, (box[0] + 40, box[1] + 30))
    inner_w = box[2] - box[0] - 100
    sub_h = 120 if s.get("sub") else 0
    f, cap, total_h = fit_title(s["title"], inner_w, box[3] - box[1] - 150 - sub_h - 50, start=170)
    y = box[1] + 140
    y = draw_title(d, s["title"], box[0] + 50, y, f, cap)
    ul = UNDERLINE.resize((min(inner_w, 560), 44))
    im.paste(ul, (box[0] + 46, y - 6))
    if s.get("sub"):
        draw_body(d, s["sub"], box[0] + 52, y + 50, inner_w, size=42, colour=GREY)
    footer(im, d, n, total)
    return im


def content(s, n, total):
    im = background()
    box = (60, 110, W - 60, H - 130)
    rounded_card(im, box)
    d = ImageDraw.Draw(im)
    hdr = HEADER.resize((int(HEADER.width * 0.75), int(HEADER.height * 0.75)))
    im.paste(hdr, (box[0] + 40, box[1] + 30))
    inner_w = box[2] - box[0] - 120
    top, bottom = box[1] + 130, box[3] - 50
    # draw the block on a scratch layer, then centre it vertically in the card
    layer = Image.new("RGB", (box[2] - box[0], bottom - top), WHITE)
    ld = ImageDraw.Draw(layer)
    x, y = 60, 0
    if s.get("kicker"):
        ld.text((x, y), s["kicker"].upper(), font=font(BODYB, 46), fill=RED)
        y += 84
    t = s["type"]
    items = s.get("items", [])
    room = 110 * len(items) + 40 if t == "list" else (460 if s.get("body") else 0)
    if t == "cta":
        room += 230
    f, cap, th = fit_title(s["title"], inner_w, max(220, layer.height - y - room), start=170)
    y = draw_title(ld, s["title"], x, y, f, cap)
    ul = UNDERLINE.resize((min(inner_w, 460), 40))
    layer.paste(ul, (x - 4, y - 8))
    y += 66
    if t == "list":
        bf = font(BODYB, 58)
        for item in items:
            ld.ellipse((x, y + 20, x + 26, y + 46), fill=RED)
            for line in wrap(ld, item, bf, inner_w - 56):
                ld.text((x + 52, y), line, font=bf, fill=BLACK)
                y += 74
            y += 30
    elif s.get("body"):
        y = draw_body(ld, s["body"], x, y, inner_w, size=58)
    if t == "cta" and s.get("keyword"):
        kw = s["keyword"].upper()
        kf = font(HEAD, 130)
        tw = ld.textlength(kw, font=kf)
        bx = (x, y + 40, x + tw + 90, y + 40 + 180)
        ld.rounded_rectangle(bx, 30, fill=RED)
        hb = kf.getbbox("H")
        ld.text((x + 45, bx[1] + (180 - (hb[3] - hb[1])) // 2 - hb[1]), kw, font=kf, fill=WHITE)
        y = bx[3]
    used = min(y, layer.height)
    offset = top + max(0, (layer.height - used) // 2 - 30)
    im.paste(layer.crop((0, 0, layer.width, used)), (box[0], offset))
    footer(im, d, n, total)
    return im


def render(spec, outdir):
    slides = spec["slides"]
    outdir.mkdir(parents=True, exist_ok=True)
    for i, s in enumerate(slides, 1):
        im = cover(s, i, len(slides)) if s["type"] == "cover" else content(s, i, len(slides))
        im.save(outdir / f"{i:02d}.jpg", "JPEG", quality=90, optimize=True, progressive=True)
    print(f"rendered {len(slides)} slides -> {outdir}")


if __name__ == "__main__":
    for spec_path in sorted((ROOT / "carousels").glob("*.json")):
        if spec_path.name == "log.json":
            continue
        outdir = ROOT / "carousels" / spec_path.stem
        if (outdir / "01.jpg").exists():
            continue
        spec = json.loads(spec_path.read_text())
        n = len(spec["slides"])
        if not 5 <= n <= 12:
            sys.exit(f"{spec_path.name}: needs 5-12 slides, has {n}")
        render(spec, outdir)
