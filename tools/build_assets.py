"""Renders every image used by the profile README.

Everything is drawn as a mounted Japanese scroll: aged washi paper inside a
white mat, sumi ink brush lettering, ink-wash mountains, a vermilion seal, and
large kanji that drift in and out of the paper at low opacity.

    python tools/build_assets.py

Needs Yuji Syuku (tools/fonts, OFL) for the brush lettering and Goudy Old
Style for body text.
"""

import math
import os
import random
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ICONS = os.path.join(HERE, "icons")
BRUSH = os.path.join(HERE, "fonts", "YujiSyuku-Regular.ttf")

USER = "Greenythebeany"

# light: cream washi and black sumi; dark: night paper and pale ink. The mat
# is white in both, so the scrolls read as mounted on GitHub's dark canvas.
LIGHT = {
    "page": (255, 255, 255),
    "mat": (255, 255, 255),
    "mat_edge": (222, 214, 200),
    "paper": (239, 229, 207),
    "ink": (28, 24, 22),
    "faded": (112, 100, 86),
    "seal": (182, 38, 30),
    "seal_ink": (246, 236, 214),
    "grain": 7,
}

DARK = {
    "page": (13, 17, 23),
    "mat": (238, 233, 223),
    "mat_edge": (238, 233, 223),
    "paper": (28, 27, 31),
    "ink": (236, 228, 210),
    "faded": (146, 138, 124),
    "seal": (192, 44, 36),
    "seal_ink": (240, 230, 210),
    "grain": 5,
}


# --------------------------------------------------------------------------- #
# fonts and text
# --------------------------------------------------------------------------- #

_font_cache = {}


def _find_font(name):
    for d in (os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
              os.path.join(os.environ.get("LOCALAPPDATA", ""),
                           "Microsoft", "Windows", "Fonts")):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    raise FileNotFoundError(name)


