"""Gives the hooks of t, f and j the length of l's tail, shortens the crossbars to match and the arm of the sans r.

Iosevka's flat hooks run as far as the crossbar's arm (the foot of t and the top hook of f are as long
as their arms), while the tail of l and the hook of j are about half of that. With all four ending in
the same flat L-turn they read as one family only if they are equally long, so the longer ones are
cut back to l's reach. The flat-hook variants also draw longer crossbars than the round ones (the bar
of t came out wider than an n in the monospace), so the arms of both bars are cut to a multiple of
the same reach. Every cut is a vertical line across a flat end, so no curve is touched.

The r is Iosevka's flat-top one, whose arm is a rounded corner into a flat run that ends in a curl, the
same gesture as the top of f. In the sans the arm is shortened to a fraction of the reach of the shoulder
of n by taking a slice out of the middle of the flat run (the curl at the tip stays whole); the monospace
keeps it whole, because a shorter r looks small in a cell where every other letter fills its width.

The flat-hook t also loses the overshoot the round hook had: its foot sits on the baseline while the
tail of l and the round letters go 8 units below it, so the t looks lifted. Its foot is lowered to
l's bottom. The long flat bases of a b d u and of the capitals U and G stay on the baseline: overshoot
compensates for curves, and a flat edge 250 to 300 units long that sits 8 below the stems of n h i x z
H E steps visibly in `und`, `Hand` and `HUG` at heading sizes.
"""

import pathops
from fontTools.pens.ttGlyphPen import TTGlyphPen

from outline import flatten_contours
from glyphs import glyph_path, sync_bearing
from spacing import _scan

STEM_Y = 250
FOOT_TOP = 220
BAR_ARMS = (1.0, 1.3)
MONO_BAR_ARMS = (0.72, 1.0)
BAR_BAND = (380, 515)
FOOT_SOLID, FOOT_FADE = 90, 220
ARM_RATIO = 0.72
MONO_ARM_RATIO = None


def _contours(font, name):
    return flatten_contours(glyph_path(font.getGlyphSet(), name), 10)


def tail_reach(font, ch="l"):
    """How far l's tail runs past its stem."""
    contours = _contours(font, font.getBestCmap()[ord(ch)])
    stem_right = _scan(contours, STEM_Y)[1]
    foot = [p[0] for c in contours for p in c if p[1] < FOOT_TOP and p[0] > stem_right + 2]
    return max(foot) - stem_right


def _cut(font, name, box):
    """Removes the rectangle (left, bottom, right, top) from a glyph."""
    left, bottom, right, top = box
    rect = pathops.Path()
    pen = rect.getPen()
    pen.moveTo((left, bottom))
    pen.lineTo((right, bottom))
    pen.lineTo((right, top))
    pen.lineTo((left, top))
    pen.closePath()
    trimmed = pathops.op(glyph_path(font.getGlyphSet(), name), rect, pathops.PathOp.DIFFERENCE, fix_winding=True)
    out = TTGlyphPen(None)
    trimmed.draw(out)
    font["glyf"][name] = out.glyph()
    sync_bearing(font, name)


def _bottom(font, name):
    return glyph_path(font.getGlyphSet(), name).bounds[1]


def lower_foot(font, name, dy):
    """Moves the bottom of a glyph by dy, fading out between FOOT_SOLID and FOOT_FADE so the stem keeps its shape."""
    glyph = font["glyf"][name]
    for i, (x, y) in enumerate(glyph.coordinates):
        if y < FOOT_FADE:
            share = 1.0 if y <= FOOT_SOLID else (FOOT_FADE - y) / (FOOT_FADE - FOOT_SOLID)
            glyph.coordinates[i] = (x, round(y + dy * share))
    sync_bearing(font, name)


def _vscan(contours, x):
    """Heights at which the outline crosses the vertical line at x, sorted."""
    ys = []
    for pts in contours:
        for i, (x0, y0) in enumerate(pts):
            x1, y1 = pts[(i + 1) % len(pts)]
            if (x0 <= x < x1) or (x1 <= x < x0):
                ys.append(y0 + (x - x0) * (y1 - y0) / (x1 - x0))
    return sorted(ys)


def shorten_r(font, ratio):
    """Shortens the arm of r to `ratio` times the reach of the shoulder of n.

    A slice is taken out of the middle of the arm's flat run and the end is moved back against the
    rest, so the curl at the tip keeps its shape. Cutting the end instead left a slanted stub.
    """
    cmap = font.getBestCmap()
    n = _contours(font, cmap[ord("n")])
    n_reach = max(p[0] for c in n for p in c if p[1] > 400) - _scan(n, STEM_Y)[1]
    name = cmap[ord("r")]
    r = _contours(font, name)
    stem_right = _scan(r, STEM_Y)[1]
    tip = max(p[0] for c in r for p in c if p[1] > 300)
    excess = (tip - stem_right) - ratio * n_reach
    if excess < 2:
        return
    top = max(p[1] for c in r for p in c if p[0] > stem_right + 2)
    flat = [x for x in range(int(stem_right) + 2, int(tip), 2) if _vscan(r, x)[-1] >= top - 1.5]
    if not flat:
        return
    cut_x = (min(flat) + max(flat)) / 2
    shift = min(excess, 0.8 * (max(flat) - min(flat)))
    glyph = font["glyf"][name]
    for i, (x, y) in enumerate(glyph.coordinates):
        if x > cut_x:
            glyph.coordinates[i] = (round(x - shift), y)
    sync_bearing(font, name)


def match_hooks(font, arms=BAR_ARMS, r_arm=ARM_RATIO, margin=2):
    """Cuts the foot of t, the top hook of f and the hook of j back to l's reach, and the crossbar arms of
    t and f to `arms` (left, right) times that reach, and the arm of r to `r_arm` times the reach of the
    shoulder of n (not at all when None). Returns the reach used."""
    reach = tail_reach(font)
    cmap = font.getBestCmap()
    big = 2000

    t = cmap[ord("t")]
    stem_right = _scan(_contours(font, t), STEM_Y)[1]
    if max(p[0] for c in _contours(font, t) for p in c if p[1] < FOOT_TOP) - stem_right > reach + margin:
        _cut(font, t, (stem_right + reach, -big, big, 300))

    f = cmap[ord("f")]
    stem_right = _scan(_contours(font, f), STEM_Y)[1]
    if max(p[0] for c in _contours(font, f) for p in c if p[1] > 520) - stem_right > reach + margin:
        _cut(font, f, (stem_right + reach, 520, big, big))

    for ch in "tf":
        name = cmap[ord(ch)]
        stem_left, stem_right = _scan(_contours(font, name), STEM_Y)[:2]
        bottom, top = BAR_BAND
        _cut(font, name, (-big, bottom, stem_left - reach * arms[0], top))
        _cut(font, name, (stem_right + reach * arms[1], bottom, big, top))

    floor = _bottom(font, cmap[ord("l")])
    for ch in "t":
        name = cmap[ord(ch)]
        sink = floor - _bottom(font, name)
        if sink < -1:
            lower_foot(font, name, sink)

    j = cmap[ord("j")]
    stem_left = _scan(_contours(font, j), STEM_Y)[-2]
    if stem_left - min(p[0] for c in _contours(font, j) for p in c if p[1] < 0) > reach + margin:
        _cut(font, j, (-big, -big, stem_left - reach, 0))
    if r_arm:
        shorten_r(font, r_arm)
    return reach
