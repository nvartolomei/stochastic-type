"""Contextual spacing for the monospace font.

Every glyph keeps its advance, so the grid never moves. Narrow letters (r i f l t j) still leave
more air around them than their neighbours do. Each pair of letters whose optical gap is larger than
a target is closed by nudging glyphs inside their own cells with `kern` positioning. The closure is
shared over four glyphs, the pair and one more on each side, so the air removed from a loose pair is
spread over its neighbouring gaps instead of landing on one of them (which left `bool` with tight
`bo`, loose `oo`).

Only letters and a few sentence marks take part. Digits, brackets and operators stay centred in
their cells so columns and code keep their rhythm.

A sentence mark owns the air in its own cell, so in a pair with a letter only the mark moves, by the
whole shift: a letter dragged toward a colon would leave the rest of its word. For the same reason a
letter never moves away from a neighbour that does not take part (a bracket, digit or quote).

A mark moves only toward the letter before it and only when a space, or the end of the line, follows it.
Prose ends its marks that way; code does not (`std::vector`, `file.txt`, `self.name`, `http://`), and
tucking there tore `::` apart by a quarter of a cell and let dots drift. Pairs that start with a mark are
never tucked.

Four lookups do the work, one per role of the glyph in a loose pair: first, second, the glyph before
the pair and the glyph after it. Offsets add up when a glyph has several roles. The two outer roles
are limited to ASCII and Latin-1 letters, which keeps the table small enough to avoid extension
lookups (the full letter class made the Regular's GPOS 8 times larger).
"""

import unicodedata

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString

from outline import flatten_contours
from glyphs import glyph_path
from spacing import optical_edges

SENTENCE_MARKS = ".,:;!?"
BUCKET = 24
TARGET_OFFSET = -30
SHARE = 0.6
LIMIT = 60
REACH = (0.5, 0.25)
MARK_SHARE = 0.8
MARK_LIMIT = 140
STEP = 5
FLOOR = 10
FIXED_RANGES = [(0x21, 0x7E), (0xA1, 0xBF), (0x2010, 0x205E)]
CASCADE_RANGES = [(0x41, 0x5A), (0x61, 0x7A), (0xC0, 0xD6), (0xD8, 0xF6), (0xF8, 0xFF)]


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


