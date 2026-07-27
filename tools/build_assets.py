"""Renders every image used by the profile README.

Everything is drawn on a monospace character grid to keep the "BIOS setup
screen" look consistent across the hero, the project cards and the stack table.

    python tools/build_assets.py

Drop a portrait photo at <root>/face.jpg (or face.png) to get a sharp ASCII
face; without one the script falls back to recovering a luminance map out of
the previous hero render.
"""

import os
import random
import re

import numpy as np
from PIL import (Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter,
                 ImageFont, ImageOps)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
REG = os.path.join(FONTS, "consola.ttf")
BOLD = os.path.join(FONTS, "consolab.ttf")

USER = "Greenythebeany"

# backgrounds match GitHub's canvas so the panels bleed into the page
DARK = {
    "bg": (13, 17, 23),
    "faint": (14, 58, 50),
    "dim": (26, 104, 89),
    "mid": (47, 169, 143),
    "bright": (124, 245, 213),
    "hot": (196, 255, 240),
    "rule": (35, 126, 108),
    "wordmark": (13, 51, 44),
    "wordmark_edge": (24, 92, 79),
}

LIGHT = {
    "bg": (255, 255, 255),
    "faint": (198, 214, 208),
    "dim": (132, 163, 154),
    "mid": (58, 113, 100),
    "bright": (10, 58, 48),
    "hot": (2, 30, 24),
    "rule": (120, 164, 151),
    "wordmark": (228, 238, 234),
    "wordmark_edge": (198, 216, 208),
}

RAMP = " .`',:;~-+=*!?%$#&@\u2592\u2593\u2588"


# --------------------------------------------------------------------------- #
# low level helpers
# --------------------------------------------------------------------------- #

_font_cache = {}


def mono(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(BOLD if bold else REG, size)
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


def frame(d, box, color, radius=0):
    if radius:
        d.rounded_rectangle(box, radius=radius, outline=color, width=1)
    else:
        d.rectangle(box, outline=color, width=1)


def wrap(s, n):
    out, line = [], ""
    for word in s.split():
        if len(line) + len(word) + 1 > n:
            out.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line:
        out.append(line)
    return out


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


# --------------------------------------------------------------------------- #
# animation output
# --------------------------------------------------------------------------- #

def sweep(img, box, y, height, theme, strength=0.55):
    """A CRT refresh band: a horizontal slice gets brighter *and* picks up an
    additive phosphor glow, so the beam is visible over empty background and
    not just over the glyphs."""
    x0, y0, x1, y1 = box
    glow = theme["mid"]
    steps = 6
    for s in range(steps):
        top = int(y + height * s / steps)
        bottom = int(y + height * (s + 1) / steps)
        top, bottom = max(top, y0), min(bottom, y1)
        if bottom <= top:
            continue
        # triangular falloff across the band
        f = (1.0 - abs((s + 0.5) / steps - 0.5) * 2) * strength
        band = img.crop((x0, top, x1, bottom))
        band = ImageEnhance.Brightness(band).enhance(1 + 0.75 * f)
        wash = Image.new("RGB", band.size,
                         tuple(int(c * 0.30 * f) for c in glow))
        img.paste(ImageChops.add(band, wash), (x0, top))


def save_gif(frames, path, duration):
    """One shared palette across every frame, so the encoder can ship each
    frame as just the rectangle that actually changed."""
    base = frames[0].convert("P", palette=Image.ADAPTIVE, colors=200)
    qs = [f.quantize(palette=base, dither=Image.NONE) for f in frames]
    qs[0].save(path, save_all=True, append_images=qs[1:], loop=0,
               duration=duration, disposal=1, optimize=False)
    return path


# --------------------------------------------------------------------------- #
# glitched display type
# --------------------------------------------------------------------------- #

def glitch_text(s, font, tracking, fg, ghost, seed=7):
    """Render display type into an RGBA tile with sliced/offset scanlines."""
    w = int(width_of(s, font, tracking)) + 40
    asc, desc = font.getmetrics()
    h = asc + desc + 20
    tile = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    text(td, (20, 8), s, font, ghost + (200,), tracking)

    solid = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(solid)
    text(sd, (20, 8), s, font, fg + (255,), tracking)

    rng = random.Random(seed)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.alpha_composite(tile, (rng.randint(3, 7), 0))

    y = 0
    while y < h:
        band = rng.randint(3, 11)
        strip = solid.crop((0, y, w, min(y + band, h)))
        dx = rng.choice([0, 0, 0, -6, -3, 3, 6, 11])
        out.alpha_composite(strip, (max(0, dx), y))
        y += band

    # a couple of hard dropouts, like a bad refresh
    od = ImageDraw.Draw(out)
    for _ in range(3):
        yy = rng.randint(8, h - 12)
        od.rectangle([0, yy, w, yy + rng.randint(1, 3)], fill=(0, 0, 0, 0))
    return out


# --------------------------------------------------------------------------- #
# the ASCII portrait
# --------------------------------------------------------------------------- #

RECOVERED = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "face-recovered.png")
_face = None


