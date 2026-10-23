"""Stage 2: the "RICOH GR II" wordmark.

Lockup (top-right sky, where the subject is looking):

         |~~|          <- hairline threads from the top of the screen,
    R I C O H  |  |       bridged by a sagging web strand
    G R       |  |     <- heavy grotesk + Roman numeral II built from two
              |  |        hanging web strands

All geometry is in 1x screen units (640x480).  Layers are drawn at
DRAW px per unit, then downsampled to the output scale, which gives clean
anti-aliasing at both 1x and 2x.  Every animated property is a field of
WordmarkState so animate.py can keyframe it.
"""
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Bahnschrift is a variable font (wght + wdth axes); it ships with Windows.
FONT_PATH = os.environ.get("GR2_FONT", "C:/Windows/Fonts/bahnschrift.ttf")

INK = np.array([34, 30, 42], dtype=np.float32)      # sampled from suit shadows
RED = np.array([190, 42, 36], dtype=np.float32)     # suit red, slightly deepened
WEB = np.array([96, 16, 20], dtype=np.float32)      # suit seam red for webbing
GLOW = np.array([255, 96, 60], dtype=np.float32)    # warm halation around the II

SS = 4  # supersampling factor relative to the output scale


@dataclass
class WordmarkState:
    ricoh_alpha: float = 1.0
    ricoh_spread: float = 0.0        # extra tracking in cap-heights, eases to 0
    gr_alpha: float = 1.0
    gr_dy: float = 0.0
    strand_drop: tuple = (1.0, 1.0)  # 0 = above the screen, 1 = landed
    thread_alpha: float = 1.0
    cross_progress: float = 1.0      # 0..1 draw-on of the cross strand
    drop_alpha: float = 0.0         # dew drops (off: they read as '!!')
    glow: float = 0.0                # extra halation pulse on the II
    ink_alpha: float = 1.0           # global fade for RICOH GR
    red_alpha: float = 1.0           # global fade for the II


@dataclass
class Layout:
    right: float = 606.0   # right edge of the lockup
    top: float = 26.0      # top of RICOH caps
    cap: float = 54.0      # GR cap height
    ricoh_cap_ratio: float = 0.235
    ricoh_gap_ratio: float = 0.30
    ii_gap_ratio: float = 0.36
    ii_width_ratio: float = 0.64
    bridge_k: tuple = (1.80, 1.70)  # web bridge height above baseline, in caps
    bridge_sag: float = 0.10        # bridge sag, in caps
    thread_w: float = 0.9           # hairline width, 1x px
    glow_radius: float = 4.0        # II halation blur, 1x px
    ii_web: bool = False            # suit-style webbing inside the II strands
    strand_dome: bool = False       # domed strand tops (reads better when large)
    # Serif lockup (v3). With serif_font set, GR, RICOH and the II are all set
    # in that static font and the II is a pair of glyphs instead of strands.
    serif_font: str = ""
    ii_track: float = 0.04          # tracking between the two I's, in caps
    ricoh_track: float = -1.0       # RICOH tracking in caps; < 0 spreads it to GR's width
    rule: bool = False              # hairline rule under the lockup, like a plate caption
    ink: tuple = tuple(INK.tolist())
    red: tuple = tuple(RED.tolist())
    halation: bool = True           # warm glow under the II
    misregister: bool = True        # colour plates nudged apart
    # derived (filled by solve())
    gr_x: float = 0.0
    gr_w: float = 0.0
    baseline: float = 0.0
    ii_x: float = 0.0
    ii_w: float = 0.0
    left: float = 0.0
    width: float = 0.0
    ricoh_cap: float = 0.0
    strands: list = field(default_factory=list)


def _font(weight, width=100):
    f = ImageFont.truetype(FONT_PATH, 100)
    f.set_variation_by_axes([weight, width])
    return f


def _cap_ratio(font):
    l, t, r, b = font.getbbox("H")
    return (b - t) / font.size


GR_FONT = _font(700, 100)
RICOH_FONT = _font(600, 100)
GR_CAP = _cap_ratio(GR_FONT)
RICOH_CAP = _cap_ratio(RICOH_FONT)


def _text_width(font, size, text, tracking=0.0):
    f = font.font_variant(size=size)
    return sum(f.getlength(ch) for ch in text) + tracking * (len(text) - 1)


@lru_cache(maxsize=None)
def _static_font(path):
    if not Path(path).exists():
        raise SystemExit(f"serif font not found: {path}\n"
                         "set GR2_SERIF_FONT to Centaur or another static serif .ttf")
    return ImageFont.truetype(path, 100)


