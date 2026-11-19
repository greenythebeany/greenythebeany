"""Renders every image used by the profile README.

The look follows greenybeany.dev/me: warm near-black (or paper) ground,
Fraunces headings with one green italic phrase, JetBrains Mono labels,
Atkinson Hyperlegible Next for prose and hairline rules. The hero is a fastfetch run in a terminal window, with 緑 as the distro
logo; faint scanlines, a block cursor and the odd glitch frame add a little
cyberpunk on top.

    python tools/build_assets.py

Fonts live in tools/fonts (all OFL); the 緑 logo uses Yu Gothic.
"""

import math
import os
import random
import re

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONT_DIR = os.path.join(HERE, "fonts")
WINFONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

USER = "Greenythebeany"
SITE = "greenybeany.dev/me"

# the site's own tokens, dark and light
DARK = {
    "bg": (11, 11, 10),
    "ghost": (31, 30, 27),
    "faint": (42, 40, 36),
    "dim": (70, 66, 59),
    "mid": (153, 146, 138),
    "bright": (143, 214, 127),
    "hot": (185, 232, 173),
    "ink": (235, 228, 216),
    "ink_soft": (196, 188, 175),
    "rule": (42, 41, 37),
    "rule_strong": (107, 102, 93),
}

LIGHT = {
    "bg": (244, 241, 234),
    "ghost": (227, 222, 210),
    "faint": (217, 211, 198),
    "dim": (180, 173, 159),
    "mid": (98, 92, 83),
    "bright": (46, 107, 34),
    "hot": (31, 77, 22),
    "ink": (28, 27, 24),
    "ink_soft": (72, 68, 61),
    "rule": (214, 208, 195),
    "rule_strong": (128, 122, 110),
}

W = 1800
M = 64


# --------------------------------------------------------------------------- #
# type
# --------------------------------------------------------------------------- #

_font_cache = {}


def _font(file, size, axes=None):
    key = (file, size, tuple(axes or ()))
    if key not in _font_cache:
        f = ImageFont.truetype(os.path.join(FONT_DIR, file), size)
        if axes:
            f.set_variation_by_axes(list(axes))
        _font_cache[key] = f
    return _font_cache[key]


def serif(size, weight=400, italic=False):
    # axes: optical size, weight, softness, wonk
    return _font("Fraunces-Italic.ttf" if italic else "Fraunces.ttf", size,
                 (min(144, max(9, size / 1.8)), weight, 0, 0))


def mono(size, weight=400):
    return _font("JetBrainsMono.ttf", size, (weight,))


def sans(size, weight=400):
    return _font("AtkinsonHyperlegibleNext.ttf", size, (weight,))


