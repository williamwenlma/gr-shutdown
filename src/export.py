"""Stage 4: frames -> GIFs, MP4 preview, stills, and the wordmark as SVG.

    python src/export.py            # all versions
    python src/export.py v2         # one version
    python src/export.py --crop-y 0 # override the crop for a new photo

Outputs (out/ for v1, out/v2/ with a gr2_v2_ prefix for v2):
  gr2_shutdown_640x480.gif         camera master: 6 frames x 200 ms, plays once,
                                   ends on black
  gr2_shutdown_640x480_loop.gif    same, looping (for sharing / previews)
  gr2_shutdown_1280x960_loop.gif   2x share copy
  gr2_shutdown_preview.mp4         2x H.264 preview
  gr2_still_*.png/.jpg             key frame with the full lockup
  ricoh_gr2_wordmark.svg           editable vector lockup (also in type/)
"""
import argparse
import dataclasses
import shutil
import subprocess
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import animate  # noqa: E402
import prepare  # noqa: E402
import typography as ty  # noqa: E402
from versions import VERSIONS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
STILL_FRAME = 0  # the held key frame, before the fade


def run(cmd):
    print(" ".join(map(str, cmd)))
    subprocess.run(list(map(str, cmd)), check=True, capture_output=True)


def render_frames(v, scale):
    P = animate.Plates(scale, v.layout, v.base_suffix)
    d = BUILD / f"frames_{v.name}_{scale}x"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for f in range(animate.N_FRAMES):
        animate.render_frame(P, f).save(d / f"{f:04d}.png")
    return d


def make_gif(frames, out, loop):
    pal = BUILD / f"palette_{frames.name}.png"
    src = ["-framerate", animate.FPS, "-i", frames / "%04d.png"]
    run(["ffmpeg", "-y", "-v", "error", *src,
         "-vf", "palettegen=stats_mode=full", pal])
    run(["ffmpeg", "-y", "-v", "error", *src, "-i", pal,
         "-lavfi", "[0:v][1:v]paletteuse=dither=none:diff_mode=rectangle",
         "-loop", 0 if loop else -1, out])


def make_mp4(frames, out):
    run(["ffmpeg", "-y", "-v", "error", "-framerate", animate.FPS, "-i", frames / "%04d.png",
         "-vf", "fps=30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16",
         "-movflags", "+faststart", out])


def make_stills(v, frames, scale):
    W, H = 640 * scale, 480 * scale
    im = Image.open(frames / f"{STILL_FRAME:04d}.png").convert("RGB")
    im.save(v.out_dir / f"{v.prefix}_still_{W}x{H}.png")
    im.save(v.out_dir / f"{v.prefix}_still_{W}x{H}.jpg", quality=95, subsampling=0)


# --------------------------------------------------------------------------- #
# SVG wordmark
# --------------------------------------------------------------------------- #
def _instance(weight):
    f = TTFont(ty.FONT_PATH)
    return instancer.instantiateVariableFont(f, {"wght": weight, "wdth": 100})


def _glyph_paths(font, text, cap_h, x0, baseline, tracking):
    upm = font["head"].unitsPerEm
    cap_units = font["OS/2"].sCapHeight
    s = cap_h / cap_units
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    paths = []
    x = x0 - hmtx[cmap[ord(text[0])]][1] * s
    for ch in text:
        name = cmap[ord(ch)]
        pen = SVGPathPen(gs)
        gs[name].draw(TransformPen(pen, (s, 0, 0, -s, x, baseline)))
        paths.append(pen.getCommands())
        x += hmtx[name][0] * s + tracking
    return paths, s, upm


def _advance_width(font, text, s):
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    return sum(hmtx[cmap[ord(c)]][0] for c in text) * s