def fonts(lay):
    """(GR font, RICOH font) for a layout, both at size 100."""
    if lay.serif_font:
        f = _static_font(lay.serif_font)
        return f, f
    return GR_FONT, RICOH_FONT


def ricoh_placement(lay):
    """(x of the first RICOH cap, tracking), both in 1x units."""
    if lay.ricoh_track < 0:
        _, rf = fonts(lay)
        base_w = _text_width(rf, lay.ricoh_cap / _cap_ratio(rf), "RICOH")
        return lay.gr_x, (lay.gr_w - base_w) / 4
    _, rf = fonts(lay)
    tracking = lay.ricoh_track * lay.cap
    w = _text_width(rf, lay.ricoh_cap / _cap_ratio(rf), "RICOH", tracking)
    return lay.gr_x + (lay.width - w) / 2, tracking


def solve(lay=None):
    lay = lay or Layout()
    cap = lay.cap
    gf, _ = fonts(lay)
    gr_size = cap / _cap_ratio(gf)
    f = gf.font_variant(size=gr_size)
    l, t, r, b = f.getbbox("GR")
    lay.gr_w = r - l
    if lay.serif_font:
        # matches _draw_text: the first I's ink starts at ii_x, the second
        # follows one advance plus tracking later
        _, _, ir, _ = f.getbbox("I")
        lay.ii_w = f.getlength("I") + cap * lay.ii_track + ir
    else:
        lay.ii_w = cap * lay.ii_width_ratio
    lay.width = lay.gr_w + cap * lay.ii_gap_ratio + lay.ii_w
    lay.left = lay.right - lay.width
    lay.gr_x = lay.left
    lay.ii_x = lay.gr_x + lay.gr_w + cap * lay.ii_gap_ratio
    lay.ricoh_cap = cap * lay.ricoh_cap_ratio
    lay.baseline = lay.top + lay.ricoh_cap + cap * lay.ricoh_gap_ratio + cap
    stem = cap * 0.17
    lay.strands = [lay.ii_x + stem / 2, lay.ii_x + lay.ii_w - stem / 2]
    return lay


def centered(lay, cx=320.0):
    """Solve `lay`, then shift it so the lockup is centred on x = cx."""
    solve(lay)
    lay.right = cx + lay.width / 2
    return solve(lay)


def left_aligned(lay, x=26.0):
    """Solve `lay`, then shift it so the lockup starts at x."""
    solve(lay)
    lay.right = x + lay.width
    return solve(lay)


LAYOUT = solve()


# --------------------------------------------------------------------------- #
# Mask drawing (draw space: units * D)
# --------------------------------------------------------------------------- #
def _draw_text(mask, font, cap_h, x, base_y, text, tracking, D):
    size = cap_h / (_cap_ratio(font)) * D
    f = font.font_variant(size=size)
    l, t, r, b = f.getbbox("H")
    d = ImageDraw.Draw(mask)
    cx = x * D
    for ch in text:
        cl, _, _, _ = f.getbbox(ch)
        d.text((cx - (cl if ch == text[0] else 0), base_y * D - b), ch, font=f, fill=255)
        cx += f.getlength(ch) + tracking * D


def _strand_poly(cx, top, bottom, cap, dome=False):
    """A hanging strand: hairline at the top flaring into a stem with a slight
    waist, so it reads as a web line that thickens into a letter.  With
    `dome`, the top is a flattened dome instead of a taper, which keeps large
    strands from looking like pencil tips."""
    w = cap * 0.17
    flare = w * 0.45 if dome else cap * 0.07
    pts_l, pts_r = [], []
    for i in range(41):
        s = i / 40
        y = top + (bottom - top) * s
        dist = (y - top)
        k = min(1.0, dist / flare)
        k = np.sqrt(1 - (1 - k) ** 2) if dome else 1 - (1 - k) ** 2
        waist = 1 - 0.06 * np.sin(np.pi * s)    # subtle silk waist
        half = (cap * 0.012 + (w / 2 - cap * 0.012) * k) * waist
        pts_l.append((cx - half, y))
        pts_r.append((cx + half, y))
    return pts_l + pts_r[::-1]


