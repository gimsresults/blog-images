"""Find GIMS blog posts still using the placeholder cover and write a cover spec
(covers/<slug>.json) for each one, built from the post title.

Runs inside the GitHub Action every few minutes. Reads only public pages.
"""
import html
import json
import pathlib
import re
import urllib.parse
import urllib.request

SITE = "https://gimsresults.com.au"
PLACEHOLDER = "assets/placeholder.jpg"
ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (gims-cover-bot)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def meta(page, prop):
    m = re.search(r'<meta[^>]+property="%s"[^>]+content="([^"]*)"' % re.escape(prop), page)
    if not m:
        m = re.search(r'<meta[^>]+content="([^"]*)"[^>]+property="%s"' % re.escape(prop), page)
    return html.unescape(m.group(1)) if m else ""


def split_title(title):
    """Split a title into 2-4 balanced lines; the second line is red."""
    words = title.upper().split()
    total = len(" ".join(words))
    n = 2 if total <= 24 else 3 if total <= 54 else 4
    n = min(n, len(words))
    best = None

    def rec(start, k, acc):
        nonlocal best
        if k == 1:
            parts = acc + [" ".join(words[start:])]
            score = max(len(p) for p in parts)
            if best is None or score < best[0]:
                best = (score, parts)
            return
        for end in range(start + 1, len(words) - k + 2):
            rec(end, k - 1, acc + [" ".join(words[start:end])])

    rec(0, n, [])
    lines = best[1]
    red = 1 if len(lines) > 1 else 0
    lines[red] = "*" + lines[red] + "*"
    return lines


def main():
    index = get(SITE + "/blog")
    links = sorted(set(re.findall(r'href="(https://gimsresults\.com\.au/post/[^"#?]+)"', index)))
    created = 0
    for url in links:
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        if (ROOT / "images" / f"{slug}.jpg").exists() or (ROOT / "covers" / f"{slug}.json").exists():
            continue
        try:
            page = get(url)
        except Exception as e:  # keep going on one bad page
            print("skip", url, e)
            continue
        og_image = meta(page, "og:image")
        if PLACEHOLDER not in og_image:
            continue
        title = meta(page, "og:title") or slug.replace("-", " ")
        spec = urllib.parse.parse_qs(urllib.parse.urlparse(og_image).query).get("cover", [""])[0]
        lines = [l.strip() for l in spec.split("|") if l.strip()][:4] if spec else []
        if not lines or not any(l.startswith("*") and l.endswith("*") for l in lines):
            lines = split_title(title)
        (ROOT / "covers" / f"{slug}.json").write_text(json.dumps({"lines": lines, "title": title}) + "\n")
        print("queued", slug, lines)
        created += 1
    print("new cover specs:", created)


if __name__ == "__main__":
    main()
