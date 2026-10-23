"""Design versions: crop + wordmark layout + output naming.

v1  photo-led: small lockup tucked into the sky band, top right.
v2  type-led: "GR II" is the hero, centred large in the sky with the subject
    below it; RICOH shrinks to a quiet tracked credit; the big II strands
    carry suit webbing.
v3  print-led, for monochrome pictorialist photographs: a Centaur roman
    lockup in warm photogravure ink, the II rubricated in brick red the way
    Arts & Crafts printers marked initials, and a hairline rule beneath like
    a plate caption. No misregistration or glow: a gravure is one ink.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import typography as ty

ROOT = Path(__file__).resolve().parents[1]
SERIF_FONT = os.environ.get("GR2_SERIF_FONT", "C:/Windows/Fonts/CENTAUR.TTF")


@dataclass
class Version:
    name: str
    crop_y0: int
    base_suffix: str
    make_layout: Callable[[], ty.Layout]  # built on use, so a missing font only fails its own version
    out_dir: Path
    prefix: str

    @property
    def layout(self):
        return self.make_layout()


V1 = Version("v1", 520, "", lambda: ty.LAYOUT, ROOT / "out", "gr2")

V2 = Version(
    "v2", 150, "_v2",
    lambda: ty.centered(ty.Layout(
        top=30.0, cap=150.0,
        ricoh_cap_ratio=0.105, ricoh_gap_ratio=0.12,
        bridge_k=(1.22, 1.17), bridge_sag=0.05,
        thread_w=1.1, glow_radius=9.0, ii_web=True, strand_dome=True,
    ), cx=320.0),
    ROOT / "out" / "v2", "gr2_v2",
)

V3 = Version(
    "v3", 0, "_v3",
    lambda: ty.left_aligned(ty.Layout(
        top=26.0, cap=52.0,
        ricoh_cap_ratio=0.20, ricoh_gap_ratio=0.42, ii_gap_ratio=0.26,
        serif_font=SERIF_FONT, ricoh_track=0.30, rule=True,
        ink=(52, 40, 33),    # warm black-brown, darker than the photo's deepest tone
        red=(150, 56, 40),   # brick rubric red
        halation=False, misregister=False,
    ), x=26.0),
    ROOT / "out" / "v3", "gr2_v3",
)

VERSIONS = {"v1": V1, "v2": V2, "v3": V3}