def _drop_poly(cx, y, cap):
    """Small dew drop hanging just below a strand foot."""
    r = cap * 0.052
    cy = y + cap * 0.10 + r
    pts = []
    for i in range(48):
        a = 2 * np.pi * i / 48
        px, py = np.sin(a) * r, -np.cos(a) * r
        if py < 0:  # pinch the top into a point
            px *= (1 + py / r) ** 0.8
            py *= 1.45
        pts.append((cx + px, cy + py))
    return pts


def draw_masks(state, lay=LAYOUT, D=4):
    """Return (ink_mask, red_mask, thread_mask) as float arrays in draw space
    covering the whole 640x480 canvas."""
    W, H = int(640 * D), int(480 * D)
    ink = Image.new("L", (W, H), 0)
    red = Image.new("L", (W, H), 0)
    thread = Image.new("L", (W, H), 0)
    cap = lay.cap

    gr_font, ricoh_font = fonts(lay)

    # RICOH, tracked so it spans the lockup width (or centred over it)
    if state.ricoh_alpha > 0:
        rc = lay.ricoh_cap
        x0, tracking = ricoh_placement(lay)
        tracking += state.ricoh_spread * cap
        m = Image.new("L", (W, H), 0)
        _draw_text(m, ricoh_font, rc, x0, lay.top + rc, "RICOH", tracking, D)
        ink.paste(Image.eval(m, lambda v: int(v * state.ricoh_alpha)), (0, 0), m)

    # GR
    if state.gr_alpha > 0:
        m = Image.new("L", (W, H), 0)
        _draw_text(m, gr_font, cap, lay.gr_x, lay.baseline + state.gr_dy, "GR", 0, D)
        a = state.gr_alpha
        ink = Image.fromarray(np.maximum(np.asarray(ink), (np.asarray(m) * a).astype(np.uint8)))

    if lay.serif_font:
        # II as two roman capitals, and a hairline rule under the lockup
        _draw_text(red, gr_font, cap, lay.ii_x, lay.baseline, "II", cap * lay.ii_track, D)
        if lay.rule:
            y = (lay.baseline + cap * 0.30) * D
            ImageDraw.Draw(ink).line([(lay.left * D, y), ((lay.left + lay.width) * D, y)],
                                     fill=190, width=max(1, int(round(lay.thread_w * D))))
        return ink, red, thread

    # II: strands, threads, cross strand, drops
    top_y = lay.baseline - cap
    travel = lay.baseline + cap * 0.4
    dr = ImageDraw.Draw(red)
    dt = ImageDraw.Draw(thread)
    feet = []
    for cx, p in zip(lay.strands, state.strand_drop):
        if p <= 0:
            feet.append(None)
            continue
        dy = (p - 1) * travel
        t, b = top_y + dy, lay.baseline + dy
        if b < -2:
            feet.append(None)
            continue
        dr.polygon([(x * D, y * D) for x, y in _strand_poly(cx, t, b, cap, lay.strand_dome)], fill=255)
        if state.thread_alpha > 0 and t > 0:
            dt.line([(cx * D, 0), (cx * D, (t + cap * 0.02) * D)],
                    fill=int(255 * state.thread_alpha), width=max(1, int(round(lay.thread_w * D))))
        feet.append((cx, b))

    if state.cross_progress > 0 and all(feet):
        # Web bridge between the two threads, above the letters, so the
        # numeral itself stays a clean II.
        (x1, b1), (x2, b2) = feet
        y1, y2 = b1 - cap * lay.bridge_k[0], b2 - cap * lay.bridge_k[1]
        n = 24
        pts = []
        for i in range(n + 1):
            s = i / n * state.cross_progress
            x = x1 + (x2 - x1) * s
            y = y1 + (y2 - y1) * s + np.sin(np.pi * s) * cap * lay.bridge_sag
            pts.append((x * D, y * D))
        dt.line(pts, fill=int(255 * state.thread_alpha),
                width=max(1, int(round(lay.thread_w * D))), joint="curve")

    if state.drop_alpha > 0:
        m = Image.new("L", (W, H), 0)
        dm = ImageDraw.Draw(m)
        for foot in feet:
            if foot:
                dm.polygon([(x * D, y * D) for x, y in _drop_poly(foot[0], foot[1], cap)],
                           fill=int(255 * state.drop_alpha))
        red = Image.fromarray(np.maximum(np.asarray(red), np.asarray(m)))

    return ink, red, thread