def fit_aspect(im, target, bias=0.42):
    """Centre-crop to a width/height ratio, sitting the window slightly high
    so the crop takes shoulders off rather than hair."""
    w, h = im.size
    if w / h < target:
        nh = int(w / target)
        top = int((h - nh) * bias)
        return im.crop((0, top, w, top + nh))
    nw = int(h * target)
    lf = (w - nw) // 2
    return im.crop((lf, 0, lf + nw, h))


def curve(im, floor=0.30, gamma=0.85, blur=0.7):
    """Push the backdrop to true black and stretch what is left, so the ramp
    spends all of its glyphs on the face instead of on grain."""
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(im).astype(float) / 255.0
    lo, hi = np.percentile(a, 3), np.percentile(a, 97)
    if hi - lo < 1e-6:
        hi = lo + 1e-6
    a = np.clip((a - lo) / (hi - lo), 0, 1)
    a = np.clip((a - floor) / (1 - floor), 0, 1) ** gamma
    return Image.fromarray((a * 255).astype("uint8"))


def load_face():
    """Luminance source for the portrait: a real photo if one is present,
    otherwise the tone map recovered out of the very first hero render (kept
    beside this script, because main() overwrites hero-dark.png)."""
    global _face
    if _face is not None:
        return _face

    src, real = None, False
    for name in ("face.jpg", "face.png", "face.jpeg", "me.jpg", "me.png"):
        p = os.path.join(ROOT, name)
        if os.path.exists(p):
            # a light studio backdrop has to become empty space, not a wall
            src = ImageOps.invert(Image.open(p).convert("L"))
            src = src.resize((260, int(260 * src.height / src.width)),
                             Image.LANCZOS)
            real = True
            break

    if src is None and os.path.exists(RECOVERED):
        src = Image.open(RECOVERED).convert("L")

    if src is None:
        legacy = os.path.join(ROOT, "hero-dark.png")
        if os.path.exists(legacy):
            src = Image.open(legacy).convert("L").crop((76, 330, 620, 1072))
            src = ImageOps.autocontrast(src.resize((136, 186), Image.LANCZOS),
                                        cutoff=(0.5, 6))
            src.save(RECOVERED)
        else:
            src = Image.new("L", (100, 130), 0)

    _face = (curve(fit_aspect(src, 0.88), floor=0.30 if not real else 0.24),
             real)
    return _face


