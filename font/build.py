#!/usr/bin/env python3
"""Turns the Iosevka base into Stochastic Sans.

    python font/build.py BASE.ttf OUT.ttf --weight Regular|Bold [--mono]

Subset to the target codepoints, scale to the target x-height, thicken or thin to the target
stem, push bowls toward squircles (squarify.py), fill slivers, snap near-axis lines, respace
(spacing.py) and add pair kerning (kerning.py) or, for the monospace build, contextual tucking
(tuck.py), then rename and set line metrics.
"""

import argparse
import os
import sys
from array import array
from pathlib import Path

from fontTools import subset
from fontTools.pens.boundsPen import BoundsPen
from fontTools.misc.timeTools import epoch_diff
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).parent))
from charset import target_codepoints  # noqa: E402
from restyle import rescale, restyle_font  # noqa: E402
from spacing import letterspace, stem_width  # noqa: E402
from kerning import kern  # noqa: E402
from tuck import tuck  # noqa: E402

FAMILY = "Stochastic Sans"
MONO_FAMILY = "Stochastic Mono"
VERSION = "0.3"
WEIGHTS = {"Regular": 400, "Bold": 700}

TARGET_XHEIGHT = 504
TARGET_STEM = {"Regular": 76, "Bold": 118}
STYLE = dict(squircle_n=3.2)
CLOSE_RADIUS = 7
SPACING = dict(target=80, strength=0.6)
ASCENDER, DESCENDER = 920, -280
# Builds are reproducible: font timestamps come from SOURCE_DATE_EPOCH, or this fixed release date.
RELEASE_EPOCH = 1790000000
MONO_FILL = dict(fill_chars="WwMm", fill_close=22)


def measure(font, ch):
    gs = font.getGlyphSet()
    bp = BoundsPen(gs)
    gs[font.getBestCmap()[ord(ch)]].draw(bp)
    return bp.bounds


def subset_to(font, unicodes):
    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.glyph_names = True
    opts.notdef_outline = True
    opts.hinting = False
    opts.name_IDs = ["*"]
    opts.drop_tables += ["DSIG", "FFTM"]
    s = subset.Subsetter(opts)
    s.populate(unicodes=unicodes)
    s.subset(font)


def set_metrics(font):
    """One line box on every platform: 1.2 em, with the Windows clip area covering all glyphs."""
    glyf = font["glyf"]
    drawn = [glyf[n] for n in glyf.keys() if glyf[n].numberOfContours]
    top = max((g.yMax for g in drawn), default=ASCENDER)
    bottom = min((g.yMin for g in drawn), default=DESCENDER)
    os2, hhea = font["OS/2"], font["hhea"]
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = ASCENDER, DESCENDER, 0
    hhea.ascent, hhea.descent, hhea.lineGap = ASCENDER, DESCENDER, 0
    os2.usWinAscent, os2.usWinDescent = max(top, ASCENDER), max(-bottom, -DESCENDER)
    os2.fsSelection |= 1 << 7


def finish(font):
    for tag in ("DSIG", "fpgm", "prep", "cvt "):
        if tag in font:
            del font[tag]
    font["head"].fontRevision = float(VERSION)
    stamp = int(os.environ.get("SOURCE_DATE_EPOCH", RELEASE_EPOCH)) - epoch_diff
    font["head"].created = font["head"].modified = stamp
    font.recalcTimestamp = False
    glyf = font["glyf"]
    for n in font.getGlyphOrder():
        g = glyf[n]
        if g.numberOfContours > 0:
            # Glyphs kept as the base drew them carry its per-point overlap bits, which browser
            # font sanitizers reject; only the on-curve bit is meaningful here.
            g.flags = array("B", [f & 0x01 for f in g.flags])
        g.recalcBounds(glyf)
        adv, _ = font["hmtx"][n]
        font["hmtx"][n] = (adv, g.xMin if g.numberOfContours else 0)
    if "gasp" in font:
        font["gasp"].gaspRange = {0xFFFF: 0x000F}
    set_metrics(font)


def rename(font, weight, family=FAMILY):
    name = font["name"]
    copyright_ = name.getDebugName(0)
    name.names = []
    ps = f"{family.replace(' ', '')}-{weight}"
    records = {
        0: copyright_ + " Modified version by the iamai project.",
        1: family,
        2: weight,
        3: f"{VERSION};{ps}",
        4: f"{family} {weight}",
        5: f"Version {VERSION}",
        6: ps,
        13: "Licensed under the SIL Open Font License, Version 1.1.",
        14: "https://openfontlicense.org",
        16: family,
        17: weight,
    }
    for nid, text in records.items():
        for plat, enc, lang in ((3, 1, 0x409), (1, 0, 0)):
            name.setName(text, nid, plat, enc, lang)
    font["OS/2"].usWeightClass = WEIGHTS[weight]


def build(src, out, weight, mono=False):
    """The proportional build is respaced; the monospace build keeps its fixed cell and gets contextual tucking."""
    font = TTFont(src)
    subset_to(font, target_codepoints())
    rescale(font, TARGET_XHEIGHT / measure(font, "x")[3])
    respaced = 0 if mono else letterspace(font, **SPACING)
    base_stem = stem_width(font)
    cfg = dict(embolden=TARGET_STEM[weight] - base_stem, close=CLOSE_RADIUS, style=STYLE,
               **(MONO_FILL if mono else {}))
    log = []
    restyle_font(font, cfg, log)
    finish(font)
    if mono:
        tuck(font)
    else:
        kern(font)
    rename(font, weight, MONO_FAMILY if mono else FAMILY)
    font.save(out)
    return base_stem, respaced, log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("--weight", default="Regular", choices=WEIGHTS)
    ap.add_argument("--mono", action="store_true", help="monospace build: keep the base's advances")
    args = ap.parse_args()
    stem, respaced, log = build(args.base, args.out, args.weight, args.mono)
    print(f"{args.out}: base stem {stem:.0f}, {respaced} glyphs respaced, {len(log)} area fallbacks")


if __name__ == "__main__":
    main()