def brush(size):
    key = ("brush", size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(BRUSH, size)
    return _font_cache[key]


def serif(size, style=""):
    key = ("serif", size, style)
    if key not in _font_cache:
        name = {"": "GOUDOS.TTF", "b": "GOUDOSB.TTF", "i": "GOUDOSI.TTF"}[style]
        _font_cache[key] = ImageFont.truetype(_find_font(name), size)
    return _font_cache[key]


def width_of(s, font, tracking=0):
    if not s:
        return 0
    return font.getlength(s) + tracking * (len(s) - 1)


def text(d, xy, s, font, fill, tracking=0, align="left"):
    """Draw a string, optionally letterspaced. Returns the width drawn."""
    w = width_of(s, font, tracking)
    x, y = xy
    if align == "right":
        x -= w
    elif align == "center":
        x -= w / 2
    if tracking == 0:
        d.text((x, y), s, font=font, fill=fill)
    else:
        for ch in s:
            d.text((x, y), ch, font=font, fill=fill)
            x += font.getlength(ch) + tracking
    return w


def joined(d, xy, parts, font, fill, tracking=3, align="left", gap=36):
    """Parts set apart by small round ink dots. Goudy has no middle dot, and
    a drawn one sits on the x-height wherever the size goes."""
    ws = [width_of(p, font, tracking) for p in parts]
    total = sum(ws) + gap * (len(parts) - 1)
    x, y = xy
    if align == "right":
        x -= total
    elif align == "center":
        x -= total / 2
    asc, _ = font.getmetrics()
    r = max(1.8, font.size * 0.1)
    for i, (p, w) in enumerate(zip(parts, ws)):
        text(d, (x, y), p, font, fill, tracking)
        x += w
        if i < len(parts) - 1:
            cx, cy = x + gap / 2, y + asc * 0.6
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
            x += gap
    return total


def wrap(s, font, max_w):
    out, line = [], ""
    for word in s.split():
        trial = (line + " " + word).strip()
        if line and font.getlength(trial) > max_w:
            out.append(line)
            line = word
        else:
            line = trial
    if line:
        out.append(line)
    return out


def rgba(c, a):
    return tuple(c) + (int(round(255 * a)),)


# --------------------------------------------------------------------------- #
# paper, ink and brush
# --------------------------------------------------------------------------- #

def washi(w, h, theme, seed):
    """Paper with fine grain, slow blotches and a scatter of long fibres."""
    rng = np.random.default_rng(seed)
    base = np.array(theme["paper"], float)
    g = theme["grain"]
    fine = rng.normal(0, 1, (h, w))
    fine = np.asarray(Image.fromarray(((fine * 40) + 128).clip(0, 255)
                                      .astype("uint8")).filter(
        ImageFilter.GaussianBlur(0.8)), float) / 40 - 3.2
    coarse = rng.normal(0, 1, (h // 48 + 2, w // 48 + 2))
    coarse = np.asarray(Image.fromarray(((coarse * 40) + 128).clip(0, 255)
                                        .astype("uint8")).resize(
        (w, h), Image.BICUBIC), float) / 40 - 3.2
    a = base[None, None, :] + (fine * g * 0.5 + coarse * g)[..., None]
    img = Image.fromarray(a.clip(0, 255).astype("uint8"), "RGB")

    fib = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fib)
    r = random.Random(seed)
    tone = theme["ink"]
    for _ in range(int(w * h / 2600)):
        x, y = r.uniform(0, w), r.uniform(0, h)
        L, a0 = r.uniform(12, 60), r.uniform(0, math.pi)
        bend = r.uniform(-0.6, 0.6)
        pts = []
        for k in range(6):
            t = k / 5
            ang = a0 + bend * t
            pts.append((x + math.cos(ang) * L * t, y + math.sin(ang) * L * t))
        fd.line(pts, fill=rgba(tone, r.uniform(0.02, 0.06)), width=1)
    img.paste(fib, (0, 0), fib)
    return img


def draw(img):
    """A blending draw: on an RGB image, RGBA fills are mixed over what is
    already there instead of overwriting it, so faded ink stays faded."""
    return ImageDraw.Draw(img, "RGBA")


def lay(img, layer, xy=(0, 0)):
    img.paste(layer, xy, layer)


def mount(theme, w, h, seed, mat=12):
    """White mat, washi inside it, and a thin double rule just in from the
    paper edge, the way a hanging scroll is framed."""
    img = Image.new("RGB", (w, h), theme["page"])
    d = draw(img)
    d.rectangle([0, 0, w - 1, h - 1], fill=theme["mat"],
                outline=theme["mat_edge"])
    paper = washi(w - 2 * mat, h - 2 * mat, theme, seed)
    img.paste(paper, (mat, mat))
    d = draw(img)
    i0 = mat + 16
    d.rectangle([i0, i0, w - 1 - i0, h - 1 - i0],
                outline=rgba(theme["ink"], 0.55), width=2)
    i1 = i0 + 6
    d.rectangle([i1, i1, w - 1 - i1, h - 1 - i1],
                outline=rgba(theme["ink"], 0.22), width=1)
    return img


def stroke(layer, pts, width, color, alpha=1.0, seed=0, dry=0.25):
    """A brush stroke along a polyline: the bristles press in, swell, and lift
    off; near the edges some of them run dry and leave gaps."""
    rng = random.Random(seed)
    d = ImageDraw.Draw(layer)
    seg = []
    total = 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        seg.append((a, b, L))
        total += L
    if total == 0:
        return
    step = max(1.0, width / 6)
    n = int(total / step)
    s_acc = 0.0
    k = 0
    for a, b, L in seg:
        m = max(1, int(L / step))
        for j in range(m):
            t = j / m
            x = a[0] + (b[0] - a[0]) * t
            y = a[1] + (b[1] - a[1]) * t
            u = (s_acc + L * t) / total
            press = math.sin(math.pi * min(1, u * 1.15)) ** 0.6
            r = max(0.6, width / 2 * (0.35 + 0.65 * press)
                    * (1 + 0.08 * math.sin(k * 0.7)))
            col = rgba(color, alpha * (0.85 + 0.15 * rng.random()))
            d.ellipse([x - r, y - r, x + r, y + r], fill=col)
            if dry and u > 0.55:
                for _ in range(3):
                    if rng.random() < dry * u:
                        ox = rng.uniform(-r, r)
                        oy = rng.uniform(-r, r)
                        rr = rng.uniform(0.6, r * 0.35)
                        d.ellipse([x + ox - rr, y + oy - rr, x + ox + rr,
                                   y + oy + rr], fill=(0, 0, 0, 0))
            k += 1
        s_acc += L


def brush_rule(layer, x0, x1, y, width, color, alpha, seed):
    rng = random.Random(seed)
    pts = []
    n = 24
    for i in range(n + 1):
        t = i / n
        pts.append((x0 + (x1 - x0) * t,
                    y + math.sin(t * 3.1 + seed) * 1.6 + rng.uniform(-0.6, 0.6)))
    stroke(layer, pts, width, color, alpha, seed, dry=0.06)


def enso(layer, cx, cy, r, width, color, alpha, seed, start=-100, sweep=320):
    pts = []
    n = 90
    for i in range(n + 1):
        a = math.radians(start + sweep * i / n)
        rr = r * (1 + 0.02 * math.sin(i * 0.3 + seed))
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    stroke(layer, pts, width, color, alpha, seed, dry=0.4)


def ridge(w, seed, rough=1.0):
    """1-D fractal ridge in 0..1, built from a few octaves of random sines."""
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 1, w)
    y = np.zeros(w)
    amp, freq = 1.0, 1.4
    for _ in range(6):
        y += amp * np.sin(2 * np.pi * (freq * x + rng.uniform(0, 1)))
        amp *= 0.5 * rough + 0.05
        freq *= 2.1
    y = (y - y.min()) / (y.max() - y.min() + 1e-9)
    return y


def mountains(size, box, theme, seed, layers=3, strength=0.5, fade_left=True):
    """Ink-wash ridges: each one a hard brushed crest that bleeds downward
    into mist, the farther ones paler."""
    w, h = size
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    alpha = np.zeros((h, w))
    ys = np.arange(bh)[:, None]
    for k in range(layers):
        far = (layers - 1 - k) / max(1, layers - 1)
        r = ridge(bw, seed + k * 17, rough=0.9)
        top = bh * (0.15 + 0.32 * k / max(1, layers)) + r * bh * (0.45 - 0.08 * k)
        top = top[None, :]
        depth = ys - top
        a = np.where(depth >= 0, np.exp(-depth / (bh * (0.10 + 0.05 * k))), 0)
        a = a * (0.40 + 0.6 * (1 - far)) * strength
        alpha[y0:y1, x0:x1] = np.maximum(alpha[y0:y1, x0:x1], a)
    if fade_left:
        ramp = np.clip((np.arange(w) - x0) / (bw * 0.35), 0, 1)
        alpha *= ramp[None, :]
    a8 = Image.fromarray((alpha.clip(0, 1) * 255).astype("uint8"))
    a8 = a8.filter(ImageFilter.GaussianBlur(2.6))
    layer = Image.new("RGBA", (w, h), rgba(theme["ink"], 0))
    layer.putalpha(a8)
    return layer


def sun(layer, cx, cy, r, theme, alpha=0.9):
    d = ImageDraw.Draw(layer)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rgba(theme["seal"], alpha))