def portrait(d, box, theme, cw, ch, gamma=1.0):
    x0, y0, x1, y1 = box
    cols = int((x1 - x0) // cw)
    rows = int((y1 - y0) // ch)

    src, _ = load_face()
    sw, sh = src.size
    # fit inside the panel while respecting the 2:1 character cell
    scale = min(cols / sw, rows * (ch / cw) / sh)
    gw = max(1, int(sw * scale))
    gh = max(1, int(sh * scale * (cw / ch)))
    grid = src.resize((gw, gh), Image.LANCZOS)
    px = grid.load()

    ox = x0 + (cols - gw) * cw // 2
    oy = y0 + (rows - gh) * ch // 2

    font = mono(int(ch * 0.95))
    rng = random.Random(11)
    top = len(RAMP) - 1

    for j in range(gh):
        for i in range(gw):
            v = pow(px[i, j] / 255.0, gamma)
            if v < 0.05:
                continue
            k = int(round(v * top + rng.uniform(-0.2, 0.2)))
            k = max(1, min(top, k))
            if v > 0.78:
                col = theme["hot"]
            elif v > 0.45:
                col = theme["bright"]
            elif v > 0.22:
                col = theme["mid"]
            else:
                col = theme["dim"]
            d.text((ox + i * cw, oy + j * ch), RAMP[k], font=font, fill=col)


# --------------------------------------------------------------------------- #
# copy
# --------------------------------------------------------------------------- #

LOG_HEAD = [
    ("dim", "0100 GREENYBEANY BIOS (C) 2026 GREENYBEANY SOFTWARE, INC."),
    ("dim", "0100 SYSTEM CONFIGURATION UTILITY -- VERSION 2.6"),
    ("faint", "0100"),
    ("dim", "0101 POST ......................................... OK"),
    ("dim", "0102 OPERATOR DETECTED ON CHANNEL 0 ................ OK"),
    ("faint", "0102"),
    ("mid", "0103 OPERATOR"),
    ("dim", "0103   HANDLE ........ GREENYBEANY"),
    ("dim", "0103   ROLE .......... STUDENT / ROBOTICS & CYBERNETICS"),
    ("dim", "0103   SITE .......... FEI STU BRATISLAVA, SK"),
    ("dim", "0103   SHELL ......... BASH / ZSH"),
    ("faint", "0103"),
    ("mid", "0104 SUBSYSTEMS ENABLED"),
    ("dim", "0104   [X] EMBEDDED SYSTEMS      [X] CONTROL THEORY"),
    ("dim", "0104   [X] INDUSTRIAL AUTOMATION [X] SIMULATION"),
    ("dim", "0104   [X] ROBOTICS              [ ] SLEEP"),
    ("faint", "0104"),
    ("mid", "0105 VOLUMES MOUNTED"),
    ("dim", "0105   /dev/quest  BEANY'S DISCORD QUEST MAKER"),
    ("dim", "0105   /dev/box    BEANYBOX"),
    ("dim", "0105   /dev/drive  BEANYDRIVE"),
    ("faint", "0105"),
    ("dim", "0106 MEMORY TEST : 640K BASE, 65535K EXTENDED ...... OK"),
    ("dim", "0107 CAFFEINE BUS : SATURATED ...................... OK"),
    ("dim", "0108 SEARCHING FOR BOOT RECORD ..................... OK"),
    ("faint", "0108"),
]

LOG_BODY = (
    "I BUILD THINGS THAT MOVE. MOTORS, SERVOS, STATE MACHINES, THE OCCASIONAL "
    "TERMINAL APP THAT REFUSES TO ACT LIKE ONE. MOST OF WHAT I MAKE STARTS AS A "
    "SMALL ANNOYANCE -- A CLIENT THAT IS TOO HEAVY, A STORAGE LIMIT THAT IS TOO "
    "LOW, A CHORE A MACHINE SHOULD BE DOING INSTEAD OF ME -- AND ENDS AS "
    "SOMETHING I CAN RUN FROM A BLINKING CURSOR. "
    "I LIKE THE PART OF ENGINEERING WHERE THEORY MEETS A REAL ACTUATOR AND "
    "IMMEDIATELY DISAGREES WITH THE MODEL. CONTROL LOOPS, SENSOR NOISE, TIMING "
    "BUDGETS, THE SLOW WORK OF MAKING A SYSTEM BEHAVE THE SAME WAY TWICE. "
    "STUDYING ROBOTICS AND CYBERNETICS AT FEI STU IN BRATISLAVA. WRITING C WHEN "
    "IT HAS TO BE FAST, PYTHON WHEN IT HAS TO EXIST BY TOMORROW, MATLAB AND "
    "SIMULINK WHEN SOMETHING HAS TO BE PROVEN BEFORE IT IS SOLDERED. "
    "EVERYTHING HERE IS A WORK IN PROGRESS. THAT IS THE POINT. PULL REQUESTS, "
    "ISSUES AND BAD IDEAS ARE ALL WELCOME."
)

LOG_TAIL = [
    ("faint", ""),
    ("mid", "0109 DUMP 0000:7C00"),
    ("faint", "0109 7C00  47 52 45 45 4E 59 42 45  41 4E 59 20 42 49 4F 53   GREENYBEANY BIOS"),
    ("faint", "0109 7C10  20 32 30 32 36 20 2D 2D  20 46 45 49 20 53 54 55    2026 -- FEI STU"),
    ("faint", "0109 7C20  20 42 52 41 54 49 53 4C  41 56 41 2C 20 53 4B 00    BRATISLAVA, SK."),
    ("faint", "0109 7C30  52 4F 42 4F 54 49 43 53  20 26 20 43 59 42 45 52   ROBOTICS & CYBER"),
    ("faint", "0109 7C40  4E 45 54 49 43 53 00 00  53 54 49 4C 4C 20 4C 45   NETICS..STILL LE"),
    ("faint", "0109 7C50  41 52 4E 49 4E 47 2E 20  41 4C 57 41 59 53 2E 00   ARNING. ALWAYS.."),
    ("faint", "0109"),
    ("mid", "010A SEQ"),
    ("dim", "010A   1. FIND SOMETHING THAT IS SLIGHTLY ANNOYING"),
    ("dim", "010A   2. OVERBUILD A FIX FOR IT"),
    ("dim", "010A   3. GIVE IT A TERMINAL UI IT DID NOT NEED"),
    ("dim", "010A   4. PUSH TO MAIN. GOTO 1"),
    ("faint", "010A"),
    ("mid", "010B PRESS <F2> TO ENTER SETUP -- PRESS <ANY> TO CONTINUE"),
    ("dim", "010B BOOTING FROM /dev/curiosity ..."),
    ("bright", "010B _"),
]

ECHO_LINES = [
    "ECHO [ COFFEE IN, FIRMWARE OUT. ]",
    "ECHO [ IF IT COMPILES, SHIP IT. IF IT MOVES, MEASURE IT. ]",
    "ECHO [ THE DEMO WORKED YESTERDAY. THAT COUNTS. ]",
    "ECHO [ NEVER TRUST A SENSOR THAT AGREES WITH YOU. ]",
    "ECHO [ ONE MORE COMMIT AND THEN BED. LINE 1 OF 400. ]",
    "ECHO [ IT IS NOT A BUG, IT IS UNDOCUMENTED FEEDBACK. ]",
]

BANK1 = ["ROBOTICS", "EMBEDDED", "CONTROL", "AUTOMATION"]
BANK2 = ["C", "PYTHON", "MATLAB", "JAVA"]


# --------------------------------------------------------------------------- #
# hero
# --------------------------------------------------------------------------- #

def render_hero(theme, out_path, frames=16, duration=110):
    W, H = 1800, 1508
    img = Image.new("RGB", (W, H), theme["bg"])
    d = ImageDraw.Draw(img)

    M = 34
    f_head = mono(19, True)
    f_menu = mono(27, True)
    f_tiny = mono(13)
    f_small = mono(16)

    # ---- top status line -------------------------------------------------- #
    y = 26
    cells = [
        (M, "GREENYBEANY (TM)"),
        (M + 300, "COPYRIGHT GREENYBEANY(C) 2026"),
        (M + 760, "ROBOTICS"),
        (M + 1010, "VER V2.06"),
        (M + 1310, "PORT......3"),
    ]
    for x, s in cells:
        text(d, (x, y), s, f_head, theme["mid"], tracking=2.4)

    # ---- menu bar --------------------------------------------------------- #
    bar = (M, 66, W - M, 124)
    frame(d, bar, theme["rule"], radius=10)
    items = ["SUMMARY", "PROJECTS", "STACK", "BOOT", "MORE+"]
    inner = (W - 2 * M) - 96
    step = inner / (len(items) - 1)
    for i, s in enumerate(items):
        text(d, (M + 48 + i * step, 82), s, f_menu, theme["bright"],
             tracking=2.0, align="center" if 0 < i < len(items) - 1 else
             ("left" if i == 0 else "right"))

    # ---- main frame ------------------------------------------------------- #
    top = 146
    bot = 1118
    frame(d, (M, top, W - M, bot), theme["rule"])

    split = M + 862
    left = (M + 12, top + 12, split - 12, bot - 12)
    right = (split + 12, top + 12, W - M - 12, bot - 12)
    frame(d, left, theme["rule"])
    frame(d, right, theme["rule"])

    # ---- left panel: the log --------------------------------------------- #
    lx = left[0] + 16
    ly = left[1] + 14
    lh = 16
    cols = int((left[2] - left[0] - 34) / f_tiny.getlength("M"))

    lines = []
    for tone, s in LOG_HEAD:
        lines.append((tone if tone in theme else "dim", s))
    lines.append(("faint", ""))
    for s in wrap(LOG_BODY, cols - 5):
        lines.append(("faint", "0108 " + s))
    lines.extend(LOG_TAIL)

    caret = None
    for i, (tone, s) in enumerate(lines):
        yy = ly + i * lh
        if yy > left[3] - 16:
            break
        if s.endswith(" _"):
            s = s[:-1]                       # the caret is drawn per frame
            caret = (lx + f_tiny.getlength(s), yy)
        d.text((lx, yy), s, font=f_tiny, fill=theme[tone])

    # display type over the log, the way the reference stacks it; it is the
    # one element re-rolled on every frame, so the slices never settle
    glitch_at = (lx - 10, ly + 27 * lh - 10)

    # ---- right panel: portrait ------------------------------------------- #
    portrait(d, (right[0] + 18, right[1] + 16, right[2] - 18, right[3] - 16),
             theme, cw=9, ch=12, gamma=0.92)

    # ---- bottom left: the batch file ------------------------------------- #
    by = bot + 26
    bx = M + 6
    batch = [
        ("mid", "ECHO OFF"),
        ("dim", "TITLE  GREENYBEANY #0416"),
        ("dim", "MODE CON: COLS=180 LINES=78"),
        ("dim", "CLS"),
        ("faint", ""),
        ("mid", ":: BIOS BOOT SCREEN"),
        ("faint", "ECHO"),
    ]
    for i, (tone, s) in enumerate(batch):
        d.text((bx, by + i * 19), s, font=f_small, fill=theme[tone])

    ey = by + len(batch) * 19 + 4
    for i, s in enumerate(ECHO_LINES):
        d.text((bx, ey + i * 19), s, font=f_small, fill=theme["dim"])

    # ---- bottom middle: memory banks ------------------------------------- #
    # labels are static; the cells themselves are refreshed per frame so one
    # of them can drop out like a bad module
    f_bank_l = mono(17, True)
    f_bank = mono(21, True)
    bank_x = M + 566
    cell_w = 166
    banks = []
    for row, (label, vals) in enumerate([("BANK 1", BANK1), ("BANK 2", BANK2)]):
        yy = by + 12 + row * 62
        text(d, (bank_x, yy + 4), label, f_bank_l, theme["mid"], tracking=2)
        for c, v in enumerate(vals):
            banks.append((bank_x + 118 + c * cell_w, yy, v))

    # ---- bottom right: the little config box ----------------------------- #
    box = (W - M - 366, by + 4, W - M - 6, by + 128)
    frame(d, box, theme["rule"])
    f_nano = mono(11)
    nano = [
        "CPU 0 .... BEANY CORE @ 4.1 GHZ",
        "IDE 0 .... /dev/quest    ONLINE",
        "IDE 1 .... /dev/box      ONLINE",
        "IDE 2 .... /dev/drive    ONLINE",
        "NET 0 .... github.com/" + USER,
        "LOC 0 .... BRATISLAVA, SK  UTC+1",
        "",
        "EXIT ..... SAVE & WRITE MAIN",
    ]
    for i, s in enumerate(nano):
        d.text((box[0] + 12, box[1] + 10 + i * 14), s,
               font=f_nano, fill=theme["dim"])

    # ---- giant wordmark --------------------------------------------------- #
    wm_font = mono(96, True)
    wm = "GREENYBEANY"
    wx = W - M - 44
    wy = H - 176
    text(d, (wx + 4, wy + 4), wm, wm_font, theme["wordmark"], 14, align="right")
    text(d, (wx, wy), wm, wm_font, theme["wordmark_edge"], 14, align="right")
    text(d, (W - M - 6, H - 46), "(C)", mono(18, True), theme["wordmark_edge"],
         align="right")

    # ---- frames ----------------------------------------------------------- #
    glitch_font = mono(88, True)
    band = 150
    travel = (right[3] - right[1]) + band

    out = []
    for t in range(frames):
        f = img.copy()
        fd = ImageDraw.Draw(f)

        # refresh band crawling down the portrait
        sweep(f, (right[0] + 1, right[1] + 1, right[2], right[3]),
              right[1] - band + travel * t / frames, band, theme, 0.5)

        g = glitch_text("HELLO WORLD", glitch_font, 6, theme["bright"],
                        theme["rule"], seed=40 + t)
        f.paste(g, (glitch_at[0] + (t % 3) - 1, glitch_at[1]), g)

        for i, (bxx, byy, v) in enumerate(banks):
            dead = (t + i * 5) % 37 < 2
            text(fd, (bxx, byy), v, f_bank,
                 theme["faint"] if dead else theme["bright"], tracking=1.5)

        if caret and t % frames < frames * 0.55:
            fd.text(caret, "_", font=f_tiny, fill=theme["bright"])

        out.append(f)

    return save_gif(out, out_path, duration)


# --------------------------------------------------------------------------- #
# project cards
# --------------------------------------------------------------------------- #

PROJECTS = [
    {
        "slug": "questmaker",
        "index": "01",
        "name": "QUEST MAKER",
        "full": "BEANY'S DISCORD QUEST MAKER",
        "url": "https://github.com/Greenythebeany/Beany-s-Discord-Quest-Maker",
        "desc": "TUI app that clears Discord's Orb quests for games you do not own. "
                "Spoofs the play session, watches the progress endpoint, claims the reward.",
        "specs": [("LANG", "PYTHON"), ("TYPE", "TUI"), ("IFACE", "DISCORD API")],
        "art": [
            "....########....",
            "...##......##...",
            "..##..####..##..",
            ".##..##..##..##.",
            ".##..##..##..##.",
            ".##..######..##.",
            "..##..####..##..",
            "...##......##...",
            "....########....",
            "......####......",
            ".......##.......",
            "......####......",
        ],
    },
    {
        "slug": "beanybox",
        "index": "02",
        "name": "BEANYBOX",
        "full": "BEANYBOX",
        "url": "https://github.com/Greenythebeany/BeanyBox",
        "desc": "Terminal-styled desktop mail client for Gmail. Threads, labels and "
                "search rendered as a green-on-black console instead of another web view.",
        "specs": [("LANG", "PYTHON"), ("TYPE", "DESKTOP"), ("IFACE", "GMAIL API")],
        "art": [
            "################",
            "##............##",
            "##.##......##.##",
            "##...##..##...##",
            "##.....##.....##",
            "##...##..##...##",
            "##.##......##.##",
            "##............##",
            "################",
            "..##########....",
            "....######......",
            "......##........",
        ],
    },
    {
        "slug": "beanydrive",
        "index": "03",
        "name": "BEANYDRIVE",
        "full": "BEANYDRIVE",
        "url": "https://github.com/Greenythebeany/BeanyDrive",
        "desc": "Turns a Discord channel into a personal cloud drive. Chunks files, "
                "uploads them as attachments, rebuilds them on the way back down.",
        "specs": [("LANG", "PYTHON"), ("TYPE", "STORAGE"), ("IFACE", "DISCORD API")],
        "art": [
            "..############..",
            ".##..........##.",
            "##..########..##",
            "##..##....##..##",
            "##..##....##..##",
            "##..########..##",
            "##............##",
            "##..##########..",
            ".##..........##.",
            "..############..",
            "....##....##....",
            "..####....####..",
        ],
    },
]


def render_card(p, theme, out_path, frames=14, duration=120):
    W, H = 1800, 372
    img = Image.new("RGB", (W, H), theme["bg"])
    d = ImageDraw.Draw(img)
    M = 34

    f_head = mono(19, True)
    f_small = mono(17)
    f_spec = mono(18, True)
    f_tiny = mono(13)

    # header strip
    text(d, (M, 20), ">> MODULE " + p["index"] + "/03", f_head,
         theme["mid"], tracking=2.4)
    text(d, (W / 2, 20), p["full"], f_head, theme["mid"], tracking=2.4,
         align="center")
    text(d, (W - M, 20), "STATUS: ONLINE", f_head, theme["bright"],
         tracking=2.4, align="right")

    top, bot = 58, H - 26
    frame(d, (M, top, W - M, bot), theme["rule"])

    # ghost index, layered under the copy the way the hero wordmark is
    text(d, (W - M - 34, top + 26), p["index"], mono(150, True),
         theme["wordmark"], tracking=8, align="right")

    # left cell: the block glyph, drawn as rects so the pixels stay square
    cell = (M + 12, top + 12, M + 12 + (bot - top - 24), bot - 12)
    frame(d, cell, theme["rule"])
    art = p["art"]
    aw, ah = len(art[0]), len(art)
    step = int(min((cell[2] - cell[0]) * 0.82 / aw,
                   (cell[3] - cell[1]) * 0.82 / ah))
    ax = cell[0] + ((cell[2] - cell[0]) - aw * step) / 2
    ay = cell[1] + ((cell[3] - cell[1]) - ah * step) / 2
    for j, row in enumerate(art):
        for i, ch in enumerate(row):
            x, y = ax + i * step, ay + j * step
            if ch == "#":
                d.rectangle([x, y, x + step - 2, y + step - 2],
                            fill=theme["bright"])
            else:
                d.rectangle([x + step / 2 - 1, y + step / 2 - 1,
                             x + step / 2, y + step / 2], fill=theme["faint"])

    # title -- re-rolled per frame
    tx = cell[2] + 42
    glitch_at = (tx - 18, top + 16)

    ty = top + 104
    for i, line in enumerate(wrap(p["desc"], 88)):
        d.text((tx, ty + i * 25), line, font=f_small, fill=theme["dim"])

    sy = ty + 2 * 25 + 26
    for i, (k, v) in enumerate(p["specs"]):
        x = tx + i * 286
        text(d, (x, sy + 2), k + " ....", f_tiny, theme["faint"], tracking=1)
        text(d, (x + 92, sy), v, f_spec, theme["mid"], tracking=1.5)

    text(d, (W - M - 26, bot - 70), p["url"].replace("https://", ""),
         f_tiny, theme["faint"], tracking=1, align="right")

    # ---- frames ----------------------------------------------------------- #
    glitch_font = mono(58, True)
    f_press = mono(20, True)
    seed0 = sum(map(ord, p["slug"]))
    band = 90
    travel = (cell[3] - cell[1]) + band

    out = []
    for t in range(frames):
        f = img.copy()
        fd = ImageDraw.Draw(f)

        sweep(f, (cell[0] + 1, cell[1] + 1, cell[2], cell[3]),
              cell[1] - band + travel * t / frames, band, theme, 0.45)

        g = glitch_text(p["name"], glitch_font, 5, theme["bright"],
                        theme["rule"], seed=seed0 + t)
        f.paste(g, (glitch_at[0] + (t % 3) - 1, glitch_at[1]), g)

        # the call to action pulses rather than hard-blinks
        phase = abs((t / frames) * 2 - 1)
        text(fd, (W - M - 26, bot - 44), "PRESS <ENTER> TO OPEN >>", f_press,
             mix(theme["rule"], theme["hot"], phase), tracking=2, align="right")

        out.append(f)

    return save_gif(out, out_path, duration)


# --------------------------------------------------------------------------- #
# detected devices table
# --------------------------------------------------------------------------- #

STACK = [
    ("CH 0 MASTER", "C / C++", "EMBEDDED", "OK"),
    ("CH 0 SLAVE", "PYTHON", "TOOLING", "OK"),
    ("CH 1 MASTER", "JAVA", "COURSEWORK", "OK"),
    ("CH 1 SLAVE", "JAVASCRIPT", "WEB", "OK"),
    ("CH 2 MASTER", "MATLAB", "MODELLING", "OK"),
    ("CH 2 SLAVE", "SIMULINK", "SIMULATION", "OK"),
    ("CH 3 MASTER", "ARDUINO", "HARDWARE", "OK"),
    ("CH 3 SLAVE", "GIT / GITHUB", "VERSIONING", "OK"),
    ("USB 0", "LINUX (FEDORA / UBUNTU)", "DAILY DRIVER", "OK"),
    ("USB 1", "VS CODE / CLION / IDEA", "EDITORS", "OK"),
]


def render_stack(theme, out_path, duration=150):
    W = 1800
    H = 120 + len(STACK) * 30 + 92
    img = Image.new("RGB", (W, H), theme["bg"])
    d = ImageDraw.Draw(img)
    M = 34

    f_head = mono(19, True)
    f_row = mono(19)
    f_rowb = mono(19, True)

    text(d, (M, 22), "DETECTING IDE DEVICES ...", f_head, theme["mid"],
         tracking=2.4)
    text(d, (W - M, 22), "10 DEVICES FOUND", f_head, theme["bright"],
         tracking=2.4, align="right")

    top = 62
    bot = H - 30
    frame(d, (M, top, W - M, bot), theme["rule"])

    cx = [M + 26, M + 300, M + 860, W - M - 26]
    hy = top + 18
    for label, x in zip(["CHANNEL", "DEVICE", "FUNCTION"], cx[:3]):
        text(d, (x, hy), label, mono(15, True), theme["faint"], tracking=2)
    text(d, (cx[3], hy), "MODE", mono(15, True), theme["faint"], tracking=2,
         align="right")
    d.line([(M + 14, hy + 26), (W - M - 14, hy + 26)], fill=theme["rule"])

    for i, (chan, dev, fn, st) in enumerate(STACK):
        y = hy + 42 + i * 30
        d.text((cx[0], y), chan, font=f_row, fill=theme["dim"])
        d.text((cx[1], y), dev, font=f_rowb, fill=theme["bright"])
        d.text((cx[2], y), fn, font=f_row, fill=theme["mid"])

    y = hy + 42 + len(STACK) * 30 + 14
    d.line([(M + 14, y), (W - M - 14, y)], fill=theme["rule"])
    text(d, (cx[0], y + 14), "ALL DEVICES INITIALISED -- PRESS <ANY KEY>",
         mono(16), theme["faint"], tracking=1)

    # ---- frames: the probe walks the table, one device at a time ---------- #
    out = []
    for t in range(len(STACK) + 2):
        f = img.copy()
        fd = ImageDraw.Draw(f)
        for i, (chan, dev, fn, st) in enumerate(STACK):
            ry = hy + 42 + i * 30
            if i > t:
                text(fd, (cx[3], ry), "....", f_rowb, theme["faint"],
                     align="right")
            elif i == t:
                fd.rectangle([M + 14, ry - 4, W - M - 14, ry + 26],
                             fill=theme["faint"])
                fd.text((cx[0], ry), chan, font=f_row, fill=theme["hot"])
                fd.text((cx[1], ry), dev, font=f_rowb, fill=theme["hot"])
                fd.text((cx[2], ry), fn, font=f_row, fill=theme["hot"])
                text(fd, (cx[3], ry), "????", f_rowb, theme["hot"],
                     align="right")
            else:
                text(fd, (cx[3], ry), st, f_rowb, theme["hot"], align="right")
        out.append(f)

    return save_gif(out, out_path, duration)


# --------------------------------------------------------------------------- #
# footer
# --------------------------------------------------------------------------- #

def render_footer(theme, out_path, duration=420):
    W, H = 1800, 178
    img = Image.new("RGB", (W, H), theme["bg"])
    d = ImageDraw.Draw(img)
    M = 34

    f_prompt = mono(34, True)
    prompt = "C:\\USERS\\GREENYBEANY> "

    frame(d, (M, 16, W - M, 124), theme["rule"], radius=10)
    # the caret is part of the line's width, so the prompt does not shift
    # when it blinks off
    full = width_of(prompt + "_", f_prompt, 3)
    px = W / 2 - full / 2
    text(d, (px, 36), prompt, f_prompt, theme["bright"], tracking=3)
    caret = (px + width_of(prompt, f_prompt, 3) + 3, 36)

    text(d, (W / 2, 84), "THANKS FOR STOPPING BY  --  SYSTEM HALTED",
         mono(18), theme["dim"], tracking=3, align="center")
    text(d, (W / 2, H - 34), "github.com/" + USER, mono(15), theme["faint"],
         tracking=2, align="center")

    out = []
    for t in range(2):
        f = img.copy()
        if t == 0:
            ImageDraw.Draw(f).text(caret, "_", font=f_prompt,
                                   fill=theme["bright"])
        out.append(f)

    return save_gif(out, out_path, duration)


# --------------------------------------------------------------------------- #
# snake contribution graph, recoloured to match
# --------------------------------------------------------------------------- #

# --cs is the snake, --c0..--c4 the contribution levels, --ce an eaten cell,
# --cb the cell stroke. snk emits no --c0 in its dark block, which would leave
# pale cells on a dark canvas, so every variant declares the full set.
# --ce sits a hair off the page background rather than exactly on it, so an
# empty day still reads as a cell instead of vanishing.
SNAKE = {
    "dark": ("--cb:#7cf5d52e;--cs:#7cf5d5;--ce:#11201d;--c0:#11201d;"
             "--c1:#0e3a32;--c2:#17715f;--c3:#2fa98f;--c4:#7cf5d5"),
    "light": ("--cb:#0b2e2824;--cs:#0c3c33;--ce:#f4f8f6;--c0:#f4f8f6;"
              "--c1:#cfe8df;--c2:#8ccbb7;--c3:#3f9c84;--c4:#0c3c33"),
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
