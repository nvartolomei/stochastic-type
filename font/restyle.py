"""Restyles glyph outlines in place, for any TrueType base font.

Composite glyphs are left alone: their components are restyled and keep their
extents, so offsets, kerning and mark positioning of the base stay valid.
"""

import unicodedata

import pathops
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.scaleUpem import scale_upem

from charset import is_exact
from squarify import soften

FIT_X_MIN_EXTENT = 250
FIT_Y_MIN_EXTENT = 300

# Brackets keep the base's own curves. They are long, gentle arcs whose tangent sits near 45
# degrees for most of their length, so the squircle push would flare their ends like bowls.
UNPUSHED_CATEGORIES = {"Ps", "Pe"}


def glyph_path(glyph_set, name):
    p = pathops.Path()
    glyph_set[name].draw(p.getPen(glyphSet=glyph_set))
    p.simplify(fix_winding=True)
    return p


def embolden(path, amount):
    """Grows stems by `amount` units; negative values thin them."""
    if amount == 0:
        return path
    stroked = pathops.Path(path)
    stroked.stroke(abs(amount), pathops.LineCap.BUTT_CAP, pathops.LineJoin.MITER_JOIN, 3)
    stroked.convertConicsToQuads()
    op = pathops.PathOp.UNION if amount > 0 else pathops.PathOp.DIFFERENCE
    return pathops.op(path, stroked, op, fix_winding=True)


def close_slits(path, radius):
    """Fills slivers narrower than 2*radius (morphological closing)."""
    if radius <= 0:
        return path
    return embolden(embolden(path, 2 * radius), -2 * radius)


def fit_axis(lo, hi, orig_lo, orig_hi, min_extent):
    """Scale/offset mapping the new extent back onto the original one when the
    original extent is large enough to be an alignment-bearing feature."""
    if hi - lo < 1e-6:
        return 1.0, 0.0
    if orig_hi - orig_lo >= min_extent:
        s = (orig_hi - orig_lo) / (hi - lo)
        return s, orig_lo - lo * s
    return 1.0, (orig_lo + orig_hi) / 2 - (lo + hi) / 2


def restyle_path(orig, cfg, name, log):
    """cfg: embolden (stem change in units), close (sliver radius), style (squarify parameters)."""
    if not list(orig.contours):
        return None
    ob = orig.bounds
    wide = embolden(orig, cfg["embolden"])
    if not list(wide.contours):
        return None
    fitted = close_slits(soften(wide, cfg["style"]), cfg["close"])
    ratio = abs(fitted.area) / max(abs(wide.area), 1)
    if not 0.8 < ratio < 1.25:
        log.append((name, "area-ratio", round(ratio, 2)))
        fitted = wide
    nb = fitted.bounds
    sx, tx = fit_axis(nb[0], nb[2], ob[0], ob[2], FIT_X_MIN_EXTENT)
    sy, ty = fit_axis(nb[1], nb[3], ob[1], ob[3], FIT_Y_MIN_EXTENT)
    pen = TTGlyphPen(None)
    fitted.draw(TransformPen(Cu2QuPen(pen, 1.0, reverse_direction=True), (sx, 0, 0, sy, tx, ty)))
    return pen.glyph()


def rescale(font, factor):
    """Uniformly scales a font by `factor` while keeping 1000 units per em."""
    scale_upem(font, round(font["head"].unitsPerEm * factor))
    font["head"].unitsPerEm = 1000


def restyle_font(font, cfg, log):
    gs = font.getGlyphSet()
    glyf = font["glyf"]
    unpushed = {name for cp, name in font.getBestCmap().items()
                if unicodedata.category(chr(cp)) in UNPUSHED_CATEGORIES}
    unpushed_cfg = dict(cfg, style=dict(cfg["style"], squircle_n=2.0))
    cmap = font.getBestCmap()
    # Letters that pack several strokes into one cell get a larger closing radius, which fills
    # the sliver counters between their strokes (an ink-trap fill) so rows of them do not shimmer.
    filled = {cmap[ord(ch)] for ch in cfg.get("fill_chars", "") if ord(ch) in cmap}
    filled_cfg = dict(cfg, close=cfg.get("fill_close", cfg["close"]))
    exact = {name for cp, name in cmap.items() if is_exact(cp)}
    new = {}
    for name in font.getGlyphOrder():
        g = glyf[name]
        if g.isComposite() or g.numberOfContours == 0 or name in exact:
            continue
        use = unpushed_cfg if name in unpushed else filled_cfg if name in filled else cfg
        new[name] = restyle_path(glyph_path(gs, name), use, name, log)
    for name, g in new.items():
        glyf[name] = g if g is not None else TTGlyphPen(None).glyph()
