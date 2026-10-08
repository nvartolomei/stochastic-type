"""Outline helpers shared by the build steps."""

import pathops
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
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


def sync_bearing(font, name):
    """Stores the left sidebearing of a simple glyph as its xMin, after its coordinates were edited.

    The glyph set draws an outline shifted so that xMin equals the stored left sidebearing. Scanning a
    glyph through it after a raw edit, without this, measures the wrong frame: the spacing step then
    placed capitals 8 to 45 units off-centre and shifted t and f by 33.
    """
    glyph = font["glyf"][name]
    if glyph.numberOfContours == 0:
        return
    glyph.recalcBounds(font["glyf"])
    advance, _ = font["hmtx"][name]
    font["hmtx"][name] = (advance, glyph.xMin)


def _ink(glyph_set, name):
    pen = BoundsPen(glyph_set)
    glyph_set[name].draw(pen)
    return pen.bounds


def is_accented(glyph_set, glyph):
    """True for a composite whose other components sit over its first one: a letter with an accent.

    The test is that the centre of every other component lies within the ink of the first. Parts set side
    by side (the two commas of „, the N and o of №, the I and J of Ĳ, the D and z of Ǆ) fail it.
    """
    first = glyph.components[0]
    base = _ink(glyph_set, first.glyphName)
    if base is None:
        return True
    low, high = base[0] + first.x, base[2] + first.x
    for comp in glyph.components[1:]:
        if getattr(comp, "transform", [[1, 0], [0, 1]]) != [[1, 0], [0, 1]]:
            return False
        ink = _ink(glyph_set, comp.glyphName)
        if ink is not None and not low <= (ink[0] + ink[2]) / 2 + comp.x <= high:
            return False
    return True


def decompose_side_by_side(font):
    """Turns composites built from parts side by side into plain glyphs; returns their names.

    Spacing gives a composite the advance of its first component, which is right for an accent and wrong
    for „ « Ĳ Ǆ ₨ № Ⅲ, whose ink then ran past the advance (up to 1100 units). The base glyph is also
    edited later (capitals are widened), which would move the other parts of such a glyph against it.
    As plain glyphs they are spaced from their own outline, or left as Iosevka drew them when they are
    not text.
    """
    glyf, gs = font["glyf"], font.getGlyphSet()
    done = []
    for name in font.getGlyphOrder():
        glyph = glyf[name]
        if not glyph.isComposite() or len(glyph.components) < 2:
            continue
        sync_bearing(font, name)
        if is_accented(gs, glyph):
            continue
        recording = DecomposingRecordingPen(gs)
        gs[name].draw(recording)
        pen = TTGlyphPen(None)
        recording.replay(pen)
        glyf[name] = pen.glyph()
        sync_bearing(font, name)
        done.append(name)
    return done


def rescale(font, factor):
    """Uniformly scales a font by `factor` while keeping 1000 units per em."""
    scale_upem(font, round(font["head"].unitsPerEm * factor))
    font["head"].unitsPerEm = 1000
