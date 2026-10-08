"""Gives the braces more character: a longer middle tip and shorter arms.

Iosevka's straight brace is two arms joined to a stem by quarter bends, with a short tip in the middle.
Next to a parenthesis it differs little, and when text is small or blurry it reads as one. The middle tip
is lengthened, as a line is extended, and the arms are cut back so the bends are not carried on to the end.
Both are measured in stems.

Only the end of the tip moves: its flat nub and the points beside it go out in full, and the points before
them fade out within a fraction of the tip's length, so the curve joins the longer end smoothly and the
rest of the body stays as Iosevka drew it. (Pushing the whole middle section out, which was tried first,
straightened the diagonals into an angular waist.) The arms are cut with a vertical line across the
end, as the hooks in hooks.py are.
"""

from glyphs import sync_bearing
from hooks import _cut

AXIS = 340
BIG = 2000
TIP_HOLD, TIP_FADE = 0.15, 0.55


def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _shape(font, name, sign, tip, arm, keep_centre):
    """`sign` is -1 where the tip points left (the opening brace) and 1 where it points right."""
    glyph = font["glyf"][name]
    coords, flags = glyph.coordinates, glyph.flags
    on = [i for i in range(len(coords)) if flags[i] & 1]
    far = [i for i in on if abs(coords[i][1] - AXIS) > 100]
    stem_x = (min if sign < 0 else max)(coords[i][0] for i in far)
    tip_x = (min if sign < 0 else max)(p[0] for p in coords)
    nub = max(abs(p[1] - AXIS) for p in coords if p[0] == tip_x)
    xs = [p[0] for p in coords]
    centre = (min(xs) + max(xs)) / 2
    end = (max if sign < 0 else min)(xs)
    length = abs(stem_x - tip_x)
    for i, (x, y) in enumerate(coords):
        # The end of the tip moves in full and the points before it fade out within TIP_FADE of the tip's
        # length, so the curve joins the longer end smoothly and the rest of the body stays as drawn.
        weight = 1.0 - _smooth((abs(x - tip_x) - TIP_HOLD * length) / (TIP_FADE * length))
        if weight > 0 and abs(y - AXIS) <= nub + 12:
            coords[i] = (round(x + sign * tip * weight), y)
    sync_bearing(font, name)
    cut = end + sign * arm  # the arms end `arm` units nearer the stem
    box = (cut, -BIG, BIG, BIG) if sign < 0 else (-BIG, -BIG, cut, BIG)
    if arm:
        _cut(font, name, box)
    if keep_centre:
        glyph = font["glyf"][name]
        xs = [p[0] for p in glyph.coordinates]
        glyph.coordinates.translate((round(centre - (min(xs) + max(xs)) / 2), 0))
        sync_bearing(font, name)


def shape_braces(font, stem, tip=0.5, arm=0.6, keep_centre=False):
    """Pushes the middle tip of { and } out by `tip` stems and cuts the arms back by `arm` stems.

    With `keep_centre` the ink stays centred where it was (for the monospace, whose advance is fixed);
    otherwise the caller respaces the glyphs.
    """
    cmap = font.getBestCmap()
    for ch, sign in (("{", -1), ("}", 1)):
        _shape(font, cmap[ord(ch)], sign, round(tip * stem), round(arm * stem), keep_centre)
