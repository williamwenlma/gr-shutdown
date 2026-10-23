"""Stage 3: render the shutdown animation frames.

6 frames x 200 ms = 1.2 s:
  0-1  the photo with the full RICOH GR II lockup holds (0.4 s)
  2-5  natural fade to black

The fade is computed in linear light, so equal steps in the schedule read
as an even dimming on screen rather than a sudden drop.  Bright pixels
(city lights, the II's halation) fade a touch later than the rest, like a
screen or print losing its light.
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

import typography as ty
from versions import VERSIONS

ROOT = Path(__file__).resolve().parents[1]
N_FRAMES = 6
FRAME_MS = 200
FPS = 1000 // FRAME_MS
FADE = [1.0, 1.0, 0.50, 0.20, 0.05, 0.0]  # linear-light brightness per frame
LINGER = 0.4  # how much longer highlights hold during the fade (0 = uniform)


def srgb_to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


class Plates:
    def __init__(self, scale, layout=ty.LAYOUT, base_suffix="", seed=7):
        self.scale = scale
        W, H = 640 * scale, 480 * scale
        self.size = (W, H)
        base = np.asarray(
            Image.open(ROOT / f"assets/prepared/base_{W}x{H}{base_suffix}.png").convert("RGB"),
            dtype=np.float32)
        self.lum_w = np.array([0.299, 0.587, 0.114], dtype=np.float32)

        # Static film grain: one plate, so held frames are identical and the
        # GIF only stores what changes.
        rng = np.random.default_rng(seed)
        n = rng.normal(0, 1, (H, W)).astype(np.float32)
        img = Image.fromarray(np.clip(n * 40 + 128, 0, 255).astype(np.uint8))
        img = img.filter(ImageFilter.GaussianBlur(0.45 * scale))
        g = (np.asarray(img, dtype=np.float32) - 128) / 40
        grain = g / (g.std() + 1e-6)

        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        vig = np.clip(1 - 0.18 * d ** 2.2, 0, 1)

        # The finished key frame: photo + wordmark + grain + vignette.
        img = ty.composite(base, ty.WordmarkState(), scale, layout)
        lum = np.clip((img @ self.lum_w) / 255, 0, 1)[..., None]
        img = img + grain[..., None] * 7.0 * (0.35 + 2.2 * lum * (1 - lum))
        img = img * vig[..., None]
        self.key = np.clip(img / 255, 0, 1)
        self.key_lin = srgb_to_linear(self.key)
        self.key_lum = (self.key @ self.lum_w)[..., None]


def render_frame(P, f):
    k = FADE[f]
    if k >= 1:
        out = P.key
    elif k <= 0:
        out = np.zeros_like(P.key)
    else:
        kp = k ** (1 - LINGER * P.key_lum)  # highlights hold a little longer
        out = linear_to_srgb(P.key_lin * kp)
    return Image.fromarray(np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=1, choices=[1, 2])
    ap.add_argument("--version", default="v1", choices=sorted(VERSIONS))
    args = ap.parse_args()
    v = VERSIONS[args.version]
    P = Plates(args.scale, v.layout, v.base_suffix)
    out = ROOT / "build" / f"frames_{v.name}_{args.scale}x"
    out.mkdir(parents=True, exist_ok=True)
    for f in range(N_FRAMES):
        render_frame(P, f).save(out / f"{f:04d}.png")
    print(f"{N_FRAMES} frames -> {out}")


if __name__ == "__main__":
    main()
