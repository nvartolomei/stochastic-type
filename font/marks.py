"""Lightens the dots and commas of sentence marks.

Iosevka sizes its dots against its own stem, so with the thinner stem of this family the dot of a
period is twice as wide as a stroke and the semicolon, a dot over a comma, reads as the heaviest
thing on the line. The dots and comma heads of the sentence marks are scaled to a multiple of the
target stem. Each contour is scaled about the centre of its head, so dots keep their place on the
baseline and x-height and commas keep their hang. The colon and semicolon are composites of a period
or comma and U+A78F, the dot at x-height, so that glyph is scaled too.
"""

from fontTools.pens.boundsPen import BoundsPen

DOT_RATIO = 1.6
MARKS = ".,!?¡¿…‥‼⁇⁈⁉‽\ua78f"


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


def lighten_marks(font, target_stem, base_stem, ratio=None):
    """Scales dot and comma contours so that, after the stem change, a dot is `ratio` stems wide.

    Returns the scale used (1 when the dots are already light enough).
    """
    ratio = DOT_RATIO if ratio is None else ratio
    delta = target_stem - base_stem
    dot = dot_size(font)
    scale = (ratio * target_stem - delta) / dot
    if scale >= 1:
        return 1.0
    glyf, cmap = font["glyf"], font.getBestCmap()
    done = set()
    for ch in MARKS:
        name = cmap.get(ord(ch))
        if name is None or name in done or glyf[name].isComposite() or glyf[name].numberOfContours == 0:
            continue
        done.add(name)
        glyph = glyf[name]
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
