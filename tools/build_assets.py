"""Renders every image used by the profile README.

Everything is drawn in the Nothing OS idiom: black widget tiles floating on
the page, white dot-matrix type lit on an LED grid, and exactly one red accent
per image.

    python tools/build_assets.py
"""

import math
import os
import random
import re

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
SANS = os.path.join(FONTS, "bahnschrift.ttf")
ICONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

USER = "Greenythebeany"

# canvases match GitHub's page background so the tiles float on it
DARK = {
    "bg": (13, 17, 23),
    "tile": (0, 0, 0),
    "edge": (38, 38, 38),
    "inset": (17, 17, 17),
    "off": (36, 36, 36),
    "faint": (84, 84, 84),
    "dim": (150, 150, 150),
    "text": (242, 242, 242),
    "accent": (215, 25, 33),
}

LIGHT = {
    "bg": (255, 255, 255),
    "tile": (242, 242, 242),
    "edge": (226, 226, 226),
    "inset": (231, 231, 231),
    "off": (214, 214, 214),
    "faint": (168, 168, 168),
    "dim": (100, 100, 100),
    "text": (14, 14, 14),
    "accent": (215, 25, 33),
}


# --------------------------------------------------------------------------- #
# low level helpers
# --------------------------------------------------------------------------- #

_font_cache = {}


def sans(size, weight="Regular"):
    key = (size, weight)
    if key not in _font_cache:
        f = ImageFont.truetype(SANS, size)
        f.set_variation_by_name(weight)
        _font_cache[key] = f
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


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _rr_mask(w, h, r, s=4):
    m = Image.new("L", (w * s, h * s), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * s - 1, h * s - 1],
                                        radius=r * s, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def tile(img, box, theme, fill="tile", radius=28, edge=True):
    """A widget tile. Drawn supersampled: PIL's own rounded_rectangle has no
    antialiasing and the corners would stair-step on a 2x display."""
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    w, h = x1 - x0, y1 - y0
    if edge:
        img.paste(theme["edge"], (x0, y0), _rr_mask(w, h, radius))
        img.paste(theme[fill], (x0 + 1, y0 + 1),
                  _rr_mask(w - 2, h - 2, radius - 1))
    else:
        img.paste(theme[fill], (x0, y0), _rr_mask(w, h, radius))


_dot_cache = {}


def dot(img, xy, r, color):
    """One antialiased LED, pasted from a cached sprite per radius."""
    key = max(1, int(round(r * 4)))
    m = _dot_cache.get(key)
    if m is None:
        rr, s = key / 4.0, 4
        size = int(math.ceil(rr * 2)) + 2
        big = Image.new("L", (size * s, size * s), 0)
        c = size * s / 2
        ImageDraw.Draw(big).ellipse([c - rr * s, c - rr * s,
                                     c + rr * s, c + rr * s], fill=255)
        m = _dot_cache[key] = big.resize((size, size), Image.LANCZOS)
    size = m.size[0]
    img.paste(color, (int(round(xy[0] - size / 2)),
                      int(round(xy[1] - size / 2))), m)


def save_gif(frames, path, duration):
    """One shared palette across every frame, so the encoder can ship each
    frame as just the rectangle that actually changed."""
    base = frames[0].convert("P", palette=Image.ADAPTIVE, colors=200)
    qs = [f.quantize(palette=base, dither=Image.NONE) for f in frames]
    qs[0].save(path, save_all=True, append_images=qs[1:], loop=0,
               duration=duration, disposal=1, optimize=False)
    return path


# --------------------------------------------------------------------------- #
# dot-matrix type: a 5x7 LED face, narrow glyphs for punctuation
# --------------------------------------------------------------------------- #

GLYPHS = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["###", ".#.", ".#.", ".#.", ".#.", ".#.", "###"],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
    "0": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
    " ": ["...", "...", "...", "...", "...", "...", "..."],
    ":": [".", "#", ".", ".", ".", "#", "."],
    ".": [".", ".", ".", ".", ".", ".", "#"],
    "!": ["#", "#", "#", "#", "#", ".", "#"],
    "'": ["#", "#", ".", ".", ".", ".", "."],
    "-": ["....", "....", "....", "####", "....", "....", "...."],
    "/": ["....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."],
    ">": ["#...", ".#..", "..#.", "...#", "..#.", ".#..", "#..."],
    "&": [".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"],
    "%": ["##..#", "##..#", "...#.", "..#..", ".#...", "#..##", "#..##"],
}


