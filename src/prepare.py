"""Stage 1: crop the portrait source to the GR II's 4:3 screen and regrade it.

Crop A ("skyline band"): full source width, 4:3 window placed so a strip of
dusk sky stays at the top for the wordmark.
"""
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
# Bring your own portrait photo; no image ships with the repo.
SRC = Path(os.environ.get("GR2_SOURCE", ROOT / "assets" / "raw" / "source.png"))
OUT_DIR = ROOT / "assets" / "prepared"

SIZES = {"1x": (640, 480), "2x": (1280, 960)}
CROP_Y0 = 520  # top of the 4:3 window in source pixels (crop A)


def crop_4x3(im, y0):
    w = im.width
    h = round(w * 3 / 4)
    y0 = max(0, min(y0, im.height - h))
    return im.crop((0, y0, w, y0 + h))


def grade(arr):
    """Gentle film grade: lift blacks slightly toward navy, warm highlights."""
    a = arr.astype(np.float32) / 255.0
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    shadow = np.clip(1.0 - lum * 2.2, 0, 1)[..., None]
    a = a + shadow * np.array([-0.004, 0.004, 0.018], dtype=np.float32)
    high = np.clip(lum * 1.6 - 0.7, 0, 1)[..., None]
    a = a + high * np.array([0.012, 0.004, -0.010], dtype=np.float32)
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def prepare(y0=CROP_Y0, suffix=""):
    if not SRC.exists():
        sys.exit(f"source image not found: {SRC}\n"
                 "put a photo at assets/raw/source.png or set GR2_SOURCE")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    src = Image.open(SRC).convert("RGB")
    crop = crop_4x3(src, y0)
    # Light median pass knocks back the original's coarse grain before the
    # downscale; fresh grain sized for the screen is added at animation time.
    crop = crop.filter(ImageFilter.MedianFilter(3))
    outs = {}
    for tag, size in SIZES.items():
        im = crop.resize(size, Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=45, threshold=2))
        im = Image.fromarray(grade(np.asarray(im)))
        path = OUT_DIR / f"base_{size[0]}x{size[1]}{suffix}.png"
        im.save(path)
        outs[tag] = path
    return outs


if __name__ == "__main__":
    if len(sys.argv) > 1:  # crop exploration: python prepare.py 560 640 720
        for y in map(int, sys.argv[1:]):
            print(prepare(y, suffix=f"_y{y}")["1x"])
    else:
        print(prepare())
