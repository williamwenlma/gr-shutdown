# gr2anime

Turns a portrait photo into a 1.2-second power-off animation styled after the Ricoh GR II's
4:3 screen: the photo holds with a "RICOH GR II" lockup in the sky, then fades to black.
Everything, including the wordmark, is drawn in code; no image editor is involved.

<!-- Add a demo GIF here, rendered from a photo you own. -->

## Pipeline

```
photo ─► prepare.py ─► typography.py ─► animate.py ─► export.py
         crop + grade   wordmark layers   6 frames      GIF / MP4 / stills / SVG
```

| Stage | File | What it does |
|---|---|---|
| 1 | `src/prepare.py` | Crops the portrait to a 4:3 window that leaves a band of sky for the type, removes coarse grain with a median pass, resizes to 640x480 and 1280x960, and applies a gentle film grade (navy shadows, warm highlights). |
| 2 | `src/typography.py` | Builds the lockup. "RICOH" is tracked to the width of "GR"; the numeral II is two hanging web strands that flare from hairline threads into letter stems, bridged by a sagging strand. Every animatable property lives in one `WordmarkState` dataclass. |
| 3 | `src/animate.py` | Renders 6 frames x 200 ms: two held frames, then a fade to black. |
| 4 | `src/export.py` | Encodes the frames into GIFs (play-once master and looping copies), an H.264 preview and stills, and writes the wordmark as an editable SVG. |

`src/versions.py` defines two designs that share the pipeline:
- **v1, photo-led:** a small lockup tucked into the sky, top right.
- **v2, type-led:** "GR II" is the hero, centred and large; RICOH becomes a quiet credit,
  and the big II strands carry suit-style webbing.

## Details worth reading in the code

- **The fade is computed in linear light,** so equal steps read as even dimming on screen
  instead of a sudden drop. Highlights fade slightly later than the rest
  (`k ** (1 - LINGER * luminance)`), the way a screen loses its light.
- **Type is drawn at 4x and box-downsampled,** which gives clean anti-aliasing at both
  output sizes.
- **Print-style misregistration:** each colour plate of the type is offset by a fraction
  of a pixel (red right, blue left) so the lockup sits in the image rather than on top of it.
- **One static grain plate** for every frame, so held frames are identical and the GIF only
  stores what changes. Grain strength follows luminance, strongest in the midtones.
- **The SVG is built from the font's real glyph outlines** with fontTools
  (`instantiateVariableFont` at weights 700 and 600), so it matches the raster lockup.
- **GIFs use one palette generated from all frames,** with no dithering and only the
  changed rectangle stored per frame, so the fade has no dither noise and the file stays small.

## Run

Requires Python 3.10+, ffmpeg on `PATH`, and the Bahnschrift variable font (ships with
Windows; set `GR2_FONT` to its path elsewhere).

```bash
pip install -r requirements.txt
cp /path/to/your/photo.png assets/raw/source.png   # or set GR2_SOURCE
python src/export.py        # both versions -> out/ and out/v2/
python src/export.py v2     # one version
```

The crop offsets in `src/versions.py` (`crop_y0`) are tuned per photo. To find a good one,
render a few candidates and compare:

```bash
python src/prepare.py 400 520 640   # writes assets/prepared/base_640x480_y<N>.png
```

## Notes

No images are included: bring a photo you have the rights to use. This is an
independent fan project, not affiliated with or endorsed by Ricoh; "RICOH" and "GR" are
Ricoh's trademarks.
