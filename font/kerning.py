"""Pair kerning for the proportional font from the same optical-gap model as the monospace tucking.

Sidebearings are set per glyph (spacing.py) so every letter has the same optical bearing, which
makes every pair's optical gap equal. Where a glyph could not reach that (a floor, a hook that must
not touch its neighbour) or the depth model is off, some pairs still look looser or tighter than the
rest. Those pairs get a `kern` value that moves them toward the median gap: tighter for loose
pairs, a little looser for tight ones.

Classes are 4-unit buckets of optical bearing, fine enough that the estimate carries no visible
quantisation noise and coarse enough that the class pair table stays small.
"""

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

from outline import flatten_contours
from restyle import glyph_path
from spacing import _scan, stem_width
from tuck import optical_bearings

BUCKET = 4
BAR_Y = 470
BAR_GAP_RATIO = 0.85
LEFT_BIAS = {"t": 25, "f": 25}


def plan(bearings, share=0.7, tighten_limit=70, loosen_limit=25, floor=8, step=2):
    gaps = sorted(r + l for _, r in bearings.values() for l, _ in bearings.values())
    target = gaps[len(gaps) // 2]
    right, left = {}, {}
    for name, (lb, rb) in bearings.items():
        right.setdefault(int(rb // BUCKET), []).append(name)
        left.setdefault(int(lb // BUCKET), []).append(name)
    rules = []
    for kr in right:
        for kl in left:
            gap = (kr + 0.5) * BUCKET + (kl + 0.5) * BUCKET
            value = -share * (gap - target)
            value = max(-tighten_limit, min(loosen_limit, value))
            value = int(round(value / step) * step)
            if abs(value) >= floor:
                rules.append((kr, kl, value))
    return target, right, left, rules


def bar_pairs(font, gap):
    """Glyph pairs of f and t that put the two crossbars `gap` units apart.

    The crossbars of f and t sit at the same height, so the gap between their ends is what the eye
    reads in `ft`, `tf`, `tt` and `ff`, whatever the optical gap of the letters says.
    """
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    extent = {}
    for ch in "ft":
        xs = _scan(flatten_contours(glyph_path(font.getGlyphSet(), cmap[ord(ch)]), 10), BAR_Y)
        extent[ch] = (xs[0], xs[-1])
    lines = []
    for a in "ft":
        for b in "ft":
            natural = hmtx[cmap[ord(a)]][0] - extent[a][1] + extent[b][0]
            lines.append(f"    pos {cmap[ord(a)]} {cmap[ord(b)]} {round(gap - natural)};")
    return lines


def feature_code(right, left, rules, extra=()):
    lines = ["languagesystem DFLT dflt;", "languagesystem latn dflt;"]
    for k in sorted({kr for kr, _, _ in rules}):
        lines.append(f"@R{k} = [{' '.join(sorted(right[k]))}];")
    for k in sorted({kl for _, kl, _ in rules}):
        lines.append(f"@L{k} = [{' '.join(sorted(left[k]))}];")
    lines.append("feature kern {")
    lines += extra
    lines += [f"    pos @R{kr} @L{kl} {v};" for kr, kl, v in rules]
    lines.append("} kern;")
    return "\n".join(lines)


def biased_bearings(font, left_bias):
    """Optical bearings with extra left bearing for glyphs whose crossbar earns less credit than the model gives.

    A crossbar fills only a seventh of the height, so the model's credit for the room it takes
    on the left makes the stem look detached from the letter before it. Raising the left bearing
    makes the pairs read as looser, which kerns the stem closer.
    """
    cmap = font.getBestCmap()
    bearings = optical_bearings(font)
    for ch, extra in left_bias.items():
        name = cmap[ord(ch)]
        lb, rb = bearings[name]
        bearings[name] = (lb + extra, rb)
    return bearings


def kern(font, bar_gap=None, left_bias=None, **kwargs):
    """Adds class pair kerning as the font's GPOS kern feature. Returns (median gap, rule count).

    The crossbars of f and t end `bar_gap` units apart in ff, ft, tf and tt, by default about one bar
    thickness, so they read as two bars and neither join nor nearly touch.
    """
    if bar_gap is None:
        bar_gap = round(BAR_GAP_RATIO * stem_width(font))
    target, right, left, rules = plan(biased_bearings(font, LEFT_BIAS if left_bias is None else left_bias), **kwargs)
    code = feature_code(right, left, rules, bar_pairs(font, bar_gap))
    addOpenTypeFeaturesFromString(font, code, tables=["GPOS"])
    return target, len(rules)