def ii_web_lines(lay):
    """Suit-style webbing for large II strands, as polylines in 1x units:
    a centre seam, plus rings that droop into a U between the seam and each
    edge, the way the web cells hang on Spider-Man's sleeves."""
    cap = lay.cap
    w = cap * 0.17
    top, bottom = lay.baseline - cap, lay.baseline
    pitch = w * 0.72
    sag = pitch * 0.32
    lines = []
    for cx in lay.strands:
        lines.append([(cx, top + w * 0.30), (cx, bottom)])
        y = top + w * 0.55
        while y < bottom - pitch * 0.25:
            for side in (-1, 1):
                pts = []
                for i in range(9):
                    u = i / 8                                  # seam -> edge
                    x = cx + side * u * w * 0.62
                    pts.append((x, y + np.sin(np.pi * u) * sag))
                lines.append(pts)
            y += pitch
    return lines


def draw_ii_web(lay, D):
    m = Image.new("L", (int(640 * D), int(480 * D)), 0)
    d = ImageDraw.Draw(m)
    lw = max(1, int(round(0.9 * D)))
    for pts in ii_web_lines(lay):
        d.line([(x * D, y * D) for x, y in pts], fill=255, width=lw, joint="curve")
    return m


# --------------------------------------------------------------------------- #
# Compositing
# --------------------------------------------------------------------------- #
def _down(mask, size):
    return np.asarray(mask.resize(size, Image.BOX), dtype=np.float32) / 255.0


def _shift(a, dx):
    out = np.zeros_like(a)
    if dx > 0:
        out[:, dx:] = a[:, :-dx]
    elif dx < 0:
        out[:, :dx] = a[:, -dx:]
    else:
        out[:] = a
    return out


def composite(base, state, scale=1, lay=LAYOUT):
    """Lay the wordmark over `base` (float32 HxWx3, 0..255) at the given scale."""
    D = SS * scale
    ink_m, red_m, thr_m = draw_masks(state, lay, D)
    # A whisper of softness so the type sits in the emulsion, not on top of it.
    soft = ImageFilter.GaussianBlur(0.35 * D)
    ink_m, red_m, thr_m = ink_m.filter(soft), red_m.filter(soft), thr_m.filter(soft)

    H, W = base.shape[:2]
    big = (W * SS, H * SS)  # draw space is already at D = SS*scale per unit
    assert ink_m.size == big
    # Downsample with misregistration: red plate nudged right, blue plate left.
    off = (SS // 2 + 1 if scale == 1 else SS) if lay.misregister else 0
    ink_c, red_c = np.array(lay.ink, dtype=np.float32), np.array(lay.red, dtype=np.float32)
    out = base.copy()

    def lay_plate(mask_img, color, alpha):
        if alpha <= 0:
            return
        a = np.asarray(mask_img, dtype=np.float32) / 255.0
        planes = [_shift(a, off), a, _shift(a, -off)]
        for c in range(3):
            m = Image.fromarray((planes[c] * 255).astype(np.uint8)).resize((W, H), Image.BOX)
            m = np.asarray(m, dtype=np.float32) / 255.0 * alpha
            out[..., c] = out[..., c] * (1 - m) + color[c] * m

    # Hairline threads: semi-transparent ink
    lay_plate(thr_m, ink_c, 0.55 * state.red_alpha)
    lay_plate(ink_m, ink_c, state.ink_alpha)

    # Halation under the II (always a little, more during the pulse)
    g_amt = (0.22 + 0.45 * state.glow) * state.red_alpha
    if g_amt > 0 and lay.halation:
        g = red_m.resize((W, H), Image.BOX).filter(ImageFilter.GaussianBlur(lay.glow_radius * scale))
        g = np.asarray(g, dtype=np.float32)[..., None] / 255.0 * g_amt
        out = out * (1 - g) + GLOW * g

    lay_plate(red_m, red_c, state.red_alpha)
    if lay.ii_web:
        web = np.asarray(draw_ii_web(lay, D).filter(soft), dtype=np.float32)
        web = web * (np.asarray(red_m, dtype=np.float32) / 255.0)  # clip to the strands
        lay_plate(Image.fromarray(web.astype(np.uint8)), WEB, 0.85 * state.red_alpha)
    return out


def ii_center(lay=LAYOUT):
    return ((lay.strands[0] + lay.strands[1]) / 2, lay.baseline - lay.cap * 0.5)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    base = np.asarray(Image.open(root / "assets/prepared/base_640x480.png").convert("RGB"), dtype=np.float32)
    out = composite(base, WordmarkState(), 1)
    (root / "build").mkdir(exist_ok=True)
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(root / "build/type_preview_1x.png")
    print(LAYOUT)
