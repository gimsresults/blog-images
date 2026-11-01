"""Dynamic edit for a talking-head reel: punch-in zooms, word-timed captions with
red keywords, animated info cards, logo badge, branded end card and a ducked
music bed.

Usage:
  python3 scripts/edit_reel.py spec.json out.mp4 template.png headline.woff body.woff body_bold.woff

spec.json:
{
  "clips": [{"src": "th1.mp4", "dur": 14.4}, ...],      # played back to back, lip-synced
  "voice": "voice.wav",                                  # full voiceover, same timeline
  "music": "music.wav",                                  # optional bed (ducked under voice)
  "words": [[start, end, "word"], ...],                  # global timings for captions
  "red": ["SEO", "FREE", ...],                           # words drawn in red
  "cards": [ {"t0": 0.0, "t1": 2.4, "type": "title", "small": "DOES YOUR BUSINESS NEED", "big": "SEO?"},
             {"t0": 9.9, "t1": 14.4, "type": "search", "queries": [[10.1, "electrician perth"], ...]},
             {"t0": 25.6, "t1": 32.1, "type": "growth", "labels": ["QUIET", "BUILDS", "KEEPS BUILDING"]},
             {"t0": .., "t1": .., "type": "badge", "kicker": "QUESTION 1", "text": "DO PEOPLE SEARCH FOR YOU?"},
             {"t0": .., "t1": .., "type": "call"}, {"type": "no"}, {"type": "stack"}, {"type": "checks"}, {"type": "dm"} ],
  "cta": {"title": ["WANT A", "*FREE AUDIT?*"], "body": "...", "keyword": "DM US", "dur": 2.6}
}
"""
import json
import math
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SPEC, OUT, TPL, HEAD, BODY, BODYB = sys.argv[1:7]
W, H, FPS = 1080, 1920, 30
BLACK, RED, WHITE, GREEN, GREY = (12, 12, 12), (236, 18, 18), (253, 253, 253), (34, 170, 84), (120, 120, 120)
spec = json.load(open(SPEC))
tpl = Image.open(TPL).convert("RGB")
HEADER = tpl.crop((672, 208, 1062, 298))
UNDERLINE = tpl.crop((700, 684, 1192, 724))
BG_TEXTURE = tpl.crop((900, 0, 1661, 150))
_fonts = {}


def F(path, size):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


def ease_out_back(x):
    x = max(0.0, min(1.0, x))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


# ---------- captions ----------
words = spec["words"]
RED_WORDS = {w.upper() for w in spec.get("red", [])}
caps, cur = [], []
for k, (ws, we, w) in enumerate(words):
    nxt = words[k + 1][2] if k + 1 < len(words) else ""
    cur.append((ws, we, w))
    end_punct = re.search(r"[.?!,]$", w)
    if len(cur) >= 4 or (end_punct and (len(cur) >= 2 or not caps)):
        caps.append(cur)
        cur = []
    elif end_punct and len(cur) == 1 and caps and not re.search(r"[.?!]$", caps[-1][-1][2]):
        caps[-1] += cur
        cur = []
if cur:
    caps.append(cur)
cap_times = [(c[0][0], (caps[i + 1][0][0] if i + 1 < len(caps) else c[-1][1] + 0.3)) for i, c in enumerate(caps)]


def draw_caption(im, idx, t):
    c = caps[idx]
    t0, _ = cap_times[idx]
    s = 0.82 + 0.18 * ease_out_back((t - t0) / 0.14)
    size = int(92 * s)
    f = F(HEAD, size)
    d = ImageDraw.Draw(im)
    toks = [(w.upper(), re.sub(r"[^A-Z0-9']", "", w.upper()) in RED_WORDS) for _, _, w in c]
    space = d.textlength(" ", font=f)
    lines, line, lw = [], [], 0
    for tok in toks:
        tw = d.textlength(tok[0], font=f)
        if line and lw + space + tw > W - 140:
            lines.append((line, lw))
            line, lw = [], 0
        lw = lw + (space if line else 0) + tw
        line.append((tok, tw))
    lines.append((line, lw))
    lh = int(size * 1.06)
    y = 1250 - lh * len(lines) // 2
    for ln, lwid in lines:
        x = (W - lwid) / 2
        for (txt, red), tw in ln:
            d.text((x, y), txt, font=f, fill=RED if red else WHITE, stroke_width=max(6, int(9 * s)), stroke_fill=BLACK)
            x += tw + space
        y += lh


