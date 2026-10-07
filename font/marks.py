"""Lightens the dots and commas of sentence marks.

Iosevka sizes its dots against its own stem, so with the thinner stem of this family the dot of a
period is twice as wide as a stroke and the semicolon, a dot over a comma, reads as the heaviest
thing on the line. The dots and comma heads of the sentence marks are scaled to a multiple of the
stem. Each contour is scaled about the centre of its head, so dots keep their place on the
baseline and x-height and commas keep their hang. The colon and semicolon are composites of a period
or comma and U+A78F, the dot at x-height. That glyph has no codepoint in the subset, so it is found
through the components of the composites; scaling only the glyphs the cmap names left the top dot of
`:` and `;` 25 percent larger than the period.
"""

from fontTools.pens.boundsPen import BoundsPen

DOT_RATIO = 1.6
MARKS = ".,:;!?¡¿…‥‼⁇⁈⁉‽"


def _contours(glyph):
    start = 0
    for end in glyph.endPtsOfContours:
        yield start, end + 1
        start = end + 1


def dot_size(font):
    gs = font.getGlyphSet()
    bp = BoundsPen(gs)
    gs[font.getBestCmap()[ord(".")]].draw(bp)
    return bp.bounds[2] - bp.bounds[0]


def lighten_marks(font, stem, ratio=None):
    """Scales dot and comma contours so that a dot is `ratio` stems wide.

    Returns the scale used (1 when the dots are already light enough).
    """
    ratio = DOT_RATIO if ratio is None else ratio
    dot = dot_size(font)
    scale = ratio * stem / dot
    if scale >= 1:
        return 1.0
    glyf, cmap = font["glyf"], font.getBestCmap()
    names = []
    for ch in MARKS:
        name = cmap.get(ord(ch))
        if name is None:
            continue
        glyph = glyf[name]
        if glyph.isComposite():
            names += [c.glyphName for c in glyph.components if not glyf[c.glyphName].isComposite()]
        else:
            names.append(name)
    done = set()
    for name in names:
        glyph = glyf[name]
        if name in done or glyph.numberOfContours == 0:
            continue
        done.add(name)
        coords = glyph.coordinates
        for lo, hi in _contours(glyph):
            pts = [coords[i] for i in range(lo, hi)]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            width = max(xs) - min(xs)
            if not 0.8 * dot <= width <= 1.25 * dot:
                continue
            cx, cy = (max(xs) + min(xs)) / 2, max(ys) - width / 2
            for i in range(lo, hi):
                x, y = coords[i]
                coords[i] = (round(cx + scale * (x - cx)), round(cy + scale * (y - cy)))
        glyph.recalcBounds(glyf)
    return scale