def make_svg(lay, out_paths):
    cap = lay.cap
    bold, semi = _instance(700), _instance(600)
    gr, _, _ = _glyph_paths(bold, "GR", cap, lay.gr_x, lay.baseline, 0)
    rc = lay.ricoh_cap
    s = rc / semi["OS/2"].sCapHeight
    tracking = (lay.gr_w - _advance_width(semi, "RICOH", s)) / 4
    ricoh, _, _ = _glyph_paths(semi, "RICOH", rc, lay.gr_x, lay.top + rc, tracking)

    top_y = lay.baseline - cap
    strands = ["M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in ty._strand_poly(cx, top_y, lay.baseline, cap, lay.strand_dome)) + " Z"
               for cx in lay.strands]
    (x1, x2) = lay.strands
    y1, y2 = lay.baseline - cap * lay.bridge_k[0], lay.baseline - cap * lay.bridge_k[1]
    sag = cap * lay.bridge_sag * 2  # quadratic control point doubles the sine peak
    bridge = f"M{x1:.2f},{y1:.2f} Q{(x1 + x2) / 2:.2f},{(y1 + y2) / 2 + sag:.2f} {x2:.2f},{y2:.2f}"
    threads = "".join(f'<line x1="{cx:.2f}" y1="0" x2="{cx:.2f}" y2="{top_y + 1:.2f}"/>' for cx in lay.strands)

    vx, vw = lay.left - 12, lay.width + 24
    vh = lay.baseline + 14
    web = ""
    if lay.ii_web:
        clip = "".join(f'<path d="{p}"/>' for p in strands)
        lines = "".join('<polyline points="' + " ".join(f"{x:.2f},{y:.2f}" for x, y in pts) + '"/>'
                        for pts in ty.ii_web_lines(lay))
        web_col = "#%02x%02x%02x" % tuple(int(v) for v in ty.WEB)
        web = (f'\n  <clipPath id="ii-clip">{clip}</clipPath>'
               f'\n  <g id="ii-web" clip-path="url(#ii-clip)" stroke="{web_col}" stroke-opacity="0.85" '
               f'stroke-width="0.9" fill="none" stroke-linejoin="round">{lines}</g>')
    ink = "#%02x%02x%02x" % tuple(int(v) for v in ty.INK)
    red = "#%02x%02x%02x" % tuple(int(v) for v in ty.RED)
    glow = "#%02x%02x%02x" % tuple(int(v) for v in ty.GLOW)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx:.1f} 0 {vw:.1f} {vh:.1f}" width="{vw * 4:.0f}" height="{vh * 4:.0f}">
  <title>RICOH GR II - web-strand wordmark</title>
  <defs>
    <filter id="halation" x="-50%" y="-20%" width="200%" height="140%">
      <feGaussianBlur stdDeviation="{lay.glow_radius:g}"/>
    </filter>
  </defs>
  <g id="threads" stroke="{ink}" stroke-opacity="0.55" stroke-width="{lay.thread_w}" fill="none">
    {threads}
    <path d="{bridge}"/>
  </g>
  <g id="ricoh" fill="{ink}">{"".join(f'<path d="{p}"/>' for p in ricoh)}</g>
  <g id="gr" fill="{ink}">{"".join(f'<path d="{p}"/>' for p in gr)}</g>
  <g id="ii-halation" fill="{glow}" opacity="0.3" filter="url(#halation)">{"".join(f'<path d="{p}"/>' for p in strands)}</g>
  <g id="ii" fill="{red}">{"".join(f'<path d="{p}"/>' for p in strands)}</g>{web}
</svg>
'''
    for p in out_paths:
        p.write_text(svg, encoding="utf-8")


def build(v):
    out, pre = v.out_dir, v.prefix
    out.mkdir(parents=True, exist_ok=True)
    prepare.prepare(v.crop_y0, suffix=v.base_suffix)
    f1 = render_frames(v, 1)
    f2 = render_frames(v, 2)
    make_gif(f1, out / f"{pre}_shutdown_640x480.gif", loop=False)
    make_gif(f1, out / f"{pre}_shutdown_640x480_loop.gif", loop=True)
    make_gif(f2, out / f"{pre}_shutdown_1280x960_loop.gif", loop=True)
    make_mp4(f2, out / f"{pre}_shutdown_preview.mp4")
    make_stills(v, f1, 1)
    make_stills(v, f2, 2)
    svg_name = "ricoh_gr2_wordmark.svg" if v.name == "v1" else f"ricoh_gr2_wordmark_{v.name}.svg"
    (ROOT / "type").mkdir(exist_ok=True)
    make_svg(v.layout, [out / svg_name, ROOT / "type" / svg_name])
    for p in sorted(out.glob(f"{pre}_*")) + [out / svg_name]:
        print(f"{p.name:44s} {p.stat().st_size / 1024:8.0f} KB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("versions", nargs="*", metavar="version",
                    help=f"one or more of {', '.join(sorted(VERSIONS))} (default: all)")
    ap.add_argument("--crop-y", type=int, help="top of the 4:3 window in source pixels "
                    "(overrides the version's crop_y0, which is tuned per photo)")
    args = ap.parse_args()
    unknown = [n for n in args.versions if n not in VERSIONS]
    if unknown:
        ap.error(f"unknown version: {', '.join(unknown)}")
    for n in args.versions or sorted(VERSIONS):
        v = VERSIONS[n]
        if args.crop_y is not None:
            v = dataclasses.replace(v, crop_y0=args.crop_y)
        build(v)


if __name__ == "__main__":
    main()
