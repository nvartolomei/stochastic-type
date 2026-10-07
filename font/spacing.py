"""Sets the sidebearings of text glyphs from their outlines.

Quasi-proportional bases centre every letter in a near-uniform cell, which leaves
narrow letters (r, j, f, t) and punctuation floating in space meant for a wider one.
Sidebearings are recomputed from the shape, outlines are shifted to match, and
accent components follow their base glyph.
"""

import unicodedata

from outline import flatten_contours
from glyphs import glyph_path

TEXT_BLOCKS = [
    (0x20, 0x7E), (0xA0, 0xFF), (0x100, 0x24F), (0x1E00, 0x1EFF), (0x2010, 0x2027), (0x2030, 0x205E), (0x20A0, 0x20CF),
]


def is_text(cp):
    return any(a <= cp <= b for a, b in TEXT_BLOCKS) and unicodedata.category(chr(cp))[0] in "LNPS"


def _scan(contours, y):
    xs = []
    for pts in contours:
        n = len(pts)
        for i in range(n):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
    xs.sort()
    return xs


def stem_width(font, ch="l", y=230):
    """Ink width of a letter's stem at mid-height, where serifs, flags and tails do not reach."""
    name = font.getBestCmap()[ord(ch)]
    xs = _scan(flatten_contours(glyph_path(font.getGlyphSet(), name), 10), y)
    return xs[1] - xs[0]


def side_profile(contours, zone_top, samples=28):
    """Left and right ink extremes across the zone [0, zone_top]; None where there is no ink."""
    left, right = [], []
    for i in range(samples):
        y = zone_top * (i + 0.5) / samples
        xs = _scan(contours, y)
        left.append(xs[0] if xs else None)
        right.append(xs[-1] if xs else None)
    return left, right


def optical_edges(contours, cat, xheight=504, capheight=690):
    """(left ink edge, right ink edge, left depth, right depth) of a glyph in its zone.

    The depth is how far the outline recedes from its own outermost point on average, so a
    receding side (t, f, r, v, y) has a large depth and needs less sidebearing.
    """
    if cat in ("Ll", "Lo", "Lm"):
        zone = xheight
    elif cat in ("Lu", "Lt"):
        zone = capheight
    else:
        ys = [p[1] for pts in contours for p in pts]
        zone = max(ys) - min(ys)
    left, right = side_profile(contours, zone)
    inked_l = [e for e in left if e is not None]
    inked_r = [e for e in right if e is not None]
    if not inked_l or not inked_r:
        return None
    clip = 0.3 * zone
    zl, zr = min(inked_l), max(inked_r)
    dl = sum(min(clip, (e - zl) if e is not None else clip) for e in left) / len(left)
    dr = sum(min(clip, (zr - e) if e is not None else clip) for e in right) / len(right)
    return zl, zr, dl, dr


def letterspace(font, xheight=504, capheight=690, target=76, strength=0.55, floor=14, digit_sb=62, space=360,
                min_edge=24, hook_overhang=90):
    """Balanced spacing from glyph shape: straight sides get `target`, receding sides less.
    `min_edge` keeps ink on the right clear of the next glyph. On the left a descender hook may overhang
    the previous cell by up to `hook_overhang`, so a j sits by its stem and not by its tail."""
    glyf, hmtx, cmap = font["glyf"], font["hmtx"], font.getBestCmap()
    gs = font.getGlyphSet()
    shifts = {}
    digits = {}

    def place(name, left_ext, right_ext, left_sb, right_sb):
        g = glyf[name]
        dx = left_sb - left_ext
        g.coordinates.translate((dx, 0))
        g.recalcBounds(glyf)
        adv = round(left_sb + (right_ext - left_ext) + right_sb)
        lift = -hook_overhang - g.xMin
        if lift > 0:
            g.coordinates.translate((lift, 0))
            g.recalcBounds(glyf)
            dx += lift
            adv += round(lift)
        if g.xMax > adv - min_edge:
            adv = round(g.xMax + min_edge)
        hmtx[name] = (adv, round(g.xMin))
        shifts[name] = (dx, adv)

    for cp, name in sorted(cmap.items()):
        if not is_text(cp) or cp == 0x20 or name in shifts:
            continue
        g = glyf[name]
        if g.isComposite() or g.numberOfContours == 0:
            continue
        cat = unicodedata.category(chr(cp))
        contours = flatten_contours(glyph_path(gs, name), 10)
        if not contours:
            continue
        if cat == "Nd":
            xs = [p[0] for pts in contours for p in pts]
            digits[name] = (min(xs), max(xs))
            continue
        edges = optical_edges(contours, cat, xheight, capheight)
        if edges is None:
            continue
        zl, zr, dl, dr = edges
        t = target if cat in ("Ll", "Lu", "Lo", "Lm", "Lt") else target * 0.8
        s = strength if cat[0] == "L" else strength * 0.6
        place(name, zl, zr, max(floor, t - s * dl), max(floor, t - s * dr))

    if digits:
        body = max(b - a for a, b in digits.values())
        for name, (a, b) in digits.items():
            g = glyf[name]
            dx = digit_sb + (body - (b - a)) / 2 - a
            g.coordinates.translate((dx, 0))
            g.recalcBounds(glyf)
            adv = round(body + 2 * digit_sb)
            hmtx[name] = (adv, round(g.xMin))
            shifts[name] = (dx, adv)

    for name in font.getGlyphOrder():
        g = glyf[name]
        if not g.isComposite():
            continue
        base = g.components[0].glyphName
        if base in shifts:
            dx, adv = shifts[base]
            for comp in g.components[1:]:
                comp.x += round(dx)
            g.recalcBounds(glyf)
            hmtx[name] = (adv, g.xMin)

    if 0x20 in cmap and space:
        hmtx[cmap[0x20]] = (space, 0)
    return len(shifts)