def dot_cols(s):
    return sum(len(GLYPHS[c][0]) for c in s) + max(0, len(s) - 1)


def dot_text(img, xy, s, pitch, color, off=None, align="left", r=None,
             off_r=None):
    """Light a string on the LED grid. With `off`, the unlit cells of each
    character cell are drawn too, so the word sits on a visible matrix."""
    r = r or pitch * 0.36
    off_r = off_r or pitch * 0.2
    w = dot_cols(s) * pitch
    x, y = xy
    if align == "right":
        x -= w
    elif align == "center":
        x -= w / 2
    for k, ch in enumerate(s):
        g = GLYPHS[ch]
        gw = len(g[0])
        for j, row in enumerate(g):
            for i, c in enumerate(row):
                if c == "#" or off:
                    lit = c == "#"
                    dot(img, (x + (i + 0.5) * pitch, y + (j + 0.5) * pitch),
                        r if lit else off_r, color if lit else off)
            if off and k < len(s) - 1:
                dot(img, (x + (gw + 0.5) * pitch, y + (j + 0.5) * pitch),
                    off_r, off)
        x += (gw + 1) * pitch
    return w


class Grid:
    """An LED matrix filling a box. Shapes are rasterised onto its cells, so
    lines and curves come out as the stepped dot runs of a real panel."""

    def __init__(self, box, pitch):
        x0, y0, x1, y1 = box
        self.p = pitch
        self.cols = int((x1 - x0) // pitch)
        self.rows = int((y1 - y0) // pitch)
        self.ox = x0 + ((x1 - x0) - self.cols * pitch) / 2
        self.oy = y0 + ((y1 - y0) - self.rows * pitch) / 2

    def at(self, i, j):
        return (self.ox + (i + 0.5) * self.p, self.oy + (j + 0.5) * self.p)

    def cell(self, x, y):
        return (int((x - self.ox) // self.p), int((y - self.oy) // self.p))

    def inside(self, c):
        return 0 <= c[0] < self.cols and 0 <= c[1] < self.rows

    def blank(self, img, color, r=None):
        r = r or self.p * 0.3
        for j in range(self.rows):
            for i in range(self.cols):
                dot(img, self.at(i, j), r, color)

    def line(self, a, b):
        n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / (self.p / 3)))
        out = []
        for k in range(n + 1):
            t = k / n
            c = self.cell(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            if self.inside(c) and c not in out:
                out.append(c)
        return out

    def light(self, img, cells, color, r=None):
        r = r or self.p * 0.36
        for c in cells:
            if self.inside(c):
                dot(img, self.at(*c), r, color)


def label(d, xy, s, theme, tone="dim", size=16, align="left"):
    return text(d, xy, s, sans(size, "SemiBold"), theme[tone], tracking=2.2,
                align=align)


# --------------------------------------------------------------------------- #
# shared widgets
# --------------------------------------------------------------------------- #

def arm_pose(base, links, angles):
    """Forward kinematics of a planar serial arm; angles are relative, in
    degrees, measured from the previous link (the first from +x)."""
    pts = [base]
    a = 0.0
    for L, th in zip(links, angles):
        a += math.radians(th)
        x, y = pts[-1]
        pts.append((x + L * math.cos(a), y - L * math.sin(a)))
    return pts


def draw_arm(img, grid, pts, theme, target=None):
    for a, b in zip(pts, pts[1:]):
        grid.light(img, grid.line(a, b), theme["text"])
    for p in pts[:-1]:
        dot(img, grid.at(*grid.cell(*p)), grid.p * 0.62, theme["text"])
    if target:
        dot(img, grid.at(*grid.cell(*target)), grid.p * 0.55,
            theme["accent"])


def ease(t):
    return (1 - math.cos(math.pi * 2 * t)) / 2


# --------------------------------------------------------------------------- #
# hero
# --------------------------------------------------------------------------- #

ABOUT = (
    "I build things that move: motors, servos, state machines and the "
    "occasional terminal app that refuses to act like one. C when it has to "
    "be fast, Python when it has to exist by tomorrow, MATLAB and Simulink "
    "when it has to be proven before it is soldered."
)

SUBSYSTEMS = [
    ("EMBEDDED SYSTEMS", True),
    ("CONTROL THEORY", True),
    ("INDUSTRIAL AUTOMATION", True),
    ("SIMULATION", True),
    ("ROBOTICS", True),
    ("SLEEP", False),
]


def render_hero(theme, out_path, frames=16, duration=110):
    W, H = 1800, 1076
    img = Image.new("RGB", (W, H), theme["bg"])
    d = ImageDraw.Draw(img)
    M = 34

    # ---- top strip + wordmark -------------------------------------------- #
    label(d, (M + 4, 30), "@" + USER.upper(), theme)
    label(d, (W - M - 4, 30), "BRATISLAVA, SK  /  UTC+1:00", theme,
          align="right")

    wm = "GREENYBEANY"
    pitch = (W - 2 * M) / dot_cols(wm)
    dot_text(img, (M, 72), wm, pitch, theme["text"], off=theme["off"],
             r=pitch * 0.36, off_r=pitch * 0.16)

    sub_y = 72 + 7 * pitch + 30
    text(d, (M + 4, sub_y), "ROBOTICS & CYBERNETICS STUDENT  /  FEI STU",
         sans(24, "SemiBold"), theme["text"], tracking=2.5)
    text(d, (W - M - 4, sub_y), "I BUILD THINGS THAT MOVE.",
         sans(24), theme["dim"], tracking=2.5, align="right")

    # ---- tile grid -------------------------------------------------------- #
    g = 16
    r1 = (sub_y + 62, sub_y + 62 + 310)
    r2 = (r1[1] + g, r1[1] + g + 310)

    def cols(widths, row):
        x, out = M, []
        for w in widths:
            out.append((x, row[0], x + w, row[1]))
            x += w + g
        return out

    t_clock, t_about, t_sys = cols([560, 560, 580], r1)
    t_arm, t_ring, t_plot = cols([700, 400, 600], r2)
    for b in (t_clock, t_about, t_sys, t_arm, t_ring, t_plot):
        tile(img, b, theme)
    pad = 34

    # clock
    label(d, (t_clock[0] + pad, t_clock[1] + pad), "LOCAL TIME", theme)
    cp = 16
    clock = "04:04"
    cx = (t_clock[0] + t_clock[2]) / 2 - dot_cols(clock) * cp / 2
    cy = t_clock[1] + 110
    dot_text(img, (cx, cy), clock, cp, theme["text"], off=theme["off"])
    colon_x = cx + (dot_cols(clock[:2]) + 1) * cp
    label(d, (t_clock[0] + pad, t_clock[3] - pad - 18), "TIME NOT FOUND", theme, "faint")
    label(d, (t_clock[2] - pad, t_clock[3] - pad - 18), "UTC+1:00", theme,
          "faint", align="right")

    # about
    label(d, (t_about[0] + pad, t_about[1] + pad), "ABOUT", theme)
    f_about = sans(23)
    for i, line in enumerate(wrap(ABOUT, f_about,
                                  t_about[2] - t_about[0] - 2 * pad)):
        d.text((t_about[0] + pad, t_about[1] + 82 + i * 33), line,
               font=f_about, fill=theme["text"])

    # subsystems
    label(d, (t_sys[0] + pad, t_sys[1] + pad), "SUBSYSTEMS", theme)
    f_sys = sans(21, "SemiBold")
    for i, (name, on) in enumerate(SUBSYSTEMS):
        y = t_sys[1] + 80 + i * 36
        text(d, (t_sys[0] + pad, y), name, f_sys,
             theme["text"] if on else theme["faint"], tracking=1.5)
        text(d, (t_sys[2] - pad - 30, y + 2), "ON" if on else "OFF",
             sans(16, "SemiBold"), theme["dim"] if on else theme["faint"],
             tracking=2, align="right")
        dot(img, (t_sys[2] - pad - 6, y + 12), 6,
            theme["text"] if on else theme["off"])

    # arm: labels are static, the arm itself is redrawn per frame
    label(d, (t_arm[0] + pad, t_arm[1] + pad), "ARM  /  3 DOF", theme)
    arm_grid = Grid((t_arm[0] + 24, t_arm[1] + 70, t_arm[2] - 24,
                     t_arm[3] - 24), 11)
    arm_bg = img.crop(t_arm)
    arm_grid.blank(img, theme["off"], r=2.2)
    base = (t_arm[0] + 200, t_arm[3] - 48)
    for k in range(-4, 5):
        dot(img, arm_grid.at(*arm_grid.cell(base[0] + k * 11, base[1] + 14)),
            arm_grid.p * 0.36, theme["dim"])
    links = (150, 140, 66)
    rest = (78, -52, -34)
    reach = (30, -10, -52)
    target = arm_pose(base, links, reach)[-1]

    # caffeine ring: the one red element on the page
    label(d, (t_ring[0] + pad, t_ring[1] + pad), "CAFFEINE", theme)
    rc = ((t_ring[0] + t_ring[2]) / 2, (t_ring[1] + t_ring[3]) / 2 + 18)
    R, N, level = 96, 56, 0.72
    lit = int(N * level)
    ring = []
    for k in range(N):
        a = -math.pi / 2 + 2 * math.pi * k / N
        ring.append((rc[0] + R * math.cos(a), rc[1] + R * math.sin(a)))
        dot(img, ring[-1], 5, theme["accent"] if k < lit else theme["off"])
    dot_text(img, (rc[0] - 10, rc[1] - 36), "72", 8, theme["text"],
             align="center")
    text(d, (rc[0] + 38, rc[1] - 4), "%", sans(22, "SemiBold"), theme["dim"])
    text(d, (rc[0], rc[1] + 34), "SATURATING", sans(13, "SemiBold"),
         theme["faint"], tracking=2, align="center")

    # step response
    label(d, (t_plot[0] + pad, t_plot[1] + pad), "STEP RESPONSE", theme)
    label(d, (t_plot[2] - pad, t_plot[1] + pad), "Z 0.30  /  WN 4.0", theme,
          "faint", align="right")
    pg = Grid((t_plot[0] + 30, t_plot[1] + 76, t_plot[2] - 30,
               t_plot[3] - 30), 10)
    pg.blank(img, theme["off"], r=2.0)
    z, wn = 0.30, 4.0
    wd = wn * math.sqrt(1 - z * z)
    phi = math.acos(z)
    top_row, bot_row = 2, pg.rows - 2

    def y_row(v):
        return int(round(bot_row - (bot_row - top_row) * v / 1.45))

    set_row = y_row(1.0)
    pg.light(img, [(i, set_row) for i in range(0, pg.cols, 2)], theme["faint"],
             r=pg.p * 0.3)
    curve = []
    prev = None
    for i in range(pg.cols):
        t = 3.2 * i / (pg.cols - 1)
        v = 1 - math.exp(-z * wn * t) / math.sqrt(1 - z * z) * math.sin(
            wd * t + phi)
        row = y_row(v)
        col = []
        if prev is not None:
            step = 1 if row > prev else -1
            col = [(i, rr) for rr in range(prev + step, row, step)]
        curve.append(col + [(i, row)])
        prev = row

    # bottom strip
    label(d, (M + 4, H - 46), "GITHUB.COM/" + USER.upper(), theme, "faint")
    label(d, (W - M - 4, H - 46), "3 MODULES ONLINE", theme, "faint",
          align="right")

    # ---- frames ----------------------------------------------------------- #
    reveal = frames - 4
    out = []
    for t in range(frames):
        f = img.copy()
        fd = ImageDraw.Draw(f)

        if t % 8 >= 4:
            for rr in (1, 5):
                p = (colon_x + 0.5 * cp, cy + (rr + 0.5) * cp)
                dot(f, p, cp * 0.36 + 1, theme["tile"])
                dot(f, p, cp * 0.2, theme["off"])

        s = ease(t / frames)
        pose = [a + (b - a) * s for a, b in zip(rest, reach)]
        draw_arm(f, arm_grid, arm_pose(base, links, pose), theme, target)
        text(fd, (t_arm[2] - pad, t_arm[1] + pad),
             "  ".join("J%d %+04d" % (k + 1, round(a))
                       for k, a in enumerate(pose)),
             sans(16, "SemiBold"), theme["faint"], tracking=1.5,
             align="right")

        n = len(curve) if t >= reveal else int(len(curve) * (t + 1) / reveal)
        for i in range(n):
            pg.light(f, curve[i], theme["text"])

        head = ring[lit - 1]
        dot(f, head, 5 + (2 if t % 4 < 2 else 0), theme["accent"])

        out.append(f)

    return save_gif(out, out_path, duration)


# --------------------------------------------------------------------------- #
# project cards
# --------------------------------------------------------------------------- #

PROJECTS = [
    {
        "slug": "triptych",
        "index": "01",
        "name": "TRIPTYCH",
        "url": "https://github.com/Greenythebeany/triptych",
        "site": "https://triptych.greenybeany.dev/",
        "desc": "Free, open-source music app for your own Jellyfin server. Spotify, "
                "Apple Music or Nothing style, synced lyrics, offline downloads, "
                "stats and Wrapped.",
        "specs": ["JAVASCRIPT", "MUSIC", "JELLYFIN"],
        "widget": "eq",
    },
    {
        "slug": "beanyik",
        "index": "02",
        "name": "BEANYIK",
        "url": "https://github.com/Greenythebeany/BeanyIK",
        "site": "https://greenybeany.dev/BeanyIK/",
        "desc": "Drag and drop robot kinematics builder. DH parameters or custom "
                "matrices, forward and inverse kinematics solved live as the arm "
                "is assembled.",
        "specs": ["JAVASCRIPT", "ELECTRON", "DH / IK"],
        "widget": "arm",
    },
    {
        "slug": "beanydrive",
        "index": "03",
        "name": "BEANYDRIVE",
        "url": "https://github.com/Greenythebeany/BeanyDrive",
        "desc": "Turns a Discord channel into a personal cloud drive. Chunks files, "
                "uploads them as attachments, rebuilds them on the way back down.",
        "specs": ["JAVASCRIPT", "STORAGE", "DISCORD API"],
        "widget": "drive",
    },
]


def card_widget(kind, img, d, box, theme, t, frames, seed):
    x0, y0, x1, y1 = box
    pad = 22
    if kind == "eq":
        label(d, (x0 + pad, y0 + pad - 2), "NOW PLAYING", theme, size=14)
        grid = Grid((x0 + 18, y0 + 52, x1 - 18, y1 - 54), 12)
        grid.blank(img, theme["off"], r=2.4)
        rng = random.Random(seed)
        ph = [rng.uniform(0, 2 * math.pi) for _ in range(grid.cols)]
        for i in range(grid.cols):
            if i % 2:
                continue
            a = 2 * math.pi * t / frames
            v = 0.5 + 0.28 * math.sin(a * 2 + ph[i]) + 0.18 * math.sin(
                a * 3 + ph[i] * 1.7)
            hgt = max(1, int(round(v * grid.rows)))
            grid.light(img, [(i, grid.rows - 1 - k) for k in range(hgt)],
                       theme["text"])
        ly = y1 - 32
        lx0, lx1 = x0 + 24, x1 - 24
        n = 30
        head = int(n * (0.2 + 0.6 * t / frames))
        for k in range(n + 1):
            dot(img, (lx0 + (lx1 - lx0) * k / n, ly), 2.6,
                theme["dim"] if k < head else theme["off"])
        dot(img, (lx0 + (lx1 - lx0) * head / n, ly), 6.5, theme["accent"])

    elif kind == "arm":
        label(d, (x0 + pad, y0 + pad - 2), "SOLVING IK", theme, size=14)
        grid = Grid((x0 + 14, y0 + 48, x1 - 14, y1 - 14), 9)
        grid.blank(img, theme["off"], r=1.8)
        base = (x0 + 98, y1 - 34)
        for k in range(-3, 4):
            dot(img, grid.at(*grid.cell(base[0] + k * 9, base[1] + 12)),
                grid.p * 0.36, theme["dim"])
        links = (82, 70, 34)
        rest, reach = (78, -48, -24), (30, -6, -58)
        target = arm_pose(base, links, reach)[-1]
        s = ease(t / frames)
        pose = [a + (b - a) * s for a, b in zip(rest, reach)]
        draw_arm(img, grid, arm_pose(base, links, pose), theme, target)

    elif kind == "drive":
        label(d, (x0 + pad, y0 + pad - 2), "UPLOADING", theme, size=14)
        cols, rows = 8, 4
        total = cols * rows
        done = int(total * (0.25 + 0.7 * t / frames))
        cw = (x1 - x0 - 2 * pad) / cols
        ch = 38
        gy = y0 + 62
        for k in range(total):
            cx = x0 + pad + (k % cols) * cw + cw / 2
            cy = gy + (k // cols) * ch + ch / 2
            col = (theme["text"] if k < done else
                   theme["accent"] if k == done else theme["off"])
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    dot(img, (cx + dx * 8, cy + dy * 8), 3.1, col)
        label(d, (x0 + pad, y1 - pad - 16),
              "CHUNK %02d / %02d" % (done + 1, total), theme, "faint",
              size=14)
        label(d, (x1 - pad, y1 - pad - 16), "8 MB EACH", theme, "faint",
              size=14, align="right")


def render_card(p, theme, out_path, frames=14, duration=120):
    W, H = 1800, 336
    img = Image.new("RGB", (W, H), theme["bg"])
    d = ImageDraw.Draw(img)
    M = 34

    card = (M, 16, W - M, H - 16)
    tile(img, card, theme, radius=32)

    # icon: the project's own app icon, as shipped in its repo
    side = card[3] - card[1] - 40
    icon = (card[0] + 20, card[1] + 20, card[0] + 20 + side, card[1] + 20 + side)
    art = Image.open(os.path.join(ICONS, p["slug"] + ".png")).convert("RGBA")
    art = art.resize((side, side), Image.LANCZOS)
    img.paste(art, icon[:2], art)

    tx = icon[2] + 40
    label(d, (tx, card[1] + 30), "MODULE %s / 03" % p["index"], theme)
    dot_text(img, (tx, card[1] + 64), p["name"], 8, theme["text"])
    f_desc = sans(21)
    for i, line in enumerate(wrap(p["desc"], f_desc, 720)):
        d.text((tx, card[1] + 144 + i * 29), line, font=f_desc,
               fill=theme["dim"])

    cx = tx
    f_chip = sans(15, "SemiBold")
    for s in p["specs"]:
        w = width_of(s, f_chip, 2) + 36
        tile(img, (cx, card[3] - 62, cx + w, card[3] - 26), theme,
             fill="tile", radius=18)
        text(d, (cx + 18, card[3] - 54), s, f_chip, theme["dim"], tracking=2)
        cx += w + 12

    wbox = (1124, card[1] + 20, 1448, card[3] - 20)
    tile(img, wbox, theme, fill="inset", radius=22, edge=False)

    dot_text(img, (card[2] - 40, card[1] + 34), p["index"], 20, theme["faint"],
             off=theme["off"], align="right", r=7)
    text(d, (card[2] - 70, card[3] - 56),
         "OPEN WEBSITE" if p.get("site") else "OPEN ON GITHUB",
         sans(19, "SemiBold"), theme["text"], tracking=2.4, align="right")
    dot_text(img, (card[2] - 40, card[3] - 56), ">", 3.4, theme["text"],
             align="right", r=1.5)

    out = []
    seed = sum(map(ord, p["slug"]))
    for t in range(frames):
        f = img.copy()
        card_widget(p["widget"], f, ImageDraw.Draw(f), wbox, theme, t, frames,
                    seed)
        out.append(f)

    return save_gif(out, out_path, duration)


# --------------------------------------------------------------------------- #
# stack list
# --------------------------------------------------------------------------- #

STACK = [
    ("C / C++", "EMBEDDED"),
    ("PYTHON", "TOOLING"),
    ("JAVA", "COURSEWORK"),
    ("JAVASCRIPT", "WEB / ELECTRON"),
    ("MATLAB", "MODELLING"),
    ("SIMULINK", "SIMULATION"),
    ("ARDUINO", "HARDWARE"),
    ("GIT / GITHUB", "VERSIONING"),
    ("LINUX (FEDORA / UBUNTU)", "DAILY DRIVER"),
    ("VS CODE / CLION / IDEA", "EDITORS"),
]


def render_stack(theme, out_path, duration=150):
    W = 1800
    rh = 46
    H = 176 + len(STACK) * rh + 40
    img = Image.new("RGB", (W, H), theme["bg"])
    d = ImageDraw.Draw(img)
    M = 34

    box = (M, 16, W - M, H - 16)
    tile(img, box, theme, radius=32)
    x0, x1 = box[0] + 40, box[2] - 40

    dot_text(img, (x0, box[1] + 36), "STACK", 7, theme["text"])
    label(d, (x1, box[1] + 50), "%d DEVICES" % len(STACK), theme,
          align="right")

    hy = box[1] + 112
    cx = [x0, x0 + 90, x0 + 760]
    for s, x in zip(["#", "DEVICE", "FUNCTION"], cx):
        label(d, (x, hy), s, theme, "faint", size=14)
    label(d, (x1, hy), "STATUS", theme, "faint", size=14, align="right")

    f_dev = sans(24, "SemiBold")
    f_fn = sans(20)
    y0 = hy + 36
    for i, (dev, fn) in enumerate(STACK):
        y = y0 + i * rh
        d.line([(x0, y), (x1, y)], fill=theme["edge"])
        text(d, (cx[0], y + 12), "%02d" % (i + 1), sans(18, "SemiBold"),
             theme["faint"], tracking=1.5)
        text(d, (cx[1], y + 9), dev, f_dev, theme["text"], tracking=1.5)
        text(d, (cx[2], y + 12), fn, f_fn, theme["dim"], tracking=1.5)

    out = []
    for t in range(len(STACK) + 2):
        f = img.copy()
        fd = ImageDraw.Draw(f)
        for i in range(len(STACK)):
            y = y0 + i * rh + rh / 2
            if i > t:
                state, col, tone = "", theme["off"], "faint"
            elif i == t:
                state, col, tone = "PROBING", theme["accent"], "dim"
            else:
                state, col, tone = "OK", theme["text"], "dim"
            label(fd, (x1 - 26, y - 9), state, theme, tone, size=15,
                  align="right")
            dot(f, (x1 - 6, y), 6, col)
        out.append(f)

    return save_gif(out, out_path, duration)


# --------------------------------------------------------------------------- #
# footer
# --------------------------------------------------------------------------- #

def render_footer(theme, out_path, duration=600):
    W, H = 1800, 196
    img = Image.new("RGB", (W, H), theme["bg"])
    d = ImageDraw.Draw(img)
    M = 34

    box = (M, 16, W - M, H - 16)
    tile(img, box, theme, radius=32)
    msg = "THANKS FOR STOPPING BY"
    p = 7
    w = dot_text(img, (W / 2 + 18, 52), msg, p, theme["text"], align="center")
    rec = (W / 2 + 18 - w / 2 - 34, 52 + 3.5 * p)
    label(d, (W / 2, 122), "GITHUB.COM/" + USER.upper(), theme, "faint",
          align="center")

    out = []
    for t in range(2):
        f = img.copy()
        dot(f, rec, 9, theme["accent"] if t == 0 else theme["off"])
        out.append(f)

    return save_gif(out, out_path, duration)


# --------------------------------------------------------------------------- #
# snake contribution graph, recoloured to match
# --------------------------------------------------------------------------- #

# --cs is the snake, --c0..--c4 the contribution levels, --ce an eaten cell,
# --cb the cell stroke. snk emits no --c0 in its dark block, which would leave
# pale cells on a dark canvas, so every variant declares the full set.
# --ce sits a hair off the page background rather than exactly on it, so an
# empty day still reads as a cell instead of vanishing. The snake is the red.
SNAKE = {
    "dark": ("--cb:#ffffff14;--cs:#d71921;--ce:#161b22;--c0:#161b22;"
             "--c1:#3a3a3a;--c2:#6e6e6e;--c3:#a8a8a8;--c4:#f2f2f2"),
    "light": ("--cb:#0000001a;--cs:#d71921;--ce:#f2f2f2;--c0:#f2f2f2;"
              "--c1:#d0d0d0;--c2:#9a9a9a;--c3:#5c5c5c;--c4:#0e0e0e"),
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
