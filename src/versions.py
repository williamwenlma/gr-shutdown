"""Design versions: crop + wordmark layout + output naming.

v1  photo-led: small lockup tucked into the sky band, top right.
v2  type-led: "GR II" is the hero, centred large in the sky with the subject
    below it; RICOH shrinks to a quiet tracked credit; the big II strands
    carry suit webbing.
"""
from dataclasses import dataclass
from pathlib import Path

import typography as ty

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Version:
    name: str
    crop_y0: int
    base_suffix: str
    layout: ty.Layout
    out_dir: Path
    prefix: str


V1 = Version("v1", 520, "", ty.LAYOUT, ROOT / "out", "gr2")

V2 = Version(
    "v2", 150, "_v2",
    ty.centered(ty.Layout(
        top=30.0, cap=150.0,
        ricoh_cap_ratio=0.105, ricoh_gap_ratio=0.12,
        bridge_k=(1.22, 1.17), bridge_sag=0.05,
        thread_w=1.1, glow_radius=9.0, ii_web=True, strand_dome=True,
    ), cx=320.0),
    ROOT / "out" / "v2", "gr2_v2",
)

VERSIONS = {"v1": V1, "v2": V2}