def kanji(size):
    key = ("kanji", size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(os.path.join(WINFONTS,
                                                           "YuGothB.ttc"), size)
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


def label(d, xy, s, theme, tone="mid", size=17, align="left", weight=400):
    """The site's small uppercase mono, tracked about .14em."""
    return text(d, xy, s, mono(size, weight), theme[tone],
                tracking=size * 0.14, align=align)


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


def para(d, xy, s, font, fill, max_w, lh):
    x, y = xy
    lines = wrap(s, font, max_w)
    for i, line in enumerate(lines):
        d.text((x, y + i * lh), line, font=font, fill=fill)
    return y + len(lines) * lh


def headline(d, xy, plain, accent, size, theme):
    """A Fraunces line whose last phrase turns green and italic."""
    x, y = xy
    if plain:
        d.text((x, y), plain, font=serif(size), fill=theme["ink"])
        x += serif(size).getlength(plain)
    d.text((x, y), accent, font=serif(size, italic=True),
           fill=theme["bright"])


def hline(d, y, theme, tone="rule", x0=M, x1=W - M, width=1):
    d.line([(x0, y), (x1, y)], fill=theme[tone], width=width)


def scanlines(img, theme, step=4, alpha=7):
    """CRT rows, barely there: enough to read as a screen, not as stripes."""
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(0, img.height, step):
        d.line([(0, y), (img.width, y)], fill=theme["ink"] + (alpha,))


def cursor(d, x, y, h, theme):
    d.rectangle([x, y, x + h * 0.48, y + h], fill=theme["bright"])


def glitch(img, box, seed, theme, shift=16):
    """Tear a few horizontal slices of a region sideways."""
    rng = random.Random(seed)
    x0, y0, x1, y1 = [int(v) for v in box]
    for _ in range(4):
        h = rng.randint(6, 22)
        y = rng.randint(y0, y1 - h)
        dx = rng.choice([-1, 1]) * rng.randint(shift // 2, shift)
        band = img.crop((x0, y, x1, y + h))
        img.paste(theme["bg"], (x0, y, x1, y + h))
        img.paste(band, (x0 + dx, y))


def canvas(theme, h):
    img = Image.new("RGB", (W, h), theme["bg"])
    return img, ImageDraw.Draw(img)


def save_png(img, name, suffix):
    path = os.path.join(ROOT, "%s-%s.png" % (name, suffix))
    img.save(path, optimize=True)
    return path


def save_gif(frames, path, duration):
    """One shared palette across every frame, so the encoder can ship each
    frame as just the rectangle that actually changed."""
    base = frames[0].convert("P", palette=Image.ADAPTIVE, colors=128)
    qs = [f.quantize(palette=base, dither=Image.NONE) for f in frames]
    qs[0].save(path, save_all=True, append_images=qs[1:], loop=0,
               duration=duration, disposal=1, optimize=False)
    return path


# --------------------------------------------------------------------------- #
# hero: fastfetch, typed into a terminal window
# --------------------------------------------------------------------------- #

# (key, value); an empty key continues the line above, None is a blank line
FETCH = [
    ("User", "Matúš Ondrejka"),
    ("Location", "Bratislava, SK · UTC+1:00"),
    ("Uni", "STU FEI · Ing. Robotics & Cybernetics"),
    ("Focus", "Embedded · Control · 3D"),
    None,
    ("OS", "Windows 11"),
    ("", "Omarchy · Arch Linux + Hyprland"),
    ("", "Ubuntu 26.04"),
    ("", "Android 17"),
    None,
    ("Shell", "bash · zsh"),
    ("Editors", "VS Code · CLion · IntelliJ IDEA"),
    ("Langs", "C · Python · Java · JavaScript · MATLAB"),
    ("Hardware", "Arduino · ESP32 · Raspberry Pi · 3D printer"),
    ("Speaks", "Slovak · English B2 · French A2"),
    ("Site", SITE),
]

RAMP = " .-=+#@"


def ascii_logo(cols, rows):
    """緑 as fastfetch would ship a distro logo: one character per cell,
    denser where the stroke is solid. The glyph is cropped to its ink first
    so it fills the block edge to edge."""
    S = 16
    m = Image.new("L", (cols * S, rows * S * 2), 0)
    ImageDraw.Draw(m).text((cols * S / 2, rows * S), "緑",
                           font=kanji(int(rows * S * 1.6)), fill=255,
                           anchor="mm")
    m = m.crop(m.getbbox()).resize((cols, rows), Image.BOX)
    px = m.load()
    out = []
    for j in range(rows):
        line = ""
        for i in range(cols):
            v = px[i, j] / 255
            line += RAMP[min(len(RAMP) - 1, int(v * (len(RAMP) - 1) + 0.35))]
        out.append(line)
    return out


def render_hero(theme, suffix):
    H = 1290
    img, d = canvas(theme, H)

    # above the window, one line in the site's own voice
    headline(d, (M - 4, 34), "Hi, I’m ", "Matúš.", 92, theme)
    label(d, (W - M, 62), "ROBOTICS · EMBEDDED · CONTROL", theme,
          align="right")
    label(d, (W - M, 98), "AKA @" + USER.upper(), theme, "dim", align="right")

    # the window
    top, bot = 180, H - 40
    d.rectangle([M, top, W - M, bot], outline=theme["rule_strong"])
    d.rectangle([M + 1, top + 1, W - M - 1, top + 52], fill=theme["ghost"])
    for k in range(3):
        x = M + 26 + k * 24
        d.rectangle([x, top + 20, x + 12, top + 32],
                    outline=theme["rule_strong"])
    label(d, (W / 2, top + 17), "GREENYBEANY@FEI: ~", theme, size=16,
          align="center")
    label(d, (W - M - 24, top + 17), "TTY1", theme, "dim", size=16,
          align="right")
    d.line([(M, top + 53), (W - M, top + 53)], fill=theme["rule_strong"])

    f, fb = mono(24), mono(24, 700)
    lh = 40
    px0, py0 = M + 40, top + 84
    prompt = "greenybeany@fei:~$ "
    pw = f.getlength(prompt)

    cols, rows = 34, 18
    logo = ascii_logo(cols, rows)
    lx, ly = px0 + 10, py0 + 70
    ch_w = f.getlength("M")

    ix, iy = lx + cols * ch_w + 70, py0 + 70
    keyw = fb.getlength("Hardware") + 30

    # everything the command prints, in order, as draw calls
    out_lines = []

    def title(dd, y):
        x = ix
        for s, font, tone in (("greenybeany", fb, "bright"), ("@", f, "mid"),
                              ("fei", fb, "bright")):
            dd.text((x, y), s, font=font, fill=theme[tone])
            x += font.getlength(s)
    out_lines.append(title)
    out_lines.append(lambda dd, y: dd.text(
        (ix, y), "-" * len("greenybeany@fei"), font=f, fill=theme["dim"]))
    for row in FETCH:
        if row is None:
            out_lines.append(None)
            continue

        def draw_row(dd, y, k=row[0], v=row[1]):
            if k:
                dd.text((ix, y), k, font=fb, fill=theme["bright"])
            dd.text((ix + keyw, y), v, font=f, fill=theme["ink"])
        out_lines.append(draw_row)

    swatches = ["faint", "dim", "rule_strong", "mid", "ink_soft", "ink",
                "bright", "hot"]
    blocks_y = iy + (len(out_lines) + 1) * lh

    def frame(typed, shown, caret, glitchy=False):
        fr = img.copy()
        dd = ImageDraw.Draw(fr)
        dd.text((px0, py0), prompt, font=f, fill=theme["bright"])
        cmd = "fastfetch"[:typed]
        dd.text((px0 + pw, py0), cmd, font=f, fill=theme["ink"])
        if shown == 0 and caret:
            cursor(dd, px0 + pw + f.getlength(cmd) + 4, py0 + 2, 28, theme)
        if shown:
            n_logo = min(rows, int(rows * shown / len(out_lines)) + 1)
            for j in range(n_logo):
                dd.text((lx, ly + j * 28), logo[j], font=f,
                        fill=theme["bright"])
            for i in range(min(shown, len(out_lines))):
                if out_lines[i]:
                    out_lines[i](dd, iy + i * lh)
        if shown >= len(out_lines):
            sw = 46
            for k, tone in enumerate(swatches):
                dd.rectangle([ix + k * sw, blocks_y, ix + k * sw + sw - 6,
                              blocks_y + 26], fill=theme[tone])
            ny = blocks_y + 80
            dd.text((px0, ny), prompt, font=f, fill=theme["bright"])
            if caret:
                cursor(dd, px0 + pw + 4, ny + 2, 28, theme)
        if glitchy:
            glitch(fr, (lx - 20, ly, lx + cols * ch_w + 20, ly + rows * 28),
                   seed=7, theme=theme, shift=22)
        scanlines(fr, theme)
        return fr

    # idle prompt, the command typed out, the output scrolling in, then a
    # long hold on the finished screen with the cursor blinking
    frames, durs = [], []
    for k in range(4):
        frames.append(frame(0, 0, k % 2 == 0))
        durs.append(260)
    for t in range(1, len("fastfetch") + 1):
        frames.append(frame(t, 0, True))
        durs.append(70)
    frames.append(frame(9, 0, True))
    durs.append(300)
    for n in range(1, len(out_lines) + 1):
        frames.append(frame(9, n, False))
        durs.append(45)
    for k in range(12):
        frames.append(frame(9, len(out_lines), k % 2 == 0, glitchy=k == 7))
        durs.append(80 if k == 7 else 500)
    return save_gif(frames, os.path.join(ROOT, "hero-%s.gif" % suffix), durs)


# --------------------------------------------------------------------------- #
# projects
# --------------------------------------------------------------------------- #

PROJECTS = [
    {
        "slug": "triptych",
        "name": "triptych",
        "url": "https://triptych.greenybeany.dev/",
        "desc": "Free, open-source music app for your own Jellyfin server or "
                "Navidrome. Spotify, Apple Music or Nothing style, synced lyrics, "
                "offline downloads, stats & Wrapped. Windows, Linux, Android and "
                "iPhone.",
        "tags": "JAVASCRIPT",
        "web": True,
    },
    {
        "slug": "beanyik",
        "name": "BeanyIK",
        "url": "https://greenybeany.dev/BeanyIK/",
        "desc": "A drag & drop robot kinematics builder. Chain joints with DH "
                "parameters or custom matrices, then solve forward and inverse "
                "kinematics and watch the arm move.",
        "tags": "ELECTRON · KINEMATICS",
        "web": True,
    },
    {
        "slug": "beanydrive",
        "name": "BeanyDrive",
        "url": "https://github.com/Greenythebeany/BeanyDrive",
        "desc": "Turns a Discord text channel into personal cloud storage. Splits "
                "files into chunks, uploads them as attachments and rebuilds them "
                "on download, all from a keyboard-driven terminal UI.",
        "tags": "ELECTRON · DISCORD API",
    },
    {
        "slug": "beanylab",
        "name": "BeanyLab",
        "url": "https://github.com/Greenythebeany/BeanyLab",
        "desc": "An open-source numeric computing environment that runs .m files, "
                "with a block-diagram simulator. Clean-room, Apache-2.0, for "
                "Windows and Linux.",
        "tags": "RUST · TAURI · NUMERICS",
    },
    {
        "slug": "betterais",
        "name": "BetterAIS",
        "url": "https://github.com/Greenythebeany/BetterAis",
        "desc": "A Chrome extension that gives is.stuba.sk a calmer, modern look: "
                "better typography, a cleaner layout and less clutter for the "
                "daily AIS routine.",
        "tags": "CHROME EXTENSION · CSS",
    },
]


def render_projects_head(theme, suffix):
    H = 300
    img, d = canvas(theme, H)
    headline(d, (M - 4, 40), "Things I’m ", "building.", 92, theme)
    f = mono(24)
    w = text(d, (M, 200), "greenybeany@fei:~$ ", f, theme["bright"])
    text(d, (M + w, 200), "ls ~/projects", f, theme["ink"])
    label(d, (W - M, 206), "%02d ITEMS" % len(PROJECTS), theme, align="right")
    scanlines(img, theme)
    return save_png(img, "projects", suffix)


def render_project(p, i, theme, suffix):
    f_desc = sans(26)
    lines = wrap(p["desc"], f_desc, 1080)
    H = 132 + len(lines) * 42 + 72
    img, d = canvas(theme, H)
    hline(d, 0, theme, width=2)

    label(d, (M, 56), "[%02d]" % i, theme, "bright")
    tx = M + 156
    d.text((tx, 36), p["name"], font=serif(54), fill=theme["ink"])
    for k, line in enumerate(lines):
        d.text((tx, 126 + k * 42), line, font=f_desc, fill=theme["ink_soft"])
    ty = 126 + len(lines) * 42 + 22
    w = label(d, (tx, ty), "> " + p["tags"], theme, size=15)
    if p.get("web"):
        label(d, (tx + w + 30, ty), "WEBSITE ↗", theme, "bright", size=15,
              weight=700)
    text(d, (W - M, 40), "↗", mono(40), theme["mid"], align="right")
    return save_png(img, "project-" + p["slug"], suffix)


# --------------------------------------------------------------------------- #
# footer
# --------------------------------------------------------------------------- #

def render_footer(theme, suffix, frames=2, duration=550):
    H = 380
    img, d = canvas(theme, H)
    hline(d, 0, theme, width=2)
    label(d, (M, 60), "ALL REPOSITORIES ON GITHUB ↗", theme, "ink", size=17,
          weight=700)
    label(d, (W - M, 60), "GITHUB.COM/" + USER.upper(), theme, size=17,
          align="right")
    hline(d, 120, theme)
    headline(d, (M - 4, 160), "Thanks for ", "stopping by.", 72, theme)
    label(d, (W - M, 196), "MORE AT " + SITE.upper() + " ↗", theme, "bright",
          size=17, align="right", weight=700)
    hline(d, 286, theme)
    f = mono(19)
    prompt = "greenybeany@fei:~$ "
    w = text(d, (M, 314), prompt, f, theme["bright"])
    w += text(d, (M + w, 314), "exit", f, theme["ink"])
    label(d, (W - M, 316), "SESSION CLOSED · 0 ERRORS", theme, "dim", size=15,
          align="right")
    scanlines(img, theme)

    out = []
    for t in range(frames):
        fr = img.copy()
        if t == 0:
            cursor(ImageDraw.Draw(fr), M + w + 12, 314, 26, theme)
        out.append(fr)
    return save_gif(out, os.path.join(ROOT, "footer-%s.gif" % suffix),
                    duration)


# --------------------------------------------------------------------------- #
# snake contribution graph, recoloured to match
# --------------------------------------------------------------------------- #

# --cs is the snake, --c0..--c4 the contribution levels, --ce an eaten cell,
# --cb the cell stroke. snk emits no --c0 in its dark block, which would leave
# pale cells on a dark canvas, so every variant declares the full set.
# --ce sits a hair off the page background rather than exactly on it, so an
# empty day still reads as a cell instead of vanishing. Levels climb through
# the site's green; the snake is its ink.
SNAKE = {
    "dark": ("--cb:#2a2925;--cs:#ebe4d8;--ce:#1f1e1b;--c0:#1f1e1b;"
             "--c1:#2c4426;--c2:#467a3a;--c3:#6aae5b;--c4:#8fd67f"),
    "light": ("--cb:#d6d0c3;--cs:#1c1b18;--ce:#e3ded2;--c0:#e3ded2;"
              "--c1:#c3d8b8;--c2:#8bb87e;--c3:#4f8a40;--c4:#2e6b22"),
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
        outs = [
            render_hero(theme, suffix),
            render_projects_head(theme, suffix),
        ]
        for i, p in enumerate(PROJECTS, 1):
            outs.append(render_project(p, i, theme, suffix))
        outs.append(render_footer(theme, suffix))
        for o in outs:
            print("%8.0f KB  %s" % (os.path.getsize(o) / 1024,
                                    os.path.basename(o)))
    for o in render_snake():
        print("%8.0f KB  %s" % (os.path.getsize(o) / 1024,
                                os.path.basename(o)))


if __name__ == "__main__":
    main()
