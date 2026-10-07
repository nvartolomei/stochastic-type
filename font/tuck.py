"""Contextual spacing for the monospace font.

Every glyph keeps its advance, so the grid never moves. Narrow letters (r i f l t j) still leave
more air around them than their neighbours do. For each pair whose optical gap is larger than a
target, both glyphs are nudged toward each other inside their own cells with `kern` positioning:
one contextual lookup shifts the first glyph by looking ahead, a second shifts the second glyph by
looking behind, and the two shifts add up when a glyph takes part in two pairs.

Only letters and a few sentence marks take part. Digits, brackets and operators stay centred in
their cells so columns and code keep their rhythm.
"""

import unicodedata

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

from outline import flatten_contours
from restyle import glyph_path
from spacing import optical_edges

SENTENCE_MARKS = ".,:;!?"
BUCKET = 20


def eligible(cp):
    ch = chr(cp)
    return unicodedata.category(ch)[0] == "L" or ch in SENTENCE_MARKS


def optical_bearings(font, strength=0.6, xheight=504, capheight=690):
    """{glyph: (left, right)}: sidebearing plus a share of how far each side recedes."""
    glyf, hmtx, gs = font["glyf"], font["hmtx"], font.getGlyphSet()
    out = {}
    for cp, name in sorted(font.getBestCmap().items()):
        if name in out or not eligible(cp) or glyf[name].numberOfContours == 0 and not glyf[name].isComposite():
            continue
        cat = unicodedata.category(chr(cp))
        edges = optical_edges(flatten_contours(glyph_path(gs, name), 10), cat, xheight, capheight)
        if edges is None:
            continue
        zl, zr, dl, dr = edges
        out[name] = (zl + strength * dl, (hmtx[name][0] - zr) + strength * dr)
    return out


def shift_for(gap, target, share, limit, step=5, floor=10):
    d = share * (gap - target) / 2
    if d < floor:
        return 0
    return int(min(d, limit) // step * step)


def plan(bearings, target=None, share=0.9, limit=70):
    """Class pairs and shifts. Returns (target, left classes, right classes, rules)."""
    if target is None:
        gaps = sorted(r + l for _, r in bearings.values() for l, _ in bearings.values())
        target = gaps[len(gaps) // 2]
    right = {}
    left = {}
    for name, (lb, rb) in bearings.items():
        right.setdefault(int(rb // BUCKET), []).append(name)
        left.setdefault(int(lb // BUCKET), []).append(name)
    rules = []
    for kr, _ in right.items():
        for kl, _ in left.items():
            gap = (kr + 0.5) * BUCKET + (kl + 0.5) * BUCKET
            d = shift_for(gap, target, share, limit)
            if d:
                rules.append((kr, kl, d))
    return target, right, left, rules


def feature_code(right, left, rules):
    lines = ["languagesystem DFLT dflt;", "languagesystem latn dflt;", "languagesystem cyrl dflt;",
             "languagesystem grek dflt;"]
    used_r = sorted({kr for kr, _, _ in rules})
    used_l = sorted({kl for _, kl, _ in rules})
    for k in used_r:
        lines.append(f"@R{k} = [{' '.join(sorted(right[k]))}];")
    for k in used_l:
        lines.append(f"@L{k} = [{' '.join(sorted(left[k]))}];")
    lines.append("lookup TUCK_FIRST {")
    lines += [f"    pos @R{kr}' <{d} 0 0 0> @L{kl};" for kr, kl, d in rules]
    lines.append("} TUCK_FIRST;")
    lines.append("lookup TUCK_SECOND {")
    lines += [f"    pos @R{kr} @L{kl}' <{-d} 0 0 0>;" for kr, kl, d in rules]
    lines.append("} TUCK_SECOND;")
    lines.append("feature kern { lookup TUCK_FIRST; lookup TUCK_SECOND; } kern;")
    return "\n".join(lines)


def tuck(font, **kwargs):
    """Adds the tuck rules as the font's GPOS kern feature. Returns (target gap, rule count)."""
    target, right, left, rules = plan(optical_bearings(font), **kwargs)
    addOpenTypeFeaturesFromString(font, feature_code(right, left, rules), tables=["GPOS"])
    return target, len(rules)
