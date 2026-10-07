"""Outline helpers shared by the build steps."""

import pathops
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.scaleUpem import scale_upem


def glyph_path(glyph_set, name):
    p = pathops.Path()
    glyph_set[name].draw(p.getPen(glyphSet=glyph_set))
    p.simplify(fix_winding=True)
    return p


def embolden(path, amount):
    """Grows stems by `amount` units; negative values thin them."""
    if amount == 0:
        return path
    stroked = pathops.Path(path)
    stroked.stroke(abs(amount), pathops.LineCap.BUTT_CAP, pathops.LineJoin.MITER_JOIN, 3)
    stroked.convertConicsToQuads()
    op = pathops.PathOp.UNION if amount > 0 else pathops.PathOp.DIFFERENCE
    return pathops.op(path, stroked, op, fix_winding=True)


def close_slits(path, radius):
    """Fills slivers narrower than 2*radius (morphological closing)."""
    if radius <= 0:
        return path
    return embolden(embolden(path, 2 * radius), -2 * radius)


def fill_traps(font, chars, radius):
    """Closes the slivers between the strokes of `chars`, like an ink trap filled in.

    Letters that pack four strokes into one cell (W w M m in the monospace) leave counters so narrow
    that rows of them shimmer at small sizes.
    """
    cmap, gs = font.getBestCmap(), font.getGlyphSet()
    for ch in chars:
        name = cmap[ord(ch)]
        pen = TTGlyphPen(None)
        close_slits(glyph_path(gs, name), radius).draw(pen)
        font["glyf"][name] = pen.glyph()


def rescale(font, factor):
    """Uniformly scales a font by `factor` while keeping 1000 units per em."""
    scale_upem(font, round(font["head"].unitsPerEm * factor))
    font["head"].unitsPerEm = 1000