def birds(layer, pts, theme, alpha=0.7):
    for i, (x, y, s) in enumerate(pts):
        stroke(layer, [(x - s, y - s * 0.35), (x - s * 0.4, y - s * 0.5),
                       (x, y)], s * 0.22, theme["ink"], alpha, seed=i)
        stroke(layer, [(x, y), (x + s * 0.45, y - s * 0.55),
                       (x + s * 1.05, y - s * 0.45)], s * 0.22, theme["ink"],
               alpha, seed=i + 9)


def seal(img, box, chars, theme, seed=3):
    """A vermilion hanko: carved characters reversed out of a stamp whose
    edges and fill both bite unevenly into the paper."""
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    m = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(m)
    md.rounded_rectangle([0, 0, w - 1, h - 1], radius=max(2, w // 14),
                         fill=235)
    n = len(chars)
    size = int(min(w * 0.78, h * 0.86 / n))
    f = brush(size)
    for i, ch in enumerate(chars):
        cy = h * (i + 0.5) / n
        md.text((w / 2, cy), ch, font=f, fill=0, anchor="mm")
    rng = np.random.default_rng(seed)
    noise = rng.random((h, w))
    arr = np.asarray(m, float)
    arr = np.where(noise < 0.06, arr * 0.4, arr)
    m = Image.fromarray(arr.astype("uint8")).filter(ImageFilter.GaussianBlur(0.5))
    stamp = Image.new("RGBA", (w, h), rgba(theme["seal"], 1))
    stamp.putalpha(m)
    lay(img, stamp, (x0, y0))


def vertical(d, x, y, s, font, fill, gap=1.0):
    """Japanese set top to bottom, one character per line."""
    size = font.size
    for i, ch in enumerate(s):
        d.text((x, y + i * size * gap), ch, font=font, fill=fill, anchor="mt")


class Drift:
    """Big kanji that surface out of the paper and sink back once per loop,
    each on its own phase, so there is always one somewhere mid-breath."""

    def __init__(self, size, slots, theme, peak=0.11):
        self.slots = []
        for ch, x, y, s, off in slots:
            m = Image.new("L", size, 0)
            ImageDraw.Draw(m).text((x, y), ch, font=brush(s), fill=255,
                                   anchor="mm")
            box = m.getbbox()
            if box:
                self.slots.append((m.crop(box), box[:2], off))
        self.color = theme["ink"]
        self.peak = peak

    def apply(self, img, t, frames):
        for m, xy, off in self.slots:
            a = max(0.0, math.sin(2 * math.pi * (t / frames + off))) ** 2
            if a < 0.02:
                continue
            k = a * self.peak
            layer = Image.new("RGBA", m.size, rgba(self.color, 1))
            layer.putalpha(m.point(lambda v: int(v * k)))
            lay(img, layer, xy)


def save_gif(frames, path, duration):
    """One shared palette across every frame, so the encoder can ship each
    frame as just the rectangle that actually changed. The palette is drawn
    from several frames at once so the fading kanji have tones to land on."""
    picks = frames[::max(1, len(frames) // 4)][:4]
    w, h = frames[0].size
    sample = Image.new("RGB", (w, h * len(picks)))
    for i, f in enumerate(picks):
        sample.paste(f, (0, i * h))
    pal = sample.convert("P", palette=Image.ADAPTIVE, colors=255)
    qs = [f.quantize(palette=pal, dither=Image.NONE) for f in frames]
    qs[0].save(path, save_all=True, append_images=qs[1:], loop=0,
               duration=duration, disposal=1, optimize=False)
    return path


# --------------------------------------------------------------------------- #
# hero
# --------------------------------------------------------------------------- #

ABOUT = (
    "I build things that move: motors, servos, state machines and the "
    "occasional terminal app that refuses to act like one. C when it has to "
    "be fast, Python when it has to exist by tomorrow, MATLAB and Simulink "
    "when it has to be proven before it is soldered."
)

PATHS = [
    ("機", "Embedded systems"),
    ("制", "Control theory"),
    ("動", "Robotics"),
    ("自", "Industrial automation"),
    ("模", "Simulation"),
    ("眠", "Sleep, not found"),
]


def render_hero(theme, out_path, frames=20, duration=160):
    W, H = 1800, 1000
    img = mount(theme, W, H, seed=11)
    ink, faded = theme["ink"], theme["faded"]

    art = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sun(art, 1420, 300, 112, theme, 0.88)
    lay(img, art)
    lay(img, mountains((W, H), (760, 330, W - 40, H - 40), theme,
                                  seed=5, layers=3, strength=0.62))
    art = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    birds(art, [(1210, 250, 18), (1250, 222, 13), (1176, 214, 10)], theme)
    lay(img, art)

    d = draw(img)
    L = 92
    joined(d, (L, 84), ["ROBOTICS & CYBERNETICS", "FEI STU", "BRATISLAVA"],
           serif(21), rgba(faded, 1))
    d.text((L - 6, 118), "GreenyBeany", font=brush(148), fill=rgba(ink, 1))
    art = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    brush_rule(art, L, L + 560, 316, 9, ink, 0.85, seed=2)
    lay(img, art)
    d = draw(img)

    f_body = serif(30)
    for i, line in enumerate(wrap(ABOUT, f_body, 860)):
        d.text((L, 350 + i * 42), line, font=f_body, fill=rgba(ink, 0.92))

    w = joined(d, (L, 548), ["THE WAY", ""], serif(19), rgba(faded, 1))
    d.text((L + w, 540), "道", font=brush(28), fill=rgba(faded, 1))
    f_k, f_p = brush(40), serif(27)
    for i, (k, s) in enumerate(PATHS):
        x = L + (i % 2) * 430
        y = 594 + (i // 2) * 62
        last = i == len(PATHS) - 1
        d.text((x, y), k, font=f_k, fill=rgba(theme["seal"] if not last
                                              else faded, 0.95))
        d.text((x + 58, y + 8), s, font=f_p,
               fill=rgba(faded if last else ink, 1))

    joined(d, (L, H - 112), ["04:04", "TIME NOT FOUND", "UTC+1:00"], serif(19),
           rgba(faded, 1))

    # the name, written down the right edge, signed with the seal
    vertical(d, W - 132, 92, "緑豆", brush(132), rgba(ink, 1), gap=1.02)
    seal(img, (W - 170, 380, W - 94, 456), "豆", theme)
    vertical(draw(img), W - 214, 104, "動く物を作る", brush(30),
             rgba(faded, 1), gap=1.18)

    drift = Drift((W, H), [
        ("夢", 560, 240, 300, 0.00),
        ("道", 1080, 640, 260, 0.33),
        ("創", 300, 760, 240, 0.66),
        ("風", 1460, 760, 220, 0.50),
        ("機", 920, 170, 200, 0.16),
    ], theme)

    out = []
    for t in range(frames):
        f = img.copy()
        drift.apply(f, t, frames)
        out.append(f)
    return save_gif(out, out_path, duration)


# --------------------------------------------------------------------------- #
# project cards
# --------------------------------------------------------------------------- #

PROJECTS = [
    {
        "slug": "triptych",
        "index": "一",
        "name": "Triptych",
        "jp": "三連",
        "url": "https://github.com/Greenythebeany/triptych",
        "site": "https://triptych.greenybeany.dev/",
        "desc": "Free, open-source music app for your own Jellyfin server. Spotify, "
                "Apple Music or Nothing style, synced lyrics, offline downloads, "
                "stats and Wrapped.",
        "specs": ["JavaScript", "Music", "Jellyfin"],
        "drift": "音",
    },
    {
        "slug": "beanyik",
        "index": "二",
        "name": "BeanyIK",
        "jp": "運動学",
        "url": "https://github.com/Greenythebeany/BeanyIK",
        "site": "https://greenybeany.dev/BeanyIK/",
        "desc": "Drag and drop robot kinematics builder. DH parameters or custom "
                "matrices, forward and inverse kinematics solved live as the arm "
                "is assembled.",
        "specs": ["JavaScript", "Electron", "DH / IK"],
        "drift": "腕",
    },
    {
        "slug": "beanydrive",
        "index": "三",
        "name": "BeanyDrive",
        "jp": "雲倉",
        "url": "https://github.com/Greenythebeany/BeanyDrive",
        "desc": "Turns a Discord channel into a personal cloud drive. Chunks files, "
                "uploads them as attachments, rebuilds them on the way back down.",
        "specs": ["JavaScript", "Storage", "Discord API"],
        "drift": "雲",
    },
]


def render_card(p, theme, out_path, frames=16, duration=160):
    W, H = 1800, 340
    seed = sum(map(ord, p["slug"]))
    img = mount(theme, W, H, seed=seed)
    ink, faded = theme["ink"], theme["faded"]

    lay(img, mountains((W, H), (1100, 120, W - 40, H - 40), theme,
                                  seed=seed, layers=2, strength=0.32))

    # Pillow ignores a fill's alpha when it rasterises glyphs, so faint type
    # goes through its own layer
    ghost = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ghost).text((W - 330, H / 2 - 24), p["index"],
                               font=brush(200), fill=rgba(ink, 0.09),
                               anchor="mm")
    lay(img, ghost)
    d = draw(img)

    # the app icon, hung in its own thin ink frame
    side = 216
    ix, iy = 76, (H - side) // 2
    d.rectangle([ix - 10, iy - 10, ix + side + 9, iy + side + 9],
                outline=rgba(ink, 0.5), width=1)
    icon = Image.open(os.path.join(ICONS, p["slug"] + ".png")).convert("RGBA")
    lay(img, icon.resize((side, side), Image.LANCZOS), (ix, iy))

    tx = ix + side + 64
    d = draw(img)
    nw = d.textlength(p["name"], font=brush(78))
    d.text((tx - 4, 52), p["name"], font=brush(78), fill=rgba(ink, 1))
    d.text((tx + nw + 22, 84), p["jp"], font=brush(34), fill=rgba(faded, 1))
    f_desc = serif(25)
    for i, line in enumerate(wrap(p["desc"], f_desc, 860)):
        d.text((tx, 160 + i * 34), line, font=f_desc, fill=rgba(ink, 0.88))
    joined(d, (tx, H - 84), [s.upper() for s in p["specs"]], serif(18),
           rgba(faded, 1))

    label = "OPEN WEBSITE" if p.get("site") else "OPEN ON GITHUB"
    sx = W - 92
    seal(img, (sx - 58, H - 120, sx, H - 62), "開", theme, seed=seed)
    text(draw(img), (sx - 76, H - 104), label, serif(21, "b"),
         rgba(ink, 1), tracking=3, align="right")

    drift = Drift((W, H), [(p["drift"], 1040, H / 2, 240, 0.0)], theme,
                  peak=0.10)
    out = []
    for t in range(frames):
        f = img.copy()
        drift.apply(f, t, frames)
        out.append(f)
    return save_gif(out, out_path, duration)


# --------------------------------------------------------------------------- #
# stack list
# --------------------------------------------------------------------------- #

STACK = [
    ("C / C++", "embedded"),
    ("Python", "tooling"),
    ("Java", "coursework"),
    ("JavaScript", "web / electron"),
    ("MATLAB", "modelling"),
    ("Simulink", "simulation"),
    ("Arduino", "hardware"),
    ("Git / GitHub", "versioning"),
    ("Linux (Fedora / Ubuntu)", "daily driver"),
    ("VS Code / CLion / IDEA", "editors"),
]

NUMERALS = "一二三四五六七八九十"


def render_stack(theme, out_path, frames=16, duration=160):
    W = 1800
    rh = 46
    H = 196 + len(STACK) * rh + 56
    img = mount(theme, W, H, seed=23)
    ink, faded = theme["ink"], theme["faded"]

    d = draw(img)
    L, R = 92, W - 92
    d.text((L - 4, 58), "Stack", font=brush(72), fill=rgba(ink, 1))
    d.text((L + d.textlength("Stack", font=brush(72)) + 18, 88), "道具",
           font=brush(34), fill=rgba(faded, 1))
    text(d, (R, 92), "TEN TOOLS, WELL WORN", serif(19), rgba(faded, 1),
         tracking=3, align="right")

    art = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y0 = 172
    for i in range(len(STACK) + 1):
        brush_rule(art, L, R, y0 + i * rh, 2.6 if i else 4.2, ink,
                   0.35 if i else 0.7, seed=i + 40)
    lay(img, art)
    d = draw(img)

    f_n, f_dev, f_fn = brush(28), serif(28), serif(25, "i")
    for i, (dev, fn) in enumerate(STACK):
        y = y0 + i * rh
        d.text((L + 6, y + 8), NUMERALS[i], font=f_n,
               fill=rgba(theme["seal"], 0.9))
        d.text((L + 80, y + 9), dev, font=f_dev, fill=rgba(ink, 1))
        d.text((L + 760, y + 11), fn, font=f_fn, fill=rgba(faded, 1))

    drift = Drift((W, H), [
        ("技", 1420, H / 2 + 20, 300, 0.0),
        ("学", 1180, H / 2 + 120, 220, 0.5),
    ], theme, peak=0.09)
    out = []
    for t in range(frames):
        f = img.copy()
        drift.apply(f, t, frames)
        out.append(f)
    return save_gif(out, out_path, duration)


# --------------------------------------------------------------------------- #
# footer
# --------------------------------------------------------------------------- #

def render_footer(theme, out_path, frames=16, duration=160):
    W, H = 1800, 240
    img = mount(theme, W, H, seed=31)
    ink, faded = theme["ink"], theme["faded"]

    art = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    enso(art, 300, H / 2, 74, 15, ink, 0.55, seed=4)
    lay(img, art)

    d = draw(img)
    msg = "Thanks for stopping by"
    f = brush(64)
    mw = d.textlength(msg, font=f)
    d.text((W / 2, 70), msg, font=f, fill=rgba(ink, 1), anchor="mt")
    f_k, f_u = brush(26), serif(19)
    url = "GITHUB.COM/" + USER.upper()
    kw = d.textlength("ありがとう", font=f_k)
    total = kw + 36 + width_of(url, f_u, 3)
    x = W / 2 - total / 2
    d.text((x, 152), "ありがとう", font=f_k, fill=rgba(faded, 1))
    joined(d, (x + kw, 158), ["", url], f_u, rgba(faded, 1))
    seal(img, (W / 2 + mw / 2 + 30, 70, W / 2 + mw / 2 + 96, 136), "豆",
         theme, seed=9)

    drift = Drift((W, H), [("縁", 1500, H / 2, 200, 0.0)], theme, peak=0.10)
    out = []
    for t in range(frames):
        fr = img.copy()
        drift.apply(fr, t, frames)
        out.append(fr)
    return save_gif(out, out_path, duration)


# --------------------------------------------------------------------------- #
# snake contribution graph, recoloured to match
# --------------------------------------------------------------------------- #

# --cs is the snake, --c0..--c4 the contribution levels, --ce an eaten cell,
# --cb the cell stroke. snk emits no --c0 in its dark block, which would leave
# pale cells on a dark canvas, so every variant declares the full set.
# --ce sits a hair off the page background rather than exactly on it, so an
# empty day still reads as a cell instead of vanishing. Levels go up in ink,
# and the snake is the seal's vermilion.
SNAKE = {
    "dark": ("--cb:#eee9df1a;--cs:#c02c24;--ce:#1c1b1f;--c0:#1c1b1f;"
             "--c1:#4a4640;--c2:#7d766b;--c3:#b4ab9c;--c4:#ece4d2"),
    "light": ("--cb:#1c181620;--cs:#b6261e;--ce:#efe5cf;--c0:#efe5cf;"
              "--c1:#d4c6a8;--c2:#a39579;--c3:#62584b;--c4:#1c1816"),
}


def render_snake():
    """Split contributions.svg into one file per theme.

    The generated SVG themes itself with its own prefers-color-scheme block,
    but an SVG loaded through <img> resolves that against the *operating
    system*, not GitHub's theme toggle -- so the snake ends up disagreeing
    with every other image on the page. Stripping the media query and emitting
    two fixed palettes puts it back under the same <picture> switch as the
    rest of the README.

    contributions.svg stays untouched as the input, so re-running snk and
    rebuilding is all it takes to refresh the graph.
    """
    src = os.path.join(ROOT, "contributions.svg")
    if not os.path.exists(src):
        return []
    svg = open(src, encoding="utf-8").read()
    svg = re.sub(r"@media\s*\(prefers-color-scheme:\s*dark\)\s*"
                 r"\{\s*:root\{[^}]*\}\s*\}", "", svg)

    out = []
    for name, palette in SNAKE.items():
        variant = re.sub(r":root\{[^}]*\}", ":root{" + palette + "}",
                         svg, count=1)
        path = os.path.join(ROOT, "contributions-%s.svg" % name)
        open(path, "w", encoding="utf-8").write(variant)
        out.append(path)
    return out


# --------------------------------------------------------------------------- #

def main():
    for suffix, theme in (("dark", DARK), ("light", LIGHT)):
        outs = [render_hero(theme, os.path.join(ROOT, "hero-%s.gif" % suffix))]
        for p in PROJECTS:
            outs.append(render_card(
                p, theme,
                os.path.join(ROOT, "card-%s-%s.gif" % (p["slug"], suffix))))
        outs.append(render_stack(theme,
                                 os.path.join(ROOT, "stack-%s.gif" % suffix)))
        outs.append(render_footer(theme,
                                  os.path.join(ROOT, "footer-%s.gif" % suffix)))
        for o in outs:
            print("%8.0f KB  %s" % (os.path.getsize(o) / 1024,
                                    os.path.basename(o)))
    for o in render_snake():
        print("%8.0f KB  %s" % (os.path.getsize(o) / 1024,
                                os.path.basename(o)))


if __name__ == "__main__":
    main()