def quantise(value):
    return int(value // STEP) * STEP


def closure_for(gap, target, share, limit):
    """How much a pair is closed, in units, or 0 when the excess is too small to act on."""
    closure = share * (gap - target)
    if closure < 2 * FLOOR:
        return 0
    return min(closure, 2 * limit)


def fixed_glyphs(font):
    """Glyphs that stay put: punctuation, brackets, digits and symbols a letter can sit next to."""
    out = []
    for cp, name in sorted(font.getBestCmap().items()):
        if any(lo <= cp <= hi for lo, hi in FIXED_RANGES) and not eligible(cp):
            out.append(name)
    return out


def not_space_glyphs(font):
    """Every glyph a mark could be followed by in running text, code or markup: all but the spaces.

    A shorter list (ASCII, Latin-1, general punctuation) let a mark move before any other glyph, so
    `tỉ.ệ`, `x.│` and `ok:→` were tucked.
    """
    spaces = {name for cp, name in font.getBestCmap().items() if unicodedata.category(chr(cp)) == "Zs"}
    return [name for name in font.getGlyphOrder() if name not in spaces and name != ".notdef"]


def plan(bearings, marks=(), target=None, share=SHARE, limit=LIMIT, mark_share=MARK_SHARE, mark_limit=MARK_LIMIT):
    """Class pairs and shifts.

    Returns (target, right classes, left classes, rules). Classes are keyed (is mark, bucket). A rule
    is (first is mark, right bucket, second is mark, left bucket, shifts) with shifts the offsets of
    the first glyph, the second glyph, the glyph before the pair and the glyph after it.
    """
    if target is None:
        gaps = sorted(r + l for _, r in bearings.values() for l, _ in bearings.values())
        target = gaps[len(gaps) // 2] + TARGET_OFFSET
    right = {}
    left = {}
    for name, (lb, rb) in bearings.items():
        is_mark = name in marks
        right.setdefault((is_mark, int(rb // BUCKET)), []).append(name)
        left.setdefault((is_mark, int(lb // BUCKET)), []).append(name)
    rules = []
    for (m1, kr) in right:
        if m1:
            continue
        for (m2, kl) in left:
            gap = (kr + 0.5) * BUCKET + (kl + 0.5) * BUCKET
            if m2:
                d = quantise(closure_for(gap, target, mark_share, mark_limit / 2))
                shifts = (0, -d, 0, 0)
            else:
                closure = closure_for(gap, target, share, limit)
                near, far = quantise(REACH[0] * closure), quantise(REACH[1] * closure)
                shifts = (near, -near, far, -far)
            if any(shifts):
                rules.append((m1, kr, m2, kl, shifts))
    return target, right, left, rules


def class_name(side, is_mark, k):
    return f"@{side}{'M' if is_mark else ''}{k}"


def feature_code(right, left, rules, fixed, cascade, not_space):
    lines = ["languagesystem DFLT dflt;", "languagesystem latn dflt;"]
    for m, k in sorted({(m, k) for m, k, _, _, _ in rules}):
        lines.append(f"{class_name('R', m, k)} = [{' '.join(sorted(right[(m, k)]))}];")
    for m, k in sorted({(m, k) for _, _, m, k, s in rules}):
        lines.append(f"{class_name('L', m, k)} = [{' '.join(sorted(left[(m, k)]))}];")
    lines.append(f"@FIXED = [{' '.join(fixed)}];")
    lines.append(f"@LETTER = [{' '.join(cascade)}];")
    lines.append(f"@NOTSPACE = [{' '.join(not_space)}];")

    def pair(m1, kr, m2, kl):
        return class_name("R", m1, kr), class_name("L", m2, kl)

    def lookup(name, role, template, guard, mark_guard=None):
        lines.append(f"lookup {name} {{")
        used = [(m1, kr, m2, kl, s[role]) for m1, kr, m2, kl, s in rules if s[role]]
        for m1, kr, m2, kl, _ in used:
            r, l = pair(m1, kr, m2, kl)
            lines.append("    " + (mark_guard if m2 and mark_guard else guard).format(r=r, l=l))
        for m1, kr, m2, kl, v in used:
            r, l = pair(m1, kr, m2, kl)
            lines.append("    " + template.format(r=r, l=l, v=v))
        lines.append(f"}} {name};")

    lookup("TUCK_FIRST", 0, "pos {r}' <{v} 0 0 0> {l};", "ignore pos @FIXED {r}' {l};")
    lookup("TUCK_SECOND", 1, "pos {r} {l}' <{v} 0 0 0>;", "ignore pos {r} {l}' @FIXED;", "ignore pos {r} {l}' @NOTSPACE;")
    lookup("TUCK_BEFORE", 2, "pos @LETTER' <{v} 0 0 0> {r} {l};", "ignore pos @FIXED @LETTER' {r} {l};")
    lookup("TUCK_AFTER", 3, "pos {r} {l} @LETTER' <{v} 0 0 0>;", "ignore pos {r} {l} @LETTER' @FIXED;")
    lines.append("feature kern { lookup TUCK_FIRST; lookup TUCK_SECOND; lookup TUCK_BEFORE; lookup TUCK_AFTER; } kern;")
    return "\n".join(lines)


def tuck(font, **kwargs):
    """Adds the tuck rules as the font's GPOS kern feature. Returns (target gap, rule count)."""
    cmap = font.getBestCmap()
    marks = {cmap[ord(ch)] for ch in SENTENCE_MARKS if ord(ch) in cmap}
    bearings = optical_bearings(font)
    target, right, left, rules = plan(bearings, marks, **kwargs)
    cascade = sorted({name for cp, name in cmap.items()
                      if any(lo <= cp <= hi for lo, hi in CASCADE_RANGES) and name in bearings})
    code = feature_code(right, left, rules, fixed_glyphs(font), cascade, not_space_glyphs(font))
    addOpenTypeFeaturesFromString(font, code, tables=["GPOS"])
    return target, len(rules)
