"""Contextual spacing for the monospace font.

Every glyph keeps its advance, so the grid never moves. Narrow letters (r i f l t j) still leave
more air around them than their neighbours do. For each pair whose optical gap is larger than a
target, both glyphs are nudged toward each other inside their own cells with `kern` positioning:
one contextual lookup shifts the first glyph by looking ahead, a second shifts the second glyph by
looking behind, and the two shifts add up when a glyph takes part in two pairs.

Only letters and a few sentence marks take part. Digits, brackets and operators stay centred in
their cells so columns and code keep their rhythm.

A sentence mark owns the air in its own cell, so in a pair with a letter only the mark moves, by the
whole shift: a letter dragged toward a colon would leave the rest of its word. For the same reason a
letter never moves away from a neighbour that does not take part (a bracket, digit or quote).
"""

import unicodedata

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

from outline import flatten_contours
from restyle import glyph_path
from spacing import optical_edges

SENTENCE_MARKS = ".,:;!?"
BUCKET = 20
MARK_LIMIT = 90
FIXED_RANGES = [(0x21, 0x7E), (0xA1, 0xBF), (0x2010, 0x205E)]


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


def fixed_glyphs(font):
    """Glyphs that stay put: punctuation, brackets, digits and symbols a letter can sit next to."""
    out = []
    for cp, name in sorted(font.getBestCmap().items()):
        if any(lo <= cp <= hi for lo, hi in FIXED_RANGES) and not eligible(cp):
            out.append(name)
    return out


def plan(bearings, marks=(), target=None, share=0.9, limit=70):
    """Class pairs and shifts.

    Returns (target, right classes, left classes, rules). Classes are keyed (is mark, bucket) and a
    rule is (first is mark, right bucket, second is mark, left bucket, first shift, second shift).
    """
    if target is None:
        gaps = sorted(r + l for _, r in bearings.values() for l, _ in bearings.values())
        target = gaps[len(gaps) // 2]
    right = {}
    left = {}
    for name, (lb, rb) in bearings.items():
        is_mark = name in marks
        right.setdefault((is_mark, int(rb // BUCKET)), []).append(name)
        left.setdefault((is_mark, int(lb // BUCKET)), []).append(name)
    rules = []
    for (m1, kr) in right:
        for (m2, kl) in left:
            gap = (kr + 0.5) * BUCKET + (kl + 0.5) * BUCKET
            if m1 != m2:
                d = shift_for(gap, target, share * 2, MARK_LIMIT)
                first, second = (d, 0) if m1 else (0, -d)
            else:
                d = shift_for(gap, target, share, limit)
                first, second = d, -d
            if first or second:
                rules.append((m1, kr, m2, kl, first, second))
    return target, right, left, rules


def class_name(side, is_mark, k):
    return f"@{side}{'M' if is_mark else ''}{k}"


def feature_code(right, left, rules, fixed):
    lines = ["languagesystem DFLT dflt;", "languagesystem latn dflt;"]
    for m, k in sorted({(m, k) for m, k, _, _, f, _ in rules if f}):
        lines.append(f"{class_name('R', m, k)} = [{' '.join(sorted(right[(m, k)]))}];")
    for m, k in sorted({(m, k) for _, _, m, k, _, sec in rules if sec}):
        lines.append(f"{class_name('L', m, k)} = [{' '.join(sorted(left[(m, k)]))}];")
    lines.append(f"@FIXED = [{' '.join(fixed)}];")
    first_rules = [(m1, kr, m2, kl, f) for m1, kr, m2, kl, f, _ in rules if f]
    second_rules = [(m1, kr, m2, kl, sec) for m1, kr, m2, kl, _, sec in rules if sec]
    lines.append("lookup TUCK_FIRST {")
    for m1, kr, m2, kl, f in first_rules:
        lines.append(f"    ignore pos @FIXED {class_name('R', m1, kr)}' {class_name('L', m2, kl)};")
    for m1, kr, m2, kl, f in first_rules:
        lines.append(f"    pos {class_name('R', m1, kr)}' <{f} 0 0 0> {class_name('L', m2, kl)};")
    lines.append("} TUCK_FIRST;")
    lines.append("lookup TUCK_SECOND {")
    for m1, kr, m2, kl, sec in second_rules:
        lines.append(f"    ignore pos {class_name('R', m1, kr)} {class_name('L', m2, kl)}' @FIXED;")
    for m1, kr, m2, kl, sec in second_rules:
        lines.append(f"    pos {class_name('R', m1, kr)} {class_name('L', m2, kl)}' <{sec} 0 0 0>;")
    lines.append("} TUCK_SECOND;")
    lines.append("feature kern { lookup TUCK_FIRST; lookup TUCK_SECOND; } kern;")
    return "\n".join(lines)


def tuck(font, **kwargs):
    """Adds the tuck rules as the font's GPOS kern feature. Returns (target gap, rule count)."""
    cmap = font.getBestCmap()
    marks = {cmap[ord(ch)] for ch in SENTENCE_MARKS if ord(ch) in cmap}
    target, right, left, rules = plan(optical_bearings(font), marks, **kwargs)
    addOpenTypeFeaturesFromString(font, feature_code(right, left, rules, fixed_glyphs(font)), tables=["GPOS"])
    return target, len(rules)
