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

from tuck import optical_bearings

BUCKET = 4


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


def feature_code(right, left, rules):
    lines = ["languagesystem DFLT dflt;", "languagesystem latn dflt;"]
    for k in sorted({kr for kr, _, _ in rules}):
        lines.append(f"@R{k} = [{' '.join(sorted(right[k]))}];")
    for k in sorted({kl for _, kl, _ in rules}):
        lines.append(f"@L{k} = [{' '.join(sorted(left[k]))}];")
    lines.append("feature kern {")
    lines += [f"    pos @R{kr} @L{kl} {v};" for kr, kl, v in rules]
    lines.append("} kern;")
    return "\n".join(lines)


def kern(font, **kwargs):
    """Adds class pair kerning as the font's GPOS kern feature. Returns (median gap, rule count)."""
    target, right, left, rules = plan(optical_bearings(font), **kwargs)
    addOpenTypeFeaturesFromString(font, feature_code(right, left, rules), tables=["GPOS"])
    return target, len(rules)