# ---------- cards ----------
def card_base(w, h, r=40):
    out = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    sh = Image.new("L", out.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((34, 40, w + 26, h + 32), r, fill=110)
    out.paste((0, 0, 0, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(14)))
    ImageDraw.Draw(out).rounded_rectangle((30, 30, w + 30, h + 30), r, fill=WHITE + (255,))
    return out


def tick(d, cx, cy, r, col):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    d.line([(cx - r * 0.45, cy), (cx - r * 0.1, cy + r * 0.38), (cx + r * 0.5, cy - r * 0.35)], fill=WHITE, width=max(4, int(r * 0.22)), joint="curve")


def cross(d, cx, cy, r, col):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    k = r * 0.38
    d.line((cx - k, cy - k, cx + k, cy + k), fill=WHITE, width=max(4, int(r * 0.2)))
    d.line((cx - k, cy + k, cx + k, cy - k), fill=WHITE, width=max(4, int(r * 0.2)))


def centered(d, text, f, y, cx, fill):
    d.text((cx - d.textlength(text, font=f) / 2, y), text, font=f, fill=fill)


def card_title(c, t):
    im = card_base(820, 300)
    d = ImageDraw.Draw(im)
    centered(d, c["small"], F(HEAD, 64), 70, im.width / 2, BLACK)
    centered(d, c["big"], F(HEAD, 170), 140, im.width / 2, RED)
    return im


def card_badge(c, t):
    f = F(HEAD, 74)
    lines = wrap_text(c["text"], f, 780)
    h = 120 + 84 * len(lines)
    im = card_base(860, h)
    d = ImageDraw.Draw(im)
    kf = F(HEAD, 50)
    kw = d.textlength(c["kicker"], font=kf) + 50
    d.rounded_rectangle((im.width / 2 - kw / 2, 52, im.width / 2 + kw / 2, 112), 18, fill=RED)
    centered(d, c["kicker"], kf, 56, im.width / 2, WHITE)
    y = 130
    for ln in lines:
        centered(d, ln, f, y, im.width / 2, BLACK)
        y += 84
    return im


def wrap_text(text, f, maxw):
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    out, cur = [], ""
    for w in text.split():
        tt = (cur + " " + w).strip()
        if d.textlength(tt, font=f) <= maxw:
            cur = tt
        else:
            out.append(cur)
            cur = w
    out.append(cur)
    return out


def card_search(c, t):
    im = card_base(900, 330)
    d = ImageDraw.Draw(im)
    centered(d, "WHAT PEOPLE TYPE", F(HEAD, 54), 56, im.width / 2, GREY)
    bar = (70, 140, im.width - 70, 250)
    d.rounded_rectangle(bar, 55, fill=(255, 255, 255), outline=(210, 210, 210), width=4)
    # magnifier
    cx, cy = bar[0] + 62, (bar[1] + bar[3]) // 2
    d.ellipse((cx - 20, cy - 24, cx + 16, cy + 12), outline=GREY, width=7)
    d.line((cx + 10, cy + 6, cx + 30, cy + 26), fill=GREY, width=8)
    q, qs = "", c["queries"]
    for i, (st, text) in enumerate(qs):
        if t >= st:
            nxt = qs[i + 1][0] if i + 1 < len(qs) else c["t1"]
            n = int(len(text) * min(1, (t - st) / max(0.35, min(0.8, (nxt - st) * 0.6))))
            q = text[:n]
    f = F(BODYB, 54)
    d.text((bar[0] + 110, cy - 33), q, font=f, fill=BLACK)
    if int(t * 2.5) % 2 == 0:  # cursor
        x = bar[0] + 112 + d.textlength(q, font=f)
        d.line((x, cy - 28, x, cy + 30), fill=BLACK, width=4)
    return im


def card_call(c, t):
    im = card_base(760, 380)
    d = ImageDraw.Draw(im)
    centered(d, "INCOMING CALL", F(HEAD, 60), 60, im.width / 2, GREY)
    centered(d, "NEW CUSTOMER", F(HEAD, 92), 125, im.width / 2, BLACK)
    pulse = 1 + 0.08 * math.sin(t * 12)
    r = 46 * pulse
    cross(d, im.width / 2 - 140, 320, r, RED)
    tick(d, im.width / 2 + 140, 320, r, GREEN)
    return im


def card_no(c, t):
    im = card_base(820, 300)
    d = ImageDraw.Draw(im)
    centered(d, "0 SEARCHES?", F(HEAD, 110), 60, im.width / 2, BLACK)
    centered(d, "SEO WON'T SAVE YOU", F(HEAD, 72), 190, im.width / 2, RED)
    return im


def card_growth(c, t):
    im = card_base(900, 420)
    d = ImageDraw.Draw(im)
    centered(d, "GOOD SEO COMPOUNDS", F(HEAD, 64), 56, im.width / 2, BLACK)
    x0, y0, x1, y1 = 110, 380, im.width - 110, 150
    d.line((x0, y0, x1, y0), fill=(200, 200, 200), width=4)
    p = ease((t - c["t0"]) / (c["t1"] - c["t0"] - 0.6))
    pts = []
    for i in range(61):
        u = i / 60
        if u > p:
            break
        pts.append((x0 + (x1 - x0) * u, y0 - (y0 - y1) * (u ** 2.4)))
    if len(pts) > 1:
        d.line(pts, fill=RED, width=12, joint="curve")
        ex, ey = pts[-1]
        d.ellipse((ex - 14, ey - 14, ex + 14, ey + 14), fill=RED)
    labs = c["labels"]
    f = F(HEAD, 40)
    for i, lab in enumerate(labs):
        u = [0.08, 0.55, 0.92][i]
        if p >= u - 0.05:
            lx = x0 + (x1 - x0) * u
            ly = y0 - (y0 - y1) * (u ** 2.4) - 70
            centered(d, lab, f, ly, lx, GREY if i == 0 else BLACK)
    return im


def card_stack(c, t):
    im = card_base(820, 380)
    d = ImageDraw.Draw(im)
    centered(d, "NEED JOBS THIS WEEK?", F(HEAD, 62), 56, im.width / 2, BLACK)
    p = (t - c["t0"])
    d.rounded_rectangle((120, 150, im.width - 120, 250), 22, fill=RED)
    centered(d, "1. GOOGLE ADS FIRST", F(HEAD, 62), 162, im.width / 2, WHITE)
    if p > c.get("second", 3.0):
        d.rounded_rectangle((120, 270, im.width - 120, 370), 22, fill=BLACK)
        centered(d, "2. THEN SEO UNDERNEATH", F(HEAD, 62), 282, im.width / 2, WHITE)
    return im


def card_checks(c, t):
    im = card_base(820, 300)
    d = ImageDraw.Draw(im)
    f = F(HEAD, 92)
    p = t - c["t0"]
    fy = F(HEAD, 96)
    for k, cx in enumerate((im.width / 2 - 170, im.width / 2 + 170)):
        if p > 0.4 * k:
            tick(d, cx - 95, 112, 38, GREEN)
            d.text((cx - 45, 62), "YES", font=fy, fill=GREEN)
    if p > 1.2:
        centered(d, "LOSING CALLS NOW", f, 160, im.width / 2, RED)
    return im


def card_dm(c, t):
    im = card_base(820, 320)
    d = ImageDraw.Draw(im)
    centered(d, "FREE GOOGLE PROFILE CHECK", F(HEAD, 60), 58, im.width / 2, BLACK)
    s = 1 + 0.05 * math.sin(t * 8)
    bw, bh = 380 * s, 130 * s
    d.rounded_rectangle((im.width / 2 - bw / 2, 150, im.width / 2 + bw / 2, 150 + bh), 36, fill=RED)
    centered(d, "DM US", F(HEAD, int(96 * s)), 158, im.width / 2, WHITE)
    return im


CARDS = {"title": card_title, "badge": card_badge, "search": card_search, "call": card_call, "no": card_no,
         "growth": card_growth, "stack": card_stack, "checks": card_checks, "dm": card_dm}


def paste_card(frame, c, t):
    im = CARDS[c["type"]](c, t)
    a_in = ease_out_back((t - c["t0"]) / 0.22)
    a_out = 1 - ease((t - (c["t1"] - 0.15)) / 0.15)
    s = max(0.05, min(a_in, 1.08)) * max(0.0, a_out) if t > c["t1"] - 0.15 else max(0.05, a_in)
    if s <= 0.02:
        return
    w, h = int(im.width * s), int(im.height * s)
    im = im.resize((w, h), Image.BILINEAR)
    cy = c.get("y", 470)
    frame.alpha_composite(im, (int((W - w) / 2), int(cy - h / 2)))


# ---------- badge ----------
hw, hh = HEADER.size
LOGO = HEADER.resize((300, int(hh * 300 / hw)))
BADGE = Image.new("RGBA", (340, LOGO.height + 24), (0, 0, 0, 0))
ImageDraw.Draw(BADGE).rounded_rectangle((0, 0, 339, LOGO.height + 23), 22, fill=WHITE + (235,))
BADGE.paste(LOGO, (20, 12))


# ---------- end card ----------
def cta_frame(c):
    tex = BG_TEXTURE.resize((W, int(W * BG_TEXTURE.height / BG_TEXTURE.width)))
    bg = Image.new("RGB", (W, H))
    for y in range(0, H, tex.height):
        bg.paste(tex, (0, y))
    bg = bg.filter(ImageFilter.GaussianBlur(1))
    red = Image.new("RGB", (W, H), (120, 0, 0))
    mask = Image.linear_gradient("L").resize((W, H))
    im = Image.composite(red, bg, mask.point(lambda v: int(v * 0.75)))
    d = ImageDraw.Draw(im)
    box = (70, 420, W - 70, 1500)
    d.rounded_rectangle(box, 50, fill=WHITE)
    logo = HEADER.resize((360, int(hh * 360 / hw)))
    im.paste(logo, ((W - logo.width) // 2, box[1] + 70))
    y = box[1] + 70 + logo.height + 70
    for line in c["title"]:
        t = line.strip("*").upper()
        centered(d, t, F(HEAD, 150), y, W / 2, RED if line.startswith("*") else BLACK)
        y += 160
    ul = UNDERLINE.resize((520, int(UNDERLINE.height * 520 / UNDERLINE.width)))
    im.paste(ul, ((W - ul.width) // 2, y))
    y += ul.height + 50
    for ln in wrap_text(c["body"], F(BODY, 52), box[2] - box[0] - 140):
        centered(d, ln, F(BODY, 52), y, W / 2, BLACK)
        y += 66
    kw = d.textlength(c["keyword"], font=F(HEAD, 96))
    d.rounded_rectangle(((W - kw) / 2 - 60, y + 50, (W + kw) / 2 + 60, y + 190), 34, fill=RED)
    centered(d, c["keyword"], F(HEAD, 96), y + 68, W / 2, WHITE)
    centered(d, "@gimsresults", F(BODYB, 46), 1620, W / 2, WHITE)
    return im


# ---------- render ----------
def zoom_at(t):
    """Punch in/out on caption changes: alternate 1.00 and 1.10 with a fast ease."""
    idx = max([i for i, (a, _) in enumerate(cap_times) if a <= t] or [0])
    target = 1.10 if idx % 2 else 1.0
    prev = 1.0 if idx % 2 else 1.10
    if idx == 0:
        prev = 1.0
    return prev + (target - prev) * ease((t - cap_times[idx][0]) / 0.18)


def main():
    clips = spec["clips"]
    total = sum(c["dur"] for c in clips)
    cta = spec["cta"]
    cta_img = cta_frame(cta)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                            "-pix_fmt", "yuv420p", "/tmp/edit_video.mp4"], stdin=subprocess.PIPE)
    t_off = 0.0
    fno = 0
    for c in clips:
        n = int(round(c["dur"] * FPS))
        dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", c["src"], "-vf",
                                f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
                                "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        for i in range(n):
            raw = dec.stdout.read(W * H * 3)
            if len(raw) < W * H * 3:
                raw = last
            last = raw
            t = fno / FPS
            fr = Image.frombytes("RGB", (W, H), raw)
            z = zoom_at(t)
            if z > 1.001:
                cw, ch = W / z, H / z
                x0, y0 = (W - cw) / 2, (H - ch) * 0.38
                fr = fr.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
            fr = fr.convert("RGBA")
            fr.alpha_composite(BADGE, ((W - BADGE.width) // 2, 70))
            for cd in spec["cards"]:
                if cd["t0"] <= t < cd["t1"]:
                    paste_card(fr, cd, t)
            for k, (a, b) in enumerate(cap_times):
                if a <= t < b:
                    draw_caption(fr, k, t)
            enc.stdin.write(fr.convert("RGB").tobytes())
            fno += 1
        dec.wait()
        t_off += c["dur"]
    for i in range(int(cta["dur"] * FPS)):
        z = 1 + 0.03 * i / (cta["dur"] * FPS)
        cw, ch = W / z, H / z
        fr = cta_img.resize((W, H), Image.BICUBIC, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
        enc.stdin.write(fr.tobytes())
    enc.stdin.close()
    enc.wait()
    dur = total + cta["dur"]
    # audio: voice + ducked music bed
    inputs = ["-i", "/tmp/edit_video.mp4", "-i", spec["voice"]]
    if spec.get("music"):
        inputs += ["-i", spec["music"]]
        # voice is pre-normalised (~-14 LUFS); music sits ~18 dB below it and ducks further while he talks
        af = (f"[1:a]aresample=44100,aformat=channel_layouts=stereo,apad,atrim=0:{dur},asplit=2[v1][v2];"
              f"[2:a]aresample=44100,aformat=channel_layouts=stereo,atrim=0:{dur},volume={spec.get('music_gain', 0.14)}[m];"
              f"[m][v2]sidechaincompress=threshold=0.02:ratio=8:attack=15:release=350[md];"
              f"[v1][md]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89[a]")
    else:
        af = f"[1:a]aresample=44100,apad,atrim=0:{dur},loudnorm=I=-14:TP=-1.5[a]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", af, "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", str(dur), OUT], check=True)
    print(OUT, round(dur, 2), "s")


if __name__ == "__main__":
    main()
