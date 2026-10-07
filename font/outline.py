"""Outline plumbing: segment extraction and flattening of curves into polygons."""

from fontTools.pens.basePen import BasePen


class SegPen(BasePen):
    def __init__(self):
        super().__init__(None)
        self.contours = []
        self.cur = None
        self.pt = None

    def _moveTo(self, p):
        self.cur = []
        self.start = p
        self.pt = p

    def _lineTo(self, p):
        self.cur.append(("L", self.pt, p))
        self.pt = p

    def _qCurveToOne(self, c, p):
        self.cur.append(("Q", self.pt, c, p))
        self.pt = p

    def _curveToOne(self, c1, c2, p):
        self.cur.append(("C", self.pt, c1, c2, p))
        self.pt = p

    def _closePath(self):
        if self.pt != self.start:
            self.cur.append(("L", self.pt, self.start))
        if self.cur:
            self.contours.append(self.cur)
        self.cur = None

    _endPath = _closePath


def flatten(s, k):
    out = []
    for i in range(1, k + 1):
        t = i / k
        u = 1 - t
        if s[0] == "Q":
            p0, c, p1 = s[1], s[2], s[3]
            out.append((u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0],
                        u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1]))
        elif s[0] == "C":
            p0, c1, c2, p1 = s[1], s[2], s[3], s[4]
            out.append((u**3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t**3 * p1[0],
                        u**3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t**3 * p1[1]))
        else:
            out.append(s[2])
    return out


def flatten_contours(path, samples=12):
    """Contours of a pathops path as polygons."""
    pen = SegPen()
    path.draw(pen)
    out = []
    for segs in pen.contours:
        pts = [segs[0][1]]
        for s in segs:
            pts += flatten(s, samples)
        out.append(pts)
    return out
