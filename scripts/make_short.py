"""Assemble a GIMS Results vertical short (1080x1920 MP4) from AI clips + voiceover.

Spec (JSON):
{
  "scenes": [
    {"clip": "<url or path to a 9:16 video>", "vo": "<url or path to mp3>", "caption": "Spoken line, shown as captions."},
    ...
  ],
  "cta": {"vo": "<url or path>", "title": ["WANT A", "*FREE AUDIT?*"],
          "body": "Send us a DM and I'll check your Google profile for free.", "keyword": "DM US"}
}

Each scene lasts as long as its voiceover + 0.6s (the clip is slowed down a
little if it is shorter, trimmed if longer; its own audio is muted). Captions
are timed across the voiceover by text length. The CTA end card uses the same
brand look as the carousels.

Usage: python3 scripts/make_short.py spec.json out.mp4 template.png headline.woff body.woff body_bold.woff
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.request

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SPEC, OUT, TPL, HEAD, BODY, BODYB = sys.argv[1:7]
W, H, FPS = 1080, 1920, 30
BLACK, RED, WHITE = (12, 12, 12), (236, 18, 18), (253, 253, 253)
LEAD, TAIL = 0.25, 0.35
tpl = Image.open(TPL).convert("RGB")
HEADER = tpl.crop((672, 208, 1062, 298))
UNDERLINE = tpl.crop((700, 684, 1192, 724))
BG_TEXTURE = tpl.crop((900, 0, 1661, 150))


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         check=True, capture_output=True, text=True).stdout
    return float(out.strip())


def fetch(src, dest):
    if re.match(r"https?://", src):
        req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
            f.write(r.read())
        return dest
    return src


def chunks(text, max_words=4):
    words = text.split()
    out, cur = [], []
    for k, w in enumerate(words):
        cur.append(w)
        nxt = words[k + 1] if k + 1 < len(words) else ""
        # keep a short word that ends the sentence ("me.") with its line
        if len(cur) >= max_words and re.search(r"[.?!]$", nxt) and len(nxt) <= 5:
            continue
        if re.search(r"[.?!]$", w) and len(cur) == 1 and out and not re.search(r"[.?!]$", out[-1]):
            out[-1] += " " + w  # "a" / "suspension." -> keep the sentence end with its line
            cur = []
            continue
        if len(cur) >= max_words or re.search(r"[.?!,:]$", w) and len(cur) >= 2:
            out.append(" ".join(cur))
            cur = []
    if cur:
        if out and len(cur) == 1:
            out[-1] += " " + cur[0]
        else:
            out.append(" ".join(cur))
    return out


def caption_png(text, path):
    im = Image.new("RGBA", (W, 420), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    size = 96
    while size > 52:
        f = ImageFont.truetype(HEAD, size)
        lines = wrap(d, text.upper(), f, W - 140)
        if len(lines) <= 2:
            break
        size -= 4
    lh = int(size * 1.08)
    y = (420 - lh * len(lines)) // 2
    for line in lines:
        w = d.textlength(line, font=f)
        d.text(((W - w) / 2, y), line, font=f, fill=WHITE, stroke_width=9, stroke_fill=BLACK)
        y += lh
    im.save(path)


def wrap(d, text, f, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def badge_png(path):
    """Small white pill with the GIMS Results logo, top of frame."""
    hw, hh = HEADER.size
    scale = 300 / hw
    logo = HEADER.resize((300, int(hh * scale)))
    im = Image.new("RGBA", (W, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bx = ((W - 340) // 2, 70, (W + 340) // 2, 70 + logo.height + 24)
    d.rounded_rectangle(bx, 22, fill=WHITE + (235,))
    im.paste(logo, (bx[0] + 20, bx[1] + 12))
    im.save(path)


def background():
    tex = BG_TEXTURE.resize((W, int(W * BG_TEXTURE.height / BG_TEXTURE.width)))
    bg = Image.new("RGB", (W, H))
    for y in range(0, H, tex.height):
        bg.paste(tex, (0, y))
    bg = bg.filter(ImageFilter.GaussianBlur(1))
    red = Image.new("RGB", (W, H), (120, 0, 0))
    mask = Image.linear_gradient("L").resize((W, H))
    return Image.composite(red, bg, mask.point(lambda v: int(v * 0.75)))


def cta_png(spec, path):
    im = background()
    d = ImageDraw.Draw(im)
    box = (70, 420, W - 70, 1500)
    d.rounded_rectangle(box, 50, fill=WHITE)
    hw, hh = HEADER.size
    logo = HEADER.resize((360, int(hh * 360 / hw)))
    im.paste(logo, ((W - logo.width) // 2, box[1] + 70))
    y = box[1] + 70 + logo.height + 70
    f = ImageFont.truetype(HEAD, 150)
    for line in spec.get("title", ["WANT A", "*FREE AUDIT?*"]):
        red = line.startswith("*")
        t = line.strip("*").upper()
        w = d.textlength(t, font=f)
        d.text(((W - w) / 2, y), t, font=f, fill=RED if red else BLACK)
        y += 160
    ul = UNDERLINE.resize((520, int(UNDERLINE.height * 520 / UNDERLINE.width)))
    im.paste(ul, ((W - ul.width) // 2, y))
    y += ul.height + 50
    fb = ImageFont.truetype(BODY, 52)
    for line in wrap(d, spec["body"], fb, box[2] - box[0] - 140):
        w = d.textlength(line, font=fb)
        d.text(((W - w) / 2, y), line, font=fb, fill=BLACK)
        y += 66
    kw = spec.get("keyword", "DM US")
    fk = ImageFont.truetype(HEAD, 96)
    kwid = d.textlength(kw, font=fk)
    bx = ((W - kwid) / 2 - 60, y + 50, (W + kwid) / 2 + 60, y + 50 + 140)
    d.rounded_rectangle(bx, 34, fill=RED)
    d.text(((W - kwid) / 2, bx[1] + 18), kw, font=fk, fill=WHITE)
    fh = ImageFont.truetype(BODYB, 46)
    t = "@gimsresults"
    d.text(((W - d.textlength(t, font=fh)) / 2, 1620), t, font=fh, fill=WHITE)
    im.save(path)


def main():
    spec = json.loads(pathlib.Path(SPEC).read_text())
    tmp = pathlib.Path(tempfile.mkdtemp())
    badge = tmp / "badge.png"
    badge_png(badge)
    parts = []
    for i, sc in enumerate(spec["scenes"], 1):
        clip = fetch(sc["clip"], str(tmp / f"clip{i}.mp4"))
        vo = fetch(sc["vo"], str(tmp / f"vo{i}.mp3"))
        vd, cd = dur(vo), dur(clip)
        D = round(LEAD + vd + TAIL, 3)
        slow = max(1.0, D / cd)
        caps = chunks(sc["caption"])
        total = sum(len(c) for c in caps)
        t = LEAD
        inputs = ["-i", clip, "-i", vo, "-i", str(badge)]
        filt = [f"[0:v]setpts={slow:.4f}*PTS,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},trim=0:{D},setpts=PTS-STARTPTS[v0]",
                "[v0][2:v]overlay=0:0[v1]"]
        last = "v1"
        for j, c in enumerate(caps):
            png = tmp / f"cap{i}_{j}.png"
            caption_png(c, png)
            seg = vd * len(c) / total
            start, end = t, (t + seg if j < len(caps) - 1 else D)
            inputs += ["-i", str(png)]
            filt.append(f"[{last}][{3 + j}:v]overlay=0:1180:enable='between(t,{start:.3f},{end:.3f})'[c{j}]")
            last = f"c{j}"
            t += seg
        filt.append(f"[1:a]adelay={int(LEAD * 1000)}|{int(LEAD * 1000)},apad,atrim=0:{D},aresample=44100,aformat=channel_layouts=stereo[a]")
        out = tmp / f"part{i}.mp4"
        run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filt), "-map", f"[{last}]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-c:a", "aac", "-b:a", "160k", "-t", str(D), str(out)])
        parts.append(out)
    cta = spec["cta"]
    vo = fetch(cta["vo"], str(tmp / "vo_cta.mp3"))
    D = round(LEAD + dur(vo) + 1.2, 3)
    card = tmp / "cta.png"
    cta_png(cta, card)
    out = tmp / "part_cta.mp4"
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(card), "-i", vo, "-filter_complex",
         f"[0:v]scale={W}:{H},format=yuv420p,zoompan=z='min(zoom+0.0006,1.04)':d=1:s={W}x{H}:fps={FPS}[v];"
         f"[1:a]adelay={int(LEAD * 1000)}|{int(LEAD * 1000)},apad,atrim=0:{D},aresample=44100,aformat=channel_layouts=stereo[a]",
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-c:a", "aac", "-b:a", "160k", "-t", str(D), str(out)])
    parts.append(out)
    ins, fl = [], []
    for k, p in enumerate(parts):
        ins += ["-i", str(p)]
        fl.append(f"[{k}:v][{k}:a]")
    run(["ffmpeg", "-y", *ins, "-filter_complex", "".join(fl) + f"concat=n={len(parts)}:v=1:a=1[v][a]",
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", OUT])
    print(OUT, round(dur(OUT), 2), "s")


if __name__ == "__main__":
    main()
