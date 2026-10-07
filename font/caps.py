"""Widens the capitals, digits and wide symbols of the sans, without thickening their stems unevenly.

Iosevka draws them for a narrow cell, so beside the lowercase they look condensed: H has the same
counter as n, E is as wide as H, and O is only 0.63 as wide as it is tall (Inter 0.86), which makes
acronyms read as a second, condensed font.

Scaling a glyph horizontally by a factor per shape group fixed the widths but thickened the vertical
stems by the same factor, so E F L had 79 units, H and U 85, and O C G Q D 91 to 93 against 76 in the
lowercase (Bold 122 to 142 against 118): the round capitals looked bolder than the straight ones. Now
every glyph first gets one small scale (the optical correction that makes capitals a little heavier
than the lowercase), and the rest of the width goes into the counters only: x is remapped with slope 1
across each vertical stem and a larger slope between stems, with smooth ramps so curves get no kink.
Stems are the ink spans no wider than 1.4 stems that repeat at the same x on several scanlines. A glyph
with no vertical stem (A V W X Y Z) is simply scaled to the target width.
"""

import unicodedata

from fontTools.pens.boundsPen import BoundsPen

from glyphs import glyph_path, sync_bearing
from outline import flatten_contours
from spacing import _scan, is_text, stem_width

DEFAULT = 1.10
GROUPS = {
    "OCGQD": 1.20,
    "HNUM": 1.12,
    "AVWXYZKT": 1.08,
    "EFLPBRS": 1.04,
}
SIMILAR = {"Ø": "O", "Đ": "D", "Ð": "D", "Ł": "L", "Þ": "P", "Ħ": "H", "Ŧ": "T"}
SYMBOLS = "&@%$#"
STEM_FACTOR = 1.08
RAMP = 22
SCANS = (0.2, 0.35, 0.5, 0.65, 0.8)


def base_letter(ch):
    """The letter whose shape group a capital follows: Ơ and É follow O and E, Ø follows O."""
    return SIMILAR.get(ch) or unicodedata.normalize("NFD", ch)[0]


def factor_for(ch, uniform=None):
    if uniform is not None:
        return uniform
    base = base_letter(ch)
    for letters, factor in GROUPS.items():
        if base in letters:
            return factor
    return DEFAULT


def wanted(cp):
    ch = chr(cp)
    category = unicodedata.category(ch)
    return is_text(cp) and (category in ("Lu", "Sc") or "0" <= ch <= "9" or ch in SYMBOLS)


def _contours(font, name):
    return flatten_contours(glyph_path(font.getGlyphSet(), name), 10)


def stem_bands(contours, top, stem):
    """x ranges of the vertical stems of a glyph: narrow ink spans that repeat on several scanlines."""
    rows = []
    for fraction in SCANS:
        xs = _scan(contours, fraction * top)
        rows.append([(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2) if xs[i + 1] - xs[i] <= 1.4 * stem])
    bands = []
    for i, row in enumerate(rows):
        for a, b in row:
            hits = sum(any(abs(a - a2) <= 10 and abs(b - b2) <= 10 for a2, b2 in other)
                       for j, other in enumerate(rows) if j != i)
            if hits >= 1 and not any(abs(a - x) <= 10 for x, _ in bands):
                bands.append((a - 4, b + 4))
    return bands


def _smooth(t):
    return t * t * (3 - 2 * t)


def _remap(coordinates, contours, bands, target):
    """New x for every coordinate: slope 1 inside the stem bands, the rest of the width between them."""
    xs = [p[0] for c in contours for p in c]
    b0, b1 = min(xs), max(xs)
    n = int(b1 - b0) + 1

    def weight(x):
        w = 1.0
        for a, b in bands:
            w = min(w, _smooth(min(1.0, max(a - x, x - b, 0.0) / RAMP)))
        return w

    weights = [weight(b0 + i + 0.5) for i in range(n)]
    free = sum(weights)
    if free <= 1:
        scale = target / (b1 - b0)
        return [round(b0 + (x - b0) * scale) for x, _ in coordinates]
    extra = (target - (b1 - b0)) / free
    cumulative = [0.0]
    for w in weights:
        cumulative.append(cumulative[-1] + 1 + extra * w)

    def new_x(x):
        t = min(max(x - b0, 0.0), n - 1e-6)
        i = int(t)
        return b0 + cumulative[i] + (t - i) * (cumulative[i + 1] - cumulative[i])

    return [round(new_x(x)) for x, _ in coordinates]


def widen_caps(font, uniform=None):
    """Widens capitals, ASCII digits, currency signs and SYMBOLS. Returns how many glyphs were changed."""
    cmap, glyf = font.getBestCmap(), font["glyf"]
    stem = stem_width(font) * STEM_FACTOR
    moved = {}
    for cp, name in sorted(cmap.items()):
        if not wanted(cp) or name in moved:
            continue
        glyph = glyf[name]
        if glyph.isComposite() or glyph.numberOfContours == 0:
            continue
        factor = factor_for(chr(cp), uniform)
        xs = [x for x, _ in glyph.coordinates]
        lo, hi = min(xs), max(xs)
        centre, target = (lo + hi) / 2, (hi - lo) * factor
        for i, (x, y) in enumerate(glyph.coordinates):
            glyph.coordinates[i] = (round(centre + (x - centre) * STEM_FACTOR), y)
        sync_bearing(font, name)
        contours = _contours(font, name)
        top = max(p[1] for c in contours for p in c)
        new_x = _remap(glyph.coordinates, contours, stem_bands(contours, top, stem), target)
        for i, (_, y) in enumerate(glyph.coordinates):
            glyph.coordinates[i] = (new_x[i], y)
        sync_bearing(font, name)
        new_centre = (min(new_x) + max(new_x)) / 2
        moved[name] = (centre, new_centre, factor)
    glyph_set = font.getGlyphSet()
    for name in font.getGlyphOrder():
        glyph = glyf[name]
        if not glyph.isComposite() or glyph.components[0].glyphName not in moved:
            continue
        centre, new_centre, factor = moved[glyph.components[0].glyphName]
        for comp in glyph.components[1:]:
            pen = BoundsPen(glyph_set)
            glyph_set[comp.glyphName].draw(pen)
            if pen.bounds is None:
                continue
            accent_centre = comp.x + (pen.bounds[0] + pen.bounds[2]) / 2
            comp.x += round((new_centre - centre) + (factor - 1) * (accent_centre - centre))
        glyph.recalcBounds(glyf)
    return len(moved)
