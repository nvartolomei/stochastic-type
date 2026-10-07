"""Pair kerning for the proportional font from the same optical-gap model as the monospace tucking.

Sidebearings are set per glyph (spacing.py) so every letter has the same optical bearing, which
makes every pair's optical gap equal. Where a glyph could not reach that (a floor, a hook that must
not touch its neighbour) or the depth model is off, some pairs still look looser or tighter than the
rest. Those pairs get a `kern` value that moves them toward the median gap: tighter for loose
pairs, a little looser for tight ones.

Classes are 4-unit buckets of optical bearing, fine enough that the estimate carries no visible
quantisation noise and coarse enough that the class pair table stays small.

Three kinds of explicit glyph pair sit in front of the classes, because a sum of two per-glyph
averages cannot see how two shapes face each other. The crossbars of f and t get a fixed gap. A letter
or digit followed by a period, comma, colon, semicolon, apostrophe, closing quote or hyphen is tucked
by how far its edge recedes at the height of the mark, beyond the recession the per-glyph model has
already credited: `V.` `y.` `L'` `P.` `7.` leave a hole under an arm or a bar that no class can fill,
while `n.` and `o.` stay as they were.
"""

import unicodedata

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

from outline import flatten_contours
from glyphs import glyph_path
from spacing import _scan, is_text, optical_edges, stem_width
from tuck import optical_bearings

BUCKET = 4
BAR_Y = 470
BAR_GAP_RATIO = 0.85
LEFT_BIAS = {"t": 25, "f": 25}
MARK_AFTER = ".,:;'\"\u2019\u201d-"
MARK_WINDOW = 60
MARK_DEADBAND = 20
MARK_SHARE = 1.0
MARK_LIMIT = 140
MARK_FLOOR = 10
MARK_CLEAR = 0.7
MARK_LOOSEN = 40
TWO_PART_MARKS = ":;"
CREDIT = 0.6
ROW = 20


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


def _zone(cat, contours):
    if cat in ("Ll", "Lo", "Lm"):
        return 504
    if cat in ("Lu", "Lt"):
        return 690
    ys = [p[1] for pts in contours for p in pts]
    return max(ys) - min(ys)


def mark_pairs(font, old_value, clear=None):
    """Explicit pairs of a letter or digit and the marks that follow it, tucked by local recession.

    `old_value(first, second)` is the class kerning the pair would otherwise get; it is added so that
    the explicit pair replaces the class pair without losing it.

    The colon and semicolon have a dot at x-height, level with the crossbar of t and the arms of f r y v,
    where nothing can tuck: the class kerning had pulled their nearest ink to half the usual gap. So
    for those two marks the nearest ink of every letter keeps at least `clear` times the median gap
    of the unkerned lowercase pairs, and a letter that is closer than that by nature (`t;`) is loosened.
    """
    clear = MARK_CLEAR if clear is None else clear
    cmap, gs, hmtx = font.getBestCmap(), font.getGlyphSet(), font["hmtx"]
    marks = {ch: cmap[ord(ch)] for ch in MARK_AFTER if ord(ch) in cmap}
    mark_rows, mark_left = {}, {}
    for ch, name in marks.items():
        contours = flatten_contours(glyph_path(gs, name), 10)
        ys = [p[1] for pts in contours for p in pts]
        mark_rows[ch] = [y for y in range(int(min(ys)) // ROW * ROW, int(max(ys)) + 1, ROW) if _scan(contours, y + 0.5)]
        mark_left[ch] = {y: _scan(contours, y + 0.5)[0] for y in mark_rows[ch]}
    letters = {}
    for cp, name in sorted(cmap.items()):
        cat = unicodedata.category(chr(cp))
        if not is_text(cp) or name in letters or not (cat[0] == "L" or cat == "Nd"):
            continue
        contours = flatten_contours(glyph_path(gs, name), 10)
        edges = optical_edges(contours, cat)
        if edges is None:
            continue
        right = {y: (lambda xs: xs[-1] if xs else None)(_scan(contours, y + 0.5)) for y in range(-300, 800, ROW)}
        letters[name] = (cat, contours, edges, right, hmtx[name][0])

    def nearest(name, ch):
        advance, right = letters[name][4], letters[name][3]
        gaps = [advance + mark_left[ch][y] - right[y] for y in mark_rows[ch] if right.get(y) is not None]
        return min(gaps) if gaps else None

    floors = {}
    for ch in TWO_PART_MARKS:
        if ch in marks:
            plain = sorted(g for g in (nearest(cmap[ord(c)], ch) for c in "abcdefghijklmnopqrstuvwxyz") if g is not None)
            floors[ch] = clear * plain[len(plain) // 2]
    lines = []
    for name, (cat, contours, edges, right, advance) in letters.items():
        reach, depth = edges[1], edges[3]
        clip = 0.3 * _zone(cat, contours)
        for ch, mark in marks.items():
            local = []
            for y in mark_rows[ch]:
                near = [min(clip, reach - right[yy]) for yy in range(y - MARK_WINDOW, y + MARK_WINDOW + 1, ROW)
                        if right.get(yy) is not None]
                if near:
                    local.append(min(near))
            tuck = 0
            if local:
                excess = sum(local) / len(local) - CREDIT * depth - MARK_DEADBAND
                if excess > 0:
                    tuck = -min(MARK_LIMIT, int(round(MARK_SHARE * excess / 2) * 2))
                    if -tuck < MARK_FLOOR:
                        tuck = 0
            before = old_value(name, mark)
            total = before + tuck
            if ch in floors:
                gap = nearest(name, ch)
                if gap is not None:
                    total = min(MARK_LOOSEN, max(total, int(round(floors[ch] - gap))))
            if total != before:
                lines.append(f"    pos {name} {mark} {total};")
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
    right_class = {name: k for k, names in right.items() for name in names}
    left_class = {name: k for k, names in left.items() for name in names}
    class_value = {(kr, kl): v for kr, kl, v in rules}

    def old_value(first, second):
        if first in right_class and second in left_class:
            return class_value.get((right_class[first], left_class[second]), 0)
        return 0

    code = feature_code(right, left, rules, bar_pairs(font, bar_gap) + mark_pairs(font, old_value))
    addOpenTypeFeaturesFromString(font, code, tables=["GPOS"])
    return target, len(rules)
