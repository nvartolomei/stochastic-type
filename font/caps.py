"""Widens the capitals, digits and wide symbols of the sans.

Iosevka draws them for a narrow cell, so beside the lowercase they look condensed: H has the same
counter as n, E is as wide as H, and O is only 0.63 as wide as it is tall (Inter 0.86), which makes
acronyms read as a second, condensed font. Each glyph is scaled horizontally about its centre, by a
factor per shape group: rounds most, E F L least. Scaling also thickens the vertical stems, which
puts capitals slightly heavier than the lowercase, as optical correction wants.
"""

import unicodedata

from fontTools.pens.boundsPen import BoundsPen

from spacing import is_text

DEFAULT = 1.10
GROUPS = {
    "OCGQD": 1.20,
    "HNUM": 1.12,
    "AVWXYZKT": 1.08,
    "EFLPBRS": 1.04,
}
SYMBOLS = "&@%$#"


def factor_for(ch, uniform=None):
    if uniform is not None:
        return uniform
    for letters, factor in GROUPS.items():
        if ch in letters:
            return factor
    return DEFAULT


def widen_caps(font, uniform=None):
    """Scales capitals, ASCII digits and SYMBOLS. A glyph is scaled once, whatever it is reached through."""
    cmap, glyf = font.getBestCmap(), font["glyf"]
    scaled = {}
    for cp, name in sorted(cmap.items()):
        ch = chr(cp)
        if not is_text(cp) or name in scaled:
            continue
        if not (unicodedata.category(ch) == "Lu" or "0" <= ch <= "9" or ch in SYMBOLS):
            continue
        glyph = glyf[name]
        if glyph.isComposite() or glyph.numberOfContours == 0:
            continue
        factor = factor_for(ch, uniform)
        xs = [x for x, _ in glyph.coordinates]
        centre = (max(xs) + min(xs)) / 2
        for i, (x, y) in enumerate(glyph.coordinates):
            glyph.coordinates[i] = (round(centre + factor * (x - centre)), y)
        glyph.recalcBounds(glyf)
        scaled[name] = (centre, factor)
    glyph_set = font.getGlyphSet()
    for name in font.getGlyphOrder():
        glyph = glyf[name]
        if not glyph.isComposite() or glyph.components[0].glyphName not in scaled:
            continue
        centre, factor = scaled[glyph.components[0].glyphName]
        for comp in glyph.components[1:]:
            pen = BoundsPen(glyph_set)
            glyph_set[comp.glyphName].draw(pen)
            if pen.bounds is None:
                continue
            accent_centre = comp.x + (pen.bounds[0] + pen.bounds[2]) / 2
            comp.x += round((factor - 1) * (accent_centre - centre))
        glyph.recalcBounds(glyf)
    return len(scaled)
